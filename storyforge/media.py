"""Local media inspection; the runtime never calls a paid generator implicitly."""
from __future__ import annotations

import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path


def probe_media(path: Path) -> dict:
    if shutil.which("ffprobe") is None: raise RuntimeError("ffprobe is required to verify media. Install FFmpeg first.")
    p = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path.resolve())],
                       capture_output=True, text=True, timeout=90, check=False)
    if p.returncode: raise RuntimeError("ffprobe could not decode the supplied media")
    try: result = json.loads(p.stdout)
    except json.JSONDecodeError as ex: raise RuntimeError("ffprobe returned invalid JSON") from ex
    if not isinstance(result, dict) or not isinstance(result.get("streams"), list): raise RuntimeError("ffprobe result is missing streams")
    return result


def validate_video(path: Path, brief: dict) -> dict:
    errors: list[str] = []
    try: probe = probe_media(path)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as ex:
        return {"passed": False, "errors": [str(ex)], "probe": None}
    videos = [s for s in probe["streams"] if s.get("codec_type") == "video"]
    audios = [s for s in probe["streams"] if s.get("codec_type") == "audio"]
    if not videos: errors.append("Export has no video stream")
    else:
        v = videos[0]
        width, height = v.get("width", 0), v.get("height", 0)
        expected = Fraction(brief["format"].replace(":", "/"))
        if not height or abs(width / height - float(expected)) > 0.01: errors.append("Export aspect ratio differs from brief")
        try:
            actual_fps = float(Fraction(v.get("avg_frame_rate", "0/1")))
            if abs(actual_fps - brief["fps"]) > 0.01: errors.append("Export frame rate differs from brief")
        except (ValueError, ZeroDivisionError): errors.append("Cannot read export frame rate")
        if v.get("pix_fmt") not in {"yuv420p", "yuvj420p"}: errors.append("Delivery should use yuv420p for broad playback compatibility")
    try:
        duration = float(probe["format"]["duration"])
        tolerance = max(0.25, 2 / brief["fps"])
        if abs(duration - brief["duration_seconds"]) > tolerance: errors.append("Encoded duration differs from brief")
    except (TypeError, KeyError, ValueError): errors.append("Cannot measure encoded duration")
    if brief.get("voice", {}).get("required", True) and not audios: errors.append("Narrated production has no audio stream")
    return {"passed": not errors, "errors": errors, "probe": probe,
            "requires_human_review": ["Speech is intelligible and complete", "No silent or clipped narration", "Actual caption sync", "Rendered visual continuity", "Facts and rights match final packaging"]}


def captions_to_srt(words: list[dict], max_words: int = 7) -> str:
    def stamp(t: float) -> str:
        ms = round(t * 1000)
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    blocks = []
    for i in range(0, len(words), max_words):
        group = words[i:i+max_words]
        blocks.append(f"{len(blocks)+1}\n{stamp(group[0]['start'])} --> {stamp(group[-1]['end'])}\n{' '.join(w['text'] for w in group)}")
    return "\n\n".join(blocks) + "\n"
