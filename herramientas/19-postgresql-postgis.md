# PostgreSQL + PostGIS — operación, no administración

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 3 — soporte del catálogo y del registry
**Competencia de la matriz:** 17

---

## 1. Qué es, aquí

PostgreSQL es la base de datos de **tres** componentes del Middleware:

| Componente | Qué guarda |
|---|---|
| **Data Discovery and Access** (§3.2.4) | El catálogo, vía PgSTAC (collections e items como JSONB) |
| **Application Registry** (§3.4.4) | *"PostgreSQL… is used within GitLab to manage the metadata associated with each application package"* |
| **User Workspace** (§3.6.4) | Metadatos del workspace |

**PostGIS** es la extensión que le da capacidades geoespaciales: *"used to extend the
capabilities of the PostgreSQL relational database by adding support for storing, indexing,
and querying **geospatial data**"* (D2 §3.2.4).

Se entrega como **DBaaS** — servicio administrado del proveedor. D2 §7.14:

> *"PostgreSQL is expected to be provided as a **managed service** by the cloud provider…
> including automated maintenance, backups, and scaling, allowing the platform to focus on
> its core functionalities rather than database management."*

**Ésa es exactamente la frontera de este archivo.**

---

## 2. La frontera — la más nítida de la carpeta

El perfil ESA §2.3.3 lo escribe con una claridad que agradecerás:

> *"Operational monitoring of managed databases (availability, connectivity, basic
> performance), **backup verification**, **restore testing** (when defined), diagnosis of
> connectivity issues and basic bottlenecks, and coordination with the DBaaS provider for
> incidents, scalability, and planned changes.*
>
> ***Excludes** engine administration, patching, HA configuration, and **backup
> execution**."*

| Materia | Proveedor | Tú |
|---|---|---|
| Motor, versiones, parches | **Sí** | No |
| Alta disponibilidad | **Sí** | Validas que funciona |
| **Ejecución** de respaldos | **Sí** | No |
| **Verificación** de respaldos | Reporta | **Sí — verificas tú** |
| **Pruebas de restauración** | Facilita | **Sí — cuando estén definidas** |
| Escalado y cifrado | **Sí** | Solicitas |
| Conectividad y salud | — | **Sí** |
| Desempeño básico, consultas lentas | — | **Sí** |
| Índices y esquema de PgSTAC | No sabe qué es | **Sí** → [05](05-stac-pgstac-stac-fastapi.md) |
| Gestión de accesos administrativos | Habilita (pliego §8.5.16) | **Coordinas** |

La distinción entre **verificar** un respaldo y **ejecutarlo** es la que más vas a repetir en
reuniones. Ejecutar es del proveedor. Verificar que existe, que es reciente y que
**restaura de verdad** es tuyo — y sin eso, un respaldo es una suposición.

---

## 3. Qué debes saber

### Nivel imprescindible

**Conectividad y diagnóstico básico**
- Cadena de conexión, `psql`, `\l`, `\dt`, `\dn`, `\d+ tabla`, `\di`.
- Diagnóstico desde un pod: ¿resuelve el DNS del servicio? ¿el puerto 5432 está abierto?
  ¿las credenciales son correctas? Los tres fallos dan mensajes distintos.
- `pg_isready`.

**Sesiones y bloqueos**
- `pg_stat_activity`: quién está conectado, qué ejecuta, desde cuándo, en qué estado.
- Estados: `active`, `idle`, **`idle in transaction`** (el que agota conexiones sin hacer
  nada — el sospechoso favorito).
- `pg_locks` y consultas bloqueadas.
- `pg_terminate_backend()` — y cuándo es legítimo usarlo.

**Pool de conexiones**
- `max_connections` y por qué se agota: normalmente no por carga real sino por pools mal
  dimensionados en las aplicaciones.
- El error `FATAL: sorry, too many clients already` — **avería 11 del catálogo**.
- Relación con stac-fastapi: pools de lectura y escritura separados.

**Consultas lentas**
- `EXPLAIN` vs `EXPLAIN ANALYZE`.
- Leer un plan: seq scan vs index scan, coste estimado vs tiempo real.
- `pg_stat_statements` si está disponible.
- Índices: B-tree, **GiST** (el espacial de PostGIS), GIN (para JSONB).

