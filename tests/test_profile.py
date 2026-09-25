"""Profile command tests: explicit approval is always required."""

import os

from conftest import add_account, cli, state


def test_profile_update_needs_explicit_approve(home):
    add_account(home)
    r = cli("profile", "update", "--account", "main", "--bio", "AI video daily",
            home=home)
    assert r.returncode == 0 and "PROPOSED" in r.stdout
    pid = state(home, "profiles.json")["proposals"][0]["id"]
    assert state(home, "profiles.json")["proposals"][0]["status"] == "proposed"
    # done without approve is refused
    r = cli("profile", "done", pid, home=home)
    assert r.returncode == 1 and "approve it first" in r.stderr
    # explicit approve works
    r = cli("profile", "approve", pid, home=home)
    assert r.returncode == 0 and "APPROVED" in r.stdout
    r = cli("profile", "done", pid, "--result", "bio updated in browser", home=home)
    assert r.returncode == 0
    p = state(home, "profiles.json")
    assert p["proposals"][0]["status"] == "done"
    assert p["accounts"]["tester"]["bio"] == "AI video daily"


def test_profile_never_auto_approved_in_autonomous_mode(home):
    add_account(home)
    mdir = os.path.join(home, "missions")
    os.makedirs(mdir, exist_ok=True)
    mc = lambda *a: cli(*a, home=home, missions=mdir)
    mc("mission", "create", "--name", "m1", "--platforms", "tiktok",
       "--topics", "ai video", "--actions", "post,like")
    mc("autonomy", "grant", "--mission", "m1", "--confirm")
    r = cli("profile", "update", "--account", "main",
            "--display-name", "New Name", home=home)
    assert r.returncode == 0
    prop = state(home, "profiles.json")["proposals"][0]
    # autonomy granted, yet the proposal stays proposed: no auto-approval path
    assert prop["status"] == "proposed"
    assert prop.get("auto_approved") is not True


def test_profile_view(home):
    add_account(home)
    r = cli("profile", "view", "--account", "main", home=home)
    assert r.returncode == 0 and "tester" in r.stdout
