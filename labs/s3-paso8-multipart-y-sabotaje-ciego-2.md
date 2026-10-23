# S3/MinIO — Paso 8: multipart abortado + segundo sabotaje a ciegas

**Objetivo:** cerrar el único ítem de S3 que sigue en ⚠️ (`multipart abortado`) y, sobre ese
mismo terreno, repetir el formato del 1-oct: Claude rompe **una** cosa sin decir cuál, tú
diagnosticas con el audit log y el respaldo.

**Por qué importa aquí:** en el Centro CopernicusLAC las subidas son productos de GB. Una
subida de 4 GB que se corta a mitad **no deja objeto**, pero sí deja las partes ocupando
disco — invisibles a `mc ls`. Sobre 2 PB, basura multipart no vigilada es espacio perdido que
nadie ve y nadie factura a ningún proceso. La regla que la limpia se escribe en el mismo
sitio que la de expiración, y por eso se puede escribir mal igual que aquella.

**Duración estimada:** 75–90 minutos.
**Requisito previo:** las dos instancias MinIO vivas y el receptor de audit log escuchando
(muere al reiniciar WSL — §"Rearranque" abajo).

---

## Mapa de la sesión

| Bloque | Qué haces | Qué demuestras |
|---|---|---|
| 0 | Rearranque y respaldo | Sin respaldo no hay diagnóstico posible |
| A | Subida multipart cortada a propósito | Que las partes sobreviven y `mc ls` no las ve |
| B | Medir el espacio que ocupan | Que la basura es real, no teórica |
| C | Regla `AbortIncompleteMultipartUpload` | Que se limpia sola, y en cuántos días |
| D | **Sabotaje a ciegas nº 2** | Diagnóstico desde el síntoma, sin pista |
| E | Cierre: chuleta, runbook, bitácora | Artefacto contractual |

---

## Bloque 0 — Rearranque y respaldo

```bash
export PATH="$HOME/bin:$PATH"

# ¿están vivas las dos instancias?
curl -fsS http://127.0.0.1:9000/minio/health/live && echo "CALIENTE OK"
curl -fsS http://127.0.0.1:9002/minio/health/live && echo "FRIO OK"

# ¿está vivo el receptor de audit log?
curl -fsS -X POST -d '{"ping":1}' http://127.0.0.1:8080 >/dev/null && echo "RECEPTOR OK"
```

Si alguna falla, rearranca según `chuletas/s3-minio-ilm.md`. **No sigas sin RECEPTOR OK**: el
Bloque D es indiagnosticable sin él.

Respaldo **antes** de que Claude toque nada (§7.4 de la chuleta):

```bash
mkdir -p ~/.lab-backup/$(date +%F)
cd ~/.lab-backup/$(date +%F)
mc ilm rule export lab/productos > ilm-productos.json
mc ilm rule export lab/staging   > ilm-staging.json
mc admin policy info lab solo-lectura-s2 > pol-solo-lectura-s2.json
mc admin config get lab > config-lab.txt
ls -la
```

> **Anota en la bitácora la hora exacta del respaldo.** Es tu línea de corte: todo evento
> `200` posterior a esa hora es candidato a ser el sabotaje.

---

## Bloque A — Cortar una subida multipart

Un multipart solo ocurre si el fichero supera el umbral de parte (MinIO: 16 MiB por defecto
en `mc`). Genera uno de 120 MB para que se parta en varias:

```bash
mkdir -p ~/lab-s3/tmp && cd ~/lab-s3/tmp
head -c 120M /dev/urandom > grande.tif
ls -lh grande.tif
```

Lánzalo y **córtalo a mitad** con Ctrl-C (espera a ver la barra pasar de ~40 %):

```bash
mc cp grande.tif lab/productos/sentinel-2/2025/grande.tif
# ...  Ctrl-C  cuando veas progreso
```

Ahora las dos preguntas que importan:

```bash
# 1. ¿Existe el objeto?
mc ls lab/productos/sentinel-2/2025/ | grep grande

# 2. ¿Existen las partes?
mc ls --incomplete lab/productos/sentinel-2/2025/
```

**Qué esperar, y anótalo tal cual lo veas:** la primera no devuelve nada — el objeto no
existe. La segunda sí lista un upload incompleto. Son dos espacios de nombres distintos sobre
el mismo bucket; `mc ls` a secas **nunca** te mostrará esto.

