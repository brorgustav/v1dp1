#!/usr/bin/env python3
"""Generate random noise overlay on Raspberry Pi framebuffer."""

import argparse
import mmap
import os
import sys
import time
import subprocess
import colorsys
from typing import Optional

import numpy as np

# === Default Configuration ===
CONFIG = {
    "fb": "/dev/fb0",                 # Framebuffer device path (usually /dev/fb0)

    "width": None,                    # Framebuffer width in pixels (auto-detect if None)
    "height": None,                   # Framebuffer height in pixels (auto-detect if None)

    "opacity": 0.5,                   # Opacity of new noise over the previous frame (0.0–1.0)

    "seed": True,                    # Enable reproducible noise pattern by seeding with a random value
    "debug": True,                   # Print config and runtime debug info to console
    "partial_update": True,         # If True, only update a moving band on screen each frame

    "noise_mode": {
        "type": "rgb",         # Type of noise to generate: blackwhite, rgb, colormap
        "blackwhite_mapping": "gray"  # Only used when type == 'colormap': gray, hsv, hot
    }
}

def parse_args():
    p = argparse.ArgumentParser(description="Random framebuffer overlay")
    p.add_argument("--fb", default=CONFIG["fb"], help="Framebuffer device")
    p.add_argument("--width", type=int, default=CONFIG["width"], help="Framebuffer width (auto-detect)")
    p.add_argument("--height", type=int, default=CONFIG["height"], help="Framebuffer height (auto-detect)")
    p.add_argument("--opacity", type=float, default=CONFIG["opacity"], help="Opacity of noise overlay (0.0 to 1.0)")

    p.add_argument("--blackwhite-mapping", choices=["gray", "hsv", "hot"],
                   default=CONFIG["noise_mode"]["blackwhite_mapping"],
                   help="How to colorize grayscale noise in colormap mode")

    p.add_argument("--noise-mode", choices=["blackwhite", "rgb", "colormap"],
                   default=CONFIG["noise_mode"]["type"],
                   help="Noise style: blackwhite = grayscale, rgb = true color, colormap = grayscale with color mapping")

    p.add_argument("--seed", action="store_true", default=CONFIG["seed"],
                   help="Enable reproducible noise pattern (random seed will be printed)")

    p.add_argument("--debug", action="store_true", default=CONFIG["debug"], help="Enable debug output")
    p.add_argument("--partial-update", action="store_true", default=CONFIG["partial_update"], help="Enable partial screen updates")
    args = p.parse_args()

    if args.seed:
        import random
        seed = random.randint(0, 2**32 - 1)
        np.random.seed(seed)
        if args.debug:
            print(f"Using seed: {seed}")

    if args.debug:
        print("Running with configuration:")
        for k, v in vars(args).items():
            print(f"  {k}: {v}")
    return args

def get_resolution_from_fbset(fb: str) -> Optional[tuple[int, int]]:
    try:
        output = subprocess.check_output(["fbset", "-fb", fb], text=True)
        for line in output.splitlines():
            if "geometry" in line:
                parts = line.split()
                return int(parts[1]), int(parts[2])
    except Exception:
        return None

def get_bits_per_pixel(fb: str) -> int:
    name = os.path.basename(fb)
    try:
        with open(f"/sys/class/graphics/{name}/bits_per_pixel") as f:
            return int(f.read().strip())
    except:
        return 8

def apply_colormap(gray: np.ndarray, method: str) -> np.ndarray:
    if method == "gray":
        return np.stack([gray, gray, gray], axis=-1)
    elif method == "hsv":
        flat = gray.flatten() / 255.0
        rgb = np.array([colorsys.hsv_to_rgb(h, 1.0, 1.0) for h in flat])
        return (rgb.reshape(gray.shape + (3,)) * 255).astype(np.uint8)
    elif method == "hot":
        r = np.clip(gray * 3, 0, 255)
        g = np.clip(gray * 3 - 255, 0, 255)
        b = np.clip(gray * 3 - 510, 0, 255)
        return np.stack([r, g, b], axis=-1).astype(np.uint8)

def rgb_to_rgb565(rgb: np.ndarray) -> bytes:
    r = (rgb[:, :, 0] >> 3).astype(np.uint16) << 11
    g = (rgb[:, :, 1] >> 2).astype(np.uint16) << 5
    b = (rgb[:, :, 2] >> 3).astype(np.uint16)
    return (r | g | b).astype(np.uint16).tobytes()

