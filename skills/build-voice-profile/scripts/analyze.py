#!/usr/bin/env python3
"""Measure how a person writes and talks, per register, from corpus.jsonl (see collect.py).

Writes into --out:
  report.md            the numbers, readable (Claude reads this first)
  stats.json           the same numbers, machine-readable
  samples/<reg>.md     stratified verbatim samples per register (Claude reads these next)
  profile.json         draft rules for lint.py (Claude reviews and edits)

Usage: python3 analyze.py --corpus corpus.jsonl --out work/ [--name "Jordan"] [--samples 150]
Stdlib only.
"""
import argparse, datetime, json, os, re, statistics
from collections import Counter, defaultdict

COMMON = set("""a about above across after again against all almost alone along already also although always am among an and
another any anybody anyone anything anyway anywhere are around as ask asked at away back be became because become been before
began behind being believe below best better between big both bring but by call came can cannot car case change children city
close come could country course day days did different do does doing done down during each early end enough even ever every
everyone everything example eye eyes face fact family far feel few find first five follow for found four friend from front full
gave get give given go going good got great group had hand hard has have having he head hear heard help her here high him himself
his home house how however i idea if important in into is it its itself job just keep kind knew know large last later least left
less let life light like line little live long look looking lot made make man many may me mean men might mind money more most
mother much must my myself name near need never new next night no not nothing now number of off often old on once one only open
or order other our out over own part people perhaps place play point possible power problem put question quite rather read real
really right room run said same saw say school second see seem seemed seen set several she should show side since small so some
someone something sometimes soon start state still stop story study such sure take talk tell than that the their them then there
these they thing things think this those though thought three through time to today together told too took toward try turn two
under until up upon us use used very want was water way we week well went were what when where whether which while white who
whole why will with within without woman word words work world would write year years yes yet you young your yours yeah okay ok
im dont thats its ive ill cant didnt doesnt isnt wasnt youre theyre lets whats theres""".split())

STOP = set("""a an the and or but so to of in on at for with from by as is are was were be been being it its this that these those
i me my we us our you your he she they them their his her him not no do does did have has had will would can could should just
if then than there here what which who when where how all any some very too also up out about into over""".split())

