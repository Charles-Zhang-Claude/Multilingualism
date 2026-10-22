"""Step 4: merge Wiktionary translations with AI gap fills and write the
published data set (served from the repo via jsDelivr and documented as the API).

Usage: python3 04_build.py <words.jsonl> <jobs dir> <out data dir>
Writes:
  meta.json            languages, regions, categories, counts, sources, licence
  index.json           every headword: [slug, word, pos, category, langs covered]
  words/<slug>.json    one file per headword (primary sense + other senses)
  langs/<code>.json    one file per language: primary translation of every headword
"""
import sys, json, re, csv, shutil, unicodedata, datetime, collections
from pathlib import Path
from nltk.corpus import wordnet as wn

HERE = Path(__file__).parent
LANGS = json.loads((HERE / "languages.json").read_text())
CODES = [L["code"] for L in LANGS]
src, jobs, outdir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
MAX_ITEMS = 4          # translations shown per language per sense
MAX_OTHER_SENSES = 5
MAX_OTHER_ITEMS = 2

REGIONS = [
    {"id": "european", "name": "European"},
    {"id": "asian", "name": "Asian"},
    {"id": "middle-eastern", "name": "Middle Eastern"},
    {"id": "african", "name": "African"},
    {"id": "austronesian", "name": "Austronesian"},
    {"id": "other", "name": "Constructed, classical and creole"},
]
SR_CYR = dict(zip("абвгдђежзијклљмнњопрстћуфхцчџш",
                  ["a","b","v","g","d","đ","e","ž","z","i","j","k","l","lj","m","n","nj","o","p","r","s","t","ć","u","f","h","c","č","dž","š"]))

# ---------- categories ----------
LEX = {
    "noun.feeling": "feelings", "verb.emotion": "feelings",
    "noun.food": "food", "verb.consumption": "food",
    "noun.animal": "animals",
    "noun.plant": "nature", "noun.object": "nature", "noun.phenomenon": "nature", "verb.weather": "nature",
    "noun.body": "body", "verb.body": "body", "noun.state": "body",
    "noun.time": "time",
    "noun.location": "places",
    "noun.person": "people", "verb.social": "people", "noun.group": "society",
    "noun.artifact": "things",
    "noun.communication": "communication", "verb.communication": "communication",
    "noun.act": "activities", "verb.competition": "activities", "verb.creation": "activities",
    "noun.event": "activities", "noun.process": "activities",
    "verb.motion": "movement", "noun.motive": "mind",
    "noun.substance": "materials",
    "noun.quantity": "numbers",
    "noun.attribute": "qualities", "noun.shape": "qualities", "noun.relation": "qualities",
    "noun.cognition": "mind", "verb.cognition": "mind", "verb.perception": "mind",
    "noun.possession": "money", "verb.possession": "money",
    "verb.change": "actions", "verb.contact": "actions", "verb.stative": "actions",
}
CATEGORIES = {
    "phrases": "Phrases and greetings", "feelings": "Feelings and emotions", "people": "People and family",
    "food": "Food and drink", "animals": "Animals", "nature": "Nature and weather", "body": "Body and health",
    "time": "Time and calendar", "places": "Places and countries", "numbers": "Numbers and amounts",
    "colors": "Colours", "things": "Things and objects", "communication": "Language and communication",
    "activities": "Activities and events", "movement": "Movement and travel", "actions": "Everyday verbs",
    "materials": "Materials and substances", "qualities": "Qualities and shapes", "mind": "Thinking and knowing",
    "money": "Money and ownership", "society": "Groups and society", "describing": "Describing words",
    "adverbs": "Adverbs", "grammar": "Grammar words",
}
COLORS = {"red","blue","green","yellow","black","white","orange","purple","pink","brown","grey","gray","violet",
          "gold","silver","beige","turquoise","cyan","magenta","indigo","maroon","navy","crimson","scarlet","lilac","colour","color"}
FAMILY = {"mother","father","brother","sister","son","daughter","family","wife","husband","grandmother","grandfather",
          "aunt","uncle","cousin","nephew","niece","parent","child","baby","grandson","granddaughter","friend"}
WN_POS = {"noun": "n", "verb": "v", "adj": "a", "adv": "r", "name": "n"}


