"""Helper of REPRODUCE_SVE_TRI_OBJAVE_7F.ps1 (Phase 7G). Local and free: no network, no API key, no paid model call.

Run it with the WORKSPACE interpreter (.venv\\Scripts\\python.exe: needs numpy, Pillow, OpenCV, imageio-ffmpeg from the ".[dev,media]" install).
Every sub-command appends one JSON record to <out>\\_work\\checks.jsonl and exits 0 (check passed) or 1 (check failed).

  copy         copy a stored, human-approved final file out of the package; its SHA-256 must equal SHA256SUMS.txt
  compare      generated file vs the packaged final: SHA-256 first; if the bytes differ, decoded pixels / decoded frames / decoded audio
  cover-b      rebuild cover B with the shipped script cover_wrapper_fix.py (output redirected to <out>\\_work)
  reel-v8      re-assemble the whole Reel FINAL V8 (video + synthesised foley audio) with the shipped assemble_reel_v8_candidate.py in a fresh interpreter
  audio        extract the Reel audio track of a given mp4 to .m4a (stream copy) and .wav
  contact      six-panel carousel overview, same code and layout as final_contact_sheet_v4.py but reading the six slides produced in <out>
  media        technical check of one produced file (size, fps, frame count, duration, audio stream, not silent)
  summary      write REPRODUCE_REPORT.json / .txt and exit non-zero if any check failed
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

SUB = Path(__file__).resolve().parents[1]                      # the extracted package ("submission" folder)
REEL_DIR = "plans/gymbeam_hr/phase6/reel"


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sums() -> dict:
    d = {}
    for line in (SUB / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if "  " in line:
            h, rel = line.split("  ", 1); d[rel] = h
    return d


def record(out: Path, **kw) -> int:
    w = out / "_work"; w.mkdir(parents=True, exist_ok=True)
    kw["ok"] = bool(kw["ok"])
    kw["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(w / "checks.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(kw, ensure_ascii=False) + "\n")
    print(("PASS  " if kw["ok"] else "FAIL  ") + kw["name"] + "  --  " + kw["detail"])
    return 0 if kw["ok"] else 1


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def read_frames(ws: Path, path, w, h):
    sys.path.insert(0, str(ws / REEL_DIR))
    from reel_lib import read_frames as rf
    return rf(path, w, h)


def info(path) -> dict:
    """Parse ffmpeg's stream banner (there is no ffprobe in the package): size, fps, duration, codecs."""
    err = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    import re
    r = {"video": None, "audio": None, "duration": None, "fps": None, "size": None}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if m: r["duration"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    for line in err.splitlines():
        if "Video:" in line and r["video"] is None:
            r["video"] = line.strip()
            s = re.search(r"(\d{3,4})x(\d{3,4})", line.split("Video:")[1]); r["size"] = f"{s[1]}x{s[2]}" if s else None
            f = re.search(r"([\d.]+) fps", line); r["fps"] = float(f[1]) if f else None
        if "Audio:" in line and r["audio"] is None:
            r["audio"] = line.strip()
    return r


def ffmpeg_name() -> str:
    return os.path.basename(ffmpeg())


def pinned_ffmpeg() -> bool:
    return "7.1" in ffmpeg_name()          # imageio-ffmpeg 0.7.0 ships ffmpeg-win-x86_64-v7.1.exe (the build of the delivered files)


def audio_snr(a, b) -> float:
    def pcm(p):
        return np.frombuffer(subprocess.run([ffmpeg(), "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "-"], capture_output=True, check=True).stdout, np.int16).astype(np.float64)
    x, y = pcm(a), pcm(b)
    best = -200.0
    for lag in range(-2400, 2401, 16):                                      # encoders may add a different priming delay
        u, v = (x[lag:], y[:len(y) - lag]) if lag >= 0 else (x[:lag], y[-lag:])
        n = min(len(u), len(v))
        if n < 48000: continue
        d = np.sum((u[:n] - v[:n]) ** 2)
        best = max(best, 10 * np.log10(np.sum(v[:n] ** 2) / max(d, 1e-9)))
    return best


def pcm_hash(path) -> tuple[str, float, int]:
    """Decoded audio (mono, 48 kHz, signed 16 bit) -> (sha256, RMS in dBFS, samples)."""
    raw = subprocess.run([ffmpeg(), "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float64) / 32768.0
    rms = float(np.sqrt(np.mean(a ** 2))) if len(a) else 0.0
    return hashlib.sha256(raw).hexdigest(), (20 * np.log10(rms) if rms > 0 else -200.0), len(a)


# ---------------------------------------------------------------------------------------------------------------------
def cmd_copy(a):
    src = SUB / a.rel; dst = Path(a.dst)
    if not src.is_file():
        return record(a.out, name=a.name, ok=False, detail=f"missing in package: {a.rel}", kind="copy")
    want = sums().get(a.rel)
    got = sha(src)
    if want != got:
        return record(a.out, name=a.name, ok=False, detail=f"{a.rel}: SHA-256 {got[:12]} differs from SHA256SUMS.txt {str(want)[:12]}", kind="copy")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return record(a.out, name=a.name, ok=False, detail=f"refusing to overwrite {dst}", kind="copy")
    shutil.copyfile(src, dst)
    ok = sha(dst) == got
    return record(a.out, name=a.name, ok=ok, detail=f"STORED approved final copied from package ({a.rel}); sha256 {got[:16]}... verified against SHA256SUMS.txt; this is a copy, not a regeneration", kind="copy", file=str(dst), sha256=got)


def compare_files(gen: Path, ref: Path, ws: Path, kind: str) -> tuple[bool, str, str]:
    """Returns (ok, level, detail). level: sha256 | pixels | frames | audio+frames."""
    if not gen.is_file():
        return False, "missing", f"generated file missing: {gen}"
    if not ref.is_file():
        return False, "missing", f"reference file missing: {ref}"
    hg, hr = sha(gen), sha(ref)
    if hg == hr:
        return True, "sha256", f"SHA-256 identical ({hg[:16]}...)"
    if kind == "png":
        from PIL import Image
        A = np.asarray(Image.open(gen).convert("RGBA")); B = np.asarray(Image.open(ref).convert("RGBA"))
        same = A.shape == B.shape and np.array_equal(A, B)
        return same, "pixels", "bytes differ but every decoded pixel is identical (PNG container only)" if same else f"PIXELS DIFFER ({A.shape} vs {B.shape})"
    w, h = (int(x) for x in kind.split(":")[1].split("x"))
    Fg, Fr = read_frames(ws, gen, w, h), read_frames(ws, ref, w, h)
    fm = len(Fg) == len(Fr) and hashlib.md5(Fg.tobytes()).hexdigest() == hashlib.md5(Fr.tobytes()).hexdigest()
    if not fm:
        return False, "frames", f"DECODED FRAMES DIFFER ({len(Fg)} vs {len(Fr)} frames)"
    if kind.startswith("reel"):
        ag, ar = pcm_hash(gen), pcm_hash(ref)
        if ag[0] == ar[0]:
            return True, "audio+frames", f"bytes differ; {len(Fg)} decoded frames identical; decoded audio identical"
        if pinned_ffmpeg():
            return False, "audio+frames", "decoded audio DIFFERS although the pinned ffmpeg 7.1 is in use"
        snr = audio_snr(gen, ref)
        ok = snr >= 18.0
        return ok, "frames+audio_snr", (f"NOT the pinned ffmpeg 7.1 ({ffmpeg_name()}): {len(Fg)} decoded frames identical; the AAC re-encode differs by encoder build only, audio SNR vs delivered {snr:.1f} dB "
                                          f"({'same waveform' if ok else 'TOO LOW'}). Install with -c constraints-media-7G.txt for byte-identical output")
    return True, "frames", f"bytes differ but all {len(Fg)} decoded frames are identical"


def cmd_compare(a):
    ref = SUB / a.ref
    ok, level, detail = compare_files(Path(a.gen), ref, a.ws, a.kind)
    return record(a.out, name=a.name, ok=ok, detail=f"{detail} -- vs package {a.ref}", kind="compare", level=level, file=str(a.gen))


def cmd_cover(a):
    ws = a.ws; work = a.out / "_work" / "cover_b"; work.mkdir(parents=True, exist_ok=True)
    script = ws / REEL_DIR / "cover_wrapper_fix.py"
    src = script.read_text(encoding="utf-8").replace('OUT = R / "cover_options"', f'OUT = Path(r"{work}")')
    if str(work) not in src:
        return record(a.out, name=a.name, ok=False, detail="cover_wrapper_fix.py no longer contains the expected OUT line", kind="rebuild")
    g = {"__file__": str(script), "__name__": "__main__"}
    exec(compile(src, "cover_wrapper_fix.py", "exec"), g)
    built = work / "COVER_B_corrected_wrapper_1080x1920.png"
    dst = Path(a.dst); dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(built, dst)
    ok, level, detail = compare_files(dst, SUB / a.ref, ws, "png")
    return record(a.out, name=a.name, ok=ok, detail=f"REBUILT locally by cover_wrapper_fix.py from the archived cover and S01 still: {detail}", kind="rebuild", level=level, file=str(dst))


def cmd_reel(a):
    ws = a.ws.resolve(); work = (a.out / "_work" / "reel_v8").resolve(); (work / "logs").mkdir(parents=True, exist_ok=True); (work / "audio").mkdir(exist_ok=True)
    code = ("import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
            "from pathlib import Path\nimport assemble_reel as A\nA.FIN = A.AUD = A.R = Path(%r)\n"
            "import importlib; importlib.import_module('assemble_reel_v8_candidate').main()\n") % (str(ws), str(ws / REEL_DIR), str(work))
    t = time.time()
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ws)
    print(r.stdout.strip())
    cand = work / "GYMBEAM_WAFER_LIFESTYLE_REEL_V8_CANDIDATE.mp4"
    if r.returncode != 0 or not cand.is_file():
        print(r.stderr[-1500:])
        return record(a.out, name=a.name, ok=False, detail="assemble_reel_v8_candidate.py failed: " + (r.stderr.strip().splitlines() or ["no output"])[-1][:200], kind="rebuild")
    dst = Path(a.dst); dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cand, dst)                                            # the delivered FINAL V8 is the V8 candidate, byte for byte
    wav_src = work / "audio" / "V8_candidate_foley_only_mix.wav"
    wav_dst = Path(a.wav); wav_dst.parent.mkdir(parents=True, exist_ok=True)
    if wav_src.is_file():
        shutil.copyfile(wav_src, wav_dst)
    ok, level, detail = compare_files(dst, SUB / a.ref, ws, "reel:1080x1920")
    return record(a.out, name=a.name, ok=ok, detail=f"REASSEMBLED from the 4 archived Kling clips (S02, S03B, S06, S08) + S01 still with synthesised foley, {time.time() - t:.0f} s: {detail}", kind="rebuild", level=level, file=str(dst))


def cmd_audio(a):
    src, m4a, wav = Path(a.mp4), Path(a.m4a), Path(a.wav)
    m4a.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vn", "-c:a", "copy", str(m4a)], check=True)
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(wav)], check=True)
    h, db, n = pcm_hash(m4a); ref_h, _, _ = pcm_hash(SUB / "posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4")
    same = h == ref_h
    snr = None if same or pinned_ffmpeg() else audio_snr(m4a, SUB / "posts/post_03_gymbeam_wafer_reel/GYMBEAM_WAFER_LIFESTYLE_REEL_FINAL_V8.mp4")
    ok = (same or (snr is not None and snr >= 18.0)) and db > -60 and n > 8 * 48000
    return record(a.out, name=a.name, ok=ok, detail=f"audio track of the re-assembled Reel extracted (stream copy, AAC .m4a + 48 kHz .wav); decoded audio {'identical to' if same else ('same waveform as (SNR %.1f dB, other ffmpeg build)' % snr if ok else 'DIFFERENT from')} the packaged FINAL V8; level {db:.1f} dBFS RMS; {n / 48000:.2f} s", kind="audio", file=str(m4a))


def cmd_contact(a):
    from PIL import Image
    D = Path(a.dir); work = a.out / "_work"; work.mkdir(parents=True, exist_ok=True)
    names = sorted(p.name for p in D.glob("slide_*"))
    if len(names) != 6:
        return record(a.out, name=a.name, ok=False, detail=f"expected 6 slide files, found {names}", kind="rebuild")
    src = []
    for n in names:
        p = D / n
        if p.suffix == ".mp4":
            f0 = work / (p.stem + "_FIRST_FRAME.png")
            subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(p), "-frames:v", "1", "-update", "1", str(f0)], check=True); src.append(f0)
        else:
            src.append(p)
    PW, PH, GAP = 768, 960, 24                                            # identical to final_contact_sheet_v4.py
    sheet = Image.new("RGB", (6 * PW + 7 * GAP, PH + 2 * GAP), (24, 20, 22))
    for i, p in enumerate(src):
        im = Image.open(p).convert("RGB"); assert im.size == (1080, 1350), (p, im.size)
        sheet.paste(im.resize((PW, PH), Image.LANCZOS), (GAP + i * (PW + GAP), GAP))
    dst = Path(a.dst); dst.parent.mkdir(parents=True, exist_ok=True); sheet.save(dst)
    ok, level, detail = compare_files(dst, SUB / a.ref, a.ws, "png")
    return record(a.out, name=a.name, ok=ok, detail=f"REBUILT from the six slides produced in this run (same code as final_contact_sheet_v4.py): {detail}", kind="rebuild", level=level, file=str(dst))


