# Chuleta — S3 / MinIO: ILM, reglas y tiers

Comandos practicados y verificados en el laboratorio. **Formato** + **ejemplo real**.

> El pliego contrata rotación anual caliente→frío sobre 2 PB. En la tabla de frontera:
> **Reglas de ciclo de vida (hot→cold) — Proveedor: No · Tú: Sí.** Cuando en una reunión
> pregunten *"¿quién gestiona el ILM del object storage?"*, la respuesta eres tú.

---

## 0. Antes de buscar nada: `--help`

**No hace falta memorizar los comandos. `mc` los lleva dentro.** La ayuda es *anidada*: se
va bajando nivel a nivel hasta el comando exacto.

```bash
mc --help                    # los ~40 comandos: alias, admin, ilm, ls, cp, share...
mc ilm --help                # dentro de ilm: rule · tier · restore
mc ilm tier --help           # dentro de tier: add · ls · info · check · update · rm
mc ilm tier check --help     # la firma exacta: USAGE + FLAGS + EJEMPLOS
```

El último nivel es el que resuelve las dudas de sintaxis. Por ejemplo:

```
USAGE:  mc ilm tier check TARGET NAME
```

Eso dice que van **dos** argumentos: el **alias del servidor** (`lab`) y el **nombre del
tier** (`FRIO`) → `mc ilm tier check lab FRIO`.

> **Verificado el 15-sep:** el comando `mc ilm tier check` —justo el que hacía falta para
> validar la credencial del tier— estaba en `mc ilm tier --help` desde el principio. Se
> perdió tiempo inventando un `mc admin config get lab tier` que no existe. **Antes de
> suponer que un comando existe, se mira el `--help` del nivel correspondiente.**

Atajos útiles:

```bash
mc <comando> -h              # -h equivale a --help
mc --help | grep -i tier     # buscar por palabra cuando no recuerdas el nombre
```

---

## 0.1 Cómo leer un comando de `mc`

El **primer argumento siempre responde "¿a qué servidor le hablo?"**. Lo que viene después
depende de si la cosa pertenece al servidor entero o a un bucket concreto.

```bash
mc ls             lab/productos     # alias/bucket
mc admin user ls  lab               # alias — usuarios del SERVIDOR
mc ilm rule ls    lab/productos     # alias/bucket — reglas de ESE bucket
mc ilm tier ls    lab               # alias — tiers del SERVIDOR
mc ilm tier check lab FRIO          # alias + nombre del tier
```

Los **tiers son del servidor**, no de un bucket: un mismo `FRIO` puede recibir objetos de
`productos` y de `staging`. Las **reglas sí son por bucket**.

### La trampa de los tres "frio"

| Escribes | Qué es | Dónde vive |
|---|---|---|
| `frio` | Un **alias** tuyo | `~/.mc/config.json`, en tu disco |
| `FRIO` | Un **tier** del caliente | `.minio.sys/` dentro de `lab-s3/data` |
| `lab/frio` | Un **bucket** del caliente | Dentro del servidor caliente |

Un alias es una etiqueta **local**: `lab` no significa nada para MinIO, solo guarda URL y
credenciales en tu máquina. El tier `FRIO` es al revés — vive **dentro** del servidor
caliente, y el MinIO frío no sabe que se llama así. Es como un contacto en tu agenda: el
nombre que le pones no lo conoce la otra persona.

El tier se escribe en mayúsculas por convención, para distinguirlo de un vistazo.

---

## 1. Qué significa ILM

**ILM = Information Lifecycle Management** — gestión del ciclo de vida de la información.

Es el término estándar de la industria del almacenamiento para las reglas que deciden **qué
le pasa a un dato con el paso del tiempo**, sin que nadie intervenga. El dato nace, se usa
mucho, se usa poco, y al final se archiva o se destruye.

