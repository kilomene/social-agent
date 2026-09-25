"""v10: identity store — multiple persistent social identities.

identity/
  accounts/          per-account files (handle, platform, persona, owner)
  browser_profiles/  accounts -> ONE shared profile dir per identity
  permissions/       per-identity grants (fail-closed: no grant = no action)
  fingerprints/      human-consistency notes (NOT spoofing tooling)
  identities.db      SQLite registry tying it together
"""

import json
import os

import pytest

from identity import store as ids


def test_create_and_list_identities(home):
    i = ids.create_identity(home, "Nova", owner_name="Ochacho")
    assert i["id"] == "nova"
    assert i["owner_name"] == "Ochacho"
    assert [x["id"] for x in ids.list_identities(home)] == ["nova"]
    # re-creating updates, never duplicates
    ids.create_identity(home, "Nova", owner_name="Ochacho")
    assert len(ids.list_identities(home)) == 1


def test_link_account_shares_one_profile(home):
    ids.create_identity(home, "Nova")
    ids.link_account(home, "nova", "tt-main", "tiktok", handle="@nova")
    ids.link_account(home, "nova", "x-main", "x", handle="@nova_x")
    ident = ids.get_identity(home, "nova")
    labels = {a["account_label"] for a in ident["accounts"]}
    assert labels == {"tt-main", "x-main"}
    p1 = ids.shared_profile_dir(home, "nova")
    # both accounts resolve to the SAME shared profile dir
    r1 = ids.resolve_profile_dir(home, "tt-main", legacy_dir="/legacy/tt")
    r2 = ids.resolve_profile_dir(home, "x-main", legacy_dir="/legacy/x")
    assert r1 == r2 == p1
    assert os.path.isdir(p1)
    # registry file maps accounts -> profile
    reg = json.load(open(os.path.join(
        home, "identity", "browser_profiles", "nova.json")))
    assert reg["profile_dir"] == p1
    assert len(reg["accounts"]) == 2
    # unlinked accounts fall back to their legacy dir
    assert ids.resolve_profile_dir(home, "stranger",
                                   legacy_dir="/legacy/s") == "/legacy/s"
    assert ids.identity_for_account(home, "tt-main") == "nova"
    assert ids.identity_for_account(home, "stranger") is None


def test_permissions_fail_closed(home):
    ids.create_identity(home, "Nova")
    # unknown identity: denied
    assert ids.may(home, "ghost", "like") is False
    # known identity, no grants: denied (fail-closed)
    assert ids.may(home, "nova", "like") is False
    # empty action: denied
    assert ids.may(home, "nova", "") is False
    ids.grant(home, "nova", "like")
    assert ids.may(home, "nova", "like") is True
    assert ids.may(home, "nova", "comment") is False  # not granted
    ids.revoke(home, "nova", "like")
    assert ids.may(home, "nova", "like") is False
    # wildcard grant
    ids.set_permissions(home, "nova", {"actions": ["*"]})
    assert ids.may(home, "nova", "anything") is True


def test_approval_required_defaults_to_yes(home):
    ids.create_identity(home, "Nova")
    # fail-closed: approval required unless explicitly exempted
    assert ids.approval_required(home, "nova", "publish") is True
    ids.set_permissions(home, "nova",
                        {"actions": ["like"],
                         "require_approval_exempt": ["like"]})
    assert ids.approval_required(home, "nova", "like") is False
    assert ids.approval_required(home, "nova", "publish") is True
    # permission files are human-readable JSON on disk
    perms = json.load(open(os.path.join(
        home, "identity", "permissions", "nova.json")))
    assert perms["grants"]["actions"] == ["like"]


def test_fingerprint_notes_are_consistency_not_spoofing(home):
    ids.create_identity(home, "Nova")
    fp = ids.set_fingerprint(home, "nova", viewport="1366x768",
                             locale="en-US", timezone_name="America/Los_Angeles",
                             notes="owner's real laptop browser")
    assert fp["viewport"] == "1366x768"
    assert fp["locale"] == "en-US"
    got = ids.get_fingerprint(home, "nova")
    assert got["timezone"] == "America/Los_Angeles"
    # no rotation/randomization fields exist anywhere in the record
    for forbidden in ("rotate", "random", "spoof", "proxy"):
        assert forbidden not in json.dumps(got).lower()


def test_link_unknown_identity_refused(home):
    with pytest.raises(KeyError):
        ids.link_account(home, "ghost", "a1", "tiktok")
    with pytest.raises(KeyError):
        ids.grant(home, "ghost", "like")
