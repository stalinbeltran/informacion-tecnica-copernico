# S3/MinIO — Paso 7: ciclo de vida caliente→frío

**Objetivo de la sesión:** demostrar, con evidencia en pantalla, que una regla de ciclo de
vida **mueve** un objeto de `productos` a un almacenamiento frío separado — y que una regla
mal escrita **lo borra**. Es el único punto del criterio de dominio de S3 que quedó sin
verificar.

**Por qué importa aquí:** el pliego contrata rotación anual caliente→frío sobre 2 PB. Nadie
más administra esa regla. Si la escribes mal, el dato no se archiva: desaparece. Y en
`staging`, que no tiene versionado, desaparece sin vuelta.

**Duración estimada:** 90 minutos.
**Requisito previo resuelto en esta sesión:** el intento del 11-sep falló porque
`mc ilm tier add` apuntado al propio MinIO **se cuelga sin timeout** — valida el destino
contra su propio endpoint. Por eso hoy levantamos una **segunda instancia**.

---

## Mapa de la sesión

| Bloque | Qué haces | Qué demuestras |
|---|---|---|
| A | Levantar MinIO "frío" en `:9002` | El tier remoto existe y responde |
| B | Declarar el tier con `mc ilm tier add` | Por qué el paso previo era obligatorio |
| C | Regla de **transición** y forzar el reloj | Que **mueve**: sale de origen, llega a destino |
| D | **Sabotaje:** regla de expiración en vez de transición | Que **borra**, y que el versionado lo salva |
| E | **Sabotaje:** lo mismo en `staging` sin versionado | Que ahí no hay red |
| F | Cierre: actualizar runbook y bitácora | Artefacto contractual |

---

## Bloque A — La segunda instancia (el "frío")

El MinIO actual (`:9000`, datos en `~/lab-s3/data`) es el **caliente**. Levantamos otro
proceso, con su propio directorio de datos y sus propias credenciales, en `:9002`.

```bash
export PATH="$HOME/bin:$PATH"
mkdir -p ~/lab-s3-frio/data ~/lab-s3-frio/logs

MINIO_ROOT_USER=admin MINIO_ROOT_PASSWORD=frio12345 \
  nohup minio server ~/lab-s3-frio/data --address :9002 --console-address :9003 \
  > ~/lab-s3-frio/logs/minio.log 2>&1 &
```

Verifica que **los dos** están vivos antes de seguir:

```bash
curl -fsS http://127.0.0.1:9000/minio/health/live && echo "CALIENTE OK"
curl -fsS http://127.0.0.1:9002/minio/health/live && echo "FRIO OK"
```

Alias y bucket destino:

```bash
mc alias set frio http://127.0.0.1:9002 admin frio12345
mc mb frio/archivo
mc ls frio
```

> **Anota:** ¿por qué credenciales distintas en cada instancia? Porque el tier frío es, en la
> plataforma real, **otro servicio del proveedor** — posiblemente otra cuenta, otra región,
> otro contrato de latencia. Tratarlo como "el mismo MinIO con otro bucket" es el error
> conceptual que lleva a configurar lifecycle sin entender qué cruza la frontera.

---

## Bloque B — Declarar el tier

Aquí está el hallazgo del intento anterior: **una regla de transición no puede nombrar un
tier que no existe** (`Invalid storage class`). El tier se declara primero, en el MinIO
**caliente**, apuntando al **frío**:

```bash
mc ilm tier add minio lab FRIO \
  --endpoint http://127.0.0.1:9002 \
  --access-key admin \
  --secret-key frio12345 \
  --bucket archivo \
  --prefix rotado/
```

Comprueba:

```bash
mc ilm tier ls lab
mc ilm tier info lab FRIO
```

**Lee la salida con atención.** Fíjate en:
- El **nombre del tier** (`FRIO`) es una etiqueta local del MinIO caliente. No existe en el frío.
- El `--prefix rotado/` define **dónde aterrizan** los objetos transicionados.
- Las credenciales quedan **guardadas en el MinIO caliente**. Esto es una credencial más que
  rotar — y si caduca, la rotación caliente→frío falla en silencio. Apúntalo: es candidato a
  ítem de monitorización en el runbook.

