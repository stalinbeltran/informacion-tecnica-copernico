# -*- coding: utf-8 -*-
"""Extrae texto estructurado + figuras de un PDF a JSON, usando el TOC como esqueleto."""
import fitz, sys, json, re, os, unicodedata
from collections import Counter, defaultdict

PDF = sys.argv[1]
OUT_JSON = sys.argv[2]
IMG_DIR = sys.argv[3]
DOC_ID = sys.argv[4]

HEAD_Y = 112.0
FOOT_Y = 742.0
MONO = ("Consolas", "CourierNew", "Courier")
BULLETS = "●○■▪–—•‣"

# lineas de cabecera/pie que se repiten en todas las paginas
BOILER = re.compile(
    r"^(©\s*Terradue|This document may only be reproduced|any means electronic|"
    r"with the terms of ESA Contract|with the prior permission of Terradue|"
    r"any means electronic, mechanical|Page \d+ of \d+|Ref:\s*T2-ESA|Issue:\s*\d|"
    r"Date:\s*20\d\d-\d\d-\d\d|Copernicus\s*LAC Infrastructure Support)", re.I)

os.makedirs(IMG_DIR, exist_ok=True)
doc = fitz.open(PDF)
NPAGES = doc.page_count


def norm(s):
    s = s.replace("​", "").replace("\xa0", " ")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- TOC -> arbol
toc = doc.get_toc()
# el primer entry (portada) no es capitulo real
nodes = []
for lvl, title, page in toc:
    t = norm(title)
    m = re.match(r"^((?:\d+\.)*\d+)\s*(.*)$", t)
    num = m.group(1) if m else ""
    name = m.group(2).strip() if m else t
    nodes.append({"level": lvl, "num": num, "title": name, "raw": t, "page": page})

# ------------------------------------------------- imagenes: descartar logos
xref_pages = defaultdict(set)
for pno in range(NPAGES):
    for im in doc[pno].get_images(full=True):
        xref_pages[im[0]].add(pno)
LOGOS = {x for x, ps in xref_pages.items() if len(ps) > 4}

# primera pagina de cuerpo: la del primer apartado numerado del TOC
FIRST_BODY_PAGE = min((n["page"] for n in nodes if n["num"]), default=1)

saved_imgs = {}


