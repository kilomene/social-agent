# ProviderDefinition contract and provider registry.
#
# Substantial derivation from Toonflow-app
# (https://github.com/HBAI-Ltd/Toonflow-app):
#
#   MIT License — Copyright (c) 2026 HBAI-Ltd
#
#   Permission is hereby granted, free of charge, to any person obtaining a
#   copy of this software and associated documentation files (the "Software"),
#   to deal in the Software without restriction, including without limitation
#   the rights to use, copy, modify, merge, publish, distribute, sublicense,
#   and/or sell copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included
#   in all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#   OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#   MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#   CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#   TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#   SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# Adapted from Toonflow's packages/providers (types.d.ts) ProviderDefinition:
# {id, label, version, rules[], models[]} + optional generateImage /
# generateVideo / generateAudio / getPrice / getBalance / processMedia.
# Generate functions return FINAL media assets, never task IDs.

"""Provider registry (importlib-loaded; third-party modules are trusted code)."""

from __future__ import annotations

import importlib

from . import base  # noqa: F401  (re-exported contract)
from .. import definition as d

_BUILTIN_MODULES = ("local_ffmpeg", "stubs")
_CACHE = {}


def _load_module(name):
    if name not in _CACHE:
        _CACHE[name] = importlib.import_module(f".{name}", __name__)
    return _CACHE[name]


def _module_providers(name):
    mod = _load_module(name)
    if hasattr(mod, "PROVIDER"):
        return [mod.PROVIDER]
    if hasattr(mod, "PROVIDERS"):
        return list(mod.PROVIDERS)
    raise d.PipelineError(
        f"provider module {name!r} exports neither PROVIDER nor PROVIDERS")


def list_providers():
    """Return all registered provider instances."""
    out = []
    for name in _BUILTIN_MODULES:
        out.extend(_module_providers(name))
    return out


def get_provider(provider_id, config=None, cancelled=None):
    """Resolve a provider by id and bind its config/cancel context."""
    for prov in list_providers():
        if prov.id == provider_id:
            return base.bind(prov, config=config, cancelled=cancelled)
    known = ", ".join(sorted(p.id for p in list_providers()))
    raise d.PipelineError(
        f"unknown provider {provider_id!r} (known: {known})")


def free_providers():
    """Providers with rules == [] (no apiKey): usable under the $0 budget."""
    return [p for p in list_providers() if not p.rules]


__all__ = ["base", "list_providers", "get_provider", "free_providers"]
