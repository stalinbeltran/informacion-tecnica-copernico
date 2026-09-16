# Bitácora de ejecución

**Qué es esto:** el registro factual de lo que se ha **ejecutado realmente** en el
laboratorio. Sin interpretación, sin conceptos — para eso está
[`bitacora-aprendizaje.md`](bitacora-aprendizaje.md).

**Por qué existe:** el 2026-09-15 se descubrió que no había forma de distinguir lo que se
había ejecutado de lo que solo estaba escrito en el runbook. El bloque de ciclo de vida del
Paso 4 estaba documentado como configuración vigente, pero nunca se había visto actuar
ninguna regla — y nada lo registraba.

**La regla:** lo que no esté aquí **no se da por hecho**. Si una sección no aparece en este
archivo, se trata como pendiente aunque el runbook la documente.

---

## Fuentes de verdad

| Fuente | Qué registra | Dónde |
|---|---|---|
| Transcripción de sesión | Todo lo tecleado y toda la salida | `~/lab-s3/transcripciones/AAAA-MM-DD.log` |
| Historial de bash | Comandos con fecha y hora | `~/.bash_history` |
| Este archivo | Resumen curado por sesión | aquí |
| Audit log de MinIO | Cada llamada API con usuario y resultado | **pendiente de montar** |

### Cómo grabar una sesión

```bash
lab-rec        # arranca la grabación del día (alias de script -a -f)
# ...trabajar con normalidad...
exit           # cierra la grabación
```

La grabación es **acumulativa por día** (`-a`) y se vuelca al instante (`-f`), así que puede
leerse mientras la sesión sigue abierta.

---

## Estado real por paso — S3 / MinIO

Leyenda: **✅ ejecutado y verificado** · **⚠️ configurado pero nunca visto actuar** · **❌ pendiente**

| Paso | Bloque | Estado | Evidencia |
|---|---|---|---|
| 1 | Buckets y objetos | ✅ | 3 buckets existen; 10 objetos en `productos` |
| 2 | Prefijos, stat, upload | ✅ | Entrada en bitácora de aprendizaje |
| 3 | Lecturas parciales y latencias | ✅ | Números anotados: 16 KB → 1,80 ms · 1 MB → 2,22 ms |
| 4a | Políticas de acceso | ✅ | Usuarios `lector` y `analista`; políticas `solo-lectura-s2`, `lectura-s2`, `prueba-rota`, `solo-lectura-rota` |
| 4b | **Reglas de ciclo de vida** | **⚠️** | Las 3 reglas existen en el servidor y están en el runbook, pero **ninguna se ha visto actuar** |
| 4c | **Transición a tier frío** | **❌** | `mc ilm tier add` se colgó (MinIO contra sí mismo). Nunca completado |
| 5 | Versionado y delete marker | ✅ | `historia.tif` con v1/v2/v3; recuperación por borrado de marker |
| 6 | URLs prefirmadas | ✅ | `AccessDenied` / *Request has expired* obtenidos; sabotaje de firma cerrado el 15-sep |
| 7 | Auditoría de accesos | ⚠️ | Procedimiento escrito en el runbook; no re-verificado |

### Sabotajes

| Sabotaje | Estado |
|---|---|
| `Resource` bucket vs `bucket/*` | ✅ |
| Política sin `ListBucket` | ✅ |
| URL firmada de objeto inexistente | ✅ |
| URL firmada expirada | ✅ |
| URL firmada **alterada y vigente** → `SignatureDoesNotMatch` | ✅ 15-sep: key alterada y firma alterada, ambas `SignatureDoesNotMatch`, con control 200 posterior |
| Lifecycle que borra en vez de mover | ❌ requiere tier frío |
| Multipart abortado | ⚠️ sin confirmar |
| Credencial rotada sin actualizar Secret | ❌ requiere clúster |

---

## Sesiones

### 2026-09-11 — Pasos 1 a 6

Sesión **sin transcripción** (anterior a este mecanismo). Lo anotado aquí se reconstruyó el
15-sep a partir del estado del servidor, del runbook y de la bitácora de aprendizaje.

Entorno: MinIO `RELEASE.2025-09-07`, WSL2 Ubuntu 24.04, binarios en `~/bin`, datos en
`~/lab-s3/data`, API `:9000`, consola `:9001`.

