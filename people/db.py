"""People memory database — now SQLite-backed (core/memory.py).

Public API is unchanged (upsert/get/top/score/notes/tags/top-fan).
Storage moved from people/*.json to the permanent memory.db; the legacy
JSON files are imported once and archived to people_legacy_<ts>/.
"""

from core import memory as _mem

KINDS = _mem.KINDS
WEIGHTS = _mem.WEIGHTS


def utcnow():
    return _mem.utcnow()


def upsert(home, account, handle, kind, text=None, sentiment=None,
           summary=None):
    return _mem.upsert_interaction(home, account, handle, kind, text=text,
                                   sentiment=sentiment, summary=summary)


def get(home, account, handle):
    return _mem.get_person(home, account, handle)


def score(rec):
    return _mem.person_score(rec.get("counts", {}))


def sentiment_trend(rec):
    s = rec.get("sentiments") or []
    if not s:
        return None
    return round(sum(s) / len(s), 3)


def top(home, account, n=10):
    return _mem.top_people(home, account, n=n)


def ensure(home, account, handle):
    return _mem.ensure_person(home, account, handle)


def add_note(home, account, handle, text):
    return _mem.add_person_note(home, account, handle, text)


def add_tag(home, account, handle, tag):
    return _mem.add_person_tag(home, account, handle, tag)


def remove_tag(home, account, handle, tag):
    return _mem.remove_person_tag(home, account, handle, tag)


def qualifies_as_top_fan(home, account, handle):
    return _mem.qualifies_as_top_fan(home, account, handle)


def is_top_fan(home, account, handle):
    return _mem.is_top_fan(home, account, handle)
