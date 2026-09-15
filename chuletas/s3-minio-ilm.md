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

---

## 7. Pendiente de verificar

- [ ] Ver una regla de transición **actuar** (nunca observado)
- [ ] Demostrar que **mueve y no borra**: objeto accesible por la misma key + bytes en destino
- [ ] Sabotaje: `--expire-days` en vez de `--transition-days`, y recuperar por delete marker
- [ ] El mismo sabotaje en `staging` (un-versioned) → irreversible
- [ ] `mc ilm tier check` tras rotar la credencial en el frío
