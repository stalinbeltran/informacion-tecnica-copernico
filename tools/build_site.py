# -*- coding: utf-8 -*-
"""Genera el sitio HTML navegable por niveles a partir del JSON extraido del PDF."""
import json, os, sys, html, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
DATA = os.path.join(WEB, "data")
DOCS = os.path.join(WEB, "docs")

# ----------------------------------------------------------------- catalogo
CATALOG = [
    {
        "id": "d1-centre-specification",
        "code": "D1",
        "ref": "T2-ESA-COPLACI-RS-24-028",
        "file": ("T2-ESA-COPLACI-RS-24-028 D1 CopernicusLAC Centre Specification "
                 "and Performance Requirements v1.4.pdf"),
        "name": "CopernicusLAC Centre Specification and Performance Requirements",
        "version": "v1.4",
        "role": "Qué debe cumplir el Centro",
        "ready": True,
    },
    {
        "id": "d2-system-architecture",
        "code": "D2",
        "ref": "T2-ESA-COPLACI-DD-24-029",
        "file": "T2-ESA-COPLACI-DD-24-029 D2 System Architecture Description v1.3.pdf",
        "name": "System Architecture Description",
        "version": "v1.3",
        "role": "Cómo está construida la plataforma",
        "ready": True,
    },
    {
        "id": "d3-interface-control",
        "code": "D3",
        "ref": "T2-ESA-COPLACI-ID-24-030",
        "file": "T2-ESA-COPLACI-ID-24-030 D3 Interface Control Document v1.3.pdf",
        "name": "Interface Control Document",
        "version": "v1.3",
        "role": "Cómo se integra con ella desde fuera",
        "ready": True,
    },
]

e = html.escape

# --------------------------------------------------------- glosario de siglas
GLOSSARY = {}      # sigla -> significado
TOKEN_RE = None    # URLs + siglas, resuelto en build_glossary()


def build_glossary():
    """Reúne las tablas de acrónimos de todos los documentos en un único glosario."""
    global TOKEN_RE
    for m in CATALOG:
        p = os.path.join(DATA, m["id"] + ".json")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            doc = json.load(f)
        for s in doc["sections"]:
            if "cronym" not in s["title"]:
                continue
            for b in s["blocks"]:
                if b["type"] != "table":
                    continue
                for row in b["rows"]:
                    if len(row) >= 2 and row[0].strip() and row[1].strip():
                        GLOSSARY.setdefault(row[0].strip(), row[1].strip())

    if not GLOSSARY:
        TOKEN_RE = re.compile(r"(?P<url>https?://[^\s<>\"]+)|(?P<acr>(?!x)x)")
        return
    alt = "|".join(re.escape(k) for k in sorted(GLOSSARY, key=len, reverse=True))
    TOKEN_RE = re.compile(
        r"(?P<url>https?://[^\s<>\"]+)"
        r"|(?<![A-Za-z0-9_])(?P<acr>" + alt + r")s?(?![A-Za-z0-9_])")


def esc(t, acronyms=True):
    """Escapa el texto, enlaza URLs y marca las siglas con su definición."""
    out, pos = [], 0
    for m in TOKEN_RE.finditer(t):
        out.append(e(t[pos:m.start()]))
        if m.group("url"):
            u = e(m.group("url"))
            out.append(f'<a href="{u}" target="_blank" rel="noopener">{u}</a>')
        elif acronyms:
            out.append(f'<abbr class="acr" title="{e(GLOSSARY[m.group("acr")])}"'
                       f' tabindex="0">{e(m.group(0))}</abbr>')
        else:
            out.append(e(m.group(0)))
        pos = m.end()
    out.append(e(t[pos:]))
    return "".join(out)


# ------------------------------------------------------------------- plantilla
def page(title, subtitle, body, depth, extra_head="", body_class=""):
    up = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="stylesheet" href="{up}assets/css/style.css">
{extra_head}
</head>
<body class="{body_class}">
<header class="topbar">
  <a class="brand" href="{up}index.html">
    <span class="brand-mark">CL</span>
    <span class="brand-txt">Información Técnica<br><b>CopernicusLAC</b></span>
  </a>
  <button class="theme-toggle" type="button" data-theme-toggle title="Cambiar tema">◐</button>
