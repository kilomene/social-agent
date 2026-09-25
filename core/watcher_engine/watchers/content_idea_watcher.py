"""Content-idea watcher: mines comment sections for repeated questions.

"People keep asking X" -> that's your next video. Comments asking the same
thing (min_repeats, default 3) are clustered by normalized question text and
emitted as one content-idea event with a proposed post angle.

Items: {"id", "text", "author", "likes"} (comments on your content).
"""

import re
from collections import defaultdict

from ..framework import Watcher

QUESTION_HINTS = ("?", "how ", "what ", "why ", "when ", "where ", "can you",
                  "could you", "please make", "do a video", "tutorial",
                  "part 2", "part2")


def normalize(text):
    t = (text or "").lower()
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def is_question(text):
    low = (text or "").lower()
    return any(h in low for h in QUESTION_HINTS)


class ContentIdeaWatcher(Watcher):
    type = "content-idea"
    description = "Aggregates repeated audience questions into content ideas."
    schema = {
        "required": [],
        "optional": {
            "min_repeats": 3,
            "propose_content": True,
        },
    }

    def detect(self, items):
        cfg = self.effective_config()
        clusters = defaultdict(list)
        for it in items:
            text = it.get("text", "")
            if not is_question(text):
                continue
            clusters[normalize(text)].append(it)
        events = []
        for key, group in clusters.items():
            if len(group) < cfg["min_repeats"]:
                continue
            rep = max(group, key=lambda g: g.get("likes", 0) or 0)
            proposed = None
            if cfg["propose_content"]:
                proposed = {
                    "action": "post",
                    "target": f"idea:{rep.get('id')}",
                    "note": (f"Video idea: answer '{rep.get('text')}' "
                             f"(asked {len(group)}x by your audience)."),
                }
            askers = ", ".join(f"@{g.get('author', '?')}" for g in group[:5])
            events.append(
                self.make_event(
                    item_id=f"idea-{abs(hash(key)) % 10**8}",
                    kind="content-idea:request",
                    summary=(f"audience keeps asking ({len(group)}x): "
                             f"'{rep.get('text')}' — {askers}"),
                    data={"question": rep.get("text"), "count": len(group),
                          "askers": [g.get("author") for g in group]},
                    proposed_action=proposed,
                )
            )
        return events
