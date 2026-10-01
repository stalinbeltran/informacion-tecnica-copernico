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
| 4b | **Reglas de ciclo de vida** | **✅** | 29-sep: la regla `dalbkgrks34dq4krgq90` expiró 2 objetos de `landsat-8/2025/`; delete markers verificados |
| 4c | **Transición a tier frío** | **✅** | 15-sep: tier `FRIO` declarado y `producto-viejo.tif` transicionado; caliente pasó de 5 MiB a 8 KB |
| 5 | Versionado y delete marker | ✅ | `historia.tif` con v1/v2/v3; recuperación por borrado de marker. 30-sep: repetido sobre objeto expirado por lifecycle |
| 6 | URLs prefirmadas | ✅ | `AccessDenied` / *Request has expired* obtenidos; sabotaje de firma cerrado el 15-sep |
| 7 | Auditoría de accesos | ✅ | 30-sep: `audit_webhook:lab` activo con receptor propio; 14 eventos capturados con hora, operación, objeto, IP y credencial |

### Sabotajes

| Sabotaje | Estado |
|---|---|
| `Resource` bucket vs `bucket/*` | ✅ |
| Política sin `ListBucket` | ✅ |
| URL firmada de objeto inexistente | ✅ |
| URL firmada expirada | ✅ |
| URL firmada **alterada y vigente** → `SignatureDoesNotMatch` | ✅ 15-sep: key alterada y firma alterada, ambas `SignatureDoesNotMatch`, con control 200 posterior |
| Lifecycle que borra en vez de mover | ✅ 30-sep: borrado por regla, delete marker y recuperación verificados |
| Expiración en bucket **sin versionado** (`staging`) | ✅ 30-sep: `rm` no deja marker, objeto irrecuperable; regla armada para el 1-oct |
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

**Verificación de liberación de espacio en el caliente — `mc du` NO sirve para esto:**

Tras la transición, el objeto ocupa en el disco caliente **8 KB en vez de 5 MiB**. Solo queda
`xl.meta` (579 bytes): la key, el ETag, el VersionID y el puntero al tier. El directorio con
los bytes **desapareció**.

Contraste en disco, misma instancia:

| Objeto | Estado | Disco real | Contenido del directorio |
|---|---|---|---|
| `grande.tif` (512 MiB) | normal | **513 M** | `xl.meta` + directorio de bytes `0a1e19ef-…` |
| `producto-viejo.tif` (5 MiB) | transicionado | **8 K** | **solo** `xl.meta` |

Totales: caliente `~/lab-s3/data` = **518 M** · frío `~/lab-s3-frio/data` = **5,3 M**.

**La trampa:** `mc du lab/productos` sigue diciendo `517MiB / 11 objects` — cuenta los 5 MiB
que ya **no** están en ese disco. No es un bug: reporta el tamaño **lógico** (lo que el cliente
vería al descargar), y en ese sentido es correcto.

> **Regla operativa para el runbook:** `mc du` mide el dato que ve el usuario, no la ocupación
> del disco. Para capacidad real del caliente: `du -sh` sobre el directorio de datos, o las
> métricas del servidor. En una rotación anual sobre 2 PB, confundir ambas cifras lleva a creer
> que no se ha liberado nada — o a dimensionar mal la compra de disco.

**Tercera cosa que solo vive en el caliente:** `xl.meta`. Refuerza el punto del backup — no es
solo "la metadata" en abstracto, es este fichero por objeto. Sin él, el objeto opaco del frío
es irrecuperable.

### 2026-09-16 — Bloque D: hallazgo, `--expire-days 0` está PROHIBIDO

**El runbook estaba mal.** `mc ilm rule add ... --expire-days 0` falla:

```
mc: <ERROR> Unable to generate new lifecycle rules for the input:
expiration days cannot be set to zero.
```

**La asimetría, que es el hallazgo real:**

| Acción | `Days: 0` | Comportamiento |
|---|---|---|
| `--transition-days 0` | ✅ aceptado | Se creó la regla del Bloque C y transicionó |
| `--expire-days 0` | ❌ **rechazado** | MinIO se niega a crear la regla |

MinIO **no deja escribir una regla que borre el mismo día**. Un mínimo de 1 día es obligatorio.
Archivar hoy sí; destruir hoy no. Es una barrera de seguridad deliberada del producto — el
único punto del ciclo de vida donde MinIO protege al administrador de sí mismo.

