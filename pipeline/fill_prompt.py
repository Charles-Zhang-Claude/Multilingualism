"""Prints the instruction text for one AI gap-fill job.
Usage: python3 fill_prompt.py <jobs dir> <code>.<n>
"""
import sys, json
from pathlib import Path

HERE = Path(__file__).parent
LANGS = {L["code"]: L for L in json.loads((HERE / "languages.json").read_text())}
jobs, job = Path(sys.argv[1]), sys.argv[2]
code = job.split(".")[0]
L = LANGS[code]

NOTES = {
    "zh-Hans": "Mandarin Chinese in Simplified characters as used in mainland China. Romanization: Hanyu Pinyin with tone marks (e.g. ài, xièxie).",
    "zh-Hant": "Mandarin Chinese in Traditional characters as used in Taiwan. Romanization: Hanyu Pinyin with tone marks.",
    "ja": "Write as normally written (kanji/kana mix). Romanization: modified Hepburn (e.g. arigatō).",
    "ko": "Hangul. Romanization: Revised Romanization (e.g. saranghae).",
    "sr": "Serbian in Cyrillic script, ekavian standard (e.g. млеко, волети). Romanization: Serbian Latin (Gaj's alphabet).",
    "hr": "Croatian standard, ijekavian, Latin script; prefer Croatian vocabulary (kruh, tisuća, zrakoplov). No romanization.",
    "bs": "Bosnian standard, ijekavian, Latin script. No romanization.",
    "no": "Norwegian Bokmål.",
    "mn": "Mongolian in Cyrillic script. Romanization: a common Latin transliteration.",
    "kmr": "Northern Kurdish (Kurmanji) in Latin (Hawar) script. No romanization.",
    "pa": "Punjabi in Gurmukhi script. Romanization: common simplified transliteration.",
    "ms": "Malay in Latin (Rumi) script.",
    "uz": "Uzbek in Latin script (oʻ, gʻ).",
    "az": "Azerbaijani in Latin script.",
    "kk": "Kazakh in Cyrillic script. Romanization: common Latin transliteration.",
    "ky": "Kyrgyz in Cyrillic script. Romanization: common Latin transliteration.",
    "tt": "Tatar in Cyrillic script. Romanization: common Latin transliteration.",
    "tg": "Tajik in Cyrillic script. Romanization: common Latin transliteration.",
    "ug": "Uyghur in Arabic script (UEY). Romanization: Uyghur Latin (ULY).",
    "sd": "Sindhi in Perso-Arabic script. Romanization: common simplified transliteration.",
    "hmn": "White Hmong (Hmoob Dawb) in the Romanized Popular Alphabet (RPA).",
    "fil": "Filipino (Tagalog-based standard). Common Spanish/English loanwords are fine when that is what people actually say.",
    "ar": "Modern Standard Arabic, without short-vowel diacritics. Romanization: simple scholarly transliteration (e.g. ḥubb, shukran).",
    "he": "Modern Hebrew without niqqud. Romanization: simple modern transliteration (e.g. ahava, toda).",
    "yi": "Yiddish in Hebrew script, YIVO orthography. Romanization: YIVO romanization.",
    "fa": "Iranian Persian. Romanization: simple transliteration (e.g. eshq, merci).",
    "ps": "Pashto. Romanization: simple transliteration.",
    "ur": "Urdu. Romanization: simple transliteration (e.g. mohabbat, shukriya).",
    "ru": "No stress marks. Romanization: simple scientific/BGN-style transliteration.",
    "uk": "No stress marks. Romanization: Ukrainian national transliteration.",
    "be": "No stress marks. Romanization: common Latin transliteration.",
    "bg": "No stress marks. Romanization: Bulgarian streamlined system.",
    "mk": "Romanization: Macedonian Latin transliteration.",
    "el": "Modern Greek with monotonic accents. Romanization: simple ELOT-style (e.g. agápi).",
    "la": "Classical Latin spelling without macrons.",
    "eo": "Esperanto with proper diacritics (ĉ ĝ ĥ ĵ ŝ ŭ).",
    "ht": "Haitian Creole (Kreyòl ayisyen) standard orthography.",
    "haw": "Hawaiian with ʻokina and kahakō.",
    "mi": "Māori with macrons.",
    "sm": "Samoan.",
}
SCRIPT_ROMAN = {"am","ar","hy","be","bn","bg","zh-Hans","zh-Hant","ka","el","gu","he","hi","ja","kn","kk","km","ko","ky","lo","mk","ml","mr","mn","my","ne","or","ps","fa","pa","ru","sr","sd","si","tg","ta","tt","te","th","uk","ur","ug","yi"}

roman_rule = ("Fill the romanization column with a romanization of your translation." if code in SCRIPT_ROMAN
              else "Leave the romanization column empty (this language uses Latin script).")
src = jobs / "in" / f"{job}.tsv"
out = jobs / "out" / f"{job}.tsv"
n = sum(1 for _ in open(src, encoding="utf-8")) - 1

print(f"""You are producing dictionary translations from English into {L['name']} ({L['native']}) for an open multilingual word site. Native speakers will read these, so prefer the word or expression people actually use today in the standard language.

Input: {src}  ({n} rows, tab-separated, header: id, english, pos, meaning). "meaning" says which sense of the English headword to translate; translate THAT sense, matching the part of speech (verbs as the dictionary/citation form the language normally uses, nouns in the singular unless the English is plural, phrases as the natural equivalent expression rather than word-for-word). Proper names (countries, cities, seas, people) use the established {L['name']} name.

Language conventions: {NOTES.get(code, 'Standard written ' + L['name'] + ' in its usual script and spelling.')} {roman_rule}

Output: write {out} as tab-separated UTF-8 with header line `id\ttranslation\tromanization\tconfidence`, exactly one line per input id, in input order. Give ONE best translation per row (no alternatives, no slashes, no notes, no quotes). confidence is `h` when you are confident a native speaker would agree, `l` when you are unsure or had to coin/borrow a term. Never leave translation empty: if the language genuinely lacks a term, give the usual loanword or descriptive equivalent and mark `l`.

Isolation: other translators are working in parallel in this same machine. Never create, edit or run files in any shared scratchpad or temp directory; if you need a helper file, put it only under /home/claude/raw/fill/tmp/{job}/ (create it). Never touch any file in /home/claude/raw/fill/out/ except {out}.

How to work: read the input file in slices (e.g. 250 rows at a time with the Read tool's offset/limit), and write the output incrementally by appending each slice's lines to the output file with a Bash heredoc (cat >> FILE <<'EOF' ... EOF), creating the file with the header first. Do not write any scripts that call external translation services or the network; translate yourself. Do not modify the input file. When finished, verify with `wc -l` that the output has {n + 1} lines and that every input id appears once (fix any gaps), then reply with just: DONE {job} <row count> <number of l rows>.""")
