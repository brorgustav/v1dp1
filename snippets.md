

sudo rm /home/bgw/v1dp1_rand.py
touch /home/bgw/v1dp1_rand.py
sudo chmod a+x /home/bgw/v1dp1_rand.py
sudo nano /home/bgw/v1dp1_rand.py
python3 /home/bgw/v1dp1_rand.py



source /home/bgw/bgwxv1dp1/bin/activate

sudo rm v1dp1_rand.py
touch v1dp1_rand.py
sudo chmod a+x v1dp1_rand.py
sudo echo " " > v1dp1_rand.py
python3 v1dp1_rand.py



##sudo rm -r /home/bgw/v1dp1
##git clone https://github.com/brorgustav/v1dp1
##python3 /home/bgw/v1dp1/randomfb.py

(cmdline) video=HDMI-A-1:640x480@60:e

export PYTHONPATH="/home/bgw/bgwxv1dp1"


If you want to change the PYTHONPATH used in a virtualenv, you can add the following line to your virtualenv's bin/activate file:

export PYTHONPATH="/the/path/you/want"

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