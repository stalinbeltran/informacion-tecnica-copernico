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
