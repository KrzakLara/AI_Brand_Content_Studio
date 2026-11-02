"""Procedural foley + music bed for the Post 3 reel (numpy only, deterministic, seed-fixed).
All sounds are synthesized here = our own work: no third-party audio, no licence dependency.
"""
import wave

import numpy as np

SR = 44100
RNG = np.random.default_rng(20261029)


def _t(d):
    return np.arange(int(d * SR)) / SR


def _bp(x, lo, hi):
    """Crude FFT band-pass (zero-phase)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def _env(n, attack=0.002, decay=0.05):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-5)) * np.exp(-t / decay)


def noise(d):
    return RNG.standard_normal(int(d * SR))


def zipper(d=1.0):
    """Ratchet of tiny metallic ticks, constant pace, with a soft tail."""
    n = int(d * SR); out = np.zeros(n)
    for k in np.arange(0.0, d - 0.05, 1 / 52):
        i = int(k * SR); tick = _bp(noise(0.012), 2500, 9000) * _env(int(0.012 * SR), 0.0005, 0.003)
        out[i:i + len(tick)] += tick * (0.6 + 0.4 * RNG.random())
    return out / np.abs(out).max() * 0.55


def rustle(d=1.2, density=140, lo=1800, hi=9000):
    """Crinkly wrapper/paper: random sparse crackles inside a slowly moving envelope."""
    n = int(d * SR); out = np.zeros(n)
    amp = np.abs(np.convolve(noise(d), np.ones(int(0.06 * SR)) / (0.06 * SR), "same")); amp /= amp.max()
    for _ in range(int(density * d)):
        i = int(RNG.random() * (n - 800)); L = int(RNG.uniform(0.001, 0.006) * SR)
        c = _bp(noise(L / SR + 0.002), lo, hi)[:L] * _env(L, 0.0003, 0.002)
        out[i:i + L] += c * amp[i] * RNG.uniform(0.3, 1.0)
    fade = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (0.08 * SR))
    return out / np.abs(out).max() * 0.6 * fade


def door_thunk():
    """Closed car door heard from outside/inside: low thump + latch click."""
    t = _t(0.5); f = 90 * np.exp(-t * 7) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    thud = _bp(noise(0.5), 60, 400) * np.exp(-t * 14)
    click = np.zeros_like(t); L = int(0.02 * SR)
    click[int(0.07 * SR):int(0.07 * SR) + L] = _bp(noise(0.02), 1500, 6000)[:L] * _env(L, 0.0004, 0.004)
    return (body * 0.9 + thud * 0.7 + click * 0.35) / 1.3


def footsteps(times, d, soft=1.0):
    out = np.zeros(int(d * SR))
    for ts in times:
        i = int(ts * SR); L = int(0.14 * SR)
        s = _bp(noise(0.14), 90, 900)[:L] * _env(L, 0.003, 0.04) * 0.5 * soft
        s += _bp(noise(0.14), 1500, 5000)[:L] * _env(L, 0.001, 0.012) * 0.12 * soft
        out[i:i + L] += s[: len(out) - i] if i + L > len(out) else s
    return out


def crunch():
    """Hero wafer snap: a sharp crack, several layered crisp fractures, then fine crumbs."""
    d = 0.9; n = int(d * SR); out = np.zeros(n)
    # primary crack
    L = int(0.05 * SR); out[:L] += _bp(noise(0.05), 800, 8000)[:L] * _env(L, 0.0003, 0.012) * 1.0
    out[:L] += _bp(noise(0.05), 90, 300)[:L] * _env(L, 0.001, 0.02) * 0.6
    # layered fractures (3 wafer layers + chocolate shell)
    for off, g in ((0.03, 0.8), (0.06, 0.7), (0.095, 0.6), (0.14, 0.5), (0.19, 0.4), (0.25, 0.3)):
        i = int(off * SR); L = int(RNG.uniform(0.012, 0.03) * SR)
        out[i:i + L] += _bp(noise(0.04), 1200, 7500)[:L] * _env(L, 0.0004, 0.006) * g
    # crumbs
    for _ in range(26):
        i = int(RNG.uniform(0.18, 0.85) * SR); L = int(0.004 * SR)
        out[i:i + L] += _bp(noise(0.01), 2500, 9000)[:L] * _env(L, 0.0002, 0.0012) * RNG.uniform(0.05, 0.25)
    return out / np.abs(out).max() * 0.95


def whoosh(d=0.6):
    t = _t(d); n = len(t); x = _bp(noise(d), 300, 3500)
    return x * np.sin(np.pi * t / d) ** 2 * 0.5 / np.abs(x).max()


def glass_door_push():
    t = _t(0.7); low = _bp(noise(0.7), 40, 220) * np.sin(np.pi * t / 0.7) * 0.8
    metal = np.zeros_like(t); L = int(0.03 * SR)
    metal[int(0.05 * SR):int(0.05 * SR) + L] = _bp(noise(0.03), 900, 4500)[:L] * _env(L, 0.0004, 0.01)
    air = _bp(noise(0.7), 800, 2500) * np.sin(np.pi * t / 0.7) ** 2 * 0.25
    return (low / np.abs(low).max() * 0.5 + metal * 0.6 + air / (np.abs(air).max() + 1e-9) * 0.25)


def keys_jingle():
    out = np.zeros(int(0.9 * SR))
    for off in (0.0, 0.07, 0.13, 0.22, 0.31):
        t = _t(0.5); f = RNG.choice([3100, 3900, 4700, 5600])
        s = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.4 * t)) * np.exp(-t * 14)
        i = int(off * SR); out[i:i + len(s)] += s[: len(out) - i] * 0.18
    return out


def music_bed(d, bpm=92):
    """Soft warm bed: slow pad chords + very quiet pluck pattern (our own generated music, not a library track)."""
    n = int(d * SR); t = np.arange(n) / SR
    chords = [(261.63, 329.63, 392.0, 493.88), (220.0, 261.63, 329.63, 392.0), (174.61, 220.0, 261.63, 329.63), (196.0, 246.94, 293.66, 392.0)]
    beat = 60 / bpm; bar = 4 * beat; pad = np.zeros(n)
    for b in range(int(d / bar) + 1):
        i0 = int(b * bar * SR); i1 = min(n, int((b + 1) * bar * SR) + int(0.4 * SR)); tt = np.arange(i1 - i0) / SR
        env = np.minimum(1, tt / 0.6) * np.minimum(1, (bar + 0.4 - tt) / 0.6).clip(0)
        for f in chords[b % 4]:
            pad[i0:i1] += (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt) + 0.12 * np.sin(2 * np.pi * 3 * f * tt)) * env * 0.05
    pl = np.zeros(n)
    for s in range(int(d / (beat / 2))):
        i = int(s * beat / 2 * SR); ch = chords[(s // 8) % 4]; f = ch[[0, 2, 1, 3, 2, 1, 3, 2][s % 8]] * 2
        tt = np.arange(int(0.5 * SR)) / SR; note = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 7) * 0.035
        pl[i:i + len(note)] += note[: n - i]
    bed = pad + pl
    fade = np.minimum(1, t / 1.2) * np.minimum(1, (d - t) / 1.8)
    return bed * fade


def place(mix, x, at, gain=1.0, pan=None):
    i = int(at * SR)
    if i >= len(mix):
        return
    seg = x[: len(mix) - i]
    mix[i:i + len(seg)] += seg * gain


def to_wav(path, mono, peak=0.89):
    m = mono / (np.abs(mono).max() + 1e-9) * peak
    pcm = (np.clip(m, -1, 1) * 32767).astype("<i2")
    stereo = np.stack([pcm, pcm], 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(stereo.tobytes())
