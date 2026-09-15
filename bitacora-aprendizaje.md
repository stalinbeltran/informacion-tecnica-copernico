# Bitácora de aprendizaje — Administrador de Middleware CopernicusLAC

**Titular:** Stalin Beltrán
**Naturaleza de este archivo:** registro **append-only**. Se añaden entradas al final.
**Nunca se edita ni se reordena lo ya escrito** — un error registrado se corrige con una
entrada nueva que lo enmienda, no borrando la anterior.

**Formato de cada entrada:**

```
## [fecha] — [bloque] — [título]
**Concepto enseñado:** ...
**Comandos introducidos:** ...
**Resultado del alumno:** ...
**Hallazgo / error:** ...
```

---

## 2026-09-11 — S3/MinIO — Montaje del laboratorio

**Concepto enseñado:** ninguno (preparación de entorno).

**Qué se montó:**
- WSL2 Ubuntu 24.04 (ya existía en la máquina).
- Binarios `minio` (RELEASE.2025-09-07) y `mc` (RELEASE.2025-08-13) descargados en `~/bin`.
  Se eligieron binarios estáticos sin root porque `sudo` pide contraseña en esta máquina.
- Servidor en `http://localhost:9000`, consola web en `http://localhost:9001`.
- Credenciales de laboratorio: `admin` / `admin12345` (**solo local, sin datos reales**).
- Buckets creados: `productos`, `staging`, `frio`.

**Resultado del alumno:** no aplica — lo ejecutó Claude.

**Hallazgo metodológico (importante):** esta primera sesión se hizo mal desde el punto de
vista del aprendizaje. Claude ejecutó los siete pasos del laboratorio y Stalin los leyó.
El resultado fue un runbook correcto y cero práctica. **Corrección acordada:** a partir de
aquí Claude da instrucciones explícitas y completas (comandos, formatos, explicación previa)
y Stalin ejecuta. Claude no ejecuta los ejercicios del alumno.

**Segunda corrección acordada (misma sesión):** Stalin parte de cero en S3/MinIO y no hay
tiempo para investigación autónoma. No se le pide buscar en internet ni deducir sintaxis.
Se le entrega la información necesaria para avanzar. Si quiere investigar por su cuenta,
lo avisa él.

---

## 2026-09-11 — S3/MinIO — Sesión 1: modelo de objetos (bucket, key, prefijo)

**Concepto enseñado:**

1. **En S3 no existen los directorios.** Solo hay dos cosas: el **bucket** (el contenedor) y
   la **key** (el nombre completo del objeto, una sola cadena de texto).
   En `productos/landsat-8/L8_demo/red.tif`, el bucket es `productos` y la key completa es
   `landsat-8/L8_demo/red.tif`. Las barras `/` son caracteres del nombre, no separadores de
   carpeta.
2. **Prefijo** = el comienzo de una key. `landsat-8/` es un prefijo, no una carpeta.
   `mc ls` sin `--recursive` dibuja las carpetas por comodidad del cliente; el servidor solo
   tiene keys largas.
3. **Por qué importa:** las políticas de permisos se escriben por prefijo. "Puede leer
   `sentinel-2/*`" significa "puede leer todo objeto cuya key empiece con `sentinel-2/`".
   Pensar en carpetas impide entender cómo se escribe una política.
4. **Alias** (`lab`): apodo guardado que contiene dirección del servidor + credenciales, para
   no repetirlas en cada comando.
5. **Metadatos** de `mc stat`: `Name` (la key), `Size`, `ETag` (huella del contenido — cambia
   si el contenido cambia, sirve para detectar corrupción) y `Type` (media type; aquí
   aparecerá `image/tiff; application=geotiff; profile=cloud-optimized` para declarar un COG).

**Comandos introducidos:**

| Comando | Para qué |
|---|---|
| `wsl` | Entrar a Ubuntu desde Windows |
| `export PATH="$HOME/bin:$PATH"` | Encontrar `mc` y `minio`. Una vez por sesión. |
| `mc alias set lab http://127.0.0.1:9000 admin admin12345` | Recrear el alias si se pierde |
| `mc ls lab` | Listar buckets |
| `mc ls lab/productos` | Listar con la ilusión de carpetas |
| `mc ls --recursive lab/productos` | Listar keys completas (la realidad) |
| `mc cp <origen> lab/<bucket>/<key>` | Subir un objeto |
| `mc cat lab/<bucket>/<key>` | Leer contenido sin descargar |
| `mc stat lab/<bucket>/<key>` | Ver metadatos |
| `mc rm lab/<bucket>/<key>` | Borrar un objeto |

