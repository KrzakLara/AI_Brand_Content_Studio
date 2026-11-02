"""Shared helpers for the Post 3 reel (local, deterministic)."""
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 24


def read_frames(path, w=W, h=H):
    """All frames of a video as uint8 arrays (n,h,w,3), resampled to 24 fps and scaled to w x h."""
    p = subprocess.run([FF, "-loglevel", "error", "-i", str(path), "-vf", f"fps={FPS},scale={w}:{h}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w, 3)
