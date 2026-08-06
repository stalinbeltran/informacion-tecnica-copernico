# STAC + PgSTAC + stac-fastapi — el catálogo

**Nivel exigido:** E — lo diseñas, lo optimizas y lo enseñas
**Prioridad:** 2 — alto y **desatendido**: el contrato del proveedor no lo cubre
**Competencia de la matriz:** 16

---

## 1. Qué es, aquí

El catálogo es el **componente 2 del Middleware** (Data Discovery and Access) y es la pieza
que convierte "hay datos en un bucket" en "un usuario encuentra el dato que necesita". Sin
catálogo no hay plataforma.

La pila, según D2 §3.2.4, tiene tres capas que debes distinguir con precisión:

| Capa | Qué es | Qué hace |
|---|---|---|
| **STAC** | El **estándar** (SpatioTemporal Asset Catalog) | Define cómo se describe un producto EO en JSON |
| **PgSTAC** | El **backend** sobre PostgreSQL/PostGIS | *"Stores all collection and item records as JSONB, allowing for any STAC custom fields to be stored and retrieved transparently"* |
| **stac-fastapi** | La **API** | *"The FastAPI interface validates requests and data sent to the PgSTAC backend"* |

Confundirlas es la causa de la mitad de los diagnósticos fallidos: un item rechazado por
stac-fastapi es un problema distinto de un item cargado en PgSTAC que no aparece en
búsqueda.

