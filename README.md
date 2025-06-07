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

Make sure the `--width` and `--height` match your framebuffer's
resolution. If they are smaller than the actual display, the overlay will
only cover part of the screen. You can check the current resolution with
`fbset -s` and pass the values to `randomfb.py` for a full-screen effect.

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
