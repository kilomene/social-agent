"""Per-platform Terms of Service compliance layer (pure stdlib).

Layer order for every acting operation:
    1. ToS check      <- this module. A prohibition here CANNOT be overridden
                         by missions, autonomy, approvals, or rate-limit
                         headroom. The platform's own rules are the ceiling.
    2. Mission scope / autonomy
    3. Quiet hours, rate limits, anti-spam guards

Each platform ships platforms/<name>/tos_rules.yaml with a status for every
action class:
    prohibited  the platform's terms bar this automation category -> refused
                (raises ToSRefusal; the CLI exits 2 and logs to refusals.jsonl)
    restricted  the terms impose conditions (permission required, API-only,
                no spam, low-volume, ...) -> the CLI proceeds but prints the
                condition as an advisory so the operator sees the constraint
    allowed     no relevant restriction found in the platform's terms

The YAML files are plain-language summaries with links to the official
documents. The official documents govern; these summaries do not, and they
are not legal advice. Each file records its last-checked date because these
documents change over time and must be re-checked periodically.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from policy import yaml_lite

ACTION_CLASSES = (
    "automated_likes",
    "automated_comments",
    "automated_follows",
    "automated_reshares",
    "automated_dms",
    "automated_posting",
    "automated_data_collection",
    "profile_modification",
    "automated_reading",
    "comment_moderation",
)

STATUSES = ("prohibited", "restricted", "allowed")

# CLI operation name -> ToS action class. Anything not in this map has no
# ToS classification and is refused by default (fail closed).
CLI_OP_TO_CLASS = {
    "like": "automated_likes",
    "comment": "automated_comments",
    "follow": "automated_follows",
    "retweet": "automated_reshares",
    "dm": "automated_dms",
    "post": "automated_posting",
    "profile": "profile_modification",
    "read": "automated_reading",
    "watch": "automated_data_collection",
    "hide": "comment_moderation",
    "scan": "automated_data_collection",
}


class ToSRefusal(Exception):
    """A platform's Terms of Service prohibit this action. Not overridable."""

    def __init__(self, platform, action_class, basis, sources):
        self.platform = platform
        self.action_class = action_class
        self.basis = basis
        self.sources = list(sources or [])
        msg = (f"ToS refusal: {action_class} is prohibited on {platform}. "
               f"{basis}")
        if self.sources:
            msg += " See: " + ", ".join(self.sources)
        super().__init__(msg)


_rules_cache = {}


def rules_path(platform):
    return os.path.join(REPO_ROOT, "platforms", platform, "tos_rules.yaml")


def load_rules(platform):
    """Load and validate a platform's tos_rules.yaml (cached per process)."""
    if platform in _rules_cache:
        return _rules_cache[platform]
    path = rules_path(platform)
    if not os.path.exists(path):
        raise ToSRefusal(platform, "unknown",
                         "no ToS rules on file for this platform", [])
    try:
        rules = yaml_lite.load(path)
    except Exception as e:
        raise ToSRefusal(platform, "unknown",
                         f"ToS rules failed to parse: {e}", [])
    if not isinstance(rules, dict) or not isinstance(rules.get("actions"), dict):
        raise ToSRefusal(platform, "unknown",
                         "ToS rules file is malformed (missing actions map)", [])
    _rules_cache[platform] = rules
    return rules


def check_tos(platform, action_class):
    """Enforce the ToS layer for one action. Returns the rule dict.

    Raises ToSRefusal for prohibited actions (and for missing/incomplete
    rules — fail closed). Prints a one-line advisory to stderr for
    restricted actions; allowed actions pass silently.
    """
    if action_class not in ACTION_CLASSES:
        raise ToSRefusal(platform, action_class,
                         "no ToS classification exists for this action class",
                         [])
    rules = load_rules(platform)
    rule = rules["actions"].get(action_class)
    if not isinstance(rule, dict) or rule.get("status") not in STATUSES:
        raise ToSRefusal(platform, action_class,
                         "ToS rules are incomplete for this action class", [])
    if rule["status"] == "prohibited":
        raise ToSRefusal(platform, action_class,
                         rule.get("basis", "prohibited by the platform's terms"),
                         rule.get("sources", []))
    if rule["status"] == "restricted":
        basis = rule.get("basis", "")
        print(f"ToS note [{platform}/{action_class}]: restricted. {basis}",
              file=sys.stderr)
    return rule
