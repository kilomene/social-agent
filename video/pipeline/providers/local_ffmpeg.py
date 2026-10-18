"""Free local provider: synthetic test media via ffmpeg lavfi.

rules: [] (no apiKey), hardcoded models. This provider is NOT an AI
generator: it only synthesizes honest test/placeholder media from an
explicit lavfi spec in request["other"]["lavfi"]. Anything else raises
PipelineBlockedError. Used for pipeline smoke tests and gate-harness
fixtures where no $0 generation provider exists.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from .base import ProviderDefinition
from .. import definition as d


class LocalFfmpegProvider(ProviderDefinition):
    id = "local-ffmpeg"
    label = "Local FFmpeg (synthetic test media)"
    version = "1"
    rules = []
    models = [
        {"id": "lavfi-video", "label": "lavfi synthetic video", "type": "video"},
        {"id": "lavfi-audio", "label": "lavfi synthetic audio", "type": "audio"},
        {"id": "lavfi-image", "label": "lavfi synthetic still", "type": "image"},
    ]

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _ffmpeg():
        ff = shutil.which("ffmpeg")
        if not ff:
            raise d.PipelineBlockedError(
                "local-ffmpeg: ffmpeg binary not found on this host")
        return ff

    @staticmethod
    def _lavfi(request):
        spec = ((request or {}).get("other") or {}).get("lavfi")
        if not spec or not isinstance(spec, str):
            raise d.PipelineBlockedError(
                "local-ffmpeg is not an AI generator: it synthesizes test "
                "media only, and needs request['other']['lavfi'] with an "
                "explicit ffmpeg lavfi filter (e.g. "
                "'testsrc=duration=5:size=1280x720:rate=24')")
        return spec

    @staticmethod
    def _duration(request, default=5.0):
        return float(((request or {}).get("other") or {}).get("duration_s")
                     or default)

    def _synth(self, ctx, request, argv, mime, media_type):
        ctx.check_cancelled()
        suffix = {"video": ".mp4", "audio": ".wav",
                  "image": ".png"}[media_type]
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            proc = subprocess.run(argv + [tmp], capture_output=True, text=True)
            if proc.returncode != 0:
                raise d.ProviderError(
                    f"local-ffmpeg failed (exit {proc.returncode}): "
                    f"{proc.stderr.strip()[-300:]}")
            with open(tmp, "rb") as fh:
                data = fh.read()
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return [{"mediaType": media_type, "data": data, "mimeType": mime}]

    # -- capabilities ------------------------------------------------------
    def generate_video(self, ctx, request):
        ff = self._ffmpeg()
        spec = self._lavfi(request)
        dur = self._duration(request)
        return self._synth(ctx, request,
                           [ff, "-y", "-v", "error", "-f", "lavfi",
                            "-i", f"{spec},trim=duration={dur},"
                            "setpts=PTS-STARTPTS",
                            "-f", "lavfi", "-i",
                            f"anullsrc=r=44100:cl=stereo:d={dur}",
                            "-pix_fmt", "yuv420p", "-c:v", "libx264",
                            "-c:a", "aac", "-shortest"],
                           "video/mp4", "video")

    def generate_audio(self, ctx, request):
        ff = self._ffmpeg()
        spec = self._lavfi(request)
        dur = self._duration(request)
        return self._synth(ctx, request,
                           [ff, "-y", "-v", "error", "-f", "lavfi",
                            "-i", f"{spec},atrim=duration={dur},"
                            "asetpts=PTS-STARTPTS",
                            "-ar", "44100", "-ac", "1"],
                           "audio/wav", "audio")

    def generate_image(self, ctx, request):
        ff = self._ffmpeg()
        spec = self._lavfi(request)
        return self._synth(ctx, request,
                           [ff, "-y", "-v", "error", "-f", "lavfi",
                            "-i", spec, "-frames:v", "1"],
                           "image/png", "image")

    def get_price(self, ctx, request):
        return {"price": "$0 (local compute)", "tips": ""}

    def get_balance(self, ctx):
        return {"balance": float("inf"), "unit": "local", "keyBalance": None}


PROVIDER = LocalFfmpegProvider()