def category(word, pos):
    lw = word.lower()
    if lw in COLORS:
        return "colors"
    if lw in FAMILY:
        return "people"
    if " " in word and pos in ("phrase", "intj", "proverb"):
        return "phrases"
    if pos in ("phrase", "intj", "proverb"):
        return "phrases"
    if pos == "num":
        return "numbers"
    if pos in ("pron", "prep", "conj", "det", "article", "particle", "postp"):
        return "grammar"
    p = WN_POS.get(pos)
    syns = wn.synsets(word.replace(" ", "_"), pos=p) if p else []
    if not syns and p:
        syns = wn.synsets(word.replace(" ", "_"))
    if pos == "adj":
        return "colors" if lw in COLORS else "describing"
    if pos == "adv":
        return "adverbs"
    if syns:
        c = LEX.get(syns[0].lexname())
        if c:
            return c
    if pos == "verb":
        return "actions"
    if pos == "name":
        return "places"
    if " " in word:
        return "phrases"
    return "things"


# ---------- helpers ----------
def primary(rec):
    e = rec["variants"][0]["entries"][0]
    covs = [len(s["tr"]) for s in e["senses"]]
    m = max(covs)
    for i, (s, c) in enumerate(zip(e["senses"], covs)):
        if c >= 0.5 * m:
            return e, i, s