**Consecuencia operativa:** una regla de expiración **siempre** da al menos 24 h de margen
entre que se escribe y que destruye. Ese día es la ventana real para detectar el error y
retirar la regla. En el runbook: tras tocar cualquier regla de expiración, `mc ilm rule export`
**el mismo día** — al día siguiente ya ha actuado.

**Estado:** `producto-condenado.tif` subido a `landsat-8/2025/` (5 MiB, 2026-09-16 08:59:17).
La regla asesina **no existe**. El sabotaje aún no se ha ejecutado.

### 2026-09-16 — Bloque D: dos hallazgos sobre el RELOJ de la expiración

Regla creada: `{"ID":"dalbkgrks34dq4krgq90","Filter":{"Prefix":"landsat-8/2025/"},"Expiration":{"Days":1}}`.
Tras `mc admin service restart lab`: **no borró nada**. Los dos objetos siguen vivos, sin
delete marker. No es un fallo — es el comportamiento correcto, por dos razones.

**Hallazgo 1 — `touch` no engaña a MinIO. La antigüedad la fija el servidor.**

| Fecha | Valor |
|---|---|
| mtime del fichero local (tras `touch -d "3 days ago"`) | `2026-09-13 10:47:58` |
| Fecha que MinIO asigna al objeto | **`2026-09-16 10:48:09`** |

MinIO **ignora** el mtime del fichero de origen y sella el objeto con la hora del `PUT`. El
reloj del ciclo de vida es el del servidor, no el del cliente.

> **Consecuencia:** no se puede acelerar una prueba de expiración falseando fechas desde el
> cliente. Un objeto recién subido tiene 0 días de antigüedad, siempre. Para probar reglas de
> expiración hay que esperar el reloj real o manipular el servidor.

**Hallazgo 2 — `mc stat` ANUNCIA la ejecución futura. Es la herramienta de auditoría que faltaba.**

```
Expiration: 2026-09-17 19:00:00 EST (lifecycle-rule-id: dalbkgrks34dq4krgq90)
```

El objeto **sabe y declara** qué día morirá y **qué regla lo matará**. Esto es lo más
operativamente útil del Paso 7:

> **Procedimiento de verificación para el runbook:** tras escribir cualquier regla de
> expiración, `mc stat` sobre un objeto afectado. Si aparece la línea `Expiration:`, la regla
> **ya tiene sentencia dictada** — muestra la fecha y el ID de la regla culpable. Es la forma
> de auditar el impacto **antes** de que se ejecute, sin esperar al barrido.
> Y a la inversa: si se espera que una regla actúe y `mc stat` **no** muestra `Expiration:`,
> la regla no está alcanzando a ese objeto (prefijo mal escrito, filtro equivocado).

**Detalle del reloj:** sentencia a las `19:00:00`, no a las 10:48. MinIO **redondea al límite
de día UTC** — 2026-09-17 00:00 UTC = 19:00 EST del día anterior. Por eso `Days: 1` no
significa "24 h exactas desde el PUT", sino "al cruzar el siguiente límite de día". La ventana
real puede ser de pocas horas, no de un día completo.

**Estado:** `producto-condenado.tif` y `condenado2.tif` vivos, con sentencia para el
**2026-09-17 19:00 EST**. La regla `dalbkgrks34dq4krgq90` sigue activa. El borrado y su
recuperación por delete marker quedan **pendientes de verificar**.

### 2026-09-29 — La regla expiró los objetos, y el acceso a la consola desde Windows

**Estado al retomar:** ambas instancias arrancadas hoy (PID 516 frío 15:40:30, PID 536
caliente 15:40:46). `mc admin info lab` daba `connection refused` **antes** de ese arranque;
el servidor estaba genuinamente caído.

**La regla `dalbkgrks34dq4krgq90` actuó.** `mc ls lab/productos/landsat-8/2025/` vacío, y
`mc ls --versions`:

```
[2026-09-17 22:08:11 EST]     0B  v2 DEL  condenado2.tif
[2026-09-16 10:48:09 EST] 5.0MiB  v1 PUT  condenado2.tif
[2026-09-17 22:08:11 EST]     0B  v2 DEL  producto-condenado.tif
[2026-09-16 08:59:17 EST] 5.0MiB  v1 PUT  producto-condenado.tif
```

`mc admin info` confirma: 13 objetos, 18 versiones, **2 delete markers**.

**Confirmado:** en bucket versionado la expiración **pone lápida, no destruye**. Las v1 con
sus 5 MiB siguen intactas. Esto es lo que hace recuperable el sabotaje "lifecycle que borra
en vez de mover".

**Hallazgo — el timestamp de un delete marker no es la hora del borrado.**

