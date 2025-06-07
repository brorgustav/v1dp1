# v1dp1
video raspberry pi

Utilities for experimenting with video on the Raspberry Pi.

## Random Framebuffer Overlay

`randomfb.py` generates a noisy overlay on a framebuffer device (default
`/dev/fb0`). Use `--fb` to select another device, such as the Pi's second
framebuffer, when layering over another video source.

### Usage

```bash
sudo ./randomfb.py --width 640 --height 480 \
                   --opacity 0.5 --colormap hsv --fps 30
```

Available colormaps: `gray`, `hsv`, `hot`.

To modulate the noise with hardware input, provide a numeric file path using
`--input-path`. The value read is scaled between `--min-value` and
`--max-value` before affecting brightness.

Example using the CPU temperature sensor:

```bash
sudo ./randomfb.py --input-path /sys/class/thermal/thermal_zone0/temp \
                   --min-value 30000 --max-value 80000
```

Specify `--seed` with an integer to reproduce the same random pattern across
runs.