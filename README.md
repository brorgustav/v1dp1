# v1dp1 — Framebuffer Noise Generator

Framebuffer video noise experiments on Raspberry Pi using Python and `/dev/fb0`.

## 🎯 Overview

`v1dp1_rand.py` generates real-time visual noise directly onto the framebuffer of your Raspberry Pi. You can create grayscale, RGB, or colormap-based effects with optional opacity, partial screen updates, and reproducibility.

---

## 🔧 Features

- 🖼️ Noise types: **blackwhite**, **rgb**, **colormap**
- 🎨 Colormaps: `gray`, `hsv`, `hot` (used with `colormap` noise)
- 🪄 Opacity blending (fade noise onto screen)
- 🧩 Partial updates (banded motion or reduced bandwidth)
- 🔁 Reproducible output with `--seed`
- 🕵️ Debug output for config + runtime info
- 🧠 Auto-detect resolution and color depth (8/16/32 bpp)

---

## 🚀 Usage
//
config.txt:
dtoverlay=dwc2
or
dtoverlay=dwc2,dr_mode=peripheral
//
cmdline.txt:
console=serial0,115200 console=tty1
then DIRECTLY after rootwait:
modules-load=dwc2,g_serial
//
sudo systemctl enable serial-getty@ttyGS0.service
sudo systemctl start serial-getty@ttyGS0.service
sudo systemctl is-active serial-getty@ttyGS0.service

(cmdline.txt) video=HDMI-A-1:640x480@60:e

```bash
sudo python3 v1dp1_rand.py [OPTIONS]
