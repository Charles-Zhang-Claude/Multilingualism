"""Step 2: map Wiktionary translations onto our language list, normalize them,
choose the ~10k most useful English headwords, and write the merged dataset.

Usage: python3 02_select.py <reduced.jsonl> <out words.jsonl> [target_count]
Output: one JSON object per headword (merged across parts of speech).
"""
import sys, re, json, unicodedata, collections
from pathlib import Path
import orjson
from wordfreq import zipf_frequency

HERE = Path(__file__).parent
LANGS = json.loads((HERE / "languages.json").read_text())
src, dst = sys.argv[1], sys.argv[2]
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 10000
MAX_PHRASES = 1500
SKIP_POS = {"prefix", "suffix", "infix", "interfix", "affix", "character", "symbol",
            "punct", "abbrev", "circumfix", "combining_form", "contraction", "romanization"}

# Wiktionary language name -> our codes (Serbo-Croatian and Chinese fan out)
NAME_MAP = collections.defaultdict(list)
for L in LANGS:
    for n in L["wikt"]:
        NAME_MAP[n].append(L["code"])
NAME_MAP["Serbo-Croatian"] += ["sr", "hr", "bs"]
NAME_MAP["Chinese Mandarin"] += ["zh-Hans", "zh-Hant"]
NAME_MAP["Māori"] += ["mi"]
NAME_MAP["West-Frisian"] += ["fy"]
NAME_MAP["Iranian Persian"] += ["fa"]
for bad in ("Chinese",):  # plain "Chinese" in kaikki is mostly Hokkien/Dungan
    NAME_MAP.pop(bad, None)
NAME_MAP["Kurdish"] = ["kmr"]

EXCLUDE_TAGS = {
    "ar": lambda tg: any("Arabic" in t for t in tg) or "Classical" in tg,
    "mn": lambda tg: "Mongolian script" in tg or "China" in tg,
    "az": lambda tg: "Cyrillic" in tg or "Arabic" in tg,
    "uz": lambda tg: "Cyrillic" in tg or "Arabic" in tg,
    "ms": lambda tg: "Jawi" in tg,
    "pa": lambda tg: "Shahmukhi" in tg or "Western-Punjabi" in tg,
    "kk": lambda tg: "Latin" in tg or "Arabic" in tg,
    "ky": lambda tg: "Arabic" in tg,
    "tk": lambda tg: "Cyrillic" in tg,
    "tt": lambda tg: "Latin" in tg,
    "tg": lambda tg: "Latin" in tg or "Persian" in tg,
    "ug": lambda tg: "Cyrillic" in tg or "Latin" in tg,
    "fa": lambda tg: "Classical Persian" in tg or "Dari" in tg or "Tajik" in tg,
    "zh-Hans": lambda tg: "Taiwan" in tg,
    "zh-Hant": lambda tg: "Mainland-China" in tg,
    "sr": lambda tg: "Latin" in tg or "Arebica" in tg or "Croatia" in tg or "Bosnia" in tg or "Glagolitic" in tg,
    "hr": lambda tg: "Cyrillic" in tg or "Arebica" in tg or "Serbia" in tg or "Glagolitic" in tg,
    "bs": lambda tg: "Cyrillic" in tg or "Arebica" in tg or "Glagolitic" in tg,
    "no": lambda tg: "Nynorsk" in tg,
}
BAD_TAGS = {"obsolete", "archaic", "dated", "rare", "vulgar", "offensive", "derogatory",
            "historical", "nonstandard", "proscribed", "misspelling", "Internet", "dialectal"}
GENDER = {"masculine": "m", "feminine": "f", "neuter": "n", "common-gender": "c"}

SR_CYR = dict(zip("абвгдђежзијклљмнњопрстћуфхцчџш",
                  ["a","b","v","g","d","đ","e","ž","z","i","j","k","l","lj","m","n","nj","o","p","r","s","t","ć","u","f","h","c","č","dž","š"]))
VOWELS = set("aeiouAEIOUаеиоуАЕИОУrRрРyYæøåœ")


def strip_accents(s, vowels_only=True):
    out = []
    for ch in unicodedata.normalize("NFD", s):
        if unicodedata.combining(ch) and ch in "̀́̂̄̆̏̑" and out and (not vowels_only or out[-1] in VOWELS):
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def norm_word(code, w):
    w = w.strip()
    w = re.sub(r"\s*\((?:[a-z]{2,3}|[a-z]{2}-[A-Za-z]+)\)$", "", w)  # trailing "(ku)" style codes
    if code in ("sr", "hr", "bs"):
        w = strip_accents(w)
    elif code in ("ru", "uk", "be", "bg", "mk", "rw"):
        w = unicodedata.normalize("NFC", unicodedata.normalize("NFD", w).replace("́", "").replace("̀", ""))
        w = w.replace("ѐ", "е").replace("ѝ", "и") if code in ("ru", "uk", "be") else w
    elif code == "ar":
        w = re.sub(r"[ً-ْٰـ]", "", w)
    elif code == "he":
        w = re.sub(r"[֑-ׇ]", "", w)
    return w


def sr_roman(cyr):
    return "".join(SR_CYR.get(ch, SR_CYR.get(ch.lower(), ch).capitalize() if ch.lower() in SR_CYR else ch) for ch in cyr)


def ijekavian_of(a, b):
    """True if b is the ijekavian counterpart of ekavian a (vòleti/vòljeti, mleko/mlijeko)."""
    if a == b or len(b) <= len(a):
        return False
    return b.replace("ije", "e").replace("je", "e") == a or b.replace("ije", "e") == a


