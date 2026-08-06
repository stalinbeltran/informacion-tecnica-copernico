# Titiler + COG + WMTS/XYZ — la visualización

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 3 — lo tocas al operar la visualización
**Competencia de la matriz:** 19

---

## 1. Qué es, aquí

Titiler es el servicio que convierte rasters en teselas de mapa **al vuelo**, sin
preprocesar. D2 §5.5:

> *"Titiler is a **dynamic stateless tiling server**… optimised for cloud environments,
> especially cloud storage solutions like S3… With Titiler, platforms can effortlessly
> generate tiles from large geospatial raster datasets **directly from cloud storage,
> without the need to download or process the entire file**. Titiler capitalises on the
> innate advantages of CoG, where **partial data reads** can be performed, meaning that only
> the necessary portions of the data relevant to a user's viewport are processed."*

La cadena entera es:

```
COG en S3  ──(lectura parcial por rangos)──▶  Titiler  ──(PNG)──▶  Leaflet/OpenLayers  ──▶  el usuario
     ▲                                                                     ▲
     └── el asset del STAC Item                        el link rel:"xyz" del STAC Item ─┘
```

Y la pieza que lo une es el **STAC Item**: sus assets apuntan al COG, y sus links `rel: "xyz"`
contienen la plantilla de teselas ya parametrizada. Sin esos links, el portal no sabe cómo
pintar el producto.

Titiler forma parte del **componente 2** (Data Discovery and Access) —
[05-stac-pgstac-stac-fastapi.md](05-stac-pgstac-stac-fastapi.md).

---

## 2. La frontera

Tuyo. *Platform Domains Support → catalog → Not covered*. El proveedor entrega S3 y el
clúster; que un mapa se pinte o no es asunto del Middleware.

---

## 3. Qué debes saber

### Nivel imprescindible — COG

- Qué es un **Cloud-Optimized GeoTIFF**: un GeoTIFF con estructura interna (*tiling* interno
  y *overviews*) y un layout que permite leer **solo** el trozo que necesitas mediante
  peticiones HTTP con `Range`.
- Por qué eso importa aquí: el pliego especifica **lecturas parciales de 16 KB – 1 MB** sobre
  objetos de 100 MB – 1 GB. **El COG es la razón de que esa cifra sea así.**
- Cómo verificar que un GeoTIFF es realmente un COG:
  `rio cogeo validate archivo.tif` o `gdalinfo` mirando `Block` y `Overviews`.
- Cómo convertir: `rio cogeo create` o `gdal_translate -of COG`.
- Compresión (`DEFLATE`, `ZSTD`), *overviews*, tamaño de bloque, y su efecto en el
  rendimiento de las teselas.
- **Un COG mal formado no da error: da lentitud o un mapa en blanco.** Ése es el aprendizaje.

### Nivel imprescindible — las URLs de teselas

Ésta es la plantilla real de la plataforma (D3 §4.4 y §5.4.1), con sus parámetros:

```
<view-url>/collections/sentinel-s2-l1c-cogs/items/S2A_MSIL1C_20231122T102331_N0509_R065_T32TMR_20231122T122209
  /tiles/WebMercatorQuad/{z}/{x}/{y}@1x
  ?assets=red&assets=green&assets=blue
  &color_formula=Gamma RGB 1.5 Saturation 1 Sigmoidal RGB 10 0.3
  &rescale=1,6000&rescale=1,6000&rescale=1,6000
```

Descompuesta:

| Parte | Qué es |
|---|---|
| `WebMercatorQuad` | El TileMatrixSet (la cuadrícula estándar de mapas web) |
| `{z}/{x}/{y}` | Zoom, columna, fila. Se sustituyen por valores reales |
| `@1x` | Factor de escala (`@2x` para pantallas de alta densidad) |
| `assets=red&assets=green&assets=blue` | **Qué bandas** se combinan, en orden R-G-B |
| `color_formula` | Ajuste de color (gamma, saturación, sigmoidal) |
| `rescale=1,6000` | **Rango de valores** por banda. Uno por asset |

Ejemplo concreto de petición (D3 §5.4.2): `{z}=10`, `{x}=525`, `{y}=391`.

**Dos visualizaciones por producto** son lo normal: color verdadero
(`assets=red&assets=green&assets=blue`) y falso color
(`assets=nir&assets=green&assets=red`). Aparecen como dos links `rel: "xyz"` distintos, con
títulos distintos.

**Overview images** (D3 §5.3): un asset con `roles: ["overview"]` que apunta a un PNG ya
generado:
```
.../items/<item-id>/preview.png?assets=red&assets=green&assets=blue
  &color_formula=Gamma RGB 1.5 Saturation 1 Sigmoidal RGB 10 0.3
  &max_size=1024&resampling=cubic&rescale=1,7500&rescale=1,7500&rescale=1,7500
```

### Nivel operativo — las extensiones STAC de visualización

D2 §4.6 explica cómo la ingesta prepara la visualización. Dos extensiones:

