#!/usr/bin/env python3
"""Collect a person's OWN words from the places they write and talk.

Everything stays on this machine. Output is one JSON line per message/document:
  {"id", "src", "kind", "register", "at", "ctx", "text"}

kind     : ai_chat | chat | email | doc | transcript | post
register : typed-to-ai | typed-casual | email | writing | spoken | public-post

With no source flags it auto-detects Claude Code and Codex history on this machine.

Usage:
  python3 collect.py --out corpus.jsonl [--since 2026-01-01]
                     [--claude-code [DIR]] [--codex [DIR]]
                     [--claude-export FILE_OR_ZIP] [--chatgpt-export FILE_OR_ZIP]
                     [--discord DIR_OR_ZIP] [--mbox FILE --me you@example.com]
                     [--docs PATH ...] [--posts PATH ...]
                     [--transcripts PATH ...] [--speaker NAME]
                     [--include-headless] [--no-auto]
Stdlib only. Python 3.8+.
"""
import argparse, csv, email, email.policy, glob, hashlib, html, io, json, mailbox, os, re, sys, zipfile
from collections import Counter

HOME = os.path.expanduser("~")

# ---------------------------------------------------------------- redaction
RE_KEY = re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abpr]-[A-Za-z0-9\-]{10,}|AKIA[0-9A-Z]{16}|"
                    r"AIza[0-9A-Za-z_\-]{30,}|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}|"
                    r"[A-Fa-f0-9]{32,}|[A-Za-z0-9_\-]{40,})\b")
RE_EMAIL = re.compile(r"\b[\w.+\-]+@[\w\-]+\.[\w.\-]+\b")
RE_PHONE = re.compile(r"(?<!\d)(\+?\d{1,2}[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?!\d)")
RE_URL = re.compile(r"https?://[^\s)>\]]+")
RE_PATH = re.compile(r"(?:[A-Za-z]:\\|/(?:Users|home)/)[^\s'\"`]+")


def redact(t):
    t = RE_URL.sub("[link]", t)
    t = RE_EMAIL.sub("[email]", t)
    t = RE_PHONE.sub("[phone]", t)
    t = RE_KEY.sub("[secret]", t)
    t = RE_PATH.sub("[path]", t)
    return t


# ---------------------------------------------------------------- cleaning
TAG_BLOCK = re.compile(
    r"<(system-reminder|pasted_content|ide_selection|ide_opened_file|ide_diagnostics|command-[a-z\-]+|"
    r"local-command-[a-z\-]+|task-notification|bash-[a-z\-]+|user-prompt-submit-hook|environment_context|"
    r"user_instructions|recommended_plugins|turn_aborted|user_shell_command|INSTRUCTIONS|context|document|"
    r"attachment|file|image)[^>]*>.*?</\1[^>]*>", re.S | re.I)
UNCLOSED = re.compile(r"<(pasted_content|system-reminder|ide_selection|document)[^>]*>.*\Z", re.S | re.I)
MACHINE_START = re.compile(
    r"^(<|Caveat:|\[Request interrupted|This session is being continued|Base directory for this skill|"
    r"# AGENTS\.md|# CLAUDE\.md|You are (a|an|the|\w+ing) |You're (a|an|the|\w+ing) |You write |Reply with |Respond with |Return (only )?(a |the )?JSON|"
    r"Load the |\{|\[\{|Summarize the following|Here is the transcript|Please analyze the following|"
    r"Your task is|SYSTEM:|Context:|Instructions:|#{1,6} )", re.I)
HEADLESS = ("sdk-cli", "sdk-py", "sdk-ts", "sdk")


def looks_like_code_or_paste(t):
    if len(t) > 3000:
        return True
    lines = [l for l in t.splitlines() if l.strip()]
    if not lines:
        return True
    codey = sum(1 for l in lines if re.search(r"[{};=<>]\s*$|^\s*(def |class |import |from \S+ import|const |let |var |function |"
                                               r"return |if \(|for \(|#include|SELECT |\$ |PS [A-Z]:|>>> |at \S+\(|Traceback|"
                                               r"File \"|    at |\s{4,}\S)", l))
    if len(lines) >= 4 and codey / len(lines) > 0.4:
        return True
    letters = sum(c.isalpha() for c in t)
    return letters < 0.45 * len(t) and len(t) > 40


