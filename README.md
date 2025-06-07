diff --git a/README.md b/README.md
index 50d804aa298848d45cda7f3532aee2ccbccfaaa4..5b2308a4d1f250cdcf3e25f8a71e7d4d60fba6ca 100644
--- a/README.md
+++ b/README.md
@@ -1,2 +1,35 @@
 # v1dp1
-video raspberry pi
+
+Utilities for experimenting with video on the Raspberry Pi.
+
+## Random Framebuffer Overlay
+
+`randomfb.py` generates a noisy overlay on a framebuffer device (default
+`/dev/fb0`). Use `--fb` to select another device, such as the Pi's second
+framebuffer, when layering over another video source.
+
+### Usage
+
+The script automatically uses the framebuffer's current resolution so the
+overlay covers the full screen. Specify `--width` and `--height` only if you
+need a custom size.
+
+```bash
+sudo ./randomfb.py --opacity 0.5 --colormap hsv --fps 30
+```
+
+Available colormaps: `gray`, `hsv`, `hot`.
+
+To modulate the noise with hardware input, provide a numeric file path using
+`--input-path`. The value read is scaled between `--min-value` and
+`--max-value` before affecting brightness.
+
+Example using the CPU temperature sensor:
+
+```bash
+sudo ./randomfb.py --input-path /sys/class/thermal/thermal_zone0/temp \
+                   --min-value 30000 --max-value 80000
+```
+
+Specify `--seed` with an integer to reproduce the same random pattern across
+runs.
