"""Step 5: copy the built data set into the repository and consolidate the
machine translations into one reviewable TSV per language under sources/machine/.

Usage: python3 05_publish.py <built data dir> <jobs dir> <repo root>
"""
import sys, csv, json, shutil
from pathlib import Path


def is_header(row):  # the header line, not the headword "id" (whose slug is also "id")
    return row[0] == "id" and len(row) > 1 and row[1] in ("translation", "english")

built, jobs, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ids = json.loads((jobs / "ids_v1.json").read_text()) if (jobs / "ids_v1.json").exists() else {}
meanings = json.loads((jobs / "meanings.json").read_text()) if (jobs / "meanings.json").exists() else {}

shutil.rmtree(repo / "data", ignore_errors=True)
shutil.copytree(built, repo / "data")

per_lang = {}
for f in sorted((jobs / "out").glob("*.tsv")):
    code = f.name.split(".")[0]
    with open(f, encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if not row or is_header(row) or len(row) < 2 or not row[1].strip():
                continue
            slug = ids.get(row[0], row[0])
            per_lang.setdefault(code, {})[slug] = [
                slug, row[1].strip(), (row[2].strip() if len(row) > 2 else ""),
                (row[3].strip()[:1] if len(row) > 3 else ""), meanings.get(code, {}).get(slug, "")]
out = repo / "sources" / "machine"
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
total = 0
for code, rows in sorted(per_lang.items()):
    with open(out / f"{code}.tsv", "w", encoding="utf-8") as fh:
        fh.write("slug\ttranslation\tromanization\tconfidence\tmeaning\n")
        for r in sorted(rows.values()):
            fh.write("\t".join(x.replace("\t", " ") for x in r) + "\n")
            total += 1
print("published data; machine translations:", total, "in", len(per_lang), "languages")