</header>
<main>
{body}
</main>
<footer class="foot">
  <p>Vista navegable generada a partir de la documentación técnica de Terradue / ESA.
  El contenido original de los documentos se conserva en inglés.</p>
</footer>
<script src="{up}assets/js/app.js"></script>
</body>
</html>
"""


def breadcrumb(items):
    parts = []
    for i, (label, href) in enumerate(items):
        if href and i < len(items) - 1:
            parts.append(f'<a href="{href}">{e(label)}</a>')
        else:
            parts.append(f'<span>{e(label)}</span>')
    return '<nav class="crumbs">' + '<i>›</i>'.join(parts) + '</nav>'


def tagchips(tags):
    if not tags:
        return ""
    return '<div class="tags">' + "".join(f'<span class="tag">{e(t)}</span>' for t in tags) + '</div>'


# --------------------------------------------------------------- render bloques
def render_blocks(blocks, imgdir="img"):
    out, i, n = [], 0, len(blocks)
    while i < n:
        b = blocks[i]
        t = b["type"]

        if t in ("bullet",):
            # agrupa una lista completa (con su anidamiento por sangria)
            run = []
            while i < n and blocks[i]["type"] == "bullet":
                run.append(blocks[i])
                i += 1
            out.append(render_list(run))
            continue

        if t == "para":
            out.append(f'<p>{esc(b["text"])}</p>')
        elif t == "heading":
            out.append(f'<h3 class="inline-head">{esc(b["text"])}</h3>')
        elif t == "code":
            out.append(f'<pre><code>{e(b["text"])}</code></pre>')
        elif t == "figure":
            cap = f'<figcaption>{esc(b["caption"])}</figcaption>' if b.get("caption") else ""
            out.append(
                f'<figure class="fig">'
                f'<a href="{imgdir}/{b["src"]}" target="_blank" rel="noopener">'
                f'<img src="{imgdir}/{b["src"]}" alt="{e(b.get("caption","Figura"))}" loading="lazy">'
                f'</a>{cap}<span class="pg">p. {b["page"]}</span></figure>')
        elif t == "table":
            out.append(render_table(b))
        i += 1
    return "\n".join(out)


def render_list(run):
    """Reconstruye listas anidadas a partir del nivel de sangria de cada item.

    Las sublistas se emiten dentro del <li> padre, como exige el HTML.
    """
    levels = sorted({b.get("indent", 1) for b in run})
    rank = {v: k for k, v in enumerate(levels)}

    root = []
    stack = [(-1, root)]
    for b in run:
        d = rank[b.get("indent", 1)]
        while len(stack) > 1 and stack[-1][0] >= d:
            stack.pop()
        node = {"b": b, "kids": []}
        stack[-1][1].append(node)
        stack.append((d, node["kids"]))

    def emit(nodes):
        tag = "ol" if nodes[0]["b"].get("marker") else "ul"
        out = [f"<{tag}>"]
        for n in nodes:
            out.append("<li>" + esc(n["b"]["text"]))
            if n["kids"]:
                out.append(emit(n["kids"]))
            out.append("</li>")
        out.append(f"</{tag}>")
        return "".join(out)

    return emit(root) if root else ""


def render_table(b):
    rows = b["rows"]
    cap = f'<caption>{esc(b["caption"])}</caption>' if b.get("caption") else ""
    # sin fila de cabecera (glosarios, listas de términos) se vuelca todo al cuerpo;
    # ahí no se marcan siglas: la tabla ya es la definición
    if not b.get("header", True):
        body = "".join("<tr>" + "".join(f"<td>{esc(c, acronyms=False)}</td>" for c in r)
                       + "</tr>" for r in rows)
        return f'<div class="tablewrap"><table class="plain">{cap}<tbody>{body}</tbody></table></div>'
    # una primera fila casi vacía es un encabezado combinado: los nombres van debajo
    if len(rows) > 2 and sum(1 for c in rows[0] if not c) > len(rows[0]) / 2:
        rows = rows[1:]
    head = "".join(f"<th>{esc(c)}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>"
                   for r in rows[1:])
    return (f'<div class="tablewrap"><table>{cap}<thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


# ------------------------------------------------------------------- utilidades
def stats(node):
    """Metricas agregadas de un nodo y toda su descendencia."""
    figs = node["sec"]["figures"]
    tabs = node["sec"]["tables"]
    chars = node["sec"]["chars"]
    pages = {bl["page"] for bl in node["sec"]["blocks"] if "page" in bl}
    leaves = 0
    for c in node["kids"]:
        s = stats(c)
        figs += s["figs"]; tabs += s["tabs"]; chars += s["chars"]
        pages |= s["pages"]; leaves += s["leaves"]
    return {"figs": figs, "tabs": tabs, "chars": chars, "pages": pages,
            "leaves": leaves or 1}


def metrics_html(st, kids):
    m = []
    if kids:
        m.append(f'<span title="Apartados"><b>{len(kids)}</b> apartados</span>')
    if st["pages"]:
        lo, hi = min(st["pages"]), max(st["pages"])
        m.append(f'<span title="Páginas del PDF">pp. <b>{lo}{"–%d" % hi if hi > lo else ""}</b></span>')
    if st["figs"]:
        m.append(f'<span title="Figuras"><b>{st["figs"]}</b> fig.</span>')
    if st["tabs"]:
        m.append(f'<span title="Tablas"><b>{st["tabs"]}</b> tabl.</span>')
    return '<div class="metrics">' + "".join(m) + '</div>'


def card(href, eyebrow, title, summary, tags, st, kids, leaf):
    return f"""<a class="card{' leaf' if leaf else ''}" href="{href}">
  <span class="eyebrow">{e(eyebrow)}</span>
  <h3>{e(title)}</h3>
  <p class="sum">{esc(summary)}</p>
  {tagchips(tags)}
  {metrics_html(st, kids)}
  <span class="go">{'Ver el detalle' if leaf else 'Explorar'} <i>→</i></span>
