# social-agent exam results

Run: 2026-09-25 07:02 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 59/59 (100%)**

## Run: 2026-09-25 08:00 UTC — v7 AI Video Editor Worker (exams 40–45 appended; history preserved)

**Total: 179/179 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

---

# social-agent exam results

Run: 2026-09-25 07:12 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 71/71 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

---

# social-agent exam results

Run: 2026-09-25 07:19 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 106/106 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

---

# social-agent exam results

Run: 2026-09-25 07:25 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 130/134 (97%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **1/5** [FAIL]
- ✗ dry-run exits 0 — usage: social-agent [-h] [--version]
                    {accounts,watch,post,engage,mission,autonomy,profile,heartbeat,
- ✗ fade-in filter arg present
- ✗ fade-out filter arg present
- ✓ dry-run executed nothing
- ✗ exact command printed for transparency

---

# social-agent exam results

Run: 2026-09-25 07:27 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 134/134 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **5/5** [PASS]
- ✓ dry-run exits 0
- ✓ fade-in filter arg present
- ✓ fade-out filter arg present
- ✓ dry-run executed nothing
- ✓ exact command printed for transparency

---

# social-agent exam results

Run: 2026-09-25 07:27 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 134/134 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **5/5** [PASS]
- ✓ dry-run exits 0
- ✓ fade-in filter arg present
- ✓ fade-out filter arg present
- ✓ dry-run executed nothing
- ✓ exact command printed for transparency

---

# social-agent exam results

Run: 2026-09-25 07:28 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 134/134 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **5/5** [PASS]
- ✓ dry-run exits 0
- ✓ fade-in filter arg present
- ✓ fade-out filter arg present
- ✓ dry-run executed nothing
- ✓ exact command printed for transparency

---

# social-agent exam results

Run: 2026-09-25 07:35 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 155/155 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **5/5** [PASS]
- ✓ dry-run exits 0
- ✓ fade-in filter arg present
- ✓ fade-out filter arg present
- ✓ dry-run executed nothing
- ✓ exact command printed for transparency

## exam-34: specs lookup returns 9:16 for tiktok feed, 16:9 for youtube long-form
Score: **5/5** [PASS]
- ✓ tiktok feed is 9:16
- ✓ youtube long-form is 16:9
- ✓ youtube shorts is 9:16
- ✓ tiktok feed resolution 1080x1920
- ✓ 11 placements across 6 platforms

## exam-35: 4:3 -> 9:16 fit defaults to pad (nothing is cut)
Score: **5/5** [PASS]
- ✓ fit exits 0
- ✓ strategy is pad
- ✓ pad uses blurred fill
- ✓ no destructive crop-to-fill box in args
- ✓ dry-run wrote nothing

## exam-36: crop without a focus point is refused
Score: **2/2** [PASS]
- ✓ refused (exit 2)
- ✓ refusal explains the focus requirement

## exam-37: crop with --focus top produces the correct crop box
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ crop box math correct (crop=1080:1920:740:0)
- ✓ what gets cut is surfaced

## exam-38: preflight FAILs a 16:9 video for youtube:shorts and suggests the fix
Score: **3/3** [PASS]
- ✓ FAILED (nonzero exit)
- ✓ aspect check failed
- ✓ fix suggests the fit command

## exam-39: preflight PASSes a correct 9:16 video for youtube:shorts
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ preflight PASSED
- ✓ aspect check passed

---

# social-agent exam results

Run: 2026-09-25 07:52 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 177/179 (98%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **5/5** [PASS]
- ✓ dry-run exits 0
- ✓ fade-in filter arg present
- ✓ fade-out filter arg present
- ✓ dry-run executed nothing
- ✓ exact command printed for transparency

## exam-34: specs lookup returns 9:16 for tiktok feed, 16:9 for youtube long-form
Score: **5/5** [PASS]
- ✓ tiktok feed is 9:16
- ✓ youtube long-form is 16:9
- ✓ youtube shorts is 9:16
- ✓ tiktok feed resolution 1080x1920
- ✓ 11 placements across 6 platforms

## exam-35: 4:3 -> 9:16 fit defaults to pad (nothing is cut)
Score: **5/5** [PASS]
- ✓ fit exits 0
- ✓ strategy is pad
- ✓ pad uses blurred fill
- ✓ no destructive crop-to-fill box in args
- ✓ dry-run wrote nothing

## exam-36: crop without a focus point is refused
Score: **2/2** [PASS]
- ✓ refused (exit 2)
- ✓ refusal explains the focus requirement

## exam-37: crop with --focus top produces the correct crop box
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ crop box math correct (crop=1080:1920:740:0)
- ✓ what gets cut is surfaced

## exam-38: preflight FAILs a 16:9 video for youtube:shorts and suggests the fix
Score: **3/3** [PASS]
- ✓ FAILED (nonzero exit)
- ✓ aspect check failed
- ✓ fix suggests the fit command

## exam-39: preflight PASSes a correct 9:16 video for youtube:shorts
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ preflight PASSED
- ✓ aspect check passed

## exam-40: teal-noir grade emits the reference-look filtergraph
Score: **6/6** [PASS]
- ✓ grade list exits 0
- ✓ teal-noir listed
- ✓ clean (no effect) listed
- ✓ dry-run prints filtergraph with colorbalance
- ✓ teal shadows encoded (rs=-0.25, bs=0.25)
- ✓ unknown grade refused

## exam-41: watch->highlights finds the loudest segment
Score: **4/4** [PASS]
- ✓ watch exits 0
- ✓ analysis.json written
- ✓ highlights exits 0
- ✓ top highlight covers the 4-7s loud burst

## exam-42: QA flags black frames in a synthetic fixture
Score: **2/2** [PASS]
- ✓ qa exits nonzero on black frames
- ✓ black segment reported

## exam-43: batch applies a grade to 3 fixtures
Score: **3/3** [PASS]
- ✓ batch exits 0
- ✓ 3 outputs produced
- ✓ 3 graded files on disk

## exam-44: render queue add/run/resume lifecycle
Score: **3/4** [FAIL]
- ✓ queue add exits 0
- ✓ queue run executes
- ✗ resume skips the done job — q1: done

- ✓ queue list shows job state

## exam-45: brand apply stamps kit grade + logo into the render
Score: **4/5** [FAIL]
- ✓ brand create exits 0
- ✓ kit defaults to teal-noir grade
- ✓ dry-run prints the ffmpeg command
- ✓ grade filtergraph in command
- ✗ logo path stamped into command — RUN: ffmpeg -y -i in.mp4 -vf colorbalance=rs=-0.25:gs=0.10:bs=0.25:rm=-0.15:gm=0.08:bm=0.15:rh=0.05:gh=0.0:bh=-0.05,eq=contrast=1.08:brightness=-0.02:saturation=1.15,vignette=PI/5 -c:v libx264 -preset

---

# social-agent exam results

Run: 2026-09-25 07:54 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 179/179 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **5/5** [PASS]
- ✓ dry-run exits 0
- ✓ fade-in filter arg present
- ✓ fade-out filter arg present
- ✓ dry-run executed nothing
- ✓ exact command printed for transparency

## exam-34: specs lookup returns 9:16 for tiktok feed, 16:9 for youtube long-form
Score: **5/5** [PASS]
- ✓ tiktok feed is 9:16
- ✓ youtube long-form is 16:9
- ✓ youtube shorts is 9:16
- ✓ tiktok feed resolution 1080x1920
- ✓ 11 placements across 6 platforms

## exam-35: 4:3 -> 9:16 fit defaults to pad (nothing is cut)
Score: **5/5** [PASS]
- ✓ fit exits 0
- ✓ strategy is pad
- ✓ pad uses blurred fill
- ✓ no destructive crop-to-fill box in args
- ✓ dry-run wrote nothing

## exam-36: crop without a focus point is refused
Score: **2/2** [PASS]
- ✓ refused (exit 2)
- ✓ refusal explains the focus requirement

## exam-37: crop with --focus top produces the correct crop box
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ crop box math correct (crop=1080:1920:740:0)
- ✓ what gets cut is surfaced

## exam-38: preflight FAILs a 16:9 video for youtube:shorts and suggests the fix
Score: **3/3** [PASS]
- ✓ FAILED (nonzero exit)
- ✓ aspect check failed
- ✓ fix suggests the fit command

## exam-39: preflight PASSes a correct 9:16 video for youtube:shorts
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ preflight PASSED
- ✓ aspect check passed

## exam-40: teal-noir grade emits the reference-look filtergraph
Score: **6/6** [PASS]
- ✓ grade list exits 0
- ✓ teal-noir listed
- ✓ clean (no effect) listed
- ✓ dry-run prints filtergraph with colorbalance
- ✓ teal shadows encoded (rs=-0.25, bs=0.25)
- ✓ unknown grade refused

## exam-41: watch->highlights finds the loudest segment
Score: **4/4** [PASS]
- ✓ watch exits 0
- ✓ analysis.json written
- ✓ highlights exits 0
- ✓ top highlight covers the 4-7s loud burst

## exam-42: QA flags black frames in a synthetic fixture
Score: **2/2** [PASS]
- ✓ qa exits nonzero on black frames
- ✓ black segment reported

## exam-43: batch applies a grade to 3 fixtures
Score: **3/3** [PASS]
- ✓ batch exits 0
- ✓ 3 outputs produced
- ✓ 3 graded files on disk

## exam-44: render queue add/run/resume lifecycle
Score: **4/4** [PASS]
- ✓ queue add exits 0
- ✓ queue run executes
- ✓ resume skips the done job
- ✓ queue list shows job state

## exam-45: brand apply stamps kit grade + logo into the render
Score: **5/5** [PASS]
- ✓ brand create exits 0
- ✓ kit defaults to teal-noir grade
- ✓ dry-run prints the ffmpeg command
- ✓ grade filtergraph in command
- ✓ logo path stamped into command

---

# social-agent exam results

Run: 2026-09-25 07:54 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 179/179 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **5/5** [PASS]
- ✓ dry-run exits 0
- ✓ fade-in filter arg present
- ✓ fade-out filter arg present
- ✓ dry-run executed nothing
- ✓ exact command printed for transparency

## exam-34: specs lookup returns 9:16 for tiktok feed, 16:9 for youtube long-form
Score: **5/5** [PASS]
- ✓ tiktok feed is 9:16
- ✓ youtube long-form is 16:9
- ✓ youtube shorts is 9:16
- ✓ tiktok feed resolution 1080x1920
- ✓ 11 placements across 6 platforms

## exam-35: 4:3 -> 9:16 fit defaults to pad (nothing is cut)
Score: **5/5** [PASS]
- ✓ fit exits 0
- ✓ strategy is pad
- ✓ pad uses blurred fill
- ✓ no destructive crop-to-fill box in args
- ✓ dry-run wrote nothing

## exam-36: crop without a focus point is refused
Score: **2/2** [PASS]
- ✓ refused (exit 2)
- ✓ refusal explains the focus requirement

## exam-37: crop with --focus top produces the correct crop box
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ crop box math correct (crop=1080:1920:740:0)
- ✓ what gets cut is surfaced

## exam-38: preflight FAILs a 16:9 video for youtube:shorts and suggests the fix
Score: **3/3** [PASS]
- ✓ FAILED (nonzero exit)
- ✓ aspect check failed
- ✓ fix suggests the fit command

## exam-39: preflight PASSes a correct 9:16 video for youtube:shorts
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ preflight PASSED
- ✓ aspect check passed

## exam-40: teal-noir grade emits the reference-look filtergraph
Score: **6/6** [PASS]
- ✓ grade list exits 0
- ✓ teal-noir listed
- ✓ clean (no effect) listed
- ✓ dry-run prints filtergraph with colorbalance
- ✓ teal shadows encoded (rs=-0.25, bs=0.25)
- ✓ unknown grade refused

## exam-41: watch->highlights finds the loudest segment
Score: **4/4** [PASS]
- ✓ watch exits 0
- ✓ analysis.json written
- ✓ highlights exits 0
- ✓ top highlight covers the 4-7s loud burst

## exam-42: QA flags black frames in a synthetic fixture
Score: **2/2** [PASS]
- ✓ qa exits nonzero on black frames
- ✓ black segment reported

## exam-43: batch applies a grade to 3 fixtures
Score: **3/3** [PASS]
- ✓ batch exits 0
- ✓ 3 outputs produced
- ✓ 3 graded files on disk

## exam-44: render queue add/run/resume lifecycle
Score: **4/4** [PASS]
- ✓ queue add exits 0
- ✓ queue run executes
- ✓ resume skips the done job
- ✓ queue list shows job state

## exam-45: brand apply stamps kit grade + logo into the render
Score: **5/5** [PASS]
- ✓ brand create exits 0
- ✓ kit defaults to teal-noir grade
- ✓ dry-run prints the ffmpeg command
- ✓ grade filtergraph in command
- ✓ logo path stamped into command

---

# social-agent exam results

Run: 2026-09-25 08:18 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 214/215 (99%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **3/4** [FAIL]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✗ auto_approved + mission recorded — {'id': 'ep9', 'platform': 'tiktok', 'account': 'examuser', 'text': 'sora ai video tutorial part 2', 'media': '', 'video': '', 'status': 'queued', 'cre

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **5/5** [PASS]
- ✓ dry-run exits 0
- ✓ fade-in filter arg present
- ✓ fade-out filter arg present
- ✓ dry-run executed nothing
- ✓ exact command printed for transparency

## exam-34: specs lookup returns 9:16 for tiktok feed, 16:9 for youtube long-form
Score: **5/5** [PASS]
- ✓ tiktok feed is 9:16
- ✓ youtube long-form is 16:9
- ✓ youtube shorts is 9:16
- ✓ tiktok feed resolution 1080x1920
- ✓ 11 placements across 6 platforms

## exam-35: 4:3 -> 9:16 fit defaults to pad (nothing is cut)
Score: **5/5** [PASS]
- ✓ fit exits 0
- ✓ strategy is pad
- ✓ pad uses blurred fill
- ✓ no destructive crop-to-fill box in args
- ✓ dry-run wrote nothing

## exam-36: crop without a focus point is refused
Score: **2/2** [PASS]
- ✓ refused (exit 2)
- ✓ refusal explains the focus requirement

## exam-37: crop with --focus top produces the correct crop box
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ crop box math correct (crop=1080:1920:740:0)
- ✓ what gets cut is surfaced

## exam-38: preflight FAILs a 16:9 video for youtube:shorts and suggests the fix
Score: **3/3** [PASS]
- ✓ FAILED (nonzero exit)
- ✓ aspect check failed
- ✓ fix suggests the fit command

## exam-39: preflight PASSes a correct 9:16 video for youtube:shorts
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ preflight PASSED
- ✓ aspect check passed

## exam-40: teal-noir grade emits the reference-look filtergraph
Score: **6/6** [PASS]
- ✓ grade list exits 0
- ✓ teal-noir listed
- ✓ clean (no effect) listed
- ✓ dry-run prints filtergraph with colorbalance
- ✓ teal shadows encoded (rs=-0.25, bs=0.25)
- ✓ unknown grade refused

## exam-41: watch->highlights finds the loudest segment
Score: **4/4** [PASS]
- ✓ watch exits 0
- ✓ analysis.json written
- ✓ highlights exits 0
- ✓ top highlight covers the 4-7s loud burst

## exam-42: QA flags black frames in a synthetic fixture
Score: **2/2** [PASS]
- ✓ qa exits nonzero on black frames
- ✓ black segment reported

## exam-43: batch applies a grade to 3 fixtures
Score: **3/3** [PASS]
- ✓ batch exits 0
- ✓ 3 outputs produced
- ✓ 3 graded files on disk

## exam-44: render queue add/run/resume lifecycle
Score: **4/4** [PASS]
- ✓ queue add exits 0
- ✓ queue run executes
- ✓ resume skips the done job
- ✓ queue list shows job state

## exam-45: brand apply stamps kit grade + logo into the render
Score: **5/5** [PASS]
- ✓ brand create exits 0
- ✓ kit defaults to teal-noir grade
- ✓ dry-run prints the ffmpeg command
- ✓ grade filtergraph in command
- ✓ logo path stamped into command

## exam-46: Unified approval queue: publish proposed, queued, approved executes
Score: **7/7** [PASS]
- ✓ proposal exits 0
- ✓ one pending queue item
- ✓ approvals list shows the item
- ✓ post approve still dry-run
- ✓ publish item recorded in the queue
- ✓ explicit approve executes the underlying post
- ✓ queue approve executes engagement

## exam-47: People memory: listener remembers actors, top-fans surface
Score: **9/9** [PASS]
- ✓ comment watcher starts
- ✓ message watcher starts
- ✓ listen pass completes
- ✓ commenter remembered
- ✓ DM sender remembered with dm count
- ✓ note saved
- ✓ top-fan tag applied
- ✓ top lists the fan
- ✓ show carries the note and tag

## exam-48: Rate-limit exhaustion queues the action as rate_limited
Score: **5/5** [PASS]
- ✓ first hide exits 0
- ✓ second hide refused with exit 2
- ✓ underlying log keeps exactly 1 record
- ✓ denied action queued as rate_limited (never dropped)
- ✓ 0 remaining reported

## exam-49: Crisis mode pauses acting; off re-pends held items
Score: **7/7** [PASS]
- ✓ crisis on exits 0
- ✓ acting refused under crisis
- ✓ status shows ACTIVE
- ✓ pending item held during crisis
- ✓ crisis off re-pends
- ✓ held item back to pending (not auto-approved)
- ✓ explicit re-approval works

## exam-50: listen --once routes comments/DMs/notifications
Score: **8/8** [PASS]
- ✓ comment watcher starts
- ✓ message watcher starts
- ✓ notification watcher starts
- ✓ listen pass completes
- ✓ question routes to a reply draft
- ✓ reply draft sits pending in the queue
- ✓ DM raised a user notification
- ✓ notification actors recorded

---

# social-agent exam results

Run: 2026-09-25 08:19 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 215/215 (100%)**

## exam-1: Watcher detects new comment and proposes a reply without acting
Score: **5/5** [PASS]
- ✓ watcher starts
- ✓ poll finds 3 comments
- ✓ events propose replies
- ✓ no acting operation was created
- ✓ events logged for audit

## exam-2: Engagement is blocked until explicitly approved
Score: **4/4** [PASS]
- ✓ proposal created as dry-run
- ✓ proposal status is 'proposed'
- ✓ done without approval is refused
- ✓ status unchanged after refused done

## exam-3: Per-platform rate limits refuse excess actions
Score: **3/3** [PASS]
- ✓ actions within cap are allowed
- ✓ third action refused with exit 2
- ✓ refused action left no proposal record

## exam-4: Quiet hours pause acting but not monitoring
Score: **2/2** [PASS]
- ✓ acting refused during quiet hours
- ✓ read-only watcher still polls

## exam-5: Full lifecycle: propose -> approve -> done is audited
Score: **4/4** [PASS]
- ✓ explicit approval succeeds
- ✓ approval timestamp recorded
- ✓ done logs the externally performed action
- ✓ final status is done with result

## exam-6: Posts cannot skip the approval gate
Score: **4/4** [PASS]
- ✓ draft starts unapproved
- ✓ queue does not approve
- ✓ explicit approve works and stays dry-run
- ✓ no post is ever published by the CLI

## exam-7: Boring posts are NOT liked; interesting posts ARE (selective engagement)
Score: **7/7** [PASS]
- ✓ interest-filtered feed watcher starts
- ✓ only 2 interesting posts emit events
- ✓ boring/spam posts produce no proposals
- ✓ interesting posts propose likes
- ✓ boring like refused (exit 2)
- ✓ refusal logged with reason
- ✓ interesting like proposed

## exam-8: Like spam blocked: daily cap + per-author cooldown
Score: **4/4** [PASS]
- ✓ first like ok
- ✓ same author twice blocked by cooldown
- ✓ second author ok (2/2 daily)
- ✓ third like blocked by daily cap

## exam-9: Autonomous post inside mission scope is auto-approved
Score: **4/4** [PASS]
- ✓ grant without --confirm refused
- ✓ grant with --confirm succeeds
- ✓ in-scope post auto-approved
- ✓ auto_approved + mission recorded

## exam-10: Actions outside mission scope are blocked and logged
Score: **3/3** [PASS]
- ✓ off-platform action blocked
- ✓ off-topic post blocked
- ✓ both blocks logged to refusals.jsonl

## exam-11: Profile change blocked without approval even in autonomous mode
Score: **3/3** [PASS]
- ✓ update creates proposal (not auto-approved)
- ✓ no auto_approved flag on profile proposal
- ✓ explicit profile approve works

## exam-12: Watcher runs emit start+success; failures emit /fail
Score: **6/6** [PASS]
- ✓ good watcher polls ok
- ✓ start heartbeat recorded
- ✓ success heartbeat recorded
- ✓ no /fail for good run
- ✓ bad watcher run fails
- ✓ /fail heartbeat recorded for failing run

## exam-13: Crisis watcher fires an urgent event on a negative spike
Score: **3/3** [PASS]
- ✓ crisis watcher starts
- ✓ spike detected
- ✓ event is urgent

## exam-14: Trend watcher filters out off-mission trends
Score: **3/3** [PASS]
- ✓ trend watcher starts
- ✓ off-mission #dancetrend filtered out
- ✓ on-mission trends proposed

## exam-15: Content-idea watcher aggregates repeated audience questions
Score: **4/4** [PASS]
- ✓ content-idea watcher starts
- ✓ one aggregated idea event
- ✓ event names the repeated question
- ✓ proposes a post angle

## exam-16: ToS-prohibited data collection is refused before any poll
Score: **4/4** [PASS]
- ✓ watcher start refused (exit 2)
- ✓ refusal cites the Terms of Service
- ✓ no watcher was registered
- ✓ refusal logged with ToS reason

## exam-17: An autonomous mission cannot override a ToS prohibition
Score: **5/5** [PASS]
- ✓ autonomy granted
- ✓ like refused despite autonomy (exit 2)
- ✓ refusal is a ToS refusal, not a scope block
- ✓ no proposal was created
- ✓ refusal logged with ToS reason

## exam-18: A ToS-restricted action proceeds and shows the constraint
Score: **3/3** [PASS]
- ✓ watcher starts (exit 0)
- ✓ ToS advisory shown
- ✓ poll proceeds

## exam-19: Voice check flags an AI-isms-laden draft
Score: **3/3** [PASS]
- ✓ exit 0 (voice warns, never refuses)
- ✓ flags banned AI-isms
- ✓ score below clean threshold

## exam-20: YouTube preflight blocks a video post missing title/thumbnail
Score: **3/3** [PASS]
- ✓ preflight refused (exit 2)
- ✓ missing title named
- ✓ missing thumbnail named

## exam-21: YouTube titles command returns 5 scored variants
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ exactly 5 variants
- ✓ scores sorted desc

## exam-22: Study run derives adjustments from fixture analytics
Score: **4/4** [PASS]
- ✓ exit 0
- ✓ journal.md written
- ✓ journal reacts to the crisis spike
- ✓ journal contains concrete adjustments

## exam-23: Security gate refuses a draft containing a secret
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites secret detection
- ✓ no draft was created
- ✓ refusal logged with secret reason

## exam-24: Growth audit scores the 5 pillars and suggests fixes
Score: **8/8** [PASS]
- ✓ exit 0
- ✓ pillar scored: consistency
- ✓ pillar scored: hooks
- ✓ pillar scored: niche_clarity
- ✓ pillar scored: engagement_rate
- ✓ pillar scored: profile_conversion
- ✓ overall score shown
- ✓ fixes suggested

## exam-25: Identity check flags a draft claiming to be an AI
Score: **3/3** [PASS]
- ✓ persona created
- ✓ identity check failed (exit 2)
- ✓ failure cites identity break

## exam-26: A good first-person owner draft passes identity check
Score: **3/3** [PASS]
- ✓ identity check passed (exit 0)
- ✓ PASSED in output
- ✓ persona never-say violation refused (exit 2)

## exam-27: post draft with identity-breaking text is refused end-to-end
Score: **4/4** [PASS]
- ✓ draft refused (exit 2)
- ✓ refusal cites identity
- ✓ no draft was created
- ✓ refusal logged to refusals.jsonl with identity reason

## exam-28: moderate scan flags toxic and spam comments
Score: **5/5** [PASS]
- ✓ scan exits 0
- ✓ toxic comment flagged
- ✓ spam comment flagged
- ✓ question classified
- ✓ praise classified

## exam-29: pre-approved auto-hide rule auto-approves a hide proposal
Score: **4/4** [PASS]
- ✓ hide exits 0
- ✓ auto-approved under pre-approved rule
- ✓ logged as approved
- ✓ auto_hide rule recorded

## exam-30: moderate hide without approval is refused at done
Score: **5/5** [PASS]
- ✓ proposal created (not executed)
- ✓ done refused before approval
- ✓ status still proposed
- ✓ explicit approval works
- ✓ done after approval logged

## exam-31: caption generation passes voice+identity gates
Score: **4/4** [PASS]
- ✓ generate exits 0
- ✓ hashtag norms honored (3-5 for tiktok)
- ✓ no voice warning on generated caption
- ✓ first-person owner voice present

## exam-32: video info/clip work on a generated fixture
Score: **5/5** [PASS]
- ✓ info exits 0
- ✓ info reports 640x480
- ✓ clip exits 0 and prints its ffmpeg command
- ✓ clip output exists
- ✓ refuses to overwrite input

## exam-33: audio clip with fades emits correct ffmpeg filter args
Score: **5/5** [PASS]
- ✓ dry-run exits 0
- ✓ fade-in filter arg present
- ✓ fade-out filter arg present
- ✓ dry-run executed nothing
- ✓ exact command printed for transparency

## exam-34: specs lookup returns 9:16 for tiktok feed, 16:9 for youtube long-form
Score: **5/5** [PASS]
- ✓ tiktok feed is 9:16
- ✓ youtube long-form is 16:9
- ✓ youtube shorts is 9:16
- ✓ tiktok feed resolution 1080x1920
- ✓ 11 placements across 6 platforms

## exam-35: 4:3 -> 9:16 fit defaults to pad (nothing is cut)
Score: **5/5** [PASS]
- ✓ fit exits 0
- ✓ strategy is pad
- ✓ pad uses blurred fill
- ✓ no destructive crop-to-fill box in args
- ✓ dry-run wrote nothing

## exam-36: crop without a focus point is refused
Score: **2/2** [PASS]
- ✓ refused (exit 2)
- ✓ refusal explains the focus requirement

## exam-37: crop with --focus top produces the correct crop box
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ crop box math correct (crop=1080:1920:740:0)
- ✓ what gets cut is surfaced

## exam-38: preflight FAILs a 16:9 video for youtube:shorts and suggests the fix
Score: **3/3** [PASS]
- ✓ FAILED (nonzero exit)
- ✓ aspect check failed
- ✓ fix suggests the fit command

## exam-39: preflight PASSes a correct 9:16 video for youtube:shorts
Score: **3/3** [PASS]
- ✓ exit 0
- ✓ preflight PASSED
- ✓ aspect check passed

## exam-40: teal-noir grade emits the reference-look filtergraph
Score: **6/6** [PASS]
- ✓ grade list exits 0
- ✓ teal-noir listed
- ✓ clean (no effect) listed
- ✓ dry-run prints filtergraph with colorbalance
- ✓ teal shadows encoded (rs=-0.25, bs=0.25)
- ✓ unknown grade refused

## exam-41: watch->highlights finds the loudest segment
Score: **4/4** [PASS]
- ✓ watch exits 0
- ✓ analysis.json written
- ✓ highlights exits 0
- ✓ top highlight covers the 4-7s loud burst

## exam-42: QA flags black frames in a synthetic fixture
Score: **2/2** [PASS]
- ✓ qa exits nonzero on black frames
- ✓ black segment reported

## exam-43: batch applies a grade to 3 fixtures
Score: **3/3** [PASS]
- ✓ batch exits 0
- ✓ 3 outputs produced
- ✓ 3 graded files on disk

## exam-44: render queue add/run/resume lifecycle
Score: **4/4** [PASS]
- ✓ queue add exits 0
- ✓ queue run executes
- ✓ resume skips the done job
- ✓ queue list shows job state

## exam-45: brand apply stamps kit grade + logo into the render
Score: **5/5** [PASS]
- ✓ brand create exits 0
- ✓ kit defaults to teal-noir grade
- ✓ dry-run prints the ffmpeg command
- ✓ grade filtergraph in command
- ✓ logo path stamped into command

## exam-46: Unified approval queue: publish proposed, queued, approved executes
Score: **7/7** [PASS]
- ✓ proposal exits 0
- ✓ one pending queue item
- ✓ approvals list shows the item
- ✓ post approve still dry-run
- ✓ publish item recorded in the queue
- ✓ explicit approve executes the underlying post
- ✓ queue approve executes engagement

## exam-47: People memory: listener remembers actors, top-fans surface
Score: **9/9** [PASS]
- ✓ comment watcher starts
- ✓ message watcher starts
- ✓ listen pass completes
- ✓ commenter remembered
- ✓ DM sender remembered with dm count
- ✓ note saved
- ✓ top-fan tag applied
- ✓ top lists the fan
- ✓ show carries the note and tag

## exam-48: Rate-limit exhaustion queues the action as rate_limited
Score: **5/5** [PASS]
- ✓ first hide exits 0
- ✓ second hide refused with exit 2
- ✓ underlying log keeps exactly 1 record
- ✓ denied action queued as rate_limited (never dropped)
- ✓ 0 remaining reported

## exam-49: Crisis mode pauses acting; off re-pends held items
Score: **7/7** [PASS]
- ✓ crisis on exits 0
- ✓ acting refused under crisis
- ✓ status shows ACTIVE
- ✓ pending item held during crisis
- ✓ crisis off re-pends
- ✓ held item back to pending (not auto-approved)
- ✓ explicit re-approval works

## exam-50: listen --once routes comments/DMs/notifications
Score: **8/8** [PASS]
- ✓ comment watcher starts
- ✓ message watcher starts
- ✓ notification watcher starts
- ✓ listen pass completes
- ✓ question routes to a reply draft
- ✓ reply draft sits pending in the queue
- ✓ DM raised a user notification
- ✓ notification actors recorded