def clean(t):
    t = TAG_BLOCK.sub("", t or "")
    t = UNCLOSED.sub("", t)
    t = re.sub(r"```.*?```", "", t, flags=re.S)  # fenced code is never their voice
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t


def keep(t):
    if not t or MACHINE_START.match(t):
        return False
    if chr(13) + chr(10) in t:  # CRLF text comes from a script or a paste, not a chat box
        return False
    if looks_like_code_or_paste(t):
        return False
    return bool(re.search(r"[A-Za-z]", t))


# ---------------------------------------------------------------- writer
class Out:
    def __init__(self, path, since):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.fh = open(path, "w", encoding="utf-8")
        self.since = since or ""
        self.seen = set()
        self.counts = Counter()
        self.long_repeats = Counter()
        self.rows = []

    def add(self, src, kind, register, text, at="", ctx=""):
        at = (at or "")[:19]
        if self.since and at and at[:10] < self.since:
            return
        text = clean(text)
        if not keep(text):
            return
        text = redact(text)
        norm = re.sub(r"\W+", " ", text.lower()).strip()
        h = hashlib.md5((kind + norm).encode("utf-8")).hexdigest()
        if h in self.seen:
            if len(norm) > 80:
                self.long_repeats[h] += 1
            return
        self.seen.add(h)
        self.rows.append({"id": h[:12], "src": src, "kind": kind, "register": register,
                          "at": at, "ctx": redact(ctx or "")[:80], "text": text[:20000]})
        self.counts[src] += 1

    def close(self):
        # a long message that shows up 3+ times is a template or a script, not a person
        bad = {h[:12] for h, n in self.long_repeats.items() if n >= 2}
        n = 0
        for r in self.rows:
            if r["id"] in bad:
                continue
            self.fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
        self.fh.close()
        return n


def ts_from_epoch(x):
    import datetime
    try:
        return datetime.datetime.fromtimestamp(float(x), datetime.timezone.utc).isoformat()[:19]
    except Exception:
        return ""


