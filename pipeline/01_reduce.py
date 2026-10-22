"""Step 1: stream the kaikki.org English Wiktionary extract and keep only
English entries that have translation tables, with the fields we need.

Usage: python3 01_reduce.py <kaikki-English.jsonl> <out reduced.jsonl>
"""
import sys
import orjson

src, dst = sys.argv[1], sys.argv[2]
kept = 0
with open(src, "rb") as f, open(dst, "wb") as out:
    for line in f:
        if b'"translations"' not in line:
            continue
        d = orjson.loads(line)
        if d.get("lang_code") != "en":
            continue
        trs = d.get("translations") or []
        # translations can also live inside senses in some extracts
        for s in d.get("senses") or []:
            trs.extend(s.get("translations") or [])
        if not trs:
            continue
        senses = []
        cats = set()
        for s in d.get("senses") or []:
            g = (s.get("glosses") or [None])[0]
            if g:
                senses.append({"gloss": g, "tags": s.get("tags") or []})
            for c in s.get("categories") or []:
                name = c.get("name") if isinstance(c, dict) else c
                if name and name.startswith("en:"):
                    cats.add(name)
            for t in s.get("topics") or []:
                cats.add("topic:" + t)
        keep = []
        for t in trs:
            w = t.get("word")
            if not w:
                continue
            r = {"l": t.get("lang"), "c": t.get("code") or t.get("lang_code"), "w": w}
            for k_src, k_dst in (("roman", "r"), ("sense", "s"), ("tags", "t"), ("raw_tags", "rt"), ("alt", "a"), ("note", "n")):
                v = t.get(k_src)
                if v:
                    r[k_dst] = v
            keep.append(r)
        rec = {
            "word": d["word"],
            "pos": d.get("pos"),
            "senses": senses[:6],
            "cats": sorted(cats),
            "tr": keep,
        }
        out.write(orjson.dumps(rec) + b"\n")
        kept += 1
print("kept", kept)