**Verificado hoy contra el servidor:**

```
Buckets:    productos (versioning enabled) · staging (un-versioned) · frio (un-versioned)
Objetos:    10 en productos, 13 versiones totales, 0 delete markers
Usuarios:   lector → solo-lectura-s2 · analista → lectura-s2
Políticas:  solo-lectura-s2, lectura-s2, prueba-rota, solo-lectura-rota
ILM productos: 3 reglas (JSON abajo)
ILM staging:   1 regla (Expiration Days 365)
```

Reglas de `productos`, salida literal de `mc ilm rule export lab/productos`:

```json
{"Rules":[
 {"ID":"dai0tlrks34ceaika6mg","NoncurrentVersionExpiration":{"NoncurrentDays":30},"Status":"Enabled"},
 {"ID":"dai0tojks34cep6fqo30","Filter":{"Prefix":"sentinel-2/"},"NoncurrentVersionExpiration":{"NoncurrentDays":30},"Status":"Enabled"},
 {"ID":"dai0tojks34ceukoakcg","Expiration":{"ExpiredObjectDeleteMarker":true},"Status":"Enabled"}
]}
```

**Lo que no se pudo establecer:** quién creó esas reglas y cuándo. MinIO no guarda autoría de
cambios de configuración, `~/.bash_history` se cortó en el Paso 6 (la sesión seguía abierta,
bash vuelca al cerrar), y la bitácora de aprendizaje **no tiene entrada del bloque de ciclo
de vida**. La atribución al 11-sep es **inferencia** por coincidencia exacta con el JSON del
runbook, no un hecho registrado.

**Comprobado el 15-sep (tarde):** `grep ilm ~/.bash_history` devuelve **cero líneas** sobre 183. Stalin
no ha tecleado nunca un comando `mc ilm`. Los únicos `ilm` con constancia los ejecutó Claude
(`mc ilm rule export`, 15-sep). El Bloque B del Paso 7 es la **primera vez** que se practican.

---

### 2026-09-15 — Preparación del Paso 7 y trazabilidad

**Ejecutado por Claude, verificado en pantalla:**

| # | Acción | Resultado |
|---|---|---|
| 1 | Comprobar MinIO caliente | Vivo, PID 1161, desde 2026-09-11 01:56 |
| 2 | Levantar segundo MinIO "frío" | PID 3700 · `:9002` API · `:9003` consola · datos `~/lab-s3-frio/data` · `admin`/`frio12345` |
| 3 | Health check de ambos | `CALIENTE OK` · `FRIO OK` |
| 4 | `mc alias set frio http://127.0.0.1:9002` | `Added 'frio' successfully` |
| 5 | `mc mb frio/archivo` | `Bucket created successfully` |
| 6 | Auditar estado del caliente | Sin cambios; los 3 buckets intactos |
| 7 | `mc ilm rule export lab/productos` | JSON de las 3 reglas (arriba) |
| 8 | Configurar trazabilidad en `~/.bashrc` | `HISTTIMEFORMAT`, `HISTSIZE=50000`, `PROMPT_COMMAND="history -a"`, alias `lab-rec`. Backup en `~/.bashrc.bak-2026-09-15` |
| 9 | Crear `~/lab-s3/transcripciones/` | Creada |

**No ejecutado todavía:** Bloque B en adelante del Paso 7 (declarar el tier, transición,
sabotajes). El laboratorio está preparado, no avanzado.

**Trampa a recordar — dos cosas se llaman `frio`:**

| Nombre | Qué es | Uso |
|---|---|---|
| `lab/frio` | Un **bucket** dentro del MinIO caliente | ❌ no usar — no es un tier real |
| `frio/archivo` | Bucket en la **segunda instancia** (`:9002`) | ✅ el destino de la transición |

### 2026-09-15 (tarde) — Cierre del sabotaje de firma del Paso 6

**Ejecutado por Stalin, con transcripción en `~/lab-s3/transcripciones/2026-09-15.log`:**