**PostGIS, lo justo**
- `geometry` vs `geography`, SRID y por qué 4326 es el habitual.
- `ST_Intersects`, `ST_AsText`, `ST_GeomFromText`, `ST_MakeEnvelope`.
- **Índice GiST**: sin él, una consulta espacial hace scan completo. Medirlo es el ejercicio
  del [bloque 4](05-stac-pgstac-stac-fastapi.md).
- `ANALYZE` y por qué las estadísticas desactualizadas producen planes malos.

### Nivel operativo

- **Verificación de respaldos**: qué evidencia pedir al proveedor (fecha, tamaño, resultado,
  ubicación), con qué frecuencia, y cómo dejarlo registrado en el informe mensual.
- **Prueba de restauración**: cómo se solicita, en qué entorno, qué se comprueba después.
  Sin esta prueba, RTO < 24 h y RPO < 1 h son promesas sin verificar.
- **Validación de HA funcional**: el pliego §8.5.16 lo lista como función del servicio
  administrado. Sabe cómo pedir una prueba de failover.
- Métricas a vigilar: conexiones activas vs máximo, latencia de consultas, tamaño de la base,
  bloat, replicación (lag), IOPS.
- Coordinación de cambios: ampliar `max_connections`, añadir un índice, escalar la instancia.
  Todo eso pasa por el proveedor.

### Nivel avanzado (para dialogar, no para ejecutar)

- Vocabulario de HA: primario/réplica, replicación síncrona vs asíncrona, failover,
  `pg_stat_replication`.
- Vocabulario de respaldos: `pg_dump`/`pg_restore` (lógico) vs base backup + WAL (físico),
  PITR. **Esto lo necesitas para entender qué significa RPO < 1 h**, no para ejecutarlo.
- Particionado, que es lo que usa PgSTAC.
- Autovacuum y bloat: por qué una tabla crece sin que crezcan los datos.

---

## 4. Datos de la plataforma que debes tener a mano

**Contratado (pliego, Anexo I):**

| Parámetro | Valor |
|---|---|
| Instancias | **2 en HA** (D1 pedía 4) |
| Recursos por instancia | **16 vCPU / 64 GB RAM / 800 GB** |
| Versión PostgreSQL | **≥ 13** (recomendado **16**) |
| Versión PostGIS | **≥ 3** (recomendado **3.5**) |
| RTO / RPO | **< 24 h** / **< 1 h** |
| Disponibilidad | 99,95 % mensual (≈43,2 min) |

**Lo que el proveedor debe poder hacer sobre DBaaS (pliego §8.5.16)** — memorízalo, es tu
palanca:

- Seguimiento técnico
- Gestión de accesos administrativos
- Coordinación ante anomalías detectadas por el middleware
- **Verificación periódica de backups**
- **Validación de HA funcional**
- Supervisión de recursos
- Documentación

Nota la asimetría: el pliego dice que **el proveedor** verifica los backups; el perfil ESA
dice que **tú** los verificas. No es contradicción: él verifica que el proceso corrió, tú
verificas la evidencia y pruebas la restauración. **Ambas cosas deben ocurrir, y la tuya es
la que aparece en el informe mensual.**

---

## 5. Laboratorio

Apoyado en el [bloque 4](05-stac-pgstac-stac-fastapi.md).

1. **Levanta PostgreSQL con PostGIS** en el clúster (o en contenedor). Conecta con `psql`
   desde un pod.
2. **Explora**: `\l`, `\dn`, `\dt pgstac.*`, `\di pgstac.*`.
3. **Sesiones**: abre varias conexiones y obsérvalas en `pg_stat_activity`. Deja una en
   `idle in transaction` (`BEGIN;` sin `COMMIT`) y comprueba que se ve.
4. **Agota el pool**: baja `max_connections` a 10 y abre 15 conexiones. Observa el error
   exacto. **Éste es el error que verás en producción.**
5. **Consulta lenta**: haz una búsqueda espacial sobre la tabla de items **sin** índice.
   Cronométrala con `EXPLAIN ANALYZE`. Crea el índice GiST. Repite. **Anota los dos
   números** — es tu primera evidencia de rendimiento.
6. **Bloqueo**: abre dos sesiones, bloquea una fila desde la primera y actualízala desde la
   segunda. Localiza el bloqueo en `pg_locks` y resuélvelo.