**Ejercicios propuestos:**
- Paso 1: listar con y sin `--recursive` y comparar.
- Paso 2: crear `/tmp/prueba.tif`, subirlo, leerlo con `cat`, inspeccionarlo con `stat`.
- Paso 3: subir a una ruta de seis niveles inexistente (`inventado/carpeta/que/no/existia/`)
  **sin crear nada antes** — demuestra que no hay directorios que crear. Luego borrarlo.

**Resultado del alumno:** pendiente de ejecución.

**Nota de seguridad dada al alumno:** la contraseña aparece en texto plano en la línea de
comandos. Es aceptable en un laboratorio local aislado sin datos reales; en producción nunca
se hace. El manejo real (Secrets de Kubernetes, External Secrets Operator) se ve en el bloque
de Kubernetes.

---

## 2026-09-11 — S3/MinIO — Sesión 1: resultado del alumno

**Resultado del alumno:** ejecutado. `mc cp` funcionó a la primera; el objeto
`sentinel-2/S2A_demo/prueba.tif` (17 B) quedó subido a las 10:02.

**Error cometido y su valor didáctico:**

Stalin ejecutó `mc ls lab/productos/sentinel-2/S2Ademo/` y reportó "no sale nada".
El prefijo real es `S2A_demo` — **faltó el guion bajo**.

Lo relevante no es el typo sino la respuesta de S3: **un prefijo inexistente devuelve lista
vacía y exit limpio, sin error**. Es coherente con el modelo — la pregunta no fue "¿existe
esta carpeta?" sino "¿qué keys empiezan con este texto?", y la respuesta correcta es
"ninguna". No hay carpetas que puedan faltar.

| Sistema de archivos normal | S3 |
|---|---|
| `ls /carpeta_inexistente` → error | prefijo inexistente → lista vacía, sin error |
| Hay que crear carpetas antes de escribir | Se escribe la key directamente |

Es el paso 3 visto al revés: escribir en seis niveles "inexistentes" funciona porque no hay
nada que crear; leer un prefijo inexistente sale vacío porque no hay nada que falte.

**Consecuencia operativa:** cuando un usuario reporte "mis datos desaparecieron" y el listado
salga vacío, **vacío no significa borrado**. Puede ser prefijo mal escrito o diferencia de
mayúsculas — S3 distingue: `S2A_demo`, `s2a_demo` y `S2ADEMO` son tres prefijos distintos.

**Reflejo correcto que el alumno aplicó solo:** ante un listado vacío, subió un nivel
(`mc ls lab/productos/sentinel-2/`) para ver el nombre real. Ese es el procedimiento.

**Diagnóstico fallido de Claude (se registra por honestidad del log):** Claude supuso primero
que la causa era el `PATH` perdido al abrir terminal nueva. Era falso — `mc cp` había
funcionado en la misma sesión, luego `mc` estaba disponible. La evidencia de la propia
terminal del alumno descartó la hipótesis.

**Técnica dada:** usar Tab para autocompletar prefijos, o copiar/pegar del listado anterior
en vez de teclear.

**Nota lateral:** el alumno hizo `cd ..` hasta `/`. No afecta a `mc`, que habla con el
servidor por red; el directorio local solo importa para rutas locales como `/tmp/prueba.tif`.

---

## 2026-09-11 — S3/MinIO — Sesión 1 (cont.): metadatos, ETag y media type

**Concepto enseñado — campos de `mc stat`:**

| Campo | Qué es | Para qué sirve en el puesto |
|---|---|---|
| `Name` | `mc` muestra solo el final si diste prefijo; la key real es la ruta completa | — |
| `Size` | Bytes | — |
| `ETag` | Hash del contenido. Mismo contenido → mismo ETag; cambia un byte y cambia entero | **Verificar integridad sin descargar.** Comparar el ETag del objeto con el registrado en la ingesta. Es la palabra *integridad* que el perfil ESA asigna al rol |
| `Type: file` | Solo indica "objeto, no prefijo" — **no** es el media type | — |
| `Content-Type` | El media type real | Lo que el asset STAC declara |
| `VersionID` | Aparece porque `productos` tiene versionado activo | Red de seguridad ante borrados y lifecycle mal escrito |

**El media type es una declaración, no un hecho.** El archivo del alumno contenía el texto
"mi primera banda" y quedó etiquetado `image/tiff` porque `mc` **adivinó por la extensión**.
S3 no abre el archivo ni valida la cabecera. Los bytes y la etiqueta son cosas independientes.