> Si este comando se queda colgado: estás apuntando al endpoint equivocado (`:9000` en vez de
> `:9002`). Ctrl-C, revisa el `--endpoint`.

---

## Bloque C — La regla que MUEVE

Sube un objeto de prueba:

```bash
head -c 5M /dev/urandom > /tmp/producto-viejo.tif
mc cp /tmp/producto-viejo.tif lab/productos/sentinel-2/2025/producto-viejo.tif
mc stat lab/productos/sentinel-2/2025/producto-viejo.tif
```

Añade la regla de **transición** (no de expiración):

```bash
mc ilm rule add lab/productos \
  --prefix "sentinel-2/2025/" \
  --transition-days 0 \
  --transition-tier FRIO
mc ilm rule ls lab/productos
```

**El problema del reloj:** MinIO evalúa el ciclo de vida en un barrido periódico, no al
instante. Por eso la regla va con `--transition-days 0`. Si aun así no pasa nada, acelera el
escáner:

```bash
mc admin scanner status lab        # observa el ciclo
mc admin config set lab scanner speed=fastest
```

**La verificación — esto es lo que demuestra el criterio de dominio.** No basta con "ya no
está en caliente". Hay que probar las **tres** cosas a la vez:

```bash
# 1. El objeto SIGUE siendo visible y descargable desde el bucket original
mc stat lab/productos/sentinel-2/2025/producto-viejo.tif
mc cp lab/productos/sentinel-2/2025/producto-viejo.tif /tmp/recuperado.tif

# 2. Su metadato dice que está en el tier frío
mc stat lab/productos/sentinel-2/2025/producto-viejo.tif | grep -i "storage\|tier\|class"

# 3. Los BYTES están ahora en la otra instancia
mc ls --recursive frio/archivo
mc du frio/archivo
mc du lab/productos
```

**El concepto central:** una transición **no cambia la dirección del objeto**. La key sigue
siendo `productos/sentinel-2/2025/producto-viejo.tif`. Lo que cambia es **dónde viven los
bytes**. Por eso el asset STAC que apunta ahí con `s3://` **no se rompe** al archivar — y por
eso archivar es seguro y borrar no lo es.

```bash
diff /tmp/producto-viejo.tif /tmp/recuperado.tif && echo "IDENTICOS — la transicion no corrompe"
```

> **Anota la latencia.** Cronometra la descarga del objeto transicionado y compárala con una
> de las del Paso 6 (16 KB → 1,80 ms · 1 MB → 2,22 ms, todas en caliente). En producción esa
> diferencia es la que hay que reportar al usuario que pregunta por qué una descarga tarda más.

```bash
time mc cp lab/productos/sentinel-2/2025/producto-viejo.tif /tmp/x1.tif
```

---

## Bloque D — SABOTAJE 1: la regla que borra

Este es el sabotaje pendiente de la lista obligatoria. Cambia **una palabra** de la regla:

```bash
# Sube un segundo objeto, virgen
head -c 5M /dev/urandom > /tmp/producto-condenado.tif
mc cp /tmp/producto-condenado.tif lab/productos/landsat-8/2025/producto-condenado.tif

# La regla equivocada: EXPIRE en vez de TRANSITION
mc ilm rule add lab/productos \
  --prefix "landsat-8/2025/" \
  --expire-days 0
mc ilm rule ls lab/productos
```

Espera el barrido y observa:

```bash
mc ls lab/productos/landsat-8/2025/
mc ls --versions lab/productos/landsat-8/2025/
```

**Lo que debes ver y explicar:**
- El objeto **ya no aparece** en un listado normal.
- Con `--versions` aparece **un delete marker** encima de la versión real.
- Los bytes **no llegaron a `frio/archivo`**: `mc ls --recursive frio/archivo` no los tiene.

Recupéralo aplicando lo del Paso 5 — **borra el marcador de borrado**:

