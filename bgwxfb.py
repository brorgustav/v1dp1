#!/usr/bin/env python3

# Top-level debug print to confirm script is executed
print("🔍 bgwxfb script loaded", flush=True)

import sounddevice as sd
import numpy as np
import time
import mmap
import argparse
import sys
import os
import signal
import configparser

# Determine directory where the script resides
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# Standard Linux INI config paths, plus script directory
CONFIG_PATHS = [
    '/etc/bgwxfb.conf',
    os.path.expanduser('~/.config/bgwxfb.conf'),
    os.path.join(SCRIPT_DIR, 'bgwxfb.conf')
]

class Bgwxfb:
    def __init__(self):
        print("💡 Entered Bgwxfb.__init__", flush=True)
        # Default b/w mode flag
        self.use_black_and_white = False

        # === CLI args ===
        parser = argparse.ArgumentParser(
            description="bgwxfb - framebuffer audio visual blending"
        )
        parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
        parser.add_argument("-f", "--freq", action="store_true", help="Use frequency mode instead of amplitude")
        parser.add_argument("-b", "--blend", action="store_true", help="Enable blending mode")
        parser.add_argument("-m", "--mixed", action="store_true", help="Use pixelwise mixed write mode")
        parser.add_argument("-r", "--ratio", type=float, help="Blend ratio (0.0 to 1.0)")
        parser.add_argument("-p", "--partial", action="store_true", help="Enable partial framebuffer updates")
        parser.add_argument("-o", "--offset", type=float, help="Amplitude offset (-1.0 to 1.0)")
        parser.add_argument("-i", "--input-device", type=int, help="Audio input device index")
        parser.add_argument("--blocksize", type=int, help="Audio block size")
        parser.add_argument("--random", action="store_true", help="Enable random pixel mapping")
        parser.add_argument("--reshuffle", action="store_true", help="Re‐shuffle random map each frame")
        parser.add_argument("--fb", type=int, choices=[0, 1], help="Framebuffer number (0 or 1)")
        parser.add_argument("-c", "--config", type=str, help="Path to INI config file")
        args = parser.parse_args()

        # === Defaults for INI fallback ===
        defaults = {
            'debug': 'false',
            'use_frequency_mode': 'false',
            'use_blend_mode': 'false',
            'use_mixed_raw': 'false',
            'blend_ratio': '0.5',
            'use_partial_update': 'false',
            'amplitude_offset': '0.0',
            'input_device': '0',
            'blocksize': '512',
            'use_random': 'false',
            'reshuffle': 'false',
            'fb': '0'
        }

        # === Load INI config, seed defaults ===
        config = configparser.ConfigParser()
        config.read_dict({'settings': defaults})
        # determine config paths to read
        config_paths = [args.config] if args.config else CONFIG_PATHS
        if args.debug and args.config:
            print(f"🔧 Loading config from: {args.config}", flush=True)
        read_files = config.read(config_paths)
        if args.debug:
            print(f"🔧 Attempted config paths: {config_paths}")
            print(f"🔧 Files actually loaded: {read_files}")
        if args.debug and not read_files:
            print(f"⚠️ No config loaded, using built-in defaults", flush=True)
        s = config['settings']

        # === Merge settings (CLI overrides INI) ===
        self.debug = args.debug or s.getboolean('debug')
        self.use_frequency_mode = args.freq or s.getboolean('use_frequency_mode')
        self.use_blend_mode = args.blend or s.getboolean('use_blend_mode')
        self.use_mixed_raw = args.mixed or s.getboolean('use_mixed_raw')
        self.use_random_map = args.random or s.getboolean('use_random')
        self.reshuffle_each_frame = args.reshuffle or s.getboolean('reshuffle')

        ini_ratio = s.getfloat('blend_ratio')
        self.blend_ratio = args.ratio if args.ratio is not None else ini_ratio
        self.blend_ratio = max(0.0, min(1.0, self.blend_ratio))

        self.use_partial_update = args.partial or s.getboolean('use_partial_update')

        ini_offset = s.getfloat('amplitude_offset')
        self.amplitude_offset = args.offset if args.offset is not None else ini_offset
        self.amplitude_offset = max(-1.0, min(1.0, self.amplitude_offset))

        ini_dev = s.getint('input_device')
        self.input_device = args.input_device if args.input_device is not None else ini_dev

        ini_block = s.getint('blocksize')
        self.blocksize = args.blocksize if args.blocksize is not None else ini_block
        # framebuffer number
        ini_fb = s.getint('fb')
        fb_num = args.fb if args.fb is not None else ini_fb
        self.fb_device = f"/dev/fb{fb_num}"
        # framebuffer number and device path
        ini_fb = s.getint('fb')
        fb_num = args.fb if args.fb is not None else ini_fb
        self.fb_device = f"/dev/fb{fb_num}"

        if self.debug:
            print(f"Config files read: {read_files}", flush=True)
            print(
                f"Settings: debug={self.debug}, freq={self.use_frequency_mode}, blend={self.use_blend_mode}, mixed={self.use_mixed_raw}, \
                ratio={self.blend_ratio}, partial={self.use_partial_update}, offset={self.amplitude_offset}, \
                input_device={self.input_device}, blocksize={self.blocksize}, random={self.use_random_map}, reshuffle={self.reshuffle_each_frame}",
                flush=True
            )

        # === Audio setup ===
        try:
            device_info = sd.query_devices(self.input_device)
            self.samplerate = int(device_info['default_samplerate'])
        except Exception as e:
            print("❌ Failed to query audio device:", e, flush=True)
            sys.exit(1)
        if self.debug:
            print(f"🎧 Audio Device: {device_info['name']}", flush=True)
            print(f"    Sample rate: {device_info['default_samplerate']} Hz", flush=True)
            print(f"    Max channels: {device_info['max_input_channels']}", flush=True)

        # === Framebuffer setup ===
        try:
            with open("/sys/class/graphics/fb0/virtual_size") as f:
                self.width, self.height = map(int, f.read().split(","))
            with open("/sys/class/graphics/fb0/bits_per_pixel") as f:
                bpp = int(f.read().strip())
            # fb_path is derived from fb_device
            fb_path = self.fb_device
            self.fb_size = self.width * self.height * (bpp // 8)
            self.interp_x = np.linspace(0, self.blocksize//2+1, self.width*self.height, endpoint=False)
            self.fb_fd = open(fb_path, "r+b")
            self.fb_mmap = mmap.mmap(self.fb_fd.fileno(), self.fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE|mmap.PROT_READ)
            self.fb_array = np.ndarray((self.height, self.width), dtype=np.uint16, buffer=self.fb_mmap)
            self.prev_frame = np.zeros_like(self.fb_array)
        except Exception as e:
            print("❌ Framebuffer setup failed:", e, flush=True)
            sys.exit(1)

        # === Random mapping setup ===
        n_pixels = self.width * self.height
        self.random_map = np.random.permutation(n_pixels)

        # === HSV→RGB565 LUT ===
        self.hue_lut = np.array([self._hsv_to_rgb565_base(i/360.0) for i in range(360)], dtype=np.uint16)

        # Frame stats
        self.frame_count = 0
        self.fps_last_time = time.perf_counter()

    def _hsv_to_rgb565_base(self, h):
        i = int(h*6) % 6
        f = (h*6) - int(h*6)
        p, q, t = 0, 1-f, f
        if i==0: r,g,b=1,t,p
        elif i==1: r,g,b=q,1,p
        elif i==2: r,g,b=p,1,t
        elif i==3: r,g,b=p,q,1
        elif i==4: r,g,b=t,p,1
        else:    r,g,b=1,p,q
        return ((int(r*31)&0x1F)<<11)|((int(g*63)&0x3F)<<5)|(int(b*31)&0x1F)

    def float_to_rgb565(self,h,v):
        if self.use_black_and_white:
            gray=int(v*31)&0x1F
            return (gray<<11)|((gray<<1)<<5)|gray
        base=self.hue_lut[int((h%1.0)*360)]
        r5=(base>>11)&0x1F; g6=(base>>5)&0x3F; b5=base&0x1F
        return ((int(r5*v)&0x1F)<<11)|((int(g6*v)&0x3F)<<5)|(int(b5*v)&0x1F)

    def write_pixelwise_mixed(self,interp):
        flat=interp[:self.width*self.height]
        idx=np.arange(flat.size)
        mixed=np.zeros_like(flat)
        even=idx%2==0
        x_e=idx[even]//self.height; y_e=idx[even]%self.height
        mixed[y_e*self.width+x_e]=flat[even]
        odd=~even
        y_o=idx[odd]//self.width; x_o=idx[odd]%self.width
        mixed[y_o*self.width+x_o]=flat[odd]
        return mixed.reshape((self.height,self.width))

    def write_blended(self,interp):
        raw=interp[:self.width*self.height].reshape((self.height,self.width))
        mixed=self.write_pixelwise_mixed(interp)
        if self.blend_ratio<=0: return raw
        if self.blend_ratio>=1: return mixed
        raw_r=(raw>>11)&0x1F; raw_g=(raw>>5)&0x3F; raw_b=raw&0x1F
        mix_r=(mixed>>11)&0x1F; mix_g=(mixed>>5)&0x3F; mix_b=mixed&0x1F
        br=(raw_r*self._blend_inv+mix_r*self._blend_coef)>>8
        bg=(raw_g*self._blend_inv+mix_g*self._blend_coef)>>8
        bb=(raw_b*self._blend_inv+mix_b*self._blend_coef)>>8
        blended=((br&0x1F)<<11)|((bg&0x3F)<<5)|(bb&0x1F)
        if self.use_black_and_white:
            gray5=((blended*31)//65535)&0x1F; gray6=((blended*63)//65535)&0x3F
            blended=(gray5<<11)|(gray6<<5)|gray5
        return blended

    def audio_callback(self,indata,frames,time_info,status):
        t0=time.perf_counter()
        buf=indata[:,0]
        if self.use_frequency_mode:
            fft = np.fft.rfft(buf)
            amp = np.abs(fft)
            maxv = amp.max() or 1.0
            amp = amp / maxv
        else:
            amp=np.clip(np.abs(buf)+self.amplitude_offset,0,1)
        t1=time.perf_counter()
        rgb=np.array([self.float_to_rgb565(i/len(amp),amp[i]) for i in range(len(amp))],dtype=np.uint16)
        t2=time.perf_counter()
        interp=np.interp(self.interp_x,np.arange(len(rgb)),rgb).astype(np.uint16)
        t3=time.perf_counter()
        n_pixels=self.width*self.height
        if self.use_random_map:
            flat=interp[:n_pixels]
            if self.reshuffle_each_frame:
                self.random_map=np.random.permutation(n_pixels)
            frame=flat[self.random_map].reshape((self.height,self.width))
        elif self.use_blend_mode:
            frame=self.write_blended(interp)
        elif self.use_mixed_raw:
            frame=self.write_pixelwise_mixed(interp)
        else:
            frame=interp[:n_pixels].reshape((self.height,self.width))
        if self.use_partial_update:
            self.prev_frame_update(frame)
        else:
            np.copyto(self.fb_array,frame)
        t4=time.perf_counter()
        if self.debug and t4-self.fps_last_time>=1:
            fps=self.frame_count; self.frame_count=0; self.fps_last_time=t4
            print(f"FPS:{fps}|a:{(t1-t0)*1e3:.1f}ms rgb:{(t2-t1)*1e3:.1f}ms int:{(t3-t2)*1e3:.1f}ms wr:{(t4-t3)*1e3:.1f}ms tot:{(t4-t0)*1e3:.1f}ms",flush=True)
        self.frame_count+=1

    def prev_frame_update(self,new_frame):
        diff=new_frame!=self.prev_frame
        if not diff.any():return
        rows=np.any(diff,axis=1);cols=np.any(diff,axis=0)
        r0,r1=np.where(rows)[0][[0,-1]];c0,c1=np.where(cols)[0][[0,-1]]
        self.fb_array[r0:r1+1,c0:c1+1]=new_frame[r0:r1+1,c0:c1+1]
        self.prev_frame[:,:]=new_frame

    def run(self):
        self.fb_array[:,:]=0
        with sd.InputStream(device=(self.input_device,None),callback=self.audio_callback,channels=1,samplerate=self.samplerate,blocksize=self.blocksize,dtype='float32'):
            if self.debug:print("✅ Audio stream running",flush=True)
            signal.pause()

if __name__=='__main__':
    print("💥 About to instantiate Bgwxfb",flush=True)
    viz=Bgwxfb()
    print("🚀 Instantiated Bgwxfb",flush=True)
    try:viz.run()
    except Exception as e:
        print("❌ Unhandled Exception:",e,flush=True)
        viz.fb_array[:,:]=0;viz.fb_mmap.close();viz.fb_fd.close();sys.exit(1)