# ---------------------------------------------------------------- sources
def claude_code(out, root, include_headless):
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        if "subagents" in path.replace("\\", "/"):
            continue
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"user"' not in line:
                    continue
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                if m.get("type") != "user" or m.get("isMeta") or m.get("isSidechain") or m.get("toolUseResult"):
                    continue
                origin = (m.get("origin") or {}).get("kind")
                if origin and origin != "human":
                    continue
                if not include_headless and m.get("entrypoint") in HEADLESS and origin != "human":
                    continue
                c = (m.get("message") or {}).get("content")
                if isinstance(c, list):
                    parts = [b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"]
                    if not parts:
                        continue
                    c = "\n".join(parts)
                if not isinstance(c, str):
                    continue
                ctx = os.path.basename((m.get("cwd") or "").rstrip("\\/"))
                out.add("claude-code", "ai_chat", "typed-to-ai", c, m.get("timestamp"), ctx)


def codex(out, root):
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        ctx = ""
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                p = m.get("payload") or {}
                if m.get("type") == "session_meta":
                    ctx = os.path.basename((p.get("cwd") or "").rstrip("\\/"))
                    if (p.get("thread_source") or "").startswith("agent") and p.get("source") == "exec":
                        break
                if m.get("type") == "event_msg" and p.get("type") == "user_message":
                    out.add("codex", "ai_chat", "typed-to-ai", p.get("message", ""), m.get("timestamp"), ctx)
                elif m.get("type") == "response_item" and p.get("role") == "user":
                    for b in p.get("content") or []:
                        if isinstance(b, dict) and b.get("type") == "input_text":
                            out.add("codex", "ai_chat", "typed-to-ai", b.get("text", ""), m.get("timestamp"), ctx)


def read_json_maybe_zip(path, inner_suffix):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(inner_suffix):
                    return json.loads(z.read(n).decode("utf-8"))
        raise SystemExit(f"no {inner_suffix} inside {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def claude_export(out, path):
    """claude.ai -> Settings -> Privacy -> Export data -> conversations.json"""
    for conv in read_json_maybe_zip(path, "conversations.json"):
        ctx = conv.get("name") or ""
        for msg in conv.get("chat_messages") or []:
            if msg.get("sender") != "human":
                continue
            t = msg.get("text") or "\n".join(b.get("text", "") for b in msg.get("content") or [] if b.get("type") == "text")
            out.add("claude.ai", "ai_chat", "typed-to-ai", t, msg.get("created_at"), ctx)


def chatgpt_export(out, path):
    """ChatGPT -> Settings -> Data controls -> Export -> conversations.json"""
    for conv in read_json_maybe_zip(path, "conversations.json"):
        ctx = conv.get("title") or ""
        for node in (conv.get("mapping") or {}).values():
            msg = node.get("message") or {}
            if (msg.get("author") or {}).get("role") != "user":
                continue
            content = msg.get("content") or {}
            if content.get("content_type") != "text":
                continue
            t = "\n".join(p for p in content.get("parts") or [] if isinstance(p, str))
            out.add("chatgpt", "ai_chat", "typed-to-ai", t, ts_from_epoch(msg.get("create_time") or 0), ctx)


def discord(out, path):
    """Discord -> Settings -> Data & Privacy -> Request data. Folder or the zip."""
    files = {}
    if zipfile.is_zipfile(path):
        z = zipfile.ZipFile(path)
        for n in z.namelist():
            files[n] = (lambda n=n: z.read(n).decode("utf-8", "replace"))
    else:
        for p in glob.glob(os.path.join(path, "**", "*"), recursive=True):
            if os.path.isfile(p):
                files[os.path.relpath(p, path).replace("\\", "/")] = (lambda p=p: open(p, encoding="utf-8", errors="replace").read())
    for name, read in files.items():
        low = name.lower()
        if "messages/" not in low or not (low.endswith("messages.json") or low.endswith("messages.csv")):
            continue
        ctx = "discord"
        chan = name.rsplit("/", 1)[0] + "/channel.json"
        if chan in files:
            try:
                info = json.loads(files[chan]())
                ctx = "discord DM" if info.get("type") in (1, 3, "DM", "GROUP_DM") else "discord server: " + str((info.get("guild") or {}).get("name", ""))
            except Exception:
                pass
        raw = read()
        rows = json.loads(raw) if low.endswith(".json") else list(csv.DictReader(io.StringIO(raw)))
        for r in rows:
            out.add("discord", "chat", "typed-casual", r.get("Contents") or r.get("contents") or "",
                    (r.get("Timestamp") or r.get("timestamp") or "").replace(" ", "T"), ctx)


def strip_reply(body):
    lines = []
    for l in body.splitlines():
        if re.match(r"^\s*>", l):
            continue
        if re.match(r"^\s*(On .{5,200} wrote:|-----Original Message-----|From: .+|Sent from my )", l):
            break
        if l.strip() == "--":
            break
        lines.append(l)
    return "\n".join(lines).strip()


def mbox(out, path, me):
    me = (me or "").lower()
    for msg in mailbox.mbox(path):
        frm = (msg.get("From") or "").lower()
        if me and me not in frm:
            continue
        body = ""
        parts = msg.walk() if msg.is_multipart() else [msg]
        for part in parts:
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
                except Exception:
                    continue
                break
        import email.utils
        try:
            at = email.utils.parsedate_to_datetime(msg.get("Date")).isoformat()
        except Exception:
            at = ""
        to = (msg.get("To") or "")
        out.add("email", "email", "email", strip_reply(body), at, "to " + to.split("@")[-1][:40] if "@" in to else "")


def read_doc(p):
    ext = os.path.splitext(p)[1].lower()
    if ext == ".docx":
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
        return "\n\n".join(html.unescape("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", x, re.S))) for x in paras)
    raw = open(p, encoding="utf-8", errors="replace").read()
    if ext in (".html", ".htm"):
        raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.S | re.I)
        raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return raw


def iter_files(paths, exts):
    for p in paths:
        if os.path.isdir(p):
            for f in glob.glob(os.path.join(p, "**", "*"), recursive=True):
                if os.path.splitext(f)[1].lower() in exts:
                    yield f
        elif os.path.isfile(p):
            yield p


def docs(out, paths, kind, register):
    import datetime
    for f in iter_files(paths, {".txt", ".md", ".docx", ".html", ".htm"}):
        try:
            t = read_doc(f)
        except Exception as e:
            print(f"  skip {f}: {e}", file=sys.stderr)
            continue
        at = datetime.datetime.fromtimestamp(os.path.getmtime(f), datetime.timezone.utc).isoformat()[:19]
        # documents are long on purpose: bypass the paste filter by adding paragraph by paragraph
        for i, para in enumerate(re.split(r"\n\s*\n", t)):
            para = para.strip()
            if len(para.split()) >= 4:
                out.add("files", kind, register, para[:2900], at, os.path.basename(f))


