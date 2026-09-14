# Chuleta — S3 / MinIO: trabajar con objetos

Comandos practicados y verificados en el laboratorio. Cada uno con **formato** y **ejemplo
real tal como se escribe**.

**Alcance de esta chuleta:** listar, subir, bajar, leer, inspeccionar y borrar objetos.
Políticas, versionado y URLs prefirmadas van en chuletas aparte.

---

## 0. Antes de empezar — cada vez que abres una terminal

| Qué | Comando |
|---|---|
| Entrar a Ubuntu desde Windows | `wsl` |
| Que Linux encuentre `mc` y `minio` | `export PATH="$HOME/bin:$PATH"` |

Para no repetir el `export` nunca más (**una sola vez en la vida**):
```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
```
⚠️ Son **dos** `>>`. Con uno solo (`>`) borrarías el archivo entero.

Si MinIO está apagado:
```bash
MINIO_ROOT_USER=admin MINIO_ROOT_PASSWORD=admin12345 \
  nohup minio server ~/lab-s3/data --address :9000 --console-address :9001 \
  > ~/lab-s3/logs/minio.log 2>&1 &
```

Consola web: **http://localhost:9001** — usuario `admin`, contraseña `admin12345`.

---

## 1. Alias — el apodo del servidor

Un alias guarda dirección + credenciales para no repetirlas en cada comando.

**Formato**
```bash
mc alias set <apodo> <url> <usuario> <contraseña>
```

**Ejemplo real**
```bash
mc alias set lab http://127.0.0.1:9000 admin admin12345
```

Ya está guardado. Solo hace falta si ves el error `Unable to find alias lab`.

| Comando | Para qué |
|---|---|
| `mc alias list` | Ver los alias configurados |
| `mc alias remove lab` | Borrar uno |

---

## 2. Listar

**Formato**
```bash
mc ls <alias>                          # buckets
mc ls <alias>/<bucket>                 # un nivel (dibuja "carpetas" que no existen)
mc ls --recursive <alias>/<bucket>     # keys completas — la realidad
mc ls <alias>/<bucket>/<prefijo>/      # solo lo que empieza con ese prefijo
```

**Ejemplos reales**
```bash
mc ls lab
mc ls lab/productos
mc ls --recursive lab/productos
mc ls lab/productos/sentinel-2/S2A_demo/
```

> ⚠️ **Un listado vacío NO es un error.** Un prefijo que no existe devuelve lista vacía y
> exit limpio: preguntaste "¿qué keys empiezan con este texto?" y la respuesta es "ninguna".
> **S3 distingue mayúsculas y minúsculas:** `S2A_demo`, `s2a_demo` y `S2ADEMO` son tres
> prefijos distintos. Si sale vacío, **sube un nivel** y mira cómo se llama de verdad.

---

## 3. Subir

**Formato**
```bash
mc cp <archivo-local> <alias>/<bucket>/<key>
```

**Ejemplo real**
```bash
echo "mi primera banda" > /tmp/prueba.tif
mc cp /tmp/prueba.tif lab/productos/sentinel-2/S2A_demo/prueba.tif
```

**No hay que crear carpetas antes.** Esto funciona tal cual:
```bash
mc cp /tmp/prueba.tif lab/productos/inventado/carpeta/que/no/existia/archivo.tif
```
No creaste seis carpetas: creaste **un objeto con una key larga**.

### Subir declarando el media type

**Formato**
```bash
mc cp --attr "Content-Type=<tipo>" <archivo-local> <alias>/<bucket>/<key>
```

**Ejemplo real**
```bash
mc cp --attr "Content-Type=image/tiff-COG-FALSO" /tmp/mentira.tif \
  lab/productos/sentinel-2/S2A_demo/mentira.tif
```

> ⚠️ **`mc --attr` parte el valor por `;`** — usa el punto y coma como separador interno de
> atributos. Un media type de COG completo
> (`image/tiff; application=geotiff; profile=cloud-optimized`) **llega truncado a
> `image/tiff`**. `curl -F` hace lo mismo. Ver [preguntas-para-esa.md](../preguntas-para-esa.md), pregunta S3-07.

---

## 4. Bajar

**Formato**
```bash
mc cp <alias>/<bucket>/<key> <ruta-local>
```

