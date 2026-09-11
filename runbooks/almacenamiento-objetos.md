# Runbook — Almacenamiento de objetos (S3 / MinIO)

**Área:** Object Storage — *declarada "Not covered" por el contrato del proveedor.*
**Responsable:** Administrador de Middleware.
**Base de laboratorio:** MinIO `RELEASE.2025-09-07` sobre WSL2 Ubuntu 24.04.
**Última verificación:** 2026-09-11.

> Este runbook documenta un área que el contrato del proveedor **no cubre**. Es la evidencia
> de que el riesgo está gestionado y no simplemente sin dueño.

---

## 1. Entorno de laboratorio

| Elemento | Valor |
|---|---|
| Binarios | `~/bin/minio`, `~/bin/mc` (estáticos, sin root) |
| Datos | `~/lab-s3/data` |
| Log | `~/lab-s3/logs/minio.log` |
| API S3 | `http://localhost:9000` |
| Consola web | `http://localhost:9001` |
| Credenciales root | `admin` / `admin12345` (**solo laboratorio**) |

Arranque:
```bash
export PATH="$HOME/bin:$PATH"
MINIO_ROOT_USER=admin MINIO_ROOT_PASSWORD=admin12345 \
  nohup minio server ~/lab-s3/data --address :9000 --console-address :9001 \
  > ~/lab-s3/logs/minio.log 2>&1 &
mc alias set lab http://127.0.0.1:9000 admin admin12345
```

Verificación de salud: `curl -fsS http://127.0.0.1:9000/minio/health/live`

---

## 2. Esquema de buckets y prefijos

| Bucket | Propósito | Versionado | Lifecycle |
|---|---|---|---|
| `productos` | Productos publicados, referenciados por assets STAC | **Enabled** | 3 reglas |
| `staging` | Zona intermedia de ingesta | un-versioned | 1 regla (expira 365 d) |
| `frio` | Destino de la rotación caliente→frío | un-versioned | — |

El prefijo es la unidad de organización **y de política**: `productos/sentinel-2/...`,
`productos/landsat-8/...`. No existen directorios; lo que parece carpeta es prefijo de key.

---

## 3. Políticas de acceso

### 3.1 La regla que evita el 403 más común

| ARN | Para qué sirve |
|---|---|
| `arn:aws:s3:::productos` | El **bucket** — acciones de bucket: `s3:ListBucket` |
| `arn:aws:s3:::productos/*` | Los **objetos** — acciones de objeto: `s3:GetObject` |

Confundirlos produce un 403 que no menciona el ARN. **Verificado en laboratorio:** una
política con `"Resource": ["arn:aws:s3:::productos"]` + `s3:GetObject` deniega toda lectura.