---

## 2026-09-11 — S3/MinIO — Experimento propuesto por el alumno: falsificar un media type COG

**Iniciativa del alumno.** Stalin preguntó cómo crear un archivo falso etiquetado como
`profile=cloud-optimized`. Es el experimento correcto: reproduce la avería 13 en 30 segundos.

**Comando dado por Claude — INCORRECTO:**
```bash
mc cp --attr "Content-Type=image/tiff; application=geotiff; profile=cloud-optimized" ...
```

**Resultado real:** quedó guardado `image/tiff` a secas. Verificado con `mc stat --json`:
los parámetros `application=geotiff` y `profile=cloud-optimized` **no llegaron al servidor**.

**Causa:** `mc` usa `;` como **separador interno** del valor de `--attr` (permite
`--attr "A=1;B=2"`). Partió el valor en tres y descartó los dos fragmentos sin formato
`clave=valor` válido. No es problema de S3 ni de comillas de bash.

**Vías correctas:**
1. URL de subida firmada + `curl -H "Content-Type: image/tiff; application=geotiff; profile=cloud-optimized"`
   — el `;` dentro de una cabecera HTTP no se parte.
   ```bash
   mc share upload --expire 5m lab/<bucket>/<key>
   # copiar el curl que imprime y añadirle la cabecera -H
   ```
2. `aws s3api put-object --content-type "..."` (requiere AWS CLI, no instalado).
3. Prueba equivalente sin `;`: `--attr "Content-Type=image/tiff-cloud-optimized-FALSO"`
   — demuestra que S3 acepta **cualquier** etiqueta, incluso un tipo MIME inexistente.

**Hallazgo inesperado y más valioso que el experimento original:**

El fallo produjo el caso **inverso** al buscado, que es igual de real en producción:

| Caso | Etiqueta | Realidad | Síntoma |
|---|---|---|---|
| Buscado | dice COG | no lo es | Titiler falla, mapa en blanco (avería 13) |
| **Provocado por el error** | dice `image/tiff` a secas | **sí es COG** | Nada falla; todo se descarga entero y va lentísimo. Nadie sospecha |

Un workflow de ingesta con el `--attr` mal escrito produce exactamente esto: COGs legítimos
que el catálogo no anuncia como cloud-optimized, luego ningún cliente intenta lectura parcial.
**Avería silenciosa** — no hay error, solo desempeño degradado sin causa aparente.

**Pregunta ganada para el proveedor / Terradue:** ¿quién valida que un objeto etiquetado como
COG lo sea realmente, y que un COG real se etiquete completo? ¿El workflow de ingesta?
¿Nadie? Si es "nadie", es un hallazgo.

**Resultado del alumno:** ejecutó el comando y reportó la discrepancia. El reporte fue
correcto y destapó el error de Claude.

**Pendiente:** rehacer el experimento por la vía 1 o 3.

---

## 2026-09-11 — S3/MinIO — Cierre del experimento de media type: dos fallos apilados

**Intento por la vía de `mc share upload` + `curl`. Falló por dos causas distintas.**

**Fallo 1 — curl también parte por `;`:**
```
Warning: skip unknown form field: application=geotiff
Warning: skip unknown form field: profile=cloud-optimized
```
`curl -F` trata el `;` como separador de campos, igual que `mc --attr`. Las comillas simples
no lo evitan: el corte lo hace curl al interpretar su propio argumento.

**Patrón detectado — no es casualidad:** dos herramientas independientes, en la misma sesión,
truncaron el mismo media type dejando `image/tiff` a secas. **El `;` dentro de un media type
es un punto de fallo recurrente en toda la cadena de herramientas.** Esto explica por qué en
producción los media types de COG llegan truncados con tanta facilidad.

**Fallo 2 — `SignatureDoesNotMatch`:**
La política firmada por `mc share upload` contiene una **lista cerrada de campos**
(`bucket`, `key`, `x-amz-date`, `x-amz-algorithm`, `x-amz-credential`). Añadir el campo
`Content-Type` hizo que la petición dejara de coincidir con lo firmado.

**Conexión importante:** es el **mismo código de error** que se vio al alterar la key de una
URL firmada de descarga. Distinta causa, mismo `SignatureDoesNotMatch`. Segunda forma
conocida de provocarlo:

