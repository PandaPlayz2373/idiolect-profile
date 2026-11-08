# Idiolect

Your **idiolect** is the way *you* use language: your words, your punctuation, the phrases you lean on, the
typos your fingers always make, how you change between texting a friend, emailing a client and writing an
essay.

This Claude Code plugin measures yours from your own words and turns it into a personal skill. After that,
whenever Claude writes something you'll send, post, say or submit as yourself, it writes it **the way you
would**: same tone, same rhythm, same habits, none of the AI tells.

## Install

In Claude Code:

```
/plugin marketplace add PandaPlayz2373/idiolect-profile
/plugin install idiolect@idiolect-profile
```

Then just say:

```
build my voice profile
```

(or run `/idiolect:build-voice-profile`). It takes a few minutes.

## What happens

1. **Collect.** It reads what you've typed to Claude Code and Codex on your machine. You can add more: a
   claude.ai or ChatGPT export, your Discord data package, a Gmail `.mbox` of sent mail, folders of essays,
   docs and posts you wrote, and transcripts of you talking (podcasts, videos, voice memos). Secrets, emails,
   phone numbers, links and file paths are masked before anything else looks at it. Pasted text, code and
   script-written prompts are thrown out.
2. **Measure.** A script counts what you actually do, per context ("register"): how often you start
   lowercase, drop apostrophes, end without punctuation, use `!`, emoji, semicolons, em dashes; your openers
   and sign-offs, filler and hedge words, favorite phrases, your real typos (`teh`, `adn`, `becuase`), and
   which AI-sounding words you never use.
3. **Read.** Claude reads a spread of your real messages in each register, the way a friend would, for the
   things numbers miss: how you explain, ask, push back, get excited, correct yourself.
4. **Write.** It writes `~/.claude/skills/sound-like-<you>/`: a profile with one section per register, your
   rules, your phrases, verbatim examples, and a checker (`lint.py`) that flags anything you'd never write.
5. **Check with you.** It writes three short pieces as you, puts each next to a real message of yours, and
   asks if they sound like you. Whatever's off goes into a "Corrections" section that outranks everything
   else.

After that it's automatic. Ask for "a caption for this, in my voice", "reply to her for me", "write my
discussion post", or just ask Claude to draft something you'll send, and the profile kicks in.

## Use it on claude.ai too

The build makes `sound-like-<you>.zip` in `~/.claude/idiolect/<you>/`. Upload it in claude.ai under
Settings > Capabilities > Skills and the same profile works in the Claude apps.

## Keep it current

Say **"refresh my voice profile"** every couple of months. It re-reads the same sources plus anything new,
updates the numbers and keeps your corrections.

## What it registers

Depending on what you give it:

| Source | Register it teaches |
|---|---|
| Claude Code / Codex history | how you type to AI (and, if you dictate, how you talk) |
| claude.ai / ChatGPT export | same, plus more topics |
| Discord data package | texting friends |
| Gmail Sent `.mbox` | email |
| Essays, docs, cover letters | formal writing |
| Posts, captions | public posts |
| Transcripts (`.srt .vtt .txt .json`) | talking, on camera, podcasts |

Only add writing you did **without AI help**. Feed it AI-polished text and it learns to sound like AI.

## Privacy

- Everything is read and measured locally by stdlib Python. The scripts make no network calls.
- Claude reads a sample of your (masked) messages during the build, the same way it reads anything else you
  show it in a session.
- The private working files (corpus, stats, samples) stay in `~/.claude/idiolect/<you>/`. Delete that folder
  any time; the installed profile doesn't need it.
- The profile contains your real phrases and a few verbatim examples. Treat it like your texts: don't commit
  it to a public repo.

## Profiles for someone else

You can build one for a co-founder, a client or a brand voice from files they gave you ("build a voice
profile for Sam from these files"). Use it to write *with* them or *for* them with their OK, never to pass as
someone to people who don't know.

## Requirements

Claude Code and Python 3.8+ (`python3`, or `python` on Windows). No packages to install.

## Files

```
.claude-plugin/          plugin + marketplace manifests
skills/build-voice-profile/
  SKILL.md               the build procedure Claude follows
  reference/profile-template.md   the shape of the profile it writes
  scripts/collect.py     sources -> corpus.jsonl (masked, filtered)
  scripts/analyze.py     corpus -> report.md, stats.json, samples/, profile.json
  scripts/lint.py        checks a draft against a profile (ships inside every profile)
  scripts/install_profile.py   installs the profile skill, zips it for claude.ai
```

MIT licensed.