</a>"""


# ----------------------------------------------------------------- construccion
def build_doc(meta):
    with open(os.path.join(DATA, meta["id"] + ".json"), encoding="utf-8") as f:
        doc = json.load(f)
    spath = os.path.join(DATA, meta["id"] + ".summaries.json")
    summ = json.load(open(spath, encoding="utf-8")) if os.path.exists(spath) else {"sections": {}}
    S = summ.get("sections", {})

    def sm(sec, key="short"):
        return S.get(sec["id"], {}).get(key, "")

    def tg(sec):
        return S.get(sec["id"], {}).get("tags", [])

    # arbol
    roots, stack = [], []
    for sec in doc["sections"]:
        node = {"sec": sec, "kids": []}
        lvl = sec["level"]
        if lvl <= 1:
            roots.append(node)
            stack = [node]
        else:
            while len(stack) > lvl - 1:
                stack.pop()
            (stack[-1]["kids"] if stack else roots).append(node)
            stack.append(node)

    outdir = os.path.join(DOCS, meta["id"])
    os.makedirs(outdir, exist_ok=True)
    docname = f'{meta["code"]} · {meta["name"]}'

    index_of = {}

    def walk(node, parents):
        sec = node["sec"]
        index_of[sec["id"]] = (sec, parents[:])
        for k in node["kids"]:
            walk(k, parents + [node])
    for r in roots:
        walk(r, [])

    # ------------------------------------------------- pagina de cada seccion
    flat_nodes = []

    def collect(node):
        flat_nodes.append(node)
        for k in node["kids"]:
            collect(k)
    for r in roots:
        collect(r)

    order = [n["sec"]["id"] for n in flat_nodes]

    def label(sec):
        return (f'{sec["num"]} · {sec["title"]}' if sec["num"] not in ("0", "")
                else sec["title"])

    for pos, node in enumerate(flat_nodes):
        sec = node["sec"]
        _, parents = index_of[sec["id"]]
        crumbs = [("Documentos", "../../index.html"), (meta["code"], "index.html")]
        for p in parents:
            crumbs.append((p["sec"]["num"] or p["sec"]["title"], p["sec"]["id"] + ".html"))
        crumbs.append((label(sec), None))

        st = stats(node)
        leaf = not node["kids"]
        body = [breadcrumb(crumbs)]
        body.append(f"""<div class="pagehead">
  <span class="eyebrow">{e(docname)}{' · Capítulo ' + sec["num"] if sec["num"] not in ("0","") else ''}</span>
  <h1>{e(sec["title"])}</h1>
  <p class="lede">{esc(sm(sec))}</p>
  {tagchips(tg(sec))}
  {metrics_html(st, node["kids"])}
