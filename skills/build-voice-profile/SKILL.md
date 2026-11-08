---
name: build-voice-profile
description: Builds (or refreshes) the user's idiolect profile - a personal skill that makes Claude write exactly the way they type, talk and write in each context, measured from their own words in their Claude Code / Codex history plus any exports, documents or transcripts they add. Use when the user asks to "build my voice profile", "make my idiolect profile", "learn how I talk / write / type", "make Claude sound like me", "stop sounding like AI when you write as me", "refresh / update my voice profile", or wants a voice profile for someone else from files they provide.
---

# Build a voice profile

You are building a personal skill that lets any future Claude session write as this person so closely that
the people who know them can't tell. The skill you produce lives at `~/.claude/skills/sound-like-<slug>/` and
loads itself whenever they need something in their voice.

The rule that matters most: **every claim in the profile must come from their real words.** Numbers come from
the scripts; phrases, habits and examples come from reading their samples. Never fill gaps with what people
"usually" sound like. A thin, true profile beats a full, invented one.

Scripts are in `scripts/` next to this file. Use `python3` (on Windows: `python`). They are stdlib-only and
never send anything anywhere. Run them with the full path to this skill's folder.

## 0. Set up (one message, then go)

Tell the user in two or three lines what will happen: you'll read their own past messages on this machine
(Claude Code and Codex history), measure how they write, read a sample, and write the profile; secrets, emails,
phone numbers, links and file paths are masked automatically; the private working files stay in
`~/.claude/idiolect/<slug>/`.

Work out without asking:
- **Name**: from how they sign things or refer to themselves in their history, `git config user.name`, or the
  OS user. `slug` = lowercase first name (`sound-like-jordan`). If two people could be meant, ask.
- **Refresh vs new**: if `~/.claude/skills/sound-like-<slug>/` exists, this is a refresh. Read the current
  SKILL.md first and keep its "Corrections from <Name>" section word for word.

Then ask ONE question (AskUserQuestion if you have it, multi-select) about extra sources. More registers come
from more kinds of writing, so offer what they likely have:
- claude.ai export (Settings > Privacy > Export data) - `conversations.json` or the zip
- ChatGPT export (Settings > Data controls > Export) - `conversations.json` or the zip
- Discord data package (Settings > Data & Privacy > Request data) - casual typing to friends
- Gmail / Google Takeout `.mbox` of Sent mail - emails (needs their address for `--me`)
- Folders of things they wrote themselves: essays, docs, notes, posts, captions (`.txt .md .docx .html`)
- Transcripts or captions of them talking: podcasts, videos, voice memos (`.srt .vtt .txt .json`)
- "Just use my Claude history for now"

Only include documents they wrote **without AI help**. An AI-polished essay teaches the profile to sound like AI.

## 1. Collect and measure

```
W=~/.claude/idiolect/<slug>
python3 <skill-dir>/scripts/collect.py --out $W/corpus.jsonl [--since YYYY-MM-DD] \
    [--claude-export F] [--chatgpt-export F] [--discord D] [--mbox F --me addr] \
    [--docs PATH ...] [--posts PATH ...] [--transcripts PATH ... --speaker NAME]
python3 <skill-dir>/scripts/analyze.py --corpus $W/corpus.jsonl --out $W --name "<Name>"
```

Claude Code and Codex history on this machine are picked up automatically (`--no-auto` turns that off, e.g.
when building a profile for someone else from their files). Use `--since` only if their style changed (say,
the last 12 months). Headless `claude -p` runs are skipped because those are scripts, not them.

If the total is under ~150 messages, say the profile will be thin and offer the extra sources again. Keep
going either way.

## 2. Read, in this order

1. `$W/report.md` - all the numbers, per register, plus which AI-sounding phrases they use and never use.
2. Every file in `$W/samples/` - read all of it. This is where the real voice is: what they talk about, how
   a thought unfolds, how they ask for things, how they disagree, how they get excited or annoyed, what they
   say to check they were understood, how they correct themselves.
3. `$W/stats.json` only if you need a number the report doesn't show.

