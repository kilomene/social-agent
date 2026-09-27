# Contributing

Thanks for considering a contribution. This is a small, instruction-based skill, so
contributions are lightweight — mostly markdown edits, not code.

## Most useful contributions

1. **`references/platform-notes.md` updates** — this is the file most likely to go
   stale. If a platform (Sora, Veo, Kling, Runway, Seedance, Pika, etc.) ships a new
   or changed reference-image/character-consistency feature, please open a PR or
   issue with:
   - Platform name and feature name
   - What it does (one or two sentences)
   - A source link (official docs preferred)

2. **New failure modes** — if you hit a specific type of character drift not covered
   in the "Common failure modes" section of `SKILL.md`, add it with a short
   description of the symptom and the fix that worked.

3. **Additional worked examples** — a new file under `examples/` showing a filled-in
   character bible for a different genre/style is welcome.

## Guidelines

- Keep `SKILL.md` itself under ~500 lines. If it's growing past that, propose
  splitting new content into a `references/` file instead, with a pointer from
  `SKILL.md`.
- No code dependencies, please — this skill is intentionally plain-instruction only,
  with no API or model calls of its own. If you want to propose a heavier,
  code-based variant (e.g. one that does call face-embedding comparison), that's a
  good candidate for a separate skill/repo rather than folding it into this one.
- Match the existing tone: direct, and honest about what the workflow can and can't
  guarantee. Avoid language that overpromises technical certainty this skill doesn't
  have.

## Testing a change

Since this is instructions, not code, "testing" means running the workflow with an
agent against a real (or toy) multi-scene project and checking whether the agent
follows the steps correctly. If you're using Claude's skill-creator tooling, you can
run its eval loop against this skill — see that tool's own documentation for how.

## Reporting issues

Open a GitHub issue. Include:
- Which agent/platform you were using
- What step of the workflow didn't behave as expected
- What you expected instead
