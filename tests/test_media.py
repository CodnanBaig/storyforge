import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from storyforge.intake import make_brief
from storyforge.media import captions_to_srt, validate_video


class CaptionTests(unittest.TestCase):
    def test_srt_preserves_measured_boundaries(self):
        result = captions_to_srt([{"text": "Hello", "start": 0.15, "end": 0.45}, {"text": "world.", "start": 0.55, "end": 1.2}])
        self.assertIn("00:00:00,150 --> 00:00:01,200", result)
        self.assertIn("Hello world.", result)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class EncodedMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.path = Path(cls.tmp.name) / "fixture.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=navy:s=160x90:r=30:d=1",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-shortest", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-y", str(cls.path)], check=True, timeout=30)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def test_actual_encoded_video_is_probed(self):
        brief = make_brief(duration=1, format="16:9")
        report = validate_video(self.path, brief)
        self.assertTrue(report["passed"], report["errors"])
        self.assertTrue(report["requires_human_review"])

    def test_wrong_dimensions_or_duration_are_rejected(self):
        report = validate_video(self.path, make_brief(duration=45, format="9:16"))
        self.assertFalse(report["passed"])
        self.assertGreaterEqual(len(report["errors"]), 2)


if __name__ == "__main__": unittest.main()
