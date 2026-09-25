"""Tests: voice module (human-sounding checks) + security + learning + identity."""

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from voice import check as voice_check
from security import secrets as secrets_mod
from security import audit as security_audit_mod
from learning import study as study_mod
from identity import check as identity_check
from conftest import add_account, cli, state


# ------------------------------------------------------------ voice ---

def test_voice_flags_ai_isms():
    r = voice_check.check_text("Delve into this game-changer: leverage these tips!")
    assert r["flags"], "AI-isms must be flagged"
    assert r["score"] < 100
    assert r["suggestions"], "flags must come with fixes"


def test_voice_clean_text_scores_high():
    r = voice_check.check_text("I rendered this shot three times. Here's the one that worked.")
    assert r["score"] >= voice_check.WARN_THRESHOLD
    assert r["human"]


def test_voice_identity_phrases_banned():
    r = voice_check.check_text("As an AI, I can help with that.")
    assert any(f["match"] == "as an ai" for f in r["flags"])


def test_voice_emoji_spam_flagged():
    r = voice_check.check_text("wow 🔥🔥🔥🔥 so good!!!")
    assert any(f["type"] == "emoji_spam" for f in r["flags"])


def test_cli_voice_check(home):
    r = cli("voice", "check", "--text", "Delve into this game-changer!",
            home=home)
    assert r.returncode == 0, r.stderr
    assert "score" in r.stdout.lower() and "delve" in r.stdout.lower()


# --------------------------------------------------------- security ---

def test_secrets_detection():
    found, _ = secrets_mod.contains_secret("token sk-abcdefghij1234567890 done")
    assert found
    found, _ = secrets_mod.contains_secret("-----BEGIN PRIVATE KEY-----")
    assert found
    found, _ = secrets_mod.contains_secret("nothing secret here")
    assert not found


def test_security_refuses_secret_draft_e2e(home):
    add_account(home)
    r = cli("post", "draft", "--platform", "tiktok", "--account", "main",
            "--text", "my api_key=sk-abcdefghij1234567890 leak", home=home)
    assert r.returncode == 2, r.stderr
    assert "secret" in r.stderr.lower()
    assert _no_queue(home), "refused draft must not create a queue entry"


def test_security_audit_flags_secrets_in_state(home):
    os.makedirs(home, exist_ok=True)
    with open(os.path.join(home, "queue.json"), "w", encoding="utf-8") as fh:
        json.dump([{"text": "oops sk-abcdefghij1234567890"}], fh)
    results = security_audit_mod.security_audit(home)
    assert results, "audit must return checks"
    assert any(r["status"] == "fail" for r in results), results


def test_cli_security_audit_and_scan(home):
    r = cli("security", "audit", home=home)
    assert r.returncode == 0, r.stderr
    r = cli("security", "scan", "--text", "hello world", home=home)
    assert r.returncode == 0
    r = cli("security", "scan", "--text", "sk-abcdefghij1234567890", home=home)
    assert r.returncode == 2


# --------------------------------------------------------- learning ---

def test_study_writes_journal_with_adjustments(home):
    os.makedirs(home, exist_ok=True)
    with open(os.path.join(home, "events.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"timestamp": "2026-09-25T00:00:00Z",
                             "kind": "crisis:spike", "data": {}}) + "\n")
    entry = study_mod.run_study(home)
    assert len(entry["adjustments"]) == 3
    j = os.path.join(home, "learning", "journal.md")
    assert os.path.exists(j)
    assert "3 concrete adjustments" in open(j, encoding="utf-8").read()


def test_study_proposals_never_auto_applied(home):
    os.makedirs(home, exist_ok=True)
    props = study_mod.propose_updates(home)
    p = os.path.join(home, "learning", "proposals.md")
    assert os.path.exists(p)
    body = open(p, encoding="utf-8").read()
    assert "REVIEW ONLY" in body and len(props) > 0


def test_experiments_lifecycle(home):
    study_mod.start_experiment(home, "t1", "title", "A variant", "B variant")
    assert len(study_mod.list_experiments(home)) == 1
    exp = study_mod.conclude_experiment(home, "t1", 4.2, 5.9)
    assert exp["winner"] == "B" and exp["status"] == "concluded"