7. **Respaldo y restauración a pequeña escala**: `pg_dump` de la base, bórrala, restáurala,
   y **verifica que los datos están**. No es tu trabajo hacerlo en producción, pero necesitas
   saber qué se comprueba.
8. **Escribe la lista de verificación** que usarás para validar el respaldo del proveedor:
   ¿existe? ¿de cuándo? ¿de qué tamaño? ¿restauró alguna vez? ¿dónde está la evidencia?

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Agotar `max_connections` | `too many clients already`. **Avería 11** |
| Dejar una sesión `idle in transaction` | Cómo una sola sesión olvidada bloquea la base |
| Borrar el índice espacial | La búsqueda pasa de ms a segundos. **Avería 11** |
| Rotar la credencial sin actualizar el Secret | `password authentication failed`. **Avería 17** → [14](14-external-secrets-operator.md) |
| NetworkPolicy que bloquea el 5432 | `connection refused`, no error de credenciales → [18](18-ingress-tls-cert-manager.md) |
| `ANALYZE` no ejecutado tras una carga masiva | Plan de consulta malo con datos correctos |

---

## 7. Averías de producción que este bloque entrena

- **Avería 11:** catálogo lento — índice espacial ausente o pool agotado.
- **Avería 17:** base de datos inalcanzable — credencial rotada sin actualizar el Secret.

**Cómo distinguir las tres causas de "no puedo conectar":**

| Mensaje | Causa | De quién |
|---|---|---|
| `connection refused` / timeout | Red, NetworkPolicy, servicio caído | Red (tuyo) o servicio (proveedor) |
| `password authentication failed` | Credencial | **Tuyo** — el Secret |
| `too many clients already` | Pool agotado | **Tuyo** — dimensionamiento |
| `FATAL: database ... does not exist` | Configuración | **Tuyo** |
| Timeout tras conectar | Consulta lenta o bloqueo | **Tuyo** — investiga antes de escalar |

---

## 8. Consultas de bolsillo

```sql
-- ¿Quién está conectado y qué hace?
SELECT pid, usename, application_name, client_addr, state,
       now() - state_change AS duracion, left(query, 80) AS consulta
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY duracion DESC;

-- Sesiones idle in transaction (el asesino silencioso)
SELECT pid, usename, now() - state_change AS parada, left(query,60)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY parada DESC;

-- ¿Cuántas conexiones quedan?
SELECT count(*) AS actuales,
       current_setting('max_connections')::int AS maximo
FROM pg_stat_activity;

-- Bloqueos
SELECT bloqueada.pid AS bloqueada, bloqueante.pid AS bloqueante,
       left(bloqueada.query,60) AS consulta_bloqueada
FROM pg_stat_activity bloqueada
JOIN pg_stat_activity bloqueante
  ON bloqueante.pid = ANY(pg_blocking_pids(bloqueada.pid));

-- Terminar una sesión (con criterio)
SELECT pg_terminate_backend(<pid>);

-- Tamaños
SELECT pg_size_pretty(pg_database_size(current_database()));
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS tamano
FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;

-- Índices del esquema del catálogo
SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'pgstac';

-- ¿Por qué es lenta esta consulta?
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM pgstac.items
WHERE ST_Intersects(geometry, ST_MakeEnvelope(7.8,45.2,9.0,45.8,4326));

-- Estado de la réplica (para validar HA)
SELECT client_addr, state, sent_lsn, replay_lsn,
       sent_lsn - replay_lsn AS lag_bytes
FROM pg_stat_replication;

-- Versiones (contrástalas con el pliego: PG ≥13, PostGIS ≥3)
SELECT version();
SELECT postgis_full_version();
```

```bash
# Desde un pod
kubectl run tmp --rm -it --image=postgres:16 -- \
  psql "postgresql://usuario@host:5432/base"
pg_isready -h <host> -p 5432
nc -zv <host> 5432          # ¿es red o son credenciales?
```

---

## 9. Criterio de dominio