def transcripts(out, paths, speaker):
    import datetime
    for f in iter_files(paths, {".srt", ".vtt", ".txt", ".json"}):
        raw = open(f, encoding="utf-8", errors="replace").read()
        if f.lower().endswith(".json"):
            try:
                j = json.loads(raw)
                raw = j.get("text") or " ".join(s.get("text", "") for s in j.get("segments", []))
            except Exception:
                continue
        lines, current = [], None
        for l in raw.splitlines():
            l = l.strip()
            if not l or l == "WEBVTT" or l.isdigit() or "-->" in l or re.match(r"^(NOTE|Kind:|Language:)", l):
                continue
            l = re.sub(r"<[^>]+>", "", l)
            m = re.match(r"^\[?([A-Z][\w .'\-]{0,30})\]?:\s+(.*)$", l)
            if m:
                current, l = m.group(1).strip().lower(), m.group(2)
            if speaker and current is not None and current != speaker.lower():
                continue  # someone else talking; unlabelled lines carry the last label
            if lines and lines[-1] == l:
                continue  # auto-captions repeat lines
            lines.append(l)
        text = " ".join(lines)
        at = datetime.datetime.fromtimestamp(os.path.getmtime(f), datetime.timezone.utc).isoformat()[:19]
        # chunk into ~120-word pieces so one long transcript doesn't dominate
        words = text.split()
        for i in range(0, len(words), 120):
            chunk = " ".join(words[i:i + 120])
            if len(chunk.split()) >= 8:
                out.add("transcript", "transcript", "spoken", chunk, at, os.path.basename(f))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--since", default="")
    ap.add_argument("--claude-code", nargs="?", const=os.path.join(HOME, ".claude", "projects"))
    ap.add_argument("--codex", nargs="?", const=os.path.join(HOME, ".codex", "sessions"))
    ap.add_argument("--claude-export")
    ap.add_argument("--chatgpt-export")
    ap.add_argument("--discord")
    ap.add_argument("--mbox")
    ap.add_argument("--me", help="your email address, to keep only mail you sent")
    ap.add_argument("--docs", nargs="*", default=[], help="files/folders of writing you did yourself (no AI rewrites)")
    ap.add_argument("--posts", nargs="*", default=[], help="files/folders of public posts/captions you wrote")
    ap.add_argument("--transcripts", nargs="*", default=[], help=".srt/.vtt/.txt/.json of you talking")
    ap.add_argument("--speaker", help="keep only this speaker's lines in transcripts")
    ap.add_argument("--include-headless", action="store_true", help="also read `claude -p` / SDK runs (usually scripts, not you)")
    ap.add_argument("--no-auto", action="store_true", help="don't auto-detect Claude Code / Codex history")
    a = ap.parse_args()

    out = Out(a.out, a.since)
    cc = a.claude_code or (None if a.no_auto else os.path.join(HOME, ".claude", "projects"))
    cx = a.codex or (None if a.no_auto else os.path.join(HOME, ".codex", "sessions"))
    if cc and os.path.isdir(cc):
        claude_code(out, cc, a.include_headless)
    if cx and os.path.isdir(cx):
        codex(out, cx)
    if a.claude_export:
        claude_export(out, a.claude_export)
    if a.chatgpt_export:
        chatgpt_export(out, a.chatgpt_export)
    if a.discord:
        discord(out, a.discord)
    if a.mbox:
        mbox(out, a.mbox, a.me)
    if a.docs:
        docs(out, a.docs, "doc", "writing")
    if a.posts:
        docs(out, a.posts, "post", "public-post")
    if a.transcripts:
        transcripts(out, a.transcripts, a.speaker)
    n = out.close()
    import datetime, shlex
    res = {"written": n, "by_source": dict(out.counts), "out": os.path.abspath(a.out),
           "built": datetime.date.today().isoformat(),
           "command": "python3 collect.py " + " ".join(shlex.quote(x) for x in sys.argv[1:])}
    with open(os.path.splitext(a.out)[0] + ".manifest.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