def row_is_bold(page, rect):
    """Una tabla tiene fila de cabecera real si esa fila va en negrita."""
    d = page.get_text("dict", clip=fitz.Rect(rect))
    tot = bold = 0
    for b in d["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                n = len(s["text"].strip())
                tot += n
                if "Bold" in s["font"]:
                    bold += n
    return tot > 0 and bold / tot > 0.6


def save_image(xref):
    if xref in saved_imgs:
        return saved_imgs[xref]
    d = doc.extract_image(xref)
    ext = d["ext"]
    fn = f"fig-{xref:04d}.{ext}"
    with open(os.path.join(IMG_DIR, fn), "wb") as f:
        f.write(d["image"])
    saved_imgs[xref] = (fn, d["width"], d["height"])
    return saved_imgs[xref]


# ------------------------------------------------------------ recorrer paginas
items = []  # (page, y0, x0, dict)

for pno in range(NPAGES):
    page = doc[pno]
    pnum = pno + 1

    # --- tablas: reservar sus areas para excluir el texto que contienen
    tboxes = []
    try:
        for t in page.find_tables().tables:
            data = t.extract()
            clean = [[norm(c or "") for c in row] for row in data]
            if not any(any(c for c in row) for row in clean):
                continue
            tboxes.append(fitz.Rect(t.bbox))
            hdr = bool(t.rows) and row_is_bold(page, t.rows[0].bbox)
            items.append((pnum, t.bbox[1], t.bbox[0],
                          {"type": "table", "rows": clean, "header": hdr,
                           "page": pnum}))
    except Exception:
        pass

    # --- figuras
    for im in page.get_images(full=True):
        xref = im[0]
        if xref in LOGOS:
            continue
        rects = page.get_image_rects(xref)
        for r in rects:
            if r.width < 40 or r.height < 30:
                continue
            fn, w, h = save_image(xref)
            items.append((pnum, r.y0, r.x0,
                          {"type": "figure", "src": fn, "w": w, "h": h, "page": pnum}))

    # --- lineas de texto
    lines = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            y0, y1 = l["bbox"][1], l["bbox"][3]
            if y1 < HEAD_Y or y0 > FOOT_Y:
                continue
            joined = "".join(s["text"] for s in l["spans"])
            txt = norm(joined)
            if not txt or BOILER.match(txt):
                continue
            # el codigo conserva su sangria original
            raw = joined.replace("​", "").replace("\xa0", " ").rstrip()
            c = fitz.Rect(l["bbox"]).tl + fitz.Rect(l["bbox"]).br
            center = fitz.Point(c.x / 2, c.y / 2)
            if any(tb.contains(center) for tb in tboxes):
                continue
            spans = [s for s in l["spans"] if s["text"].strip()]
            if not spans:
                continue
            size = max(s["size"] for s in spans)
            bold = all(("Bold" in s["font"]) for s in spans)
            mono = any(any(m in s["font"] for m in MONO) for s in spans)
            # ancho medio de caracter, para reconstruir la sangria del codigo
            cw = 0.0
            for s in spans:
                n = len(s["text"])
                if n:
                    cw = max(cw, (s["bbox"][2] - s["bbox"][0]) / n)
            lines.append({"y0": y0, "y1": y1, "x0": l["bbox"][0], "txt": txt,
                          "raw": raw, "size": size, "bold": bold, "mono": mono,
                          "cw": cw or 5.0, "block": b["number"]})
    lines.sort(key=lambda d: (round(d["y0"], 1), d["x0"]))

    # pitch tipico para separar parrafos
    gaps = [round(lines[i + 1]["y0"] - lines[i]["y0"], 1)
            for i in range(len(lines) - 1) if lines[i + 1]["y0"] > lines[i]["y0"]]
    pitch = Counter(g for g in gaps if 5 < g < 40).most_common(1)
    pitch = pitch[0][0] if pitch else 18.0

    # el indice impreso repite los titulos: no se buscan antes del primer capitulo
    toc_here = ({n["raw"] for n in nodes if n["page"] == pnum}
                if pnum >= FIRST_BODY_PAGE else set())

    para = None
    skip_to = -1
    for i, ln in enumerate(lines):
        if i <= skip_to:
            continue
        t = ln["txt"]
        is_toc_head = t in toc_here
        last_line = i
        if not is_toc_head:
            # un titulo largo puede ocupar dos o tres lineas en el cuerpo
            for k in (1, 2):
                if i + k >= len(lines):
                    break
                cand = norm(" ".join(lines[j]["txt"] for j in range(i, i + k + 1)))
                if cand in toc_here:
                    t, is_toc_head, last_line = cand, True, i + k
                    break
        bullet = t[0] in BULLETS
        nm = re.match(r"^(\d{1,2}[.)]|[a-z][.)])\s+(\S.*)$", t)
        numbered = bool(nm) and not ln["mono"]
        big = ln["size"] >= 13
        if ln["mono"]:
            newpara = (para is None or not para["mono"]
                       or (ln["y0"] - lines[i - 1]["y1"]) > pitch * 1.2)
        else:
            # una vinieta sangra su primera linea con el simbolo; las lineas de
            # continuacion caen mas a la derecha y deben seguir en el mismo item
            if para is not None and para["type"] == "bullet":
                dx = ln["x0"] - para["x0"]
                same_col = -6 <= dx <= 32
            else:
                same_col = para is not None and abs(ln["x0"] - para["x0"]) <= 6
            newpara = (para is None or bullet or numbered or is_toc_head or big
                       or ln["mono"] != para["mono"]
                       or (ln["y0"] - lines[i - 1]["y1"]) > pitch * 0.55
                       or not same_col)

        if is_toc_head or (big and ln["bold"]) or (ln["bold"] and len(t) < 90 and not bullet):
            items.append((pnum, ln["y0"], ln["x0"],
                          {"type": "heading", "text": t, "toc": is_toc_head,
                           "size": ln["size"], "page": pnum}))
            para = None
            skip_to = last_line
            continue

        if newpara:
            kind = "code" if ln["mono"] else ("bullet" if bullet or numbered else "para")
            body = ln["raw"] if ln["mono"] else t
            marker = None
            if bullet:
                body = t[1:].strip()
            elif numbered:
                marker, body = nm.group(1), nm.group(2)
            para = {"type": kind, "text": body, "x0": ln["x0"], "mono": ln["mono"],
                    "page": pnum, "indent": int(max(0, (ln["x0"] - 72) // 18))}
            if marker:
                para["marker"] = marker
            items.append((pnum, ln["y0"], ln["x0"], para))
        else:
            if ln["mono"]:
                pad = " " * int(round(max(0.0, ln["x0"] - para["x0"]) / ln["cw"]))
                para["text"] = para["text"] + "\n" + pad + ln["raw"]
            else:
                para["text"] = (para["text"] + " " + t).strip()

items.sort(key=lambda it: (it[0], round(it[1], 1), it[2]))
flat = [it[3] for it in items]

# limpiar campos auxiliares
for b in flat:
    b.pop("x0", None)
    b.pop("mono", None)

# --- unir tablas partidas por salto de pagina
merged = []
for b in flat:
    if (b["type"] == "table" and merged and merged[-1]["type"] == "table"
            and len(merged[-1]["rows"][0]) == len(b["rows"][0])
            and b["page"] - merged[-1]["page"] <= 1):
        merged[-1]["rows"].extend(b["rows"])
        continue
    merged.append(b)
flat = merged

# --- adjuntar pies "Figure N - ..." / "Table N - ..." a su figura/tabla
CAP = re.compile(r"^(Figure|Table|Fig\.)\s*\d+\s*[-–:]", re.I)
keep = []
for i, b in enumerate(flat):
    if b["type"] in ("para", "bullet") and CAP.match(b["text"]) and len(b["text"]) < 220:
        target = None
        for prev in reversed(keep[-3:]):            # pie debajo del elemento
            if prev["type"] in ("figure", "table"):
                target = prev
                break
        if target is None:                          # o titulo encima
            for nxt in flat[i + 1:i + 3]:
                if nxt["type"] in ("figure", "table"):
                    target = nxt
                    break
        if target is not None and "caption" not in target:
            target["caption"] = b["text"]
            continue
    keep.append(b)
flat = keep

# ------------------------------------------------- asignar bloques a secciones
sections = []
FRONT = {"level": 0, "num": "0", "title": "Portada, control del documento e índice",
         "raw": "__front__", "page": 1, "blocks": []}
cur = FRONT
sections.append(FRONT)
node_i = 0
# las entradas de portada del TOC no llevan numeracion: van al front matter
real_nodes = [n for n in nodes if n["num"]]

for b in flat:
    if b["type"] == "heading" and b.get("toc"):
        match = None
        for n in real_nodes:
            if n.get("_used"):
                continue
            if n["raw"] == b["text"] and abs(n["page"] - b["page"]) <= 1:
                match = n
                break
        if match:
            match["_used"] = True
            cur = dict(match)
            cur["blocks"] = []
            cur.pop("_used", None)
            sections.append(cur)
            continue
    cur["blocks"].append(b)

# el indice impreso del PDF sobra: la navegacion del sitio lo sustituye
fb = FRONT["blocks"]
for i, b in enumerate(fb):
    if b["type"] == "heading" and b["text"].lower().startswith("table of content"):
        FRONT["blocks"] = fb[:i]
        break

for n in real_nodes:
    if not n.get("_used"):
        print("  [aviso] seccion del TOC no localizada en el texto:", n["num"], n["title"])

# ----------------------------------------------------------------- ids / arbol
def make_id(sec):
    if sec["num"] == "0":
        return "portada"
    return "s" + sec["num"].replace(".", "-")


for s in sections:
    s["id"] = make_id(s)
    s.pop("raw", None)
    s.pop("_used", None)
    s["chars"] = sum(len(b.get("text", "")) for b in s["blocks"])
    s["figures"] = sum(1 for b in s["blocks"] if b["type"] == "figure")
    s["tables"] = sum(1 for b in s["blocks"] if b["type"] == "table")

out = {
    "doc_id": DOC_ID,
    "source_pdf": os.path.basename(PDF),
    "title": doc.metadata.get("title") or DOC_ID,
    "pages": NPAGES,
    "sections": sections,
}
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("secciones:", len(sections))
print("figuras guardadas:", len(saved_imgs))
print("tablas:", sum(s["tables"] for s in sections))
print("caracteres de texto:", sum(s["chars"] for s in sections))