def cmd_media(a):
    p = Path(a.file); probs = []; det = ""
    if not p.is_file() or p.stat().st_size < 1000:
        return record(a.out, name=a.name, ok=False, detail=f"missing or empty: {p}", kind="media")
    if p.suffix.lower() == ".png":
        from PIL import Image
        im = Image.open(p); arr = np.asarray(im.convert("RGB"))
        if f"{im.size[0]}x{im.size[1]}" != a.size: probs.append(f"size {im.size}")
        if arr.std() < 20 or len(np.unique(arr.reshape(-1, 3), axis=0)) < 5000: probs.append("looks like a flat/placeholder image")
        det = f"PNG {im.size[0]}x{im.size[1]}, {len(np.unique(arr.reshape(-1, 3), axis=0))} distinct colours, std {arr.std():.0f} (a mock placeholder is one flat colour)"
    else:
        i = info(p)
        if i["size"] != a.size: probs.append(f"size {i['size']}")
        if i["fps"] != 24: probs.append(f"fps {i['fps']}")
        if a.duration and abs((i["duration"] or 0) - a.duration) > 0.06: probs.append(f"duration {i['duration']}")
        if "h264" not in (i["video"] or ""): probs.append("not H.264")
        fr = read_frames(a.ws, p, *(int(x) for x in a.size.split("x")))
        if a.frames and len(fr) != a.frames: probs.append(f"{len(fr)} frames, expected {a.frames}")
        mv = float(np.abs(np.diff(fr[::6].astype(np.int16), axis=0)).mean())
        if mv < 0.05: probs.append("frames do not change (static)")
        det = f"{i['size']} {i['fps']} fps H.264, {len(fr)} decoded frames, {i['duration']:.2f} s, mean inter-frame change {mv:.2f}"
        if a.audio:
            if not i["audio"]: probs.append("NO AUDIO STREAM")
            else:
                _, db, n = pcm_hash(p)
                if db < -60: probs.append(f"audio silent ({db:.0f} dBFS)")
                det += f"; audio: {i['audio'].split('Audio:')[1].split(',')[0].strip()} {n / 48000:.2f} s at {db:.1f} dBFS RMS"
        elif i["audio"]:
            probs.append("unexpected audio stream")
    return record(a.out, name=a.name, ok=not probs, detail=det + ("" if not probs else "  PROBLEMS: " + "; ".join(probs)), kind="media", file=str(p))


