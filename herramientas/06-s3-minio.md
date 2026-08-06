# S3 / MinIO — buckets, políticas, ciclo de vida y URLs firmadas

**Nivel exigido:** E — lo diseñas, lo optimizas y lo enseñas
**Prioridad:** 2 — **brecha declarada**: el análisis ESA marca esta área como *no cubierta*
**Competencia de la matriz:** 18

---

## 1. Qué es, aquí

Todo el dato pesado de CopernicusLAC vive en almacenamiento de objetos compatible con S3.
D2 §2.5 lo declara como supuesto de arquitectura:

> *"The use of object storage enables data management through a highly available S3
> compatible API… supports Cloud-Optimised Geotiffs (CoG). In addition to the primary object
> storage layer, the infrastructure expects also to interoperate with a **deep/cold storage
> archive tier**… Data recovered from cold storage will be staged back into the primary
> S3-compatible object storage layer for access and processing."*

Aparece en cinco sitios distintos: la ingesta guarda ahí los productos (D2 §4.2), el
catálogo apunta ahí con URIs `s3://` (D3 §4.4), el procesamiento lee y escribe ahí
(D2 §3.3.4), los workspaces de usuario reciben **buckets propios** aprovisionados por
Crossplane (D2 §3.6.2), y la descarga de usuarios pasa por **URLs prefirmadas** (D3 §6).

---

## 2. La frontera — la brecha más explícita de todo el encargo

El análisis de perfil de ESA tiene una fila que deberías poder citar de memoria:

| Área / Competencia | Alcance contratado | Perfil ESA | Cobertura |
|---|---|---|---|
| **S3 Object Storage** | **Not included in contracted scope** | IAM, lifecycle, retention | **Not covered** |

