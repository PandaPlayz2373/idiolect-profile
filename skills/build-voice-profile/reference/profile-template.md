# Template for the generated profile

Write `draft/SKILL.md` in this shape. Replace everything in <angle brackets>. Keep the headings. Cut any
section that the data doesn't support rather than padding it. Write the profile itself plainly: short rules,
real numbers, their exact words in quotes.

````markdown
---
name: sound-like-<slug>
description: <Name>'s idiolect profile - how <Name> <types / talks / writes: list the registers you have>, measured from their own words. Use whenever writing anything <Name> will send, post, say, submit or sign as themselves - <the concrete things they actually produce, from the samples: texts, DMs, emails to clients, captions, reel scripts, essays, cover letters, bios, replies...> - and whenever they ask for something "in my voice", "like me", "the way I'd say it", "sound like me", "less AI" or "more human". Pick the register first, then follow it.
---

# How <Name> sounds

Built <YYYY-MM-DD> from <N> pieces of <Name>'s own words: <counts per source, e.g. "1,840 messages typed to
Claude Code, 212 dictated, 64 sent emails, 9 essays">. Verbatim examples: [examples.md](examples.md).
Check a draft: `python3 lint.py draft.txt --register <register>` (in this folder). Rebuild: [refresh.md](refresh.md).

This is for writing **as** <Name>. It does not change how Claude talks to <Name> in chat.

Who they are, for content (only what their own words show; no guesses): <2-4 lines: what they do, what
they're building or studying, the people and places that come up, what they care about and talk about>.

## Step 1: pick the register

| They'd be... | Register | Use for |
|---|---|---|
| <typing fast to someone they know> | **A. <label>** | <texts, DMs, Discord, quick notes> |
| <...> | **B. <label>** | <...> |

If it's unclear, don't ask: <default rule, e.g. "anything posted gets D, anything spoken gets B, school work gets C">.

## Rules for every register

- <Their punctuation hard rules from the numbers, e.g. "No em dashes. They use 0 per 1,000 words.">
- Never write these (they don't use them, and they read as AI): <the never-used AI tells that matter most,
  comma-separated; the full list is in profile.json and lint.py checks all of them>.
- <How they reason / explain: "says why: 'because...', 'so then...'"; how concrete they are; what kind of
  details they use; what they do with repetition>.
- <Anything else that holds across every register, from the samples.>
- Facts must be their real ones. Don't invent stories, numbers, quotes, people or results. If a piece needs a
  fact you don't have, leave a [bracket] for them to fill.

## A. <label>

<6-12 bullets. Each one specific and checkable. Cover, where the data shows it:>
- Shape: <median length, how long ones get, one line vs several, how a long message is organized>.
- Case and punctuation: <"starts lowercase ~9 in 10", "no full stop at the end 2 in 3", apostrophes kept or
  dropped ("dont, im, thats"), lowercase "i", periods as pauses mid-thought, commas, line breaks between asks>.
- Openers they really use: <"can you", "so i", "is there a way", with rough shares>.
- Glue and hedge words: <"like", "basically", "kind of", "or something like that", with rates>.
- How they check they were understood / sign off: <"make sense?", "you see what i'm saying?">.
- Emotion: <excited = ALL CAPS + "!!!"; annoyed = short and blunt; how they praise>.
- Typos they really make (typed registers only): <list>. <How often: "about one every N words; use 1-3 in a
  short message, never on every word, never in names">.
- Short replies are normal: <"yes", "go", "i like 2">.
- Never: <things they never do here>.

## B. <label>
<same treatment; spoken registers: run-ons, "and then", self-corrections mid-sentence ("or I mean"), filler words
(keep "um/uh" only for transcripts, drop them for scripts), how they end; writing registers: their transition
phrases, paragraph shape, how formal, citation style, how they hedge, headings/format they use>

## Context changes the voice
<Only if the samples show it: to clients vs friends vs teachers vs AI; one project vs another; how the same
person shifts. Delete this section if nothing shows up.>

## Corrections from <Name>
<Quoted feedback from the check step, newest first, with the date. These outrank everything above. On a refresh,
keep every entry.>

## Before you hand it over

1. Read it as if <Name> said it out loud. Anything they'd never say (big words, slogans, "furthermore") goes.
2. Run `python3 lint.py <file> --register <register>`. Fix every HARD line. Fix soft lines unless you have a
   reason from the samples.
3. The register's habits should be present but not overdone: a few per piece, never one per sentence. A
   parody is as wrong as a polished AI draft.
4. Check every fact is theirs. No invented stories, numbers or people.
````

`draft/examples.md`:

````markdown
# Verbatim examples (their words, unedited)

Use these to calibrate, not to copy. Typos are theirs. Personal details are masked.

## A. <label>
> <6-12 real messages that show the register's habits best: some short, some long, at least one where they
> explain something, one where they react, one where they ask for something. Use `/` to join separate lines
> of one message if needed.>

## B. <label>
> <...>
````

Choosing examples: pick the ones a friend would read and say "that's so them". Skip ones with private details
the masking missed (addresses, other people's personal matters, money, health); pick another.
