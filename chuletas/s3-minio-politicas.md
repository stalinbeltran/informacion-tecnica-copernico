# Chuleta — S3 / MinIO: usuarios y políticas de acceso

Comandos practicados y verificados en el laboratorio. **Formato** + **ejemplo real**.

> Esta es el área que el contrato del proveedor marca como **Not covered**: buckets,
> políticas, retención y auditoría son responsabilidad del Administrador de Middleware.

---

## 1. Anatomía de una política

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::productos/sentinel-2/*"]
    }
  ]
}
```

| Campo | Qué es |
|---|---|
| `Version` | **Siempre** `"2012-10-17"`. Es la versión del *lenguaje* de políticas, no de la tuya. Se copia tal cual |
| `Statement` | **Lista** de permisos. Puede tener varios bloques |
| `Effect` | `Allow` o `Deny`. **Un `Deny` gana siempre sobre cualquier `Allow`** |
| `Action` | Qué operaciones se permiten |
| `Resource` | Sobre qué recursos (en formato ARN) |
| `Condition` | *(opcional)* Restricción extra |

Lo único que cambia entre políticas es `Action` y `Resource`. El resto es plantilla.

---

## 2. ARN — Amazon Resource Name

Formato de seis campos:
```
arn : aws : s3 : <región> : <cuenta> : <recurso>
```

En S3 **región y cuenta van vacías** → de ahí el `:::`. No es un error de tipeo: los nombres
de bucket son globalmente únicos y no necesitan desambiguación. MinIO usa `arn:aws:...` por
compatibilidad S3, aunque no tenga relación con Amazon.

### ⚠️ La distinción que causa el 403 nº 1

| ARN | Nombra | Acciones que acepta |
|---|---|---|
| `arn:aws:s3:::productos` | **El bucket** | `s3:ListBucket` |
| `arn:aws:s3:::productos/*` | **Los objetos dentro** | `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` |

**Listar y descargar son operaciones sobre cosas distintas.** Un permiso no implica el otro:
- `GetObject` sin `ListBucket` → descargas si conoces la key exacta, pero no ves qué hay
- `ListBucket` sin `GetObject` → ves los nombres pero no puedes abrir nada
- `GetObject` sobre el bucket sin `/*` → **no funciona nada**

### Alcance del patrón

| ARN | Cubre |
|---|---|
| `arn:aws:s3:::productos/*` | Todos los objetos del bucket |
| `arn:aws:s3:::productos/sentinel-2/*` | Solo los que empiezan con `sentinel-2/` |
| `arn:aws:s3:::productos/sentinel-2/S2A_demo/red.tif` | Un objeto exacto |

Recuerda: **no son carpetas, son prefijos.** `productos/sentinel-2/*` = "toda key que empiece
con `sentinel-2/`".

---

## 3. Acciones más usadas

| Acción | Qué permite | ARN que necesita |
|---|---|---|
| `s3:GetObject` | Descargar / leer un objeto | `bucket/*` |
| `s3:PutObject` | Subir / sobrescribir | `bucket/*` |
| `s3:DeleteObject` | Borrar | `bucket/*` |
| `s3:ListBucket` | Listar el contenido | `bucket` (**sin** `/*`) |
| `s3:GetBucketLocation` | Consultar la región del bucket | `bucket` |
| `s3:AbortMultipartUpload` | Cancelar subidas incompletas | `bucket/*` |

---

## 4. Crear un usuario y aplicarle una política

**Formato**
```bash
mc admin user add     <alias-admin> <usuario> <contraseña>
mc admin policy create <alias-admin> <nombre-politica> <archivo.json>
mc admin policy attach <alias-admin> <nombre-politica> --user <usuario>
```

**Ejemplo real**
```bash
mc admin user add lab analista analista12345
mc admin policy create lab lectura-s2 buena.json
mc admin policy attach lab lectura-s2 --user analista
```

Crear y asignar son pasos **separados**: una misma política puede ir a varios usuarios.

| Comando | Para qué |
|---|---|
| `mc admin user ls lab` | Listar usuarios |
| `mc admin user info lab analista` | Ver la política efectiva de uno |
| `mc admin policy ls lab` | Listar políticas |
| `mc admin policy info lab lectura-s2` | Ver el JSON de una política |
| `mc admin policy detach lab <pol> --user <user>` | Quitar una política |
| `mc admin user remove lab analista` | Borrar usuario |

> ⚠️ **Si no haces `detach` de la anterior, los permisos se SUMAN.** Al cambiar una política
> por otra hay que quitar la vieja explícitamente.

---

## 5. Probar una política — cambiar de identidad

Un alias por identidad. **Cambiar de alias es cambiar de usuario.**

```bash
mc alias set analista http://127.0.0.1:9000 analista analista12345
```

| Alias | Identidad |
|---|---|
| `lab` | admin — lo ve todo |
| `analista` | usuario limitado — solo lo que su política permite |

---

## 6. Política de referencia: solo lectura sobre un prefijo

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
      "Condition": {
        "StringLike": { "s3:prefix": ["sentinel-2/*"] }
      }
    }
  ]
}
```

**Por qué dos bloques:** descargar y listar actúan sobre recursos distintos (objetos vs.
bucket), así que necesitan ARNs distintos.

**Por qué el `Condition`:** sin él, el usuario podría listar **todo** el bucket, `landsat-8/`
incluido. `s3:prefix` es el prefijo **que el usuario pide al listar**, no la key de un objeto.

---

## 7. ⚠️ La barra final cambia el resultado

**Verificado en laboratorio** — misma política, mismo usuario, un carácter de diferencia:

```bash
mc ls analista/productos/sentinel-2      # → Access Denied
mc ls analista/productos/sentinel-2/     # → funciona
```

| Lo que pides | Lo que `mc` envía | ¿Encaja con `sentinel-2/*`? |
|---|---|---|
| `sentinel-2/` | `prefix=sentinel-2/` | ✅ Sí (`*` admite cadena vacía) |
| `sentinel-2` | `prefix=sentinel-2` | ❌ No — el patrón exige la barra |

**Consecuencia operativa:** un usuario jura que no puede listar, tú pruebas con barra y te
funciona. Los dos veis cosas distintas y ninguno miente.

Para cubrir ambos: `"s3:prefix": ["sentinel-2/*", "sentinel-2"]`. Pero cuanto más permisiva
la condición, menos aísla — **es decisión de diseño, no un arreglo automático**.

---

## 8. Procedimiento de verificación — las CUATRO pruebas

> **Nunca se da por válida una política por haberla leído.**
> Comprobar solo que lo permitido funciona es **media verificación**: una política que
> permite de más también pasa esa prueba. Lo que demuestra que está bien escrita es
> **que lo prohibido falle**.

```bash
# [1] Leer lo permitido — debe FUNCIONAR
mc cat analista/productos/sentinel-2/S2A_demo/prueba.tif

# [2] Listar lo permitido — debe FUNCIONAR
mc ls analista/productos/sentinel-2/

# [3] Leer fuera del prefijo — debe FALLAR
mc cat analista/productos/landsat-8/L8_demo/red.tif

# [4] Escribir — debe FALLAR
echo prueba | mc pipe analista/productos/sentinel-2/intruso.tif
```

Se repiten **cada vez** que se toca una política.

---

## 9. ⚠️ Qué NO te dice un 403

**El mensaje es siempre el mismo:**
```
mc: <ERROR> Unable to read from ... Insufficient permissions to access this path ...
mc: <ERROR> Unable to list folder. Access Denied.
```

No dice qué ARN, qué acción faltó, ni qué política miró. **Cuatro causas distintas producen
el mismo mensaje:**

1. ARN mal escrito (`bucket` en vez de `bucket/*`)
2. La acción no está en la política
3. Un `Deny` explícito en otra política gana
4. El usuario no tiene política asignada

**Por eso hay que saber la distinción bucket/objetos de memoria.**

### El 403 tampoco revela si el objeto existe

**Verificado en laboratorio** — tres keys en un prefijo denegado:

| Key | ¿Existe? | Respuesta |
|---|---|---|
| `red.tif` | **Sí** | *Insufficient permissions* |
| `red2.tif` | No | *Insufficient permissions* |
| `red2xxxx.tif` | No | *Insufficient permissions* |

**Idéntica.** Es **deliberado**: si devolviera 404 para lo inexistente y 403 para lo
existente, cualquiera sin acceso podría mapear el bucket probando nombres y observando el
error (*enumeración*). Ocultarlo es diseño de seguridad correcto.

**Consecuencia:** desde la cuenta del usuario **no se puede saber si el objeto existe**.
Hay que comprobarlo con credenciales administrativas:
```bash
mc stat lab/productos/landsat-8/L8_demo/red2.tif
```
Por eso "¿existe el objeto?" es un **paso separado** del árbol de diagnóstico, y no se salta.

---

## 10. Auditoría — "¿quién tiene acceso a qué?"

Objetivo del criterio de dominio: responder **en menos de 15 minutos, con evidencia**.

```bash
mc admin user ls lab                    # usuarios y su política
mc admin policy ls lab                  # políticas definidas
mc admin user info lab <usuario>        # política efectiva de uno
mc admin policy info lab <politica>     # el JSON completo
mc anonymous get lab/<bucket>           # ¿hay acceso anónimo?
```

**La auditoría no termina enumerando políticas.** Se cierra ejecutando las cuatro pruebas
(§8) sobre cada usuario listado. Enumerar es describir; auditar es **demostrar que el
denegado deniega**.

---

## 11. Referencia rápida

| Quiero… | Comando |
|---|---|
| Crear usuario | `mc admin user add lab analista analista12345` |
| Registrar política | `mc admin policy create lab lectura-s2 buena.json` |
| Asignar | `mc admin policy attach lab lectura-s2 --user analista` |
| Quitar | `mc admin policy detach lab lectura-s2 --user analista` |
| Ver política de un usuario | `mc admin user info lab analista` |
| Ver el JSON de una política | `mc admin policy info lab lectura-s2` |
| Probar como ese usuario | `mc alias set analista http://127.0.0.1:9000 analista analista12345` |
| Listar usuarios | `mc admin user ls lab` |
| Listar políticas | `mc admin policy ls lab` |

---

*Practicado y verificado el 2026-09-11. Primer criterio de dominio del archivo
[06-s3-minio.md](../herramientas/06-s3-minio.md) cumplido.
Bitácora en [bitacora-aprendizaje.md](../bitacora-aprendizaje.md).*
