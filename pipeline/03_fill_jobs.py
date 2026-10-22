"""Step 3: build AI gap-fill jobs. For each language, list the headwords whose
primary sense has no Wiktionary translation, plus a hidden control sample of
words Wiktionary does cover (used to estimate accuracy per language).

Usage: python3 03_fill_jobs.py <words.jsonl> <jobs dir> [chunk size] [job tag]
A job tag (e.g. "t") names new jobs <code>.t<n> so earlier job files are left alone.
Writes <jobs dir>/in/<code>.<n>.tsv with columns: id (the headword slug), english, pos, meaning
and <jobs dir>/controls.json mapping code -> {slug: [accepted translations]}.
Words already filled in <jobs dir>/out/ are skipped, so jobs can be regenerated safely.
"""
import sys, json, random, csv
from pathlib import Path

HERE = Path(__file__).parent
LANGS = json.loads((HERE / "languages.json").read_text())
src, jobs = sys.argv[1], Path(sys.argv[2])
CHUNK = int(sys.argv[3]) if len(sys.argv) > 3 else 2500
TAG = sys.argv[4] if len(sys.argv) > 4 else ""
CONTROLS = 40
(jobs / "in").mkdir(parents=True, exist_ok=True)
(jobs / "out").mkdir(parents=True, exist_ok=True)


def primary(rec):
    e = rec["variants"][0]["entries"][0]
    covs = [len(s["tr"]) for s in e["senses"]]
    m = max(covs)
    for s, c in zip(e["senses"], covs):
        if c >= 0.5 * m:
            return e, s


def clean(t):
    return (t or "").replace("\t", " ").replace("\n", " ").strip()


recs = [json.loads(l) for l in open(src, encoding="utf-8")]
# earlier pilot jobs used numeric ids; ids_v1.json maps them to slugs
OLD_IDS = json.loads((jobs / "ids_v1.json").read_text()) if (jobs / "ids_v1.json").exists() else {}
MEANINGS_FILE = jobs / "meanings.json"   # code -> slug -> meaning the job was given
MEANINGS = json.loads(MEANINGS_FILE.read_text()) if MEANINGS_FILE.exists() else {}
current = {}
for r in recs:
    e, s = primary(r)
    current[r["slug"]] = clean(s["gloss"] or (e["defs"][0] if e["defs"] else ""))[:160]
done = {}  # a fill counts only if it was made for the meaning the headword has now
for f in (jobs / "out").glob("*.tsv"):
    code = f.name.split(".")[0]
    with open(f, encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if row and row[0] != "id" and len(row) > 1 and row[1].strip():
                slug = OLD_IDS.get(row[0], row[0])
                if MEANINGS.get(code, {}).get(slug) == current.get(slug):
                    done.setdefault(code, set()).add(slug)
rng = random.Random(7)
old_controls = {}
if (jobs / "controls.json").exists():
    for code, ctl in json.loads((jobs / "controls.json").read_text()).items():
        conv = {OLD_IDS.get(k, k): v for k, v in ctl.items()}
        if code in done and any(k in done[code] for k in conv):
            old_controls[code] = conv
controls = {}
summary = {}
for L in LANGS:
    code = L["code"]
    rows, have = [], []
    for r in recs:
        e, s = primary(r)
        meaning = s["gloss"] or (e["defs"][0] if e["defs"] else "")
        row = (r["slug"], clean(r["variants"][0]["word"]), e["pos"], clean(meaning)[:160])
        if code in s["tr"]:
            have.append((row, [i["w"] for i in s["tr"][code]]))
        elif r["slug"] not in done.get(code, ()):
            rows.append(row)
    prev = old_controls.get(code)
    if prev:  # language already has control results from a pilot: keep those, add none
        controls[code] = prev
        ctl = []
    else:
        ctl = rng.sample(have, min(CONTROLS, len(have)))
        controls[code] = {row[0]: acc for row, acc in ctl}
    # mix controls into the first chunk so they look like any other row
    first = rows[:CHUNK] + [row for row, _ in ctl]
    rng.shuffle(first)
    chunks = [first] + [rows[i:i + CHUNK] for i in range(CHUNK, len(rows), CHUNK)]
    for n, ch in enumerate(chunks):
        if not ch:
            continue
        with open(jobs / "in" / f"{code}.{TAG}{n}.tsv", "w", encoding="utf-8") as f:
            f.write("id\tenglish\tpos\tmeaning\n")
            for row in ch:
                f.write("\t".join(row) + "\n")
                MEANINGS.setdefault(code, {})[row[0]] = row[3]
    summary[code] = len(rows)
(jobs / "controls.json").write_text(json.dumps(controls, ensure_ascii=False))
MEANINGS_FILE.write_text(json.dumps(MEANINGS, ensure_ascii=False))
print(sum(summary.values()), "rows to fill;", len(list((jobs / "in").glob("*.tsv"))), "job files")