def test_cli_study_run(home):
    r = cli("study", "run", home=home)
    assert r.returncode == 0, r.stderr
    assert os.path.exists(os.path.join(home, "learning", "journal.md"))
    r = cli("study", "experiment", "start", "--name", "e1", "--kind", "hook",
            "--a", "claim", "--b", "question", home=home)
    assert r.returncode == 0, r.stderr
    r = cli("study", "experiment", "conclude", "--name", "e1",
            "--metric-a", "3", "--metric-b", "7", home=home)
    assert r.returncode == 0 and "winner=B" in r.stdout, r.stderr


# --------------------------------------------------------- identity ---

def _persona(home, never_say=""):
    import identity.check as ic
    os.makedirs(os.path.join(home, "identity", "accounts"), exist_ok=True)
    with open(ic.persona_path(home, "main"), "w", encoding="utf-8") as fh:
        fh.write('---\nname: "Exam Owner"\nnever_say:\n')
        if never_say:
            fh.write(f"  - {json.dumps(never_say)}\n")
        fh.write('---\nnotes\n')


def _no_queue(home):
    p = os.path.join(home, "queue.json")
    return not os.path.exists(p) or json.load(open(p, encoding="utf-8")) == []


def test_identity_flags_ai_claim():
    res = identity_check.check_identity(
        "As an AI language model, I think this is great", "main", "/nonexistent")
    assert not res["pass"]
    assert any("identity break" in r for r in res["reasons"])


def test_identity_good_first_person_passes(home):
    _persona(home)
    res = identity_check.check_identity(
        "I spent all night on this edit. My favorite part is the lighting.", "main", home)
    assert res["pass"], res["reasons"]
    assert not any("identity break" in r for r in res["reasons"])


def test_identity_never_say_violation(home):
    _persona(home, never_say="smash that like button")
    res = identity_check.check_identity("Smash that like button guys!", "main", home)
    assert not res["pass"]
    assert any("never-say" in r for r in res["reasons"])


def test_identity_missing_persona_is_advisory_only():
    res = identity_check.check_identity("hello world, I am here", "ghost", "/nonexistent")
    assert res["pass"]
    assert any("no persona" in a for a in res["advisories"])


def test_cli_identity_lifecycle(home):
    add_account(home)
    r = cli("identity", "create", "--account", "main", "--name", "Tester",
            "--voice-traits", "dry humor", "--never-say", "smash that like button",
            home=home)
    assert r.returncode == 0, r.stderr
    r = cli("identity", "show", "--account", "main", home=home)
    assert r.returncode == 0 and "Tester" in r.stdout, r.stderr
    r = cli("identity", "check", "--text", "I love making these videos.",
            "--account", "main", home=home)
    assert r.returncode == 0 and "PASSED" in r.stdout, r.stderr
    r = cli("identity", "check", "--text", "I'm a chatbot, hello!",
            "--account", "main", home=home)
    assert r.returncode == 2 and "identity break" in r.stderr.lower(), r.stderr


def test_identity_break_refuses_post_draft_e2e(home):
    add_account(home)
    r = cli("post", "draft", "--platform", "tiktok", "--account", "main",
            "--text", "As an AI language model, here is my post", home=home)
    assert r.returncode == 2, r.stderr
    assert "identity" in r.stderr.lower()
    assert _no_queue(home), "refused draft must not create a queue entry"
    refusals = [json.loads(l) for l in open(os.path.join(home, "refusals.jsonl"))]
    assert refusals and "identity" in refusals[0]["reason"].lower()


def test_engage_comment_runs_gates(home):
    add_account(home)
    r = cli("engage", "comment", "--platform", "tiktok", "--account", "main",
            "--target", "v1", "--text", "I'm an AI and this is great", home=home)
    assert r.returncode == 2, r.stderr
    assert "identity" in r.stderr.lower()
    r = cli("engage", "comment", "--platform", "tiktok", "--account", "main",
            "--target", "v1", "--text", "This breakdown helped me a lot.", home=home)
    assert r.returncode == 0, r.stderr
