/* Multilingualism: a static single-page dictionary.
   Data is fetched from the GitHub repository through jsDelivr (pinned to a commit),
   with raw.githubusercontent.com as a fallback. No build step, no dependencies. */
(() => {
  "use strict";

  const CFG = window.MLG_CONFIG || {};
  const BASES = [CFG.dataBase, CFG.fallbackBase].filter(Boolean);
  const main = document.getElementById("main");
  const POS_NAMES = {
    noun: "Noun", verb: "Verb", adj: "Adjective", adv: "Adverb", name: "Proper noun", phrase: "Phrase",
    intj: "Interjection", prep: "Preposition", pron: "Pronoun", conj: "Conjunction", num: "Number",
    det: "Determiner", article: "Article", particle: "Particle", proverb: "Proverb", prep_phrase: "Prepositional phrase",
    postp: "Postposition",
  };
  const POPULAR = ["love", "thank_you", "hello", "beautiful", "happy_birthday", "merry_christmas", "sorry", "water",
    "friend", "good_morning", "good_night", "i_love_you", "i_miss_you", "happy_new_year", "family", "mother",
    "father", "peace", "moon", "sun", "star", "cat", "dog", "wolf", "blue", "red", "black", "white", "light",
    "baby", "welcome", "goodbye", "please", "yes", "no", "how_are_you"];
  const HTML_LANG = { "kmr": "ku", "no": "nb", "sr": "sr-Cyrl", "hmn": "hmn", "fil": "fil" };
  const GENDER = { m: "masculine", f: "feminine", n: "neuter", c: "common gender" };
  const PAGE = 250;

  /* ---------------- utilities ---------------- */
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const slugify = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  const fmt = (n) => Number(n).toLocaleString("en");
  const norm = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } },
  };

  const cache = new Map();
  async function getJSON(path) {
    if (cache.has(path)) return cache.get(path);
    const p = (async () => {
      let lastErr;
      for (const base of BASES) {
        try {
          const r = await fetch(base + path);
          if (r.status === 404) { const e = new Error("not found"); e.notFound = true; throw e; }
          if (!r.ok) throw new Error("HTTP " + r.status);
          return await r.json();
        } catch (e) {
          lastErr = e;
          if (e.notFound) break;
        }
      }
      throw lastErr;
    })();
    cache.set(path, p);
    p.catch(() => cache.delete(path));
    return p;
  }
  const dataURL = (path) => (BASES[0] || "") + path;

  let META, INDEX, BY_SLUG, LANG_BY_CODE, ALPHA;
  async function meta() {
    if (!META) {
      META = await getJSON("meta.json");
      LANG_BY_CODE = new Map(META.languages.map((l) => [l.code, l]));
    }
    return META;
  }
  async function index() {
    if (!INDEX) {
      const d = await getJSON("index.json");
      INDEX = d.rows.map((r, i) => ({ slug: r[0], word: r[1], pos: r[2], cat: r[3], n: r[4], rank: i + 1, key: norm(r[1]) }));
      BY_SLUG = new Map(INDEX.map((r) => [r.slug, r]));
    }
    return INDEX;
  }
  function alphabetical() {
    if (!ALPHA) ALPHA = INDEX.slice().sort((a, b) => a.key.localeCompare(b.key, "en"));
    return ALPHA;
  }

  function langAttr(code) { return HTML_LANG[code] || code; }
  function regionOf(code) { return (LANG_BY_CODE.get(code) || {}).region || "other"; }
  function tintStyle(region) { return `--tint: var(--t-${region}); --accent: var(--i-${region});`; }

  /* "langs" URL parameter: codes or names, comma separated */
  function parseLangs(param) {
    if (!param) return null;
    const want = param.split(/[,\s]+/).map((s) => s.trim().toLowerCase()).filter(Boolean);
    const out = [];
    for (const w of want) {
      const hit = META.languages.find((l) => l.code.toLowerCase() === w || l.name.toLowerCase() === w || norm(l.native) === norm(w));
      if (hit && !out.includes(hit.code)) out.push(hit.code);
    }
    return out.length ? out : null;
  }

  let toastTimer;
  function toast(msg) {
    let el = document.querySelector(".toast");
    if (!el) { el = document.createElement("div"); el.className = "toast"; el.setAttribute("role", "status"); document.body.appendChild(el); }
    el.textContent = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.remove(), 1800);
  }
  async function copy(text, label) {
    try { await navigator.clipboard.writeText(text); toast(label || `Copied ${text}`); }
    catch (e) { toast("Copying isn't available in this browser"); }
  }

  function pinned() { return store.get("mlg-langs", []); }
  function setPinned(list) { store.set("mlg-langs", list); }

  /* ---------------- routing ---------------- */
  function navigate(href, replace) {
    if (replace) history.replaceState(null, "", href); else history.pushState(null, "", href);
    route();
  }
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a");
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (a.target || a.hasAttribute("download")) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin) return;
    if (url.pathname === location.pathname && url.search === location.search && url.hash) return; // in-page jump
    e.preventDefault();
    navigate(url.pathname + url.search + url.hash);
  });
  window.addEventListener("popstate", route);

  function setTitle(t) { document.title = t ? `${t} | Multilingualism` : "Multilingualism: say it in 108 languages"; }
  function setNav(which) {
    document.querySelectorAll("[data-nav]").forEach((a) => {
      if (a.dataset.nav === which) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
  }
  function focusMain() {
    const h = main.querySelector("h1");
    if (h) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); }
  }

  /* Footer "Suggest a correction": opens a new GitHub issue, prefilled with the word or language being viewed. */
  const ISSUES = "https://github.com/MethodoxTech/Multilingualism/issues/new";
  function setSuggestLink(name, arg) {
    const links = [document.getElementById("suggest-fix"), ...main.querySelectorAll("a.js-suggest")].filter(Boolean);
    if (!links.length) return;
    const h = main.querySelector("h1");
    let subject = h ? h.textContent.trim() : "";
    if (name === "lang") {
      const l = (parseLangs(arg) || [])[0];
      if (l) subject = LANG_BY_CODE.get(l).name;
    }
    const page = location.origin + location.pathname + location.search;
    let title = "Correction: ";
    let body = "";
    if (name === "word" && subject) {
      title += subject;
      body = `Word: ${subject}\nLanguage: \nShown translation: \nSuggested translation: \nNotes (source, region, why): \n\nPage: ${page}\n`;
    } else if (name === "lang" && subject) {
      title += `${subject} translations`;
      body = `Language: ${subject}\nWord: \nShown translation: \nSuggested translation: \nNotes (source, region, why): \n\nPage: ${page}\n`;
    } else {
      title = "";
      body = `Word: \nLanguage: \nShown translation: \nSuggested translation: \nNotes (source, region, why): \n\nPage: ${page}\n`;
    }
    const q = new URLSearchParams();
    if (title) q.set("title", title);
    q.set("body", body);
    links.forEach((a) => { a.href = `${ISSUES}?${q.toString()}`; });
  }

  let routeSeq = 0;
  async function route() {
    const seq = ++routeSeq;
    const url = new URL(location.href);
    const p = url.searchParams;
    const seg = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);
    const asJSON = (p.get("format") || "").toLowerCase() === "json";
    closeSuggest();
    try {
      await meta();
      if (seq !== routeSeq) return;
      let view;
      if (p.has("w")) view = ["word", p.get("w")];
      else if (p.has("q")) view = ["search", p.get("q")];
      else if (p.has("lang")) view = ["lang", p.get("lang")];
      else if (p.has("cat")) view = ["category", p.get("cat")];
      else if (p.has("letter")) view = ["letter", p.get("letter")];
      else if (seg[0] === "word" && seg[1]) view = ["word", seg[1]];
      else if (seg[0] === "words" && seg[1]) view = ["word", seg[1]];
      else if (seg[0] === "lang" && seg[1]) view = ["lang", seg[1]];
      else if (seg[0] === "category" && seg[1]) view = ["category", seg[1]];
      else if (seg[0] === "letter" && seg[1]) view = ["letter", seg[1]];
      else if (seg[0] === "dictionary" && seg[1]) view = ["letter", seg[1]];
      else if (seg[0] === "search") view = ["search", p.get("q") || ""];
      else if (["languages", "categories", "api", "about"].includes(seg[0]) && seg.length === 1) view = [seg[0]];
      else if (seg.length === 0) view = ["home"];
      else view = ["notfound"];

      const langs = parseLangs(p.get("langs"));
      const [name, arg] = view;
      if (asJSON) return await viewJSON(name, arg, langs, p);
      setNav(["languages", "lang"].includes(name) ? "languages" : ["categories", "category"].includes(name) ? "categories" : name);
      const fn = VIEWS[name];
      await fn(arg, langs, p, seq);
      if (seq !== routeSeq) return;
      setSuggestLink(name, arg);
      if (!url.hash) window.scrollTo(0, 0);
      else { const t = document.getElementById(url.hash.slice(1)); if (t) t.scrollIntoView(); }
      if (name !== "home") focusMain();
    } catch (e) {
      console.error(e);
      if (seq !== routeSeq) return;
      main.innerHTML = `<div class="state"><h1>Couldn't load the dictionary data</h1><p class="muted">The data server didn't respond (${esc(e.message)}). Check your connection and <a href="${esc(location.href)}">try again</a>.</p></div>`;
    }
  }

  /* ---------------- JSON view (URL API) ---------------- */
  async function resolveWord(arg) {
    const slug = slugify(arg);
    try { return await getJSON(`words/${slug}.json`); }
    catch (e) {
      if (!e.notFound) throw e;
      await index();
      const key = norm(arg);
      const hit = INDEX.find((r) => r.key === key);
      if (hit && hit.slug !== slug) return getJSON(`words/${hit.slug}.json`);
      return null;
    }
  }
  function filterWord(doc, langs) {
    if (!langs) return doc;
    const pick = (tr) => Object.fromEntries(langs.filter((c) => tr[c]).map((c) => [c, tr[c]]));
    return { ...doc, translations: pick(doc.translations), otherSenses: doc.otherSenses.map((s) => ({ ...s, tr: pick(s.tr) })) };
  }
  async function viewJSON(name, arg, langs, p) {
    let data, file = null;
    if (name === "word") {
      const doc = await resolveWord(arg);
      data = doc ? filterWord(doc, langs) : { error: "not_found", query: arg };
      if (doc) file = `words/${doc.slug}.json`;
    } else if (name === "lang") {
      const code = (parseLangs(arg) || [])[0];
      if (code) {
        const d = await getJSON(`langs/${code}.json`);
        const w = p.get("words");
        if (w) {
          await index();
          const want = new Set(w.split(",").map(slugify));
          data = { ...d, rows: d.rows.filter((r) => want.has(r[0])) };
        } else data = d;
        file = `langs/${code}.json`;
      } else data = { error: "unknown_language", query: arg };
    } else if (name === "search") {
      await index();
      data = { query: arg, results: searchIndex(arg, 50).map((r) => ({ slug: r.slug, word: r.word, pos: r.pos, category: r.cat })) };
    } else if (name === "languages") { data = META.languages; file = "meta.json"; }
    else if (name === "categories") { data = META.categories; file = "meta.json"; }
    else if (name === "category" || name === "letter") {
      await index();
      const rows = name === "category" ? INDEX.filter((r) => r.cat === arg) : alphabetical().filter((r) => r.key.startsWith(norm(arg)));
      data = { [name]: arg, words: rows.map((r) => ({ slug: r.slug, word: r.word, pos: r.pos })) };
    } else { data = META; file = "meta.json"; }
    const text = JSON.stringify(data, null, 2);
    setTitle("JSON");
    main.innerHTML = `<div class="page-head json-view"><h1 class="sr-only">JSON result</h1>
      <p class="muted small">This page shows the result as JSON for reading in a browser. Scripts should request the static files directly${file ? `: <a href="${esc(dataURL(file))}">${esc(dataURL(file))}</a>` : ""}. See the <a href="/api">API guide</a>.</p>
      <p><button class="btn secondary" type="button" id="copy-json">Copy JSON</button></p>
      <pre class="codeblock">${esc(text)}</pre></div>`;
    document.getElementById("copy-json").onclick = () => copy(text, "Copied JSON");
  }

  /* ---------------- search ---------------- */
  function searchIndex(q, limit) {
    const key = norm(q).replace(/_/g, " ");
    if (!key) return [];
    const exact = [], prefix = [], wordPrefix = [], contains = [];
    for (const r of INDEX) {
      if (r.key === key) exact.push(r);
      else if (r.key.startsWith(key)) prefix.push(r);
      else if (r.key.includes(" " + key)) wordPrefix.push(r);
      else if (key.length > 2 && r.key.includes(key)) contains.push(r);
      if (exact.length + prefix.length > limit * 4) break;
    }
    prefix.sort((a, b) => a.rank - b.rank);
    return exact.concat(prefix, wordPrefix, contains).slice(0, limit);
  }

  const qInput = document.getElementById("q");
  const sugg = document.getElementById("suggest");
  let suggItems = [], suggIdx = -1;
  function closeSuggest() { sugg.hidden = true; qInput.setAttribute("aria-expanded", "false"); suggIdx = -1; qInput.removeAttribute("aria-activedescendant"); }
  function renderSuggest() {
    const q = qInput.value.trim();
    if (!q || !INDEX) return closeSuggest();
    suggItems = searchIndex(q, 8);
    if (!suggItems.length) {
      sugg.innerHTML = `<li class="hint" role="presentation">No English entry starts with “${esc(q)}”. Press Enter to search.</li>`;
    } else {
      sugg.innerHTML = suggItems.map((r, i) => `<li role="option" id="sg-${i}" data-slug="${esc(r.slug)}" aria-selected="${i === suggIdx}"><span>${esc(r.word)}</span><span class="pos">${esc(POS_NAMES[r.pos] || r.pos)}</span></li>`).join("");
    }
    sugg.hidden = false;
    qInput.setAttribute("aria-expanded", "true");
  }
  qInput.addEventListener("focus", () => { index().then(renderSuggest).catch(() => {}); });
  qInput.addEventListener("input", () => { suggIdx = -1; if (INDEX) renderSuggest(); else index().then(renderSuggest).catch(() => {}); });
  qInput.addEventListener("keydown", (e) => {
    if (sugg.hidden || !suggItems.length) { if (e.key === "Escape") closeSuggest(); return; }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      suggIdx = (suggIdx + (e.key === "ArrowDown" ? 1 : -1) + suggItems.length) % suggItems.length;
      [...sugg.children].forEach((li, i) => li.setAttribute("aria-selected", String(i === suggIdx)));
      qInput.setAttribute("aria-activedescendant", "sg-" + suggIdx);
    } else if (e.key === "Escape") closeSuggest();
  });
  sugg.addEventListener("mousedown", (e) => {
    const li = e.target.closest("li[data-slug]");
    if (!li) return;
    e.preventDefault();
    qInput.value = "";
    closeSuggest();
    navigate("/word/" + li.dataset.slug);
  });
  qInput.addEventListener("blur", () => setTimeout(closeSuggest, 120));
  document.getElementById("search-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = qInput.value.trim();
    if (!q) return;
    await index();
    const pick = suggIdx >= 0 ? suggItems[suggIdx] : INDEX.find((r) => r.key === norm(q));
    qInput.value = "";
    closeSuggest();
    qInput.blur();
    navigate(pick ? "/word/" + pick.slug : "/search?q=" + encodeURIComponent(q));
  });

  /* ---------------- shared bits ---------------- */
  function letterBar(current) {
    return `<nav class="alpha" aria-label="Browse by letter">${"abcdefghijklmnopqrstuvwxyz".split("").map((l) =>
      `<a href="/letter/${l}"${l === current ? ' aria-current="page"' : ""}>${l.toUpperCase()}</a>`).join("")}</nav>`;
  }
  function langOptions(selected) {
    return `<option value="">None</option>` + META.languages.slice().sort((a, b) => a.name.localeCompare(b.name))
      .map((l) => `<option value="${l.code}"${l.code === selected ? " selected" : ""}>${esc(l.name)}</option>`).join("");
  }
  async function wordList(rows, el, showLang) {
    let tmap = null, L = null;
    if (showLang) {
      L = LANG_BY_CODE.get(showLang);
      const d = await getJSON(`langs/${showLang}.json`);
      tmap = new Map(d.rows.map((r) => [r[0], r]));
    }
    let shown = 0;
    const ul = document.createElement("ul");
    ul.className = "word-cols";
    el.innerHTML = "";
    el.appendChild(ul);
    const more = document.createElement("p");
    more.className = "more";
    function addPage() {
      const html = rows.slice(shown, shown + PAGE * 2).map((r) => {
        const t = tmap && tmap.get(r.slug);
        return `<li><a href="/word/${r.slug}">${esc(r.word)}</a>${t ? `<span class="x" lang="${langAttr(showLang)}" dir="auto">${esc(t[1])}</span>` : ""}</li>`;
      }).join("");
      ul.insertAdjacentHTML("beforeend", html);
      shown += PAGE * 2;
      more.innerHTML = shown < rows.length ? `<button class="btn secondary" type="button">Show more (${fmt(rows.length - shown)} left)</button>` : "";
      const b = more.querySelector("button");
      if (b) b.onclick = addPage;
    }
    el.appendChild(more);
    addPage();
    if (L && L.rtl) ul.querySelectorAll(".x").forEach((x) => x.setAttribute("dir", "rtl"));
  }
  function listWithLanguagePicker(title, intro, rows, crumbs) {
    const sel = store.get("mlg-list-lang", pinned()[0] || "");
    main.innerHTML = `<div class="page-head">${crumbs || ""}<h1 class="headword" style="font-size:clamp(2rem,5vw,3.4rem)">${esc(title)}</h1><p class="lede">${intro}</p></div>
      <div class="list-tools"><label>Show translations in <select id="list-lang">${langOptions(sel)}</select></label></div>
      <div id="list"></div>`;
    const listEl = document.getElementById("list");
    const select = document.getElementById("list-lang");
    const draw = () => wordList(rows, listEl, select.value || null).catch(() => { listEl.innerHTML = `<p class="muted">Couldn't load translations for that language.</p>`; });
    select.onchange = () => { store.set("mlg-list-lang", select.value); draw(); };
    return draw();
  }

  /* ---------------- views ---------------- */
  const VIEWS = {};

  VIEWS.home = async () => {
    setTitle("");
    const m = META;
    const regions = m.regions.map((rg) => {
      const ls = m.languages.filter((l) => l.region === rg.id).sort((a, b) => a.name.localeCompare(b.name));
      return `<div class="region-block"><h3><span class="swatch" style="background:var(--t-${rg.id});box-shadow:inset 0 0 0 1px var(--i-${rg.id})"></span>${esc(rg.name)}</h3>
        <ul>${ls.map((l) => `<li><a href="/lang/${l.code}">${esc(l.name)}</a></li>`).join("")}</ul></div>`;
    }).join("");
    main.innerHTML = `
      <section class="hero">
        <h1>How do you say it in ${m.counts.languages} languages?</h1>
        <p>Look up ${fmt(m.counts.words)} everyday English words and phrases and see them written in every script, with romanizations, from open Wiktionary data.</p>
        <ul class="specimen" id="specimen" aria-label="“Thank you” in several languages"></ul>
        <p class="specimen-caption" id="specimen-caption"></p>
      </section>
      <div class="home-grid">
        <section class="popular"><h2>Popular words</h2><ul class="chips" id="popular"></ul></section>
        <section class="letters"><h2>Browse A to Z</h2>${letterBar()}</section>
        <section><h2>Categories</h2><ul class="cat-list">${m.categories.map((c) => `<li><a href="/category/${c.id}">${esc(c.name)}</a><span class="n">${fmt(c.count)}</span></li>`).join("")}</ul></section>
        <section><h2>Languages</h2><div class="regions">${regions}</div></section>
      </div>`;
    // specimen line: one real entry rendered across scripts
    getJSON("words/thank_you.json").then((d) => {
      const pick = ["ja", "ko", "zh-Hans", "ar", "hi", "ru", "el", "he", "th", "am", "ka", "ta", "fr", "sw", "es", "tr", "hy", "km"];
      const ul = document.getElementById("specimen");
      if (!ul) return;
      ul.innerHTML = pick.filter((c) => d.translations[c]).map((c) => {
        const L = LANG_BY_CODE.get(c);
        return `<li><a href="/word/thank_you?langs=${c}" lang="${langAttr(c)}" dir="auto">${esc(d.translations[c][0].w)}</a><small>${esc(L.name)}</small></li>`;
      }).join("");
      document.getElementById("specimen-caption").innerHTML = `“Thank you” in ${pick.length} of ${m.counts.languages} languages. <a href="/word/thank_you">See them all</a>.`;
    }).catch(() => {});
    index().then(() => {
      const el = document.getElementById("popular");
      if (el) el.innerHTML = POPULAR.filter((s) => BY_SLUG.has(s)).map((s) => `<li><a href="/word/${s}">${esc(BY_SLUG.get(s).word)}</a></li>`).join("");
    }).catch(() => {});
  };

  VIEWS.word = async (arg, langs, params, seq) => {
    main.innerHTML = `<p class="loading">Loading…</p>`;
    const doc = await resolveWord(arg);
    if (seq !== routeSeq) return;
    if (!doc) {
      await index();
      const near = searchIndex(arg, 12);
      setTitle(arg);
      main.innerHTML = `<div class="state"><h1>“${esc(arg)}” isn't in the dictionary yet</h1>
        <p class="muted">The dictionary covers ${fmt(META.counts.words)} common English words and phrases.${near.length ? " These are close:" : " Try a simpler form of the word, such as the singular or the base verb."}</p>
        ${near.length ? `<ul class="chips">${near.map((r) => `<li><a href="/word/${r.slug}">${esc(r.word)}</a></li>`).join("")}</ul>` : ""}</div>`;
      return;
    }
    const canonical = `/word/${doc.slug}`;
    const urlNow = new URL(location.href);
    if (urlNow.searchParams.has("w")) { // normalise ?w= links to the word path, keeping other parameters
      urlNow.searchParams.delete("w");
      const rest = urlNow.searchParams.toString();
      history.replaceState(null, "", canonical + (rest ? "?" + rest : "") + urlNow.hash);
    }
    setTitle(`${doc.word} in different languages`);
    const tr = doc.translations;
    const covered = Object.keys(tr).length;
    const pos = POS_NAMES[doc.pos] || doc.pos;
    const sense = doc.gloss ? `${pos}, as in “<em>${esc(doc.gloss)}</em>”.` : `${pos}.`;
    const also = doc.alsoSpelled && doc.alsoSpelled.length ? ` Also covers ${doc.alsoSpelled.map((w) => `“${esc(w)}”`).join(", ")}.` : "";
    const letter = doc.slug[0];

    main.innerHTML = `
      <div class="page-head">
        <p class="crumbs"><a href="/">Home</a> / <a href="/letter/${letter}">${letter.toUpperCase()}</a></p>
        <h1 class="headword">${esc(doc.word)}</h1>
        <p class="sense-line">${sense}${also}</p>
      </div>
      <div class="toolbar" role="region" aria-label="Translation tools">
        <label class="sr-only" for="lang-filter">Filter languages</label>
        <input type="search" id="lang-filter" placeholder="Filter languages">
        <div class="jump" id="jump"></div>
        <span class="spacer"></span>
        <button class="linkbtn" type="button" id="copy-link">Copy link</button>
        <a href="?format=json${langs ? "&langs=" + langs.join(",") : ""}" id="json-link">JSON</a>
      </div>
      <div id="tr"></div>
      <p class="legend"><span>Machine translation</span> marks entries filled in by AI where Wiktionary has no translation yet. Select a translation to copy it; use ☆ to keep a language at the top of every page.</p>
      <div class="detail">
        <section><h2>Meaning</h2><ol class="defs">${(doc.definitions || []).map((d) => `<li>${esc(d)}</li>`).join("")}</ol>
          <p class="small muted">Definitions and native translations from <a href="${esc(doc.source)}" rel="noopener">Wiktionary</a>. Spotted a mistake? <a class="js-suggest" href="https://github.com/MethodoxTech/Multilingualism/issues/new" rel="noopener">Suggest a correction</a>, or fix it on Wiktionary, which this site rebuilds from.</p>
          ${doc.otherSenses.length ? `<h2 style="margin-top:28px">Other meanings</h2>${doc.otherSenses.map((s, i) => otherSense(s, i)).join("")}` : ""}
        </section>
        <section><h2>Nearby words</h2><ul class="near" id="near"><li class="muted">…</li></ul>
          <h2 style="margin-top:28px">Use this in your own app</h2>
          <p class="small">All translations of “${esc(doc.word)}” as JSON: <a href="${esc(dataURL("words/" + doc.slug + ".json"))}" rel="noopener">${esc("words/" + doc.slug + ".json")}</a>. See the <a href="/api">API guide</a>.</p>
        </section>
      </div>`;

    const trEl = document.getElementById("tr");
    const jumpEl = document.getElementById("jump");
    function draw() {
      const mine = pinned().filter((c) => LANG_BY_CODE.has(c));
      const filter = norm(document.getElementById("lang-filter").value);
      const match = (c) => { const L = LANG_BY_CODE.get(c); return !filter || norm(L.name).includes(filter) || norm(L.native).includes(filter) || c.toLowerCase() === filter; };
      let html = "";
      const jumps = [];
      if (langs) {
        const shown = langs.filter(match);
        html += `<p class="only-note">Showing ${shown.length} of ${META.counts.languages} languages. <a href="${canonical}">Show all languages</a></p>`;
        html += section("chosen", "Chosen languages", shown, tr, "mine");
      } else {
        if (mine.length && !filter) {
          html += section("mine", "Your languages", mine, tr, "mine");
          jumps.push(["mine", "Yours", "mine"]);
        }
        for (const rg of META.regions) {
          const codes = META.languages.filter((l) => l.region === rg.id).map((l) => l.code).filter(match)
            .sort((a, b) => LANG_BY_CODE.get(a).name.localeCompare(LANG_BY_CODE.get(b).name));
          if (!codes.length) continue;
          html += section(rg.id, rg.name, codes, tr, rg.id);
          jumps.push([rg.id, rg.name.split(",")[0].replace("Constructed", "Other"), rg.id]);
        }
        if (!html) html = `<p class="muted" style="padding:24px 0">No language matches “${esc(filter)}”.</p>`;
      }
      trEl.innerHTML = html;
      jumpEl.innerHTML = jumps.map(([id, label, rg]) => `<a href="#r-${id}" style="background:var(--t-${rg})">${esc(label)}</a>`).join("");
    }
    draw();
    document.getElementById("lang-filter").addEventListener("input", draw);
    trEl.addEventListener("click", (e) => {
      const pin = e.target.closest(".pin");
      if (pin) {
        const c = pin.dataset.code;
        const list = pinned();
        const i = list.indexOf(c);
        if (i >= 0) list.splice(i, 1); else list.push(c);
        setPinned(list);
        toast(i >= 0 ? `Removed ${LANG_BY_CODE.get(c).name} from your languages` : `Added ${LANG_BY_CODE.get(c).name} to your languages`);
        draw();
        return;
      }
      const t = e.target.closest("button.tr");
      if (t) copy(t.dataset.copy);
    });
    document.getElementById("copy-link").onclick = () => copy(location.origin + canonical + (langs ? "?langs=" + langs.join(",") : ""), "Link copied");
    index().then(() => {
      const al = alphabetical();
      const i = al.findIndex((r) => r.slug === doc.slug);
      const near = i < 0 ? [] : al.slice(Math.max(0, i - 4), i).concat(al.slice(i + 1, i + 5));
      const el = document.getElementById("near");
      if (el) el.innerHTML = near.map((r) => `<li><a href="/word/${r.slug}">${esc(r.word)}</a></li>`).join("");
    }).catch(() => {});
  };

  function section(id, title, codes, tr, region) {
    const have = codes.filter((c) => tr[c]).length;
    return `<section class="region" id="r-${id}" aria-labelledby="h-${id}">
      <div class="region-title"><h2 id="h-${id}">${esc(title)}</h2><span class="count">${have} of ${codes.length}</span></div>
      <div class="grid">${codes.map((c) => cell(c, tr[c], region === "mine" ? regionOf(c) : region)).join("")}</div></section>`;
  }
  function cell(code, items, region) {
    const L = LANG_BY_CODE.get(code);
    const isPinned = pinned().includes(code);
    const head = `<div class="lang"><a href="/lang/${code}">${esc(L.name)}</a><button class="pin" type="button" data-code="${code}" aria-pressed="${isPinned}" aria-label="${isPinned ? "Remove" : "Add"} ${esc(L.name)} ${isPinned ? "from" : "to"} your languages" title="${isPinned ? "Remove from" : "Add to"} your languages">${isPinned ? "★" : "☆"}</button></div>`;
    if (!items || !items.length) {
      return `<div class="cell missing" style="${tintStyle(region)}">${head}<span class="tr">Not translated yet</span></div>`;
    }
    const [first, ...rest] = items;
    const dir = L.rtl ? "rtl" : "auto";
    const g = first.g ? `<abbr class="g" title="${first.g.split("").map((x) => GENDER[x]).join(", ")}">${first.g.split("").join("/")}</abbr>` : "";
    const rom = [first.k, first.r].filter(Boolean).map(esc).join(", ");
    const alts = rest.length ? `<div class="alts">Also: <span lang="${langAttr(code)}" dir="${dir}">${rest.map((i) => esc(i.w)).join(", ")}</span></div>` : "";
    const mt = first.src === "ai" ? `<div class="mt">Machine translation${first.low ? ", unsure" : ""}</div>` : "";
    return `<div class="cell" style="${tintStyle(region)}">${head}
      <div><button class="tr" type="button" lang="${langAttr(code)}" dir="${dir}" data-copy="${esc(first.w)}" title="Copy">${esc(first.w)}</button>${g}</div>
      ${rom ? `<div class="rom">${rom}</div>` : ""}${alts}${mt}</div>`;
  }
  function otherSense(s, i) {
    const items = Object.entries(s.tr).slice(0, 40);
    return `<details class="sense"><summary>${esc(s.gloss || s.word)}<span class="pos">${esc(POS_NAMES[s.pos] || s.pos)}${s.word !== s.word.toLowerCase() ? ", " + esc(s.word) : ""}</span></summary>
      <ul class="mini">${items.map(([c, its]) => `<li><b>${esc(LANG_BY_CODE.get(c).name)}</b><span lang="${langAttr(c)}" dir="auto">${its.map((x) => esc(x.w)).join(", ")}</span></li>`).join("")}</ul></details>`;
  }

  VIEWS.lang = async (arg, _langs, params, seq) => {
    const code = (parseLangs(arg) || [])[0];
    if (!code) return VIEWS.notfound();
    const L = LANG_BY_CODE.get(code);
    main.innerHTML = `<p class="loading">Loading…</p>`;
    const [d] = await Promise.all([getJSON(`langs/${code}.json`), index()]);
    if (seq !== routeSeq) return;
    setTitle(`English to ${L.name}`);
    const total = d.rows.length;
    const wk = L.wiktionary, ai = L.machine;
    const agree = L.controlAgreement;
    const region = META.regions.find((r) => r.id === L.region);
    let rows = d.rows.map((r) => ({ slug: r[0], t: r[1], r: r[2], ai: r[3], w: BY_SLUG.get(r[0]) }))
      .filter((x) => x.w);
    const hasRom = rows.some((x) => x.r);
    main.innerHTML = `
      <div class="page-head">
        <p class="crumbs"><a href="/languages">Languages</a> / ${esc(region ? region.name : "")}</p>
        <h1 class="headword" lang="${langAttr(code)}" dir="auto" style="font-family:var(--text);font-weight:650">${esc(L.native)}</h1>
        <p class="lede">${esc(L.name)}: ${fmt(total)} English words and phrases translated, ${ai ? `${fmt(wk)} from Wiktionary and ${fmt(ai)} by machine translation${agree ? ` (in a spot check, machine translations matched Wiktionary for ${agree.matched} of ${agree.checked} words)` : ""}` : "all from Wiktionary so far"}.</p>
        <p class="small links"><a href="?format=json">View as JSON</a><a href="${esc(dataURL("langs/" + code + ".json"))}" rel="noopener">Raw data file</a></p>
      </div>
      <div class="list-tools">
        <label class="sr-only" for="lf">Filter words</label>
        <input type="search" id="lf" placeholder="Filter English or ${esc(L.name)}">
        <label>Order <select id="lo"><option value="az">A to Z</option><option value="common">Most common first</option></select></label>
      </div>
      <table class="words"><thead><tr><th scope="col">English</th><th scope="col">${esc(L.name)}</th>${hasRom ? `<th scope="col">Romanization</th>` : ""}</tr></thead><tbody id="lt"></tbody></table>
      <p class="more" id="lm"></p>`;
    const tbody = document.getElementById("lt"), moreEl = document.getElementById("lm");
    const lf = document.getElementById("lf"), lo = document.getElementById("lo");
    const dir = L.rtl ? "rtl" : "auto";
    let view = [], shown = 0;
    function rowsFor() {
      const f = norm(lf.value);
      let v = f ? rows.filter((x) => x.w.key.includes(f) || norm(x.t).includes(f)) : rows.slice();
      if (lo.value === "az") v.sort((a, b) => a.w.key.localeCompare(b.w.key, "en")); else v.sort((a, b) => a.w.rank - b.w.rank);
      return v;
    }
    function more() {
      tbody.insertAdjacentHTML("beforeend", view.slice(shown, shown + PAGE).map((x) =>
        `<tr><td><a href="/word/${x.slug}">${esc(x.w.word)}</a></td><td class="t" lang="${langAttr(code)}" dir="${dir}">${esc(x.t)}${x.ai ? `<span class="mt" title="Machine translation">machine</span>` : ""}</td>${hasRom ? `<td class="r">${esc(x.r)}</td>` : ""}</tr>`).join(""));
      shown += PAGE;
      moreEl.innerHTML = shown < view.length ? `<button class="btn secondary" type="button">Show more (${fmt(view.length - shown)} left)</button>` : (view.length ? "" : `<span class="muted">Nothing matches that filter.</span>`);
      const b = moreEl.querySelector("button");
      if (b) b.onclick = more;
    }
    function redraw() { view = rowsFor(); shown = 0; tbody.innerHTML = ""; more(); }
    lf.addEventListener("input", redraw);
    lo.addEventListener("change", redraw);
    redraw();
  };

  VIEWS.languages = async () => {
    setTitle("Languages");
    const m = META;
    main.innerHTML = `<div class="page-head"><h1 class="headword" style="font-size:clamp(2rem,5vw,3.4rem)">${m.counts.languages} languages</h1>
      <p class="lede">Grouped by region. Counts show how many of the ${fmt(m.counts.words)} headwords have a translation, and how many of those come from Wiktionary rather than machine translation.</p></div>
      ${m.regions.map((rg) => {
        const ls = m.languages.filter((l) => l.region === rg.id).sort((a, b) => a.name.localeCompare(b.name));
        return `<section class="region" id="r-${rg.id}"><div class="region-title"><h2>${esc(rg.name)}</h2><span class="count">${ls.length} languages</span></div>
          <table class="words"><thead><tr><th scope="col">Language</th><th scope="col">Native name</th><th scope="col">Words</th><th scope="col">From Wiktionary</th></tr></thead><tbody>
          ${ls.map((l) => { const t = l.wiktionary + l.machine; return `<tr><td><span class="swatch" style="display:inline-block;vertical-align:-2px;margin-right:8px;background:var(--t-${rg.id});box-shadow:inset 0 0 0 1px var(--i-${rg.id})"></span><a href="/lang/${l.code}">${esc(l.name)}</a></td><td lang="${langAttr(l.code)}" dir="auto">${esc(l.native)}</td><td>${fmt(t)}</td><td>${t ? Math.round((100 * l.wiktionary) / t) : 0}%</td></tr>`; }).join("")}
          </tbody></table></section>`;
      }).join("")}`;
  };

  VIEWS.categories = async () => {
    setTitle("Categories");
    main.innerHTML = `<div class="page-head"><h1 class="headword" style="font-size:clamp(2rem,5vw,3.4rem)">Categories</h1>
      <p class="lede">Every headword sits in one topic, assigned from Princeton WordNet's word groups. Pick one to browse its words with translations in a language of your choice.</p></div>
      <ul class="cat-list">${META.categories.map((c) => `<li><a href="/category/${c.id}">${esc(c.name)}</a><span class="n">${fmt(c.count)}</span></li>`).join("")}</ul>`;
  };

  VIEWS.category = async (id) => {
    const c = META.categories.find((x) => x.id === id);
    if (!c) return VIEWS.notfound();
    await index();
    setTitle(c.name);
    const rows = INDEX.filter((r) => r.cat === id);
    return listWithLanguagePicker(c.name, `${fmt(rows.length)} words, most common first.`, rows, `<p class="crumbs"><a href="/categories">Categories</a></p>`);
  };

  VIEWS.letter = async (l) => {
    const letter = norm(l).slice(0, 1);
    if (!/[a-z]/.test(letter)) return VIEWS.notfound();
    await index();
    setTitle(`Words starting with ${letter.toUpperCase()}`);
    const rows = alphabetical().filter((r) => r.key.startsWith(letter));
    await listWithLanguagePicker(`Words starting with ${letter.toUpperCase()}`, `${fmt(rows.length)} words and phrases, A to Z.`, rows, "");
    main.querySelector(".page-head").insertAdjacentHTML("beforeend", `<div style="margin-top:18px">${letterBar(letter)}</div>`);
  };

  VIEWS.search = async (q) => {
    await index();
    setTitle(`Search: ${q}`);
    const rows = searchIndex(q, 200);
    if (!rows.length) {
      main.innerHTML = `<div class="state"><h1>No results for “${esc(q)}”</h1><p class="muted">Search matches English headwords. Try a shorter or more common form, or browse <a href="/letter/${esc(slugify(q)[0] || "a")}">by letter</a>.</p></div>`;
      return;
    }
    return listWithLanguagePicker(`Results for “${q}”`, `${rows.length === 200 ? "First 200" : fmt(rows.length)} matching English headwords.`, rows, "");
  };

  VIEWS.api = async () => {
    setTitle("API");
    const base = BASES[0] || "";
    const ex = (p) => `<a href="${esc(base + p)}" rel="noopener"><code>${esc(base + p)}</code></a>`;
    main.innerHTML = `<div class="page-head prose"><h1 class="headword" style="font-size:clamp(2rem,5vw,3.4rem)">API</h1>
      <p class="lede">All data is published as static JSON files on a global CDN. There is no key and no rate limit beyond the CDN's own; responses are CORS-enabled so you can call them from a browser.</p></div>
      <div class="prose">
      <h2>Static JSON files</h2>
      <p>Base URL, pinned to data version <code>${esc(CFG.ref ? CFG.ref.slice(0, 7) : "")}</code>:</p>
      <pre class="codeblock">${esc(base)}</pre>
      <table class="ref"><thead><tr><th>File</th><th>Contains</th></tr></thead><tbody>
        <tr><td><code>meta.json</code></td><td>Languages (code, names, region, coverage), categories, counts, sources and licence.</td></tr>
        <tr><td><code>index.json</code></td><td>Every headword as <code>[slug, word, pos, category, languages]</code>, most common first.</td></tr>
        <tr><td><code>words/{slug}.json</code></td><td>One headword: meaning, definitions, translations keyed by language code, and other senses.</td></tr>
        <tr><td><code>langs/{code}.json</code></td><td>One language: <code>[slug, translation, romanization, machine]</code> for every headword.</td></tr>
      </tbody></table>
      <p>Slugs are the English word in lower case with anything other than letters and digits replaced by <code>_</code>, so “Thank you” is <code>thank_you</code>.</p>
      <h3>Examples</h3>
      <p>${ex("words/love.json")}</p>
      <p>${ex("langs/ja.json")}</p>
      <pre class="codeblock">curl -s ${esc(base)}words/thank_you.json | jq '.translations.ja[0]'
{ "w": "ありがとう", "r": "arigatō" }</pre>
      <h3>Translation objects</h3>
      <table class="ref"><tbody>
        <tr><th><code>w</code></th><td>The translation as written.</td></tr>
        <tr><th><code>r</code></th><td>Romanization, for non-Latin scripts.</td></tr>
        <tr><th><code>k</code></th><td>Japanese kana reading.</td></tr>
        <tr><th><code>g</code></th><td>Grammatical gender: <code>m</code>, <code>f</code>, <code>n</code>, <code>c</code>, or a combination.</td></tr>
        <tr><th><code>src</code></th><td><code>"ai"</code> when the entry is a machine translation; absent for Wiktionary.</td></tr>
        <tr><th><code>low</code></th><td><code>1</code> when the machine translation was flagged as uncertain.</td></tr>
      </tbody></table>
      <h2>URL parameters on this site</h2>
      <p>Every page can be opened with query parameters, which is handy for links and quick lookups. Add <code>format=json</code> to see the result as JSON in the browser. Scripts should use the static files above, since this site returns its HTML page to non-browser clients.</p>
      <table class="ref"><thead><tr><th>Parameter</th><th>Example</th><th>Does</th></tr></thead><tbody>
        <tr><td><code>w</code></td><td><a href="/?w=good morning">/?w=good morning</a></td><td>Opens a word or phrase.</td></tr>
        <tr><td><code>langs</code></td><td><a href="/?w=love&amp;langs=fr,ja,zh-Hans">/?w=love&amp;langs=fr,ja,zh-Hans</a></td><td>Shows only these languages, in this order. Accepts codes or English names.</td></tr>
        <tr><td><code>q</code></td><td><a href="/?q=sun">/?q=sun</a></td><td>Searches English headwords.</td></tr>
        <tr><td><code>lang</code></td><td><a href="/?lang=sw">/?lang=sw</a></td><td>Opens a language's full word list.</td></tr>
        <tr><td><code>cat</code></td><td><a href="/?cat=food">/?cat=food</a></td><td>Opens a category.</td></tr>
        <tr><td><code>letter</code></td><td><a href="/?letter=b">/?letter=b</a></td><td>Lists words starting with a letter.</td></tr>
        <tr><td><code>format</code></td><td><a href="/?w=love&amp;langs=fr,de&amp;format=json">/?w=love&amp;langs=fr,de&amp;format=json</a></td><td>Shows the result as JSON instead of a page.</td></tr>
        <tr><td><code>words</code></td><td><a href="/?lang=es&amp;words=cat,dog,bird&amp;format=json">/?lang=es&amp;words=cat,dog,bird&amp;format=json</a></td><td>With <code>lang</code>: only these headwords.</td></tr>
      </tbody></table>
      <p>Pages also have path forms: <code>/word/love</code>, <code>/lang/fr</code>, <code>/category/food</code>, <code>/letter/a</code>, <code>/search?q=sun</code>.</p>
      <h2>Language codes</h2>
      <p>${META.languages.slice().sort((a, b) => a.name.localeCompare(b.name)).map((l) => `<code>${l.code}</code>&nbsp;${esc(l.name)}`).join(", ")}.</p>
      <h2>Licence</h2>
      <p>The data is licensed <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener">CC BY-SA 4.0</a>, because Wiktionary's is. Credit “Multilingualism, from Wiktionary contributors” and share adaptations under the same licence.</p>
      </div>`;
  };

  VIEWS.about = async () => {
    setTitle("About");
    const m = META;
    const ag = m.languages.filter((l) => l.controlAgreement).sort((a, b) => a.name.localeCompare(b.name));
    main.innerHTML = `<div class="page-head prose"><h1 class="headword" style="font-size:clamp(2rem,5vw,3.4rem)">About</h1>
      <p class="lede">A fast, open alternative to word-in-many-languages sites, built from Wiktionary and published as plain files.</p></div>
      <div class="prose">
      <h2>Where the translations come from</h2>
      <p>${fmt(m.counts.wiktionary)} translations come from the English Wiktionary's translation tables, written by volunteer contributors, as extracted by <a href="https://kaikki.org/" rel="noopener">kaikki.org</a> (Wiktextract). For each headword the site shows the most widely translated sense, with other senses listed below it.</p>
      <p>Where Wiktionary has no translation for a language, the gap is filled by machine translation (${fmt(m.counts.machine)} entries) and labelled “Machine translation” on the page and <code>"src": "ai"</code> in the data. Translations the model flagged as uncertain say so. Treat these as a starting point, especially for languages with few online resources.</p>
      <p>Headwords were chosen by everyday frequency (from <a href="https://github.com/rspeer/wordfreq" rel="noopener">wordfreq</a>) among Wiktionary entries that have translation tables, plus common phrases. Categories come from <a href="https://wordnet.princeton.edu/" rel="noopener">Princeton WordNet</a>.</p>
      ${ag.length ? `<h2>How reliable are the machine translations?</h2>
      <p>To check, the machine translator was also given a hidden sample of words that Wiktionary already covers. The table shows how often its single answer matched one of Wiktionary's translations, ignoring punctuation, accents and short inflectional endings. A mismatch is often still a valid synonym or spelling, so these numbers are a floor, not an error rate.</p>
      <table class="ref"><thead><tr><th>Language</th><th>Matched</th></tr></thead><tbody>
      ${ag.map((l) => `<tr><td><a href="/lang/${l.code}">${esc(l.name)}</a></td><td>${l.controlAgreement.matched} of ${l.controlAgreement.checked}</td></tr>`).join("")}</tbody></table>` : ""}
      <h2>Corrections</h2>
      <p>To report a wrong or awkward translation, especially a machine translation, use <a class="js-suggest" href="https://github.com/MethodoxTech/Multilingualism/issues/new" rel="noopener">Suggest a correction</a> at the bottom of any page. It opens an issue on GitHub, prefilled with the word or language you were viewing.</p>
      <p>You can also fix or add translations on Wiktionary: every word page links to its Wiktionary entry. The site is rebuilt from new Wiktionary data, and a Wiktionary translation replaces any machine translation for the same word and language.</p>
      <h2>Sources and licence</h2>
      <ul>${m.sources.map((s) => `<li>${s.url ? `<a href="${esc(s.url)}" rel="noopener">${esc(s.name)}</a>` : esc(s.name)}${s.license ? ` (${esc(s.license)})` : ""}</li>`).join("")}</ul>
      <p>Data version ${esc(m.version)}. Source code and data: <a href="https://github.com/MethodoxTech/Multilingualism" rel="noopener">GitHub</a>.</p>
      </div>`;
  };

  VIEWS.notfound = async () => {
    setTitle("Not found");
    main.innerHTML = `<div class="state"><h1>There's no page here</h1><p class="muted">Search for a word above, or start from the <a href="/">home page</a>.</p></div>`;
  };

  /* ---------------- theme ---------------- */
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("mlg-theme", next); } catch (e) { /* ignore */ }
  });

  route();
})();
