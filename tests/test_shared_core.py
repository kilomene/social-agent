"""Anti-regression tripwire: the per-platform workspace layout never
duplicates shared core.

Shared core (single instance per install — see core/SHARED_CORE.md):
  permanent memory, watcher engine, hands handoff (execution tickets),
  backup & recovery, resume engine, scheduler, event bus, video editor,
  audio engine, caption generator, analytics database, human approval
  system.

The repo drives no browser itself: there is no browser engine, no
Playwright, no persistent profiles anywhere. Approved actions become
execution tickets (hands/) fulfilled visibly by an external agent in its
own live browser; host sessions are recorded via hands.tickets.

Every platform gets its own source tree::

    platforms/<name>/
      __init__.py        adapter spec (declarative, no-API: execution via
                         execution tickets in the external agent's browser)
      terms.md / tos_rules.yaml
      watchers/          REGISTRATION manifest only (no watcher classes)
      memory/            namespaced VIEW into the shared DB (no .db copy)
      workspace/         shipped workspace template

This test scans every platform subtree and FAILS if any shared-core
module basename or package directory reappears there. It also fails if a
`browser_profile` directory reappears under platforms/ or if any file
imports playwright.
"""

import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORMS = os.path.join(REPO, "platforms")

WATCHER_TYPES = (
    "activity", "channel", "comment", "competitor", "content-idea",
    "crisis", "feed", "follow", "mention", "message", "notification",
    "security", "sentiment", "trend", "velocity",
)

# basenames of shared-core modules — must not exist under platforms/<p>/
SHARED_CORE_FILES = {
    # 1. permanent memory
    "memory.py",
    # 3. backup & recovery / resume
    "backup.py", "recovery.py", "remote.py",
    # 4. scheduler / event bus
    "scheduler.py",
    # hands handoff (execution tickets live once in hands/)
    "tickets.py", "steps.py",
    # watcher engine (lives once in core/watcher_engine/)
    "framework.py", "engine.py",
    # 5. video editor
    "analyze.py", "kdenlive.py", "shotcut.py",
    # 6. audio engine
    "clips.py",
    # 7. caption generator
    "generate.py",
    # 9. human approval system
    "queue.py",
    # supporting singletons
    "tos.py", "controller.py", "mode.py",
} | {f"{t.replace('-', '_')}_watcher.py" for t in WATCHER_TYPES}

# directory names of shared-core packages — must not exist under
# platforms/<p>/, EXCEPT the sanctioned platforms/<p>/memory/ view dir
# (asserted separately to hold no database).
SHARED_CORE_DIRS = {
    "core", "hands", "editor", "audio", "captions", "approvals",
    "platforms", "ratelimit", "crisis", "identity",
    "watcher_engine", "scheduler", "event_bus", "resume_engine",
}

# platforms/<p>/memory is the sanctioned namespaced-view exception
SANCTIONED_MEMORY_DIRS = {"memory"}


def _platform_subtrees():
    for platform in sorted(os.listdir(PLATFORMS)):
        pdir = os.path.join(PLATFORMS, platform)
        if not os.path.isdir(pdir):
            continue
        for sub in ("workspace", "watchers", "memory"):
            sdir = os.path.join(pdir, sub)
            if os.path.isdir(sdir):
                yield platform, sub, sdir


def _iter_files(sdir):
    for dp, dn, fn in os.walk(sdir):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for f in fn:
            if f.endswith(".pyc"):
                continue
            yield os.path.join(dp, f)


def _iter_dirs(sdir):
    for dp, dn, fn in os.walk(sdir):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for d in dn:
            yield os.path.join(dp, d)


def test_top_level_watchers_dir_is_gone():
    assert not os.path.exists(os.path.join(REPO, "watchers")), \
        "top-level watchers/ must be deleted — watchers live in " \
        "core/watcher_engine/ and register per-platform"
    try:
        import watchers  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        raise AssertionError("import watchers should fail loudly")


def test_no_shared_core_files_in_platform_trees():
    hits = []
    for platform, sub, sdir in _platform_subtrees():
        for path in _iter_files(sdir):
            if os.path.basename(path) in SHARED_CORE_FILES:
                hits.append(os.path.relpath(path, REPO))
    assert not hits, (
        "shared-core modules duplicated inside platform trees: "
        f"{hits} — platforms must USE shared core, never copy it"
    )


def test_no_shared_core_dirs_in_platform_trees():
    hits = []
    for platform, sub, sdir in _platform_subtrees():
        for path in _iter_dirs(sdir):
            name = os.path.basename(path)
            if name in SHARED_CORE_DIRS:
                hits.append(os.path.relpath(path, REPO))
    assert not hits, (
        "shared-core packages duplicated inside platform trees: "
        f"{hits} — platforms must USE shared core, never copy it"
    )