```bash
mc ls --versions lab/productos/landsat-8/2025/producto-condenado.tif
mc rm --version-id <ID-DEL-DELETE-MARKER> lab/productos/landsat-8/2025/producto-condenado.tif
mc ls lab/productos/landsat-8/2025/
```

**Limpia la regla asesina antes de seguir:**

```bash
mc ilm rule ls lab/productos          # localiza el ID
mc ilm rule rm --id <ID> lab/productos
```

> **La frase que tienes que poder decir:** *"`--expire-days` y `--transition-days` se escriben
> igual de fácil y hacen lo contrario. En un bucket versionado, la equivocación se revierte.
> Por eso el versionado se activa ANTES de tocar ciclo de vida, no después."*

---

## Bloque E — SABOTAJE 2: lo mismo en `staging`, sin red

`staging` es un-versioned. Repite exactamente el mismo error:

```bash
head -c 2M /dev/urandom > /tmp/sin-red.tif
mc cp /tmp/sin-red.tif lab/staging/entrada/sin-red.tif
mc stat lab/staging/entrada/sin-red.tif

mc ilm rule add lab/staging --prefix "entrada/" --expire-days 0
```

Tras el barrido:

```bash
mc ls lab/staging/entrada/
mc ls --versions lab/staging/entrada/
```

**Qué demuestra:** sin versionado no hay delete marker, no hay versión anterior, **no hay
recuperación**. La misma regla, el mismo error, resultado irreversible. Esto cierra también
el pendiente del Paso 5: el contraste `staging` sin versionado vs `productos` versionado.

Limpia:
```bash
mc ilm rule ls lab/staging
mc ilm rule rm --id <ID> lab/staging
```

> **Consecuencia operativa que va al runbook:** toda regla de ciclo de vida sobre un bucket
> sin versionado es un cambio **irreversible**. Procedimiento: se prueba primero en un bucket
> versionado, se verifica con `mc ilm rule ls`, y solo entonces se aplica. Nunca se escribe
> una regla directamente en producción sin versionado.

---

## Bloque F — Cierre

1. **Runbook** `runbooks/almacenamiento-objetos.md`, sección de rotación caliente→frío:
   - Los comandos exactos de declaración del tier (Bloque B).
   - El procedimiento de **verificación de que mueve** — las tres comprobaciones del Bloque C.
   - La advertencia `--expire-days` vs `--transition-days`.
   - La regla de oro: versionado antes que lifecycle.
   - La credencial del tier como ítem de rotación y monitorización.

2. **Bitácora** `bitacora-aprendizaje.md`: entrada del Paso 7 con lo que salió distinto a lo
   esperado. Esa parte es la que vale.

3. **Tabla de estado** `herramientas/00-orden-estudio-p2.md`: si los seis bloques salen,
   marca el **Dominio** de S3.

---

## Criterio de logro de esta sesión

- [ ] Explico por qué `mc ilm tier add` necesitaba una segunda instancia.
- [ ] Demuestro con tres comprobaciones que la transición **mueve** y no rompe la key.
- [ ] Explico por qué un asset STAC con `s3://` sobrevive a la rotación caliente→frío.
- [ ] Provoco el borrado por regla y lo recupero con el delete marker.
- [ ] Explico por qué el mismo error en `staging` es irreversible.
- [ ] Dejo escrito el procedimiento de rotación verificado en el runbook.

---

## Preguntas que esta sesión genera para el proveedor

Añádelas a `preguntas-para-esa.md` con lo que hayas observado:

1. La transición caliente→frío, ¿es transición de **clase** dentro del mismo servicio o
   movimiento a **otro endpoint** con credenciales propias? (Cambia quién rota esa credencial.)
2. Si es otro endpoint: ¿quién monitoriza que la credencial del tier sigue siendo válida?
   Una rotación caliente→frío falla **en silencio**.
3. Tras la transición, ¿el objeto sigue siendo legible por la misma key sin restauración
   previa, o requiere `RestoreObject`? El §8 del documento de la herramienta asume lo segundo;
   hay que confirmarlo, porque decide si Titiler y los assets STAC siguen funcionando.
4. ¿Qué latencia tiene la primera lectura de un objeto ya transicionado?
