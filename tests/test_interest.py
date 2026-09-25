"""Interest-scoring model tests (pure unit, no subprocess)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engagement import interest


def profile():
    return {
        "enabled": True,
        "topics": ["ai video", "sora"],
        "hashtags": ["aivideo"],
        "authors": ["creator_x"],
        "quality_signals": {"min_likes": 50, "min_comments": 5},
        "weights": {"topic": 2, "hashtag": 3, "author": 4, "quality_signal": 1},
        "threshold": 5,
    }


def test_interesting_post_scores_above_threshold():
    item = {"author": "someone", "text": "New AI video workflow just dropped #aivideo",
            "hashtags": ["aivideo"], "likes": 500, "comments": 40}
    score, reasons, interesting = interest.score_post(item, profile())
    assert score == 7  # topic 2 + hashtag 3 + likes 1 + comments 1
    assert interesting
    assert any("topic" in r for r in reasons)
    assert any("hashtag" in r for r in reasons)


def test_boring_post_is_not_interesting():
    item = {"author": "dancer_y", "text": "POV: your cat pays rent", "likes": 5}
    score, reasons, interesting = interest.score_post(item, profile())
    assert score == 0 and not interesting


def test_author_affinity_alone_below_threshold():
    item = {"author": "creator_x", "text": "hello world", "likes": 1}
    score, reasons, interesting = interest.score_post(item, profile())
    assert score == 4 and not interesting


def test_hashtag_extracted_from_text_case_insensitive():
    item = {"author": "z", "text": "check this #AIvideo out", "likes": 60}
    score, _, interesting = interest.score_post(item, profile())
    assert score == 4 and not interesting  # hashtag 3 + quality 1


def test_extract_hashtags():
    assert interest.extract_hashtags("a #Test and #aivideo!") == ["test", "aivideo"]


def test_score_user_author_affinity():
    score, _, interesting = interest.score_user(
        {"username": "creator_x", "bio": "filmmaker"}, profile())
    assert score == 4 and not interesting


def test_score_user_bio_topic():
    score, _, interesting = interest.score_user(
        {"username": "newbie", "bio": "I make ai video tutorials"}, profile())
    assert score == 2 and not interesting


def test_disabled_profile_interesting_by_default():
    p = profile()
    p["enabled"] = False
    _, _, interesting = interest.score_post({"text": "x"}, p)
    assert interesting
