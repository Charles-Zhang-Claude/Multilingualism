# Multilingualism

How to say English words and phrases in 108 languages, with romanizations. A fast, open alternative to sites like In Different Languages, live at **https://multilingualism.divooka.app**.

- About 9,850 everyday English words and phrases, chosen by frequency.
- Translations from the English Wiktionary's translation tables (via [kaikki.org](https://kaikki.org/) / Wiktextract), with gaps filled by machine translation and clearly labelled.
- A static single-page app with no server and no build step. All data is plain JSON in this repository, served through the jsDelivr CDN, which doubles as a free API.

## Using the data (API)

Every file under `data/` is available from jsDelivr. Pin a commit for immutable, fast-cached URLs:

```
https://cdn.jsdelivr.net/gh/Charles-Zhang-Claude/Multilingualism@<commit>/data/meta.json
https://cdn.jsdelivr.net/gh/Charles-Zhang-Claude/Multilingualism@<commit>/data/index.json
https://cdn.jsdelivr.net/gh/Charles-Zhang-Claude/Multilingualism@<commit>/data/words/thank_you.json
https://cdn.jsdelivr.net/gh/Charles-Zhang-Claude/Multilingualism@<commit>/data/langs/ja.json
```

| File | Contains |
| --- | --- |
| `meta.json` | Languages (code, names, region, coverage, machine-translation spot-check results), categories, counts, sources, licence. |
| `index.json` | Every headword as `[slug, word, pos, category, languages]`, most common first. |
| `words/{slug}.json` | One headword: meaning, definitions, `translations` keyed by language code, and `otherSenses`. |
| `langs/{code}.json` | One language: `[slug, translation, romanization, machine]` for every headword. |

A slug is the English headword in lower case with anything other than `a-z0-9` replaced by `_` (“Thank you” is `thank_you`). Translation objects carry `w` (the word), and optionally `r` (romanization), `k` (Japanese kana), `g` (gender: `m`, `f`, `n`, `c`), `src: "ai"` for machine translations and `low: 1` when the machine translation was flagged as uncertain.

The site also accepts URL parameters for links and in-browser lookups, for example `/?w=love&langs=fr,ja,zh-Hans` or `/?w=love&langs=fr,de&format=json`. The full list is on the site's [API page](https://multilingualism.divooka.app/api).

## Repository layout

| Path | What |
| --- | --- |
| `app/` | The single-page app: `index.html`, `app.js`, `styles.css`. `config.js` is generated at deploy time and pins the data commit. |
| `data/` | The published data set (generated; do not edit by hand). |
| `sources/machine/` | Every machine translation, one TSV per language, with the meaning it was made for. Review or correct these here. |
| `pipeline/` | Scripts that rebuild everything from a Wiktionary dump. |

## Rebuilding the data

Requires Python 3.11+ with `orjson`, `wordfreq` and `nltk` (WordNet corpus).

1. Download the English extract: `curl -O https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl`
2. `python3 pipeline/01_reduce.py kaikki.org-dictionary-English.jsonl reduced.jsonl` keeps English entries with translation tables.
3. `python3 pipeline/02_select.py reduced.jsonl words.jsonl 10000` maps languages (see `pipeline/languages.json`), normalizes spellings and picks headwords.
4. `python3 pipeline/03_fill_jobs.py words.jsonl fill/` lists the word and language gaps as translation jobs; `pipeline/fill_prompt.py` prints the instructions given to the translating model for each job.
5. `python3 pipeline/04_build.py words.jsonl fill/ build/` merges Wiktionary with the machine translations and writes the data set.
6. `python3 pipeline/05_publish.py build/ fill/ .` copies it into `data/` and refreshes `sources/machine/`.

A Wiktionary translation always takes precedence over a machine translation for the same word and language, so improving Wiktionary and rebuilding improves the site. `pipeline/devserver.py` serves a local preview at `http://127.0.0.1:8765`.

## Licence

The data (`data/`, `sources/`) is licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), as required by Wiktionary's licence; please credit “Multilingualism, from Wiktionary contributors”. The code (`app/`, `pipeline/`) is MIT licensed. See `LICENSE`.
