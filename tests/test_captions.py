"""Tests for the caption generator."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from captions import generate as cap


def test_generate_structure():
    c = cap.generate("tiktok", "sora camera moves", "bold")
    for key in ("hook", "body", "cta", "hashtags", "caption"):
        assert c[key]
    assert "sora camera moves" in c["caption"]
    assert 3 <= len(c["hashtags"]) <= 5  # tiktok norms


def test_platform_hashtag_norms():
    assert len(cap.generate("x", "sora", "bold")["hashtags"]) <= 2
    assert len(cap.generate("instagram", "sora", "bold")["hashtags"]) <= 10
    assert cap.generate("reddit", "sora", "bold")["hashtags"] == []


def test_x_char_limit():
    c = cap.generate("x", "a very long topic name " * 10, "bold")
    assert len(c["caption"]) <= 280


def test_variants_differ():
    vs = cap.variants("tiktok", "sora camera moves", "bold", n=5)
    assert len(vs) == 5
    hooks = {v["hook"] for v in vs}
    assert len(hooks) > 1  # different hooks across variants


def test_deterministic():
    a = cap.generate("tiktok", "sora", "bold", seed=2)
    b = cap.generate("tiktok", "sora", "bold", seed=2)
    assert a["caption"] == b["caption"]


def test_bad_platform():
    with pytest.raises(ValueError):
        cap.generate("myspace", "sora", "bold")


def test_bad_tone():
    with pytest.raises(ValueError):
        cap.generate("tiktok", "sora", "robotic")
