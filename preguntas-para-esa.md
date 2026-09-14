# Preguntas y consultas para ESA / Terradue / Proveedor

Registro vivo de las preguntas que hay que llevar a una reunión. Se añaden según aparecen —
en el estudio, en el laboratorio o en un incidente.

**Cómo usar este archivo:** antes de una reunión, filtrar por destinatario y por prioridad.
Cuando una se responda, anotar la respuesta **y la fecha** en su fila; no borrar la pregunta.

**Estados:** 🔴 abierta · 🟡 respuesta parcial · 🟢 respondida · ⚪ ya no aplica

**Prioridad:** **A** = bloquea trabajo o decisión · **B** = importante, no urgente ·
**C** = conviene saberlo

---

## Índice por destinatario

| Destinatario | Abiertas |
|---|---|
| [Proveedor de infraestructura](#proveedor-de-infraestructura) | 8 |
| [ESA / Terradue](#esa--terradue) | 7 |

---

## Proveedor de infraestructura

### S3 / Object Storage

> **Contexto que justifica todo este bloque:** el análisis de perfil de ESA marca
> *S3 Object Storage — Not included in contracted scope — **Not covered***. El proveedor
> entrega el servicio (capacidad, disponibilidad, latencias); la administración lógica
> (buckets, políticas, ciclo de vida, retención, auditoría) no tiene dueño en el contrato y
> el perfil ESA la asigna al Administrador de Middleware.

| # | Pregunta | Prio | Estado | Por qué importa |
|---|---|---|---|---|
| **S3-01** | ¿Qué acceso tendré a la API de S3, por qué vía (VPN o interfaz web) y con qué permisos exactos? | **A** | 🔴 | Sin acceso administrativo no puedo gestionar políticas ni auditar. Es el primer bloqueo posible |
| **S3-02** | ¿Qué mecanismo de gestión de identidades y políticas ofrece el servicio? ¿Es compatible con políticas estilo IAM (`Version`/`Statement`/`Effect`/`Action`/`Resource`) o tiene su propio modelo? | **A** | 🔴 | Determina si lo practicado en MinIO es trasladable tal cual o hay que reaprender el modelo |
| **S3-03** | ¿Soporta versionado, Object Lock y reglas de ciclo de vida? ¿Con qué limitaciones? | **A** | 🔴 | El versionado es la red de seguridad ante un lifecycle mal escrito. Sin él, la rotación anual es irreversible |
| **S3-04** | ¿Cómo se materializa la transición caliente→frío: clase de almacenamiento, bucket separado o proceso manual? | **A** | 🔴 | La rotación anual es responsabilidad mía y no puedo diseñarla sin saber el mecanismo. **Bloqueó una prueba de laboratorio** (ver nota 1) |
| **S3-05** | ¿Cuál es el procedimiento y el tiempo esperado para recuperar desde frío? El pliego habla de **20 TB por solicitud** — ¿cómo se solicita y cuánto tarda? | **B** | 🔴 | El pliego dice que las latencias y flujos "se manejan a nivel de orquestación" = lo diseño yo |
| **S3-06** | ¿Hay logs de acceso a objetos? ¿Con qué retención y en qué formato? | **B** | 🔴 | Sin logs no puedo responder "¿quién accedió a este producto?" — y la auditoría de accesos está a mi nombre |
| **S3-07** | ¿Cómo se miden y reportan las latencias comprometidas de **100 ms lectura / 200 ms escritura**? | **B** | 🔴 | Van al informe mensual. Necesito saber si mido yo o si el proveedor entrega la métrica |
| **S3-08** | ¿Qué tamaño de parte usa el servicio en multipart upload, y es configurable? | **C** | 🔴 | Determina si un ETag es reproducible para verificar integridad (ver nota 2) |

---

## ESA / Terradue

### S3 / Almacenamiento

| # | Pregunta | Prio | Estado | Por qué importa |
|---|---|---|---|---|
| **MW-01** | ¿Cómo se gestionan los secretos y la rotación de credenciales S3 entre componentes (ESO, backend de secretos)? | **A** | 🔴 | Es la **avería 17** del catálogo: credencial rotada sin actualizar el Secret → el workflow no puede subir el artefacto |
| **MW-02** | ¿Qué servicio implementa el endpoint de URLs firmadas, qué token acepta y cuánto dura la firma? | **A** | 🔴 | D3 §6 muestra `X-Amz-Expires=120` (2 min). Necesito saber si es configurable y quién lo opera |
| **MW-03** | ¿Qué esquema de buckets y prefijos usa el Middleware? ¿Uno por colección, uno por workflow, uno por workspace? | **A** | 🔴 | Las políticas se escriben por prefijo. Sin el esquema no puedo diseñar el modelo de acceso |
| **MW-04** | ¿Quién limpia los objetos huérfanos cuando un item se elimina del catálogo? | **B** | 🔴 | Consistencia catálogo↔almacenamiento. Items que apuntan a objetos borrados y objetos sin item. Alimenta el Producto 7 (optimización) |

### Integridad y media types — **salidas del laboratorio 2026-09-11**

| # | Pregunta | Prio | Estado | Por qué importa |
|---|---|---|---|---|
| **MW-05** | **¿La ingesta guarda algún checksum del producto (SHA-256), o solo se confía en el ETag?** STAC tiene extensión estándar `file:checksum` — ¿se usa? | **A** | 🔴 | **Ver nota 2.** Si nadie la usa, verificar integridad de productos grandes **no es posible hoy**. Hallazgo |
| **MW-06** | **¿Quién valida que un objeto etiquetado como COG lo sea realmente?** ¿El workflow de ingesta, o nadie? | **A** | 🔴 | **Ver nota 3.** El media type es una declaración sin verificar. Un TIFF normal etiquetado como COG → avería 13 (mapa en blanco) |
| **MW-07** | **¿Quién valida que un COG real se etiquete con el media type COMPLETO?** ¿Hay control sobre el truncamiento a `image/tiff` a secas? | **A** | 🔴 | **Ver nota 4.** Avería **silenciosa**: nada falla, todo se descarga entero, sistema lento sin causa aparente |

---

## Notas de laboratorio que sustentan las preguntas

### Nota 1 — La transición a tier frío bloqueó una prueba (S3-04)

En MinIO, una regla de lifecycle **no puede nombrar un tier que no existe**:
```
mc: <ERROR> Unable to add this lifecycle rule. Invalid storage class.
```
El tier se declara antes con `mc ilm tier add`, apuntando a un destino S3 externo. Declararlo
contra el propio MinIO **cuelga el comando indefinidamente**. Consecuencia: el sabotaje
"lifecycle que borra en vez de mover" quedó **sin verificar** — y es justo el que importa para
la rotación anual del pliego. Requiere un segundo MinIO o el endpoint real del proveedor.

### Nota 2 — El ETag no sirve para verificar productos grandes (S3-08, MW-05)

El ETag de un objeto subido **en una sola parte** es el MD5 del contenido — verificable con
`md5sum`. **Verificado en laboratorio:** `1c8b1c0e0ec169c5f86f63a0dec68984` coincidió exacto.

Pero con **multipart upload** (automático a partir de cierto tamaño) el ETag pasa a ser un
hash de hashes con sufijo `-<nº de partes>`. Entonces:
- `md5sum` **nunca** coincide, y eso **no es corrupción**.
- Reproducirlo exige conocer **el tamaño de parte exacto** usado al subir (de ahí S3-08).

Los productos reales son de 100 MB–1 GB (máx. 8 GB) → **casi todos serán multipart**.
Conclusión: para verificar integridad de productos hace falta un checksum propio guardado en
la ingesta. De ahí MW-05.

### Nota 3 — El media type es una declaración, no un hecho (MW-06)

**Verificado:** un archivo que contenía el texto `mi primera banda` quedó almacenado con
`Content-Type: image/tiff`, porque `mc` **adivinó por la extensión `.tif`**. S3 no abre el
archivo, no busca la cabecera TIFF, no valida la estructura. Los bytes y la etiqueta son
cosas independientes.

Un asset STAC declara:
```json
"type": "image/tiff; application=geotiff; profile=cloud-optimized"
```
Ese `profile=cloud-optimized` es una **promesa** de que el archivo admite lectura parcial.
Nada ata la promesa al hecho, salvo que alguien valide en la ingesta.

### Nota 4 — El media type se trunca con facilidad alarmante (MW-07)

**Hallazgo inesperado del laboratorio.** Dos herramientas independientes, en la misma sesión,
truncaron el media type de COG dejando `image/tiff` a secas:

| Herramienta | Qué hizo |
|---|---|
| `mc cp --attr "Content-Type=image/tiff; application=geotiff; profile=cloud-optimized"` | Partió el valor por `;` (lo usa como separador interno de atributos) y descartó los fragmentos restantes |
| `curl -F 'Content-Type=image/tiff; application=geotiff; profile=cloud-optimized'` | Mismo corte: `Warning: skip unknown form field: application=geotiff` |

**El `;` dentro de un media type es un punto de fallo recurrente en toda la cadena.**

Esto produce el caso **inverso** al de la nota 3, y es peor porque es silencioso:

| Caso | Etiqueta | Realidad | Síntoma |
|---|---|---|---|
| Nota 3 | dice COG | no lo es | Titiler falla, mapa en blanco → **avería 13**, visible |
| **Nota 4** | dice `image/tiff` a secas | **sí es COG** | Nada falla. Nadie intenta lectura parcial. Todo se descarga entero. **Lentitud sin causa aparente** |

Un workflow de ingesta con el `--attr` mal escrito produce COGs legítimos que el catálogo no
anuncia como cloud-optimized. No hay error que alertar — solo desempeño degradado.

---

## Diferencias D1 ↔ pliego que conviene plantear a ESA

No son preguntas de laboratorio sino discrepancias contractuales documentadas. Hay que
conocerlas antes de cualquier reunión de expectativas.

| Parámetro | D1 (especificación ESA) | Pliego (contratado) | Diferencia |
|---|---|---|---|
| Object storage frío | 20 PB (mín. 22 PB total) | **750 TB** | ~27× menos |
| Nodos K8s | hasta 1000 | hasta 500 | mitad |
| Balanceador | ≥ 4 Gbps | ≥ 1 Gbps | ¼ |
| PostgreSQL | 4 instancias 16/64 | 2 instancias 16/64 | mitad |
| Disponibilidad | 99,5 % anual, MTTR < 1 h | 99,95 % mensual | métricas distintas, no comparables directamente |

**La del almacenamiento frío es la más grave** y afecta directamente al diseño de la rotación
anual: con 750 TB de frío en vez de 20 PB, la política de retención tiene que ser mucho más
agresiva, o el frío se llena. Relacionada con S3-04 y S3-05.

---

*Iniciado el 2026-09-11 durante el laboratorio de S3/MinIO.
Fuentes: archivo de estudio [herramientas/06-s3-minio.md](herramientas/06-s3-minio.md) §12,
perfil ESA §1.1 y §2.3.4, pliego Anexo I, y hallazgos propios del laboratorio
([bitacora-aprendizaje.md](bitacora-aprendizaje.md)).*