# Phrases that make text read as machine-written. The analyzer counts the person's OWN use of each.
# Anything they never use becomes a hard "never write this" rule in their profile.
AI_TELLS = [
    ("em dash", r"—"), ("en dash as a pause", r" – "), ("delve", r"\bdelv(e|es|ed|ing)\b"),
    ("tapestry", r"\btapestr(y|ies)\b"), ("testament to", r"\btestament to\b"), ("realm", r"\brealms?\b"),
    ("leverage (verb)", r"\bleverag(e|es|ed|ing) (the|your|our|their|this|that|it|ai)\b"), ("seamless", r"\bseamless(ly)?\b"),
    ("game-changer", r"\bgame[- ]chang(er|ing)\b"), ("unlock", r"\bunlock(s|ed|ing)?\b"), ("elevate", r"\belevat(e|es|ed|ing)\b"),
    ("level up", r"\blevel(s|ed)? up\b"), ("harness", r"\bharness(es|ed|ing)? (the|your|its)\b"), ("streamline", r"\bstreamlin(e|es|ed|ing)\b"),
    ("robust", r"\brobust\b"), ("pivotal", r"\bpivotal\b"), ("crucial", r"\bcrucial(ly)?\b"), ("vital", r"\bvital\b"),
    ("foster", r"\bfoster(s|ed|ing)?\b"), ("showcase", r"\bshowcas(e|es|ed|ing)\b"), ("embark", r"\bembark(s|ed|ing)?\b"),
    ("navigate (figurative)", r"\bnavigat(e|es|ing) (the|this|these|your|life|challenges|complex)"),
    ("landscape (figurative)", r"\b(digital|business|ever-changing|evolving|competitive|modern) landscape\b"),
    ("ever-evolving / fast-paced", r"\b(ever[- ]evolving|ever[- ]changing|fast[- ]paced)\b"),
    ("in today's world", r"\bin today'?s (world|age|era|landscape|market|digital|fast)"), ("multifaceted", r"\bmultifaceted\b"), ("nuanced", r"\bnuanced?\b"),
    ("intricate", r"\bintricat(e|ely|ies)\b"), ("meticulous", r"\bmeticulous(ly)?\b"), ("vibrant", r"\bvibrant\b"),
    ("bustling", r"\bbustling\b"), ("comprehensive", r"\bcomprehensive\b"), ("holistic", r"\bholistic\b"),
    ("synergy", r"\bsynerg(y|ies|istic)\b"), ("paradigm", r"\bparadigms?\b"), ("utilize", r"\butiliz(e|es|ed|ing|ation)\b"),
    ("furthermore", r"\bfurthermore\b"), ("moreover", r"\bmoreover\b"), ("additionally", r"\badditionally\b"),
    ("notably", r"\bnotably\b"), ("ultimately", r"\bultimately\b"), ("essentially", r"\bessentially\b"),
    ("it's worth noting", r"\bworth noting\b"), ("it's important to", r"\bit'?s (important|crucial|essential) to\b"),
    ("dive in / deep dive", r"\b(dive (in|into)|deep[- ]dive)\b"), ("let's explore", r"\blet'?s (explore|unpack|break (it|this) down)\b"),
    ("here's the thing", r"\bhere'?s the (thing|kicker|catch|truth)\b"), ("the best part?", r"\bthe best part\?"),
    ("not just X, it's Y", r"\b(it'?s|it is|this is|that'?s|that is) not (just|only|about) [^.?!]{1,40}[,;—-] ?(it'?s|it is|but|this is)\b"),
    ("whether you're", r"\bwhether you'?re\b"), ("journey (figurative)", r"\byour [a-z]+ journey\b|\bon (this|your|the) journey\b"),
    ("empower", r"\bempower(s|ed|ing|ment)?\b"), ("transformative", r"\btransformative\b"), ("cutting-edge", r"\bcutting[- ]edge\b"),
    ("in conclusion", r"\bin conclusion\b"), ("in summary", r"\bin summary\b"), ("at its core", r"\bat (its|the) core\b"),
    ("plays a crucial role", r"\bplays? an? (crucial|key|vital|pivotal) role\b"), ("a myriad of", r"\b(a )?myriad\b"),
    ("resonate", r"\bresonat(e|es|ed|ing)\b"), ("insights", r"\binsights\b"), ("curated", r"\bcurat(e|ed|ing)\b"),
    ("just wanted to (reach out / flag)", r"\bjust wanted to (reach out|flag|check in|follow up|touch base|share)\b"),
    ("I'd love to", r"\bi'?d love (to|for)\b"), ("hope you're doing well", r"\bhope (you'?re|you are|this finds you) (doing )?well\b"),
    ("excited to share", r"\b(excited|thrilled|delighted) to (share|announce)\b"), ("don't hesitate", r"\bdon'?t hesitate to\b"),
    ("I hope this helps", r"\bi hope this (helps|finds you)\b"), ("feel free to", r"\bfeel free to\b"),
    ("great question", r"\bgreat question\b"), ("absolutely!", r"\babsolutely!"), ("certainly", r"\bcertainly\b"),
    ("indeed", r"\bindeed\b"), ("thus / hence", r"\b(thus|hence)\b"), ("whilst", r"\bwhilst\b"),
    ("boasts", r"\bboasts?\b"), ("nestled", r"\bnestled\b"), ("bespoke", r"\bbespoke\b"), ("elevated", r"\belevated\b"),
    ("supercharge", r"\bsupercharg(e|es|ed|ing)\b"), ("revolutionize", r"\brevolutioniz(e|es|ed|ing)\b"),
    ("rest assured", r"\brest assured\b"), ("look no further", r"\blook no further\b"), ("stand out from the crowd", r"\bstand out from\b"),
]

