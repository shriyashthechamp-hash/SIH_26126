#!/usr/bin/env python3
"""
SIH 26126 — SegFormer-B0 Training Script

Fine-tunes SegFormer-B0 on the preprocessed RELLIS-3D dataset for
6-class terrain navigation segmentation.

Usage:
    # Smoke test (1 batch, verify pipeline works)
    python scripts/train_segformer.py --smoke-test

    # Baseline training (10 epochs)
    python scripts/train_segformer.py --epochs 10

    # Resume from checkpoint
    python scripts/train_segformer.py --epochs 10 --resume experiments/rellis_segformer_b0_baseline/last_checkpoint.pt
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import (
    SegformerForSemanticSegmentation,
    SegformerImageProcessor,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.perception.dataset import RELLISNavDataset

# ============================================================================
# Constants
# ============================================================================

NAV_NAMES = {
    0: "SMOOTH",
    1: "ROUGH",
    2: "BUMPY",
    3: "FORBIDDEN",
    4: "OBSTACLE",
    5: "BACKGROUND",
}

NUM_CLASSES = 6

MODEL_NAME = "nvidia/segformer-b0-finetuned-ade-512-512"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Device Detection
# ============================================================================

def get_device(requested: str = "auto") -> torch.device:
    """Detect best available device: MPS > CUDA > CPU."""
    if requested != "auto":
        device = torch.device(requested)
        logger.info(f"Using requested device: {device}")
        return device

    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        device = torch.device("mps")
        logger.info("Using MPS (Apple Silicon GPU)")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info(f"Using CUDA ({torch.cuda.get_device_name(0)})")
    else:
        device = torch.device("cpu")
        logger.info("Using CPU (no GPU detected)")

    return device


# ============================================================================
# Metrics
# ============================================================================

def compute_metrics(
    all_preds: list[np.ndarray],
    all_labels: list[np.ndarray],
    num_classes: int = NUM_CLASSES,
) -> dict:
    """Compute mIoU, per-class IoU, and pixel accuracy.

    Handles classes with zero ground-truth pixels gracefully.
    """
    # Build confusion matrix
    confusion = np.zeros((num_classes, num_classes), dtype=np.int64)

    for pred, label in zip(all_preds, all_labels):
        # Flatten
        pred_flat = pred.flatten()
        label_flat = label.flatten()

        # Only count valid pixels
        valid = (label_flat >= 0) & (label_flat < num_classes)
        pred_flat = pred_flat[valid]
        label_flat = label_flat[valid]

        for c_true in range(num_classes):
            for c_pred in range(num_classes):
                confusion[c_true, c_pred] += np.sum(
                    (label_flat == c_true) & (pred_flat == c_pred)
                )

    # Per-class IoU
    per_class_iou = {}
    valid_ious = []

    for c in range(num_classes):
        tp = confusion[c, c]
        fp = confusion[:, c].sum() - tp
        fn = confusion[c, :].sum() - tp

        gt_pixels = confusion[c, :].sum()

        if gt_pixels == 0:
            # No ground-truth pixels for this class
            per_class_iou[c] = {
                "name": NAV_NAMES[c],
                "iou": None,
                "note": "undefined — zero ground-truth pixels",
                "gt_pixels": 0,
            }
        else:
            denom = tp + fp + fn
            iou = tp / denom if denom > 0 else 0.0
            per_class_iou[c] = {
                "name": NAV_NAMES[c],
                "iou": round(float(iou), 4),
                "gt_pixels": int(gt_pixels),
            }
            valid_ious.append(iou)

    # mIoU (only over classes with ground-truth pixels)
    miou = float(np.mean(valid_ious)) if valid_ious else 0.0

    # Pixel accuracy
    total_correct = np.trace(confusion)
    total_pixels = confusion.sum()
    pixel_acc = total_correct / total_pixels if total_pixels > 0 else 0.0

    return {
        "miou": round(miou, 4),
        "pixel_accuracy": round(float(pixel_acc), 4),
        "per_class_iou": per_class_iou,
        "num_classes_evaluated": len(valid_ious),
    }


# ============================================================================
# Training Loop
# ============================================================================

def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler,
    device: torch.device,
    class_weights: torch.Tensor,
    epoch: int,
) -> float:
    """Train for one epoch. Returns average loss."""
    model.train()
    total_loss = 0.0
    num_batches = 0

    loss_fn = nn.CrossEntropyLoss(weight=class_weights.to(device))

    for batch_idx, batch in enumerate(dataloader):
        pixel_values = batch["pixel_values"].to(device)
        labels = batch["labels"].to(device)

        # Forward pass
        outputs = model(pixel_values=pixel_values)
        logits = outputs.logits  # (B, num_classes, H/4, W/4)

        # Upsample logits to match label size
        upsampled = nn.functional.interpolate(
            logits,
            size=labels.shape[-2:],
            mode="bilinear",
            align_corners=False,
        )

        # Compute loss
        loss = loss_fn(upsampled, labels)

        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        if scheduler is not None:
            scheduler.step()

        total_loss += loss.item()
        num_batches += 1

        if (batch_idx + 1) % 20 == 0:
            current_lr = optimizer.param_groups[0]["lr"]
            logger.info(
                f"  Epoch {epoch} [{batch_idx + 1}/{len(dataloader)}] "
                f"loss={loss.item():.4f} lr={current_lr:.4e}"
            )

    avg_loss = total_loss / max(num_batches, 1)
    return avg_loss


@torch.no_grad()
def validate(
    model: nn.Module,
    dataloader: DataLoader,
    device: torch.device,
    class_weights: torch.Tensor,
) -> tuple[float, dict]:
    """Validate. Returns (avg_loss, metrics_dict)."""
    model.eval()
    total_loss = 0.0
    num_batches = 0

    loss_fn = nn.CrossEntropyLoss(weight=class_weights.to(device))

    all_preds = []
    all_labels = []

    for batch in dataloader:
        pixel_values = batch["pixel_values"].to(device)
        labels = batch["labels"].to(device)

        outputs = model(pixel_values=pixel_values)
        logits = outputs.logits

        upsampled = nn.functional.interpolate(
            logits,
            size=labels.shape[-2:],
            mode="bilinear",
            align_corners=False,
        )

        loss = loss_fn(upsampled, labels)
        total_loss += loss.item()
        num_batches += 1

        # Predictions
        preds = upsampled.argmax(dim=1).cpu().numpy()
        labels_np = labels.cpu().numpy()

        all_preds.extend(preds)
        all_labels.extend(labels_np)

    avg_loss = total_loss / max(num_batches, 1)
    metrics = compute_metrics(all_preds, all_labels)

    return avg_loss, metrics


# ============================================================================
# Smoke Test
# ============================================================================

def run_smoke_test(args) -> int:
    """Run a minimal smoke test: 1 batch forward + backward."""

    logger.info("=" * 60)
    logger.info("SMOKE TEST")
    logger.info("=" * 60)

    # Device
    device = get_device(args.device)
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"Device: {device}")

    # Image processor
    logger.info(f"Loading image processor from {MODEL_NAME}...")
    image_processor = SegformerImageProcessor.from_pretrained(
        MODEL_NAME,
        do_resize=False,  # We already resized to 512×512
        do_rescale=True,
        do_normalize=True,
    )

    # Dataset
    train_manifest = Path(args.splits_dir) / "train.json"
    logger.info(f"Loading dataset from {train_manifest}...")
    dataset = RELLISNavDataset(
        manifest_path=train_manifest,
        image_processor=image_processor,
    )
    logger.info(f"Dataset size: {len(dataset)}")

    # DataLoader — single batch
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,  # Use 0 for smoke test
    )

    # Load one batch
    logger.info("Loading one batch...")
    batch = next(iter(loader))
    pixel_values = batch["pixel_values"]
    labels = batch["labels"]

    logger.info(f"  pixel_values shape: {pixel_values.shape}")
    logger.info(f"  pixel_values dtype:  {pixel_values.dtype}")
    logger.info(f"  labels shape:        {labels.shape}")
    logger.info(f"  labels dtype:        {labels.dtype}")
    logger.info(f"  labels unique:       {torch.unique(labels).tolist()}")

    # Model
    logger.info(f"Loading SegFormer-B0 ({MODEL_NAME})...")
    model = SegformerForSemanticSegmentation.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_CLASSES,
        ignore_mismatched_sizes=True,
    )
    model = model.to(device)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"  Total params:     {total_params:,}")
    logger.info(f"  Trainable params: {trainable_params:,}")

    # Load class weights
    weights_path = Path(args.splits_dir) / "class_weights.json"
    with open(weights_path) as f:
        weights_data = json.load(f)
    weight_vector = torch.tensor(weights_data["weight_vector"], dtype=torch.float32)
    logger.info(f"  Class weights: {weight_vector.tolist()}")

    # Forward pass
    logger.info("Running forward pass...")
    pixel_values = pixel_values.to(device)
    labels = labels.to(device)

    outputs = model(pixel_values=pixel_values)
    logits = outputs.logits
    logger.info(f"  logits shape: {logits.shape}")

    # Upsample and compute loss
    upsampled = nn.functional.interpolate(
        logits,
        size=labels.shape[-2:],
        mode="bilinear",
        align_corners=False,
    )
    logger.info(f"  upsampled shape: {upsampled.shape}")

    loss_fn = nn.CrossEntropyLoss(weight=weight_vector.to(device))
    loss = loss_fn(upsampled, labels)
    logger.info(f"  loss: {loss.item():.4f}")

    # Backward pass
    logger.info("Running backward pass...")
    loss.backward()
    logger.info("  backward: OK")

    # Optimizer step
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    optimizer.step()
    logger.info("  optimizer step: OK")

    # Predictions check
    preds = upsampled.argmax(dim=1)
    logger.info(f"  preds shape:  {preds.shape}")
    logger.info(f"  preds unique: {torch.unique(preds).tolist()}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("SMOKE TEST PASSED ✅")
    logger.info("=" * 60)

    return 0


# ============================================================================
# Verify Scheduler
# ============================================================================

def run_verify_scheduler(args) -> int:
    """Run a short dry run to verify optimizer and scheduler behave correctly."""

    logger.info("=" * 60)
    logger.info("VERIFY SCHEDULER (DRY RUN)")
    logger.info("=" * 60)

    device = get_device(args.device)
    
    image_processor = SegformerImageProcessor.from_pretrained(
        MODEL_NAME, do_resize=False, do_rescale=True, do_normalize=True
    )
    
    train_manifest = Path(args.splits_dir) / "train.json"
    dataset = RELLISNavDataset(manifest_path=train_manifest, image_processor=image_processor)
    
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    
    model = SegformerForSemanticSegmentation.from_pretrained(
        MODEL_NAME, num_labels=NUM_CLASSES, ignore_mismatched_sizes=True
    ).to(device)

    weights_path = Path(args.splits_dir) / "class_weights.json"
    with open(weights_path) as f:
        weights_data = json.load(f)
    weight_vector = torch.tensor(weights_data["weight_vector"], dtype=torch.float32)
    loss_fn = nn.CrossEntropyLoss(weight=weight_vector.to(device))

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)

    total_steps = len(loader) * args.epochs
    warmup_steps = max(1, int(total_steps * 0.05))

    def lr_lambda(step):
        if step < warmup_steps:
            return float(step) / float(max(1, warmup_steps))
        progress = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
        return max(0.0, 0.5 * (1.0 + np.cos(np.pi * progress)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    logger.info(f"Total steps: {total_steps}, Warmup steps: {warmup_steps}, Initial LR Config: {args.lr}")
    
    # Track a parameter to verify updates
    param_name = "decode_head.classifier.weight"
    param_tensor = dict(model.named_parameters())[param_name]
    initial_param_norm = param_tensor.norm().item()
    logger.info(f"Initial {param_name} norm: {initial_param_norm:.6f}")

    model.train()
    
    for step, batch in enumerate(loader):
        if step >= 20:
            break
            
        pixel_values = batch["pixel_values"].to(device)
        labels = batch["labels"].to(device)
        
        outputs = model(pixel_values=pixel_values)
        upsampled = nn.functional.interpolate(
            outputs.logits, size=labels.shape[-2:], mode="bilinear", align_corners=False
        )
        
        loss = loss_fn(upsampled, labels)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        scheduler.step()
        
        current_lr = optimizer.param_groups[0]["lr"]
        current_param_norm = param_tensor.norm().item()
        
        logger.info(
            f"Step {step+1:02d}: LR = {current_lr:.6e} | Loss = {loss.item():.4f} "
            f"| Param Norm = {current_param_norm:.6f}"
        )

    logger.info("=" * 60)
    if param_tensor.norm().item() != initial_param_norm:
        logger.info("✅ Parameter update verified (weights changed)")
    else:
        logger.info("❌ Parameter update FAILED (weights did not change)")
    
    final_lr = optimizer.param_groups[0]["lr"]
    if final_lr > 0:
        logger.info("✅ Scheduler active verified (LR > 0)")
    else:
        logger.info("❌ Scheduler inactive (LR == 0)")
    logger.info("=" * 60)
        
    return 0


# ============================================================================
# Full Training
# ============================================================================

def run_training(args) -> int:
    """Run full training loop."""

    # --- Setup ---
    device = get_device(args.device)
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"Device: {device}")

    exp_dir = Path(args.experiment_dir)
    exp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Experiment dir: {exp_dir}")

    # --- Save config ---
    config = {
        "model": MODEL_NAME,
        "num_classes": NUM_CLASSES,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "weight_decay": 0.01,
        "device": str(device),
        "splits_dir": args.splits_dir,
        "timestamp": datetime.now().isoformat(),
    }
    with open(exp_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # --- Image Processor ---
    image_processor = SegformerImageProcessor.from_pretrained(
        MODEL_NAME,
        do_resize=False,
        do_rescale=True,
        do_normalize=True,
    )

    # --- Datasets ---
    splits_dir = Path(args.splits_dir)
    train_dataset = RELLISNavDataset(
        manifest_path=splits_dir / "train.json",
        image_processor=image_processor,
    )
    val_dataset = RELLISNavDataset(
        manifest_path=splits_dir / "val.json",
        image_processor=image_processor,
    )
    logger.info(f"Train samples: {len(train_dataset)}")
    logger.info(f"Val samples:   {len(val_dataset)}")

    # --- DataLoaders ---
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=(device.type != "cpu"),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=(device.type != "cpu"),
    )
    logger.info(f"Train batches: {len(train_loader)}")
    logger.info(f"Val batches:   {len(val_loader)}")

    # --- Model ---
    logger.info(f"Loading SegFormer-B0 from {MODEL_NAME}...")
    model = SegformerForSemanticSegmentation.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_CLASSES,
        ignore_mismatched_sizes=True,
    )
    model = model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Total params:     {total_params:,}")
    logger.info(f"Trainable params: {trainable_params:,}")

    # --- Class Weights ---
    weights_path = splits_dir / "class_weights.json"
    with open(weights_path) as f:
        weights_data = json.load(f)
    class_weights = torch.tensor(
        weights_data["weight_vector"], dtype=torch.float32
    )
    logger.info(f"Class weights: {class_weights.tolist()}")

    # --- Optimizer + Scheduler ---
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=0.01,
    )

    # Linear warmup + cosine decay
    total_steps = len(train_loader) * args.epochs
    warmup_steps = max(1, int(total_steps * 0.05))

    def lr_lambda(step):
        if step < warmup_steps:
            return float(step) / float(max(1, warmup_steps))
        progress = float(step - warmup_steps) / float(
            max(1, total_steps - warmup_steps)
        )
        return max(0.0, 0.5 * (1.0 + np.cos(np.pi * progress)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # --- Resume ---
    start_epoch = 0
    best_miou = 0.0
    history = []

    if args.resume and Path(args.resume).exists():
        logger.info(f"Resuming from {args.resume}...")
        checkpoint = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        start_epoch = checkpoint.get("epoch", 0) + 1
        best_miou = checkpoint.get("best_miou", 0.0)
        history = checkpoint.get("history", [])
        logger.info(f"Resumed at epoch {start_epoch}, best mIoU={best_miou:.4f}")

    # --- Training Loop ---
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Starting training: {args.epochs} epochs")
    logger.info("=" * 60)

    for epoch in range(start_epoch, args.epochs):
        epoch_start = time.time()

        current_lr = optimizer.param_groups[0]["lr"]
        logger.info(f"--- Epoch {epoch} starts | initial lr={current_lr:.4e} ---")

        # Train
        train_loss = train_one_epoch(
            model, train_loader, optimizer, scheduler,
            device, class_weights, epoch,
        )

        current_lr = optimizer.param_groups[0]["lr"]

        # Validate
        val_loss, val_metrics = validate(
            model, val_loader, device, class_weights,
        )

        epoch_time = time.time() - epoch_start
        miou = val_metrics["miou"]
        pixel_acc = val_metrics["pixel_accuracy"]

        # Log
        logger.info(
            f"Epoch {epoch}/{args.epochs - 1} "
            f"| train_loss={train_loss:.4f} "
            f"| val_loss={val_loss:.4f} "
            f"| mIoU={miou:.4f} "
            f"| px_acc={pixel_acc:.4f} "
            f"| lr={current_lr:.2e} "
            f"| {epoch_time:.0f}s"
        )

        # Per-class IoU
        for c in range(NUM_CLASSES):
            info = val_metrics["per_class_iou"][c]
            if info["iou"] is not None:
                logger.info(f"  {info['name']:<12} IoU={info['iou']:.4f}  ({info['gt_pixels']:,} gt px)")
            else:
                logger.info(f"  {info['name']:<12} IoU=undefined — {info['note']}")

        # History
        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "val_loss": round(val_loss, 6),
            "miou": miou,
            "pixel_accuracy": pixel_acc,
            "per_class_iou": {
                NAV_NAMES[c]: val_metrics["per_class_iou"][c]["iou"]
                for c in range(NUM_CLASSES)
            },
            "lr": current_lr,
            "epoch_time_s": round(epoch_time, 1),
        }
        history.append(epoch_record)

        # Save last checkpoint
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "best_miou": best_miou,
            "history": history,
        }
        torch.save(checkpoint, exp_dir / "last_checkpoint.pt")

        # Save best model
        if miou > best_miou:
            best_miou = miou
            torch.save(
                {"model_state_dict": model.state_dict(), "epoch": epoch, "miou": miou},
                exp_dir / "best_model.pt",
            )
            logger.info(f"  ★ New best mIoU: {best_miou:.4f}")

    # --- Save final outputs ---
    logger.info("")
    logger.info("=" * 60)
    logger.info("Training complete")
    logger.info("=" * 60)

    # Save history
    with open(exp_dir / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    # Save final metrics
    final_metrics = {
        "best_miou": best_miou,
        "final_epoch": args.epochs - 1,
        "final_train_loss": history[-1]["train_loss"],
        "final_val_loss": history[-1]["val_loss"],
        "final_miou": history[-1]["miou"],
        "final_pixel_accuracy": history[-1]["pixel_accuracy"],
        "final_per_class_iou": history[-1]["per_class_iou"],
    }
    with open(exp_dir / "final_metrics.json", "w") as f:
        json.dump(final_metrics, f, indent=2)

    logger.info(f"Best mIoU:      {best_miou:.4f}")
    logger.info(f"Final val loss: {history[-1]['val_loss']:.4f}")
    logger.info(f"Checkpoints:    {exp_dir}")

    return 0


# ============================================================================
# Entry Point
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="SIH 26126 — SegFormer-B0 Training"
    )
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=6e-5)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument(
        "--splits-dir", type=str, default="data/splits",
    )
    parser.add_argument(
        "--experiment-dir", type=str,
        default="experiments/rellis_segformer_b0_baseline",
    )
    parser.add_argument("--resume", type=str, default=None)
    parser.add_argument(
        "--smoke-test", action="store_true",
        help="Run a single-batch smoke test then exit",
    )
    parser.add_argument(
        "--verify-scheduler", action="store_true",
        help="Run a short 20-batch dry run to verify optimizer and scheduler",
    )
    args = parser.parse_args()

    if args.smoke_test:
        return run_smoke_test(args)
    elif args.verify_scheduler:
        return run_verify_scheduler(args)
    else:
        return run_training(args)


if __name__ == "__main__":
    sys.exit(main())