### 3.2 Política de referencia — solo lectura sobre un prefijo

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::productos/sentinel-2/*"] },
    { "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::productos"],
      "Condition": { "StringLike": { "s3:prefix": ["sentinel-2/*"] } } }
  ]
}
```

Aplicación:
```bash
mc admin user add   lab lector lector12345
mc admin policy create lab solo-lectura-s2 politica.json
mc admin policy attach lab solo-lectura-s2 --user lector
```

---

## 4. Procedimiento de verificación de acceso

> **Nunca se da por válida una política por haberla leído.** Se prueba que el denegado deniega.

```bash
mc alias set lector http://127.0.0.1:9000 lector lector12345

mc cat lector/productos/sentinel-2/S2A_demo/red.tif      # [1] debe FUNCIONAR
mc ls  lector/productos/sentinel-2/ --recursive          # [2] debe FUNCIONAR
mc cat lector/productos/landsat-8/L8_demo/red.tif        # [3] debe FALLAR (fuera del prefijo)
echo x | mc pipe lector/productos/sentinel-2/intruso.tif # [4] debe FALLAR (solo lectura)
```

Resultado esperado y **verificado 2026-09-11**: 1 y 2 OK; 3 y 4 → *Insufficient permissions*.
Los cuatro casos deben correrse tras cada cambio de política.

---

## 5. Versionado y recuperación

```bash
mc version enable lab/productos
mc ls --versions lab/productos/<key>
```

Al borrar un objeto versionado se crea un **delete marker** (`DEL`) como versión más reciente:
el objeto desaparece de la lectura normal pero **las versiones anteriores siguen ahí**.

Recuperación — borrar el delete marker:
```bash
mc ls --versions --json lab/productos/<key> > /tmp/vers.json
# extraer el versionId cuyo isDeleteMarker sea true, y luego:
mc rm --version-id "<VERSION_ID_DEL_MARKER>" lab/productos/<key>
```

**Verificado:** objeto sobrescrito (v1→v2), borrado (v3 = delete marker) y recuperado a v2.

El versionado es la red de seguridad frente a una regla de lifecycle mal escrita. Actívalo
**antes** de tocar lifecycle, no después.

---

## 6. Ciclo de vida — rotación caliente → frío

Configuración vigente en `productos` (`mc ilm rule export lab/productos`):

```json
{
  "Rules": [
    { "ID": "...", "Status": "Enabled",
      "NoncurrentVersionExpiration": { "NoncurrentDays": 30 } },
    { "ID": "...", "Status": "Enabled",
      "Filter": { "Prefix": "sentinel-2/" },
      "NoncurrentVersionExpiration": { "NoncurrentDays": 30 } },
    { "ID": "...", "Status": "Enabled",
      "Expiration": { "ExpiredObjectDeleteMarker": true } }
  ]
}
```

### 6.1 Transición a tier frío — requisito previo

Una regla de transición **no puede nombrar un tier que no existe**. Intentar
`--transition-tier FRIO` sin declararlo antes falla con `Invalid storage class`.

```bash
mc ilm tier add minio lab FRIO \
  --endpoint <endpoint-frio> --access-key <ak> --secret-key <sk> \
  --bucket frio --prefix archivo/
mc ilm tier ls lab
mc ilm rule add --transition-days 365 --transition-tier FRIO --prefix "sentinel-2/" lab/productos
```

> **Pendiente de laboratorio:** declarar el tier apuntando el MinIO **contra sí mismo** cuelga
> el comando indefinidamente (se valida contra su propio endpoint). Requiere un segundo
> MinIO o el endpoint real del proveedor. **Pregunta abierta al proveedor:** cómo se
> materializa la transición caliente→frío — ¿clase de almacenamiento, bucket separado o
> proceso manual? (§12 del archivo de estudio, pregunta 4.)

### 6.2 Verificación de que MUEVE y no BORRA

Antes de aplicar en producción, con `--transition-days 0` sobre un prefijo de prueba:
1. `mc ls` en origen → el objeto ya no está en caliente.
2. `mc ls` en destino frío → **el objeto está ahí**.
3. `mc stat` del objeto → la clase de almacenamiento cambió; el contenido se recupera.

Si el paso 2 falla, la regla está borrando. El versionado permite revertir.

---

## 7. URLs prefirmadas

```bash
mc share download --expire 30s lab/productos/sentinel-2/S2A_demo/red.tif
```

⚠️ `mc share` imprime **dos líneas**: la URL cruda y la firmada. Al capturarla en un script
hay que filtrar la que lleva firma, o se obtiene una URL malformada (curl devuelve `HTTP 000`):

```bash
URL=$(mc share download --expire 30s lab/<bucket>/<key> \
      | grep -o 'http[^ ]*X-Amz-Signature[^ ]*' | head -1)
```

Parámetros de la firma (todos legibles sin credenciales):

| Parámetro | Ejemplo | Para qué |
|---|---|---|
| `X-Amz-Algorithm` | `AWS4-HMAC-SHA256` | Algoritmo de firma |
| `X-Amz-Credential` | `admin/20260911/us-east-1/s3/aws4_request` | Quién firma y en qué scope |
| `X-Amz-Date` | `20260911T142347Z` | Momento de la firma |
| `X-Amz-Expires` | `30` | Segundos de validez desde `X-Amz-Date` |
| `X-Amz-SignedHeaders` | `host` | Cabeceras incluidas en la firma |
| `X-Amz-Signature` | `97b99b...` | La firma HMAC |

**Para diagnosticar una expiración no hacen falta credenciales:** `X-Amz-Date + X-Amz-Expires`
se leen en la propia URL.

### 7.1 Los dos 403 — distinguirlos es el trabajo

| Situación | HTTP | `<Code>` | Significado |
|---|---|---|---|
| URL válida y vigente | 200 | — | OK |
| Key alterada / objeto inexistente | **403** | `SignatureDoesNotMatch` | La firma cubre la key; cambiarla la invalida |
| URL vencida | **403** | `AccessDenied` + *Request has expired* | Expiró |
| Token inválido al **pedir** la URL | 401 | — | Es Keycloak, no S3 → [09-keycloak.md](../herramientas/09-keycloak.md) |

Ambos casos de S3 son **403**, no 404 ni 401. El `<Code>` del cuerpo XML es lo que separa una
causa de la otra:
```bash
curl -s "$URL" | grep -oE '<Code>[^<]*</Code>|<Message>[^<]*</Message>'
```

Una URL firmada **se genera aunque el objeto no exista** — la firma no valida existencia — y
**nunca da más permisos de los que tiene quien la firma**.

### 7.2 La excepción CWL

Los servicios de procesamiento integrados vía CWL **no usan URLs firmadas**: la plataforma
hace *stage-in* y entrega rutas locales dentro del contenedor (D3 §6.1). Dos caminos para el
mismo dato — humanos/clientes externos → URL firmada; aplicaciones CWL → stage-in.
Confundirlos lleva a diagnosticar el problema equivocado.

---

## 8. Mediciones de desempeño

Método (objeto de 512 MB, 10 repeticiones por rango):
```bash
curl -s -o /dev/null -r 0-16383   -w '%{time_total}\n' "$URL"   # 16 KB
curl -s -o /dev/null -r 0-1048575 -w '%{time_total}\n' "$URL"   # 1 MB
```

**Medición 2026-09-11 (laboratorio local, WSL2 — NO comparable con producción):**

| Rango | Media medida | Objetivo del pliego |
|---|---|---|
| 16 KB | 1,80 ms | 100 ms lectura |
| 256 KB | 1,78 ms | 100 ms lectura |
| 1 MB | 2,22 ms | 100 ms lectura |
| 512 MB completos | 0,25 s (≈2,1 GB/s) | — |

> Estos números miden loopback sobre disco local: son la **línea base del método**, no del
> servicio contratado. El valor del ejercicio es el procedimiento reproducible. Repetir
> contra el endpoint real por VPN es lo que produce la cifra del informe mensual.

Patrón contratado a verificar en producción: objetos 100 MB–1 GB (máx. 8 GB), lecturas
parciales 16 KB–1 MB, latencias 100 ms lectura / 200 ms escritura.

---

## 9. Procedimiento de auditoría — "¿quién tiene acceso a qué?"

Objetivo: responder con evidencia en **menos de 15 minutos**.

```bash
mc admin user ls lab                       # usuarios y su política
mc admin policy ls lab                     # políticas definidas
mc admin user info lab <usuario>           # política efectiva de uno
mc admin policy info lab <politica>        # el JSON completo
mc anonymous get lab/<bucket>              # ¿acceso anónimo?
mc version info lab/<bucket>               # versionado
mc ilm rule ls lab/<bucket>                # reglas de ciclo de vida
```

**Estado 2026-09-11:**

| Usuario | Política | Alcance efectivo |
|---|---|---|
| `lector` | `solo-lectura-s2` | Lectura de `productos/sentinel-2/*`; listado limitado a ese prefijo |

| Bucket | Versionado | Reglas ILM |
|---|---|---|
| `productos` | enabled | 3 |
| `staging` | un-versioned | 1 |
| `frio` | un-versioned | 0 |

La auditoría se cierra **ejecutando §4** sobre cada usuario listado. Enumerar políticas no es
auditar; auditar es demostrar que el denegado deniega.

---

## 10. Árbol de diagnóstico — "la descarga da 403"

1. **¿Al pedir la URL o al usarla?** Al pedirla → token, es Keycloak. Al usarla → es S3.
2. **¿Expiró?** Lee `X-Amz-Date` + `X-Amz-Expires` en la URL. `<Code>AccessDenied</Code>` +
   *Request has expired*.
3. **¿La firma corresponde a esa key?** `<Code>SignatureDoesNotMatch</Code>` → la URL fue
   alterada o se construyó mal.
4. **¿Existe el objeto?** `mc stat` con credenciales administrativas.
5. **¿La política cubre el recurso correcto?** ¿`bucket` o `bucket/*`? ¿Coincide el prefijo?
6. **¿Hay un `Deny` explícito** en otra política? Deny gana siempre.
7. **¿Quien firma tiene permiso** sobre ese objeto? La firma no otorga permisos extra.
8. **¿Está en frío?** Un objeto transicionado puede requerir restauración previa.

Averías de producción que cubre: **12** (descarga 403), **17** (credencial rotada sin
actualizar el Secret), parcialmente **13** (mapa en blanco por Titiler sin acceso al bucket).

---

## 11. Sabotajes verificados en laboratorio

| Sabotaje | Resultado observado | Fecha |
|---|---|---|
| `Resource` = bucket sin `/*` + `GetObject` | Deniega toda lectura; el 403 no menciona el ARN | 2026-09-11 ✅ |
| Política sin `ListBucket` | *Unable to list folder. Access Denied* | 2026-09-11 ✅ |
| Acceso fuera del prefijo autorizado | *Insufficient permissions* | 2026-09-11 ✅ |
| Escritura con política de solo lectura | *Unable to write to one or more targets* | 2026-09-11 ✅ |
| URL firmada de objeto inexistente | Se genera; falla al usarla con `SignatureDoesNotMatch` | 2026-09-11 ✅ |
| URL firmada expirada | 403 `AccessDenied` — *Request has expired* | 2026-09-11 ✅ |
| Borrado con versionado activo | Delete marker; recuperado borrando el marker | 2026-09-11 ✅ |
| Transición a tier inexistente | `Invalid storage class` | 2026-09-11 ✅ |
| Lifecycle que borra en vez de mover | **Pendiente** — requiere tier frío operativo | — |
| Credencial rotada sin actualizar Secret K8s | **Pendiente** — requiere clúster (avería 17) | — |

---

## 12. Alimenta

Producto 2 (runbooks), Producto 3 (validación de desempeño), Producto 6 (SOPs),
Producto 8 (auditoría de uso de procedimientos) e informe mensual (latencias medidas vs.
contratadas).

---

## 13. Bitácora

**2026-09-11 — Primera ejecución completa del laboratorio (bloque 5).**
- Entorno: WSL2 Ubuntu 24.04, binarios MinIO en `~/bin` sin root (`sudo` pide contraseña).
- Pasos 1–7 ejecutados; 8 de 10 sabotajes verificados.
- Hallazgo: `mc ilm tier add` apuntando al mismo MinIO se cuelga sin timeout.
- Hallazgo: `mc share download` emite dos líneas; capturar la firmada con `grep X-Amz-Signature`.
- Hallazgo: los dos 403 de S3 se distinguen por `<Code>` (`SignatureDoesNotMatch` vs `AccessDenied`).