| Causa | Código |
|---|---|
| Key alterada en una URL firmada | `SignatureDoesNotMatch` |
| **Campo añadido a una petición POST firmada** | `SignatureDoesNotMatch` |
| URL vencida | `AccessDenied` + *Request has expired* |

No dijo "expiró" — la política seguía vigente. Los dos 403 siguen siendo distinguibles.

**Decisión:** se abandona esta vía. Continuar exigiría firmar a mano con AWS Signature V4
(criptografía, media hora, nada que enseñe sobre S3). El experimento ya rindió.

**Balance de lo aprendido — más de lo que buscaba el experimento original:**
1. La etiqueta es una declaración, no un hecho (`prueba.tif` con texto dentro → `image/tiff`
   porque `mc` adivinó por la extensión).
2. **El media type se trunca con facilidad alarmante** en la cadena de herramientas → avería
   silenciosa: COG real anunciado como TIFF simple, nadie intenta lectura parcial, todo se
   descarga entero, sistema lento sin causa aparente.
3. Segunda forma de provocar `SignatureDoesNotMatch`.

**Errores de Claude en esta secuencia (registrados por honestidad del log):**
- Dio `mc cp --attr` con `;`, que `mc` parte internamente.
- Supuso que las comillas simples protegerían el `;` en `curl -F`. No lo hacen.
- Sí anticipó correctamente que añadir un campo podía invalidar la firma.

**Pendiente:** cierre con la vía sin `;`
(`--attr "Content-Type=image/tiff-COG-FALSO"`), que demuestra que S3 acepta cualquier
etiqueta, incluso un tipo MIME inexistente.

---

## 2026-09-11 — S3/MinIO — Integridad: verificar un ETag (pregunta del alumno)

**Iniciativa del alumno.** Stalin preguntó cómo verificar que el ETag de un archivo sea el
correcto. Es exactamente la competencia *integridad* que el perfil ESA asigna al rol.

**Concepto enseñado:**

**El ETag de un objeto subido en una sola parte es el MD5 de su contenido.** Se verifica
calculándolo localmente y comparando.

```bash
md5sum /ruta/local.tif                                   # desde archivo local
mc cat lab/<bucket>/<key> | md5sum                       # desde el objeto remoto
mc stat lab/<bucket>/<key>                               # el ETag que guarda el servidor
```

Nota: `md5sum` imprime `-` como nombre cuando el contenido llega por tubería. Es informativo.

**Dirección de la tubería:** el alumno propuso `md5sum | mc ...`. Va al revés — en `A | B`,
A produce y B consume. `mc cat` produce el contenido, `md5sum` lo consume.

**Resultado del alumno:** ✅
```
mc cat lab/productos/sentinel-2/S2A_demo/prueba.tif | md5sum
1c8b1c0e0ec169c5f86f63a0dec68984  -
```
Idéntico al ETag reportado por `mc stat`. **Primera verificación de integridad hecha por él.**

**Coste — distinción operativa importante:**

| Comando | Transfiere | Cuándo |
|---|---|---|
| `mc stat` | Nada (el servidor ya lo tiene calculado) | Casi siempre |
| `mc cat \| md5sum` | El objeto **completo** | Solo contra un archivo local presente |

En un producto real de 8 GB, `mc cat | md5sum` descarga 8 GB. `mc stat` no descarga nada.

**LA TRAMPA — en objetos grandes el ETag NO es el MD5:**

Con multipart upload (automático a partir de cierto tamaño), S3 hashea cada parte, concatena
los hashes, hashea el resultado y añade `-<número de partes>`.

| ETag | Qué es | ¿`md5sum` coincide? |
|---|---|---|
| `1c8b1c0e...` (32 hex) | MD5 del contenido | ✅ Sí |
| `a3f5...-4` (con guion) | Hash de hashes, 4 partes | ❌ No |

**El guion es la señal.** Si está, `md5sum` no coincidirá y **eso no es corrupción**.
Reproducir un ETag multipart exige conocer el tamaño de parte exacto usado al subir: distinto
tamaño de parte → distinto ETag con el mismo contenido.

**Dos usos que no hay que confundir:**
1. **Detectar que algo cambió** → el ETag sirve siempre y es barato (`mc stat`, sin descarga).
   Guardar el ETag en la ingesta y reconsultarlo después; si cambió, alguien sobrescribió.
2. **Verificar que un producto llegó íntegro** → el ETag solo vale en objetos de una sola
   parte. Para productos grandes hace falta un checksum (SHA-256) calculado en la ingesta y
   guardado como metadato del objeto o en el item STAC.