def cmd_summary(a):
    out = a.out; rows = [json.loads(l) for l in (out / "_work" / "checks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    files = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and "_work" not in p.relative_to(out).parts and not p.name.startswith("REPRODUCE_REPORT"):
            files.append({"path": p.relative_to(out).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)})
    bad = [r for r in rows if not r["ok"]]
    rep = {"result": "ALL CHECKS PASSED" if not bad and rows else "FAILED", "checks": len(rows), "failed": len(bad), "api_calls": "none (offline guard active in every python process; no API key read)", "files": files, "check_records": rows}
    (out / "REPRODUCE_REPORT.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = [f"RESULT: {rep['result']}  ({len(rows) - len(bad)}/{len(rows)} checks)", ""]
    lines += [("PASS  " if r["ok"] else "FAIL  ") + r["name"] + "\n        " + r["detail"] for r in rows]
    lines += ["", "FILES PRODUCED:"] + [f"  {f['path']}  ({f['bytes']:,} bytes)  sha256 {f['sha256'][:16]}..." for f in files]
    (out / "REPRODUCE_REPORT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if bad or not rows else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0]); sp = ap.add_subparsers(dest="cmd", required=True)
    def add(name, fn, *args):
        p = sp.add_parser(name); p.set_defaults(fn=fn); p.add_argument("--out", type=Path, required=True)
        for x in args: p.add_argument("--" + x[0], **x[1])
        return p
    S = {"required": True}
    add("copy", cmd_copy, ("name", S), ("rel", S), ("dst", S))
    add("compare", cmd_compare, ("name", S), ("gen", {"type": Path, **S}), ("ref", S), ("kind", S), ("ws", {"type": Path, **S}))
    add("cover-b", cmd_cover, ("name", S), ("ws", {"type": Path, **S}), ("dst", S), ("ref", S))
    add("reel-v8", cmd_reel, ("name", S), ("ws", {"type": Path, **S}), ("dst", S), ("wav", S), ("ref", S))
    add("audio", cmd_audio, ("name", S), ("mp4", S), ("m4a", S), ("wav", S))
    add("contact", cmd_contact, ("name", S), ("dir", S), ("dst", S), ("ref", S), ("ws", {"type": Path, **S}))
    add("media", cmd_media, ("name", S), ("file", S), ("size", S), ("ws", {"type": Path, **S}), ("duration", {"type": float, "default": 0}), ("frames", {"type": int, "default": 0}), ("audio", {"action": "store_true"}))
    add("summary", cmd_summary)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
