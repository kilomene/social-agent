# social-agent exam results

Run: 2026-09-25 06:51 UTC — all exams execute the real CLI against isolated state dirs.

**Total: 22/22 (100%)**

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