**Rendering Extension** — define **cómo** se debe visualizar:
```json
"renders": {
  "trc": {
    "title": "True-colour composite",
    "assets": ["red", "green", "blue"],
    "resampling": "nearest",
    "rescale": [[0,5000],[0,5000],[0,5000]]
  },
  "civ": {
    "title": "Colour-infrared composite",
    "assets": ["red", "green", "nir"],
    "resampling": "nearest",
    "rescale": [[0,5000],[0,5000],[0,5000]]
  }
}
```

**Web Map Links Extension** — el resultado del ETL, los enlaces navegables:
```json
{
  "rel": "xyz",
  "href": "https://view.imagery.org?assets=red&assets=green&assets=blue&resampling=nearest&rescale=[0,5000]&rescale=[0,5000]&rescale=[0,5000]&",
  "type": "image/png",
  "title": "True-colour composite",
  "render": "trc"
}
```

**El proceso de enriquecimiento (D2 §4.6)** — importante para saber a quién reclamar cuando
falta la visualización:
- Si el item **ya** trae información de rendering y sus assets son COG → el ETL solo genera
  los Web Map Links.
- Si **no** los trae → el ETL genera nuevos COG y **añade** la información de rendering y los
  links.
- El item enriquecido y los assets nuevos se publican en el object storage y se registran en
  el catálogo.

Traducción operativa: **si un producto no se ve, puede que el problema esté en la ingesta,
no en Titiler.** Ver [07-argo-workflows.md](07-argo-workflows.md).

### Nivel avanzado

- Rendimiento: caché de teselas, CDN, y el efecto de los *overviews* del COG en los zooms
  bajos.
- Titiler leyendo directamente de S3: qué credenciales usa y qué pasa cuando caducan.
- Relación con el objetivo de **< 5 s de respuesta media** y **3.000 usuarios concurrentes**
  de D1.
- `TileJSON` y los endpoints de metadatos de Titiler.

---

## 4. Laboratorio

Parte del **Bloque 4/6**, apoyado en el catálogo y en MinIO.

1. **Consigue un COG real.** Una escena Sentinel-2 de un catálogo público.
2. **Verifícalo:** `rio cogeo validate`. Mira sus overviews con `gdalinfo`.
3. **Levanta Titiler** apuntando a tu MinIO del [bloque 5](06-s3-minio.md).
4. **Genera una tesela** manualmente: construye la URL con `{z}/{x}/{y}` reales y descárgala
   con `curl`. Ábrela.
5. **Compón color verdadero y falso color** cambiando el orden de `assets`.
6. **Juega con `rescale`.** Pon un rango absurdo (`0,10`) y observa el resultado saturado.
   Pon `0,60000` y observa la imagen negra. **Ahora entiendes la avería 13.**
7. **Enriquece un STAC Item**: añádele manualmente los `renders` y los links `rel: "xyz"`
   apuntando a tu Titiler. Cárgalo en el catálogo del [bloque 4](05-stac-pgstac-stac-fastapi.md).
8. **Píntalo en un mapa**: una página HTML mínima con Leaflet consumiendo esa plantilla XYZ.
   **Éste es el momento en que la plataforma "se ve".**
9. **Genera un overview PNG** con `max_size=1024` y compáralo con la tesela.

---

## 5. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| GeoTIFF normal (no COG) | Lentitud extrema; Titiler descarga el fichero entero |
| COG sin overviews | Los zooms bajos tardan mucho |
| `rescale` fuera de rango | **Mapa en blanco o negro. La avería 13** |
| `assets` con un nombre de banda inexistente | Error de Titiler; cómo se ve |
| Titiler sin credenciales de S3 | 403 al leer el asset; el mapa no carga |
| Item sin links `rel: "xyz"` | El portal no tiene qué pintar. **El fallo está en la ingesta** |
| Ingress mal configurado hacia Titiler | 502; ver [18](18-ingress-tls-cert-manager.md) |

---

## 6. Avería de producción que este bloque entrena

**Avería 13:** mapa en blanco — COG mal formado o `rescale` incorrecto.

---

## 7. Árbol de diagnóstico: "el mapa no carga"

En este orden. Cada paso descarta el anterior.

1. **¿El item tiene links de teselas?**
   `curl -s "$STAC/collections/$C/items/$I" | jq '.links[] | select(.rel=="xyz")'`
   Si no los tiene → **el problema está en la ingesta**, en el paso de enriquecimiento
   (D2 §4.6). No es Titiler.
2. **¿Titiler está vivo?** `kubectl get pods`, ¿responde su endpoint de salud?
3. **¿Titiler puede leer el bucket?** Sus logs mostrarán un 403 o un `NoSuchKey`.
   → [06-s3-minio.md](06-s3-minio.md).