def build_items(code, trs):
    """trs: Wiktionary translations already mapped to this language code."""
    items = []
    seen = set()
    for t in trs:
        tags = set(t.get("t", [])) | set(t.get("rt", []))
        if code in EXCLUDE_TAGS and EXCLUDE_TAGS[code](tags):
            continue
        if code == "no" and t["l"] == "Norwegian" and "Bokmål" not in tags and any(x["l"] == "Norwegian Bokmål" for x in trs):
            continue
        w = t["w"]
        if code in ("zh-Hans", "zh-Hant"):
            if "/" in w:
                trad, simp = [p.strip() for p in w.split("/", 1)]
                w = simp if code == "zh-Hans" else trad
        w = norm_word(code, w)
        if not w or w in seen or len(w) > 60:
            continue
        seen.add(w)
        it = {"w": w}
        r = t.get("r")
        if code == "sr":
            r = sr_roman(w)
        if r and code not in ("hr", "bs"):
            if code in ("ru", "uk", "be", "bg", "mk"):
                r = strip_accents(r, vowels_only=False)
            it["r"] = r
        if code == "ja" and t.get("a"):
            it["k"] = t["a"]  # kana reading
        g = "".join(GENDER[x] for x in ("masculine", "feminine", "neuter", "common-gender") if x in tags)
        if g:
            it["g"] = g
        quality = sum(1 for x in tags if x in BAD_TAGS)
        if quality:
            it["x"] = 1  # de-prioritised (archaic/rare/etc.)
        items.append(it)
    if code in ("sr", "hr", "bs"):
        ws = [i["w"] for i in items]
        drop = set()
        for a in ws:
            for b in ws:
                if ijekavian_of(a, b):
                    drop.add(b if code == "sr" else a)
        items = [i for i in items if i["w"] not in drop]
    items.sort(key=lambda i: i.get("x", 0))  # stable: keep Wiktionary order otherwise
    for i in items:
        i.pop("x", None)
    return items


def short_gloss(g):
    return g.strip()


# ---- pass 1: group entries by headword ----
groups = collections.defaultdict(list)
for line in open(src, "rb"):
    d = orjson.loads(line)
    if d["pos"] in SKIP_POS:
        continue
    w = d["word"]
    if not re.match(r"^[A-Za-z][A-Za-z' .\-!?,]*$", w) or len(w) > 40:
        continue
    if "..." in w or "…" in w:
        continue
    if d["pos"] == "name" and any(re.search(r"given name|surname|diminutive of", x["gloss"]) for x in d["senses"][:2]):
        continue
    groups[w].append(d)

records = []
for w, ents in groups.items():
    entries = []
    covered = set()
    for d in ents:
        by_sense = collections.OrderedDict()
        for t in d["tr"]:
            codes = NAME_MAP.get(t["l"])
            if not codes:
                continue
            s = t.get("s") or ""
            by_sense.setdefault(s, collections.defaultdict(list))
            for c in codes:
                by_sense[s][c].append(t)
        senses = []
        for s, per in by_sense.items():
            tr = {}
            for c, trs in per.items():
                items = build_items(c, trs)
                if items:
                    tr[c] = items
            if tr:
                senses.append({"gloss": short_gloss(s) if s else None, "tr": tr})
                covered.update(tr.keys())
        if senses:
            entries.append({
                "pos": d["pos"],
                "defs": [x["gloss"] for x in d["senses"][:4]],
                "cats": d["cats"],
                "senses": senses,
            })
    if not entries:
        continue
    multi = " " in w.strip()
    z = zipf_frequency(w, "en")
    records.append({"word": w, "zipf": z, "multi": multi, "cov": len(covered), "entries": entries})

print("headwords with mapped translations:", len(records))

# ---- choose headwords ----
def score(r):
    # frequency first; coverage breaks ties and lifts well-translated phrases
    return r["zipf"] + min(r["cov"], 100) / 40.0

singles = [r for r in records if not r["multi"] and r["cov"] >= 3 and r["zipf"] > 0]
phrases = [r for r in records if r["multi"] and r["cov"] >= 12]
singles.sort(key=score, reverse=True)
phrases.sort(key=lambda r: (r["cov"] + 8 * r["zipf"]), reverse=True)
phrases = phrases[:MAX_PHRASES]
chosen = singles[: TARGET - len(phrases)] + phrases

# merge case variants into one slug ("may" + "May")
by_slug = collections.OrderedDict()
for r in sorted(chosen, key=score, reverse=True):
    slug = re.sub(r"[^a-z0-9]+", "_", r["word"].lower()).strip("_")
    if not slug:
        continue
    by_slug.setdefault(slug, []).append(r)

out = open(dst, "w", encoding="utf-8")
total_cells = 0
for rank, (slug, rs) in enumerate(by_slug.items(), 1):
    rs.sort(key=lambda r: (r["word"] != r["word"].lower(), -r["zipf"]))
    rec = {"slug": slug, "rank": rank, "word": rs[0]["word"],
           "zipf": round(max(r["zipf"] for r in rs), 2),
           "variants": [{"word": r["word"], "entries": r["entries"]} for r in rs]}
    total_cells += len({c for r in rs for e in r["entries"] for s in e["senses"] for c in s["tr"]})
    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
out.close()
n = len(by_slug)
print("chosen headwords:", n, "phrases:", sum(1 for rs in by_slug.values() if rs[0]["multi"]))
print("language cells covered by Wiktionary:", total_cells, "of", n * len(LANGS), f"({100*total_cells/(n*len(LANGS)):.1f}%)")