**Pregunta ganada para Terradue/ESA:** ¿la ingesta guarda algún checksum del producto o solo
confía en el ETag? STAC tiene extensión estándar para esto (`file:checksum`). Si nadie la
usa, **verificar integridad de productos grandes no es posible hoy** — hallazgo.

**Pendiente:** `mc stat` sobre `grande.tif` (512 MB) para ver el ETag con guion.

---

## 2026-09-11 — S3/MinIO — Paso 4: políticas de acceso (primer criterio de dominio)

**Concepto enseñado:**

1. **Una política es JSON.** `Version` (siempre `"2012-10-17"`, es la versión del lenguaje),
   `Statement` (lista de permisos), y en cada uno `Effect` (Allow/Deny), `Action`, `Resource`.
   Lo único que cambia entre políticas es `Action` y `Resource`; el resto es plantilla.

2. **ARN = Amazon Resource Name.** Formato de seis campos:
   `arn : partición : servicio : región : cuenta : recurso`.
   En S3 región y cuenta van **vacías** (de ahí el `:::`) porque los nombres de bucket son
   globalmente únicos y no necesitan desambiguación. MinIO usa ARNs `arn:aws:...` por
   compatibilidad S3, aunque no tenga nada que ver con Amazon.

3. **La distinción que causa el 403 nº 1:**

   | ARN | Nombra | Acciones |
   |---|---|---|
   | `arn:aws:s3:::productos` | El **bucket** | `s3:ListBucket` |
   | `arn:aws:s3:::productos/*` | Los **objetos** | `s3:GetObject`, `s3:PutObject` |

   Listar y descargar son operaciones sobre cosas distintas; un permiso no implica el otro.

4. **Cambiar de alias es cambiar de identidad.** `lab` = admin, `analista` = usuario limitado.
   Así se prueba una política.

**Comandos introducidos:**

| Comando | Para qué |
|---|---|
| `mc admin user add lab <user> <pass>` | Crear usuario |
| `mc admin policy create lab <nombre> <archivo.json>` | Registrar una política |
| `mc admin policy attach lab <nombre> --user <user>` | Asignarla |
| `mc admin policy detach lab <nombre> --user <user>` | Quitarla (si no, los permisos se **suman**) |
| `mc admin user info lab <user>` | Ver política efectiva |
| `mc pipe <destino>` | Escribir desde stdin — sirve para probar denegación de escritura |

**Ejercicio 4.1 — política rota a propósito.** `GetObject` sobre `arn:aws:s3:::productos`
(sin `/*`). **Resultado del alumno:** ✅ ambos comandos fallaron como se esperaba.

**Observación clave sobre el mensaje de error:** el servidor dice solo
*"Insufficient permissions"*. **No dice** qué ARN, qué acción faltó, qué política miró.
El mensaje es idéntico para cuatro causas distintas: ARN mal escrito, acción ausente, `Deny`
explícito en otra política, o usuario sin política. **Por eso hay que saber la distinción
bucket/objetos de memoria — el servidor no la recuerda por ti.**

**Ejercicio 4.2 — política correcta.** Dos `Statement`: `GetObject` sobre
`productos/sentinel-2/*`, y `ListBucket` sobre `productos` con
`Condition: StringLike s3:prefix = sentinel-2/*`. Sin la condición el usuario listaría todo
el bucket, `landsat-8/` incluido. `s3:prefix` se refiere **al prefijo que el usuario pide al
listar**, no a la key de un objeto.

**Resultado del alumno — los cuatro casos correctos:** ✅

| # | Prueba | Resultado |
|---|---|---|
| 1 | `cat` en sentinel-2 | ✅ funcionó — devolvió "mi primera banda" |
| 2 | `ls` en sentinel-2/ | ✅ funcionó |
| 3 | `cat` en landsat-8 | ✅ denegado correctamente |
| 4 | escritura con `mc pipe` | ✅ denegada correctamente |

**→ PRIMER CRITERIO DE DOMINIO CUMPLIDO:** *"Escribo una política de bucket que da acceso de
solo lectura a un prefijo, a la primera"* — y verificado con las cuatro pruebas, no solo con
las dos que debían funcionar.

**Principio de verificación:** comprobar solo que lo permitido funciona es **media
verificación**. Una política que permite de más pasa esa prueba. Lo que demuestra que está
bien escrita es **que lo prohibido falle**.

---

### Dos hallazgos del alumno (no estaban en el ejercicio)

**HALLAZGO 1 — la barra final cambia el resultado del listado.**

