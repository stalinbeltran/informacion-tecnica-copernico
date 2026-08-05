# Información Técnica CopernicusLAC

Vista HTML navegable por niveles de la documentación técnica del proyecto
*CopernicusLAC Infrastructure Support* (Terradue / ESA).

**Punto de entrada:** abre [web/index.html](web/index.html) en el navegador
(funciona con doble clic, sin servidor).

## Cómo se navega

| Nivel | Página | Qué muestra |
|---|---|---|
| 1 | `web/index.html` | Los documentos del proyecto: nombre y resumen de cada uno |
| 2 | `web/docs/<doc>/index.html` | Los capítulos del documento, cada uno resumido, más buscador |
| 3 | `web/docs/<doc>/sN.html` | Los apartados del capítulo, resumidos |
| 4 | `web/docs/<doc>/sN-M[-K].html` | El contenido íntegro: texto, figuras, tablas y código |

Cada página lleva migas de pan, navegación anterior/siguiente y métricas
(páginas del PDF, número de figuras y tablas) que anticipan la profundidad de
lo que hay debajo. El botón ◐ de la barra superior alterna tema claro/oscuro.

### Siglas con definición al vuelo

Las siglas aparecen subrayadas con puntos en el texto; al pasar el ratón (o al
tocarlas, o al llegar a ellas con el tabulador) muestran su significado sin
salir de la página. El glosario se construye automáticamente fusionando las
tablas de acrónimos de los tres documentos, de modo que una sigla definida solo
en D2 también se explica al leer D1 o D3.

Se marcan tanto en el texto de los documentos como en los resúmenes en español
(portada, cabeceras de página y tarjetas de navegación). Dentro de una tarjeta
el globo aparece al pasar el ratón pero el clic sigue navegando, para no romper
el enlace.

No se marcan siglas dentro de los bloques de código ni en las propias tablas de
acrónimos. Si el JavaScript no se ejecuta, el navegador muestra igualmente el
tooltip nativo del atributo `title`.

## Estructura del proyecto

```
.
├─ *.pdf, *.docx, *.doc                    documentos originales (sin modificar)
├─ tools/
│  ├─ extract.py                           PDF  → JSON estructurado + figuras
│  ├─ extract_docx.py                      DOCX → el mismo JSON + imágenes
│  ├─ convert_doc.ps1                      .doc heredado → .docx (usa Word)
│  └─ build_site.py                        JSON + resúmenes → sitio HTML estático
└─ web/
   ├─ index.html                           nivel 1
   ├─ assets/css/style.css, assets/js/app.js
   ├─ data/
   │  ├─ <doc>.json                        contenido extraído del original
   │  └─ <doc>.summaries.json              resúmenes escritos a mano (editable)
   └─ docs/<doc>/
      ├─ index.html, s*.html               niveles 2, 3 y 4
      └─ img/                              figuras extraídas del original
```

Los dos extractores emiten **el mismo esquema JSON**, de modo que `build_site.py`
no distingue el formato de origen.

## Estado

Los seis documentos están procesados, en dos familias.

### Documentación técnica de la plataforma (Terradue / ESA)

| Documento | Papel | Páginas | Secciones | Figuras | Tablas |
|---|---|---:|---:|---:|---:|
| D1 — Centre Specification and Performance Requirements (v1.4) | Qué debe cumplir el Centro | 42 | 73 | 11 | 13 |
| D2 — System Architecture Description (v1.3) | Cómo está construida la plataforma | 83 | 125 | 21 | 5 |
| D3 — Interface Control Document (v1.3) | Cómo se integra con ella desde fuera | 35 | 63 | 5 | 4 |

### Documentos del encargo y del puesto (AIG Panamá)

| Documento | Papel | Secciones | Figuras | Tablas |
|---|---|---:|---:|---:|
| TDR — Administrador del Middleware | Qué se contrata y qué se espera del puesto | 13 | 0 | 1 |
| PLIEGO — Servicio en la nube (IaaS, KaaS, DBaaS) | Qué contrata Panamá al proveedor de infraestructura | 92 | 4 | 11 |
| PERFIL — Comparación de perfil y definición del rol | Qué separa el alcance contratado de lo que pide ESA | 16 | 0 | 1 |

Los documentos Word no anuncian número de páginas: el formato no fija una
paginación, así que en su lugar se muestran secciones, figuras y tablas.

Los resúmenes están en español; el texto de cada documento conserva su idioma
original.

## Regenerar

Requiere Python 3 con PyMuPDF (`pip install PyMuPDF`) para los PDF. La
extracción de `.docx` no necesita dependencias externas.

```bash
# PDF
python tools/extract.py "<archivo>.pdf" web/data/<doc>.json web/docs/<doc>/img <doc>

# DOCX
python tools/extract_docx.py "<archivo>.docx" web/data/<doc>.json web/docs/<doc>/img <doc>

# .doc heredado: convertir primero (requiere Word instalado)
powershell -File tools/convert_doc.ps1 "<archivo>.doc"

python tools/build_site.py
```

Para añadir un documento nuevo: ejecuta el extractor que corresponda, escribe su
archivo `web/data/<doc>.summaries.json` con los resúmenes, añádelo a la lista
`CATALOG` de `tools/build_site.py` con `"ready": True` —indicando su `group`
(`esa` o `aig`) y su `kind` (`pdf` o `word`)— y vuelve a ejecutar
`build_site.py`, que no toca los originales ni los resúmenes: solo regenera el
HTML.

### Sobre la extracción de Word

Un `.docx` no trae índice ni paginación fiables, así que el árbol de secciones
se deduce de los títulos. Estos documentos apenas usan estilos de título, por lo
que `extract_docx.py` combina varias señales: estilo real de encabezado,
patrones de numeración (`CAPÍTULO`, romanos, decimales, `ANEXO`), ítems de lista
numerada en mayúsculas y rótulos cortos en negrita. Además desenvuelve las
tablas de una sola columna, que en el pliego encajonan capítulos enteros, y
descarta el índice impreso. El atributo `outlineLvl` se ignora a propósito:
aparece aplicado sobre texto corriente y no sirve como pista.
