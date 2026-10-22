"""Check machine-translation outputs against their job inputs.

A good output has a header plus exactly one row per input id, in input order,
with a non-empty translation. Rows from another job (e.g. leaked by a shared
helper script) break the order or duplicate ids, so they show up here.

Usage: python3 validate_fills.py <jobs dir> [job ...]   (default: every out file with an input)
Prints one line per problem job; exit code 1 if any problem was found.
With --repair, rewrites a damaged output keeping only rows that form the
longest in-order run of input ids (first occurrence wins), so a re-run fills the rest.
"""
import sys, csv
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith("--")]
repair = "--repair" in sys.argv
jobs = Path(args[0])
names = args[1:] or sorted(p.stem for p in (jobs / "out").glob("*.tsv") if (jobs / "in" / p.name).exists())


import re


def is_header(row):  # the header line, not the headword "id" (whose slug is also "id")
    return row[0] == "id" and len(row) > 1 and row[1] in ("translation", "english")
SCRIPT = {  # languages with their own script: a translation must contain at least one such character
    "am": "\u1200-\u139f", "ar": "\u0600-\u06ff", "fa": "\u0600-\u06ff", "ps": "\u0600-\u06ff", "ur": "\u0600-\u06ff",
    "sd": "\u0600-\u06ff", "ug": "\u0600-\u06ff", "hy": "\u0530-\u058f", "ka": "\u10a0-\u10ff", "el": "\u0370-\u03ff\u1f00-\u1fff",
    "he": "\u0590-\u05ff", "yi": "\u0590-\u05ff", "hi": "\u0900-\u097f", "mr": "\u0900-\u097f", "ne": "\u0900-\u097f",
    "bn": "\u0980-\u09ff", "pa": "\u0a00-\u0a7f", "gu": "\u0a80-\u0aff", "or": "\u0b00-\u0b7f", "ta": "\u0b80-\u0bff",
    "te": "\u0c00-\u0c7f", "kn": "\u0c80-\u0cff", "ml": "\u0d00-\u0d7f", "si": "\u0d80-\u0dff", "th": "\u0e00-\u0e7f",
    "lo": "\u0e80-\u0eff", "my": "\u1000-\u109f", "km": "\u1780-\u17ff", "ko": "\uac00-\ud7af\u1100-\u11ff",
    "ja": "\u3040-\u30ff\u4e00-\u9fff", "zh-Hans": "\u4e00-\u9fff", "zh-Hant": "\u4e00-\u9fff",
    "ru": "\u0400-\u04ff", "uk": "\u0400-\u04ff", "be": "\u0400-\u04ff", "bg": "\u0400-\u04ff", "mk": "\u0400-\u04ff",
    "sr": "\u0400-\u04ff", "kk": "\u0400-\u04ff", "ky": "\u0400-\u04ff", "mn": "\u0400-\u04ff", "tg": "\u0400-\u04ff", "tt": "\u0400-\u04ff",
}


def rows(path):
    with open(path, encoding="utf-8") as fh:
        return [r for r in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE) if r and not is_header(r)]


bad = 0
for name in names:
    inp = [r[0] for r in rows(jobs / "in" / f"{name}.tsv")]
    out_path = jobs / "out" / f"{name}.tsv"
    if not out_path.exists():
        print(f"{name}: no output yet")
        continue
    out = rows(out_path)
    ids = [r[0] for r in out]
    empty = sum(1 for r in out if len(r) < 2 or not r[1].strip())
    code = name.split(".")[0]
    if code in SCRIPT:
        rx = re.compile("[" + SCRIPT[code] + "]")
        wrong = [r for r in out if len(r) > 1 and r[1].strip() and not rx.search(r[1])]
        if wrong:
            print(f"{name}: {len(wrong)} rows not in the expected script, e.g. {[r[1] for r in wrong[:3]]}")
    if ids == inp and not empty:
        continue
    bad += 1
    pos = {k: i for i, k in enumerate(inp)}
    seen, kept, last = set(), [], -1
    for r in out:  # greedy in-order run: keeps the job's own rows, drops leaked blocks and repeats
        i = pos.get(r[0])
        if i is None or r[0] in seen or i <= last or len(r) < 2 or not r[1].strip():
            continue
        seen.add(r[0]); kept.append(r); last = i
    print(f"{name}: {len(out)} rows for {len(inp)} inputs, {len(ids) - len(set(ids))} duplicate ids, "
          f"{sum(1 for k in ids if k not in pos)} unknown ids, {empty} empty; {len(kept)} rows usable")
    if repair:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("id\ttranslation\tromanization\tconfidence\n")
            for r in kept:
                fh.write("\t".join(r) + "\n")
sys.exit(1 if bad else 0)