> Repítelo 2 o 3 veces, cortando en puntos distintos. Quieres varios uploads huérfanos, no
> uno, para que el Bloque B dé un número que se note.

---

## Bloque B — Medir la basura

```bash
# Lo que el bucket "contiene" según el inventario normal
mc du lab/productos

# Lo que ocupa de verdad en disco
du -sh ~/lab-s3/data/productos
```

**El hallazgo que buscas:** los dos números no coinciden, y la diferencia son las partes.
Anota ambos. Esa diferencia es exactamente lo que, escalado a 2 PB, no aparece en ningún
informe de capacidad.

Mira las partes en crudo si quieres verlas con tus ojos:

```bash
find ~/lab-s3/data/.minio.sys/multipart -maxdepth 2 -type d | head
```

Limpieza manual, para saber que existe la salida de emergencia:

```bash
mc rm --incomplete --recursive --force lab/productos/sentinel-2/2025/
mc ls --incomplete lab/productos/sentinel-2/2025/
du -sh ~/lab-s3/data/productos
```

---

## Bloque C — La regla que lo hace sola

Vuelve a crear 2 uploads huérfanos (Bloque A), luego:

```bash
mc ilm rule add lab/productos \
  --prefix "sentinel-2/" \
  --noncurrent-expire-days 0 2>/dev/null   # (ignora: es solo para ver qué rechaza)

mc ilm rule add lab/productos \
  --prefix "sentinel-2/" \
  --expire-delete-marker=false \
  --abort-incomplete-multipart-days 1

mc ilm rule ls lab/productos
```

Preguntas a contestar por escrito **antes** de forzar el reloj:

1. ¿La regla nueva convive con la de expiración del 29-sep o la reemplaza?
2. ¿`--abort-incomplete-multipart-days 1` cuenta desde el inicio del upload o desde la última
   parte recibida?
3. Si pones `0`, ¿lo acepta? (Compáralo con el hallazgo del 16-sep sobre `--expire-days 0`.)

Fuerza el reloj con el mismo método del Bloque D del 29-sep (está en la chuleta §ILM), espera
el barrido y verifica:

```bash
mc ls --incomplete lab/productos/sentinel-2/2025/
python3 ~/lab-s3/audit-q.py --write | tail -20
```

**El dato que cierra el paso:** ¿aparece el aborto en el audit log con hora real, como ocurrió
con la expiración del 1-oct? Si no aparece, eso también es un hallazgo — y es peor.

---

## Bloque D — Sabotaje a ciegas nº 2

Cuando llegues aquí, **pídeme el sabotaje**. Rompo una sola cosa relacionada con lo de hoy, te
doy solo un reporte de síntoma y nada más. Reglas iguales a las del 1-oct:

- No te digo qué toqué, ni dónde, ni cuántas cosas (es **una**).
- Tú diagnosticas: `audit-q.py --admin` → línea de corte del respaldo → `200`, no `400` →
  comparar contra `~/.lab-backup/`.
- Verificas **actuando como el usuario afectado**, no leyendo la config.
- Repararlo no basta: hay que demostrar que quedó **idéntico** al respaldo.

Anota el camino que recorriste, incluidas las ramas falsas. El valor del ejercicio anterior
estuvo ahí: "después de mucho buscar" fue lo que produjo `audit-q.py`.

---

## Bloque E — Cierre

- `chuletas/s3-minio-objetos.md`: sección nueva sobre multipart (`--incomplete`, `mc du` vs
  `du -sh`, limpieza manual).
- `chuletas/s3-minio-ilm.md`: `--abort-incomplete-multipart-days` junto a las otras reglas.
- `runbooks/`: procedimiento "detectar y purgar basura multipart" — es tarea de operación
  periódica, no de laboratorio.
- `bitacora-ejecucion.md`: sesión nueva + pasar `multipart abortado` de ⚠️ a ✅, y añadir el
  sabotaje nº 2 a la tabla.

---

## Criterio de cierre

El paso está cerrado cuando puedas responder, con evidencia pegada en la bitácora:

1. Qué devuelve `mc ls` frente a `mc ls --incomplete` tras una subida cortada.
2. Cuánto espacio ocupaban las partes, en números.
3. Si el aborto automático deja rastro en el audit log, y con qué hora.
4. Qué rompí en el Bloque D, cómo lo encontraste, y la prueba de que quedó idéntico.
