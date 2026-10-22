"""Step 3: build AI gap-fill jobs. For each language, list the headwords whose
primary sense has no Wiktionary translation, plus a hidden control sample of
words Wiktionary does cover (used to estimate accuracy per language).

Usage: python3 03_fill_jobs.py <words.jsonl> <jobs dir> [chunk size]
Writes <jobs dir>/in/<code>.<n>.tsv with columns: id, english, pos, meaning
and <jobs dir>/controls.json mapping code -> {id: [accepted translations]}.
"""
import sys, json, random
from pathlib import Path

HERE = Path(__file__).parent
LANGS = json.loads((HERE / "languages.json").read_text())
src, jobs = sys.argv[1], Path(sys.argv[2])
CHUNK = int(sys.argv[3]) if len(sys.argv) > 3 else 2500
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
rng = random.Random(7)
controls = {}
summary = {}
for L in LANGS:
    code = L["code"]
    rows, have = [], []
    for r in recs:
        e, s = primary(r)
        meaning = s["gloss"] or (e["defs"][0] if e["defs"] else "")
        row = (str(r["rank"]), clean(r["variants"][0]["word"]), e["pos"], clean(meaning)[:160])
        if code in s["tr"]:
            have.append((row, [i["w"] for i in s["tr"][code]]))
        else:
            rows.append(row)
    ctl = rng.sample(have, min(CONTROLS, len(have)))
    controls[code] = {row[0]: acc for row, acc in ctl}
    # mix controls into the first chunk so they look like any other row
    first = rows[:CHUNK] + [row for row, _ in ctl]
    rng.shuffle(first)
    chunks = [first] + [rows[i:i + CHUNK] for i in range(CHUNK, len(rows), CHUNK)]
    for n, ch in enumerate(chunks):
        if not ch:
            continue
        with open(jobs / "in" / f"{code}.{n}.tsv", "w", encoding="utf-8") as f:
            f.write("id\tenglish\tpos\tmeaning\n")
            for row in ch:
                f.write("\t".join(row) + "\n")
    summary[code] = len(rows)
(jobs / "controls.json").write_text(json.dumps(controls, ensure_ascii=False))
print(sum(summary.values()), "rows to fill;", len(list((jobs / "in").glob("*.tsv"))), "job files")
