#!/usr/bin/env python3
"""Check a draft against a person's voice profile (profile.json next to this file).

Usage:
  python3 lint.py draft.txt --register typed-to-ai
  echo "some text" | python3 lint.py - --register writing
  python3 lint.py --list-registers

Prints problems. Exit code 1 if any HARD problem (things this person never writes), else 0.
Stdlib only.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default="-")
    ap.add_argument("--register", "-r")
    ap.add_argument("--profile", default=os.path.join(HERE, "profile.json"))
    ap.add_argument("--list-registers", action="store_true")
    a = ap.parse_args()
    prof = load(a.profile)
    regs = prof.get("registers", {})
    if a.list_registers:
        for k, v in regs.items():
            print(f"{k}: {v.get('label', '')} ({v.get('messages', '?')} samples)")
        return 0
    text = sys.stdin.read() if a.file == "-" else open(a.file, encoding="utf-8").read()
    reg = regs.get(a.register or "", {})
    if a.register and not reg:
        print(f"unknown register {a.register!r}; have: {', '.join(regs)}", file=sys.stderr)
    hard, soft = [], []

    # 1. phrases they never use (the AI tells, plus anything added by hand)
    for label, rx in prof.get("banned_phrases", []):
        for m in re.finditer(rx, text, re.I):
            hard.append(f"'{m.group(0)}' ({label}): they never write this")
    for phrase in prof.get("never_say", []):
        if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I):
            hard.append(f"'{phrase}': on their never-say list")

    words = WORD.findall(text.lower().replace("’", "'"))
    n = max(len(words), 1)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    if reg:
        # 2. punctuation they (almost) never use in this register
        for key, ch, name in (("em_dash_per_1k", "—", "em dash"), ("en_dash_per_1k", "–", "en dash"),
                              ("semicolon_per_1k", ";", "semicolon")):
            c = text.count(ch)
            if c and reg.get(key, 0) < 0.3:
                (hard if ch != ";" else soft).append(f"{c} {name}(s): they use {reg.get(key, 0)} per 1,000 words here")
        # 3. capitalization, lowercase i, end punctuation, apostrophes (compared as rates, not all-or-nothing)
        letter_starts = [l[0] for l in lines if l[0].isalpha()]
        if letter_starts:
            low = 100.0 * sum(c.islower() for c in letter_starts) / len(letter_starts)
            want = reg.get("starts_lowercase_pct", 50)
            if abs(low - want) >= 45:
                soft.append(f"{low:.0f}% of lines start lowercase; they do {want}% here")
        lone = re.findall(r"(?<![\w'])[iI](?![\w])", text)
        if len(lone) >= 2:
            li = 100.0 * sum(x == "i" for x in lone) / len(lone)
            want = reg.get("lowercase_i_pct", 0)
            if abs(li - want) >= 50:
                soft.append(f"'i' is lowercase {li:.0f}% of the time in the draft; they write it lowercase {want}% here")
        ends = [l[-1] for l in lines]
        if len(ends) >= 2:
            bare = 100.0 * sum(c not in ".!?)\"'" for c in ends) / len(ends)
            want = reg.get("ends_without_punct_pct", 50)
            if abs(bare - want) >= 50:
                soft.append(f"{bare:.0f}% of lines end without punctuation; they do {want}% here")
        with_ap = len(re.findall(r"\b(don't|doesn't|didn't|can't|isn't|i'm|i've|that's|what's)\b", text.lower().replace("’", "'")))
        without = len(re.findall(r"\b(dont|doesnt|didnt|cant|isnt|im|ive|thats|whats)\b", text.lower()))
        drop = reg.get("apostrophe_dropped_pct", 0)
        if with_ap + without >= 2:
            got = 100.0 * without / (with_ap + without)
            if abs(got - drop) >= 45:
                soft.append(f"apostrophes dropped in {got:.0f}% of contractions; they drop {drop}% here (dont, im, thats)")
        # 3b. their real typos, in registers where they make them
        rate = reg.get("typo_rate_per_1k", 0)
        mine = {a for a, _ in reg.get("typos", [])}
        if rate >= 4 and len(words) >= 40 and not any(w in mine for w in words):
            ex = ", ".join(a for a, _ in reg.get("typos", [])[:6])
            soft.append(f"no typos; they make about {rate:.0f} per 1,000 words here. Use one or two of their real ones ({ex}), never in names")
        # 3c. how they open
        opens = reg.get("openers") or []
        if opens and words and reg.get("messages", 0) >= 100 and words[0] not in opens:
            soft.append(f"opens with '{words[0]}', which isn't one of their usual first words here ({', '.join(opens[:12])})")
        # 4. exclamation and emoji
        ex = text.count("!")
        if ex and reg.get("has_exclamation_pct", 0) < 3:
            soft.append(f"{ex} '!': they almost never use exclamation marks here ({reg.get('has_exclamation_pct')}% of messages)")
        emoji = len(re.findall("[\U0001F300-\U0001FAFF☀-➿]", text))
        if emoji and reg.get("emoji_per_1k", 0) < 0.5:
            soft.append(f"{emoji} emoji: they rarely use emoji here")
        # 5. length
        p90 = reg.get("p90_words") or 0
        if p90 and len(words) > 2.5 * p90 and len(words) > 60:
            soft.append(f"{len(words)} words; their long messages here top out around {p90}")

    # 5b. words they have never used anywhere (only meaningful with a decent corpus)
    vocab = set(prof.get("vocab") or [])
    if len(vocab) >= 1500:
        new = []
        for w in words:
            base = re.sub(r"(ies|es|s|ed|ing|ly)$", "", w)
            if len(w) >= 5 and w not in vocab and not ({base, base + "e", base + "y"} & vocab) and w not in new:
                new.append(w)
        if new:
            soft.append("words they've never used: " + ", ".join(new[:12]) + " (fine for names/topics; otherwise use their words)")

    # 6. structures that read as generated no matter who you are
    for rx, why in ((r"\b(it'?s|it is|this is|that'?s|that is) not (just|only|about) [^.?!]{1,40}[,;—] ?(it'?s|it is|but)\b", "'it's not X, it's Y' construction"),
                    (r"(?m)^[^\n]{0,60}:\s*$", "heading-style line ending in a colon"),
                    (r"(?m)^\s*[-*•] \*\*", "bold-label bullet list"),
                    (r"\b(\w+), (\w+),? and (\w+)\b[^.?!]*\. [^.?!]*\b(\w+), (\w+),? and (\w+)\b", "two rule-of-three lists in a row")):
        if re.search(rx, text, re.I):
            soft.append(why + " (reads as AI unless they really talk like this)")

    for h in hard:
        print("HARD  " + h)
    for s in soft:
        print("soft  " + s)
    if not hard and not soft:
        print("clean")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
