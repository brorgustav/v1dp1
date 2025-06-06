# v1dp1

Utilities for experimenting with video on the Raspberry Pi.

## Random Framebuffer Overlay

`randomfb.py` generates a noisy overlay on a framebuffer device.  It can be
layered over another video source when using the Pi's second framebuffer.

### Usage

```bash
sudo ./randomfb.py --fb /dev/fb1 --width 640 --height 480 \
                   --opacity 0.5 --colormap hsv --fps 30
```

Available colormaps: `gray`, `hsv`, `hot`.