def test_platform_memory_is_a_view_not_a_copy():
    for platform, sub, sdir in _platform_subtrees():
        if sub != "memory":
            continue
        for path in _iter_files(sdir):
            assert not path.endswith(".db"), \
                f"database copy inside {os.path.relpath(path, REPO)} — " \
                "platforms share ONE memory.db"
            assert os.path.basename(path) != "memory.py", \
                f"memory.py copy inside {os.path.relpath(path, REPO)}"


def test_no_browser_profile_dirs_anywhere():
    """The persistent-profile world is gone: no browser_profile dir may
    exist under platforms/ (execution is via hands tickets now)."""
    hits = []
    for platform in sorted(os.listdir(PLATFORMS)):
        pdir = os.path.join(PLATFORMS, platform)
        if not os.path.isdir(pdir):
            continue
        for dp, dn, _fn in os.walk(pdir):
            dn[:] = [d for d in dn if d != "__pycache__"]
            if "browser_profile" in dn:
                hits.append(os.path.relpath(
                    os.path.join(dp, "browser_profile"), REPO))
    assert not hits, (
        "browser_profile dir reappeared under platforms/: "
        f"{hits} — the repo drives no browser and keeps no profiles"
    )


def test_no_playwright_imports():
    """No file anywhere in the repo imports playwright (brain-only)."""
    import re as _re
    stmt = _re.compile(r"(?m)^\s*(import playwright|from playwright\s+import)")
    hits = []
    for dp, dn, fn in os.walk(REPO):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git")]
        for f in fn:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, encoding="utf-8", errors="strict") as fh:
                    text = fh.read()
            except OSError:
                continue
            if stmt.search(text):
                hits.append(os.path.relpath(p, REPO))
    assert not hits, f"playwright imported by: {hits}"


def test_platform_watchers_dir_is_a_manifest_not_classes():
    for platform, sub, sdir in _platform_subtrees():
        if sub != "watchers":
            continue
        names = {n for n in os.listdir(sdir) if n != "__pycache__"}
        assert names == {"__init__.py"}, \
            f"{platform}/watchers/ must hold only the registration " \
            f"manifest, found: {names}"


def test_every_platform_registers_its_watchers():
    import sys
    sys.path.insert(0, REPO)
    from core.watcher_engine import REGISTRY
    for platform in ("tiktok", "x", "instagram", "facebook", "youtube",
                     "reddit", "linkedin"):
        pkg = __import__(f"platforms.{platform}.watchers",
                         fromlist=["WATCHERS"])
        declared = {s[0] if isinstance(s, (tuple, list)) else s
                    for s in pkg.WATCHERS}
        expected = set(REGISTRY) - (set() if platform == "youtube"
                                    else {"channel"})
        assert declared == expected, \
            f"{platform}: manifest declares {sorted(declared)}, " \
            f"expected {sorted(expected)}"


def test_shared_core_manifest_documents_new_layout():
    with open(os.path.join(REPO, "core", "SHARED_CORE.md"),
              encoding="utf-8") as fh:
        text = fh.read()
    for service in ("Permanent memory", "Watcher engine", "Hands handoff",
                    "Backup & recovery", "Resume engine", "Scheduler",
                    "Event bus", "Video editor", "Audio engine",
                    "Caption generator", "Analytics database",
                    "Human approval system"):
        assert service in text, f"SHARED_CORE.md missing: {service}"
    assert "platforms/<name>/" in text
    # the old browser-engine world must not be documented anymore
    assert "Browser engine" not in text


def test_platforms_exist_for_shipped_platforms():
    for platform in ("tiktok", "x", "instagram", "facebook",
                     "youtube", "reddit", "linkedin"):
        pdir = os.path.join(PLATFORMS, platform)
        assert os.path.isdir(pdir), f"missing platform tree for {platform}"
        for sub in ("workspace", "watchers", "memory"):
            assert os.path.isdir(os.path.join(pdir, sub)), \
                f"missing {sub}/ for {platform}"
        # no persistent-profile leftovers: the brain/hands refactor deleted
        # every platforms/<name>/browser_profile/ dir
        assert not os.path.exists(os.path.join(pdir, "browser_profile")), \
            f"browser_profile/ still present for {platform}"
        for f in ("terms.md", "tos_rules.yaml"):
            assert os.path.isfile(os.path.join(pdir, f)), \
                f"missing {f} for {platform}"