4. **¿El COG es válido?** `rio cogeo validate`. ¿Tiene overviews?
5. **¿Los parámetros son correctos?** ¿`assets` nombra bandas que existen? ¿`rescale` está en
   el rango real de los datos? Compruébalo con las `raster:bands.statistics` del propio item:
   `jq '.assets.red["raster:bands"][0].statistics'`. **Ahí está el rango correcto.**
6. **¿Es el Ingress/TLS/CDN?** Prueba la misma URL desde dentro del clúster con
   `port-forward`. Si funciona dentro y no fuera → [18](18-ingress-tls-cert-manager.md).

---

## 8. Comandos de bolsillo

```bash
# ¿Es un COG de verdad?
rio cogeo validate escena.tif
gdalinfo escena.tif | grep -E 'Block|Overviews'

# Convertir a COG
rio cogeo create entrada.tif salida.tif --overview-level 5
gdal_translate -of COG entrada.tif salida.tif -co COMPRESS=DEFLATE

# Pedir una tesela a mano
curl -s -o tesela.png \
  "$TITILER/collections/$C/items/$I/tiles/WebMercatorQuad/10/525/391@1x?assets=red&assets=green&assets=blue&rescale=1,6000&rescale=1,6000&rescale=1,6000"

# ¿Tiene el item links de visualización?
curl -s "$STAC/collections/$C/items/$I" | jq '.links[] | select(.rel=="xyz") | {title, href}'

# ¿Cuál es el rango real de valores? (para acertar el rescale)
curl -s "$STAC/collections/$C/items/$I" \
  | jq '.assets | to_entries[] | {banda: .key, stats: .value["raster:bands"][0].statistics}'

# ¿Tiene overview?
curl -s "$STAC/collections/$C/items/$I" | jq '.assets | to_entries[]
  | select(.value.roles[]? == "overview") | .value.href'

# Logs de Titiler
kubectl logs -n <ns> -l app=titiler --tail=100
```

---

## 9. Criterio de dominio

- [ ] Verifico que un GeoTIFF es un COG válido y con overviews.
- [ ] Construyo una URL de tesela a mano y la descargo.
- [ ] Explico qué hacen `assets`, `color_formula` y `rescale`, y qué pasa si están mal.
- [ ] **Deduzco el `rescale` correcto de las `raster:bands.statistics` del item.**
- [ ] Distingo "falta el link de teselas" (ingesta) de "Titiler falla" (visualización).
- [ ] Diagnostico un mapa en blanco recorriendo el árbol del §7.
- [ ] Explico la Rendering Extension y la Web Map Links Extension y cómo las genera el ETL.
- [ ] Pinto un producto real en un mapa Leaflet a partir de su STAC Item.

---

## 10. Artefacto que produces

Sección de visualización en **`runbooks/`**: el árbol de diagnóstico del §7 y una página
Leaflet mínima de prueba que sirva para verificar de un vistazo si un producto se ve.

Esa página de prueba es más útil de lo que parece: convierte "el usuario dice que no ve el
mapa" en una comprobación de 30 segundos.

**Alimenta:** Producto 2 (runbooks), Producto 3 (validación de desempeño del servicio de
acceso — uno de los tres a los que D1 liga la disponibilidad).

---

## 11. Qué preguntar

**A ESA / Terradue:**
1. ¿Qué versión de Titiler está desplegada y qué endpoints expone?
2. ¿Titiler lee de S3 con credenciales propias o con URLs firmadas? ¿Cómo se rotan?
3. ¿Qué configuraciones de rendering están definidas por colección?
4. ¿Hay caché o CDN delante de Titiler? ¿Con qué política de invalidación?
5. ¿Qué hace la ingesta si un producto llega sin información de rendering — genera COG nuevos siempre?
6. ¿Qué TileMatrixSets están habilitados además de `WebMercatorQuad`?

---

## 12. Fuentes

**Documentos del proyecto:** D2 §5.5 (Visualisation Integration — Titiler en detalle),
**§4.6 (Metadata Enrichment for Visualization — Rendering y Web Map Links con los JSON de
ejemplo)**, §3.2.2 y §3.2.4 (Titiler en el stack de Data Discovery and Access), §5.3
(COG, S3 y lecturas parciales), §5.1 (extensión Web Map Links), §3.5.2 y §3.5.4 (clientes de
visualización, Leaflet/OpenLayers), §7.13 (Titiler). **D3 §5 completo** (§5.2 tipos de
visualización, §5.3 overview images con su URL de ejemplo, §5.4.1 tile visualisations,
§5.4.2 formato de petición de tesela), §4.4 (los links `rel:"xyz"` en el STAC Item real).
D1 §3.2.3. Pliego (lecturas parciales 16 KB–1 MB, latencia 100 ms).

**Documentación oficial:** `developmentseed.org/titiler`, `cogeo.org`,
`github.com/stac-extensions/render`, `github.com/stac-extensions/web-map-links`.

---

## 13. Bitácora / hallazgos

*(Configuraciones de rendering reales, rangos de rescale por colección, productos que no se
visualizan y por qué.)*