```
mc ls analista/productos/sentinel-2      → Access Denied
mc ls analista/productos/sentinel-2/     → funciona
```

Misma política, mismo usuario, **un carácter de diferencia**.

Causa: la condición es `StringLike: s3:prefix = "sentinel-2/*"`.
- Pedir `sentinel-2/` → `mc` envía `prefix=sentinel-2/` → **encaja** (`*` admite cadena vacía)
- Pedir `sentinel-2` → `mc` envía `prefix=sentinel-2` → **no encaja**, el patrón exige la barra

**Consecuencia operativa:** un usuario jura que no puede listar, el administrador prueba con
barra y le funciona. Los dos ven cosas distintas y ninguno miente. Sin conocer este detalle
el ticket se va en círculos.

Para cubrir ambos casos: `["sentinel-2/*", "sentinel-2"]`. Pero cuanto más permisiva la
condición, menos aísla — es decisión de diseño, no arreglo automático.

**HALLAZGO 2 — el 403 oculta si el objeto existe.**

El alumno probó tres keys en el prefijo denegado:

| Key | ¿Existe? | Respuesta |
|---|---|---|
| `red.tif` | **Sí** | *Insufficient permissions* |
| `red2.tif` | No | *Insufficient permissions* |
| `red2xxxx.tif` | No | *Insufficient permissions* |

**Respuesta idéntica.** S3 no distingue "no tienes permiso" de "no existe" cuando no hay
permiso. Es **deliberado**: si devolviera 404 para lo inexistente y 403 para lo existente,
cualquiera sin acceso podría mapear el contenido del bucket probando nombres y observando qué
error recibe (enumeración). Ocultarlo es diseño de seguridad correcto.

**Consecuencia:** ante un 403, **no se puede saber desde la cuenta del usuario si el objeto
existe**. Hay que verificarlo con credenciales administrativas:
```bash
mc stat lab/productos/landsat-8/L8_demo/red2.tif     # con el alias admin
```
Por eso el árbol de diagnóstico tiene "¿existe el objeto?" como **paso separado** — y no se
puede saltar.

---

## 2026-09-11 — S3/MinIO — Paso 5: versionado, delete marker y recuperación

**Concepto enseñado:**

Sin versionado, escribir sobre una key existente **destruye** el contenido anterior.
Con versionado, cada escritura crea una **versión nueva**; la anterior queda apilada debajo
con su propio `VersionID`. La key no cambia — cambia cuántas versiones hay bajo ella.

**Comandos introducidos:**

| Comando | Para qué |
|---|---|
| `mc version info lab/<bucket>` | Ver si está activado |
| `mc version enable lab/<bucket>` | Activarlo |
| `mc pipe <destino>` | Escribir desde stdin, sin archivo local |
| `mc ls --versions lab/<bucket>/<key>` | Ver todas las versiones |
| `mc cat --version-id "<id>" lab/<bucket>/<key>` | Leer una versión concreta |
| `mc rm lab/<bucket>/<key>` | Crear delete marker (**reversible**) |
| `mc rm --version-id "<id>" lab/<bucket>/<key>` | Borrar esa versión (**IRREVERSIBLE**) |

**Resultado del alumno — ciclo completo sin errores:** ✅

```
v3 PUT  13B  437cd7b3-...   ← VERSION TRES
v2 PUT  12B  fa5648a6-...   ← VERSION DOS
v1 PUT  12B  2cdec885-...   ← VERSION UNO
```
Leyó la v2 con `--version-id` → devolvió `VERSION DOS` mientras el objeto "actual" era
`VERSION TRES`. Borró, apareció `v4 DEL 0B`, borró el marker, volvió `VERSION TRES`.

**→ CRITERIO DE DOMINIO CUMPLIDO** (nº 3 del archivo): genera versiones, lee una antigua,
borra y recupera.

**Observaciones:**

1. **`mc` es explícito cuando la operación es reversible:**
   `Created delete marker ... (versionId=b9932de3-...)`. No dice "borrado" — dice qué hizo
   realmente. Contraste con los 403 del paso 4, que no explicaban nada.

2. **Cualquier punto del historial es accesible, no solo el anterior.** El alumno leyó la v2
   (intermedia) directamente. Caso real: un workflow que sobrescribe un producto tres veces
   en un día deja tres versiones; si la buena era la segunda, se saca sin "deshacer" en orden.

3. **El delete marker pesa 0 bytes.** Es una lápida, no un objeto: no guarda contenido, solo
   señala "de aquí arriba, considérese borrado".

