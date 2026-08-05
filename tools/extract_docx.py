# -*- coding: utf-8 -*-
"""Extrae texto estructurado + imagenes de un .docx al mismo JSON que extract.py.

A diferencia del PDF, un .docx no trae indice fiable ni paginacion, asi que el
arbol de secciones se deduce de los titulos y los bloques no llevan numero de
pagina. El resto del esquema es identico, para que build_site.py no distinga.

Uso:  python tools/extract_docx.py <archivo.docx> <salida.json> <dir_img> <doc_id>
"""
import sys, os, re, json, zipfile, struct, unicodedata
import xml.etree.ElementTree as ET

DOCX = sys.argv[1]
OUT_JSON = sys.argv[2]
IMG_DIR = sys.argv[3]
DOC_ID = sys.argv[4]

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
EP = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"

MONO = ("consolas", "courier", "menlo", "monaco", "mono")
# titulos por patron: capitulo, romano, decimal, anexo
PAT_CHAP = re.compile(r"^CAP[IÍ]TULO\s+([IVXLC]+)\b", re.I)
PAT_ROMAN = re.compile(r"^([IVXLC]{1,6})[.\-–)]\s+(\S.*)$")
PAT_DEC = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+(\S.*)$")
PAT_ANNEX = re.compile(r"^(ANEXO|AP[EÉ]NDICE|FORMULARIO)\s+([A-Z0-9IVX]+)\b", re.I)

os.makedirs(IMG_DIR, exist_ok=True)
z = zipfile.ZipFile(DOCX)


def norm(s):
    s = (s or "").replace("​", "").replace("\xa0", " ")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[ \t]+", " ", s).strip()


# ------------------------------------------------------------------ relaciones
rels = {}
try:
    for rel in ET.fromstring(z.read("word/_rels/document.xml.rels")):
        rels[rel.get("Id")] = rel.get("Target")
except KeyError:
    pass

# -------------------------------------------------------- estilos -> nivel
# Word guarda el nivel de esquema en el estilo, no siempre en el parrafo.
style_level = {}   # styleId -> nivel de titulo (1..6)
style_name = {}
try:
    st_root = ET.fromstring(z.read("word/styles.xml"))
    for st in st_root.iter(W + "style"):
        sid = st.get(W + "styleId") or ""
        nm = st.find(W + "name")
        nm = nm.get(W + "val") if nm is not None else ""
        style_name[sid] = nm
        lvl = None
        m = re.match(r"^(?:heading|t[ií]tulo|ttulo)\s*(\d)$", nm.strip(), re.I) \
            or re.match(r"^(?:Heading|T[ií]tulo|Ttulo)(\d)$", sid)
        if m:
            lvl = int(m.group(1))
        else:
            ppr = st.find(W + "pPr")
            if ppr is not None:
                ol = ppr.find(W + "outlineLvl")
                if ol is not None:
                    lvl = int(ol.get(W + "val")) + 1
        if lvl:
            style_level[sid] = min(lvl, 6)
except KeyError:
    pass

# ------------------------------------------------------- numeracion de listas
num_fmt = {}     # (numId, ilvl) -> formato ("bullet" | "decimal" | ...)
try:
    nb = ET.fromstring(z.read("word/numbering.xml"))
    abstract = {}
    for an in nb.iter(W + "abstractNum"):
        aid = an.get(W + "abstractNumId")
        for lv in an.findall(W + "lvl"):
            il = int(lv.get(W + "ilvl", "0"))
            f = lv.find(W + "numFmt")
            abstract[(aid, il)] = f.get(W + "val") if f is not None else "bullet"
    for n in nb.iter(W + "num"):
        nid = n.get(W + "numId")
        a = n.find(W + "abstractNumId")
        if a is None:
            continue
        aid = a.get(W + "val")
        for (xa, il), f in abstract.items():
            if xa == aid:
                num_fmt[(nid, il)] = f
except KeyError:
    pass


