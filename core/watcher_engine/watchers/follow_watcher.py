"""Follow watcher: tracks specific users, hashtags, keywords, or posts.

With score_users=true, authors of matched activity are scored against the
interest profile; with propose_follow=true, interesting authors get a
proposed follow (supervised: still needs approval; autonomous missions may
auto-approve within scope and the daily follow cap).
"""

from engagement.interest import load_profile, score_user

from ..framework import Watcher


class FollowWatcher(Watcher):
    type = "follow"
    description = "Watches specific users, hashtags, keywords, or posts for new activity."
    schema = {
        "required": ["targets"],
        "optional": {"propose_engage": False, "score_users": False,
                     "propose_follow": False},
    }

    def _targets(self):
        out = []
        for t in self.effective_config()["targets"]:
            if isinstance(t, dict) and "kind" in t and "value" in t:
                out.append((str(t["kind"]).lower(), str(t["value"]).lower()))
        return out

    def detect(self, items):
        targets = self._targets()
        events = []
        for it in items:
            tkind = str(it.get("target_kind", "")).lower()
            tval = str(it.get("target_value", "")).lower()
            author = str(it.get("author", "")).lower()
            hit = None
            for kind, value in targets:
                if kind == "user" and (author == value or tval == value):
                    hit = (kind, value)
                elif kind in ("hashtag", "keyword") and value in f"{it.get('text','')} {it.get('title','')}".lower():
                    hit = (kind, value)
                elif kind == "post" and tval == value:
                    hit = (kind, value)
                if hit:
                    break
            if not hit:
                continue
            cfg = self.effective_config()
            proposed = None
            user_score = None
            if cfg["score_users"]:
                profile = load_profile()
                user_score, reasons, interesting = score_user(
                    {"username": it.get("author"),
                     "bio": it.get("author_bio", "")}, profile)
                if interesting and cfg["propose_follow"]:
                    proposed = {
                        "action": "follow",
                        "target": it.get("author"),
                        "note": (f"Proposed follow of interesting user @{it.get('author')} "
                                 f"(score {user_score}) — requires approval."),
                    }
            if proposed is None and cfg["propose_engage"]:
                proposed = {
                    "action": "like",
                    "target": it.get("id"),
                    "note": "Proposed engagement — requires user approval.",
                }
            events.append(
                self.make_event(
                    item_id=str(it.get("id")),
                    kind=f"follow:{hit[0]}",
                    summary=f"new activity for watched {hit[0]} '{hit[1]}': "
                    f"{str(it.get('text') or it.get('title'))[:100]}"
                    + (f" [user interest {user_score}]" if user_score is not None else ""),
                    data={**it, "watched": {"kind": hit[0], "value": hit[1]},
                          "user_interest_score": user_score},
                    proposed_action=proposed,
                )
            )
        return events