4. **En un bucket versionado, borrar NO libera espacio.** Las tres versiones seguían ocupando
   sitio con el marker encima. Con 2 PB contratados y rotación anual, esto es presupuesto:
   si nadie limpia versiones antiguas, el almacenamiento crece aunque los usuarios crean que
   borran. De ahí la regla `NoncurrentVersionExpiration` del bloque de lifecycle.

5. **La paradoja de la recuperación:** no existe comando "restaurar". Se **borra el marcador
   de borrado**. Se borra algo para recuperar algo.

| Comando | Efecto |
|---|---|
| `mc rm <key>` | Añade lápida. **Reversible** |
| `mc rm --version-id <id> <key>` | Arranca la página. **Irreversible** — no genera otro marker |

**Pendiente:** contraste en `staging` (un-versioned) — sobrescribir pierde el original y
`mc rm` borra definitivamente, sin marker ni historial. Es el argumento para activar
versionado **antes** de tocar reglas de ciclo de vida: una regla mal escrita se revierte en
un bucket versionado y destruye en uno sin versionar.

---

## 2026-09-11 — S3/MinIO — Paso 6: URLs prefirmadas

**Concepto enseñado:**

Una URL prefirmada es un enlace temporal que **lleva la autorización dentro**. Quien tiene
credenciales la genera; quien la usa descarga directo de S3 **sin credenciales**.

Resuelve un problema real de la plataforma: 3.000 usuarios concurrentes descargando productos
de 2 PB. Las alternativas no sirven — repartir credenciales (gestión y rotación imposibles),
bucket público (inaceptable), o proxy por la aplicación (no escala).

**Clave del diseño:** S3 **no guarda nada**. No hay lista de URLs emitidas. La firma se
recalcula en cada petición y la URL se valida a sí misma.

**Comandos introducidos:**

| Comando | Para qué |
|---|---|
| `mc share download --expire 2m lab/<bucket>/<key>` | Generar URL de descarga |
| `echo "$URL" \| tr '&?' '\n\n'` | Descomponer la URL para leer sus parámetros |
| `curl -s -o /dev/null -w 'HTTP %{http_code}\n' "$URL"` | Ver solo el código HTTP |
| `curl -s "$URL" \| grep -oE '<Code>[^<]*</Code>\|<Message>[^<]*</Message>'` | Extraer la causa del error |
| `sed 's\|A\|B\|'` | Sustituir texto (para sabotear la URL) |

**Captura fiable de la URL** (evita el bug de las dos líneas):
```bash
U=$(mc share download --expire 5m lab/<bucket>/<key> | grep -o 'http[^ ]*X-Amz-Signature[^ ]*')
```

**Parámetros de la firma — legibles SIN credenciales:**

| Parámetro | Qué dice |
|---|---|
| `X-Amz-Algorithm` | `AWS4-HMAC-SHA256` |
| `X-Amz-Credential` | Quién firmó y en qué ámbito |
| `X-Amz-Date` | Cuándo se firmó (`20260911T180714Z`) |
| `X-Amz-Expires` | Segundos de validez desde esa fecha |
| `X-Amz-SignedHeaders` | Cabeceras incluidas en la firma |
| `X-Amz-Signature` | La firma |

**Valor operativo:** ante un "me da 403", pedir la URL al usuario y leer `X-Amz-Date` +
`X-Amz-Expires` dice si caducó, **sin acceso a nada**.

**Resultado del alumno:** ✅ obtuvo `AccessDenied` / *Request has expired* correctamente.

---

### HALLAZGO — S3 comprueba la expiración ANTES que la firma

El alumno ejecutó el sabotaje de alterar la key esperando `SignatureDoesNotMatch` y obtuvo
`Request has expired`.

**Causa:** `$U` contenía una URL de `180714Z` (18:07) y el sabotaje se ejecutó cerca de las
19:58 — casi dos horas después. Generó una URL nueva pero **no la reasignó a la variable**.
El `sed` alteró una URL ya caducada.

**Lo que esto revela:** con **dos** problemas simultáneos (caducada *y* alterada), S3 reporta
solo el primero que encuentra. **No devuelve una lista de fallos, devuelve el primero.**

**Consecuencia para el diagnóstico:** al arreglar la expiración puede aparecer un segundo
error que estaba oculto detrás. **Un 403 resuelto no garantiza que no haya otro debajo.**

---

### La tabla que hay que memorizar