| # | Acción | Resultado |
|---|---|---|
| 1 | `mc share download --expire 10m` sobre `prueba.tif` | URL emitida, `X-Amz-Expires=600`, con `versionId` |
| 2 | `curl` a la URL original (primer intento) | `HTTP 403` — variable mal poblada, no fallo del servidor |
| 3 | Reemitir URL y `curl` | `HTTP 200` |
| 4 | Key alterada `prueba.tif` → `mentira.tif` | `SignatureDoesNotMatch` |
| 5 | Firma alterada (un `0` antepuesto) | `SignatureDoesNotMatch` |
| 6 | **Control:** `curl` a la URL original otra vez | `HTTP 200` — el 403 no fue caducidad |

Con esto el Paso 6 queda **cerrado con evidencia**. El concepto está en
`bitacora-aprendizaje.md`, entrada del 15-sep.

---

**Corrección registrada:** la tabla de `mc ilm rule ls` muestra `DAYS TO EXPIRE: 0` para una
regla que **no tiene** campo `Days` — imprime `0` para un campo ausente. Leerla como "expira
en cero días" es un error de diagnóstico grave. **Ante cualquier duda sobre una regla de
ciclo de vida: `mc ilm rule export` y se lee el JSON.** La tabla es orientativa; el JSON es
la fuente de verdad.

---

### 2026-09-15 (tarde-noche) — Bloque B del Paso 7: tier declarado

**Descubierto el 15-sep al retomar:** el Bloque B **sí se ejecutó** y no estaba registrado.
La bitácora decía "No ejecutado todavía: Bloque B en adelante" — era falso. Se comprobó
contra `~/.bash_history` (líneas 207-281) y contra el estado del servidor.

**Ejecutado por Stalin:**

| # | Acción | Resultado |
|---|---|---|
| 1 | `mc ilm tier add minio lab FRIO --endpoint :9002 --bucket archivo --prefix rotado/` | Tier creado |
| 2 | `mc ilm tier ls lab` | `FRIO · minio · http://127.0.0.1:9002 · archivo · rotado/` |
| 3 | `mc ilm tier info lab FRIO` | `warm · 0 B · 0 objetos · 0 versiones` |
| 4 | `mc admin user add frio rotador rotador12345` | Usuario creado en el frío (no usado por el tier) |

Estado verificado hoy: el tier `FRIO` existe, apunta a `:9002`, bucket `archivo`, prefijo
`rotado/`, y reporta `0 objetos` — coherente con que **aún no ha transicionado nada**.

**El desvío de la sesión — qué consumió el tiempo:** unos 20 minutos buscando
`mc ilm tier check`, que **no existe** en `mc RELEASE.2025-08-13`. Se intentó 7 veces con
variantes de sintaxis. El texto `check  validate remote tier configuration` que se tecleó
salía de una lista de ayuda y se copió como si fuera un comando. También se abrió
`nano .minio.sys/config/tier-config.bin` — un binario de configuración interna que **no debe
editarse a mano**; salió sin guardar.

**Lección operativa:** cuando un subcomando no aparece en `mc ilm tier --help`, no existe.
Repetirlo con variantes no lo invoca. La verificación real de que un tier funciona **no es un
comando de check: es transicionar un objeto y ver llegar los bytes** — que es exactamente el
Bloque C.

**Pendiente real a esta hora:** Bloques C, D, E y F.

### 2026-09-15 — Bloque C en curso: regla de transición creada

**Ejecutado por Stalin:**

| # | Acción | Resultado |
|---|---|---|
| 1 | `head -c 5M /dev/urandom > /tmp/producto-viejo.tif` | Objeto de 5 MiB |
| 2 | `mc cp` a `lab/productos/sentinel-2/2025/producto-viejo.tif` | Subido. `ETag 71bd88487b4a4a80c158c96dde703fe3`, `VersionID addf1130-82b3-401a-bd7e-7b177c20406c` |
| 3 | `mc stat` (línea base) | **Sin campo de storage class** — `mc stat` omite el valor por defecto; `mc ls` sí muestra `STANDARD` |
| 4 | `mc ilm rule add --prefix sentinel-2/2025/ --transition-days 0 --transition-tier FRIO` | Regla `dakqt4rks34dnl679r70` creada |
| 5 | `mc ilm rule export lab/productos` | Verificado: `"Transition":{"StorageClass":"FRIO","Days":0}` — **es transición, no expiración** |

