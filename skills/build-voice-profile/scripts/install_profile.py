#!/usr/bin/env python3
"""Install a finished voice profile as a personal Claude skill.

Takes the draft Claude wrote (SKILL.md + examples.md) and the measured profile.json, and:
  1. writes them to ~/.claude/skills/<skill-name>/ (backing up any older version first)
  2. copies lint.py beside them so the profile can check its own drafts
  3. writes refresh.md with the exact sources used, so a rebuild is one step
  4. zips the skill folder for uploading to claude.ai (Settings > Capabilities > Skills)
  5. adds a short pointer to ~/.claude/CLAUDE.md so every session knows the profile exists

Usage:
  python3 install_profile.py --work ~/.claude/idiolect/jordan --skill sound-like-jordan --name Jordan
                             [--skills-dir DIR] [--claude-md FILE | --no-claude-md]
Stdlib only.
"""
import argparse, datetime, json, os, shutil, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, help="the work folder: draft/, profile.json, corpus.manifest.json")
    ap.add_argument("--skill", required=True, help="skill folder name, e.g. sound-like-jordan")
    ap.add_argument("--name", required=True)
    ap.add_argument("--skills-dir", default=os.path.join(HOME, ".claude", "skills"))
    ap.add_argument("--claude-md", default=os.path.join(HOME, ".claude", "CLAUDE.md"))
    ap.add_argument("--no-claude-md", action="store_true")
    a = ap.parse_args()

    work = os.path.abspath(os.path.expanduser(a.work))
    draft = os.path.join(work, "draft")
    for need in ("SKILL.md", "examples.md"):
        if not os.path.isfile(os.path.join(draft, need)):
            sys.exit(f"missing {os.path.join(draft, need)}; write the draft first")
    prof_path = os.path.join(draft, "profile.json")
    if not os.path.isfile(prof_path):
        prof_path = os.path.join(work, "profile.json")
    if not os.path.isfile(prof_path):
        sys.exit("missing profile.json; run analyze.py first")

    # sanity: the skill names itself correctly and lints with registers that exist
    import re
    skill_md = open(os.path.join(draft, "SKILL.md"), encoding="utf-8").read()
    m = re.search(r"^name:\s*(\S+)", skill_md, re.M)
    if not m or m.group(1) != a.skill:
        sys.exit(f"draft SKILL.md frontmatter name is {m.group(1) if m else 'missing'!r}, expected {a.skill!r}")
    regs = set(json.load(open(prof_path, encoding="utf-8")).get("registers", {}))
    named = set(re.findall(r"--register\s+`?([\w\-]+)", skill_md)) | set(re.findall(r"\(`([\w\-]+)`\)", skill_md))
    unknown = sorted(k for k in named if k not in regs and not k.startswith("<"))
    if unknown:
        print(f"warning: SKILL.md mentions register keys not in profile.json: {', '.join(unknown)} (have: {', '.join(sorted(regs))})")

    dest = os.path.normpath(os.path.join(os.path.expanduser(a.skills_dir), a.skill))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if os.path.isdir(dest):
        backup = os.path.join(work, "backups", stamp)
        shutil.copytree(dest, backup)
        print(f"backed up the previous version to {backup}")
        shutil.rmtree(dest)
    os.makedirs(dest)

    for f in os.listdir(draft):
        src = os.path.join(draft, f)
        if os.path.isfile(src) and f != "profile.json":
            shutil.copy2(src, os.path.join(dest, f))
    shutil.copy2(prof_path, os.path.join(dest, "profile.json"))
    shutil.copy2(os.path.join(HERE, "lint.py"), os.path.join(dest, "lint.py"))

    manifest = {}
    mpath = os.path.join(work, "corpus.manifest.json")
    if os.path.isfile(mpath):
        manifest = json.load(open(mpath, encoding="utf-8"))
    cmd = manifest.get("command", "collect.py --out corpus.jsonl")
    refresh = f"""# Refreshing this profile

Built {datetime.date.today()} by the idiolect plugin (build-voice-profile skill) from:
{json.dumps(manifest.get("by_source", {}), indent=1)}

To refresh, ask Claude: "refresh my voice profile". With the plugin installed it re-runs the same sources:

    {cmd}

and keeps the "Corrections from {a.name}" section of SKILL.md as-is (those came from {a.name} directly and
outrank anything measured). The private working files (corpus, stats, samples) are in:

    {work}

Without the plugin: re-run collect.py and analyze.py from https://github.com/PandaPlayz2373/idiolect-profile
and update the numbers in SKILL.md by hand.
"""
    open(os.path.join(dest, "refresh.md"), "w", encoding="utf-8").write(refresh)

    # zip for claude.ai: the archive must contain the skill folder itself
    zpath = os.path.normpath(os.path.join(work, f"{a.skill}.zip"))
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(dest)):
            if f == "refresh.md":
                continue  # local paths mean nothing on claude.ai
            z.write(os.path.join(dest, f), f"{a.skill}/{f}")

    if not a.no_claude_md:
        md = os.path.expanduser(a.claude_md)
        start, end = f"<!-- idiolect:{a.skill} -->", f"<!-- /idiolect:{a.skill} -->"
        block = (f"{start}\n## Sounding like {a.name}\n"
                 f"Whenever something should sound like {a.name} (anything {a.name} will send, post, say, submit or sign as "
                 f"themselves, or \"in my voice\" / \"like me\" / \"less AI\"), load the `{a.skill}` skill first and follow it: "
                 f"pick the register, write it their way, then run its lint.py. Never invent facts about {a.name}.\n{end}\n")
        old = open(md, encoding="utf-8").read() if os.path.isfile(md) else ""
        if start in old and end in old:
            new = old[:old.index(start)] + block + old[old.index(end) + len(end) + 1:]
        else:
            new = (old.rstrip() + "\n\n" if old.strip() else "") + block
        os.makedirs(os.path.dirname(md), exist_ok=True)
        open(md, "w", encoding="utf-8").write(new)
        print(f"pointer written to {md}")

    print(json.dumps({"installed": dest, "files": sorted(os.listdir(dest)), "claude_ai_zip": zpath}, indent=1))


if __name__ == "__main__":
    main()
