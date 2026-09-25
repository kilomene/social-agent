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
