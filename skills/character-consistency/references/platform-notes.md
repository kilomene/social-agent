# Platform Reference-Conditioning Notes

Last checked: September 2026. **These features change fast — re-verify with a web
search before relying on this table for a new project**, since every major platform
has shipped or reshuffled reference-image/character features multiple times in the
last year, and some platforms shut down entirely (see Sora note below).

| Platform | Reference-image / character-lock feature | Notes |
|---|---|---|
| OpenAI Sora | "Reference system" — upload one or more images to condition generation | Sora's public app and API access have an announced shutdown timeline; confirm current availability before planning a project around it |
| Google Veo (3.1) | "Ingredients to Video" + reference images + start/end frame control | Also supports extending existing clips, which helps continuity within one continuous generation rather than across separate calls |
| Kling (3.0) | "Elements 3.0" character-consistency system + multi-shot "AI Director" (2-6 coherent shots per generation) | Multi-shot mode is useful: it keeps a character consistent *within* one generated sequence, reducing how often you need cross-clip stitching |
| ByteDance Seedance 2.0 | Accepts up to ~12 mixed reference inputs (images, video clips, audio) | Marketed specifically for multi-shot/multi-angle character consistency |
| Runway (Gen-4 era) | Reference-image conditioning | Check current docs; Runway iterates quickly |

## How this affects the skill's workflow

Where a platform supports native reference-image or character-lock features (most
now do, as of this writing), **always use that platform feature as the primary
mechanism**, and treat the Identity Block (Step 2 in SKILL.md) as the backup/
supplementary layer, not the only layer. The text-based Identity Block matters most on:
- Platforms/modes without reference-image support
- The personality/speech/voice traits that reference images can't convey
- As a written checklist for the Step 4 self-review, regardless of platform

Where a platform supports multi-shot generation that keeps one character consistent
across several shots in a single call (e.g. Kling's AI Director), prefer generating
runs of scenes in one multi-shot call over many separate single-shot calls — every
new separate call is a new opportunity for drift.

## Before starting a new project

Run a quick search for "[platform name] character consistency reference image 2026"
or check the platform's current docs, since capabilities shift often enough that
information here can go stale within months.