**En AWS el mismo concepto se llama *S3 Lifecycle Configuration*** y su API es
`PutBucketLifecycleConfiguration`. MinIO implementa esa misma API pero agrupa los comandos
bajo el nombre genérico `ilm`. Son la misma cosa con dos nombres — **la documentación de AWS
sirve para MinIO**.

---

## 2. Las tres palabras del bloque

| Término | Qué es |
|---|---|
| **ILM** | El sistema de reglas en conjunto |
| **Rule** (regla) | Una instrucción concreta: *qué* objetos · *cuándo* · *qué hacer* |
| **Tier** (nivel, capa) | Un destino de almacenamiento con otro coste y otra velocidad. En AWS: `GLACIER`, `DEEP_ARCHIVE` |

### Las dos acciones que una regla puede tomar

| Acción | Qué hace | Flag |
|---|---|---|
| **Transition** (transición) | **Mueve** el objeto a otro tier. **Sigue existiendo** | `--transition-days` |
| **Expiration** (expiración) | Lo **borra** | `--expire-days` |

> ⚠️ **Se escriben igual de fácil y hacen lo contrario.** En un bucket versionado la
> equivocación se revierte; en uno sin versionar, no. **Por eso el versionado se activa
> ANTES de tocar ciclo de vida, no después.**

---

## 3. Comandos — reglas

```bash
mc ilm rule add lab/productos --prefix "sentinel-2/" --transition-days 365 --transition-tier FRIO
mc ilm rule ls     lab/productos      # tabla resumen — ORIENTATIVA
mc ilm rule export lab/productos      # JSON crudo — FUENTE DE VERDAD
mc ilm rule rm --id <ID> lab/productos
```

### ⚠️ La tabla de `rule ls` pierde información

`mc ilm rule ls` imprime **`0`** en `DAYS TO EXPIRE` cuando la regla **no tiene** campo
`Days`. No distingue *"cero días"* de *"no aplica"*.

**Verificado el 15-sep:** esta regla…

```
│ ID                   │ PREFIX │ DAYS TO EXPIRE │ EXPIRE DELETEMARKER │
│ dai0tojks34ceukoakcg │   -    │       0        │        true         │
```

…se leyó como *"borra todo el bucket inmediatamente"*. El JSON real dice otra cosa:

```json
{"Expiration":{"ExpiredObjectDeleteMarker":true}}
```

No tiene `Days`. Es una regla de **limpieza de lápidas huérfanas**, incapaz de tocar un
objeto con contenido.

> **Regla de oro: ante cualquier duda sobre una regla de ciclo de vida, `mc ilm rule export`
> y se lee el JSON.** La tabla es para mirar de reojo.

### Los tres tipos de regla que conviven en `productos`

```json
{"Rules":[
 {"NoncurrentVersionExpiration":{"NoncurrentDays":30},"Status":"Enabled"},
 {"Filter":{"Prefix":"sentinel-2/"},"NoncurrentVersionExpiration":{"NoncurrentDays":30},"Status":"Enabled"},
 {"Expiration":{"ExpiredObjectDeleteMarker":true},"Status":"Enabled"}
]}
```

| Regla | Qué hace |
|---|---|
| `NoncurrentVersionExpiration` | Caduca **versiones antiguas** a los N días. No toca la actual |
| `ExpiredObjectDeleteMarker` | Barre **delete markers huérfanos** — lápidas cuya versión real ya caducó |
| `Expiration: {Days: N}` | **Borra el objeto vivo**. El peligroso |

---

## 4. Comandos — tiers

```bash
mc ilm tier add minio lab FRIO \
  --endpoint http://127.0.0.1:9002 \
  --access-key admin --secret-key frio12345 \
  --bucket archivo --prefix rotado/

mc ilm tier ls     lab           # los tiers declarados
mc ilm tier info   lab FRIO      # uso: bytes, objetos, versiones
mc ilm tier check  lab FRIO      # ¿la credencial SIGUE siendo válida?
mc ilm tier update lab FRIO      # cambiar credenciales
mc ilm tier rm     lab FRIO      # solo si está vacío
```