STAC aparece además en **todos** los demás flujos: la ingesta publica STAC Items
(D3 §3.2.3), el procesamiento usa STAC Catalogs como manifiesto de *stage-in*/*stage-out*
(D2 §5.3), la visualización se declara mediante extensiones STAC (D2 §4.6), y la descarga
segura se declara mediante la extensión Authentication (D2 §5.1).

**Es el hilo que atraviesa la plataforma entera.**

---

## 2. La frontera — por qué esto es tuyo entero

El análisis de perfil de ESA es explícito:

| Área | Alcance contratado | Perfil ESA | Cobertura |
|---|---|---|---|
| *Platform Domains Support (Copernicus)* | Not included (infrastructure only) | Ingestion, **catalog**, workflows, registry, workspace | **Not covered** |

El proveedor administra PostgreSQL como motor (HA, parches, respaldos). **No sabe qué es
PgSTAC, ni qué es un STAC Item, ni por qué una búsqueda espacial tarda 8 segundos.** Ese es
tu terreno exclusivo.

Tuyo: extensiones y perfil de metadatos, carga de colecciones e items, índices, consultas
CQL2, rendimiento del catálogo, diagnóstico de items ausentes, migraciones de PgSTAC.
Del proveedor: que PostgreSQL esté vivo, respaldado y con recursos.
Ver [19-postgresql-postgis.md](19-postgresql-postgis.md) para esa mitad.

---

## 3. Qué debes saber

### Nivel imprescindible — el modelo STAC

**Los tres objetos**
- **Item**: un producto EO concreto. Es un **GeoJSON Feature**. La unidad atómica.
- **Collection**: agregación de items, con extensión espacial y temporal del conjunto,
  licencia, keywords, proveedores.
- **Catalog**: agrupación navegable. En la plataforma se usa sobre todo como manifiesto de
  entrada/salida de los Application Packages.

**Campos obligatorios del Item** — el perfil mínimo de metadatos que D2 §4.5 fija en su
Tabla 1. Memorízalo: es lo que valida la ingesta.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string | Identificador único del item |
| `type` | string | `"Feature"` |
| `stac_version` | string | p. ej. `"1.0.0"` |
| `stac_extensions` | array de strings | Extensiones implementadas. **Debe incluir la extensión EO** |
| `geometry` | object | Huella espacial en formato GeoJSON Geometry |
| `bbox` | array de floats | `[min lon, min lat, max lon, max lat]` en WGS84 |
| `properties` | object | Propiedades descriptivas |
| `properties.datetime` | string | Fecha-hora de captura, formato date-time |
| `links` | array de Link | **Debe incluir** un `self` y un enlace a la colección padre |
| `assets` | object | Objetos asset con clave única |
| `assets.thumbnail` | asset | Imagen de vista previa |
| `assets.data` | asset | Fichero(s) de datos geoespaciales principales |
| `collection` | string | ID de la Collection a la que pertenece |

**Assets**: cada uno con `href`, `type` (media type), `roles` (`data`, `visual`,
`reflectance`, `overview`, `thumbnail`), y opcionalmente `auth:refs` para la descarga
firmada.

**Extensiones que usa esta plataforma** (las verás en `stac_extensions` de un item real):
```
sat, eo, raster, projection, processing, view, web-map-links, authentication
```
- `eo` → `eo:cloud_cover`, `eo:bands` (con `name`, `common_name`, `center_wavelength`,
  `solar_illumination`).
- `raster` → `raster:bands` con `statistics`, `histogram`, `spatial_resolution`.
- `projection` → `proj:epsg`.
- `sat` → `sat:orbit_state`, `sat:absolute_orbit`, `sat:relative_orbit`.
- `processing` → `processing:level`, `processing:lineage`.
- `render` (Rendering) → configuraciones de visualización. Ver [16-titiler-cog.md](16-titiler-cog.md).
- `web-map-links` → enlaces `rel: "xyz"` a teselas.
- `authentication` → `auth:schemes` y `auth:refs`. Ver [06-s3-minio.md](06-s3-minio.md).

### Nivel imprescindible — la API

Endpoints que debes conocer de memoria (D3 §4):

```
GET  /collections                                  # todas las colecciones
GET  /collections/{collection-id}                  # una colección
GET  /collections/{collection-id}/items            # GeoJSON FeatureCollection
GET  /collections/{collection-id}/items/{item-id}  # un GeoJSON Feature
GET  /collections/{collection-id}/queryables       # qué campos puedo filtrar
GET  /search                                       # filtros CQL2-TEXT en query string
POST /search                                       # filtros CQL2-JSON en el cuerpo
```

`queryables` es la que casi nadie usa y la que responde *"¿por qué mi filtro no funciona?"*:
te dice exactamente qué propiedades son filtrables en esa colección. D3 §4.2.3 la describe
como el mecanismo para obtener los criterios de filtro antes de construir la consulta.

**CQL2 — las dos formas.** D3 §4.3: ambas obtienen resultados equivalentes; POST permite
consultas más complejas.

CQL2-JSON (POST), filtro temporal:
```json
{
  "collections": ["sentinel-s2-l1c-cogs"],
  "filter-lang": "cql2-json",
  "filter": {
    "op": "T_INTERSECTS",
    "args": [
      { "property": "datetime" },
      { "interval": ["2023-11-22T00:00:00Z", "2023-11-23T00:00:00Z"] }
    ]
  }
}
```

CQL2-JSON, filtro espacial:
```json
{
  "collections": ["sentinel-s2-l1c-cogs"],
  "filter-lang": "cql2-json",
  "filter": {
    "op": "S_INTERSECTS",
    "args": [
      { "property": "geometry" },
      { "type": "Polygon",
        "coordinates": [[[7.8,45.2],[9.0,45.2],[9.0,45.8],[7.8,45.8],[7.8,45.2]]] }
    ]
  }
}
```

CQL2-JSON, filtro por propiedad:
```json
{
  "collections": ["sentinel-s2-l1c-cogs"],
  "filter-lang": "cql2-json",
  "filter": { "op": "<", "args": [ { "property": "eo:cloud_cover" }, 10 ] }
}
```

CQL2-JSON, combinación con `and`:
```json
{
  "collections": ["sentinel-s2-l1c-cogs"],
  "filter-lang": "cql2-json",
  "filter": {
    "op": "and",
    "args": [
      { "op": "T_INTERSECTS",
        "args": [ { "property": "datetime" },
                  { "interval": ["2023-11-22T00:00:00Z","2023-11-23T00:00:00Z"] } ] },
      { "op": "<", "args": [ { "property": "eo:cloud_cover" }, 10 ] }
    ]
  }
}
```

CQL2-TEXT (GET), los mismos filtros sin codificar la URL:
```
filter-lang=cql2-text&collections=sentinel-s2-l1c-cogs&filter=datetime>='2023-11-22T00:00:00Z' and datetime<'2023-11-23T00:00:00Z'
filter-lang=cql2-text&collections=sentinel-s2-l1c-cogs&filter=S_INTERSECTS(geometry, POLYGON((7.8 45.2,9.0 45.2,9.0 45.8,7.8 45.8,7.8 45.2)))
filter-lang=cql2-text&collections=sentinel-s2-l1c-cogs&filter=eo:cloud_cover<10
```

La forma sencilla, sin CQL2 (D2 §5.2), también funciona y es la que verás en scripts:
```
GET /search?datetime=2020-01-01T00:00:00Z/2020-12-31T23:59:59Z
GET /search?bbox=-0.15,51.4,-0.1,51.6
GET /search?collections=[sentinel-2]
```

### Nivel operativo — PgSTAC

- **Qué es**: esquema de PostgreSQL que guarda `collections` e `items` como **JSONB**, con
  funciones y particionado propios. No es "una tabla con una columna JSON": tiene su propia
  lógica de particionado temporal y sus índices.
- **`pypgstac`**: la herramienta de línea de comandos. Dos operaciones que debes dominar:
  - `pypgstac migrate` — aplica las migraciones del esquema. **Apuntar stac-fastapi a una
    base sin migrar es un error clásico y su síntoma es confuso.**
  - `pypgstac load collections|items <archivo.ndjson>` con modos `insert`, `upsert`,
    `ignore`. El formato es **NDJSON** (un JSON por línea), no un array.
- **Índices**: el espacial (GiST sobre la geometría) y el temporal. Sin ellos una búsqueda
  espacial pasa de milisegundos a segundos. Medirlo tú mismo es parte del laboratorio.
- **Particionado**: PgSTAC particiona items por rango temporal. Entender esto explica por
  qué una consulta sin filtro de fecha es cara.
- Versión de PgSTAC vs versión de stac-fastapi: **deben ser compatibles**. Es una de las
  cosas que debes preguntar a ESA (§11).

### Nivel operativo — stac-fastapi

- Configuración: variables de conexión a PostgreSQL, pool de conexiones (lectura y
  escritura suelen ir separadas), `root_path` cuando está detrás de un Ingress.
- Validación: qué rechaza la API y con qué código. Un item sin `datetime` o con `bbox`
  inválido no llega a PgSTAC.
- Paginación: `limit`, `token`/`next`, y por qué una respuesta "incompleta" a veces es solo
  paginación.
- Documentación automática en `/docs` (OpenAPI) — úsala como referencia viva del despliegue
  real.
- `/conformance`: qué clases de conformidad declara la instancia. Te dice si el Filter
  Extension está activo.

### Nivel avanzado

- Diseño de colecciones: cuándo separar en colecciones distintas y cuándo usar propiedades.
- Rendimiento: `EXPLAIN ANALYZE` sobre una consulta de PgSTAC, índices sobre propiedades
  JSONB usadas frecuentemente en filtros.
- Backpressure del catálogo cuando la ingesta publica a alta tasa — el compromiso es
  **≥ 0,350 TB/h** con picos de **3,5 TB/h**, y cada producto genera al menos un POST de item.
- El KPI de **completitud de la oferta de datos** (% de solicitudes de items exitosas) se
  mide aquí. Instrumentarlo es tuyo.
- Reprocesamiento: qué pasa con los items cuando una ingesta se rehace. Pregunta abierta
  para ESA.

---

## 4. Datos de la plataforma que debes tener a mano

**Colección de ejemplo real** (D3 §4.2.1): `sentinel-s2-l1c-cogs`, *"Sentinel Level-1C COGs"*,
extensión espacial global `[-180,-90,180,90]`, licencia `proprietary`.

**Item de ejemplo real** (D3 §4.4): `S2A_MSIL1C_20231122T102331_N0509_R065_T32TMR_20231122T122209`.
Estructura clave:

```jsonc
{
  "id": "S2A_MSIL1C_...",
  "type": "Feature",
  "collection": "sentinel-s2-l1c-cogs",
  "links": [
    { "rel": "collection", ... }, { "rel": "parent", ... },
    { "rel": "root", ... },       { "rel": "self", ... },
    { "rel": "xyz", "href": ".../tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=red&assets=green&assets=blue&color_formula=...&rescale=1,6000",
      "type": "image/png", "title": "True colour composite visualized through a XYZ" }
  ],
  "assets": {
    "nir": {
      "href": "s3://<storage-base>/sentinel-2-l1c-ingestion-xvv8c/S2A_.../r-nir.tif",
      "type": "image/tiff; application=geotiff; profile=cloud-optimized",
      "roles": ["data", "visual", "reflectance"],
      "eo:bands": [{ "name": "nir", "common_name": "nir", "center_wavelength": 0.8328 }],
      "raster:bands": [{ "statistics": {...}, "spatial_resolution": 10.0 }],
      "auth:refs": ["signed_url_auth"]        // ← cómo se descarga
    }
  },
  "geometry": { "type": "Polygon", "coordinates": [[...]] },
  "bbox": [7.7069, 45.0581, 9.1261, 46.0535],
  "properties": {
    "datetime": "2023-11-22T10:23:31.024000Z",
    "gsd": 10.0, "platform": "sentinel-2a", "proj:epsg": 32632,
    "eo:cloud_cover": 0.243363492490071,
    "processing:level": "L1C", "sat:relative_orbit": 65,
    "auth:schemes": { "signed_url_auth": { "type": "signedUrl", ... } }
  },
  "stac_extensions": ["...sat...", "...eo...", "...raster...", "...projection...",
                      "...processing...", "...view...", "...web-map-links...",
                      "...authentication..."],
  "stac_version": "1.0.0"
}
```

Lo que D3 §4.4 subraya de este item, y que debes poder señalar en cualquier item que veas:
- **Links** apuntan a recursos relacionados (colección, catálogo) **y a un servidor de teselas**.
- **Assets** son los recursos descargables; pueden llevar información de autenticación.
- **Properties** son los campos filtrables (específicos de cada colección).
- Entre las properties están los **esquemas de autenticación** a los que los assets se refieren.

**Ruta completa que debes saber recorrer:**
```
Evento → Argo Workflow de ingesta → validación → POST del STAC Item a stac-fastapi
       → stac-fastapi valida → PgSTAC lo guarda como JSONB
       → GET /search lo devuelve → el portal lo pinta
```
Si el item no aparece, el fallo está en uno de esos saltos. Saber en cuál mirar es
exactamente el criterio de dominio de este bloque.

---

## 5. Laboratorio

**Bloque 4 de la ruta de práctica — 10 horas.**

1. **Levanta PostgreSQL con PostGIS y PgSTAC.** Imagen `pgstac` o base limpia + migraciones
   con `pypgstac migrate`.
2. **Levanta `stac-fastapi-pgstac`** apuntando a esa base. Comprueba `/`, `/conformance`
   y `/docs`.
3. **Carga datos reales.** Una colección y varios items de un catálogo público (Earth Search
   o Planetary Computer) con `pypgstac load`. Con **un solo item bien cargado** ya puedes
   practicar todo el bloque; no necesitas volumen, necesitas fidelidad.
4. **Consulta**, en este orden:
   - `GET /collections` — ¿está tu colección?
   - `GET /collections/{id}/queryables` — ¿qué puedes filtrar?
   - `GET /search` con CQL2-TEXT: temporal, espacial, por `eo:cloud_cover`.
   - `POST /search` con CQL2-JSON: los mismos tres, y la combinación con `and`.
5. **Mide.** ¿Cuánto tarda una búsqueda espacial **sin** índice? Crea el índice espacial y
   compara. Anota los dos números en la bitácora — es tu primera medición de rendimiento del
   catálogo, y ese tipo de evidencia es lo que va en el Producto 3.
6. **Recorre la ruta completa.** Publica un item vía `POST` a la API (no por `pypgstac`) y
   compruébalo en `GET /search`. Esto simula lo que hace el workflow de ingesta.

---

## 6. Sabotajes obligatorios

| Sabotaje | Síntoma que aprendes a reconocer |
|---|---|
| Item sin `datetime` | Rechazo en validación de stac-fastapi, antes de tocar la base |
| Item con `bbox` inválido (orden de coordenadas cambiado) | Se carga pero no aparece en búsquedas espaciales |
| Item con `collection` que no existe | Error de clave foránea o item huérfano |
| API apuntando a una base **sin migrar** | Error confuso de tabla/función inexistente — el clásico |
| Pool de conexiones mal dimensionado | `too many clients already`; catálogo lento bajo carga |
| Índice espacial ausente | Búsqueda espacial de milisegundos a segundos |
| Consulta sin filtro temporal sobre una tabla particionada | Escaneo de todas las particiones |
| `stac_extensions` sin la extensión EO declarada | El item se carga, pero `eo:cloud_cover` no filtra |

---

## 7. Averías de producción que este bloque entrena

- **Avería 10:** item ingerido que no aparece en búsqueda — item sin `datetime` o colección incorrecta.
- **Avería 11:** catálogo lento — índice espacial ausente o pool agotado.
- **Avería 7:** 401 en la STAC API — token expirado o audiencia incorrecta (ver [09-keycloak.md](09-keycloak.md)).

---

## 8. Árbol de diagnóstico: "el item no aparece"

Sigue el orden. Cada paso descarta el anterior.

1. **¿El workflow terminó bien?** `argo get <workflow>`, exit code. Si falló, el item nunca
   se posteó → [07-argo-workflows.md](07-argo-workflows.md).
2. **¿El POST llegó a la API?** Logs de `stac-fastapi`. ¿Hay un 4xx? Entonces el item es
   inválido: mira **cuál** campo.
3. **¿Está en PgSTAC?** Consulta directa a la base:
   `SELECT id FROM pgstac.items WHERE id = '...';`
   Si está en la base pero no en `/search`, el problema es de consulta, no de carga.
4. **¿La colección es la correcta?** `SELECT collection FROM pgstac.items WHERE id='...'`.
   Un item en la colección equivocada es invisible para quien filtra por colección.
5. **¿El filtro es el correcto?** Consulta `queryables` de esa colección y comprueba que la
   propiedad que filtras existe **y está indexada como filtrable**.
6. **¿El `datetime` cae dentro del intervalo?** Zona horaria y sufijo `Z`.
7. **¿La geometría intersecta de verdad?** Verifica el `bbox` con PostGIS:
   `SELECT ST_AsText(geometry) FROM pgstac.items WHERE id='...'`.
8. **¿Es paginación?** ¿Estás mirando solo la primera página?

---

## 9. Comandos y consultas de bolsillo

```bash
# Explorar el catálogo
curl -s "$STAC/collections" | jq -r '.collections[].id'
curl -s "$STAC/collections/sentinel-s2-l1c-cogs/queryables" | jq '.properties | keys'
curl -s "$STAC/search?limit=1" | jq '.features[0] | {id, collection, datetime: .properties.datetime}'

# Búsqueda con CQL2-JSON
curl -s -X POST "$STAC/search" -H 'Content-Type: application/json' -d '{
  "collections": ["sentinel-s2-l1c-cogs"],
  "filter-lang": "cql2-json",
  "filter": {"op":"<","args":[{"property":"eo:cloud_cover"},10]}
}' | jq '.features | length'

# Carga
pypgstac migrate --dsn "$PGDSN"
pypgstac load collections coleccion.ndjson --dsn "$PGDSN" --method upsert
pypgstac load items items.ndjson --dsn "$PGDSN" --method upsert
```

```sql
-- ¿Está el item?
SELECT id, collection FROM pgstac.items WHERE id = 'S2A_MSIL1C_...';

-- ¿Cuántos items por colección?
SELECT collection, count(*) FROM pgstac.items GROUP BY collection;

-- ¿Por qué es lenta esta consulta?
EXPLAIN ANALYZE SELECT * FROM pgstac.items
  WHERE ST_Intersects(geometry, ST_GeomFromText('POLYGON((...))', 4326));

-- Índices existentes
SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'pgstac';
```

---

## 10. Criterio de dominio

- [ ] Recito los campos obligatorios de un STAC Item sin mirar.
- [ ] Cargo colecciones e items con `pypgstac` y sé la diferencia entre `insert` y `upsert`.
- [ ] Escribo el mismo filtro en CQL2-TEXT y en CQL2-JSON.
- [ ] Uso `queryables` antes de escribir un filtro, no después de que falle.
- [ ] Diagnostico por qué un item ingerido no aparece, siguiendo el árbol del §8.
- [ ] **Explico la ruta completa desde "el workflow posteó el item" hasta "el usuario lo ve en el portal", y sé dónde mirar en cada salto.**
- [ ] Mido el efecto de un índice espacial y lo documento con números.
- [ ] Distingo un fallo de stac-fastapi (validación) de uno de PgSTAC (carga) de uno de consulta.

---

## 11. Artefactos que produces

1. **`queries/consultas-catalogo.md`** — colección de consultas CQL2 comentadas, en ambas
   formas, con el caso de uso de cada una.
2. **Nota: "por qué un item ingerido puede no aparecer en búsqueda"** — el árbol del §8
   convertido en runbook.
3. **Medición del efecto de los índices** — la evidencia de rendimiento del catálogo.

**Alimentan:** Producto 2 (arquitectura lógica y runbooks iniciales), Producto 3
(estabilización técnica: análisis de comportamiento y validación de desempeño de servicios
críticos — el catálogo es uno de los tres), Producto 7 (optimización).

---

## 12. Qué preguntar

**A ESA / Terradue:**
1. ¿Qué versión de PgSTAC y de stac-fastapi componen el release desplegado? ¿Cómo se anuncian las migraciones de esquema?
2. ¿Cuál es el perfil de metadatos vigente por colección? ¿Hay extensiones propias además de las estándar?
3. ¿Qué colecciones existen o están previstas, y quién decide crear una nueva?
4. **¿Cuál es el procedimiento de reprocesamiento cuando una ingesta falla parcialmente?** ¿Qué pasa con los items ya publicados?
5. ¿Hay un conjunto de consultas de referencia para validar la salud del catálogo?
6. ¿Quién es responsable de los índices y del particionado: viene fijado por el chart o lo ajusto yo?

**Al proveedor:** ver [19-postgresql-postgis.md](19-postgresql-postgis.md).

---

## 13. Fuentes

**Documentos del proyecto:** D2 §3.2 (Data Discovery and Access, completo), §4.4 (validación
de contenido), §4.5 (perfil mínimo de metadatos, Tabla 1), §4.6 (enriquecimiento para
visualización), §5.1 (STAC, extensiones Web Map Links y Authentication), §5.2 (Catalogue API
y CQL), §5.3 (acceso y stage-in/stage-out). D3 §4 completo (§4.2 colecciones y metadatos,
§4.2.3 queryables, §4.3 filtrado CQL2-JSON y CQL2-TEXT, §4.4 STAC Item de ejemplo
comentado). D1 §3.2.3 (requisitos de cumplimiento de estándares). Perfil ESA §1.1 (tabla de
brechas: *Platform Domains Support — Not covered*).

**Documentación oficial:** `stacspec.org` (especificación y extensiones),
`github.com/stac-utils` (stac-fastapi, pgstac, pypgstac), OGC API – Features, y la
especificación de la Filter Extension (`github.com/stac-api-extensions/filter`).

---

## 14. Bitácora / hallazgos

*(Colecciones reales, versiones de PgSTAC, tiempos de consulta medidos, items problemáticos
y su causa.)*