def gray_to_rgb565(gray: np.ndarray) -> bytes:
    return rgb_to_rgb565(np.stack([gray, gray, gray], axis=-1))

def gray_to_argb8888(gray: np.ndarray) -> bytes:
    a = np.full_like(gray, 255, dtype=np.uint8)
    rgba = np.stack((a, gray, gray, gray), axis=-1)
    return rgba.astype(np.uint8).tobytes()

def rgb_to_argb8888(rgb: np.ndarray) -> bytes:
    a = np.full((rgb.shape[0], rgb.shape[1], 1), 255, dtype=np.uint8)
    argb = np.concatenate((a, rgb), axis=-1)
    return argb.astype(np.uint8).tobytes()

def main():
    args = parse_args()

    if args.width and args.height:
        width, height = args.width, args.height
    else:
        res = get_resolution_from_fbset(args.fb)
        if res:
            width, height = res
        else:
            print("Error: could not detect resolution. Use --width/--height.")
            sys.exit(1)

    bpp = get_bits_per_pixel(args.fb)
    bytes_per_pixel = bpp // 8

    if args.debug:
        print(f"Resolution: {width}x{height}, BPP: {bpp}")

    fb_fd = os.open(args.fb, os.O_RDWR)
    fb_size = width * height * bytes_per_pixel
    framebuffer = mmap.mmap(fb_fd, fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE)

    frame = np.zeros((height, width), dtype=np.uint8)

    try:
        while True:
            if args.noise_mode == 'rgb':
                noise = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
            else:
                noise = np.random.randint(0, 256, (height, width), dtype=np.uint8)

            if args.partial_update:
                band_height = height // 4
                y_offset = (int(time.time() * 10) % (height - band_height))
                if args.noise_mode == 'rgb':
                    frame_rgb = frame if frame.ndim == 3 else np.zeros((height, width, 3), dtype=np.uint8)
                    if args.opacity < 1.0:
                        frame_rgb[y_offset:y_offset+band_height, :] = (
                            args.opacity * noise[y_offset:y_offset+band_height, :] +
                            (1.0 - args.opacity) * frame_rgb[y_offset:y_offset+band_height, :]
                        ).astype(np.uint8)
                    else:
                        frame_rgb[y_offset:y_offset+band_height, :] = noise[y_offset:y_offset+band_height, :]
                    frame = frame_rgb
                else:
                    if args.opacity < 1.0:
                        frame[y_offset:y_offset+band_height, :] = (
                            args.opacity * noise[y_offset:y_offset+band_height, :] +
                            (1.0 - args.opacity) * frame[y_offset:y_offset+band_height, :]
                        ).astype(np.uint8)
                    else:
                        frame[y_offset:y_offset+band_height, :] = noise[y_offset:y_offset+band_height, :]
            else:
                if args.noise_mode == 'rgb':
                    if args.opacity < 1.0:
                        frame = (args.opacity * noise + (1.0 - args.opacity) * frame).astype(np.uint8)
                    else:
                        frame = noise
                else:
                    if args.opacity < 1.0:
                        frame = (args.opacity * noise + (1.0 - args.opacity) * frame).astype(np.uint8)
                    else:
                        frame[:, :] = noise

            framebuffer.seek(0)

            if bpp == 8:
                framebuffer.write(frame.astype(np.uint8).tobytes())
            elif bpp == 16:
                if args.noise_mode == "rgb":
                    framebuffer.write(rgb_to_rgb565(frame))
                elif args.noise_mode == "colormap":
                    rgb = apply_colormap(frame, args.blackwhite_mapping)
                    framebuffer.write(rgb_to_rgb565(rgb))
                else:
                    framebuffer.write(gray_to_rgb565(frame))
            elif bpp == 32:
                if args.noise_mode == "rgb":
                    framebuffer.write(rgb_to_argb8888(frame))
                elif args.noise_mode == "colormap":
                    rgb = apply_colormap(frame, args.blackwhite_mapping)
                    framebuffer.write(rgb_to_argb8888(rgb))
                else:
                    framebuffer.write(gray_to_argb8888(frame))
            else:
                print(f"Unsupported BPP: {bpp}")
                break

            time.sleep(0.03)
    finally:
        framebuffer.close()
        os.close(fb_fd)

if __name__ == "__main__":
    main()