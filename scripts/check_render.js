/* Headless render check for index.html. Run from the repository root:
       node scripts/check_render.js [path/to/old/index.html path/to/old/data.json]
   Needs Node and Playwright with Chromium (npm install playwright && npx playwright install chromium).
   It serves the repository over a local HTTP port, loads the page in headless Chromium and checks that
   - the page loads with no console errors or uncaught exceptions;
   - every subject x grade x view combination of the statewide figure renders bars without errors;
   - in the cohort view, for every cohort, subject, level mode and a comparison group, the stacked
     bars in each drawn column add to 100% of the axis height;
   - in the one-school figure, for at least 30 school x student-group combinations (alone and two
     groups side by side), every reported year draws one column adding to 100%, every suppressed or
     unpublished group-year draws an explicit "Not reported" gap and no column, and no text is colored;
   - the "grouped by a characteristic" figure renders the within-school gap characteristic for
     thirds, quarters and fifths with every column adding to 100%;
   - optionally, the default view of an earlier copy of the page (old index.html + old data.json)
     produces the same chart markup as the current page, so the default view is unchanged.
   Exits with status 1 if any check fails. */
"use strict";
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = process.cwd();
const TYPES = { ".html": "text/html; charset=utf-8", ".json": "application/json", ".csv": "text/csv" };
let failures = 0;
const check = (ok, msg) => { console.log((ok ? "ok   " : "FAIL ") + msg); if (!ok) failures++; };

function serve(dir, overrides) {
  return new Promise(resolve => {
    const srv = http.createServer((req, res) => {
      const url = decodeURIComponent(req.url.split("?")[0]);
      const rel = url === "/" ? "index.html" : url.slice(1);
      const file = overrides && overrides[rel] ? overrides[rel] : path.join(dir, rel);
      fs.readFile(file, (err, buf) => {
        if (err) { res.writeHead(404); res.end("not found"); return; }
        res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream" });
        res.end(buf);
      });
    });
    srv.listen(0, "127.0.0.1", () => resolve({ srv, port: srv.address().port }));
  });
}

async function open(browser, port, errors) {
  const page = await browser.newPage();
  page.on("console", m => { if (m.type() === "error") errors.push("console: " + m.text()); });
  page.on("pageerror", e => errors.push("pageerror: " + e.message));
  await page.goto(`http://127.0.0.1:${port}/index.html`);
  await page.waitForSelector("#figA:not([hidden])", { timeout: 30000 });
  return page;
}

// Heights of the filled level bars in each column of every <svg> in a container (#aOut by default), as a share of the axis height.
const columnSums = (sel) => {
  const out = [];
  document.querySelectorAll((sel || "#aOut") + " svg").forEach(svg => {
    const axis = [...svg.querySelectorAll(":scope > line")].find(l => l.getAttribute("x1") === l.getAttribute("x2")); // the y axis, not the hatch pattern's line
    const span = +axis.getAttribute("y1") - +axis.getAttribute("y2");
    const cols = {};
    svg.querySelectorAll("rect").forEach(r => {
      const fill = r.getAttribute("fill") || "";
      if (!fill.startsWith("var(")) return; // skip hatch overlays
      const x = r.getAttribute("x");
      cols[x] = (cols[x] || 0) + +r.getAttribute("height");
    });
    out.push(Object.values(cols).map(h => h / span * 100));
  });
  return out;
};