Los delete markers llevan fecha **17-sep 22:08**, pero el proceso que los creó llevaba
**5 minutos vivo** cuando se leyeron (arrancó el 29-sep 15:40). MinIO ejecutó el barrido
pendiente **al arrancar** y selló los markers con la fecha en que los objetos vencieron, no
con la de ejecución.

> **Para el runbook:** `mc ls --versions` dice cuándo un objeto pasó a ser **elegible**, no
> cuándo se destruyó. Si el servidor estuvo apagado, el barrido actúa al arrancar con fecha
> retroactiva. Para auditar *cuándo se destruyó algo de verdad* hace falta el **audit log**
> (`audit_webhook`, hoy `off`) — que es justo el pendiente anotado el 15-sep y lo que pedirá
> el Producto 8. Este hallazgo es el argumento fuerte para activarlo.

**Corrección a un apunte del 16-sep:** se anotó que `mc stat` sentenciaba para las 19:00 EST
(límite de día UTC). No hay contradicción con el 22:08 del marker: ambas son fechas
retroactivas de elegibilidad, no de ejecución. No se observó ningún desfase real.

**Acceso a la consola web desde el navegador de Windows — dos causas de "no responde":**

| Síntoma | Causa real |
|---|---|
| `http://127.0.0.1:9000/minio/` en blanco | `:9000` es la **API S3**, no la consola. Esa ruta no existe; solo responde `/minio/health/live` |
| `http://127.0.0.1:9001` no carga | El loopback de Windows no llega a WSL. Desde WSL `curl :9001` daba **200** y `ss` mostraba el puerto escuchando en `*:9001` |

Solución verificada: **`http://172.28.215.149:9001`** (IP de la distro, `hostname -I`). La IP
cambia en cada reinicio de WSL. Arreglo permanente: `localhostForwarding=true` en
`.wslconfig` + `wsl --shutdown` (tira las dos instancias de MinIO).

Documentado en `chuletas/s3-minio-objetos.md` §0 (arranque de las dos instancias, tabla de
consolas, y bloque de diagnóstico "no responde con el servidor vivo") y referenciado desde
`runbooks/almacenamiento-objetos.md` §1.

**Hueco cerrado:** ningún documento arrancaba las **dos** instancias — el runbook y la
chuleta solo tenían el caliente, el lab del Paso 7 solo el frío. Ahora la chuleta tiene el
arranque completo con el orden (frío antes que caliente) y por qué importa.

**Pendiente del Bloque D:** la recuperación por borrado del delete marker
(`--version-id 1d40a9eb-…` de `producto-condenado.tif`). Ojo: la regla
`dalbkgrks34dq4krgq90` **sigue activa** y los objetos tienen 12 días — con `Days: 1`,
cualquier versión restaurada es elegible de inmediato. Retirar la regla antes, o dejarla y
observar la re-ejecución.

### 2026-09-30 — Bloque D CERRADO: recuperación por borrado del delete marker ✅

**Estado final verificado:**

```
mc ls lab/productos/landsat-8/2025/
[2026-09-16 08:59:17 EST] 5.0MiB STANDARD producto-condenado.tif    ← resucitado
mc admin info lab → 13 Objects, 17 Versions, 1 Delete Marker
```

De 18 versiones / 2 markers a **17 versiones / 1 marker**. El marker restante es el de
`condenado2.tif`, dejado enterrado como control.

**El ciclo completo del Bloque D, de punta a punta:**

| Fase | Evidencia |
|---|---|
| Regla creada, sentencia anunciada | `mc stat` mostró fecha + ID de la regla culpable |
| Expiración ejecutada | 2 delete markers, datos intactos en v1 |
| Recuperación **fallida** con regla activa | El objeto volvió y murió otra vez en 30 s |
| Regla retirada | Desaparece del `ilm rule export` |
| **Recuperación efectiva** | `producto-condenado.tif` visible, 5 MiB |
| Control sin recuperar | `condenado2.tif` sigue con su lápida |

**Hallazgo 1 — retirar la regla ANTES de recuperar es parte del procedimiento, no una
precaución.**

Reconstruido del `.bash_history` (timestamps Unix):

| ts | comando |
|---|---|
| 1790691317 | `mc rm --version-id 1d40a9eb-…` (regla **aún activa**) → recupera |
| — | el barrido vuelve a matarlo → nace `ba9768df-…` el 29-sep 09:15 |
| 1790794423 | `mc ilm rule rm --id dalbkgrks34dq4krgq90` → retira la regla |
| 1790794610 | `mc rm --version-id ba9768df-…` → **recupera de verdad** |

