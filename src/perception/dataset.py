"""
SIH 26126 — RELLIS-3D Navigation Dataset

PyTorch Dataset for the preprocessed RELLIS-3D data with 6-class
navigation masks. Reads from data/processed/rellis3d/ using the
split manifests in data/splits/.

Classes:
    0: SMOOTH
    1: ROUGH
    2: BUMPY
    3: FORBIDDEN
    4: OBSTACLE
    5: BACKGROUND
"""

import json
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset


class RELLISNavDataset(Dataset):
    """PyTorch Dataset for preprocessed RELLIS-3D navigation data.

    Args:
        manifest_path: Path to the split manifest JSON (train.json, val.json, test.json).
        image_processor: HuggingFace SegFormer image processor for RGB normalization.
        augment: Whether to apply training augmentations (not implemented in baseline).
    """

    NUM_CLASSES = 6

    def __init__(
        self,
        manifest_path: str | Path,
        image_processor=None,
        augment: bool = False,
    ):
        self.manifest_path = Path(manifest_path)
        self.image_processor = image_processor
        self.augment = augment

        # Load manifest
        with open(self.manifest_path, "r") as f:
            self.entries = json.load(f)

        # Validate at least one entry exists
        if not self.entries:
            raise ValueError(f"Empty manifest: {self.manifest_path}")

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, idx: int) -> dict:
        entry = self.entries[idx]

        rgb_path = Path(entry["rgb"])
        mask_path = Path(entry["mask"])

        # Load RGB image
        rgb_img = Image.open(rgb_path).convert("RGB")

        # Load mask as numpy array (single channel, values 0-5)
        mask = np.array(Image.open(mask_path), dtype=np.int64)

        # Apply image processor (handles normalization, tensor conversion)
        if self.image_processor is not None:
            # SegFormerImageProcessor expects PIL image and returns pixel_values
            encoded = self.image_processor(
                images=rgb_img,
                return_tensors="pt",
            )
            pixel_values = encoded["pixel_values"].squeeze(0)  # (C, H, W)
        else:
            # Fallback: simple tensor conversion
            pixel_values = torch.from_numpy(
                np.array(rgb_img, dtype=np.float32).transpose(2, 0, 1) / 255.0
            )

        # Mask → long tensor (H, W)
        labels = torch.from_numpy(mask).long()

        return {
            "pixel_values": pixel_values,
            "labels": labels,
            "stem": entry["stem"],
        }

    def get_entry(self, idx: int) -> dict:
        """Return raw manifest entry for debugging."""
        return self.entries[idx]
