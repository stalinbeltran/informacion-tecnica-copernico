# Argo Events — el disparador

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 2 — alto y **desatendido**
**Competencia de la matriz:** 13 (junto con [07-argo-workflows.md](07-argo-workflows.md))

---

## 1. Qué es, aquí

Argo Events es lo que convierte "llegó un dato" en "arrancó un workflow". Es el eslabón
invisible: cuando funciona nadie lo menciona, y cuando falla el síntoma es **"la ingesta no
arranca"** sin ningún error a la vista.

D2 §3.3.2 lo describe junto a su bus:

> *"The Argo Events event bus, **powered by Apache Kafka**, handles the communication between
> different parts of the system. It ensures that data is passed from the ingestion component
> to the processing workflows, and it also handles notifications and triggers for processing
> tasks."*

Y le asigna dos funciones concretas:
- **Data Flow Management**: gestiona el flujo de datos entre el componente de descubrimiento
  y los workflows de procesamiento.
- **Notification and Triggering**: *"handles notifications and triggers for processing tasks,
  ensuring that workflows are executed when data becomes available"*.

D2 §3.1.4, sobre la ingesta, es aún más directo: *"Apache Kafka is used for managing the
**Argo Events event-driven data ingestion process bus**"*.

**La arquitectura completa de la plataforma es orientada a eventos** (D2 §3.1.2:
*"An event-driven approach underpins the ingestion system, utilizing event buses to manage
the flow of data through the pipeline"*). Argo Events es donde esa arquitectura se
materializa.

---

## 2. La frontera

Tuyo entero — *Platform Domains Support: workflows → Not covered*. El proveedor no tiene
visibilidad de esta capa.

Matiz importante: **Kafka** es el bus por debajo. Si Kafka se despliega como parte del
Middleware (dentro del clúster), es tuyo. Si fuera un servicio gestionado, sería frontera
compartida. Confirma cuál es el caso con ESA (§11) — es una de las primeras cosas que debes
saber. Ver [20-kafka.md](20-kafka.md).

---

## 3. Qué debes saber

### Nivel imprescindible — los tres objetos

Argo Events tiene exactamente tres piezas, y la mayoría de los fallos son de la tercera.

**`EventBus`**
- El transporte. Puede ser NATS (por defecto) o **Kafka** (que es lo que usa esta
  plataforma).
- Se despliega una vez por namespace. Si no está, nada funciona y el error es poco
  descriptivo.

**`EventSource`**
- De dónde vienen los eventos. Tipos: `webhook`, `kafka`, `calendar`, `s3`/`minio`,
  `resource` (cambios en objetos de Kubernetes), `sqs`, `github`…
- Para esta plataforma los relevantes son **`kafka`** (el topic de nueva adquisición) y
  **`webhook`** (para pruebas y para integraciones externas).
- Cada EventSource crea un Deployment propio. Si no hay pod, no hay escucha.

**`Sensor`** — donde vive el 80 % de los problemas
- `dependencies`: a qué EventSource escucha, y con qué **filtros**.
- `triggers`: qué crea cuando se cumple. Típicamente un `Workflow` de Argo.
- **Filtros**: por `data` (contenido del mensaje, con expresiones sobre JSON), por `context`,
  por `time`, por `exprLogicalOperator`. **Un filtro que no coincide produce silencio
  absoluto: ni error, ni workflow, ni log evidente.** Es la avería 8 del catálogo.
- **Parámetros**: cómo se extrae un valor del evento y se inyecta en el workflow
  (`parameters` con `src.dependencyName`, `src.dataKey`, `dest`). Sin esto, el workflow
  arranca pero sin saber qué procesar.
- `ServiceAccount` del Sensor: necesita permiso para **crear Workflows**. Si no lo tiene, el
  sensor dispara y el trigger falla.

### Nivel operativo

- **Comprobar la cadena completa**, eslabón por eslabón (§8). Es la habilidad central de
  este archivo.
- Política de reintentos del trigger (`retryStrategy`).
- Idempotencia: qué pasa si el mismo evento llega dos veces. En una plataforma de ingesta,
  procesar dos veces el mismo producto genera items duplicados.
- `atLeastOnce` vs entrega normal, y sus implicaciones.
- Logs de cada pieza: EventSource, Sensor, y el pod del trigger. Son tres sitios distintos.
- Correlación con Kafka: `consumer group` del EventSource, y su **lag**. Un lag creciente
  significa que los eventos llegan más rápido de lo que se procesan → backpressure.

### Nivel avanzado

- Diseño de topics y filtros para múltiples colecciones sin duplicar sensores.
- Dead letter: qué hacer con eventos que fallan repetidamente.
- Los tres topics del flujo de ingesta (D3 §3.2.2 y §3.2.4): **nueva adquisición**,
  **éxito**, **fallo**. Quién consume el de éxito y el de fallo, y qué hace con ellos.
- Alertas sobre eventos que no producen workflow — la métrica que detecta un filtro roto
  antes de que alguien pregunte por qué no hay datos nuevos.

---

## 4. El contrato de eventos de la plataforma

De D3 §3 y D2 §4.2, los tres topics que estructuran la ingesta:

| Topic | Quién publica | Quién consume | Qué contiene |
|---|---|---|---|
| **Nueva adquisición** | Fuente externa / harvester (CDSE, Centro de Chile) | EventSource → Sensor → Workflow de ingesta | Notificación de dato disponible |
| **Éxito** | La aplicación de ingesta, al terminar con exit code 0 | Monitoreo, procesos aguas abajo | Confirmación de ingesta completada |
| **Fallo** | La aplicación de ingesta, al fallar | **Monitoreo** (D3 §3.5.1) | Qué falló; el dato va a almacenamiento temporal |

Secuencia textual de D3 §3.2.2:

> *"Upon receiving the data, the system triggers the ingestion process via the **Event Bus**,
> which handles the topic related to new data acquisition. The ingestion workflow then reads
> the application workflow template from the **Registry** and obtains the necessary ingestion
> images."*

Y de D3 §3.2.4:

> *"Upon successful execution, the system returns an exit code… If the application runs
> successfully, a message is pushed onto the **success topic**… In the case of failure, the
> system pushes a message onto the **failure topic**."*

Y de D3 §3.5.1:

> *"If any issues arise, such as incorrect file formats or invalid STAC Items, the system
> will move the problematic data to **temporary storage** and **notify the monitoring
> system**."*

Ese último punto es el puente entre este archivo y
[03-prometheus-grafana.md](03-prometheus-grafana.md): **el topic de fallo debería tener una
alerta encima**. Si no la tiene, las ingestas fallan en silencio.

---

## 5. Laboratorio

Parte del **Bloque 6 — 12 horas**, compartido con Argo Workflows.

1. **Instala Argo Events.** Crea el `EventBus` en tu namespace.
2. **EventSource de tipo webhook.** El más simple para empezar. Expón el puerto.
3. **Sensor** que escucha ese webhook y dispara un `Workflow` de "hola mundo".
4. **Emite el evento con `curl`** y comprueba **la cadena completa**: el pod del EventSource
   recibió, el Sensor evaluó, el Workflow se creó. Mira los logs de los tres.
5. **Añade un filtro.** Que solo dispare si el JSON del evento tiene
   `"collection": "sentinel-2"`. Emite un evento que **sí** coincide y otro que **no**.
   Observa la diferencia — y sobre todo observa **qué se ve en los logs cuando no coincide**
   (respuesta: casi nada; ése es el aprendizaje).
6. **Parámetros.** Extrae el ID del producto del evento e inyéctalo como parámetro del
   workflow. Comprueba que llegó con `argo get`.
7. **EventSource de tipo Kafka.** Si levantas Kafka en el laboratorio, conecta el
   EventSource a un topic real y publica con `kafka-console-producer`. Es lo más parecido a
   producción.
8. **Cierra el círculo.** Conecta este sensor con el pipeline de ingesta del
   [bloque 6](07-argo-workflows.md): evento → sensor → workflow → catálogo → bucket → topic
   de éxito.

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| **Sensor con un filtro que no coincide** | El silencio absoluto. La avería 8. Cómo detectarla |
| EventBus no desplegado | El error poco descriptivo que produce |
| `ServiceAccount` del Sensor sin permiso para crear Workflows | El sensor dispara, el trigger falla, y el error está en un tercer log |
| EventSource apuntando a un topic inexistente | Cómo se ve en los logs vs. cómo se ve un filtro que no casa |
| Parámetro mal mapeado (`dataKey` equivocado) | Workflow que arranca sin saber qué procesar |
| Emitir el mismo evento dos veces | Items duplicados: por qué la idempotencia importa |
| Detener el consumidor y acumular mensajes | Lag creciente en Kafka; qué pasa al reanudar |

---

## 7. Averías de producción que este bloque entrena

**Avería 8: ingesta que no arranca — sensor con filtro que no coincide.**

Merece atención especial porque es **la avería más difícil del catálogo**: no hay error, no
hay pod fallido, no hay alerta. Solo la ausencia de algo que debería haber ocurrido. Se
detecta comparando *eventos recibidos* contra *workflows creados* — que es por qué necesitas
esa métrica en tu dashboard.

---

## 8. Árbol de diagnóstico: "la ingesta no arranca"

Cada paso descarta un eslabón. **Si te saltas el 1, vas a perder una hora.**

1. **¿Existe el mensaje en el topic?**
   → `kafka-console-consumer --from-beginning --topic <topic> --max-messages 5`
   Si no hay mensaje, el problema es de la fuente, no tuyo.
2. **¿El EventSource está vivo y conectado?**
   → `kubectl get pods -l eventsource-name=<nombre>` y sus logs. ¿Se conectó al bus?
   ¿Hay errores de autenticación con Kafka?
3. **¿El EventSource recibió el evento?**
   → Sus logs deberían mostrarlo. Si el mensaje está en el topic pero el EventSource no lo
   ve, mira el **consumer group** y su offset: puede estar leyendo desde un punto posterior.
4. **¿El Sensor lo evaluó?**
   → `kubectl logs -l sensor-name=<nombre>`. Aquí verás si llegó y si pasó el filtro.
5. **¿El filtro coincide?** → **Éste es el sospechoso número uno.** Compara carácter a
   carácter el filtro con el JSON real del evento. Mayúsculas, tipos (¿`"10"` o `10`?),
   rutas anidadas.
6. **¿El trigger tiene permisos?**
   → `kubectl auth can-i create workflows --as=system:serviceaccount:<ns>:<sa-del-sensor>`
7. **¿Se creó el Workflow?**
   → `argo list -n <ns> --since 10m`. Si está aquí, el problema ya no es de Argo Events →
   [07-argo-workflows.md](07-argo-workflows.md).

---

## 9. Comandos de bolsillo

```bash
# Estado de las tres piezas
kubectl get eventbus,eventsource,sensor -n <ns>

# Logs de cada eslabón (son tres sitios distintos)
kubectl logs -n <ns> -l eventsource-name=<nombre> --tail=100
kubectl logs -n <ns> -l sensor-name=<nombre> --tail=100
argo list -n <ns> --since 10m

# Emitir un evento de prueba a un webhook
kubectl port-forward -n <ns> svc/<eventsource-svc> 12000:12000
curl -X POST -H "Content-Type: application/json" \
  -d '{"collection":"sentinel-2","id":"S2A_TEST_001"}' \
  http://localhost:12000/ingesta

# Ver la definición efectiva del filtro
kubectl get sensor <nombre> -n <ns> -o yaml | yq '.spec.dependencies'

# Permisos del sensor
kubectl auth can-i create workflows -n <ns> \
  --as=system:serviceaccount:<ns>:<sa-del-sensor>

# Kafka: ¿está el mensaje? ¿hay lag?
kafka-console-consumer --bootstrap-server <bs> --topic <topic> \
  --from-beginning --max-messages 5
kafka-consumer-groups --bootstrap-server <bs> --describe --group <grupo>
```

---

## 10. Criterio de dominio

- [ ] Explico qué hace un `Sensor` y **cómo compruebo que disparó**.
- [ ] Nombro los tres objetos de Argo Events y qué hace cada uno.
- [ ] Nombro los tres topics del flujo de ingesta y quién publica y consume en cada uno.
- [ ] Verifico la cadena completa evento → EventSource → Sensor → Workflow, eslabón por eslabón.
- [ ] Diagnostico un filtro que no coincide **sin** que haya ningún mensaje de error.
- [ ] Extraigo un valor del evento y lo inyecto como parámetro del workflow.
- [ ] Sé mirar el lag del consumer group y qué significa que crezca.
- [ ] Entiendo por qué el topic de fallo debe tener una alerta encima.

---

## 11. Artefacto que produces

Forma parte de **`runbooks/ingesta-fallida.md`** (ver [07-argo-workflows.md](07-argo-workflows.md)):
la primera mitad del árbol de diagnóstico —*¿llegó el evento? ¿disparó el sensor?*— es este
archivo.

Añade además una **alerta sobre el topic de fallo** a tus reglas de Prometheus, y una
métrica de *eventos recibidos vs. workflows creados*. Esa métrica es lo único que detecta un
filtro roto.

**Alimenta:** Producto 2 (runbooks), Producto 3 (estabilización de la ingesta).

---

## 12. Qué preguntar

**A ESA / Terradue:**
1. ¿Kafka se despliega como parte del Middleware (dentro del clúster) o se espera un servicio gestionado? **De esto depende de quién es la frontera.**
2. ¿Cuáles son los nombres reales de los topics de nueva adquisición, éxito y fallo?
3. ¿Cuál es el esquema del mensaje de cada topic? Necesito el JSON exacto para escribir filtros.
4. ¿Quién consume el topic de éxito y el de fallo? ¿Hay un consumidor de monitoreo ya definido?
5. ¿La ingesta desde CDSE se dispara por notificación o por harvesting programado?
6. ¿Qué garantías de entrega hay y cómo se maneja un evento duplicado?
7. ¿Existen sensores por colección o uno genérico con filtros?

---

## 13. Fuentes

**Documentos del proyecto:** D2 §3.1.2 (arquitectura orientada a eventos), §3.1.4 (Kafka
como bus de Argo Events en la ingesta), §3.3.2 (Event Bus: Data Flow Management y
Notification and Triggering; Event-Driven Workflow), §3.3.4 (Argo Events en el stack de
procesamiento), §4.2 (manejo de errores por nivel de ingesta), §7.8 (Kafka). D3 §3.2.2
(disparo vía Event Bus y lectura de la plantilla desde el Registry), §3.2.4 (exit codes y
topics de éxito/fallo), §3.5.1 (detección de errores, almacenamiento temporal, notificación
al monitoreo), §3.5.2 (logging).

**Documentación oficial:** `argoproj.github.io/argo-events` — Concepts (EventBus,
EventSource, Sensor), Filters, Triggers.

---

## 14. Bitácora / hallazgos

*(Nombres reales de topics, esquemas de mensaje, filtros que fallaron y por qué, lag
observado.)*
