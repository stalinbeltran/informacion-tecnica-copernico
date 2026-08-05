/* Tema claro/oscuro + buscador del índice del documento. Sin dependencias. */
(function () {
  "use strict";

  /* ---------------------------------------------------------------- tema */
  var KEY = "coplac-theme";
  try {
    var saved = localStorage.getItem(KEY);
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  } catch (e) {}

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-theme-toggle]");
    if (!btn) return;
    var cur = document.documentElement.getAttribute("data-theme");
    if (!cur) {
      cur = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    var next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem(KEY, next); } catch (e) {}
  });

  /* --------------------------------------------- tooltips de siglas (abbr) */
  (function () {
    var marks = document.querySelectorAll("abbr.acr[title]");
    if (!marks.length) return;

    // el title nativo se traslada a data-def: sirve de reserva si el JS no corre
    for (var i = 0; i < marks.length; i++) {
      marks[i].setAttribute("data-def", marks[i].getAttribute("title"));
      marks[i].removeAttribute("title");
    }

    var tip = document.createElement("div");
    tip.className = "acrtip";
    tip.setAttribute("role", "tooltip");
    document.body.appendChild(tip);
    var current = null, pinned = false;

    function show(el) {
      current = el;
      tip.textContent = el.getAttribute("data-def");
      tip.classList.add("on");
      var r = el.getBoundingClientRect();
      var w = tip.offsetWidth, h = tip.offsetHeight, pad = 8;
      var left = r.left + r.width / 2 - w / 2;
      left = Math.max(pad, Math.min(left, window.innerWidth - w - pad));
      var top = r.top - h - 9;
      tip.classList.toggle("below", top < pad);
      if (top < pad) top = r.bottom + 9;
      tip.style.left = left + "px";
      tip.style.top = top + "px";
      tip.style.setProperty("--arrow", (r.left + r.width / 2 - left) + "px");
    }

    function hide() {
      tip.classList.remove("on");
      current = null;
      pinned = false;
    }

    document.addEventListener("mouseover", function (ev) {
      var el = ev.target.closest("abbr.acr");
      if (el) { pinned = false; show(el); }
      else if (current && !pinned) hide();
    });
    document.addEventListener("focusin", function (ev) {
      var el = ev.target.closest("abbr.acr");
      if (el) show(el);
    });
    document.addEventListener("focusout", function () { if (!pinned) hide(); });
    document.addEventListener("click", function (ev) {
      var el = ev.target.closest("abbr.acr");
      // dentro de una tarjeta manda el enlace: no se secuestra el clic
      if (el && !el.closest("a")) {
        ev.preventDefault();
        pinned = current !== el || !pinned;
        show(el);
      } else {
        hide();
      }
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") hide();
    });
    window.addEventListener("scroll", function () { if (current) hide(); }, true);
    window.addEventListener("resize", hide);
  })();

  /* ------------------------------------------------------------ búsqueda */
  var input = document.getElementById("q");
  var box = document.getElementById("results");
  var idx = window.__IDX__;
  if (!input || !box || !idx) return;

  function norm(s) {
    return s.toLowerCase().normalize("NFD").replace(new RegExp("[\\u0300-\\u036f]", "g"), "");
  }

  var data = idx.map(function (r) {
    return { r: r, hay: norm((r.n || "") + " " + r.t + " " + (r.s || "")) };
  });

  function render(list, term) {
    if (!list.length) {
      box.innerHTML = '<div class="empty">Sin resultados para “' + term + '”.</div>';
      box.classList.add("on");
      return;
    }
    box.innerHTML = list.slice(0, 40).map(function (d) {
      var r = d.r;
      return '<a href="' + r.i + '.html">' +
        (r.n && r.n !== "0" ? '<span class="rn">' + r.n + '</span>' : '') +
        '<span class="rt">' + r.t + '</span>' +
        (r.s ? '<span class="rs">' + r.s + '</span>' : '') +
        '</a>';
    }).join("");
    box.classList.add("on");
  }

  var t;
  input.addEventListener("input", function () {
    clearTimeout(t);
    t = setTimeout(function () {
      var q = norm(input.value.trim());
      if (q.length < 2) { box.classList.remove("on"); box.innerHTML = ""; return; }
      var terms = q.split(/\s+/);
      var hits = data.filter(function (d) {
        return terms.every(function (w) { return d.hay.indexOf(w) !== -1; });
      });
      // los niveles mas altos primero: dan mejor punto de entrada
      hits.sort(function (a, b) { return a.r.l - b.r.l; });
      render(hits, input.value.trim());
    }, 110);
  });

  document.addEventListener("click", function (ev) {
    if (!ev.target.closest(".searchbox")) box.classList.remove("on");
  });
  input.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") { input.value = ""; box.classList.remove("on"); }
  });
})();
