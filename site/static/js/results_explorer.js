/* Results explorer: reads data/a_modelos_por_h.json (generated from results/ by docs/scripts/build_site.py)
   and renders a table and a bar chart (plain SVG). No backend, no key, no third-party library.
   MASE uses the Naive of the same horizon, so it is shown for one horizon at a time only. */
(function () {
  "use strict";

  var I18N = {
    en: {
      target: "Target",
      horizon: "Horizon",
      metric: "Metric",
      all: "All horizons (MAE or skill only)",
      model: "Model",
      mae: "MAE (admissions per day)",
      mase: "MASE (vs Naïve of the same h)",
      skill: "Skill vs best naive of the same h",
      noteMase: "MASE divides by the Naïve of the same horizon: compare models within one horizon only. The " +
        "“all horizons” view is disabled for MASE.",
      noteMae: "MAE is in admissions per day and can be compared across horizons.",
      noteSkill: "Skill = 1 − MAE / min(Naïve, Seasonal Naïve) of the same horizon; above 0 beats both naive baselines.",
      run: "Run",
      runs: "Runs",
      commit: "commit",
      error: "Could not load data/a_modelos_por_h.json. Open the page through a web server (for example " +
        "python -m http.server in site/) instead of the file system.",
      chartTitle: function (m, t, h) { return m + " · " + t + " · h = " + h; }
    },
    pt: {
      target: "Alvo",
      horizon: "Horizonte",
      metric: "Métrica",
      all: "Todos os horizontes (só MAE ou skill)",
      model: "Modelo",
      mae: "MAE (internações por dia)",
      mase: "MASE (contra o Naïve do mesmo h)",
      skill: "Skill contra o melhor ingênuo do mesmo h",
      noteMase: "O MASE divide pelo Naïve do mesmo horizonte: compare modelos só dentro de um horizonte. A visão " +
        "“todos os horizontes” fica desabilitada para o MASE.",
      noteMae: "O MAE está em internações por dia e pode ser comparado entre horizontes.",
      noteSkill: "Skill = 1 − MAE / min(Naïve, Seasonal Naïve) do mesmo horizonte; acima de 0 supera os dois ingênuos.",
      run: "Run",
      runs: "Runs",
      commit: "commit",
      error: "Não foi possível carregar data/a_modelos_por_h.json. Abra a página por um servidor web (por exemplo " +
        "python -m http.server dentro de site/) em vez do sistema de arquivos.",
      chartTitle: function (m, t, h) { return m + " · " + t + " · h = " + h; }
    }
  };
  var DECIMALS = { MAE: 2, MASE: 3, skill: 3 };

  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    if (attrs) { Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); }); }
    if (text !== undefined) { e.textContent = text; }
    return e;
  }

  function svgEl(tag, attrs, text) {
    var e = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text !== undefined) { e.textContent = text; }
    return e;
  }

  // decimal point in both languages, as in the result tables and the source files
  function fmt(v, metric) {
    return v.toFixed(DECIMALS[metric]);
  }

  function select(id, label, options) {
    var wrap = el("div");
    wrap.appendChild(el("label", { "for": id }, label));
    var sw = el("div", { "class": "select is-small" });
    var s = el("select", { id: id });
    options.forEach(function (o) {
      var opt = el("option", { value: o[0] }, o[1]);
      s.appendChild(opt);
    });
    sw.appendChild(s);
    wrap.appendChild(sw);
    return { wrap: wrap, select: s };
  }

  function barChart(data, metric, lang, title) {
    var W = 720, rowH = 30, left = 130, right = 70, top = 34, bottom = 26;
    var H = top + bottom + rowH * data.length;
    var vals = data.map(function (d) { return d.value; });
    var lo = Math.min(0, Math.min.apply(null, vals));
    var hi = Math.max(0, Math.max.apply(null, vals));
    if (hi === lo) { hi = lo + 1; }
    var span = hi - lo;
    var x = function (v) { return left + (v - lo) / span * (W - left - right); };
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": title });
    svg.appendChild(svgEl("text", { x: 0, y: 16, "font-weight": "600" }, title));
    svg.appendChild(svgEl("line", { x1: x(0), x2: x(0), y1: top - 6, y2: H - bottom + 4, stroke: "#898781", "stroke-width": 1 }));
    data.forEach(function (d, i) {
      var y = top + i * rowH;
      var x0 = x(Math.min(0, d.value)), x1 = x(Math.max(0, d.value));
      svg.appendChild(svgEl("text", { x: left - 8, y: y + rowH / 2 + 4, "text-anchor": "end" }, d.label));
      svg.appendChild(svgEl("rect", { x: x0, y: y + 5, width: Math.max(1, x1 - x0), height: Math.min(20, rowH - 10), fill: d.color, rx: 2 }));
      var tx = d.value >= 0 ? x1 + 6 : x0 - 6;
      svg.appendChild(svgEl("text", { x: tx, y: y + rowH / 2 + 4, "text-anchor": d.value >= 0 ? "start" : "end" }, fmt(d.value, metric)));
    });
    return svg;
  }

  function render(root, db, lang) {
    var t = I18N[lang];
    root.innerHTML = "";
    var controls = el("div", { "class": "rx-controls" });
    var sAlvo = select("rx-alvo", t.target, Object.keys(db.alvos).map(function (a) { return [a, db.alvos[a].rotulo[lang]]; }));
    var hOpts = db.horizontes.map(function (h) { return [String(h), "h = " + h]; });
    hOpts.push(["all", t.all]);
    var sH = select("rx-h", t.horizon, hOpts);
    var sM = select("rx-metrica", t.metric, [["MAE", t.mae], ["MASE", t.mase], ["skill", t.skill]]);
    [sAlvo, sH, sM].forEach(function (s) { controls.appendChild(s.wrap); });
    root.appendChild(controls);
    var note = el("p", { "class": "rx-note" });
    var chart = el("div", { "class": "rx-chart" });
    var tableWrap = el("div", { "class": "table-container" });
    var run = el("p", { "class": "rx-run" });
    var status = el("p", { "class": "rx-note" }, db.nota[lang]);
    [note, chart, tableWrap, run, status].forEach(function (n) { root.appendChild(n); });

    function update() {
      var alvo = sAlvo.select.value, metric = sM.select.value;
      var allOpt = sH.select.querySelector('option[value="all"]');
      allOpt.disabled = metric === "MASE";
      if (metric === "MASE" && sH.select.value === "all") { sH.select.value = String(db.horizontes[0]); }
      var hsel = sH.select.value;
      note.textContent = metric === "MASE" ? t.noteMase : (metric === "MAE" ? t.noteMae : t.noteSkill);
      var hs = hsel === "all" ? db.horizontes.map(String) : [hsel];
      var table = el("table", { "class": "table is-narrow is-fullwidth rx-table" });
      var thead = el("thead"), tr = el("tr");
      tr.appendChild(el("th", null, t.model));
      hs.forEach(function (h) { tr.appendChild(el("th", { "class": "has-text-right" }, "h = " + h)); });
      thead.appendChild(tr);
      table.appendChild(thead);
      var tbody = el("tbody");
      db.modelos.forEach(function (m) {
        var r = el("tr");
        r.appendChild(el("th", null, m.rotulo));
        hs.forEach(function (h) {
          var v = db.alvos[alvo].por_h[h].valores[m.chave][metric];
          r.appendChild(el("td", { "class": "num" }, fmt(v, metric)));
        });
        tbody.appendChild(r);
      });
      table.appendChild(tbody);
      tableWrap.innerHTML = "";
      tableWrap.appendChild(table);
      chart.innerHTML = "";
      if (hsel !== "all") {
        var data = db.modelos.map(function (m) {
          return { label: m.rotulo, color: m.cor, value: db.alvos[alvo].por_h[hsel].valores[m.chave][metric] };
        });
        var mlabel = metric === "MAE" ? t.mae : (metric === "MASE" ? t.mase : t.skill);
        chart.appendChild(barChart(data, metric, lang, t.chartTitle(mlabel, db.alvos[alvo].rotulo[lang], hsel)));
      }
      run.innerHTML = "";
      run.appendChild(document.createTextNode((hs.length > 1 ? t.runs : t.run) + ": "));
      hs.forEach(function (h, i) {
        var p = db.alvos[alvo].por_h[h];
        run.appendChild(el("code", null, p.run_id));
        run.appendChild(document.createTextNode(" (h = " + h + ", " + t.commit + " " + p.git_commit.slice(0, 7) + ")" + (i < hs.length - 1 ? ", " : "")));
      });
    }
    [sAlvo, sH, sM].forEach(function (s) { s.select.addEventListener("change", update); });
    update();
  }

  function init() {
    var root = document.getElementById("results-explorer");
    if (!root) { return; }
    var lang = root.getAttribute("data-lang") === "pt" ? "pt" : "en";
    fetch(root.getAttribute("data-src"))
      .then(function (r) { if (!r.ok) { throw new Error(r.status); } return r.json(); })
      .then(function (db) { render(root, db, lang); })
      .catch(function () { root.appendChild(el("p", { "class": "notification is-danger is-light" }, I18N[lang].error)); });
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); } else { init(); }
})();