# --------------------------------------------------------------- imagenes
def img_size(data):
    """Dimensiones en pixeles leyendo la cabecera, sin dependencias externas."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:2] == b"\xff\xd8":                       # JPEG
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            m = data[i + 1]
            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                     0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7:
                i += 2
                continue
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    if data[:6] in (b"GIF87a", b"GIF89a"):
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    return 0, 0


saved = {}


def save_image(target):
    if target in saved:
        return saved[target]
    path = "word/" + target.replace("\\", "/").lstrip("/")
    if path not in z.namelist():
        path = os.path.normpath(os.path.join("word", target)).replace("\\", "/")
    if path not in z.namelist():
        return None
    data = z.read(path)
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext not in ("png", "jpg", "jpeg", "gif", "webp"):
        return None                                   # emf/wmf no las pinta el navegador
    fn = "img-%03d.%s" % (len(saved) + 1, ext)
    with open(os.path.join(IMG_DIR, fn), "wb") as f:
        f.write(data)
    w, h = img_size(data)
    saved[target] = (fn, w, h)
    return saved[target]


# --------------------------------------------------------- lectura de parrafos
def runs_of(p):
    return [r for r in p.iter(W + "r") if r.find(W + "t") is not None]


def para_text(p):
    parts = []
    for node in p.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag in (W + "tab",):
            parts.append(" ")
        elif node.tag in (W + "br", W + "cr"):
            parts.append("\n")
    return norm("".join(parts))


def is_bold(p):
    rs = runs_of(p)
    if not rs:
        return False
    n = 0
    for r in rs:
        if not (r.find(W + "t") is not None and (r.find(W + "t").text or "").strip()):
            continue
        rpr = r.find(W + "rPr")
        b = rpr is not None and rpr.find(W + "b") is not None \
            and rpr.find(W + "b").get(W + "val") not in ("0", "false")
        if not b:
            return False
        n += 1
    return n > 0


def is_mono(p):
    for r in runs_of(p):
        rpr = r.find(W + "rPr")
        if rpr is None:
            continue
        f = rpr.find(W + "rFonts")
        if f is not None:
            name = (f.get(W + "ascii") or f.get(W + "hAnsi") or "").lower()
            if any(m in name for m in MONO):
                return True
    return False


def font_size(p):
    for r in runs_of(p):
        rpr = r.find(W + "rPr")
        if rpr is not None and rpr.find(W + "sz") is not None:
            try:
                return int(rpr.find(W + "sz").get(W + "val")) / 2.0
            except (TypeError, ValueError):
                pass
    return 0.0


def numbering_of(p):
    """(formato, nivel) si el parrafo es item de lista."""
    ppr = p.find(W + "pPr")
    if ppr is None:
        return None
    npr = ppr.find(W + "numPr")
    if npr is None:
        return None
    nid = npr.find(W + "numId")
    il = npr.find(W + "ilvl")
    if nid is None:
        return None
    nid = nid.get(W + "val")
    il = int(il.get(W + "val")) if il is not None else 0
    return num_fmt.get((nid, il), "bullet"), il


def style_of(p):
    ppr = p.find(W + "pPr")
    if ppr is None:
        return ""
    st = ppr.find(W + "pStyle")
    return st.get(W + "val") if st is not None else ""


def outline_of(p):
    ppr = p.find(W + "pPr")
    if ppr is None:
        return None
    ol = ppr.find(W + "outlineLvl")
    return int(ol.get(W + "val")) + 1 if ol is not None else None


def indent_of(p):
    ppr = p.find(W + "pPr")
    if ppr is None:
        return 0
    ind = ppr.find(W + "ind")
    if ind is None:
        return 0
    try:
        return max(0, int(ind.get(W + "left") or ind.get(W + "start") or 0) // 360)
    except (TypeError, ValueError):
        return 0


# --------------------------------------------------------- deteccion de titulo
def looks_titlish(rest):
    """El resto tras la numeracion debe parecer un rotulo, no una frase."""
    return rest and len(rest) <= 85 and len(rest.split()) <= 14


def heading_level(p, txt):
    """(nivel, fuerte) o None. 'fuerte' distingue un titulo de seccion real de
    un simple parrafo destacado, que en la portada abunda."""
    if not txt or len(txt) > 110:
        return None

    sid = style_of(p)
    if sid in style_level:
        return min(style_level[sid], 6), True
    # outlineLvl suelto no sirve de pista: en el pliego aparece sobre parrafos
    # de texto corriente, asi que solo se atiende al estilo real de titulo

    bold = is_bold(p)
    upper = txt == txt.upper() and any(c.isalpha() for c in txt)
    num = numbering_of(p)

    if PAT_CHAP.match(txt):
        return 1, True
    if PAT_ANNEX.match(txt) and (bold or upper):
        return 1, True
    m = PAT_ROMAN.match(txt)
    if m and (bold or upper) and looks_titlish(m.group(2)):
        return 1, True
    m = PAT_DEC.match(txt)
    if m and (bold or upper) and looks_titlish(m.group(2)):
        return min(m.group(1).count(".") + 2, 6), True
    # item de lista numerada en mayusculas: asi rotula sus apartados el pliego
    if num and num[0] != "bullet" and upper and 3 < len(txt) < 90:
        return min(num[1] + 2, 6), True
    # y en el capitulo tecnico los rotula igual pero sin mayusculas: item
    # decimal de primer nivel, corto y sin puntuacion de cierre
    if (num and num[0] == "decimal" and num[1] == 0 and 8 < len(txt) < 60
            and len(txt.split()) >= 2 and txt[-1] not in ":.;,"):
        return 2, True
    # rotulo suelto: corto, en mayusculas y en negrita
    if bold and upper and 3 < len(txt) < 90 and not txt.endswith("."):
        return 2, False
    # el capitulo tecnico se articula con rotulos en negrita terminados en dos
    # puntos ("Almacenamiento:", "KaaS:", "SLA minimos:"): son sus apartados
    if (bold and not num and 8 < len(txt) < 75 and not txt.endswith(".")
            and len(txt.split()) <= 10):
        return 3, False
    return None


# ------------------------------------------------------------------- recorrido
def cell_text(tc):
    # iter y no findall: estos pliegos anidan tablas dentro de las celdas y su
    # texto tambien es contenido del documento
    out = []
    for p in tc.iter(W + "p"):
        t = para_text(p)
        if t:
            out.append(t)
    return norm(" ".join(out))


def read_table(tbl):
    rows = []
    for tr in tbl.findall(W + "tr"):
        row = [cell_text(tc) for tc in tr.findall(W + "tc")]
        if row:
            rows.append(row)
    if not rows or not any(any(c for c in r) for r in rows):
        return None
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header = False
    first = tbl.find(W + "tr")
    if first is not None:
        cells = first.findall(W + "tc")
        bolds = 0
        for tc in cells:
            ps = tc.findall(W + "p")
            if ps and any(is_bold(p) and para_text(p) for p in ps):
                bolds += 1
        header = bool(cells) and bolds >= max(1, len(cells) // 2)
    return {"type": "table", "rows": rows, "header": header}


def para_images(p):
    out = []
    for blip in p.iter(A + "blip"):
        rid = blip.get(R + "embed")
        if not rid or rid not in rels:
            continue
        got = save_image(rels[rid])
        if got:
            fn, w, h = got
            out.append({"type": "figure", "src": fn, "w": w, "h": h})
    return out


body = ET.fromstring(z.read("word/document.xml")).find(W + "body")

flat = []          # bloques en orden
prev = None        # ultimo parrafo emitido, para fusionar codigo contiguo
started = False    # ya se vio el primer titulo de seccion real

def is_layout_table(tbl):
    """Tabla de una sola columna: el pliego la usa para encajonar capitulos
    enteros, asi que su contenido es cuerpo del documento, no una tabla."""
    trs = tbl.findall(W + "tr")
    return bool(trs) and all(len(tr.findall(W + "tc")) == 1 for tr in trs)


def walk(container):
    global prev, started

    for child in container:
        tag = child.tag

        if tag == W + "tbl":
            if is_layout_table(child):
                for tr in child.findall(W + "tr"):
                    for tc in tr.findall(W + "tc"):
                        walk(tc)
                continue
            for im in para_images(child):   # las figuras tambien viven en celdas
                flat.append(im)
            t = read_table(child)
            if t:
                flat.append(t)
            prev = None
            continue

        if tag != W + "p":
            continue

        handle_para(child)


def handle_para(p):
    global prev, started

    txt = para_text(p)
    imgs = para_images(p)

    for im in imgs:
        flat.append(im)
        prev = None

    if not txt:
        return

    got = heading_level(p, txt)
    if got:
        lvl, strong = got
        # hasta el primer titulo solido todo es portada: en ella cada linea va
        # centrada y en negrita, y tomarlas por secciones parte el documento
        if strong:
            started = True
        if started:
            flat.append({"type": "heading", "text": txt, "toc": True, "level": lvl,
                         "size": font_size(p)})
            prev = None
            return

    num = numbering_of(p)
    mono = is_mono(p)

    if mono:
        if prev is not None and prev["type"] == "code":
            prev["text"] += "\n" + txt
            return
        b = {"type": "code", "text": txt}
    elif num:
        fmt, il = num
        b = {"type": "bullet", "text": txt, "indent": il + 1}
        if fmt != "bullet":
            b["marker"] = "1."
    else:
        b = {"type": "para", "text": txt, "indent": indent_of(p)}

    flat.append(b)
    prev = b


walk(body)

# ------------------------------------------------- pies "Figura N" / "Tabla N"
CAP = re.compile(r"^(Figura|Figure|Tabla|Table|Fig\.|Cuadro)\s*\d+\s*[-–.:]", re.I)
keep = []
for i, b in enumerate(flat):
    if b["type"] in ("para", "bullet") and CAP.match(b["text"]) and len(b["text"]) < 220:
        target = None
        for prev_b in reversed(keep[-3:]):
            if prev_b["type"] in ("figure", "table"):
                target = prev_b
                break
        if target is None:
            for nxt in flat[i + 1:i + 3]:
                if nxt["type"] in ("figure", "table"):
                    target = nxt
                    break
        if target is not None and "caption" not in target:
            target["caption"] = b["text"]
            continue
    keep.append(b)
flat = keep

# ---------------------------------------------------- titulos -> arbol/secciones
FRONT = {"level": 0, "num": "0", "title": "Portada y preliminares", "blocks": []}
sections = [FRONT]
cur = FRONT
counters = [0] * 7

for b in flat:
    if b["type"] == "heading" and b.get("toc"):
        lvl = b.pop("level")
        b.pop("toc", None)
        # el .docx numera de forma irregular (romanos, decimales y automaticos
        # mezclados): la ruta se genera aqui y la etiqueta original se conserva
        # dentro del titulo, que es lo que el lector reconoce
        if lvl > 1 and counters[0] == 0:
            lvl = 1
        counters[lvl - 1] += 1
        for k in range(lvl, 7):
            counters[k] = 0
        num = ".".join(str(counters[k]) for k in range(lvl))
        cur = {"level": lvl, "num": num, "title": b["text"], "blocks": []}
        sections.append(cur)
        continue
    cur["blocks"].append(b)

# --- el indice impreso reaparece luego como capitulos reales: sobra aqui
TOCWORD = re.compile(r"^(CONTENIDO|[IÍ]NDICE|TABLA DE CONTENIDO|TABLE OF CONTENTS)\b", re.I)


def key(t):
    return re.sub(r"[^0-9A-Za-zÁÉÍÓÚÜÑ]+", "", t.upper())


def has_kids(i):
    lvl = sections[i]["level"]
    return i + 1 < len(sections) and sections[i + 1]["level"] > lvl


keep_secs = []
for i, s in enumerate(sections):
    if s["level"] > 0 and not s["blocks"] and not has_kids(i):
        later = {key(o["title"]) for o in sections[i + 1:]}
        if TOCWORD.match(s["title"]) or key(s["title"]) in later:
            continue
    keep_secs.append(s)
sections = keep_secs

if sections and sections[0]["num"] == "0" and not sections[0]["blocks"]:
    sections.pop(0)

# ------------------------------------------------------------------ ids / stats
seen = {}
for s in sections:
    base = "portada" if s["num"] == "0" else "s" + re.sub(r"[^0-9]+", "-", s["num"]).strip("-")
    n = seen.get(base, 0)
    seen[base] = n + 1
    s["id"] = base if n == 0 else "%s-%d" % (base, n + 1)
    s["chars"] = sum(len(b.get("text", "")) for b in s["blocks"])
    s["figures"] = sum(1 for b in s["blocks"] if b["type"] == "figure")
    s["tables"] = sum(1 for b in s["blocks"] if b["type"] == "table")

# paginas: Word guarda el recuento de la ultima vez que se guardo el archivo
pages = 0
title = DOC_ID
try:
    app = ET.fromstring(z.read("docProps/app.xml"))
    el = app.find(EP + "Pages")
    if el is not None and (el.text or "").isdigit():
        pages = int(el.text)
except KeyError:
    pass
try:
    core = ET.fromstring(z.read("docProps/core.xml"))
    for t in core.iter():
        if t.tag.endswith("}title") and (t.text or "").strip():
            title = t.text.strip()
            break
except KeyError:
    pass

out = {
    "doc_id": DOC_ID,
    "source_pdf": os.path.basename(DOCX),
    "title": title,
    "pages": pages,
    "sections": sections,
}
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("secciones:", len(sections))
print("imagenes guardadas:", len(saved))
print("tablas:", sum(s["tables"] for s in sections))
print("caracteres de texto:", sum(s["chars"] for s in sections))
