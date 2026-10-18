"""Paid/closed providers as honest stubs.

No paid APIs or services may be used ($0 budget). Each stub declares its
normal contract (id/label/rules/models) but its generate* functions raise
PipelineBlockedError naming EXACTLY what blocks — never a fake asset.
"""

from __future__ import annotations

from .base import ProviderDefinition
from .. import definition as d


class StubProvider(ProviderDefinition):
    """Base for stub providers: capability stubs raise PipelineBlockedError."""

    blocked_reason = "no $0 provider wired"

    def _blocked(self, capability):
        raise d.PipelineBlockedError(
            f"{self.id}: {self.blocked_reason} "
            f"(capability {capability} unavailable; stub, never faked)")


class MuseVideoStub(StubProvider):
    id = "muse-video"
    label = "Muse Video (region-gated)"
    version = "1"
    rules = [{"field": "region_gate", "label": "region gate (403)",
              "required": False}]  # host-driven; no key, but not usable
    models = [{"id": "muse-video-1", "label": "Muse Video",
               "type": "video"}]
    blocked_reason = ("video generation: no $0 provider; region gate 403 "
                      "\"Video generation isn't available in your country "
                      "or region\"")

    def generate_video(self, ctx, request):
        self._blocked("generate_video")


class SoraStub(StubProvider):
    id = "sora"
    label = "Sora (paid)"
    version = "1"
    rules = [{"field": "apiKey", "label": "API key", "secret": True}]
    models = [{"id": "sora-2", "label": "Sora", "type": "video"}]
    blocked_reason = "video generation: no $0 provider (paid API)"

    def generate_video(self, ctx, request):
        self._blocked("generate_video")


class KlingStub(StubProvider):
    id = "kling"
    label = "Kling (paid)"
    version = "1"
    rules = [{"field": "apiKey", "label": "API key", "secret": True}]
    models = [{"id": "kling-2.1", "label": "Kling", "type": "video"}]
    blocked_reason = "video generation: no $0 provider (paid API)"

    def generate_video(self, ctx, request):
        self._blocked("generate_video")


class VeoStub(StubProvider):
    id = "veo"
    label = "Veo (paid)"
    version = "1"
    rules = [{"field": "apiKey", "label": "API key", "secret": True}]
    models = [{"id": "veo-3.1", "label": "Veo", "type": "video"}]
    blocked_reason = "video generation: no $0 provider (paid API)"

    def generate_video(self, ctx, request):
        self._blocked("generate_video")


class TtsStub(StubProvider):
    id = "tts-stub"
    label = "TTS (no $0 provider)"
    version = "1"
    rules = [{"field": "tts_provider", "label": "no $0 TTS wired",
              "required": False}]
    models = [{"id": "none", "label": "no voice models", "type": "audio"}]
    blocked_reason = ("tts: no $0 provider; voice lines need a locked "
                      "voice ID per character before any TTS wiring")

    def generate_audio(self, ctx, request):
        self._blocked("generate_audio")


class ImageStub(StubProvider):
    id = "image-stub"
    label = "Image generation (no $0 provider)"
    version = "1"
    rules = [{"field": "image_provider", "label": "no $0 image gen wired",
              "required": False}]
    models = [{"id": "none", "label": "no image models", "type": "image"}]
    blocked_reason = "image generation: no $0 provider"

    def generate_image(self, ctx, request):
        self._blocked("generate_image")


PROVIDERS = [MuseVideoStub(), SoraStub(), KlingStub(), VeoStub(),
             TtsStub(), ImageStub()]