Con la regla activa y el objeto ya vencido (13 días de antigüedad, `Days: 1`), lo restaurado
es elegible **al instante**. El objeto vuelve y desaparece sin que se le vea, y el síntoma
—"sigue sin aparecer"— es idéntico a que el comando hubiera fallado.

**Hallazgo 2 — el barrido es mucho más agresivo de lo supuesto: 30 segundos.**

Entre el `rm` que recuperó y el `ls` que lo vio muerto pasaron **30 s** (`1790794610` →
`1790794640`). No es un barrido horario ni diario: con el servidor vivo, re-ejecuta en
menos de un minuto. Corrige la suposición del 29-sep de que el barrido actuaba
principalmente al arrancar.

**Hallazgo 3 — la salida de `mc rm` NO es la prueba; los contadores sí.**

El comando se ejecutó dos veces (`1790794610` y `1790794808`). La primera funcionó; la
segunda falló porque el ID ya no existía, y ese error se interpretó como el resultado de la
operación.

> **Regla operativa:** verificar toda operación sobre versiones con
> `mc admin info lab | tail -3` (Objects / Versions / Delete Markers), nunca con el mensaje
> del `rm`. Un `rm --version-id` repetido **siempre** falla la segunda vez — y ese fallo
> significa que la primera funcionó.

Simetría con el 29-sep, que es lo que hace útil la regla: entonces el comando **pareció
funcionar y no funcionó**; hoy **pareció fallar y sí funcionó**. En ambos casos el mensaje
de `mc` engañaba y solo el estado del servidor decidía.

**Corrección a un apunte de esta misma sesión:** se afirmó que `.bash_history` no guardaba
horas. **Sí las guarda**, como líneas `#<epoch>` intercaladas; un `grep` de los comandos las
filtraba. Gracias a ellas se pudo medir el intervalo de 30 s del Hallazgo 2.

**Trazabilidad:** el alias `lab-rec` no se ha vuelto a usar desde el 15-sep (única
transcripción en `~/lab-s3/transcripciones/`). La reconstrucción se hizo con
`.bash_history` + timestamps, que resultó suficiente. El `audit_webhook` sigue `off`.

### 2026-09-30 (tarde) — Sabotaje en `staging`: el mismo borrado, sin red

Contraste deliberado con el Bloque D. Mismo comando, mismo tipo de regla, bucket distinto.

**La diferencia de partida:**

```
mc version info lab/staging     → lab/staging is un-versioned
mc version info lab/productos   → lab/productos versioning is enabled
```

**Montaje:** `sacrificio/sin-red.tif` (5 MiB) + regla `dault0rks34cs5gqteag`
(`Expiration: Days 1`, prefijo `sacrificio/`). Sentencia para **2026-10-01 19:00 EST**.

**El testigo — borrado manual, hoy:** `testigo.tif` subido y borrado con `mc rm`
(`#1790795611` → `#1790795624`). Resultado:

| Comprobación | Resultado |
|---|---|
| `mc ls --versions sacrificio/` | **no aparece**, ni una línea |
| `mc stat testigo.tif` | `Object does not exist` |
| `mc admin info` → Delete Markers | **1** (el mismo de antes; no subió) |

En `productos` el mismo `rm` **subía** el contador de markers. Aquí no hay lápida: el objeto
se evapora. Mismo comando, resultado opuesto.

**Hallazgo 1 — `mc stat` NO distingue un borrado reversible de uno definitivo.**

```
staging   → Expiration: 2026-10-01 19:00:00 EST (lifecycle-rule-id: dault0rks34cs5gqteag)
productos → Expiration: 2026-09-17 19:00:00 EST (lifecycle-rule-id: dalbkgrks34dq4krgq90)
```

Formato idéntico. Una era recuperable y la otra no, y **la sentencia no lo insinúa**.

> **Regla operativa:** lo que decide la reversibilidad no es la regla, ni `mc stat`, ni el
> comando de borrado: es el **versionado del bucket**, que no aparece en ninguna de esas tres
> señales. Antes de tocar cualquier regla de expiración → `mc version info <bucket>`.
> Si dice `un-versioned`, **no hay red**.

**Hallazgo 2 — `null` como version-id es el delator.**

Corrige lo que se supuso antes de probarlo: en un bucket sin versionado `mc ls --versions`
**sí** lista el objeto, no calla. Pero con `null` en lugar de UUID:

```
[2026-09-30 14:09:07 EST] 5.0MiB STANDARD null v1 PUT sacrificio/sin-red.tif
```