- [ ] Diagnostico conectividad y **distingo red, credenciales y pool agotado** por el mensaje.
- [ ] Localizo sesiones bloqueantes y las resuelvo.
- [ ] Leo un `EXPLAIN ANALYZE` y sé si falta un índice.
- [ ] Mido el efecto de un índice GiST y lo documento con números.
- [ ] **Explico la diferencia entre verificar un respaldo y ejecutarlo, y sé cuál me toca.**
- [ ] Tengo una lista de verificación de respaldos y la aplico mensualmente.
- [ ] Sé pedir una prueba de restauración y qué comprobar después.
- [ ] Cito de memoria lo contratado: 2 instancias HA 16/64/800 GB, PG ≥13, PostGIS ≥3, RTO < 24 h, RPO < 1 h.
- [ ] Sé cuándo el problema es mío y cuándo escalar, **con evidencia**.

---

## 10. Artefacto que produces

**Lista de verificación de respaldos y su evidencia**, que se integra en la plantilla del
informe mensual ([03-prometheus-grafana.md](03-prometheus-grafana.md)):

- ¿Existe respaldo de las últimas 24 h? Evidencia: captura o reporte del proveedor con fecha.
- ¿El RPO real observado es < 1 h?
- ¿Se ha probado una restauración en este período? ¿Con qué resultado y en qué tiempo?
- ¿La HA está funcional? Evidencia: `pg_stat_replication` o reporte de failover.
- Métricas: conexiones máximas alcanzadas, consultas lentas, tamaño de la base.
- Hallazgos y solicitudes al proveedor.

**Alimenta:** obligación mensual del TDR, Producto 3 (validación de desempeño), Producto 9
(indicadores), Producto 10 (informe acumulativo).

---

## 11. Qué preguntar

**Al proveedor** — este archivo vive de estas respuestas:
1. **¿Con qué frecuencia y con qué evidencia se verifican los respaldos de PostgreSQL, y cuándo se puede hacer una prueba de restauración?**
2. ¿Qué tipo de respaldo hacen: lógico, físico, PITR? ¿Cómo se traduce eso en el RPO < 1 h?
3. ¿Cómo accedo a las métricas de la base (conexiones, consultas lentas, replicación) y con qué retención?
4. ¿Cuál es el `max_connections` configurado y cuál es el procedimiento para ampliarlo?
5. ¿Qué acceso administrativo tengo? ¿Puedo crear índices y extensiones?
6. ¿Cómo se valida la HA funcional y con qué frecuencia se prueba el failover?
7. ¿Qué versión exacta de PostgreSQL y PostGIS corre, y cuál es la política de upgrades?
8. ¿Cómo se notifican los mantenimientos que afecten a la base?

**A ESA / Terradue:**
1. ¿Qué bases y esquemas usa el Middleware y cuál es el dimensionamiento esperado?
2. ¿Los índices de PgSTAC vienen fijados por el despliegue o los ajusto yo?
3. ¿Qué pools de conexión configura cada componente?

---

## 12. Fuentes

**Documentos del proyecto:** D2 §2.5 (supuesto DBaaS), §3.2.2 y §3.2.4 (PostgreSQL, PostGIS
y PgSTAC en el catálogo), §3.4.4 (PostgreSQL en el Application Registry vía GitLab), §3.6.4
(en el workspace), §7.14 (PostgreSQL como servicio gestionado), §9.2 (gestión distribuida de
datos). D1 §3.2.1, §4.4, §8.1.2. Pliego §8.5.8 (DBaaS), §8.5.16 (funciones mínimas del
servicio administrado sobre DBaaS), §8.5.17 (SLA, RTO/RPO), Anexo I. **Perfil ESA §2.3.3**
(el texto que define exactamente qué incluye y qué excluye) y tabla §1.1 (*DBaaS – PostgreSQL
Operations — Covered*; *Database Access Management — Covered*).

**Documentación oficial:** `postgresql.org/docs` — Monitoring, Performance Tips.
`postgis.net/documentation`. Para PgSTAC → [05-stac-pgstac-stac-fastapi.md](05-stac-pgstac-stac-fastapi.md).

**Deliberadamente fuera:** tuning interno del motor, configuración de HA, ejecución de
respaldos, parcheo. Es del proveedor. Necesitas el vocabulario para dialogar, no la práctica.

---

## 13. Bitácora / hallazgos

*(Versiones reales, `max_connections`, respaldos verificados con fecha, pruebas de
restauración realizadas, consultas lentas identificadas.)*