While reading, throw out anything that isn't them: pasted posts, quoted emails, text a script wrote. If a
sample talks about them in the third person, it's a script.

Registers come from the scripts as `typed-to-ai`, `spoken-dictated?` (long, clean, capitalized messages that
read like voice input; confirm by reading them, merge back if they're just careful typing), `typed-casual`,
`email`, `writing`, `public-post`, `spoken`. Keep a register only if it has roughly 40+ samples or 1,500+
words; mention thinner ones as a short note. Name each register the way they'd recognize it ("Texting
friends", "Prompting AI", "Work email", "Essays for class", "Talking on camera").

Check the typo list against the samples. Keep only real slips (`teh`, `adn`, `becuase`); drop real words that
slipped through. Typos only belong in casual typed registers.

Also look for **context inside a register**: if they write differently to clients than to friends, or for one
project than another, write that down. Who they're talking to is part of the register.

## 3. Write the profile

Write `$W/draft/SKILL.md` and `$W/draft/examples.md` following
[reference/profile-template.md](reference/profile-template.md) exactly. Then edit `$W/profile.json` and save it
as `$W/draft/profile.json`:
- give each register a `"label"` (the human name you chose),
- delete registers you dropped (and merge `spoken-dictated?` back if you decided it isn't real),
- add `"never_say": [...]` for phrases you saw them push back on or that are obviously not them,
- remove any `banned_phrases` entry they actually use (the report lists those they do).

Writing the profile is the whole job. Make it specific enough that a stranger could fake their texts:
quantities ("starts lowercase about 9 times in 10", "a typo every ~100 words"), their exact phrases in quotes,
the shape of a typical message, what they never do. Every rule should be checkable against the samples.

## 4. Install

```
python3 <skill-dir>/scripts/install_profile.py --work $W --skill sound-like-<slug> --name "<Name>"
```

This writes `~/.claude/skills/sound-like-<slug>/` (SKILL.md, examples.md, profile.json, lint.py,
refresh.md), backs up any older version, makes `$W/sound-like-<slug>.zip` for claude.ai, and adds a 3-line
pointer to `~/.claude/CLAUDE.md` so every session loads the profile when it should. Pass `--no-claude-md` if
they asked you not to touch it.

## 5. Prove it, then fix it

Load the new skill and write three short pieces in the registers you have most data for, about real topics
from their samples (something they're working on, a person they mention, a thing they'd post). Run each
through the linter and fix what it flags:

```
python3 ~/.claude/skills/sound-like-<slug>/lint.py draft.txt --register <register>
```

Show the three pieces to them, each next to one real message of theirs from the same register, and ask (one
AskUserQuestion, one question per piece): "Sounds like me" / "Close, a few things are off" / "Not me". For
anything short of "Sounds like me", get what's off in their words.

Write every correction into the profile's "Corrections from <Name>" section (quote them; these outrank the
measured rules), fix the rule that caused it, and re-run step 4. One round is usually enough; offer a second
if they said "Not me" to anything.

## 6. Hand it over

Tell them, briefly:
- it's installed and loads itself whenever they ask for something in their voice, or whenever Claude writes
  something they'll send, post, say or submit as themselves;
- for claude.ai: upload `$W/sound-like-<slug>.zip` in Settings > Capabilities > Skills;
- "refresh my voice profile" rebuilds it from newer messages and keeps their corrections;
- the profile holds their real phrases and a few verbatim (masked) examples, so treat it as personal: don't
  commit it to a public repo or share it with people they wouldn't show their texts to.

## Refreshing

Same steps. Reuse the sources in `~/.claude/skills/sound-like-<slug>/refresh.md` (it records the exact
collect command), compare the new report with the current SKILL.md, update what changed, keep the
Corrections section, re-install, and do a one-piece check instead of three.

## Someone else's voice

If they want a profile for another person (a co-founder, a client, a brand persona) from files they provide:
use `--no-auto` plus the paths, that person's name and slug, and `--no-claude-md` unless they want it always
on. Only do this with material that person wrote and the user has a right to use; a voice profile of a real
person is for writing *with* them or *for* them with their OK, not for passing as them to others.
