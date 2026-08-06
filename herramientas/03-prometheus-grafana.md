# Prometheus + Grafana — observabilidad del Middleware

**Nivel exigido:** E — lo diseñas, lo optimizas y lo enseñas
**Prioridad:** 1 — núcleo diario
**Competencia de la matriz:** 22

---

## 1. Qué es, aquí

D2 §7.10 y §7.11 describen el par: **Prometheus** recolecta y almacena métricas de los
componentes del sistema (*"scrapes metrics from configured endpoints, stores them, and
allows for real-time querying and analysis"*), desplegado dentro del propio Kubernetes;
**Grafana** las visualiza en dashboards (*"system load, response times, and error rates"*).

D2 §8.5 los suma al marco de seguridad: *"The platform uses tools like Prometheus for
continuous monitoring of system performance and security metrics. This allows for real-time
detection of anomalies or potential security threats."* Y §9.4 los ata a las pruebas de
carga y el *benchmarking* periódico contra métricas de referencia.

Pero la razón por la que este archivo es prioridad 1 no está en D2. Está en el pliego:

> **El monitoreo del proveedor es 8x5. El SLA de incidentes es 24/7.**

Hay una franja —noches, fines de semana, festivos— en la que **la detección depende
exclusivamente de tu observabilidad y de tus alertas**. Si el catálogo se cae un sábado a
las 3 de la mañana, o lo ve tu alerta o lo ve un usuario el lunes.

---

## 2. La frontera

| Materia | Proveedor | Tú |
|---|---|---|
| Métricas, logs y eventos del **clúster** | Sí — y monitoreo 8x5 | Los consumes |
| Métricas del **Middleware** | No | **Sí: instrumentar lo que falte** |
| Dashboards operativos | Reportes mensuales de disponibilidad, incidentes y uso | **Los tuyos, los que usas a diario** |
| Umbrales de alerta | Los suyos, para infraestructura | **Los tuyos, justificados por escrito** |
| Correlación métrica + log + evento | No | **Sí — es el corazón del diagnóstico** |
| Validación del SLA | Reporta sus números | **Mides los tuyos y los contrastas** |

La tabla de brechas del perfil ESA clasifica *Observability* como "Covered" **para
infraestructura**. No lo está para el Middleware. Y no está cubierto en absoluto el trabajo
de correlacionar tres fuentes hasta llegar a la causa — que es lo que de verdad se te va a
pedir.

Tu trabajo aquí **no es diseñar la plataforma de monitoreo**. Es: instrumentar lo que falte
del Middleware, construir los dashboards que usarás a diario, definir umbrales con sentido y
correlacionar hasta la causa raíz.

---

## 3. Qué debes saber

### Nivel imprescindible

**Modelo de datos de Prometheus**
- Tipos de métrica: `counter` (solo sube), `gauge` (sube y baja), `histogram` (buckets +
  `_sum` + `_count`), `summary` (cuantiles precalculados). **Cuándo usar histogram y por qué
  los percentiles se calculan al consultar, no al recolectar.**
- Series temporales: nombre + etiquetas. Cardinalidad: por qué una etiqueta con el ID de
  usuario o el ID de item STAC **mata** a Prometheus.
- Scraping: `ServiceMonitor` / `PodMonitor` (operador) vs anotaciones. `scrape_interval`,
  `scrape_timeout`, `honor_labels`.
- Retención local y su límite. Cuánta historia tienes realmente.

**PromQL — lo que usarás a diario**
- Selectores: `metrica{label="valor", otro=~"regex"}`.
- Rangos: `metrica[5m]` y por qué `rate()` necesita un rango.
- `rate()` vs `irate()` vs `increase()`. **El error clásico es usar `rate` sobre un gauge.**
- Agregación: `sum`, `avg`, `max`, `min`, `count` con `by (…)` y `without (…)`.
- `histogram_quantile(0.95, sum(rate(bucket[5m])) by (le))` — la latencia p95, memorízala.
- Operaciones entre vectores y el problema del *label matching* (`on`, `ignoring`,
  `group_left`).
- Funciones: `absent()`, `changes()`, `predict_linear()`, `clamp_max()`, `topk()`.

**Métricas que importan en esta plataforma**
```promql
# Tasa de errores 5xx de un servicio
sum(rate(http_requests_total{status=~"5..", service="stac-fastapi"}[5m]))
  / sum(rate(http_requests_total{service="stac-fastapi"}[5m]))

# Latencia p95
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{service="stac-fastapi"}[5m])) by (le))

# Reinicios de pods en la última hora
increase(kube_pod_container_status_restarts_total[1h]) > 0

# Pods que no arrancan
kube_pod_status_phase{phase=~"Pending|Unknown"} > 0

# PVC en estado anómalo
kube_persistentvolumeclaim_status_phase{phase!="Bound"}

# Saturación de memoria contra el límite
container_memory_working_set_bytes / on(pod,container)
  kube_pod_container_resource_limits{resource="memory"} > 0.9

# Saturación de CPU (throttling)
rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0

# Jobs fallidos (los workflows de Argo son Jobs)
kube_job_status_failed > 0
```

**Grafana**
- Fuentes de datos, variables de dashboard (`$namespace`, `$service`), *repeat* de paneles.
- Tipos de panel: time series, stat, gauge, table, heatmap, logs.
- Transformaciones y `Instant` vs `Range`.
- Exportar un dashboard a JSON y **versionarlo en Git**. Un dashboard que solo existe en la
  UI no existe.

### Nivel operativo

**Alertas**
- Reglas de alerta (`PrometheusRule`): `expr`, `for`, `labels.severity`, `annotations`.
- El campo `for` es el que evita el ruido: una alerta que dispara con un pico de 10 segundos
  es una alerta que nadie va a mirar.
- Alertmanager: agrupación (`group_by`), inhibición, silencios, rutas por severidad.
- **Cada alerta debe traer escrito por qué ese umbral y qué acción dispara.** Una alerta sin
  acción asociada es ruido con esteroides.

**Presupuesto de error**
- Cómo traducir un objetivo de disponibilidad a minutos concretos, y cómo eso convierte cada
  incidente en una decisión ("¿cuánto puede durar esto antes de ser incumplimiento?").
- Cálculo de disponibilidad medida por ti a partir de una métrica `up` o de un *blackbox
  probe*, no del reporte del proveedor.

**Logs y eventos**
- Cómo correlacionar: la métrica te dice **cuándo y cuánto**, el evento de Kubernetes te
  dice **qué cambió**, el log te dice **por qué**. En ese orden.
- `kubectl get events --sort-by=.lastTimestamp` como tercera pata.
- Si hay un agregador de logs (Loki u otro), cómo consultarlo desde el mismo dashboard.

### Nivel avanzado

- Instrumentar un componente que no expone métricas: exporters, `/metrics` propio.
- Blackbox exporter para medir el catálogo **desde fuera** — así se mide disponibilidad
  real, no salud interna.
- Recording rules para consultas caras que usas en varios dashboards.
- Alertas sobre síntomas y no sobre causas (el usuario no sufre un pod reiniciado; sufre un
  501 en `/search`).
- Correlación entre el throughput de ingesta medido y el compromiso de **0,350 TB/h**.

---

## 4. Los números que mides contra algo

Esta es la razón por la que la observabilidad es E y no O: **eres tú quien valida el SLA del
proveedor**, mensualmente, con evidencia propia.

**Compromisos de la plataforma (D1 §3.2.1, §6):**

| Métrica | Objetivo |
|---|---|
| Disponibilidad | **99,5 % anual** ≈ 44 h/año de caída |
| MTTR | **< 1 hora** |
| Throughput ingesta/procesamiento | **≥ 0,350 TB/h**, picos **3,5 TB/h** |
| Latencia extremo a extremo | **< 1 h** productos estándar |
| Flujos en tiempo real | **≤ 5 min** desde ingesta hasta disponibilidad |
| Usuarios concurrentes | hasta **3.000** |
| Tiempo de respuesta medio | **< 5 s** carga normal, **≤ 7,5 s** pico |
| Utilización de recursos | objetivo **50–70 %** |

**KPIs propuestos por D1:** disponibilidad del sistema (ligada a **ingesta, catálogo y
acceso** — los tres servicios de tu dashboard principal), *Data Ingestion Timeliness*,
capacidad/escalabilidad de usuarios, y **completitud de la oferta de datos** (% de
solicitudes de items exitosas).

**Compromisos del proveedor (pliego §8.5.17):**

| Severidad | Respuesta máx. | Resolución máx. |
|---|---|---|
| Crítico | 15 min | 2 h |
| Alto | 1 h | 4 h |
| Medio | 2 h | 8 h |
| Normal | 4 h | 24 h |

- 24/7, incluidos fines de semana y festivos.
- Disponibilidad **99,95 % mensual** ≈ **43,2 min/mes**, excluyendo mantenimientos avisados
  con ≥ 48 h.
- **RTO < 24 h**, **RPO < 1 h**.
- Penalidad: 4 % de la mensualidad ÷ 30 por cada día calendario o proporcional de afectación.
- Monitoreo **8x5** de SO, Kubernetes y aplicaciones.
- Latencia del almacenamiento caliente: **100 ms lectura / 200 ms escritura**.
- Balanceador: **25.000 RPS** pico, **10.000** conexiones.

**Presupuesto de error, en minutos:**

| Objetivo | Ventana | Caída admisible |
|---|---|---|
| 99,5 % (plataforma, D1) | anual | ≈ **44 h** |
| 99,95 % (proveedor, pliego) | mensual | ≈ **43,2 min** |

Estos dos números conviven y no son el mismo compromiso. Sabrás cuál citar según a quién
tengas delante.

---

## 5. Laboratorio

1. **Instala `kube-prometheus-stack`** (Helm). Explora los dashboards que trae: úsalos como
   referencia de qué se puede medir, no como tu dashboard.
2. **Escribe tus propias consultas PromQL.** Las siete del §3. Ejecútalas en el explorador de
   Prometheus antes de meterlas en un panel.
3. **Construye tu dashboard operativo.** Una sola pantalla, tres bloques: **ingesta,
   catálogo y acceso** — exactamente los tres servicios a los que D1 liga la disponibilidad
   del sistema. Cada bloque: disponibilidad, tasa de error, latencia p95, y una métrica
   propia del dominio (items ingeridos/hora, búsquedas/min, descargas/min).
4. **Define 3 alertas con umbral justificado por escrito.** Para cada una: expresión, `for`,
   severidad, **por qué ese número**, y **qué acción dispara**. Ejemplo de justificación
   buena: *"5xx > 1 % durante 5 min → severidad Alta, porque a esa tasa el KPI de
   completitud de la oferta de datos cae por debajo del objetivo en menos de una hora;
   acción: ejecutar `runbooks/diagnostico-pod.md` sobre stac-fastapi y revisar el pool de
   PostgreSQL."*
5. **Calcula el presupuesto de error.** Traduce el 99,5 % anual y el 99,95 % mensual a
   minutos y escribe la frase: *"este incidente puede durar N minutos antes de ser un
   incumplimiento"*.
6. **Redacta la plantilla del informe mensual de validación del proveedor** (§10).
7. **Instrumenta.** Añade a tu app del laboratorio un `/metrics` con un counter de
   peticiones y un histogram de latencia. Móntalo en el dashboard.
8. **Mide desde fuera.** Añade un blackbox probe contra el catálogo y compara su
   disponibilidad con la métrica interna. Van a diferir; entender por qué es el ejercicio.

---

## 6. Sabotaje obligatorio

**Provoca una caída de 20 minutos del catálogo** (escala a 0, o rompe la conexión a
PostgreSQL) y practica el ciclo completo, cronometrado:

1. **Detectar** — por tu alerta, no mirando la pantalla.
2. **Clasificar** severidad según la tabla del SLA.
3. **Contener** — la acción que restablece el servicio.
4. **Comunicar** — a quién, por qué canal, con qué contenido.
5. **Documentar** causa raíz, impacto (en minutos y en presupuesto de error consumido) y
   acción correctiva.

El criterio de éxito no es arreglarlo. Es que la alerta te haya avisado **antes** de que
tuvieras que mirar.

Otros sabotajes útiles: una etiqueta de alta cardinalidad que degrade Prometheus; una alerta
sin `for` que dispare con cada pico; un dashboard con `rate()` sobre un gauge (verás una
línea plana en cero y tardarás en entender por qué).

---

## 7. Averías de producción que este bloque entrena

Todas. La observabilidad no diagnostica una avería concreta: es lo que convierte cualquiera
de las 18 del catálogo en algo que ves antes de que te llamen. Especialmente relevante para
la 3 (`OOMKilled` bajo carga), la 11 (catálogo lento por índice ausente o pool agotado) y
la 15 (namespace que rechaza pods por cuota agotada) — las tres que son graduales y no
binarias, y que por tanto solo se detectan con métricas.

---

## 8. Consultas de bolsillo

```promql
# ¿Está vivo?
up{job="stac-fastapi"}

# Top 5 pods por memoria
topk(5, container_memory_working_set_bytes{namespace="copernicus"})

# Contenedores reiniciados en 24 h
sort_desc(increase(kube_pod_container_status_restarts_total[24h]))

# Disponibilidad medida en la última hora
avg_over_time(up{job="stac-fastapi"}[1h])

# Predicción: ¿se llena el disco en 4 h?
predict_linear(kubelet_volume_stats_available_bytes[1h], 4*3600) < 0

# Alerta muda (métrica que desapareció — el fallo que nadie detecta)
absent(up{job="stac-fastapi"})
```

Esa última merece un párrafo: **una métrica que deja de existir no dispara ninguna alerta
basada en umbrales**. Si el exportador muere, tus gráficas se quedan planas y todo "parece
bien". `absent()` es la alerta que detecta que dejaste de mirar.

---

## 9. Criterio de dominio

- [ ] Escribo una consulta PromQL de tasa de error 5xx sin consultar nada.
- [ ] Calculo un p95 con `histogram_quantile` y explico por qué el cálculo va en la consulta.
- [ ] Tengo **mi** dashboard operativo: una pantalla, ingesta + catálogo + acceso.
- [ ] Cada una de mis alertas tiene umbral justificado por escrito y acción asociada.
- [ ] Traduzco 99,5 % anual y 99,95 % mensual a minutos de memoria.
- [ ] Correlaciono métrica + evento + log hasta la causa, en ese orden.
- [ ] **Me entero de un fallo por mi alerta y no por un usuario.**
- [ ] Produzco el informe mensual de validación en **menos de 2 horas**.
- [ ] Detecto que un exportador murió, no solo que una métrica cruzó un umbral.

---

## 10. Artefactos que produces

1. **Dashboard exportado a JSON y versionado** en `manifests/observabilidad/`.
2. **Reglas de alerta** (`PrometheusRule`) versionadas, con la justificación de cada umbral
   en un comentario o en un documento adjunto.
3. **`runbooks/gestion-incidentes.md`** — clasificación por severidad según la tabla del
   SLA, contención, comunicación, documentación de causa raíz.
4. **Plantilla del informe mensual de validación del proveedor**, con estas secciones:
   - Disponibilidad **medida por ti** vs. reportada por el proveedor, con la diferencia explicada.
   - Incidentes por severidad, con tiempos de respuesta y resolución **reales** frente a la tabla del SLA.
   - Conectividad (3 Gbps a Europa, ≥ 1 Gbps de salida).
   - Métricas de rendimiento contra los objetivos de D1.
   - Hallazgos y solicitudes formales.

**Alimentan:** obligación mensual del TDR · Producto 1 (validaciones técnicas) ·
Producto 9 (informe de métricas e indicadores operativos) · Producto 10 (informe
acumulativo de validación de entregables del proveedor).

De todos los artefactos de esta carpeta, la plantilla del informe mensual es el de mayor
retorno: la vas a usar 18 veces.

---

## 11. Qué preguntar

**A ESA / Terradue:**
1. ¿Qué métricas expone cada componente del Middleware y existe un conjunto de dashboards y alertas de referencia?
2. ¿Hay convenciones de nombres y etiquetas para las métricas del Middleware?
3. ¿Qué componentes **no** exponen métricas y habría que instrumentar?

**Al proveedor:**
1. ¿Cómo accedo a métricas, logs y eventos del clúster, y con qué retención?
2. ¿Qué contiene exactamente el reporte mensual de disponibilidad, incidentes y uso, y en qué formato lo entregan?
3. **Durante la franja fuera del monitoreo 8x5, ¿cómo se detecta y se abre un incidente crítico?** (Ésta es la pregunta importante.)
4. ¿Cómo se notifican los mantenimientos programados —las 48 h del pliego— y por qué canal? Necesito excluirlos de mi cálculo de disponibilidad.
5. ¿Su medición de disponibilidad es por *ping* al nodo, por API de Kubernetes, o por servicio? Necesito saber contra qué comparo.

---

## 12. Fuentes

**Documentos del proyecto:** D2 §7.10 (Prometheus), §7.11 (Grafana), §8.5 (Monitoring and
Auditing), §8.6 (Incident Response), §9.4 (Load Testing and Benchmarking), §9.5 (Resource
Management — Prometheus y Grafana para consumo de recursos), §3.8.4. D1 §3.2.1 (requisitos
de rendimiento), §7.5 (Performance Metrics), §7.4 (especificaciones operativas). Pliego
§8.5.17 (SLA, severidades, penalidades, monitoreo 8x5), §8.5.3. Perfil ESA §2.4.

**Documentación oficial:** `prometheus.io/docs` (especialmente PromQL y las *best practices*
de naming y cardinalidad), `grafana.com/docs`. Chart: `kube-prometheus-stack`.

---

## 13. Bitácora / hallazgos

*(Métricas reales que expone cada componente, umbrales que ajustaste y por qué, alertas que
resultaron ser ruido, incidentes detectados por tu alerta.)*