Salida de `tier add` cuando funciona: `Added remote tier FRIO of type minio`

### La dirección de la llamada — el concepto clave

Las credenciales del **frío** se escriben en el **caliente**, nunca al revés:

```
CALIENTE  ──PutObject con admin/frio12345──▶  FRÍO
(cliente)                                     (servidor)
   │                                             │
   └─ guarda la credencial                       └─ la valida... y puede rotarla
      y NO sabe si sigue viva                       cuando quiera, sin avisar
```

Cuando la regla dispara, **el proceso MinIO caliente actúa como cliente S3** contra el frío:
abre la conexión y hace el `PutObject`. Para eso necesita credenciales del destino. El frío
es un servidor pasivo — no sabe que existe una regla, no sabe que lo nombraron tier, y no
tiene obligación de avisar a nadie cuando cambia una clave.

### ⚠️ La credencial del tier es estática y está en texto plano

**Verificado el 15-sep:**

```bash
grep -rl "frio12345" ~/lab-s3/data/
→ /home/stalin/lab-s3/data/.minio.sys/config/tier-config.bin/xl.meta
```

La contraseña del frío está **sin cifrar en el disco del caliente**. `grep` la encuentra.

Vive en `.minio.sys/config/tier-config.bin`, un almacén **aparte** de `config.json`. Por eso
`mc admin config get lab tier` falla con `unknown subsystem: tier` — los tiers **no son un
subsistema de configuración**.

**Consecuencia operativa:** la rotación en el frío puede ser automática (política del
proveedor, cada 90 días). **La propagación al caliente no lo es: nadie la actualiza solo.**
Ese hueco entre las dos es la avería. Emparentado con la **avería 17** del catálogo —
credencial rotada sin actualizar el Secret.

→ `mc ilm tier check` es la herramienta de detección. Candidato a **chequeo periódico de
monitorización**, no a comprobación manual.

---

## 5. El reloj — por qué una regla "no hace nada"

MinIO evalúa el ciclo de vida en un **barrido periódico del scanner**, no en el momento de
escribir la regla. Una regla recién creada puede tardar en actuar.

```bash
mc admin scanner status lab                   # ver el ciclo
mc admin config set lab scanner speed=fastest # acelerar (solo laboratorio)
```

Corolario para el diagnóstico: **"la regla no ha hecho nada" no prueba que la regla esté
mal.** Puede que aún no le haya tocado el turno.

---

## 6. Errores vistos y su causa

| Error | Causa |
|---|---|
| `Invalid storage class` al añadir una regla | El tier no existe todavía. **Se declara el tier antes que la regla** |
| `mc ilm tier add` **se cuelga sin timeout** | Se apuntó el MinIO contra **sí mismo**. Valida contra su propio endpoint → espera infinita. Revisar `--endpoint` |
| `unknown subsystem: tier` | `mc admin config get lab tier` no existe. Los tiers se consultan con `mc ilm tier ls/info/check` |
| `expiration days cannot be set to zero` | `--expire-days 0` está **prohibido**. `--transition-days 0` sí se acepta: archivar hoy sí, destruir hoy no |
| `The specified version does not exist` tras un `rm --version-id` | Casi siempre **el comando anterior funcionó** y se está repitiendo. Verificar con `mc admin info`, no con el mensaje |

---

## 7. Recuperar un objeto borrado por una regla de expiración

Procedimiento verificado el 2026-09-30. En bucket **versionado**, expirar no destruye:
añade un delete marker encima. Recuperar = quitar ese marker.

**⚠️ Paso 1 — retirar la regla PRIMERO. No es una precaución, es parte del procedimiento.**

