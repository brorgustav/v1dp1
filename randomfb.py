#!/usr/bin/env python3
"""Generate random noise overlay on Raspberry Pi framebuffer.

This script writes random patterns to a framebuffer device.  The overlay can
have configurable opacity and color mapping.  It is useful when the Pi is
outputting video on another layer (e.g. /dev/fb1) and you want a random noise
layer on top (/dev/fb0).  Provide ``--seed`` to generate deterministic noise
patterns.
"""

import argparse
import colorsys
import mmap
import os
import sys
import time
from typing import Optional

import numpy as np


def read_numeric(path: str) -> Optional[float]:
    """Read a numeric value from a file path."""
    try:
        with open(path, "r") as f:
            value_str = f.readline().strip()
            return float(value_str)
    except Exception:
        return None


def parse_args():
    p = argparse.ArgumentParser(description="Random framebuffer overlay")
    p.add_argument("--fb", default="/dev/fb0", help="Framebuffer device")
    p.add_argument("--width", type=int, default=640, help="Framebuffer width")
    p.add_argument("--height", type=int, default=480, help="Framebuffer height")
    p.add_argument("--opacity", type=float, default=0.5,
                   help="Opacity 0.0-1.0 for overlay")
    p.add_argument("--colormap", choices=["gray", "hsv", "hot"], default="gray",
                   help="Color mapping for noise")
    p.add_argument("--fps", type=float, default=30.0, help="Frames per second")
    p.add_argument("--seed", type=int, help="Random seed for reproducible output")
    p.add_argument("--input-path", help="Path to numeric value for modulation")
    p.add_argument("--min-value", type=float, default=0.0,
                   help="Minimum input value for scaling")
    p.add_argument("--max-value", type=float, default=1.0,
                   help="Maximum input value for scaling")
    return p.parse_args()


def apply_colormap(gray: np.ndarray, mode: str) -> np.ndarray:
    """Map grayscale noise to RGB using a simple colormap."""
    if mode == "gray":
        rgb = np.stack([gray, gray, gray], axis=-1)
    elif mode == "hsv":
        h = gray  # hue from 0..1
        s = np.ones_like(h)
        v = np.ones_like(h)
        hsv = np.stack([h, s, v], axis=-1)
        # colorsys works on flat arrays, vectorize for simplicity
        flat = hsv.reshape(-1, 3)
        rgb_list = [colorsys.hsv_to_rgb(*t) for t in flat]
        rgb = np.array(rgb_list, dtype=np.float32).reshape(hsv.shape)
    elif mode == "hot":
        # simple "hot" colormap (black-red-yellow-white)
        r = np.clip(3 * gray, 0, 1)
        g = np.clip(3 * gray - 1, 0, 1)
        b = np.clip(3 * gray - 2, 0, 1)
        rgb = np.stack([r, g, b], axis=-1)
    else:
        raise ValueError(f"Unknown colormap: {mode}")
    return (rgb * 255).astype(np.uint8)


def main():
    args = parse_args()
    alpha = int(max(0.0, min(1.0, args.opacity)) * 255)
    frame_bytes = args.width * args.height * 4  # ARGB8888

    rng = np.random.default_rng(args.seed)

    try:
        fb_fd = os.open(args.fb, os.O_RDWR)
    except FileNotFoundError:
        sys.exit(f"Framebuffer {args.fb} not found")

    with mmap.mmap(fb_fd, frame_bytes, mmap.MAP_SHARED, mmap.PROT_WRITE) as m:
        dt = 1.0 / max(args.fps, 1)
        while True:
            gray = rng.random((args.height, args.width), dtype=np.float32)

            if args.input_path:
                val = read_numeric(args.input_path)
                if val is not None:
                    scale = (val - args.min_value) / (args.max_value - args.min_value)
                    scale = max(0.0, min(1.0, scale))
                    gray *= scale

            rgb = apply_colormap(gray, args.colormap)
            a = np.full((args.height, args.width, 1), alpha, dtype=np.uint8)
            frame = np.concatenate([a, rgb], axis=-1)
            m.seek(0)
            m.write(frame.tobytes())
            time.sleep(dt)


if __name__ == "__main__":
    main()