MARKERS = ["like", "basically", "literally", "actually", "honestly", "kind of", "kinda", "sort of", "sorta", "i mean", "you know",
           "i guess", "i feel like", "i think", "or something", "and stuff", "stuff like that", "or whatever", "whatever", "etc",
           "lowkey", "highkey", "ngl", "tbh", "fr", "imo", "idk", "bro", "dude", "man", "bruh", "yeah", "yep", "yup", "nah", "nope",
           "okay", "ok", "k", "gonna", "wanna", "gotta", "y'all", "super", "really", "pretty", "definitely", "totally", "so",
           "anyway", "anyways", "also", "and also", "plus", "just", "lol", "lmao", "haha", "omg", "wtf", "rn", "u", "ur", "pls", "plz",
           "thx", "ty", "np", "btw", "obviously", "seriously", "crazy", "insane", "awesome", "cool", "dope", "sick", "nice", "perfect",
           "amazing", "love", "hate", "sucks", "make sense", "does that make sense", "you know what i mean", "you see what i'm saying",
           "right?", "for sure", "no way", "100%", "10 times out of 10", "at the end of the day", "to be honest", "in order to",
           "so that", "and then", "because", "cause", "cuz", "bc", "though", "tho", "however", "therefore", "in fact", "as far as",
           "i'm sorry", "sorry", "please", "thanks", "thank you", "appreciate it", "awesome", "let's", "lets", "can you", "could you",
           "would you", "i want", "i need", "give me", "is there a way", "what about", "how about", "go ahead", "keep going"]
PROFANITY = ["fuck", "fucking", "shit", "damn", "hell", "ass", "crap", "bitch", "piss"]
CONTRACTIONS = {"dont": "don't", "doesnt": "doesn't", "didnt": "didn't", "cant": "can't", "isnt": "isn't", "wasnt": "wasn't",
                "im": "i'm", "ive": "i've", "thats": "that's", "whats": "what's", "theres": "there's", "youre": "you're",
                "theyre": "they're", "couldnt": "couldn't", "wouldnt": "wouldn't", "shouldnt": "shouldn't", "havent": "haven't",
                "arent": "aren't", "wont": "won't", "id": "i'd", "youve": "you've", "hes": "he's", "shes": "she's"}