`null` significa "sin versionado". No hay nada debajo que restaurar. Es la señal más rápida
para saber si estás con red o sin ella.

**Hallazgo 3 — los contadores de `admin info` también lo cuentan.** `14 Objects / 17
Versions`: en `productos` las versiones superan a los objetos porque hay historia; en
`staging` cada objeto aporta 1 y 1. Sin versionado no hay historia que contar.

**Pendiente:** verificar el 1-oct tras las 19:00 EST que `sin-red.tif` desaparece **sin dejar
marker ni versión anterior**. Eso cierra el sabotaje.

### 2026-09-30 (noche) — `audit_webhook` ACTIVADO ✅ (pendiente desde el 15-sep)

**Estado:** receptor Python en `:8080` (PID 4064), target `audit_webhook:lab` configurado,
**14 eventos capturados**. Log en `~/lab-s3/audit/audit.jsonl`.

**Hallazgo 1 — no es un fichero de log, es un webhook.** El nombre es literal: MinIO hace
**POST HTTP de cada evento** a un endpoint. Sin un receptor escuchando, activarlo no produce
nada. Por eso el pendiente llevaba 15 días sin resolverse: no es un `enable=on`.

Receptor mínimo escrito en `~/lab-s3/audit-receptor.py` (15 líneas, `http.server`, vuelca
cada POST a `audit.jsonl`).

**Hallazgo 2 — se configura como *target*, con sufijo.** `audit_webhook:lab`, no
`audit_webhook`. El bloque base sigue diciendo `enable=off` y **es correcto** — son dos
entradas distintas. Mirar solo el base hace creer que no se aplicó:

```
audit_webhook enable=off endpoint= ...                          ← base, sigue off
audit_webhook:lab endpoint=http://127.0.0.1:8080 ...            ← el target real
```

**Hallazgo 3 — requiere `mc admin service restart lab`.** La config se acepta al instante
pero no se carga hasta el reinicio.

**Lo que el evento contiene, y que ninguna otra fuente daba:**

```
2026-09-30T19:40:12.310692147Z  PutObject              staging  aud.txt  127.0.0.1
2026-09-30T19:44:29.930708001Z  DeleteMultipleObjects  staging  aud.txt  127.0.0.1
```

Hora real al nanosegundo · operación · bucket · objeto · IP · `requestID` · y la credencial
en `Authorization` (`Credential=admin/20260930/...`).

> **El círculo se cierra:** `aud.txt` vivía en `staging`, **sin versionado** — su borrado no
> dejó delete marker ni rastro alguno en el bucket (sabotaje del 30-sep tarde). Sin audit log
> ese objeto no habría existido nunca para un auditor. Ahora consta que existió 4 m 17 s y
> quién lo borró. Y frente al delete marker de `productos`, que solo daba fecha de
> *elegibilidad* y ningún autor (hallazgo del 30-sep mañana), aquí hay hora de **ejecución**.
> Es el único mecanismo que responde *cuándo* y *quién*. Producto 8.

**Hallazgo 4 — la auditoría se audita a sí misma.** Entre los eventos aparecen `SetConfigKV`
y `ServiceV2`: el propio acto de activar el audit log y reiniciar quedó registrado. Un
administrador no puede tocar el registro sin dejar constancia.

**Punto ciego, y es inherente:** eso solo se cumple con el receptor **ya escuchando**. Un
`mc admin config reset` con el receptor caído no deja nada. Mandar los logs a un proceso
local no es auditoría real — en la plataforma el destino debe ser un colector remoto,
persistente y fuera del control del administrador auditado.

**Fragilidad del montaje de laboratorio:** el receptor es un `nohup` que **muere al reiniciar
WSL**. Hay que rearrancarlo con las dos instancias de MinIO.

**Lectura del log sin `jq`** (no está instalado):

```bash
python3 -c "
import json
for l in open('/home/stalin/lab-s3/audit/audit.jsonl'):
    try:
        e=json.loads(l); a=e.get('api',{})
        if 'Delete' in a.get('name','') or 'Put' in a.get('name',''):
            print(e['time'], a['name'], a.get('bucket'), a.get('object'), e.get('remotehost'))
    except: pass
"
```

**Prueba pendiente que ata los tres días:** mañana 1-oct tras las 19:00 EST el lifecycle mata
`sin-red.tif`. Con el audit log activo debe aparecer el evento con la **hora real del
barrido** — el dato que el delete marker nunca dio. Requiere que el receptor siga vivo.
