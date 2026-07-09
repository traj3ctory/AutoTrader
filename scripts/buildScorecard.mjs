import fs from "node:fs";

const scorecardPath = new URL("../SCORECARD.json", import.meta.url);
const ledgerPath = new URL("../SETUP_LEDGER.json", import.meta.url);
const outputPath = new URL("../SCORECARD_DASHBOARD.html", import.meta.url);

const sc = JSON.parse(fs.readFileSync(scorecardPath, "utf8"));
const ledger = JSON.parse(fs.readFileSync(ledgerPath, "utf8"));

const GOAL = 30;
const s = sc.summary;
const reviewed = s.reviewed_setups || 0;
// Gate counts records that were a correct thesis OR a user-confirmed taken
// trade (one record can only count once).
const qualifying = sc.records.filter(
  (r) => /correct/i.test(String(r.outcome)) || r.trade_taken === true
).length;
const pct = Math.min(100, Math.round((qualifying / GOAL) * 100));
const accuracy = reviewed > 0 ? Math.round((s.correct_thesis / reviewed) * 100) : 0;

const tagCounts = {};
for (const j of ledger.journal || []) {
  if (j.mistake_tag) tagCounts[j.mistake_tag] = (tagCounts[j.mistake_tag] || 0) + 1;
}

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

const OUTCOME_COLOR = {
  correct: "#22d67a",
  invalidated: "#f5a524",
  other: "#5b8def",
};
const outcomeKind = (o) =>
  /correct/i.test(o) ? "correct" : /invalid/i.test(o) ? "invalidated" : "other";

// Group records by coin: coins with the most repeated analyses surface first,
// then by most recent activity, so the accordion opens onto the busiest story.
const groupsMap = new Map();
for (const r of sc.records) {
  if (!groupsMap.has(r.coin)) groupsMap.set(r.coin, []);
  groupsMap.get(r.coin).push(r);
}
const groups = [...groupsMap.entries()]
  .map(([coin, records]) => ({
    coin,
    records: records.sort((a, b) => String(b.date).localeCompare(String(a.date))),
  }))
  .sort((a, b) => {
    if (b.records.length !== a.records.length) return b.records.length - a.records.length;
    return String(b.records[0].date).localeCompare(String(a.records[0].date));
  });

const groupHtml = groups
  .map((g, i) => {
    const latest = g.records[0];
    const kind = outcomeKind(latest.outcome);
    const searchBlob = esc(
      [
        g.coin,
        ...g.records.flatMap((r) => [r.setup_type, r.outcome, r.trade_result, r.direction]),
      ]
        .join(" ")
        .toLowerCase()
    );
    const rows = g.records
      .map((r) => {
        const k = outcomeKind(r.outcome);
        return `<tr>
        <td class="date">${esc(r.date)}</td>
        <td>${esc(r.trade_type)} ${esc(r.direction)}</td>
        <td>${esc(r.setup_type)}</td>
        <td><span class="pill k-${k}">${esc(r.outcome)}</span></td>
        <td>${esc(r.trade_result)}</td>
        <td class="note">${esc(r.review_note)}</td>
      </tr>`;
      })
      .join("\n");
    return `<div class="group" data-search="${searchBlob}" data-idx="${i}">
    <button class="group-header" type="button" onclick="toggleGroup(${i})">
      <span class="chev" id="chev-${i}">&rsaquo;</span>
      <span class="g-coin">${esc(g.coin)}</span>
      <span class="g-count">${g.records.length} ${g.records.length === 1 ? "analysis" : "analyses"}</span>
      <span class="pill k-${kind}">${esc(latest.outcome)}</span>
      <span class="g-date">${esc(latest.date)}</span>
    </button>
    <div class="group-body" id="body-${i}" hidden>
      <table>
        <thead><tr><th>Date</th><th>Trade</th><th>Setup type</th><th>Outcome</th><th>Trade result</th><th>Review note</th></tr></thead>
        <tbody>
${rows}
        </tbody>
      </table>
    </div>
  </div>`;
  })
  .join("\n");

