/* Headless render check for index.html. Run from the repository root:
       node scripts/check_render.js [path/to/old/index.html path/to/old/data.json]
   Needs Node and Playwright with Chromium (npm install playwright && npx playwright install chromium).
   It serves the repository over a local HTTP port, loads the page in headless Chromium and checks that
   - the page loads with no console errors or uncaught exceptions;
   - every subject x grade x view combination of the statewide figure renders bars without errors;
   - in the cohort view, for every cohort, subject, level mode and a comparison group, the stacked
     bars in each drawn column add to 100% of the axis height;
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

// Heights of the filled level bars in each column of every <svg> in #aOut, as a share of the axis height.
const columnSums = () => {
  const out = [];
  document.querySelectorAll("#aOut svg").forEach(svg => {
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
  const data = JSON.parse(fs.readFileSync(path.join(ROOT, "data.json"), "utf-8"));
  const expectPts = [3, 4, 5, 6, 7, 8, 11].filter(g => data.years.includes(2015 + g - 3)).length;
  const drawn = await page.evaluate(([f]) => { aSubj.value = "math"; aSubj.onchange(); aCohort.value = "2015"; aG2.value = ""; aMode.value = "4"; aG2.onchange(); return eval("(" + f + ")")()[0].length; }, [columnSums.toString()]);
  check(drawn === expectPts, `grade 3 in 2015 cohort draws ${drawn} columns (expected ${expectPts}: grades 3 to 7 and 11; 2020 untested)`);

  // Back to defaults: the chart is the same markup as on first load.
  const again = await page.evaluate(() => { aView.value = "year"; aView.onchange(); aSubj.value = "math"; aSubj.onchange(); aGrade.value = "11"; aGrade.onchange(); aG2.value = ""; aG2.onchange(); return aOut.innerHTML; });
  check(again.replace(/h\d+/g, "h") === defaultHTML.a.replace(/h\d+/g, "h"), "returning to the default selections reproduces the initial chart markup");

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