```bash
mc ilm rule export lab/productos                    # localizar la regla culpable
mc ilm rule rm --id <id-de-la-regla> lab/productos
mc ilm rule export lab/productos                    # confirmar que ya NO aparece
```

Si se recupera con la regla activa, el objeto **vuelve y muere otra vez en ~30 segundos**
(medido). El síntoma —"sigue sin aparecer"— es idéntico a que el comando hubiera fallado.

**Paso 2 — identificar el marker.** Es la versión `0B` marcada `DEL`, la más reciente:

```bash
mc ls --versions lab/productos/landsat-8/2025/
# [2026-09-29 09:15:23]     0B ... ba9768df-… v2 DEL  ← el marker: este se borra
# [2026-09-16 08:59:17] 5.0MiB ... e7eb9fa9-… v1 PUT  ← los datos: NUNCA tocar este
```

**Paso 3 — borrar el marker** (sin `--versions`):

```bash
mc rm --version-id <id-del-marker> lab/productos/landsat-8/2025/producto-condenado.tif
```

> 🔪 **El filo del cuchillo:** el mismo comando recupera o destruye según el ID. Borrar el
> ID del marker resucita; borrar el ID de `v1` **destruye los datos de forma irreversible**.
> Comprobar dos veces que el ID elegido es el de la línea `0B ... DEL`.

**Paso 4 — verificar con los CONTADORES, no con la salida del `rm`:**

```bash
mc ls lab/productos/landsat-8/2025/     # el objeto reaparece con su tamaño
mc admin info lab | tail -3             # Delete Markers debe haber BAJADO en 1
```

La salida de `mc rm` engaña en las dos direcciones: el 29-sep no dio error y **no** recuperó;
el 30-sep dio `ERROR ... version does not exist` y **sí** había recuperado (era la segunda
ejecución del mismo comando). Los contadores de `admin info` son el único testigo fiable.

**Y lo que hace todo esto posible:** el bucket tiene **versionado**. En `staging`, que no lo
tiene, la misma regla de expiración es **irreversible** — no hay marker que quitar. Ver §7.1.

---

## 7.1 ⚠️ Antes de tocar una regla de expiración: ¿hay red?

**La comprobación que precede a todo lo demás** (verificado el 2026-09-30):

```bash
mc version info lab/productos    # → versioning is enabled   ✅ hay red
mc version info lab/staging      # → is un-versioned         ⛔ NO hay red
```

**Por qué importa:** ninguna otra señal lo revela. El mismo comando de borrado, la misma
regla y el mismo anuncio producen resultados opuestos:

| | `productos` (versionado) | `staging` (sin versionado) |
|---|---|---|
| `mc rm objeto` | añade delete marker | **evapora el objeto** |
| `mc ls --versions` tras borrar | v1 intacta + marker `0B DEL` | **nada** |
| Delete Markers en `admin info` | sube 1 | no cambia |
| Recuperable | ✅ borrando el marker | ⛔ **imposible** |

**Y `mc stat` NO distingue entre ambos casos.** Las dos sentencias son indistinguibles:

```
staging   → Expiration: 2026-10-01 19:00:00 EST (lifecycle-rule-id: dault0rks34cs5gqteag)
productos → Expiration: 2026-09-17 19:00:00 EST (lifecycle-rule-id: dalbkgrks34dq4krgq90)
```

Mismo formato, mismo tono de certeza. Una era recuperable y la otra no.

**El delator rápido — `null` como version-id:**

```bash
mc ls --versions lab/staging/sacrificio/
# [2026-09-30 14:09:07 EST] 5.0MiB STANDARD null v1 PUT sin-red.tif
#                                            ^^^^ sin versionado: nada que restaurar
```

Un UUID = hay historia debajo. `null` = estás sin red. (Ojo: en un bucket sin versionado
`mc ls --versions` **sí** lista el objeto — no calla, que es lo que se supone por intuición.)

---

## 7.2 Audit log — saber CUÁNDO y QUIÉN destruyó algo