</div>""")

        content = render_blocks(sec["blocks"])
        if content:
            body.append(f'<section class="prose">{content}</section>')

        if node["kids"]:
            body.append('<h2 class="secttl">En este capítulo</h2>' if sec["level"] <= 1
                        else '<h2 class="secttl">Apartados</h2>')
            body.append('<div class="grid">')
            for k in node["kids"]:
                ks, kst = k["sec"], stats(k)
                body.append(card(ks["id"] + ".html", ks["num"], ks["title"],
                                 sm(ks) or "—", tg(ks), kst, k["kids"], not k["kids"]))
            body.append('</div>')

        prev_id = order[pos - 1] if pos > 0 else None
        next_id = order[pos + 1] if pos + 1 < len(order) else None
        nav = ['<nav class="pager">']
        if prev_id:
            nav.append(f'<a class="prev" href="{prev_id}.html"><i>←</i>'
                       f'<span>{e(label(index_of[prev_id][0]))}</span></a>')
        else:
            nav.append('<span></span>')
        if next_id:
            nav.append(f'<a class="next" href="{next_id}.html">'
                       f'<span>{e(label(index_of[next_id][0]))}</span><i>→</i></a>')
        nav.append('</nav>')
        body.append("".join(nav))

        with open(os.path.join(outdir, sec["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(page(f'{sec["num"]} {sec["title"]} · {meta["code"]}', "",
                         "\n".join(body), depth=2))

    # ------------------------------------------------------ indice del documento
    idx = [{"i": n["sec"]["id"], "n": n["sec"]["num"], "t": n["sec"]["title"],
            "s": sm(n["sec"]), "l": n["sec"]["level"]} for n in flat_nodes]
    search_js = ('<script>window.__IDX__=' + json.dumps(idx, ensure_ascii=False)
                 + ';</script>')

    d = summ.get("doc", {})
    total = stats({"sec": {"figures": 0, "tables": 0, "chars": 0, "blocks": []},
                   "kids": roots})
    n_chapters = sum(1 for r in roots if r["sec"]["level"] == 1)
    body = [breadcrumb([("Documentos", "../../index.html"), (meta["code"], None)])]
    body.append(f"""<div class="pagehead doc">
  <span class="eyebrow">{e(meta["ref"])} · {e(meta["version"])} · {doc["pages"]} páginas</span>
  <h1>{e(meta["code"])} — {e(meta["name"])}</h1>
  <p class="lede">{esc(d.get("short",""))}</p>
  <p class="long">{esc(d.get("long",""))}</p>
  {tagchips(d.get("tags"))}
  <div class="metrics">
    <span><b>{n_chapters}</b> capítulos</span>
    <span><b>{len(flat_nodes)}</b> secciones</span>
    <span><b>{total["figs"]}</b> figuras</span>
    <span><b>{total["tabs"]}</b> tablas</span>
  </div>
  <p class="src">Fuente: <a href="../../../{e(meta["file"])}">{e(meta["file"])}</a></p>
</div>""")
    body.append(f"""<div class="searchbox">
  <input type="search" id="q" autocomplete="off"
         placeholder="Buscar entre las {len(flat_nodes)} secciones del documento…">
  <div id="results" class="results"></div>
