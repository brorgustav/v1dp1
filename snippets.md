source /home/bgw/v1dp1/bgwxv1dp1/bin/activate

wget 

python3 /home/bgw/v1dp1/randomfb.py


### Usage

```bash
sudo ./randomfb.py --fb /dev/fb1 --width 640 --height 480 \
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