SPOKEN_HINTS = re.compile(r"\b(um+|uh+|you know|i mean|kind of like|or something like that|you see what i'm saying|does that make sense)\b", re.I)
EMOJI = re.compile("(?![\U0001F3FB-\U0001F3FF])[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
EMOTICON = re.compile(r"(?<!\w)(:\)|:\(|:D|;\)|:P|xD|<3|:/)(?!\w)")
WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def words(t):
    return WORD.findall(t.lower().replace("’", "'"))


def pct(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def per_k(n, w):
    return round(1000.0 * n / w, 2) if w else 0.0


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", t) if s.strip()]


KEYS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
NEAR = {}
for r, row in enumerate(KEYS):
    for c, ch in enumerate(row):
        n = set()
        for dr in (-1, 0, 1):
            if 0 <= r + dr < 3:
                for dc in (-1, 0, 1):
                    cc = c + dc + (0 if dr == 0 else (-dr if dr < 0 else 0))
                    rr = KEYS[r + dr]
                    for k in (cc, cc + 1):
                        if 0 <= k < len(rr) and rr[k] != ch:
                            n.add(rr[k])
        NEAR[ch] = n


def typo_edits(w):
    """Edits that real fast typing produces: swapped letters, a dropped letter, a doubled or
    neighbouring extra key, a neighbouring wrong key. Yields (candidate, kind)."""
    letters = "abcdefghijklmnopqrstuvwxyz"
    for i in range(len(w) - 1):  # transposition: teh -> the
        if w[i] != w[i + 1]:
            yield w[:i] + w[i + 1] + w[i] + w[i + 2:], "swap"
    for i in range(1, len(w) + 1):  # the typo is missing a letter: becaue -> because
        for c in letters:
            yield w[:i] + c + w[i:], "dropped"
    for i in range(1, len(w)):  # the typo has an extra key next to a neighbour: wawnt -> want
        x = w[i]
        if x == w[i - 1] or x in NEAR.get(w[i - 1], ()) or (i + 1 < len(w) and x in NEAR.get(w[i + 1], ())):
            yield w[:i] + w[i + 1:], "extra"
    if len(w) >= 4:
        for i in range(1, len(w)):  # neighbouring wrong key: thw -> the
            for c in NEAR.get(w[i], ()):
                yield w[:i] + c + w[i + 1:], "near"


def find_typos(freq, lower_share=None):
    """Words one slip away from a word this person uses far more often = their real typos.
    Still check the list against the samples: a few real words sneak through."""
    pairs = []
    for w, n in freq.items():
        if len(w) < 3 or "'" in w or w in COMMON:
            continue
        if lower_share is not None and lower_share.get(w, 1.0) < 0.6:
            continue  # mostly written capitalized: a name or acronym (iOS, SEO, Hue), not a slip
        best = None
        for c, kind in typo_edits(w):
            m = freq.get(c, 0)
            need = 10 if kind == "swap" else 25
            if m >= 8 and m >= need * n and not (c.startswith(w) or w.startswith(c)):
                if not best or m > best[1]:
                    best = (c, m)
        if best:
            pairs.append((w, best[0], n))
    pairs.sort(key=lambda x: -x[2])
    return pairs


def third_person(name):
    if not name:
        return None
    n = re.escape(name.split()[0])
    return re.compile(rf"\b{n}('s| is| was| has| wants| asked| said| needs| will|, who)\b|\bfor {n}\b|\b{n} (writes|talks|sounds)\b", re.I)


def analyze(rows):
    texts = [r["text"] for r in rows]
    allw = [w for t in texts for w in words(t)]
    W = len(allw)
    lens = [len(words(t)) for t in texts]
    s = {"messages": len(rows), "words": W}
    if not rows:
        return s
    s["median_words"] = statistics.median(lens)
    s["p90_words"] = sorted(lens)[int(0.9 * (len(lens) - 1))]
    first_chars = [t.lstrip()[0] for t in texts if t.strip()]
    letters_first = [c for c in first_chars if c.isalpha()]
    s["starts_lowercase_pct"] = pct(sum(c.islower() for c in letters_first), len(letters_first))
    last = [t.rstrip()[-1] for t in texts if t.strip()]
    s["ends_without_punct_pct"] = pct(sum(c not in ".!?)\"'" for c in last), len(last))
    s["ends_with_period_pct"] = pct(sum(c == "." for c in last), len(last))
    s["ends_with_question_pct"] = pct(sum(c == "?" for c in last), len(last))
    s["has_exclamation_pct"] = pct(sum("!" in t for t in texts), len(texts))
    s["multi_exclamation_pct"] = pct(sum(bool(re.search(r"!{2,}", t)) for t in texts), len(texts))
    s["all_caps_msgs_pct"] = pct(sum(1 for t in texts if len(re.findall(r"[A-Za-z]", t)) >= 8 and t.upper() == t), len(texts))
    s["multi_line_pct"] = pct(sum("\n" in t.strip() for t in texts), len(texts))
    s["numbered_list_pct"] = pct(sum(bool(re.search(r"(?m)^\s*\d[.)]\s", t)) for t in texts), len(texts))
    lone_i = re.findall(r"(?<![\w'])[iI](?![\w'])", "\n".join(texts))
    s["lowercase_i_pct"] = pct(sum(x == "i" for x in lone_i), len(lone_i))
    joined = "\n".join(texts)
    s["per_1k_words"] = {
        "em_dash": per_k(joined.count("—"), W), "en_dash": per_k(joined.count("–"), W),
        "spaced_hyphen": per_k(len(re.findall(r"\s-\s", joined)), W), "double_hyphen": per_k(joined.count("--"), W),
        "semicolon": per_k(joined.count(";"), W), "colon": per_k(len(re.findall(r":(?!//)", joined)), W),
        "ellipsis": per_k(len(re.findall(r"\.\.\.|…", joined)), W), "parentheses": per_k(joined.count("("), W),
        "double_quotes": per_k(len(re.findall(r"[\"“]", joined)) / 2, W), "comma": per_k(joined.count(","), W),
        "emoji": per_k(len(EMOJI.findall(joined)), W), "emoticon": per_k(len(EMOTICON.findall(joined)), W),
    }
    s["top_emoji"] = Counter(EMOJI.findall(joined)).most_common(10)
    sl = [len(words(x)) for t in texts for x in sentences(t)]
    s["median_sentence_words"] = statistics.median(sl) if sl else 0
    # apostrophes
    f = Counter(allw)
    drop = {k: (f.get(k, 0), f.get(v, 0)) for k, v in CONTRACTIONS.items() if f.get(k, 0) + f.get(v, 0) >= 3 and k not in ("wont", "id", "hes", "shes")}
    dn = sum(a for a, b in drop.values())
    dd = sum(a + b for a, b in drop.values())
    s["apostrophe_dropped_pct"] = pct(dn, dd)
    s["apostrophe_detail"] = {k: {"without": a, "with": b} for k, (a, b) in sorted(drop.items(), key=lambda x: -sum(x[1]))[:15]}
    # openers / closers
    op1, op2, op3, cl = Counter(), Counter(), Counter(), Counter()
    for t in texts:
        w = words(t)
        if w:
            op1[w[0]] += 1
            if len(w) > 1:
                op2[" ".join(w[:2])] += 1
            if len(w) > 2:
                op3[" ".join(w[:3])] += 1
            if len(w) >= 3:
                cl[" ".join(w[-3:])] += 1
    s["openers_1"] = [(k, v, pct(v, len(texts))) for k, v in op1.most_common(25)]
    s["openers_2"] = [(k, v) for k, v in op2.most_common(25)]
    s["openers_3"] = [(k, v) for k, v in op3.most_common(20) if v >= 3]
    s["closers_3"] = [(k, v) for k, v in cl.most_common(20) if v >= 3]
    so = Counter()
    for t in texts:
        for x in sentences(t):
            m = re.match(r"^([A-Za-z']+(?: [A-Za-z']+){0,2},)", x)
            if m:
                so[m.group(1)] += 1
    s["sentence_openers_with_comma"] = [(k, v) for k, v in so.most_common(25) if v >= 2]
    # markers
    low = " " + re.sub(r"\s+", " ", joined.lower().replace("’", "'")) + " "
    mk = {}
    for m in MARKERS:
        n = len(re.findall(r"(?<![\w'])" + re.escape(m) + (r"(?![\w'])" if m[-1].isalnum() else ""), low))
        if n:
            mk[m] = (n, per_k(n, W))
    s["markers_per_1k"] = sorted(([k, v[0], v[1]] for k, v in mk.items()), key=lambda x: -x[2])[:60]
    s["profanity_per_1k"] = {p: per_k(f.get(p, 0), W) for p in PROFANITY if f.get(p, 0)}
    # n-grams
    grams = {n: Counter() for n in (2, 3, 4, 5)}
    for t in texts:
        for sent in sentences(t):
            w = words(sent)
            for n in grams:
                for i in range(len(w) - n + 1):
                    grams[n][" ".join(w[i:i + n])] += 1
    s["ngrams"] = {
        "2": [(k, v) for k, v in grams[2].most_common(400) if not all(x in STOP for x in k.split())][:40],
        "3": [(k, v) for k, v in grams[3].most_common(60) if v >= 3],
        "4": [(k, v) for k, v in grams[4].most_common(40) if v >= 3],
        "5": [(k, v) for k, v in grams[5].most_common(30) if v >= 3],
    }
    s["signature_words"] = [(k, v) for k, v in f.most_common(600) if k not in COMMON and k not in STOP and len(k) > 2][:60]
    ty = find_typos(f, case_share(texts))
    s["typos"] = ty[:40]
    s["typo_rate_per_1k"] = per_k(sum(n for _, _, n in ty), W)
    s["ai_tells"] = {}
    for label, rx in AI_TELLS:
        n = len(re.findall(rx, joined, re.I))
        s["ai_tells"][label] = n
    s["spelling"] = {"-ize": len(re.findall(r"\b\w+iz(e|es|ed|ing|ation)\b", low)), "-ise": len(re.findall(r"\b\w{3,}is(e|es|ed|ing|ation)\b", low)),
                     "color": low.count(" color"), "colour": low.count(" colour")}
    return s


def case_share(texts):
    """share of each word's occurrences written all-lowercase"""
    tot, low = Counter(), Counter()
    for t in texts:
        for m in re.findall(r"[A-Za-z]+", t):
            k = m.lower()
            tot[k] += 1
            low[k] += m == k
    return {k: low[k] / tot[k] for k in tot}


def maybe_dictated(t, typo_words):
    w = words(t)
    if len(w) < 12:
        return False
    t2 = t.strip()
    sents = sentences(t2)
    capped = sum(1 for x in sents if x[:1].isupper()) / max(len(sents), 1)
    ends_punct = t2[-1:] in ".?!"
    few_typos = sum(1 for x in w if x in typo_words) <= 1
    proper_apos = not re.search(r"\b(dont|im|cant|didnt|doesnt|thats|ive|isnt)\b", t2.lower())
    caps_i = bool(re.search(r"(?<![\w'])I(?![\w])", t2)) and not re.search(r"(?<![\w'])i(?![\w'])", t2)
    # voice input: clean contractions, capital I, sentences that start capitalized, and talk-shaped
    return (ends_punct or capped >= 0.8) and few_typos and proper_apos and (caps_i or capped >= 0.8) and \
        (bool(SPOKEN_HINTS.search(t2)) or len(w) > 25)


def pick_samples(rows, k):
    rows = sorted(rows, key=lambda r: r.get("at") or "")
    buckets = defaultdict(list)
    for r in rows:
        n = len(words(r["text"]))
        b = "1-4" if n <= 4 else "5-15" if n <= 15 else "16-40" if n <= 40 else "41-120" if n <= 120 else "121+"
        buckets[b].append(r)
    share = {"1-4": 0.12, "5-15": 0.33, "16-40": 0.3, "41-120": 0.18, "121+": 0.07}
    out = []
    for b, rs in buckets.items():
        want = max(3, int(k * share[b]))
        if len(rs) <= want:
            out += rs
        else:
            step = len(rs) / want
            out += [rs[int(i * step)] for i in range(want)]  # spread across time
    return sorted(out, key=lambda r: r.get("at") or "")[: int(k * 1.1)]


def fmt_pairs(xs, n=None):
    xs = xs[:n] if n else xs
    return ", ".join(f"`{x[0]}` ({x[1]})" for x in xs) or "none"


def report(name, stats, sources):
    L = [f"# Voice stats{(' for ' + name) if name else ''}", "",
         f"Built {datetime.date.today()} from {sum(sources.values())} pieces of their own writing/speech: " +
         ", ".join(f"{k} {v}" for k, v in sources.items()) + ".", "",
         "Numbers are descriptive, not targets to hit exactly. Registers with under ~40 messages are thin: treat them as hints.", ""]
    for reg, s in stats.items():
        if not s.get("messages"):
            continue
        p = s["per_1k_words"]
        L += [f"## Register: {reg}", ""] + ([
              "_Probably voice input. Its capitalization and punctuation come from the transcriber, not the person: "
              "use this register for word choice, rhythm and phrasing, not punctuation._", ""] if reg == "dictated" else []) + [
              f"- {s['messages']} messages, {s['words']} words. Median {s['median_words']} words/message (90th pct {s['p90_words']}), "
              f"median sentence {s['median_sentence_words']} words.",
              f"- Starts lowercase {s['starts_lowercase_pct']}%. No ending punctuation {s['ends_without_punct_pct']}%. "
              f"Ends with '.' {s['ends_with_period_pct']}%, '?' {s['ends_with_question_pct']}%.",
              f"- Lowercase standalone 'i' {s['lowercase_i_pct']}%. Apostrophes dropped in contractions {s['apostrophe_dropped_pct']}% "
              f"({', '.join(f'{k} {v['without']}/{v['with']}' for k, v in list(s['apostrophe_detail'].items())[:8])}).",
              f"- '!' in {s['has_exclamation_pct']}% of messages, '!!+' {s['multi_exclamation_pct']}%, ALL-CAPS messages {s['all_caps_msgs_pct']}%. "
              f"Multi-line {s['multi_line_pct']}%, numbered lists {s['numbered_list_pct']}%.",
              f"- Per 1k words: em dash {p['em_dash']}, en dash {p['en_dash']}, spaced hyphen {p['spaced_hyphen']}, semicolon {p['semicolon']}, "
              f"colon {p['colon']}, ellipsis {p['ellipsis']}, parentheses {p['parentheses']}, commas {p['comma']}, emoji {p['emoji']}, emoticons {p['emoticon']}.",
              f"- Top emoji: {' '.join(e for e, _ in s['top_emoji']) or 'none'}.",
              f"- Typos (real ones, 'typed -> meant (times)'): " + (", ".join(f"{a}->{b} ({n})" for a, b, n in s["typos"][:30]) or "none found") +
              f". Typo rate {s['typo_rate_per_1k']}/1k words.",
              f"- First word: {', '.join(f'`{k}` {p_}%' for k, _, p_ in s['openers_1'][:15])}.",
              f"- First two words: {fmt_pairs(s['openers_2'], 20)}.",
              f"- First three words: {fmt_pairs(s['openers_3'], 15)}.",
              f"- Last three words: {fmt_pairs(s['closers_3'], 15)}.",
              f"- Sentence openers with a comma: {fmt_pairs(s['sentence_openers_with_comma'], 20)}.",
              f"- Discourse markers per 1k words: " + ", ".join(f"`{k}` {r}" for k, _, r in s["markers_per_1k"][:45]) + ".",
              f"- Profanity per 1k: {s['profanity_per_1k'] or 'none'}.",
              f"- Phrases (3-5 words): {fmt_pairs(s['ngrams']['5'], 12)}; {fmt_pairs(s['ngrams']['4'], 15)}; {fmt_pairs(s['ngrams']['3'], 30)}.",
              f"- Word pairs: {fmt_pairs(s['ngrams']['2'], 30)}.",
              f"- Their frequent less-common words (topics + slang): {fmt_pairs(s['signature_words'], 45)}.",
              f"- Spelling: {s['spelling']}.",
              ""]
    used, never = Counter(), []
    for reg, s in stats.items():
        for k, v in (s.get("ai_tells") or {}).items():
            used[k] += v
    never = [k for k, v in used.items() if v == 0]
    L += ["## AI tells", "",
          "Phrases that read as machine-written, counted in their own words across every register.", "",
          "- **Never used (make these hard bans):** " + ", ".join(never) + ".",
          "- **They do use (allowed, at their own rate):** " + (", ".join(f"{k} ({v})" for k, v in used.most_common() if v) or "none") + ".", ""]
    return "\n".join(L), never, used


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="", help="their name; drops prompts that talk ABOUT them in the third person")
    ap.add_argument("--samples", type=int, default=150, help="verbatim samples per register")
    ap.add_argument("--no-dictation-split", action="store_true")
    ap.add_argument("--exclude", help="file of sample ids (one per line) that aren't really them; dropped before measuring")
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.corpus, encoding="utf-8") if l.strip()]
    tp = third_person(a.name)
    dropped = 0
    if tp:
        keep = [r for r in rows if not tp.search(r["text"][:400])]
        dropped = len(rows) - len(keep)
        rows = keep
    excluded = 0
    if a.exclude and os.path.isfile(a.exclude):
        bad = {l.strip().strip("[]") for l in open(a.exclude, encoding="utf-8") if l.strip() and not l.startswith("#")}
        excluded = sum(r["id"] in bad for r in rows)
        rows = [r for r in rows if r["id"] not in bad]
    sources = Counter(r["src"] for r in rows)

    # split typed-to-ai into typed vs probably-dictated (people who use voice input talk differently)
    if not a.no_dictation_split:
        tt = [r["text"] for r in rows if r["register"] == "typed-to-ai"]
        f = Counter(w for t in tt for w in words(t))
        typo_words = {t for t, _, _ in find_typos(f, case_share(tt))}
        cand = [r for r in rows if r["register"] == "typed-to-ai" and maybe_dictated(r["text"], typo_words)]
        typed = [r for r in rows if r["register"] == "typed-to-ai"]
        # only split when it is a real habit, not a handful of careful messages
        if len(cand) >= 30 and len(cand) < 0.8 * len(typed):
            ids = {r["id"] for r in cand}
            for r in rows:
                if r["id"] in ids:
                    r["register"] = "dictated"

    by = defaultdict(list)
    for r in rows:
        by[r["register"]].append(r)
    stats = {reg: analyze(rs) for reg, rs in sorted(by.items(), key=lambda x: -len(x[1]))}

    os.makedirs(os.path.join(a.out, "samples"), exist_ok=True)
    md, never, used = report(a.name, stats, sources)
    if excluded:
        md += f"\n_Excluded {excluded} samples listed in {a.exclude}._\n"
    if dropped:
        md += f"\n_Dropped {dropped} prompts that talk about {a.name} in the third person (scripts, not them)._\n"
    open(os.path.join(a.out, "report.md"), "w", encoding="utf-8").write(md)
    json.dump({"sources": sources, "stats": stats}, open(os.path.join(a.out, "stats.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    for reg, rs in by.items():
        pick = pick_samples(rs, a.samples)
        L = [f"# Samples: {reg}", "", f"{len(pick)} of {len(rs)}, spread across length and time. Verbatim (redacted). "
             "Some may still be pasted text or prompts written by a script: put the id (first field) of anything that "
             "isn't clearly them in exclude.txt and re-run analyze.py with --exclude.", ""]
        for r in pick:
            t = r["text"] if len(r["text"]) <= 1500 else r["text"][:1500] + " [...]"
            L.append(f"[{r['id']} · {(r.get('at') or '')[:10]} · {r.get('src')} · {r.get('ctx') or '-'}]")
            L.append("> " + t.replace("\n", "\n> "))
            L.append("")
        safe = re.sub(r"[^a-z0-9\-]+", "-", reg.lower()).strip("-")
        open(os.path.join(a.out, "samples", safe + ".md"), "w", encoding="utf-8").write("\n".join(L))

    prof = {"name": a.name, "built": str(datetime.date.today()),
            "banned_phrases": [[label, rx] for label, rx in AI_TELLS if used.get(label, 0) == 0],
            "registers": {}}
    for reg, s in stats.items():
        if not s.get("messages"):
            continue
        p = s["per_1k_words"]
        prof["registers"][reg] = {
            "messages": s["messages"], "median_words": s["median_words"], "p90_words": s["p90_words"],
            "starts_lowercase_pct": s["starts_lowercase_pct"], "ends_without_punct_pct": s["ends_without_punct_pct"],
            "lowercase_i_pct": s["lowercase_i_pct"], "apostrophe_dropped_pct": s["apostrophe_dropped_pct"],
            "has_exclamation_pct": s["has_exclamation_pct"], "em_dash_per_1k": p["em_dash"], "en_dash_per_1k": p["en_dash"],
            "semicolon_per_1k": p["semicolon"], "emoji_per_1k": p["emoji"], "colon_per_1k": p["colon"],
            "typo_rate_per_1k": s["typo_rate_per_1k"], "typos": [[a_, b_] for a_, b_, _ in s["typos"][:20]],
            "openers": [k for k, _, share in s["openers_1"] if share >= 0.5],
        }
    vocab = Counter(w for r in rows for w in words(r["text"]))
    prof["vocab"] = sorted(w for w in vocab if len(w) >= 3)
    json.dump(prof, open(os.path.join(a.out, "profile.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({"registers": {k: v.get("messages", 0) for k, v in stats.items()}, "dropped_third_person": dropped,
                      "out": os.path.abspath(a.out)}, indent=1))


if __name__ == "__main__":
    main()