(async () => {
  const data = JSON.parse(fs.readFileSync(path.join(ROOT, "data.json"), "utf-8"));
  const { srv, port } = await serve(ROOT);
  const browser = await chromium.launch();
  const errors = [];
  const page = await open(browser, port, errors);

  // Default state.
  const defaults = await page.evaluate(() => [aView.value, aSubj.value, aGrade.value, aG1.value, aG2.value, aMode.value, aGradeL.hidden, aCohortL.hidden, aNote.textContent]);
  check(defaults.join("|") === "year|math|11|1||4|false|true|", "default statewide view is one chart per year, math, grade 11, all students: " + JSON.stringify(defaults));
  const defaultHTML = await page.evaluate(() => ({ a: aOut.innerHTML, c: cOut.innerHTML, d: dOut.innerHTML, e: eOut.innerHTML }));
  check(/<svg/.test(defaultHTML.a) && /<svg/.test(defaultHTML.c) && /<svg/.test(defaultHTML.d) && /<svg/.test(defaultHTML.e), "all four figures drew an svg on load");

  // Every subject x grade x view, alone and with a comparison group.
  const subjects = ["math", "ela"], grades = ["3", "4", "5", "6", "7", "8", "11"], views = ["year", "time"];
  let combos = 0, bad = [];
  for (const sub of subjects) for (const gr of grades) for (const v of views) for (const cmp of ["", "31"]) {
    const n = await page.evaluate(([sub, gr, v, cmp]) => {
      aView.value = v; aView.onchange();
      aSubj.value = sub; aSubj.onchange();
      aGrade.value = gr; aGrade.onchange();
      aG2.value = cmp; aG2.onchange();
      return [aOut.querySelectorAll("svg").length, aOut.querySelectorAll("rect").length, aGradeL.hidden, aCohortL.hidden];
    }, [sub, gr, v, cmp]);
    combos++;
    const expectSvg = v === "year" ? 11 : (cmp ? 2 : 1);
    if (n[0] !== expectSvg || n[1] < 20 || n[2] || !n[3]) bad.push(`${sub} grade ${gr} ${v} cmp=${cmp}: ${JSON.stringify(n)}`);
  }
  check(bad.length === 0, `${combos} subject x grade x view combinations rendered (${bad.length} wrong)` + (bad.length ? "\n  " + bad.join("\n  ") : ""));

  // Cohort view: every cohort, both subjects, both level modes, with and without a comparison group.
  const cohorts = await page.evaluate(() => [...aCohort.options].map(o => [o.value, o.text]));
  check(cohorts.length >= 10 && cohorts.some(c => c[0] === "2015"), `${cohorts.length} cohorts listed, including grade 3 in 2015`);
  let cols = 0, badCols = 0, cohortRuns = 0, notes = [];
  for (const sub of subjects) for (const [y3] of cohorts) for (const mode of ["4", "2"]) for (const cmp of ["", "78"]) {
    const r = await page.evaluate(([sub, y3, mode, cmp, f]) => {
      aView.value = "cohort"; aView.onchange();
      aSubj.value = sub; aSubj.onchange();
      aCohort.value = y3; aMode.value = mode; aG2.value = cmp; aG2.onchange();
      const sums = eval("(" + f + ")")();
      return { sums, hidden: [aGradeL.hidden, aCohortL.hidden], note: aNote.textContent, svgs: aOut.querySelectorAll("svg").length };
    }, [sub, y3, mode, cmp, columnSums.toString()]);
    cohortRuns++;
    if (r.svgs !== (cmp ? 2 : 1) || !r.hidden[0] || r.hidden[1]) badCols++;
    for (const svg of r.sums) for (const s of svg) { cols++; if (Math.abs(s - 100) > 0.01) badCols++; }
    if (sub === "math" && mode === "4" && !cmp) notes.push(`  ${y3}: ${r.sums[0].length} columns; ${r.note}`);
  }
  check(badCols === 0, `cohort view: ${cohortRuns} runs, ${cols} drawn columns, every column's bars add to 100% of the axis (${badCols} wrong)`);
  console.log(notes.join("\n"));

  // Underlying data: the cohort for grade 3 in 2015, all students, math, as read from data.json.
  const expectPts = [3, 4, 5, 6, 7, 8, 11].filter(g => data.years.includes(2015 + g - 3)).length;
  const drawn = await page.evaluate(([f]) => { aSubj.value = "math"; aSubj.onchange(); aCohort.value = "2015"; aG2.value = ""; aMode.value = "4"; aG2.onchange(); return eval("(" + f + ")")()[0].length; }, [columnSums.toString()]);
  check(drawn === expectPts, `grade 3 in 2015 cohort draws ${drawn} columns (expected ${expectPts}: grades 3 to 7 and 11; 2020 untested)`);

  // Back to defaults: the chart is the same markup as on first load.
  const again = await page.evaluate(() => { aView.value = "year"; aView.onchange(); aSubj.value = "math"; aSubj.onchange(); aGrade.value = "11"; aGrade.onchange(); aG2.value = ""; aG2.onchange(); return aOut.innerHTML; });
  check(again.replace(/h\d+/g, "h") === defaultHTML.a.replace(/h\d+/g, "h"), "returning to the default selections reproduces the initial chart markup");

  // Figure 4 (one school): the expected picture of every school x group, computed here from data.json.
  const SG = data.school_groups, YRS = data.years, ALLY = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];
  const keyOf = s => s[0] + " — " + s[1];
  const picture = (i, g) => { // reported years and "not reported" years (from the school's first year in the file) of group g at school i
    const s = data.schools[i], rows = Object.assign({}, s[12], SG.extra[i] || {}), sup = SG.suppressed[i] || {};
    const yrs = r => new Set((r || []).map(a => YRS[a[0]]));
    const rep = yrs(rows[g]), any = new Set([...Object.values(rows).flatMap(r => [...yrs(r)]), ...Object.values(sup).flatMap(r => [...yrs(r)])]), first = Math.min(...any);
    const nr = ALLY.filter(y => !rep.has(y) && y !== 2020 && y >= first);
    return { rep: [...rep], nr, groups: Object.keys(rows) };
  };
  // Sample: every 90th school plus the default, with up to six of its groups (always the two economic-status groups when it has them).
  const sample = [];
  const idxs = data.schools.map((s, i) => i).filter(i => i % 90 === 0 || data.schools[i][0] === "Berkeley High");
  for (const i of idxs) {
    const gs = picture(i, "1").groups, pick = ["1", "31", "111", "78", "160", "7", "121", "128", "80", "76"].filter(g => gs.includes(g)).slice(0, 6);
    for (const g of pick) sample.push([i, g, ""]);
    if (gs.includes("31") && gs.includes("111")) sample.push([i, "31", "111"]);
    if (gs.includes("1") && pick[1]) sample.push([i, "1", pick[1]]);
  }
  let runs = 0, wrong = [], nrSeen = 0, pairRuns = 0, dCols = 0;
  for (const [i, g1, g2] of sample) for (const mode of (g2 ? ["4", "2"] : ["4"])) {
    const key = keyOf(data.schools[i]), p1 = picture(i, g1), p2 = g2 ? picture(i, g2) : null;
    const r = await page.evaluate(([key, g1, g2, mode, f]) => {
      eSchool.value = key; drawE(); eG1.value = g1; eG2.value = g2; eMode.value = mode; drawE();
      const texts = [...eOut.querySelectorAll("text")];
      const fills = texts.map(t => (t.getAttribute("style") || "").match(/fill:([^;]+)/)).filter(m => m).map(m => m[1].trim());
      const rects = [...eOut.querySelectorAll("rect")].filter(r => (r.getAttribute("fill") || "").startsWith("var("));
      return { svgs: eOut.querySelectorAll("svg").length, sums: eval("(" + f + ")")("#eOut"), nr: texts.filter(t => t.textContent === "Not reported").length,
        noTest: texts.filter(t => t.textContent === "No test").length, zero: Object.values(rects.reduce((o, r) => { const x = r.getAttribute("x"); o[x] = (o[x] || 0) + +r.getAttribute("height"); return o; }, {})).filter(h => h === 0).length,
        cols: new Set(rects.map(r => r.getAttribute("x"))).size, fills: [...new Set(fills)], title: eTitle.textContent, note: eNote.textContent,
        g1: eG1.value, g2: eG2.value, opts: [...eG1.options].map(o => o.value) };
    }, [key, g1, g2, mode, columnSums.toString()]);
    runs++; if (g2) pairRuns++;
    const expCols = p1.rep.length + (p2 ? p2.rep.length : 0), expNR = p1.nr.length + (p2 ? p2.nr.length : 0);
    nrSeen += expNR;
    const problems = [];
    if (r.svgs !== 1) problems.push(`${r.svgs} svgs`);
    if (r.g1 !== g1 || r.g2 !== g2) problems.push(`selection ${r.g1}/${r.g2}`);
    if (r.cols !== expCols) problems.push(`${r.cols} columns, expected ${expCols}`);
    if (r.nr !== expNR) problems.push(`${r.nr} "Not reported" labels, expected ${expNR}`);
    if (r.noTest !== 1) problems.push(`${r.noTest} "No test" labels`);
    if (r.zero) problems.push(`${r.zero} columns of zero height (a suppressed year drawn as a zero)`);
    for (const svg of r.sums) { for (const x of svg) { dCols++; if (Math.abs(x - 100) > 0.01) problems.push(`column sums to ${x}`); } }
    if (r.fills.some(f => !["#fff", "#000"].includes(f))) problems.push(`colored text: ${r.fills}`);
    if (!r.title.startsWith(data.schools[i][0])) problems.push(`title ${r.title}`);
    if (g2 && !r.note.startsWith("Left bar")) problems.push(`note: ${r.note}`);
    if (expNR && !/Not reported/.test(r.note)) problems.push("note does not explain Not reported");
    if (!expNR && !g2 && r.note) problems.push(`unexpected note: ${r.note}`);
    if (r.opts.join() !== [...r.opts].filter(o => p1.groups.includes(o)).join() || r.opts.length !== p1.groups.length) problems.push(`group menu ${r.opts.length} vs ${p1.groups.length}`);
    if (problems.length) wrong.push(`${key} ${g1}/${g2 || "-"} mode ${mode}: ${problems.join("; ")}`);
  }
  check(runs >= 30 && wrong.length === 0, `one school: ${runs} school x group runs (${pairRuns} with two groups side by side, ${dCols} drawn columns, ${nrSeen} "Not reported" gaps) match data.json (${wrong.length} wrong)` + (wrong.length ? "\n  " + wrong.slice(0, 20).join("\n  ") : ""));
  const allGroups = await page.evaluate(() => { const s = new Set(); D.schools.forEach(x => Object.keys(x[12]).forEach(g => s.add(g))); return [...s].sort(); });
  check(allGroups.length === 28 && allGroups.join() === Object.keys(SG.names).sort().join(), `the school figures offer all ${allGroups.length} student groups of the school file`);
  const eAgain = await page.evaluate(() => { eSchool.value = Object.keys(BYK).find(k => k.startsWith("Berkeley High — Berkeley")); drawE(); eG1.value = "1"; eG2.value = ""; eMode.value = "4"; drawE(); return [eOut.innerHTML, eNote.textContent]; });
  check(eAgain[0].replace(/h\d+/g, "h") === defaultHTML.e.replace(/h\d+/g, "h") && eAgain[1] === "", "one school: returning to the default selections reproduces the initial chart markup, with no note");

  // Figure 3: the within-school gap characteristic.
  let gapRuns = 0, gapBad = [], gapCols = 0;
  for (const q of ["3", "4", "5"]) for (const g of ["1", "31"]) for (const mode of ["4", "2"]) {
    const r = await page.evaluate(([q, g, mode, f]) => {
      dBy.value = "gap"; setupPick(); dSplit.value = q; dG.value = g; dMode.value = mode; drawD();
      const fills = [...dOut.querySelectorAll("text")].map(t => (t.getAttribute("style") || "").match(/fill:([^;]+)/)).filter(m => m).map(m => m[1].trim());
      return { panels: dOut.querySelectorAll("svg").length, sums: eval("(" + f + ")")("#dOut"), note: dNote.textContent, titles: [...dOut.querySelectorAll(".pt")].map(t => t.textContent), fills: [...new Set(fills)], hidden: dSplitL.hidden };
    }, [q, g, mode, columnSums.toString()]);
    gapRuns++;
    const problems = [];
    if (r.panels !== +q || r.hidden) problems.push(`${r.panels} panels`);
    if (!/pooled over the years/.test(r.note) || /poverty/i.test(r.note)) problems.push(`note: ${r.note}`);
    if (!r.titles.every(t => / pts/.test(t) && /\d schools/.test(t))) problems.push(`titles: ${r.titles.join(" | ")}`);
    for (const svg of r.sums) for (const x of svg) { gapCols++; if (Math.abs(x - 100) > 0.01) problems.push(`column sums to ${x}`); }
    if (r.fills.some(f => !["#fff", "#000"].includes(f))) problems.push(`colored text: ${r.fills}`);
    if (problems.length) gapBad.push(`split ${q} group ${g} mode ${mode}: ${problems.join("; ")}`);
  }
  check(gapBad.length === 0, `grouped schools: within-school gap characteristic, ${gapRuns} runs, ${gapCols} drawn columns add to 100% (${gapBad.length} wrong)` + (gapBad.length ? "\n  " + gapBad.join("\n  ") : ""));
  const gapCount = await page.evaluate(() => D.schools.filter(s => s[14] != null).length);
  const expGap = data.schools.filter(s => s[12]["31"] && s[12]["111"] && s[12]["31"].some(a => s[12]["111"].some(b => b[0] === a[0]))).length;
  check(gapCount === expGap && gapCount > 1000, `${gapCount} schools have a within-school gap (report both economic-status groups in some year; expected ${expGap})`);
  const dAgain = await page.evaluate(() => { dBy.value = "upp"; setupPick(); dSplit.value = "3"; dG.value = "1"; dMode.value = "4"; dCh.value = "all"; drawD(); return dOut.innerHTML; });
  check(dAgain.replace(/h\d+/g, "h") === defaultHTML.d.replace(/h\d+/g, "h"), "grouped schools: returning to the default selections reproduces the initial chart markup");
  const newWords = await page.evaluate(() => [eNote.textContent, dNote.textContent, [...dBy.options].map(o => o.text).join(" "), [...eG1.options].map(o => o.text).join(" ")].join(" "));
  check(!/poverty/i.test(newWords.replace(/Census tract poverty rate/g, "")), "no new text says \"poverty\" (the pre-existing census-tract characteristic keeps its name)");

  check(errors.length === 0, `no console errors or page errors (${errors.length})` + (errors.length ? "\n  " + errors.join("\n  ") : ""));
  await page.close();

  // Optional: compare the default view with an earlier copy of the page.
  if (process.argv[2] && process.argv[3]) {
    const oldErrors = [];
    const { srv: srv2, port: port2 } = await serve(ROOT, { "index.html": path.resolve(process.argv[2]), "data.json": path.resolve(process.argv[3]) });
    const p2 = await open(browser, port2, oldErrors);
    const oldHTML = await p2.evaluate(() => ({ a: aOut.innerHTML, c: cOut.innerHTML, d: dOut.innerHTML, e: eOut.innerHTML }));
    for (const k of ["a", "c", "d", "e"]) check(oldHTML[k].replace(/h\d+/g, "h") === defaultHTML[k].replace(/h\d+/g, "h"), `figure ${k.toUpperCase()}: default markup identical to the earlier page (${defaultHTML[k].length} chars)`);
    check(oldErrors.length === 0, "earlier page loaded without errors");
    await p2.close(); srv2.close();
  }

  await browser.close(); srv.close();
  console.log(failures ? `\n${failures} check(s) failed` : "\nall render checks passed");
  process.exit(failures ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