Verificado el 2026-09-30. Es el **único** mecanismo que responde esas dos preguntas: el
delete marker da fecha de *elegibilidad* (no de ejecución) y ningún autor; y en un bucket sin
versionado el borrado no deja **nada**.

⚠️ **No es un fichero de log: es un webhook.** MinIO hace POST HTTP de cada evento. Sin un
receptor escuchando, activarlo no produce nada.

**Montaje (laboratorio):**

```bash
mkdir -p ~/lab-s3/audit
nohup python3 ~/lab-s3/audit-receptor.py > ~/lab-s3/audit/receptor.log 2>&1 &
ss -ltn | grep 8080                       # confirmar que escucha

mc admin config set lab audit_webhook:lab endpoint="http://127.0.0.1:8080"
mc admin service restart lab              # ⚠️ obligatorio: no carga hasta reiniciar
sleep 8 && curl -fsS http://127.0.0.1:9000/minio/health/live
```

**⚠️ Se configura como *target*, con sufijo.** `audit_webhook:lab`, no `audit_webhook`. El
bloque base sigue diciendo `enable=off` y **es correcto** — son dos entradas distintas:

```
audit_webhook enable=off ...                        ← base, sigue off (normal)
audit_webhook:lab endpoint=http://127.0.0.1:8080    ← el target real
```

**Leer el log** (sin `jq`, que no está instalado):

```bash
wc -l ~/lab-s3/audit/audit.jsonl
tail -1 ~/lab-s3/audit/audit.jsonl | python3 -m json.tool

# quién hizo qué y cuándo
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

**Lo que da cada evento:** hora al nanosegundo · operación · bucket · objeto · IP ·
`requestID` · credencial usada (en `Authorization`).

```
2026-09-30T19:40:12.310692147Z  PutObject              staging  aud.txt  127.0.0.1
2026-09-30T19:44:29.930708001Z  DeleteMultipleObjects  staging  aud.txt  127.0.0.1
```

**La auditoría se audita a sí misma:** `SetConfigKV` y `ServiceV2` aparecen en el log — no se
puede tocar la configuración del registro sin dejar constancia. **Pero** solo si el receptor
ya estaba escuchando: un `config reset` con el receptor caído no deja nada.

> **Para la plataforma real:** un receptor local no es auditoría. El destino debe ser un
> colector **remoto, persistente y fuera del control del administrador auditado**. En el lab
> el receptor es un `nohup` que muere al reiniciar WSL — hay que rearrancarlo con MinIO.

---

## 7.3 Investigar en el audit log — `audit-q.py`

El log crudo es ilegible a mano: una línea JSON gigante por evento, y el 90 % son lecturas.
En el incidente del 2026-10-01 fueron **14 eventos útiles de 203**. El script
`~/lab-s3/audit-q.py` hace ese filtrado.

```bash
python3 ~/lab-s3/audit-q.py --admin                      # cambios de CONFIGURACIÓN ← empezar aquí
python3 ~/lab-s3/audit-q.py --write                      # escrituras y borrados de objetos
python3 ~/lab-s3/audit-q.py --all --grep solo-lectura-s2 # todo lo que mencione un nombre
```

Salida: hora UTC · operación · bucket/objeto · IP · **statusCode**.

**`--admin` es el filtro que resuelve los incidentes de acceso**, porque aísla las
operaciones que cambian estado: `AddCannedPolicy`, `SetPolicy`, `AddUser`, `RemoveUser`,
`SetConfigKV`, `SetBucketLifecycle`, `AddTier`, `ServiceV2`…

**La columna `OK` (statusCode) separa intento de efecto:**

```
2026-10-01 13:27:49   AddCannedPolicy   400   ← rechazado: NO se aplicó
2026-10-01 13:33:03   AddCannedPolicy   200   ← aceptado: aquí sí cambió algo
```

Un `400` es ruido —alguien peleando con la sintaxis—. Solo los `200` cambiaron el sistema.
Confundirlos lleva a culpar al cambio equivocado.

> **Procedimiento ante "a un usuario le falla el acceso y ayer funcionaba":**
> 1. `audit-q.py --admin` → ¿hay un `AddCannedPolicy`/`SetPolicy` con **200** reciente?
> 2. Identificar la política y leerla: `mc admin policy info lab <nombre>`
> 3. Comparar con el respaldo. **Sin respaldo no hay comparación posible** (§7.4)
> 4. Corregir, y verificar actuando **como el usuario**: `mc ls lector/productos/...`

---

## 7.4 ⚠️ Respaldar la configuración ANTES de tocarla

El audit log dice **qué** se cambió y **cuándo**, pero **no guarda el valor anterior**. Sin
un respaldo no hay forma de saber cómo debía ser una política.

```bash
D=~/.lab-backup && mkdir -p $D
mc ilm rule export lab/productos > $D/ilm-productos.json
mc admin policy list lab         > $D/policies.txt
for p in solo-lectura-s2 lectura-s2 prueba-rota solo-lectura-rota; do
  echo "--- $p ---" >> $D/policy-dumps.txt
  mc admin policy info lab $p    >> $D/policy-dumps.txt
