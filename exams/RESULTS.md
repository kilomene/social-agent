# social-agent exam results

Run: 2026-09-25 07:02 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 59/59 (100%)**

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