**Ejemplo real**
```bash
mc cp lab/productos/sentinel-2/S2A_demo/prueba.tif /tmp/bajado.tif
```

`mc cp` funciona en los dos sentidos. Solo cambia el orden de los argumentos.

---

## 5. Leer sin descargar a disco

**Formato**
```bash
mc cat <alias>/<bucket>/<key>
```

**Ejemplo real**
```bash
mc cat lab/productos/sentinel-2/S2A_demo/prueba.tif
```

Útil para archivos de texto, JSON y para encadenar con tuberías.
**Con un archivo binario grande llenará la pantalla de basura** — usa `mc stat`.

---

## 6. Inspeccionar metadatos

**Formato**
```bash
mc stat <alias>/<bucket>/<key>
mc stat --json <alias>/<bucket>/<key>      # salida procesable por script
```

**Ejemplo real**
```bash
mc stat lab/productos/sentinel-2/S2A_demo/prueba.tif
```

**Salida real y qué significa cada campo:**
```
Name      : prueba.tif
Date      : 2026-09-11 10:02:09 EST
Size      : 17 B
ETag      : 1c8b1c0e0ec169c5f86f63a0dec68984
VersionID : 19a3c73a-b8d2-4910-a96e-6993adce83d9
Type      : file
Metadata  :
  Content-Type: image/tiff
```

| Campo | Qué es |
|---|---|
| `Name` | Solo el final si diste prefijo. **La key real es la ruta completa.** |
| `Size` | Bytes |
| `ETag` | Huella del contenido. En objetos de una parte = MD5 |
| `VersionID` | Aparece solo si el bucket tiene versionado activo |
| `Type: file` | Significa "es un objeto, no un prefijo". **No es el media type** |
| `Content-Type` | **Este sí** es el media type |

> ⚠️ **El media type es una declaración, no un hecho.** Un archivo con el texto
> "mi primera banda" quedó etiquetado `image/tiff` porque `mc` **adivinó por la extensión**.
> S3 no abre el archivo ni valida la cabecera. Los bytes y la etiqueta son independientes.

`mc stat` **no descarga el objeto** — el servidor ya tiene los metadatos calculados.

---

## 7. Verificar integridad (ETag)

**Formato**
```bash
md5sum <archivo-local>                          # hash de un archivo local
mc cat <alias>/<bucket>/<key> | md5sum          # hash del objeto remoto
mc stat <alias>/<bucket>/<key>                  # el ETag que guarda el servidor
```

**Ejemplo real**
```bash
mc cat lab/productos/sentinel-2/S2A_demo/prueba.tif | md5sum
# 1c8b1c0e0ec169c5f86f63a0dec68984  -
```
El `-` final es el "nombre del archivo": `md5sum` lo pone cuando el contenido llega por
tubería. Es informativo, no un error.

**Comparación automática:**
```bash
LOCAL=$(md5sum /tmp/prueba.tif | cut -d' ' -f1)
REMOTO=$(mc stat --json lab/productos/sentinel-2/S2A_demo/prueba.tif \
         | python3 -c "import sys,json; print(json.load(sys.stdin)['etag'])")
echo "local:  $LOCAL"
echo "remoto: $REMOTO"
if [ "$LOCAL" = "$REMOTO" ]; then echo "COINCIDEN"; else echo "DIFIEREN"; fi
```

### Coste — elegir bien

| Comando | Transfiere | Cuándo usarlo |
|---|---|---|
| `mc stat` | **Nada** | Casi siempre. Comparar contra un valor ya conocido |
| `mc cat \| md5sum` | El objeto **completo** | Solo contra un archivo local que tienes ahora |

En un producto real de 8 GB, `mc cat | md5sum` **descarga 8 GB**.

### ⚠️ La trampa del multipart

| ETag | Qué es | ¿`md5sum` coincide? |
|---|---|---|
| `1c8b1c0e...` (32 hex) | MD5 del contenido | ✅ Sí |
| `a3f5...-4` (**con guion**) | Hash de hashes, 4 partes | ❌ **No** |

