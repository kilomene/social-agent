# Character Consistency Workflow (Agent Skill)

An installable **agent skill** that keeps a character's face, voice, and personality
consistent across every scene of a multi-clip AI video project — regardless of which
AI video generation platform you're using (Sora, Veo/Flow, Kling, Runway, Seedance,
Pika, etc.).

This is **not** software you run. It's a `SKILL.md` instruction package that an
agentic AI system (Claude, or any agent that supports the same skill format) reads and
follows step-by-step while it helps you generate your video, scene by scene.

## The problem this solves

AI-generated video clips are usually produced one scene at a time. Without a
disciplined process, the "same" character's face, voice, and personality drift
between clips — different face shape, different voice, inconsistent aging or
wardrobe — because each generation call has no memory of exactly how the character
was described last time.

## What this skill actually does

- Forces creation of a **character bible**: one file that locks down every visual,
  vocal, and personality trait of each character before any generation starts
- Compiles that bible into a **reusable Identity Block** — a fixed paragraph pasted
  verbatim into every scene prompt, so the character is never re-described from
  scratch or paraphrased differently each time
- Runs a **self-review checklist** after every generated clip, comparing it against
  the bible and flagging exactly what to fix if something drifted
- Tracks intentional changes (aging, wardrobe, injuries) in a **continuity log** so a
  20+ scene project doesn't rely on memory
- Points to each platform's **native reference-image / character-lock features**
  (Sora's reference system, Veo's Ingredients-to-Video, Kling's Elements 3.0,
  Seedance's multi-reference input, etc.) as the primary consistency mechanism where
  available, with this skill's process as the backup layer — especially for voice and
  personality, which reference images can't cover

## What this skill does *not* do

Be clear-eyed about this: no instruction skill can force a closed AI video platform to
internally guarantee facial or vocal identity across separate generation calls. This
skill can't call face-embedding or voice-embedding comparison tools — it works purely
through disciplined reference-passing and manual/agent-driven self-review, not
programmatic verification. If you need a hard technical guarantee, you'd want a
different, heavier pipeline (e.g. LoRA training per character, embedding-based face
similarity scoring, voice cloning with a fixed model) — this skill is the
lightweight, install-anywhere version of that discipline.

## Installation

### For Claude (claude.ai, Claude Code, Cowork)
1. Download `character-consistency.skill` from the [Releases](../../releases) page
   or this repo
2. Upload/attach it wherever your Claude client supports installing a `.skill` file
   (the file card will show a **Save skill** button)

### For other agents that support the same skill format
1. Clone or download this repo
2. Point your agent's skill-loading mechanism at the `character-consistency/` folder
   (containing `SKILL.md` and `references/`)
3. Confirm your agent's runtime supports the same three-file structure — see
   [Repo structure](#repo-structure) below

### Manual / no skill-loader available
You can also just paste the contents of `SKILL.md` directly into your conversation
with any capable AI agent and say "follow this workflow for my video project" — the
skill is plain-language instructions, not code, so it works even without formal
skill-loading support.

## Usage

Once installed, just start your video project normally and mention you want
consistent characters across scenes — e.g.:

> "I'm making a 15-minute short film with Kling. I need the main character's face and
> voice to stay exactly consistent across all 20 scenes."

The agent will:
1. Ask you for character details (or extract them from what you've already described)
   and build `character-bible.md`
2. Compile the reusable Identity Block
3. Check current reference-image support for your chosen platform
4. Walk through scene-by-scene generation, reusing the Identity Block every time
5. Self-review each clip against the bible before you move to the next scene
6. Keep a running `continuity-log.md` for the whole project

## Repo structure

```
character-consistency/
├── SKILL.md                              # Main workflow instructions (read first)
└── references/
    ├── character-bible-template.md       # Fillable template for character traits
    ├── continuity-log-template.md        # Per-scene tracking table
    └── platform-notes.md                 # Current platform reference-image support
```

## Keeping platform-notes.md current

AI video platforms change their reference-image and character-consistency features
often. `references/platform-notes.md` reflects what was true as of when this skill
was last updated (see file header for date). Pull requests updating it — or opening
an issue when a platform ships a relevant new feature — are welcome.

## Contributing

Issues and PRs welcome, especially:
- Updates to `platform-notes.md` as platforms ship new features
- Additional failure modes / troubleshooting notes based on real usage
- Improvements to the self-review checklist

## License

MIT — see [LICENSE](LICENSE).