</div>""")
    body.append('<h2 class="secttl">Capítulos</h2><div class="grid">')
    for r in roots:
        rs, rst = r["sec"], stats(r)
        body.append(card(rs["id"] + ".html", rs["num"] if rs["num"] != "0" else "—",
                         rs["title"], sm(rs) or "—", tg(rs), rst, r["kids"], not r["kids"]))
    body.append('</div>')

    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(page(f'{meta["code"]} · {meta["name"]}', "", "\n".join(body),
                     depth=2, extra_head=search_js))

    return {"sections": len(flat_nodes), "chapters": n_chapters,
            "figs": total["figs"], "tabs": total["tabs"], "pages": doc["pages"],
            "summary": d.get("short", ""), "tags": d.get("tags", [])}


# ------------------------------------------------------------------ portada
def build_home(results):
    cards = []
    for m in CATALOG:
        r = results.get(m["id"])
        if r:
            cards.append(f"""<a class="card doccard" href="docs/{m["id"]}/index.html">
  <span class="eyebrow">{e(m["ref"])} · {e(m["version"])}</span>
  <h3>{e(m["code"])} — {e(m["name"])}</h3>
  <p class="role">{e(m.get("role",""))}</p>
  <p class="sum">{esc(r["summary"])}</p>
  {tagchips(r["tags"])}
  <div class="metrics">
    <span><b>{r["pages"]}</b> páginas</span>
    <span><b>{r["chapters"]}</b> capítulos</span>
    <span><b>{r["sections"]}</b> secciones</span>
    <span><b>{r["figs"]}</b> figuras</span>
    <span><b>{r["tabs"]}</b> tablas</span>
  </div>
  <span class="go">Explorar el documento <i>→</i></span>
</a>""")
        else:
            cards.append(f"""<div class="card doccard pending">
  <span class="eyebrow">{e(m["ref"])} · {e(m["version"])}</span>
  <h3>{e(m["code"])} — {e(m["name"])}</h3>
  <p class="sum">Todavía no procesado. El PDF está en el proyecto y puede incorporarse
  con el mismo flujo de extracción y generación.</p>
  <span class="go pend">Pendiente de procesar</span>
</div>""")

    body = f"""<div class="hero">
  <span class="eyebrow">Documentación técnica · Terradue / ESA</span>
  <h1>Centro CopernicusLAC</h1>
  <p class="lede">Los documentos técnicos del proyecto <b>CopernicusLAC Infrastructure Support</b>,
  convertidos en una vista navegable por niveles: empieza por el documento, baja a sus capítulos,
  de ahí a cada apartado y, al final del recorrido, al texto completo con sus figuras y tablas.</p>
</div>
<h2 class="secttl">Documentos</h2>
<div class="grid">
{"".join(cards)}
</div>
<div class="howto">
  <h2>Cómo está organizado</h2>
  <ol class="levels">
    <li><b>Nivel 1 — Documentos.</b> Esta página: el nombre de cada archivo y qué contiene.</li>
    <li><b>Nivel 2 — Capítulos.</b> Los bloques principales del documento, cada uno con su resumen.</li>
    <li><b>Nivel 3 — Apartados.</b> Las secciones de cada capítulo, resumidas.</li>
    <li><b>Nivel 4 — Detalle completo.</b> El texto íntegro con las figuras, tablas y ejemplos de código del PDF original.</li>
  </ol>
</div>"""
    with open(os.path.join(WEB, "index.html"), "w", encoding="utf-8") as f:
        f.write(page("Información Técnica CopernicusLAC", "", body, depth=0,
                     body_class="home"))


if __name__ == "__main__":
    build_glossary()
    print("siglas en el glosario:", len(GLOSSARY))
    res = {}
    for m in CATALOG:
        if m["ready"] and os.path.exists(os.path.join(DATA, m["id"] + ".json")):
            res[m["id"]] = build_doc(m)
            print("generado:", m["id"], res[m["id"]]["sections"], "paginas HTML")
    build_home(res)
    print("portada generada")