| Situación | HTTP | `<Code>` |
|---|---|---|
| Todo correcto | 200 | — |
| URL alterada (key cambiada, campo añadido) | **403** | `SignatureDoesNotMatch` |
| URL caducada | **403** | `AccessDenied` + *Request has expired* |
| Token inválido al **pedir** la URL | 401 | — (es Keycloak, no S3) |

Los dos casos de S3 dan **403 idéntico**. Causas distintas: una es manipulación, la otra es
tiempo. **Solo el `<Code>` del cuerpo XML los separa.** Un usuario que reporta "403 al
descargar" no está dando información suficiente: hace falta el cuerpo de la respuesta o la
URL para leerle la fecha.

---

### Dos observaciones de la salida del alumno

1. **`versionId` en la URL firmada.** `mc` lo incluyó porque el bucket tiene versionado:
   `&versionId=19a3c73a-...`. La URL apunta a **esa versión concreta para siempre**, aunque
   después se suba una nueva. Útil para garantizar que el usuario recibe exactamente el
   producto anunciado.

2. **`X-Amz-Expires=120`** — pidió `2m` y salieron 120 segundos, **exactamente el valor que
   usa CopernicusLAC en producción** (D3 §6). Coincidencia, pero útil: dos minutos es muy
   corto y deliberado (se pide, se usa, muere). **Un usuario que copia el enlace y lo abre
   diez minutos después recibe 403 — va a ser un ticket recurrente.**

**Pendiente resuelto el 2026-09-15** — ver la entrada siguiente.

---

## 2026-09-15 — S3/MinIO — Cierre del Paso 6: `SignatureDoesNotMatch` con URL vigente

**Lo que faltaba:** el 11-sep el sabotaje de alteración se hizo sobre una URL ya caducada, así
que el 403 no probaba nada sobre la firma. Hoy se repitió con una URL de 10 minutos y se
añadió una comprobación final que el intento anterior no tenía.

**Salida literal, con transcripción en `~/lab-s3/transcripciones/2026-09-15.log`:**

| Petición | Resultado |
|---|---|
| URL original | `HTTP 200` |
| Key alterada (`prueba.tif` → `mentira.tif`) | `SignatureDoesNotMatch` |
| Firma alterada (un `0` antepuesto) | `SignatureDoesNotMatch` |
| **URL original, otra vez, después de los dos ataques** | `HTTP 200` |

**Por qué la cuarta línea es la importante.** Es la que convierte el experimento en prueba.
Sin ella, un `SignatureDoesNotMatch` podría explicarse por caducidad sobrevenida a mitad del
ejercicio. Al volver a dar 200 con la **misma** URL después de los dos rechazos, queda
demostrado que el 403 vino de la manipulación y no del reloj. **Regla general de diagnóstico:
todo experimento que provoca un fallo necesita una comprobación de control que confirme que la
vía sana seguía sana.**

**Dos superficies distintas, mismo código.** Alterar la **key** y alterar la **firma** dan el
mismo `SignatureDoesNotMatch`. No son el mismo caso:

- La firma **cubre la key**. Cambiar de objeto invalida la URL aunque el objeto exista y el
  emisor tenga permiso sobre él. Una URL prefirmada autoriza **un objeto**, no un permiso.
- Alterar la firma es el ataque ingenuo. Alterar la key es el realista: el usuario legítimo
  que recibe un enlace y edita el nombre del fichero para "ver el de al lado".

**Consecuencia operativa:** ante un ticket de 403 sobre URL prefirmada, el `<Code>` decide a
quién se escala. `AccessDenied` + *Request has expired* es un usuario que tardó: se le emite
otra. `SignatureDoesNotMatch` es una URL manipulada: no se reemite sin averiguar quién la
editó y por qué.

### Hallazgo del alumno — el primer 200 fue 403

El primer intento dio `original: HTTP 403` con una URL recién emitida. Causa: un error de
tecleo, `echo $uU` en vez de `echo "$U"`, señal de que la variable no se había poblado como
se creía en esa shell. Al reemitir la URL y repetir, dio 200 limpio.

**Lo que enseña, más allá del typo:** un 403 sobre una URL que *acabas de generar* no siempre
es del servidor. **Antes de diagnosticar S3, hay que verificar que la URL que se envió es la
que se creía enviar.** En producción esto es un ticket clásico: la URL se trunca, se le
escapa un `&` en un correo, o el cliente la recorta. La comprobación previa es imprimir la
URL y contar que lleva sus cinco parámetros `X-Amz-`.
