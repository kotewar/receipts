"""The demo page. Served live by FastAPI, or baked to static HTML for GitHub Pages."""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Receipts — a status update you can check</title>
<style>
  :root {
    --paper: #f6f4ef; --card: #fffefb; --ink: #1b1a17; --muted: #6f6a61;
    --line: #e2ddd2; --good: #1f6f4a; --goodbg: #eaf3ed;
    --bad: #a8271c; --badbg: #fbeeec; --warn: #8a5a00; --warnbg: #fdf3e0;
    --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--paper); color: var(--ink);
    font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  main { max-width: 780px; margin: 0 auto; padding: 40px 22px 90px; }
  header { margin-bottom: 26px; }
  h1 { margin: 0; font-size: 30px; letter-spacing: -0.02em; }
  h1 span { color: var(--muted); font-weight: 400; }
  .tagline { margin: 6px 0 0; color: var(--muted); max-width: 60ch; }
  .bar {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    padding: 12px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
    margin-bottom: 26px; flex-wrap: wrap;
  }
  .meta { font: 13px/1.4 var(--mono); color: var(--muted); }
  .switch { display: inline-flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; }
  .switch input { position: absolute; opacity: 0; pointer-events: none; }
  .track {
    width: 44px; height: 24px; border-radius: 99px; background: #d7d2c6;
    position: relative; transition: background .18s ease;
  }
  .track::after {
    content: ""; position: absolute; top: 3px; left: 3px; width: 18px; height: 18px;
    border-radius: 50%; background: #fff; transition: transform .18s ease;
    box-shadow: 0 1px 2px rgba(0,0,0,.25);
  }
  .switch input:checked + .track { background: var(--good); }
  .switch input:checked + .track::after { transform: translateX(20px); }
  .switch span:last-child { font-weight: 600; font-size: 14px; }
  .doc {
    background: var(--card); border: 1px solid var(--line); border-radius: 10px;
    padding: 30px 32px; box-shadow: 0 1px 2px rgba(27,26,23,.04);
  }
  .doc h2 { margin: 0 0 2px; font-size: 19px; }
  .doc .sub { margin: 0 0 22px; color: var(--muted); font-size: 14px; }
  ul { list-style: none; margin: 0; padding: 0; }
  li.bullet { padding: 13px 0 13px 20px; border-top: 1px solid var(--line); position: relative; }
  li.bullet:first-child { border-top: 0; }
  li.bullet::before {
    content: ""; position: absolute; left: 0; top: 21px; width: 7px; height: 7px;
    border-radius: 50%; background: #c9c3b6;
  }
  li.bullet.bad::before { background: var(--bad); }
  li.bullet.ok::before { background: var(--good); }
  .text { margin: 0; }
  .receipt {
    margin-top: 12px; border: 1px solid var(--line); border-radius: 8px;
    background: #fbfaf6; overflow: hidden;
  }
  .receipt .head {
    display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap;
    padding: 10px 12px; border-bottom: 1px solid var(--line);
    font: 12.5px/1.5 var(--mono);
  }
  .sha { font-weight: 700; }
  .chip {
    margin-left: auto; font: 11px/1 var(--mono); text-transform: uppercase;
    letter-spacing: .06em; padding: 5px 8px; border-radius: 4px; font-weight: 700;
  }
  .chip.ok { color: var(--good); background: var(--goodbg); }
  .chip.bad { color: var(--bad); background: var(--badbg); }
  .body { padding: 10px 12px; font-size: 13.5px; color: #45413a; }
  .files { font: 12px/1.6 var(--mono); color: var(--muted); }
  .why { margin: 10px 0 0; padding: 8px 10px; border-left: 3px solid var(--bad); background: var(--badbg); border-radius: 0 4px 4px 0; }
  .why b { color: var(--bad); }
  .needs { margin-top: 8px; font-size: 13px; color: var(--warn); background: var(--warnbg); padding: 8px 10px; border-radius: 4px; }
  .needs code { font-weight: 700; }
  details { margin-top: 10px; }
  summary { cursor: pointer; font-size: 13px; color: var(--muted); }
  pre {
    margin: 8px 0 0; padding: 10px; background: #f2efe7; border: 1px solid var(--line);
    border-radius: 6px; overflow-x: auto; font: 11.5px/1.55 var(--mono); max-height: 260px;
  }
  pre .plus { color: var(--good); } pre .minus { color: var(--bad); }
  .summary {
    margin: 18px 0 0; padding: 14px 16px; border-radius: 8px; font-size: 14.5px;
    background: var(--card); border: 1px solid var(--line);
  }
  .summary strong { font-variant-numeric: tabular-nums; }
  .raw { margin-top: 30px; }
  .raw h3 { font-size: 15px; margin: 0 0 4px; }
  .raw p { margin: 0 0 10px; color: var(--muted); font-size: 13.5px; }
  .commit { padding: 9px 0; border-top: 1px solid var(--line); font: 13px/1.5 var(--mono); }
  .commit .m { color: var(--muted); }
  .hidden { display: none; }
  footer { margin-top: 40px; color: var(--muted); font-size: 12.5px; text-align: center; }
  @media (max-width: 560px) { .doc { padding: 22px 18px; } }
</style>
</head>
<body>
<main>
  <header>
    <h1>Receipts <span>— a status update you can check</span></h1>
    <p class="tagline">
      A local 4B model reads a week of commits and writes the update a client wants to read.
      Every sentence carries the commit it came from. This page shows the update, then shows
      what the commits actually contained.
    </p>
  </header>

  <div class="bar">
    <div class="meta" id="meta">loading…</div>
    <label class="switch">
      <input type="checkbox" id="toggle">
      <span class="track"></span>
      <span>Show receipts</span>
    </label>
  </div>

  <section class="doc">
    <h2 id="client">Weekly update</h2>
    <p class="sub" id="week"></p>
    <ul id="bullets"></ul>
  </section>

  <p class="summary hidden" id="verdict"></p>

  <section class="raw">
    <h3>The raw material</h3>
    <p id="rawnote"></p>
    <div id="raw"></div>
  </section>

  <footer>One saved run, generated locally by gemma3:4b. Checked by <span style="font-family:var(--mono)">app/trace.py</span>, which is deterministic.</footer>
</main>

<!--DATA-->
<script>
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function diffHtml(diff) {
  return esc(diff).split('\\n').map(line => {
    if (line.startsWith('+')) return '<span class="plus">' + line + '</span>';
    if (line.startsWith('-')) return '<span class="minus">' + line + '</span>';
    return line;
  }).join('\\n');
}

const boot = window.__REPORT__
  ? Promise.resolve(window.__REPORT__)
  : fetch('/api/report').then(r => r.json());

boot.then(data => {
  const bySha = Object.fromEntries(data.commits.map(c => [c.short, c]));
  document.getElementById('meta').textContent =
    data.client + ' · ' + data.window[0] + ' → ' + data.window[1] + ' · ' + data.commits.length + ' commits';
  document.getElementById('client').textContent = 'Weekly update — ' + data.client;
  document.getElementById('week').textContent =
    'Week of ' + data.window[0] + '. ' + data.bullets.length + ' items.';

  const list = document.getElementById('bullets');
  list.innerHTML = data.bullets.map(b => {
    const ok = b.clean;
    const needs = b.needs ? bySha[b.needs] : null;
    const files = b.receipt.files.map(f => esc(f)).join(', ');
    const why = b.findings.length
      ? '<p class="why"><b>Receipt does not support this.</b> ' +
        b.findings.map(f => esc(f.detail)).join(' ') + '</p>'
      : '';
    const need = needs
      ? '<p class="needs">It needed <code>' + needs.short + '</code> — "' + esc(needs.message) + '"</p>'
      : '';
    return '<li class="bullet reveal ' + (ok ? 'ok' : 'bad') + '">' +
      '<p class="text">' + esc(b.text) + '</p>' +
      '<div class="receipt hidden">' +
        '<div class="head"><span class="sha">' + b.receipt.short + '</span>' +
          '<span>' + esc(b.receipt.message) + '</span>' +
          '<span class="chip ' + (ok ? 'ok' : 'bad') + '">' + (ok ? 'verified' : 'wrong receipt') + '</span>' +
        '</div>' +
        '<div class="body"><div class="files">' + esc(b.receipt.date) + ' · ' + files +
          ' · +' + b.receipt.insertions + ' −' + b.receipt.deletions + '</div>' +
          why + need +
          '<details><summary>the diff</summary><pre>' + diffHtml(b.receipt.diff) + '</pre></details>' +
        '</div>' +
      '</div></li>';
  }).join('');

  const raw = document.getElementById('raw');
  raw.innerHTML = data.commits.map(c =>
    '<div class="commit"><b>' + c.short + '</b> <span class="m">' + esc(c.date) + '</span> ' +
    esc(c.message) + '<br><span class="m">' + c.files.map(esc).join(', ') +
    ' · +' + c.insertions + ' −' + c.deletions + '</span></div>'
  ).join('');
  document.getElementById('rawnote').textContent =
    'Every commit the model was allowed to read. ' + data.commits.length + ' commits, none filtered.';

  const bad = data.bullets.filter(b => !b.clean).length;
  const verdict = document.getElementById('verdict');
  verdict.innerHTML = '<strong>' + bad + ' of ' + data.bullets.length + '</strong> receipts do not ' +
    'support the sentence above them. The report still reads perfectly.';

  document.getElementById('toggle').addEventListener('change', e => {
    document.querySelectorAll('.receipt').forEach(el => el.classList.toggle('hidden', !e.target.checked));
    verdict.classList.toggle('hidden', !e.target.checked);
  });
}).catch(err => {
  document.getElementById('meta').textContent = 'Could not load the report: ' + err;
});
</script>
</body>
</html>
"""
