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
├─ *.pdf                                   documentos originales (sin modificar)
├─ tools/
│  ├─ extract.py                           PDF → JSON estructurado + figuras PNG
│  └─ build_site.py                        JSON + resúmenes → sitio HTML estático
└─ web/
   ├─ index.html                           nivel 1
   ├─ assets/css/style.css, assets/js/app.js
   ├─ data/
   │  ├─ <doc>.json                        contenido extraído del PDF
   │  └─ <doc>.summaries.json              resúmenes escritos a mano (editable)
   └─ docs/<doc>/
      ├─ index.html, s*.html               niveles 2, 3 y 4
      └─ img/                              figuras extraídas del PDF
```

## Estado

Los tres documentos están procesados.

| Documento | Papel | Páginas | Secciones | Figuras | Tablas |
|---|---|---:|---:|---:|---:|
| D1 — Centre Specification and Performance Requirements (v1.4) | Qué debe cumplir el Centro | 42 | 73 | 11 | 13 |
| D2 — System Architecture Description (v1.3) | Cómo está construida la plataforma | 83 | 125 | 21 | 5 |
| D3 — Interface Control Document (v1.3) | Cómo se integra con ella desde fuera | 35 | 63 | 5 | 4 |

Los resúmenes están en español; el contenido de los documentos se conserva en
su inglés original.

## Regenerar

Requiere Python 3 con PyMuPDF (`pip install PyMuPDF`).

```bash
python tools/extract.py "<archivo>.pdf" web/data/<doc>.json web/docs/<doc>/img <doc>
python tools/build_site.py
```

Para añadir un documento nuevo: ejecuta `extract.py`, escribe su archivo
`web/data/<doc>.summaries.json` con los resúmenes, marca `"ready": True` en la
lista `CATALOG` de `tools/build_site.py` y vuelve a ejecutar `build_site.py`.
`build_site.py` no toca los PDF originales ni los resúmenes: solo regenera el HTML.