const tags = Object.entries(tagCounts)
  .sort((a, b) => b[1] - a[1])
  .map(
    ([tag, count]) =>
      `<div class="tag"><span class="tagname">${esc(tag)}</span><span class="tagcount">${count}</span></div>`
  )
  .join("\n");

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AutoTrader Scorecard</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 28px; background: #0a0e17; color: #e6e9f2;
    font: 14px/1.5 -apple-system, "Segoe UI", sans-serif;
  }
  h1 { font-size: 21px; font-weight: 700; margin: 0 0 4px; letter-spacing: -0.01em; }
  .sub { color: #7c8698; margin-bottom: 22px; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .tile { background: #10141f; border: 1px solid #1c2333; border-radius: 10px; padding: 14px 16px; }
  .tile .num { font-size: 26px; font-weight: 700; }
  .tile .lbl { color: #7c8698; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }
  .bar { background: #10141f; border: 1px solid #1c2333; border-radius: 10px; padding: 14px 16px; margin-bottom: 22px; }
  .track { background: #1c2333; border-radius: 5px; height: 10px; overflow: hidden; margin-top: 10px; }
  .fill { background: #3b82f6; height: 100%; }
  h2 { font-size: 15px; font-weight: 700; margin: 26px 0 10px; }
  .toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .search-wrap { position: relative; flex: 1; max-width: 360px; }
  .search-wrap input {
    width: 100%; background: #10141f; border: 1px solid #1c2333; border-radius: 8px;
    color: #e6e9f2; padding: 9px 12px 9px 32px; font-size: 13px; outline: none;
  }
  .search-wrap input:focus { border-color: #3b82f6; }
  .search-wrap::before {
    content: ""; position: absolute; left: 11px; top: 50%; transform: translateY(-50%);
    width: 13px; height: 13px; border: 1.5px solid #7c8698; border-radius: 50%;
  }
  .search-wrap::after {
    content: ""; position: absolute; left: 20px; top: 63%; width: 6px; height: 1.5px;
    background: #7c8698; transform: rotate(45deg);
  }
  #resultCount { color: #7c8698; font-size: 12px; white-space: nowrap; }
  .group { background: #10141f; border: 1px solid #1c2333; border-radius: 10px; margin-bottom: 8px; overflow: hidden; }
  .group-header {
    width: 100%; display: flex; align-items: center; gap: 12px; padding: 12px 14px;
    background: transparent; border: none; color: #e6e9f2; cursor: pointer; text-align: left;
    font: inherit;
  }
  .group-header:hover { background: #141a29; }
  .chev { color: #5b8def; font-size: 18px; font-weight: 700; width: 12px; display: inline-block; transition: transform 0.15s; }
  .chev.open { transform: rotate(90deg); }
  .g-coin { font-weight: 700; min-width: 130px; }
  .g-count { color: #7c8698; font-size: 12px; min-width: 90px; }
  .g-date { color: #7c8698; font-size: 12px; margin-left: auto; }
  .group-body { border-top: 1px solid #1c2333; padding: 4px 14px 10px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #1c2333; vertical-align: top; }
  th { color: #7c8698; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  td.date { white-space: nowrap; color: #a7b0c0; }
  .pill { border-radius: 6px; padding: 3px 9px; font-size: 12px; font-weight: 600; white-space: nowrap; }
  .k-correct { background: #22d67a1f; color: #22d67a; border: 1px solid #22d67a4d; }
  .k-invalidated { background: #f5a5241f; color: #f5a524; border: 1px solid #f5a5244d; }
  .k-other { background: #5b8def1f; color: #5b8def; border: 1px solid #5b8def4d; }
  .note { color: #a7b0c0; font-size: 13px; max-width: 380px; }
  .pagination { display: flex; align-items: center; gap: 10px; margin-top: 14px; }
  .pagination button {
    background: #10141f; border: 1px solid #1c2333; color: #e6e9f2; border-radius: 8px;
    padding: 7px 14px; font-size: 13px; cursor: pointer;
  }
  .pagination button:hover:not(:disabled) { border-color: #3b82f6; color: #5b8def; }
  .pagination button:disabled { opacity: 0.35; cursor: default; }
  #pageInfo { color: #7c8698; font-size: 12px; }
  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
  .tag { background: #10141f; border: 1px solid #1c2333; border-radius: 8px; padding: 6px 10px; display: flex; gap: 8px; align-items: center; }
  .tagname { font-family: ui-monospace, monospace; font-size: 12px; }
  .tagcount { background: #3b82f633; color: #5b8def; border-radius: 99px; padding: 0 8px; font-size: 12px; font-weight: 700; }
  .foot { color: #4b5566; font-size: 12px; margin-top: 22px; }
  .empty { color: #7c8698; font-size: 13px; padding: 20px; text-align: center; background: #10141f; border: 1px solid #1c2333; border-radius: 10px; }
  .green { color: #22d67a; } .amber { color: #f5a524; } .blue { color: #5b8def; }
</style>
</head>
<body>
<h1>AutoTrader Scorecard</h1>
<div class="sub">${esc(sc.principle)}</div>

<div class="tiles">
  <div class="tile"><div class="num">${reviewed}</div><div class="lbl">Reviewed setups</div></div>
  <div class="tile"><div class="num green">${s.correct_thesis}</div><div class="lbl">Correct thesis</div></div>
  <div class="tile"><div class="num amber">${s.invalidated_thesis}</div><div class="lbl">Invalidated thesis</div></div>
  <div class="tile"><div class="num blue">${accuracy}%</div><div class="lbl">Thesis accuracy</div></div>
  <div class="tile"><div class="num">${s.trades_taken}</div><div class="lbl">Trades taken</div></div>
  <div class="tile"><div class="num">${s.trade_wins} / ${s.trade_losses}</div><div class="lbl">Trade wins / losses</div></div>
</div>

<div class="bar">
  <strong>${qualifying} / ${GOAL}</strong> toward the automation gate — correct analyses + taken trades (${pct}%) · ${reviewed} reviewed in total
  <div class="track"><div class="fill" style="width:${pct}%"></div></div>
</div>

<h2>Records by coin</h2>
<div class="toolbar">
  <div class="search-wrap">
    <input id="search" type="text" placeholder="Search coin, setup type, outcome..." oninput="applyFilter()">
  </div>
  <span id="resultCount"></span>
</div>
<div id="groups">
${groupHtml || '<div class="empty">No records yet.</div>'}
</div>
<div class="pagination" id="pagination">
  <button id="prevBtn" onclick="changePage(-1)">Prev</button>
  <span id="pageInfo"></span>
  <button id="nextBtn" onclick="changePage(1)">Next</button>
</div>

<h2>Mistake tags (from ledger journal)</h2>
<div class="tags">
${tags}
</div>

<div class="foot">Generated ${new Date().toISOString()} from SCORECARD.json and SETUP_LEDGER.json · regenerate with: node scripts/buildScorecard.mjs</div>

<script>
  const PAGE_SIZE = 5;
  let page = 1;
  const allGroups = Array.from(document.querySelectorAll('.group'));

  function toggleGroup(i) {
    const body = document.getElementById('body-' + i);
    const chev = document.getElementById('chev-' + i);
    const isHidden = body.hasAttribute('hidden');
    if (isHidden) { body.removeAttribute('hidden'); chev.classList.add('open'); }
    else { body.setAttribute('hidden', ''); chev.classList.remove('open'); }
  }

  function applyFilter() {
    page = 1;
    render();
  }

  function changePage(delta) {
    page += delta;
    render();
  }

  function render() {
    const term = document.getElementById('search').value.trim().toLowerCase();
    const matches = allGroups.filter((g) => !term || g.dataset.search.includes(term));
    const totalPages = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
    page = Math.min(Math.max(1, page), totalPages);
    const start = (page - 1) * PAGE_SIZE;
    const visible = new Set(matches.slice(start, start + PAGE_SIZE));

    allGroups.forEach((g) => { g.style.display = visible.has(g) ? '' : 'none'; });

    const countEl = document.getElementById('resultCount');
    countEl.textContent = term
      ? matches.length + ' match' + (matches.length === 1 ? '' : 'es')
      : allGroups.length + ' coin' + (allGroups.length === 1 ? '' : 's');

    document.getElementById('pageInfo').textContent = 'Page ' + page + ' of ' + totalPages;
    document.getElementById('prevBtn').disabled = page <= 1;
    document.getElementById('nextBtn').disabled = page >= totalPages;
    document.getElementById('pagination').style.display = matches.length > PAGE_SIZE ? 'flex' : 'none';
  }

  render();
</script>
</body>
</html>
`;

fs.writeFileSync(outputPath, html);
console.log(
  `Scorecard dashboard: ${qualifying}/${GOAL} toward gate (correct + taken), ` +
    `${reviewed} reviewed, ${groups.length} coins grouped → ${outputPath.pathname}`
);