El proveedor entrega el **servicio**: capacidad, disponibilidad, latencias. No entrega la
**administración lógica**: buckets, políticas, ciclo de vida, retención, auditoría de
accesos. Eso está sin dueño en el contrato, y el perfil ESA te lo asigna a ti
(§2.3.4: *"validación de accesos, verificación de buckets y políticas, monitoreo básico de
desempeño y coordinación con el proveedor ante temas de integridad o recuperación de
datos"*).

| Materia | Proveedor | Tú |
|---|---|---|
| Servicio S3, capacidad, latencias | Sí | Los mides y los reclamas |
| Hardware, replicación, durabilidad | Sí | No |
| **Buckets y su organización** | No | **Sí** |
| **Políticas de acceso (IAM)** | No | **Sí** |
| **Reglas de ciclo de vida (hot→cold)** | No | **Sí** |
| **Retención y versionado** | No | **Sí** |
| **URLs prefirmadas y su servicio** | No | **Sí** |
| **Auditoría de quién accede a qué** | No | **Sí** |
| Recuperación de datos e integridad | Coordinas con él | Detectas y escalas |

Si te preguntan en qué se nota que este rol existe, ésta es la respuesta más limpia.

---

## 3. Qué debes saber

### Nivel imprescindible

**Modelo de objetos**
- Bucket, key (y por qué los "directorios" no existen — son prefijos), objeto, metadatos,
  ETag, versión.
- Media types y por qué importan: `image/tiff; application=geotiff; profile=cloud-optimized`
  es lo que declara un COG en un asset STAC.
- **Lecturas parciales por rango** (`Range: bytes=0-1023`). Es el mecanismo que hace posible
  el COG y Titiler: leer 16 KB de un objeto de 800 MB sin descargarlo.
- Multipart upload: cuándo se activa, por qué un objeto de 5 GB no se sube de una vez, y qué
  pasa con las partes huérfanas (ocupan espacio y no las ves listando objetos).

**Políticas de acceso**
- Estructura de una política: `Version`, `Statement`, `Effect`, `Principal`, `Action`,
  `Resource`, `Condition`.
- La distinción crítica: `arn:aws:s3:::bucket` (el bucket, para `ListBucket`) vs
  `arn:aws:s3:::bucket/*` (los objetos, para `GetObject`). **Confundirlos es el error nº 1
  y produce un 403 desconcertante.**
- Acciones que usarás: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`,
  `s3:GetBucketLocation`, `s3:AbortMultipartUpload`.
- Restricción por prefijo con `Condition` sobre `s3:prefix`.
- Deny explícito gana siempre sobre allow.

Ejemplo — solo lectura sobre un prefijo:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::productos/sentinel-2/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::productos"],
      "Condition": { "StringLike": { "s3:prefix": ["sentinel-2/*"] } }
    }
  ]
}
```

**Versionado y retención**
- Versionado: qué pasa al borrar (delete marker), cómo recuperar, y el coste en espacio.
- Object Lock / retención: si el proveedor lo soporta.
- Por qué el versionado es tu red frente a un lifecycle mal escrito.

**URLs prefirmadas**
- Qué son: una URL que lleva la firma HMAC en la query string, válida durante un tiempo
  limitado, que **no requiere credenciales en el cliente**.
- Parámetros que verás: `X-Amz-Algorithm=AWS4-HMAC-SHA256`, `X-Amz-Credential`,
  `X-Amz-Date`, `X-Amz-Expires`, `X-Amz-SignedHeaders`, `X-Amz-Signature`.
- Por qué una URL firmada de un objeto inexistente **se genera igual** y falla al usarla —
  la firma no verifica existencia.
- Por qué una URL expirada da 403 y no 401.

### Nivel operativo

**Ciclo de vida**
- Reglas por prefijo o por tag: transición entre clases de almacenamiento, expiración,
  limpieza de versiones no actuales, aborto de multipart incompletos.
- **El caso real de esta plataforma:** rotación **anual** de caliente a frío. Escribir esa
  regla y verificar que **mueve** en vez de **borrar** es un ejercicio con consecuencias.

```json
{
  "Rules": [
    {
      "ID": "rotacion-anual-caliente-a-frio",
      "Status": "Enabled",
      "Filter": { "Prefix": "productos/" },
      "Transition": { "Days": 365, "StorageClass": "GLACIER" }
    },
    {
      "ID": "limpieza-multipart-huerfanos",
      "Status": "Enabled",
      "Filter": { "Prefix": "" },
      "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
    }
  ]
}
```

**Medición de rendimiento**
- Medir latencia de **lectura parcial** con rangos de 16 KB a 1 MB sobre un objeto grande —
  exactamente el patrón que especifica el pliego.
- Medir throughput de subida y bajada. Contrastarlo con los **100 ms lectura / 200 ms
  escritura** contratados.
- Instrumentar esas mediciones para el informe mensual.

**Auditoría**
- Enumerar quién tiene acceso a qué: usuarios/cuentas, políticas asignadas, políticas de
  bucket.
- Verificar que un denegado **realmente** deniega. Nunca asumas por leer la política.
- Logs de acceso, si el proveedor los expone (pregunta abierta).

### Nivel avanzado

- Diseño del esquema de buckets y prefijos para 2 PB + 750 TB con miles de usuarios.
- Estrategia de recuperación desde frío: el pliego indica **20 TB por solicitud** como
  recuperación típica, y advierte que las latencias y flujos de gestión "se manejan a nivel
  de orquestación". Traducción: **eso lo diseñas tú.**
- Cuotas por workspace de usuario (los buckets los crea Crossplane, pero el límite es
  política).
- El servicio de URLs firmadas del Middleware: cómo se integra con Keycloak, qué token
  acepta, cuánto dura la firma.
- Consistencia entre catálogo y almacenamiento: items que apuntan a objetos borrados
  (huérfanos) y objetos sin item (basura). Detectar ambos es trabajo de optimización —
  Producto 7.

---

## 4. Datos de la plataforma que debes tener a mano

**Contratado (pliego, Anexo I):**

| Parámetro | Valor |
|---|---|
| Almacenamiento caliente | **2 PB**, S3-compatible |
| Almacenamiento frío | **750 TB** (D1 pedía 20 PB — diferencia relevante ante ESA) |
| Latencia máxima caliente | **100 ms lectura / 200 ms escritura** |
| Tamaño típico de objeto | 100 MB – 1 GB (**máx. 8 GB**) |
| Patrón de lectura | Lecturas parciales frecuentes de **16 KB – 1 MB** |
| Recuperación desde frío | típica **20 TB por solicitud** |
| Rotación | **anual**, caliente → frío |
| Acceso a la API S3 | por **VPN** (recomendado) o interfaz web |

**El esquema de descarga autenticada (D3 §6) — esto tienes que saberlo con precisión.**

El asset declara a qué esquema se acoge:
```json
"assets": {
  "nir": {
    "href": "s3://<storage-base>/sentinel-2-l1c-ingestion-xvv8c/S2A_.../r-nir.tif",
    "auth:refs": ["signed_url_auth"]
  }
}
```

Y las properties del item definen el esquema:
```json
"auth:schemes": {
  "signed_url_auth": {
    "type": "signedUrl",
    "flows": {
      "authorizationCode": {
        "method": "POST",
        "parameters": {
          "url":           { "in": "body",   "required": "true", "description": "asset URL" },
          "redirect":      { "in": "body",   "required": "true", "description": "302 con Location" },
          "Authorization": { "in": "header", "required": "true", "description": "Bearer <token>" }
        },
        "responseField": "signed_url",
        "authorizationApi": "<sign-url>"
      }
    },
    "description": "Provides an authenticated download link for an asset URL"
  }
}
```

Petición:
```bash
curl -X 'POST' \
  'https://<sign-url>?url=s3%3A%2F%2Fsentinel-2%2Fred.tif' \
  -H 'Authorization: Bearer eyJ...cmQ' \
  -d ''
```

Respuesta:
```json
{
  "signed_url": "<storage-url>/sentinel-2/red.tif?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=36TH83i1lWkOseYhN96Z%2F20240122%2Fit-rom%2Fs3%2Faws4_request&X-Amz-Date=20240122T134237Z&X-Amz-Expires=120&X-Amz-SignedHeaders=host&X-Amz-Signature=2fc41c51..."
}
```

Nota el `X-Amz-Expires=120`: **dos minutos**. Es acceso temporal, sin credenciales de larga
vida. Si `redirect` es `true`, la respuesta trae además un `302` con cabecera `Location`.

**La excepción que evita un malentendido frecuente (D3 §6.1):** los servicios de
procesamiento integrados vía CWL **no usan URLs firmadas**. La plataforma hace *stage-in* y
entrega los datos como **rutas locales dentro del contenedor**:

> *"there is no need for services to generate or manage signed URLs themselves. Instead, the
> platform handles data staging through a stage-in mechanism… avoiding the need for remote
> access logic within the service components."*

Dos caminos distintos para el mismo dato: humanos y clientes externos → URL firmada;
aplicaciones CWL → stage-in. Confundirlos lleva a diagnosticar el problema equivocado.

---

## 5. Laboratorio

**Bloque 5 de la ruta de práctica — 8 horas.** MinIO es tu S3.

1. **Levanta MinIO.** Crea tres buckets que replican la realidad: `productos`, `staging`,
   `frio`.
2. **Políticas.** Crea usuarios y políticas: uno con **solo lectura** sobre un prefijo, otro
   con **escritura** sobre otro. Verifica con `mc` o con el SDK que **el acceso denegado
   realmente se deniega**. No te fíes de haber leído la política.
3. **Versionado.** Actívalo. Sube un objeto, sobrescríbelo, bórralo y **recupéralo**.
   Observa el delete marker.
4. **Ciclo de vida.** Configura una regla que mueva objetos de más de N días a otro
   bucket/clase. Es exactamente el esquema de rotación anual caliente→frío del pliego.
   Acelera el reloj usando N pequeño.
5. **URL prefirmada.** Genera una con expiración corta (60 s). Úsala. Espera a que expire.
   Observa el error exacto. Compara la estructura de la URL con el ejemplo de D3 §6.2.3 del
   §4 de este documento.
6. **Mide.** Sube un objeto grande (≥ 500 MB) y mide la latencia de lecturas parciales con
   rangos de **16 KB y 1 MB** — el patrón que especifica el pliego. Contrasta con los
   **100 ms** contratados. Anota los números.
7. **Audita.** Escribe el procedimiento que responde, en 15 minutos, *"¿quién tiene acceso a
   qué bucket?"* y demuéstralo con evidencia (salida de comandos, no afirmaciones).

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Política con `Resource` mal escrito (bucket vs `bucket/*`) | El 403 más común del mundo S3 y cómo distinguirlo |
| Política sin `ListBucket` pero con `GetObject` | El objeto se descarga si sabes la key, pero no se puede listar |
| URL firmada de un objeto que **no existe** | Se genera igual; falla al usarla. La firma no valida existencia |
| URL firmada expirada | 403, no 401. Diferencia clave frente a un token Keycloak inválido |
| Lifecycle que **borra** en vez de **mover** | Por qué el versionado es tu red de seguridad |
| Multipart abortado sin regla de limpieza | Espacio consumido invisible al listar |
| Credencial rotada sin actualizar el Secret de Kubernetes | Avería 17 del catálogo: el workflow no puede subir el artefacto |

---

## 7. Averías de producción que este bloque entrena

- **Avería 12:** descarga que devuelve 403 — política de bucket o URL firmada expirada.
- **Avería 17:** base de datos / almacenamiento inalcanzable por credencial rotada sin
  actualizar el Secret.
- Parcialmente la **13** (mapa en blanco): si Titiler no puede leer el bucket, el síntoma
  aparece en la visualización pero la causa está aquí.

---

## 8. Árbol de diagnóstico: "la descarga da 403"

1. **¿Es la URL firmada o es la política?** Si el 403 llega **al pedir** la URL firmada, es
   el token (→ [09-keycloak.md](09-keycloak.md)). Si llega **al usar** la URL, es S3.
2. **¿Expiró?** Mira `X-Amz-Date` y `X-Amz-Expires` en la propia URL. Son legibles.
3. **¿Existe el objeto?** `mc stat` / `head-object` con credenciales administrativas.
4. **¿La política cubre el recurso correcto?** ¿`bucket` o `bucket/*`? ¿El prefijo coincide?
5. **¿Hay un `Deny` explícito** en otra política que gane?
6. **¿La credencial que firma tiene permiso sobre ese objeto?** Una URL firmada no da más
   permisos de los que tiene quien la firma.
7. **¿El objeto está en frío?** Un objeto transicionado puede no ser accesible
   directamente y requerir restauración.

---

## 9. Comandos de bolsillo

```bash
# MinIO client
mc alias set lab http://localhost:9000 ACCESS SECRET
mc ls lab/productos --recursive
mc stat lab/productos/sentinel-2/item/red.tif
mc du lab/productos

# Políticas
mc admin policy create lab solo-lectura-s2 politica.json
mc admin policy attach lab solo-lectura-s2 --user usuario1
mc admin policy info lab solo-lectura-s2

# Verificar que un denegado deniega
mc --config-dir ./conf-usuario1 cp lab/productos/otro/x.tif .   # debe fallar

# Versionado y lifecycle
mc version enable lab/productos
mc ilm rule add --expire-days 365 lab/productos
mc ilm rule ls lab/productos

# URL prefirmada
mc share download --expire 60s lab/productos/sentinel-2/red.tif

# Lectura parcial (el patrón del pliego)
curl -o /dev/null -s -w '%{time_total}\n' \
  -r 0-16383 "https://<url-firmada>"      # 16 KB
curl -o /dev/null -s -w '%{time_total}\n' \
  -r 0-1048575 "https://<url-firmada>"    # 1 MB

# Con AWS CLI (funciona contra MinIO con --endpoint-url)
aws --endpoint-url http://localhost:9000 s3api get-bucket-policy --bucket productos
aws --endpoint-url http://localhost:9000 s3api get-bucket-lifecycle-configuration --bucket productos
aws --endpoint-url http://localhost:9000 s3 presign s3://productos/x.tif --expires-in 60
```

---

## 10. Criterio de dominio

- [ ] Escribo una política de bucket que da acceso de solo lectura a un prefijo, a la primera.
- [ ] Explico la diferencia entre `arn:...:bucket` y `arn:...:bucket/*` y qué acción necesita cada uno.
- [ ] Genero, uso y dejo expirar una URL prefirmada, y sé leer sus parámetros.
- [ ] Explico el esquema `signed_url_auth` de D3 §6.2 señalando cada campo en un item real.
- [ ] Sé que las aplicaciones CWL usan stage-in y **no** URLs firmadas, y por qué.
- [ ] Configuro una regla de ciclo de vida hot→cold y verifico que mueve, no borra.
- [ ] Mido latencia de lectura parcial con rangos de 16 KB–1 MB y la contrasto con los 100 ms contratados.
- [ ] **Audito en 15 minutos quién tiene acceso a qué bucket y lo demuestro con evidencia.**

---

## 11. Artefacto que produces

**`runbooks/almacenamiento-objetos.md`**, con:
- El esquema de buckets y prefijos, comentado.
- Las políticas de acceso, comentadas una por una.
- El procedimiento de **verificación de acceso** (cómo comprobar que un denegado deniega).
- El procedimiento de **rotación** caliente→frío y su verificación.
- El procedimiento de **auditoría** de accesos, con los comandos exactos.
- Las mediciones de latencia contra los objetivos del pliego.

**Alimenta:** Producto 2 (runbooks), Producto 3 (validación de desempeño), Producto 6 (SOPs),
Producto 8 (auditoría de uso de procedimientos), e informe mensual (latencias medidas vs.
contratadas).

Este runbook tiene un valor añadido: **documenta un área que el contrato del proveedor no
cubre**. Es la evidencia de que el riesgo está gestionado y no simplemente sin dueño.

---

## 12. Qué preguntar

**Al proveedor:**
1. ¿Qué acceso tendré a la API de S3, por qué vía (VPN o web) y con qué permisos exactos?
2. ¿Qué mecanismo de gestión de identidades y políticas ofrece el servicio? ¿Es compatible con políticas estilo IAM o tiene su propio modelo?
3. ¿Soporta versionado, Object Lock y reglas de ciclo de vida? ¿Con qué limitaciones?
4. ¿Cómo se materializa la transición caliente→frío: clase de almacenamiento, bucket separado, o proceso manual?
5. ¿Cuál es el procedimiento y el tiempo esperado para recuperar desde frío? El pliego habla de 20 TB por solicitud — ¿cómo se solicita?
6. ¿Hay logs de acceso a objetos y con qué retención?
7. ¿Cómo se miden y reportan las latencias de 100 ms / 200 ms comprometidas?

**A ESA / Terradue:**
1. ¿Cómo se gestionan los secretos y la rotación de credenciales S3 entre componentes (ESO, backend de secretos)?
2. ¿Qué servicio implementa el endpoint de URLs firmadas, qué token acepta y cuánto dura la firma?
3. ¿Qué esquema de buckets y prefijos usa el Middleware? ¿Uno por colección, uno por workflow?
4. ¿Quién limpia los objetos huérfanos cuando un item se elimina del catálogo?

---

## 13. Fuentes

**Documentos del proyecto:** D2 §2.5 (supuesto de object storage y tier frío), §3.1.4,
§3.2.4, §3.3.4 (S3 en cada componente), §3.6.2 (buckets por workspace vía Crossplane),
§4.2 (Asset Loading and S3 Storage), §5.1 (extensión Authentication y URLs firmadas), §5.3
(COG + S3 + lecturas parciales). D3 §6 completo (§6.1 overview y la distinción H2M/M2M,
§6.2.1 esquema `signed_url_auth`, §6.2.2 generación, §6.2.3 respuesta y redirección, §6.2.4
flujo de ejemplo, §6.3 ejemplo práctico). D1 §4.1.2 (sistemas de almacenamiento), §4.4
(resumen de especificaciones). Pliego §8.5.6 (almacenamiento), Anexo I. **Perfil ESA §1.1
(la fila "S3 Object Storage — Not covered") y §2.3.4.**

**Documentación oficial:** `min.io/docs` (incluido `mc`), referencia de políticas y
lifecycle de S3, documentación de URLs prefirmadas.

---

## 14. Bitácora / hallazgos

*(Nombres reales de buckets, políticas aplicadas, latencias medidas, incidentes de acceso y
su causa.)*