**El guion es la señal.** Objetos grandes se suben en partes; S3 hashea cada parte, concatena,
vuelve a hashear y añade `-<nº de partes>`. Si `md5sum` no coincide en un objeto con guion,
**eso no es corrupción**. Reproducirlo exige conocer el tamaño de parte exacto usado al subir.

**Dos usos distintos:**
1. **¿Cambió algo?** → ETag siempre sirve, y es barato. Guardarlo en la ingesta, reconsultar
   después; si cambió, alguien sobrescribió.
2. **¿Llegó íntegro?** → el ETag solo vale en objetos de una sola parte. Para productos
   grandes hace falta un SHA-256 guardado en la ingesta. Ver pregunta S3-06.

---

## 8. Borrar

**Formato**
```bash
mc rm <alias>/<bucket>/<key>
mc rm --recursive --force <alias>/<bucket>/<prefijo>/
```

**Ejemplo real**
```bash
mc rm lab/productos/sentinel-2/S2A_demo/mentira.tif
```

> ⚠️ `--recursive --force` borra todo bajo el prefijo **sin preguntar**. En un bucket con
> versionado el objeto no desaparece: se crea un *delete marker* y las versiones anteriores
> quedan debajo (chuleta de versionado).

---

## 9. Espacio ocupado

**Formato**
```bash
mc du <alias>/<bucket>
mc du --recursive <alias>/<bucket>
```

**Ejemplo real**
```bash
mc du lab/productos
```

---

## 10. Trucos de terminal

**Tab NO autocompleta rutas de `mc`.** Bash solo conoce el sistema de archivos local;
`lab/productos/...` vive en el servidor y haría falta una petición de red.

Lo que sí funciona:

| Técnica | Cómo |
|---|---|
| **Copiar y pegar** del listado anterior | Seleccionar con el ratón, clic derecho pega (o `Ctrl+Shift+V`) |
| **Flecha ↑** | Trae el comando anterior; editar con ← → |
| **Variable de ruta** | La más útil ⬇ |

**Variable de ruta** — escribes la ruta larga una vez:
```bash
P=lab/productos/sentinel-2/S2A_demo

mc ls   $P/
mc cat  $P/prueba.tif
mc stat $P/prueba.tif
```
Sin espacios alrededor del `=`. Comprobar con `echo $P`. Se pierde al cerrar la terminal.

---

## 11. Conceptos que no son comandos pero evitan errores

**No existen los directorios.** Solo hay:

| Concepto | Qué es | Ejemplo |
|---|---|---|
| **Bucket** | El contenedor | `productos` |
| **Key** | El nombre completo del objeto, **una sola cadena** | `sentinel-2/S2A_demo/red.tif` |
| **Prefijo** | El comienzo de una key | `sentinel-2/` |

Las `/` son caracteres del nombre, como cualquier letra. `mc ls` dibuja carpetas por
comodidad del cliente; el servidor solo tiene keys largas.

**Por qué importa:** las políticas de permisos se escriben **por prefijo**. "Puede leer
`sentinel-2/*`" = "puede leer todo objeto cuya key empiece con `sentinel-2/`".

| Sistema de archivos normal | S3 |
|---|---|
| `ls /carpeta_inexistente` → error | prefijo inexistente → **lista vacía, sin error** |
| Hay que crear carpetas antes de escribir | Se escribe la key directamente |

---

## 12. Referencia rápida

| Quiero… | Comando |
|---|---|
| Ver buckets | `mc ls lab` |
| Ver todo un bucket | `mc ls --recursive lab/productos` |
| Subir | `mc cp /tmp/x.tif lab/productos/pre/x.tif` |
| Bajar | `mc cp lab/productos/pre/x.tif /tmp/x.tif` |
| Leer contenido | `mc cat lab/productos/pre/x.tif` |
| Ver metadatos y ETag | `mc stat lab/productos/pre/x.tif` |
| Verificar integridad | `mc cat lab/productos/pre/x.tif \| md5sum` |
| Borrar | `mc rm lab/productos/pre/x.tif` |
| Espacio ocupado | `mc du lab/productos` |
| Salud del servidor | `curl -fsS http://127.0.0.1:9000/minio/health/live` |

---

*Practicado y verificado el 2026-09-11. Bitácora completa en
[bitacora-aprendizaje.md](../bitacora-aprendizaje.md).*