done
mc admin user list lab > $D/users.txt
mc ilm tier ls lab     > $D/tiers.txt
```

Verificar que una reparación quedó **idéntica** al original, no solo "funcionando":

```bash
mc admin policy info lab solo-lectura-s2       # comparar contra policy-dumps.txt
```

---

## 7.5 Incidente resuelto 2026-10-01 — permiso de lectura sin navegación

**Síntoma reportado:** «`lector` no puede trabajar con Sentinel-2, ayer funcionaba. Algunas
cosas le funcionan y otras no.»

**Causa:** una sola cadena alterada en la `Condition` de `solo-lectura-s2`:

```
s3:prefix: ["sentinel-2/*"]   →   ["sentinel-2/2024/*"]
```

**Por qué fue difícil de ver:**

| | |
|---|---|
| JSON válido, sintaxis AWS correcta | `mc` la aceptó sin una queja; ningún validador la detecta |
| `2024` es un prefijo **plausible** | parece una decisión deliberada, no un error |
| Rompía **la mitad** del acceso | `GetObject` intacto: podía **descargar** con la ruta exacta, pero no **listar** para descubrirla |

> **El patrón a reconocer: permiso de lectura sin permiso de navegación.** `GetObject` y
> `ListBucket` son independientes. Un usuario puede tener acceso real a los datos y aun así
> ver "Access Denied" al navegar — y jurar, con razón, que tiene permisos. No es un 403 limpio.

**Diagnóstico que funcionó:** audit log → política modificada → leerla → comparar → corregir.
**Del rastro al estado, no del síntoma a la conjetura.**

**Verificación final** — actuando como el usuario, no como admin:

```bash
mc ls lector/productos/sentinel-2/     # antes: Access Denied · después: lista 2025/ y S2A_demo/
```

---

## 8. Pendiente de verificar

- [x] Ver una regla de transición **actuar** — 15-sep
- [x] Demostrar que **mueve y no borra** — 15-sep: misma key, bytes en `frio/archivo`, caliente de 5 MiB a 8 KB
- [x] Sabotaje `--expire-days` y recuperación por delete marker — 30-sep (§7)
- [x] El mismo sabotaje en `staging` (un-versioned) → irreversible — 30-sep (§7.1)
- [ ] `mc ilm tier check` tras rotar la credencial en el frío
- [x] Activar `audit_webhook` — 30-sep (§7.2). Confirma **cuándo** y **quién**; el timestamp
      del delete marker es de *elegibilidad*, no de ejecución
- [ ] Ver en el audit log el evento del **barrido de lifecycle** (1-oct, `sin-red.tif`)