def norm_cmp(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[\s.!?¡¿。？！、,，'’\-]", "", s)


def close_match(a, accepted):
    """Same word, allowing punctuation, accents, and a short inflectional ending (基本的な / 基本的)."""
    a = norm_cmp(a)
    for b in map(norm_cmp, accepted):
        if a == b or (min(len(a), len(b)) >= 2 and (a.startswith(b) or b.startswith(a)) and abs(len(a) - len(b)) <= 2):
            return True
    return False


def sr_roman(cyr):
    out = []
    for ch in cyr:
        lo = ch.lower()
        if lo in SR_CYR:
            t = SR_CYR[lo]
            out.append(t.capitalize() if ch != lo else t)
        else:
            out.append(ch)
    return "".join(out)


def trim(items):
    return [{k: v for k, v in it.items() if v} for it in items[:MAX_ITEMS]]


# ---------- AI fills ----------
IDS = json.loads((jobs / "ids_v1.json").read_text()) if (jobs / "ids_v1.json").exists() else {}  # pilot ids -> slugs
MEANINGS = json.loads((jobs / "meanings.json").read_text()) if (jobs / "meanings.json").exists() else {}
fills = collections.defaultdict(dict)   # code -> slug -> (w, r, conf)
for f in sorted((jobs / "out").glob("*.tsv")):
    code = f.name.split(".")[0]
    with open(f, encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            if not row or row[0] == "id" or len(row) < 2:
                continue
            w = row[1].strip().strip('"')
            if not w:
                continue
            r = row[2].strip() if len(row) > 2 else ""
            conf = row[3].strip().lower()[:1] if len(row) > 3 else "h"
            if code == "sr":
                r = sr_roman(w)
            if code == "he":
                w = re.sub(r"[֑-ׇ]", "", w)
            if code == "ar":
                w = re.sub(r"[ً-ْٰـ]", "", w)
            fid = row[0].strip()
            fills[code][IDS.get(fid, fid)] = (w, r, conf or "h")

controls = json.loads((jobs / "controls.json").read_text()) if (jobs / "controls.json").exists() else {}
agreement = {}
for code, ctl in controls.items():
    got = [(fills[code][IDS.get(i, i)][0], acc) for i, acc in ctl.items() if IDS.get(i, i) in fills.get(code, {})]
    if len(got) >= 10:
        hit = sum(1 for w, acc in got if close_match(w, acc))
        agreement[code] = {"checked": len(got), "matched": hit}

# ---------- build ----------
def clean(t):
    return (t or "").replace("\t", " ").replace("\n", " ").strip()

stale = 0
if outdir.exists():
    shutil.rmtree(outdir)
(outdir / "words").mkdir(parents=True)
(outdir / "langs").mkdir()

recs = [json.loads(l) for l in open(src, encoding="utf-8")]
index = []
lang_rows = collections.defaultdict(list)
stats = collections.Counter()
cat_count = collections.Counter()
for rec in recs:
    slug = rec["slug"]
    e, si, s = primary(rec)
    word = rec["variants"][0]["word"]
    cat = category(word, e["pos"])
    cat_count[cat] += 1
    tr = {}
    for code in CODES:
        items = s["tr"].get(code)
        if items:
            tr[code] = trim(items)
            stats[(code, "wikt")] += 1
        elif slug in fills.get(code, {}) and MEANINGS.get(code, {}).get(slug, None) not in (None, clean(s["gloss"] or (e["defs"][0] if e["defs"] else ""))[:160]):
            stale += 1  # fill was made for a different meaning; leave for the top-up pass
        elif slug in fills.get(code, {}):
            w, r, conf = fills[code][slug]
            it = {"w": w, "src": "ai"}
            if r:
                it["r"] = r
            if conf == "l":
                it["low"] = 1
            tr[code] = [it]
            stats[(code, "ai")] += 1
        if code in tr:
            first = tr[code][0]
            lang_rows[code].append([slug, first["w"], first.get("r", ""), 1 if first.get("src") == "ai" else 0])
    others = []
    for vi, v in enumerate(rec["variants"]):
        for ei, ent in enumerate(v["entries"]):
            for sj, sense in enumerate(ent["senses"]):
                if vi == 0 and ent is e and sj == si:
                    continue
                if len(sense["tr"]) < 5:
                    continue
                others.append({"word": v["word"], "pos": ent["pos"], "gloss": sense["gloss"],
                               "tr": {c: trim(sense["tr"][c])[:MAX_OTHER_ITEMS] for c in CODES if c in sense["tr"]}})
    others.sort(key=lambda o: -len(o["tr"]))
    doc = {
        "slug": slug,
        "word": word,
        "rank": rec["rank"],
        "category": cat,
        "pos": e["pos"],
        "gloss": s["gloss"],
        "definitions": list(dict.fromkeys(d.strip() for d in e["defs"] if d))[:3],
        "translations": tr,
        "otherSenses": others[:MAX_OTHER_SENSES],
        "alsoSpelled": [v["word"] for v in rec["variants"][1:]],
        "source": "https://en.wiktionary.org/wiki/" + word.replace(" ", "_"),
    }
    (outdir / "words" / f"{slug}.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    index.append([slug, word, e["pos"], cat, len(tr)])

for L in LANGS:
    code = L["code"]
    doc = {"code": code, "name": L["name"], "native": L["native"],
           "columns": ["slug", "translation", "romanization", "machine"], "rows": lang_rows[code]}
    (outdir / "langs" / f"{code}.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

n = len(recs)
meta = {
    "name": "Multilingualism",
    "version": datetime.date.today().isoformat(),
    "counts": {"words": n, "languages": len(LANGS),
               "wiktionary": sum(v for (c, k), v in stats.items() if k == "wikt"),
               "machine": sum(v for (c, k), v in stats.items() if k == "ai")},
    "regions": REGIONS,
    "categories": [{"id": k, "name": CATEGORIES[k], "count": cat_count[k]} for k in CATEGORIES if cat_count[k]],
    "languages": [{"code": L["code"], "name": L["name"], "native": L["native"], "region": L["region"],
                   **({"rtl": True} if L.get("rtl") else {}),
                   "wiktionary": stats[(L["code"], "wikt")], "machine": stats[(L["code"], "ai")],
                   **({"controlAgreement": agreement[L["code"]]} if L["code"] in agreement else {})}
                  for L in LANGS],
    "sources": [
        {"name": "Wiktionary (English edition), via kaikki.org / Wiktextract",
         "url": "https://kaikki.org/dictionary/English/", "license": "CC BY-SA 4.0 and GFDL"},
        {"name": "Machine-generated translations (Claude, Anthropic) for gaps, marked \"machine\"", "license": "CC BY-SA 4.0"},
        {"name": "Word frequencies: wordfreq", "url": "https://github.com/rspeer/wordfreq"},
        {"name": "Categories: Princeton WordNet 3.0 lexicographer files", "url": "https://wordnet.princeton.edu/"},
    ],
    "license": "CC BY-SA 4.0",
}
(outdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
(outdir / "index.json").write_text(json.dumps({"columns": ["slug", "word", "pos", "category", "languages"], "rows": index},
                                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("words", n, "| wiktionary cells", meta["counts"]["wiktionary"], "| machine cells", meta["counts"]["machine"])
print("stale fills skipped:", stale)
print("control agreement:", {k: f"{v['matched']}/{v['checked']}" for k, v in agreement.items()})
print("categories:", dict(cat_count.most_common()))
