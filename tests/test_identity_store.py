"""v10: identity store — multiple persistent social identities.

identity/
  accounts/          per-account files (handle, platform, persona, owner)
  host_sessions/     registry of host-browser sessions (which host agent +
                     live session performed each fulfilled execution ticket)
  permissions/       per-identity grants (fail-closed: no grant = no action)
  fingerprints/      human-consistency notes (NOT spoofing tooling)
  identities.db      SQLite registry tying it together

The repo drives no browser: there are no persistent browser profiles.
`write_platform_identity` records which identity a platform workspace
operates as; execution happens via execution tickets (hands/) fulfilled
by the host agent in its own live browser.
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


def test_platform_identity_round_trip(home):
    """write_platform_identity / read_platform_identity: which identity a
    platform workspace operates as. No browser profile behind it."""
    ids.create_identity(home, "Nova")
    rec = ids.write_platform_identity(home, "tiktok", "nova")
    assert rec["platform"] == "tiktok"
    assert rec["identity_id"] == "nova"
    assert ids.read_platform_identity(home, "tiktok") == "nova"
    # unset platform -> None (fail-soft read)
    assert ids.read_platform_identity(home, "x") is None
    # overwrite: the workspace now operates as the new identity
    ids.create_identity(home, "Second")
    ids.write_platform_identity(home, "tiktok", "second")
    assert ids.read_platform_identity(home, "tiktok") == "second"
    # stored as plain JSON under workspaces/<platform>/identity.json
    data = json.load(open(os.path.join(
        home, "workspaces", "tiktok", "identity.json")))
    assert data["identity_id"] == "second"
    # and it carries no profile dir — there is no browser here
    assert "profile" not in json.dumps(data).lower()


def test_platform_identity_unknown_identity_refused(home):
    with pytest.raises(KeyError):
        ids.write_platform_identity(home, "tiktok", "ghost")


def test_link_account(home):
    ids.create_identity(home, "Nova")
    ids.link_account(home, "nova", "tt-main", "tiktok", handle="@nova")
    ids.link_account(home, "nova", "x-main", "x", handle="@nova_x")
    ident = ids.get_identity(home, "nova")
    labels = {a["account_label"] for a in ident["accounts"]}
    assert labels == {"tt-main", "x-main"}
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
