---
name: character-consistency
description: Use this skill whenever a user is generating a multi-scene, multi-clip, or long-form AI video (any platform — Sora, Kling, Veo/Flow, Runway, Pika, etc.) and wants the same character(s) to look, sound, and act the same across every scene. Trigger this for requests like "keep the character consistent," "same face every scene," "don't let the character change," "15-minute video with one character," building a short film/series with AI video tools, or any multi-clip generation project where identity drift across cuts would be a problem. This skill has no API or model access — it works purely through disciplined reference-passing, a persistent character bible, and self-review of each generated clip against that bible.
---

# Character Consistency Workflow

## What this skill actually does (read this first)

This skill cannot force any video generation platform to internally guarantee facial
or vocal consistency — no skill can, because platforms like Sora, Veo/Flow, Kling, and
Runway don't expose a "lock this face" API to external instructions. What this skill
*can* do reliably:

1. Force disciplined creation and reuse of a **character bible** — a single source of
   truth for every visual, vocal, and behavioral trait of each character.
2. Force every single generation call to re-inject the relevant parts of that bible,
   instead of relying on the model's memory of "the character from 3 scenes ago."
3. Force a **self-review pass** after every generated clip, comparing it against the
   bible and either accepting it or regenerating it with corrective instructions.
4. Track continuity state that changes over time on purpose (aging, wardrobe changes,
   injuries, hairstyle changes) so those changes happen deliberately and consistently,
   not accidentally.

Treat this as a strict discipline/checklist system, not a technical guarantee. Tell the
user this plainly if they expect pixel-perfect identity locking — that requires
platform-level reference conditioning (e.g. image-to-video with a fixed face image,
LoRA training, or a voice-cloning tool), which is a different, heavier workflow than an
instruction skill.

## Before anything else: check current platform capabilities

Most major AI video platforms now ship native reference-image or character-lock
features (Sora's reference system, Veo's Ingredients-to-Video, Kling's Elements 3.0,
Seedance's multi-reference input, etc.), and these change often. Read
`references/platform-notes.md` and re-verify with a web search if it's been a while —
whichever platform the user is on, use its native reference/character-lock feature as
the *primary* consistency mechanism, and treat everything below (the Identity Block,
self-review checklist) as the backup layer that also covers what image references
can't: voice, personality, and speech patterns.

## When to use this

- Multi-scene or multi-clip AI video projects (shorts, films, series, ads) where one or
  more named characters must look and sound the same throughout
- Any time the user says the character's face, voice, or personality is "changing,"
  "drifting," or "not matching" between scenes
- Before generating scene 2+ of a project — always check whether a character bible
  already exists for this project first

## Step 1 — Build the Character Bible (before generating anything)

Never start generating scenes until this file exists. If the user already has one
(check the project folder for `character-bible.md`), load and use it instead of asking
again.

For each character, capture and write down, in plain unambiguous language (this
becomes a prompt block reused verbatim in every scene):

**Face & body (must be exact-repeatable, not vibes)**
- Age, apparent ethnicity/build, exact hair color/length/style, eye color, skin tone,
  distinguishing marks (scars, freckles, facial hair style)
- Height/build description
- A reference image set if the user has one (ask for 3-5 images from different
  angles/lighting if they don't) — even though this skill has no embedding-comparison
  tool, the reference images should still be attached/described in every generation
  prompt where the platform supports image references

**Voice**
- Pitch (low/medium/high), pace (slow/measured/fast/clipped), accent/region, tone
  quality (raspy, warm, nasal, breathy), any verbal tics or speech patterns
- If using a voice cloning tool separately, note the sample file name/location here

**Personality & speech patterns**
- 3-5 core personality traits
- How they speak: sentence length, vocabulary level, catchphrases, formality
- Emotional baseline (e.g. "guarded, rarely shows enthusiasm openly")

**Aging & change rules (only if the story requires change over time)**
- Explicit rule for what changes and when, e.g. "ages 10 years at scene 40; hair
  goes from black to grey specifically at that point, not gradually"
- Explicit rule for what must NOT change unless the story calls for it (default:
  everything else stays locked)

Write all of this into `character-bible.md` in the project folder. See
`references/character-bible-template.md` for the exact template to fill in.

## Step 2 — Build the reusable Identity Block

From the bible, compile a compact paragraph per character (100-150 words) that gets
pasted at the start of **every single scene prompt**, unmodified except for the
deliberate aging/wardrobe rules from Step 1. This is the single highest-leverage habit
in this whole skill — most drift happens because people paraphrase the character
description differently each time. Never paraphrase it. Copy-paste it exactly.

Example structure:
```
[CHARACTER: Maren] Woman, 34, light olive skin, shoulder-length dark brown wavy hair,
brown eyes, small scar above left eyebrow, average build, 5'6". Wears a faded green
field jacket unless scene notes say otherwise. Speaks in short, clipped sentences,
low measured voice, slight Midwestern accent, rarely raises her voice even when angry.
[REFERENCE IMAGES ATTACHED: maren_front.jpg, maren_side.jpg, maren_3quarter.jpg]
```

## Step 3 — Generate scene by scene

For each scene/clip on whichever platform the user is using:
1. Paste the unmodified Identity Block for every character appearing in the scene
2. Add only the scene-specific action/setting/dialogue on top
3. If the platform accepts reference images (image-to-video, character reference
   upload, etc.), always attach the same reference image set every time — check
   `references/platform-notes.md` for what each major platform currently supports,
   and re-verify via web search if it's been a while, since these platforms update
   their reference-image features often
4. Generate the clip

## Step 4 — Self-review pass (do this after every clip, not just at the end)

Before accepting a clip into the final cut, manually compare it against the bible:
- [ ] Face shape, hair, eye color, skin tone match the bible
- [ ] Any scars/marks present and in the right place
- [ ] Voice pitch/accent/pace matches (if audio is present)
- [ ] Wardrobe matches unless a deliberate change was scripted for this scene
- [ ] Personality/speech pattern in any dialogue matches the bible
- [ ] Any aging/change is exactly per the aging rule, not accidental drift

If a clip fails any check: do not patch it with a note like "close enough." Regenerate
with more explicit corrective language pointing at exactly what drifted (e.g. "hair
was blonde in the last clip, must be dark brown per bible, regenerate with hair color
locked to dark brown").

Log every accepted/rejected clip in `continuity-log.md` (see
`references/continuity-log-template.md`) so a 15-minute, 20+ scene project has a
running record instead of relying on memory of what happened 10 scenes ago.

## Step 5 — Voice consistency (if using separate voice generation/cloning)

If the platform generates voice separately from video (or the user is layering in a
voice-cloning tool):
- Use the exact same voice sample/model for every clip — never regenerate or
  re-describe the voice from scratch each time
- Keep pace/pitch/emotional-register notes from the bible attached to every voice
  generation call, the same way the Identity Block is reused for video

## Common failure modes to actively guard against

- **Paraphrasing the character description differently each scene** — the #1 cause of
  drift. Always copy-paste the Identity Block verbatim.
- **Letting "the story needs them older/injured/different clothes" bleed into scenes
  where it shouldn't** — only apply bible-scripted changes at the exact scene they're
  scripted for.
- **Accepting a "close enough" clip to save time** — this compounds; a slightly-off
  face in scene 3 becomes the new unintentional baseline by scene 8 if not caught.
- **Switching reference images between scenes** — always use the same reference set.
- **Forgetting to check platform capabilities** — reference-image support changes
  often across these platforms; verify current capabilities with a quick search rather
  than assuming what the platform supported last time this skill was used.