**Estado a esta hora:** la regla existe y es correcta, pero **no ha transicionado nada**:
`mc ilm tier info lab FRIO` → `0 B / 0 objetos`; `frio/archivo` vacío. Esperado: MinIO evalúa
el ciclo de vida en un barrido periódico. `Days: 0` significa *elegible ya*, no *hazlo ahora*.

**Segundo comando de `mc` que se cuelga sin timeout — patrón repetido:**
`mc admin scanner status lab` no devolvió **ni una línea** en más de 120 s. Hubo que matarlo.
Es el mismo comportamiento que `mc ilm tier add` contra el propio endpoint el 11-sep.

> **Regla operativa que sale de aquí:** todo comando `mc admin *` de este laboratorio se
> ejecuta con `timeout 20 mc ...`. Colgarse sin mensaje es un modo de fallo real de `mc`, no
> una anomalía puntual. En producción, un comando administrativo sin timeout dentro de un
> script de guardia bloquea el script entero.

**Observación:** `~/lab-s3/logs/minio.log` **no registra ninguna línea** de ILM, tier,
transition ni lifecycle. El log por defecto no traza el barrido del ciclo de vida. Candidato a
ítem de runbook: *sin audit log ni traza de ILM, una rotación caliente→frío que falla no deja
rastro en el log* — refuerza la pregunta 2 de `preguntas-para-esa.md`.

### 2026-09-15 — Bloque C CERRADO: la transición mueve y no rompe la key ✅

**Cómo se disparó el barrido** (la regla existía desde las 15:4x pero no actuaba):

```bash
timeout 20 mc admin config set lab scanner speed=fastest
timeout 20 mc admin service restart lab
```

El `service restart` fuerza un barrido al arrancar. Transición registrada a las **15:54:30**.

**Las tres comprobaciones del criterio de dominio — todas verificadas:**

| # | Comprobación | Resultado |
|---|---|---|
| 1 | El objeto sigue visible y descargable **por la misma key** | ✅ `mc cp` OK, 5 MiB a 191 MiB/s |
| 2 | Su metadato declara el tier frío | ✅ `X-Amz-Storage-Class: FRIO` **apareció** en `mc stat` |
| 3 | Los bytes están en la otra instancia | ✅ `frio/archivo` = 5 MiB / 1 objeto; tier info = `5.0 MiB / 1 / 1` |

**Integridad:** `md5 71bd88487b4a4a80c158c96dde703fe3` idéntico antes y después. El ETag del
objeto **no cambió** con la transición. La transición no corrompe ni re-empaqueta.

**Ocupación tras la transición:** `lab/productos` = 517 MiB / 11 objetos · `frio/archivo` =
5 MiB / 1 objeto. El caliente **sigue contando el objeto en su listado** aunque los bytes ya
no estén ahí.

**El hallazgo conceptual — cómo aterriza el objeto en el frío:**

```
Origen  (key lógica, no cambia):  productos/sentinel-2/2025/producto-viejo.tif
Destino (bytes físicos):          archivo/rotado/f32c6db559791296/3d/1c/3d1ced76-369c-4920-ab92-8297edf5fa5f
```

El nombre en el frío es un **identificador opaco**, no la key original. Consecuencias
operativas, y son las que van al runbook:

1. **El asset STAC con `s3://productos/...` sobrevive a la rotación.** La key lógica es
   inmutable; solo cambia dónde viven los bytes. Por eso archivar es seguro y borrar no.
2. **El bucket frío es ilegible por sí solo.** Nadie puede encontrar un producto mirando
   `frio/archivo`: los nombres no tienen semántica. El mapa key→objeto opaco vive **solo en el
   MinIO caliente**. Si se pierde la metadata del caliente, los 2 PB del frío son bytes sin índice.
3. Esto convierte el backup de la metadata del caliente en **más crítico que el propio dato frío**.

**Latencia:** la primera lectura tras transicionar fue de **0,089 s** para 5 MiB — sin
penalización perceptible y sin `RestoreObject`. Contexto: es MinIO→MinIO sobre loopback. En la
plataforma real el frío puede ser otro proveedor con latencia de restauración muy distinta;
esto **no responde** la pregunta 3/4 de `preguntas-para-esa.md`, solo confirma que en MinIO
warm-tier la lectura es transparente.
