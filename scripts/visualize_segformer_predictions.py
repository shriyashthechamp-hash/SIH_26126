#!/usr/bin/env python3
"""
SIH 26126 — Visual Diagnostic Script

Runs inference on a few deterministic validation samples and generates
side-by-side visualizations (RGB, Ground Truth, Prediction) to help
diagnose model learning behavior.

Usage:
    python scripts/visualize_segformer_predictions.py
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from transformers import (
    SegformerForSemanticSegmentation,
    SegformerImageProcessor,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.perception.dataset import RELLISNavDataset

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

NAV_NAMES = {
    0: "SMOOTH",
    1: "ROUGH",
    2: "BUMPY",
    3: "FORBIDDEN",
    4: "OBSTACLE",
    5: "BACKGROUND",
}

# Distinct colors for the 6 classes
COLORS = np.array([
    [0, 255, 0],      # 0: SMOOTH (Green)
    [255, 165, 0],    # 1: ROUGH (Orange)
    [139, 69, 19],    # 2: BUMPY (Brown)
    [0, 0, 255],      # 3: FORBIDDEN (Blue)
    [255, 0, 0],      # 4: OBSTACLE (Red)
    [128, 128, 128],  # 5: BACKGROUND (Gray)
], dtype=np.uint8)


def get_device() -> torch.device:
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def draw_segmentation(mask: np.ndarray) -> np.ndarray:
    """Convert a 2D mask of class IDs to an RGB image."""
    h, w = mask.shape
    colored = np.zeros((h, w, 3), dtype=np.uint8)
    for c in range(6):
        colored[mask == c] = COLORS[c]
    return colored


def main() -> int:
    parser = argparse.ArgumentParser(description="Visual Diagnostic")
    parser.add_argument(
        "--checkpoint", type=str,
        default="experiments/rellis_segformer_b0_baseline/best_model.pt",
    )
    parser.add_argument("--splits-dir", type=str, default="data/splits")
    parser.add_argument("--output-dir", type=str, default="experiments/rellis_segformer_b0_baseline/visuals")
    parser.add_argument("--num-samples", type=int, default=5)
    args = parser.parse_args()

    device = get_device()
    logger.info(f"Device: {device}")

    # Ensure output dir exists
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load model configuration
    config_path = Path("experiments/rellis_segformer_b0_baseline/config.json")
    if not config_path.exists():
        logger.error(f"Config not found at {config_path}")
        return 1

    with open(config_path) as f:
        config = json.load(f)
    
    model_name = config.get("model", "nvidia/segformer-b0-finetuned-ade-512-512")

    # 2. Load model & image processor
    logger.info(f"Loading processor from {model_name}...")
    processor = SegformerImageProcessor.from_pretrained(
        model_name, do_resize=False, do_rescale=True, do_normalize=True
    )

    logger.info(f"Loading model and weights from {args.checkpoint}...")
    model = SegformerForSemanticSegmentation.from_pretrained(
        model_name, num_labels=6, ignore_mismatched_sizes=True
    )
    
    ckpt_path = Path(args.checkpoint)
    if not ckpt_path.exists():
        logger.error(f"Checkpoint not found at {ckpt_path}")
        return 1
        
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(device)
    model.eval()

    # 3. Load dataset
    val_manifest = Path(args.splits_dir) / "val.json"
    dataset = RELLISNavDataset(manifest_path=val_manifest, image_processor=processor)

    logger.info(f"\nProcessing {args.num_samples} validation samples...")

    # Fixed indices for deterministic output
    indices = np.linspace(0, len(dataset) - 1, args.num_samples, dtype=int)

    for i, idx in enumerate(indices):
        sample = dataset[idx]
        stem = sample["stem"]
        
        # Original RGB (unprocessed)
        raw_entry = dataset.get_entry(idx)
        raw_rgb = Image.open(raw_entry["rgb"]).convert("RGB")
        raw_rgb_arr = np.array(raw_rgb)
        
        pixel_values = sample["pixel_values"].unsqueeze(0).to(device)
        labels = sample["labels"].numpy()

        with torch.no_grad():
            outputs = model(pixel_values=pixel_values)
            logits = outputs.logits
            
            upsampled = nn.functional.interpolate(
                logits, size=labels.shape, mode="bilinear", align_corners=False
            )
            
            pred = upsampled.argmax(dim=1).squeeze(0).cpu().numpy()

        # Stats
        unique_pred, counts_pred = np.unique(pred, return_counts=True)
        unique_gt, counts_gt = np.unique(labels, return_counts=True)
        
        logger.info(f"\nSample {i+1}: {stem}")
        logger.info("  Ground Truth Classes:")
        for c, count in zip(unique_gt, counts_gt):
            logger.info(f"    {NAV_NAMES.get(c, str(c)):<10}: {count:>8} px")
            
        logger.info("  Predicted Classes:")
        for c, count in zip(unique_pred, counts_pred):
            logger.info(f"    {NAV_NAMES.get(c, str(c)):<10}: {count:>8} px")

        # Visualization
        gt_vis = draw_segmentation(labels)
        pred_vis = draw_segmentation(pred)

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        axes[0].imshow(raw_rgb_arr)
        axes[0].set_title("Original RGB")
        axes[0].axis("off")
        
        axes[1].imshow(gt_vis)
        axes[1].set_title("Ground Truth")
        axes[1].axis("off")
        
        axes[2].imshow(pred_vis)
        axes[2].set_title("Prediction")
        axes[2].axis("off")
        
        plt.tight_layout()
        out_file = out_dir / f"val_{stem}.png"
        plt.savefig(out_file, dpi=150)
        plt.close()
        
        logger.info(f"  Saved visualization: {out_file}")

    logger.info("\nDiagnostic complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
