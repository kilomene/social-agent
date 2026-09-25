# audio/MUSIC.md — licensing rules for audio

`social-agent audio` clips, loops, mixes, and normalizes audio **you provide**.
It never sources, downloads, or searches for music itself.

## The rule

- **Platform-licensed libraries first.** TikTok's Commercial Music Library,
  YouTube's Audio Library, Instagram/Facebook's licensed catalog, and
  royalty-free libraries (Epidemic Sound, Artlist, Uppbeat with a valid
  license) are the safe sources for background music.
- **Your own audio is always safe.** Voiceovers you record, beats you make,
  and anything you hold the rights to can be clipped/mixed freely.
- **No copyrighted commercial music** pulled from the open web. Clipping a
  15-second chunk off a chart single does not make it fair use on TikTok or
  YouTube — Content ID / rights-holder takedowns will still hit the post.

## What the tool does (and doesn't do)

- `audio clip/loop/mix/extract/normalize` operate on local files you point
  at with `--input`. There is no search, no download, no "find me a track"
  step — by design.
- If you need a track, get it from a licensed library first, save it
  locally, then run the audio commands on it.

## Loudness norms (documented values)

- Short-form (TikTok/Reels/Shorts): **-14 LUFS** integrated, -1.5 dBTP
  (`audio normalize --preset tiktok`).
- YouTube long-form: **-14 LUFS** (`--preset youtube`).
- Spoken word / podcast: **-16 LUFS** (`--preset podcast`).
