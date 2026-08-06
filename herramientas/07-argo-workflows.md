# Argo Workflows — el motor de flujos

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 2 — alto y **desatendido**: el contrato del proveedor no lo cubre
**Competencia de la matriz:** 13 (junto con [08-argo-events.md](08-argo-events.md))

---

## 1. Qué es, aquí

Argo Workflows es **el motor que ejecuta la ingesta y el procesamiento**. Es el corazón
funcional de la plataforma: si Argo no corre, no entran datos nuevos y no se procesa nada.

D2 §7.7 lo define: *"an open-source container-native workflow engine for orchestrating
parallel jobs on Kubernetes… used to define, schedule, and execute complex workflows that
involve multiple steps and dependencies"*.

Aparece en dos componentes:

**Data Ingestion** (D2 §3.1.4, §4.1): orquesta los pipelines de ingesta, *"ensuring that
each step in the process is executed in the correct order and that dependencies are managed
effectively"*. Y con un matiz importante: los tres niveles de ingesta se manejan con
workflows de distinto peso —

> *"Metadata-only ingestion workflows are lightweight and emphasize speed and compliance.
> Full dataset ingestion workflows manage larger data volumes and include validation for
> data integrity and completeness. Calibration workflows leverage Argo's flexibility to
> include custom processing tasks."*

**Data Processing** (D2 §3.3.2): *"manages the execution of complex processing pipelines.
These pipelines are defined using the CWL and orchestrate various tasks such as data
validation, transformation, and analysis… managing dependencies, scheduling tasks, and
handling retries and failures."*

La relación con las piezas vecinas, que conviene tener clara desde el principio:

| Pieza | Papel |
|---|---|
| **Argo Events** | Dispara el workflow cuando llega un evento → [08](08-argo-events.md) |
| **Argo Workflows** | Orquesta los pasos, gestiona dependencias, reintentos y fallos |
| **CWL** | Describe *qué* hace cada aplicación EO → [15](15-cwl-calrissian.md) |
| **Calrissian** | Ejecuta el CWL dentro de Kubernetes → [15](15-cwl-calrissian.md) |
| **Harbor** | De donde salen las imágenes de cada paso → [10](10-harbor.md) |
| **S3/MinIO** | Donde viven los artefactos de entrada y salida → [06](06-s3-minio.md) |

---

## 2. La frontera

Enteramente tuyo. La tabla del perfil ESA lo agrupa en *"Platform Domains Support
(Copernicus) — ingestion, catalog, **workflows**, registry, workspace — **Not covered**"*.

El proveedor ve pods que arrancan y mueren. No sabe qué es un `Workflow`, ni por qué el paso
3 falló, ni qué significa un exit code 2 en un Application Package. Cuando escales un
incidente de Argo al proveedor, la respuesta correcta de su parte será "el clúster funciona",
y tendrá razón.

---

## 3. Qué debes saber

### Nivel imprescindible

**Objetos**
- `Workflow`: una ejecución concreta. Es el objeto que vas a inspeccionar mil veces.
- `WorkflowTemplate` y `ClusterWorkflowTemplate`: plantillas reutilizables. La ingesta usa
  plantillas: D3 §3.2.2 dice que *"the ingestion workflow then reads the application workflow
  template from the Registry"*.
- `CronWorkflow`: workflows programados.
- Relación con Kubernetes: **cada paso es un pod**. Todo lo que sabes de
  [01-kubernetes.md](01-kubernetes.md) aplica al diagnóstico.

**Anatomía de un workflow**
- `entrypoint` y `templates`.
- Tipos de template: `container`, `script`, `dag`, `steps`, `resource`, `suspend`.
- `steps` (secuencial, con paralelismo por lista anidada) vs `dag` (por dependencias con
  `depends`). Cuándo usar cada uno.
- Parámetros: `inputs.parameters`, `outputs.parameters`, `arguments`, y cómo se pasan entre
  pasos (`{{steps.x.outputs.parameters.y}}`, `{{tasks.x.outputs...}}`).
- Artefactos: `inputs.artifacts`, `outputs.artifacts`, y el **artifact repository** apuntando
  a S3/MinIO. Esta es la integración que más falla.
- Variables globales: `{{workflow.name}}`, `{{workflow.uid}}`, `{{pod.name}}`,
  `{{workflow.parameters.x}}`.

**Ejecución y control**
- `activeDeadlineSeconds`, `retryStrategy` (`limit`, `retryPolicy`, `backoff`),
  `parallelism`, `podGC`, `ttlStrategy`.
- `podGC` y `ttlStrategy` no son opcionales en producción: **sin ellos los pods `Completed`
  se acumulan** hasta llenar el namespace. Es uno de los sabotajes obligatorios.
- `onExit` para limpieza y notificaciones.
- `ServiceAccount` del workflow: qué permisos necesita (crear pods, leer secretos).

**Diagnóstico**
- La CLI `argo`: `list`, `get`, `logs`, `watch`, `retry`, `resubmit`, `terminate`, `stop`,
  `delete`.
- Diferencia entre `retry` (reintenta desde el paso fallido) y `resubmit` (empieza de cero).
- La UI de Argo: el grafo del DAG con los pasos en color. Es la herramienta más rápida para
  ver **dónde** falló.
- Estados: `Pending`, `Running`, `Succeeded`, `Failed`, `Error`. `Failed` = el contenedor
  devolvió exit code ≠ 0. `Error` = el sistema no pudo ejecutarlo.

### Nivel operativo

- Plantillas parametrizadas para la ingesta: una plantilla, N colecciones.
- Integración con el artifact repository: `ConfigMap` `artifact-repositories`, secreto con
  las credenciales de MinIO/S3, `key` y `bucket` por artefacto.
- Recursos por paso: `requests`/`limits` en cada template. Un paso de GDAL sin límite de
  memoria es un `OOMKilled` esperando ocurrir.
- Sincronización y semáforos: limitar cuántas ingestas concurrentes hay. Esto es
  **backpressure**, una de las competencias que ESA marca como no cubierta.
- `exit code` de las aplicaciones: D3 §3.2.4 define el contrato —
  > *"Upon successful execution, the system returns an exit code indicating the success of
  > the ingestion process. If the application runs successfully, a message is pushed onto
  > the **success topic** in the Event Bus. In the case of failure, the system pushes a
  > message onto the **failure topic**."*
- Manejo de errores según D2 §4.2, por nivel de ingesta:
  - Metadata-only: marca los metadatos incompletos para revisión manual.
  - Copiado de dataset: reintenta descarga o validación; si no se resuelve, alerta.
  - Calibración: aísla y registra los datos problemáticos sin interrumpir el flujo mayor.
- Y D3 §3.5.1: *"the system will move the problematic data to temporary storage and notify
  the monitoring system"*. **Debes saber dónde está ese almacenamiento temporal.**

### Nivel avanzado

- Argo Workflows como orquestador de Calrissian: quién lanza a quién.
- Estrategias de reintento diferenciadas por tipo de fallo (transitorio vs. determinista).
- Métricas de Argo en Prometheus: workflows por estado, duración, cola. Es lo que alimenta
  el KPI de *Data Ingestion Timeliness*.
- Dimensionamiento contra el compromiso de **≥ 0,350 TB/h**, picos de **3,5 TB/h** y
  latencia extremo a extremo **< 1 h** (y **≤ 5 min** para flujos en tiempo real).
- Reprocesamiento masivo: rehacer una colección entera sin duplicar items.

---

## 4. El flujo de ingesta que debes saber dibujar de memoria

Reconstruido de D2 §3.1, §4.2 y D3 §3:

```
1. Llega el evento al Event Bus (Kafka, topic de nueva adquisición)
2. El Workflow Engine (Argo) lee la plantilla del workflow desde el Registry
   y obtiene las imágenes de ingesta
3. Se instancia y ejecuta la aplicación de ingesta:
     · Format Assertion — ¿el formato es aceptado? (GeoTIFF, COG, .zip)
     · Selección del Application Package — según las propiedades del STAC Item
     · Validación y pre-procesamiento — según el nivel de ingesta:
         - metadata-only:  integridad y conformidad STAC
         - copiado:        checksum + comprobaciones estructurales
         - calibración:    validaciones específicas + transformación
     · Extracción de metadatos según STAC
     · Enriquecimiento para visualización (COG + render + web-map-links)
4. Catalog Registry — se publica el STAC Item en la STAC FastAPI
5. Asset Loading — el producto se guarda en el bucket S3 de datos
6. Exit code:
     éxito → mensaje al topic de éxito
     fallo → mensaje al topic de fallo,
             el dato problemático va a almacenamiento temporal,
             se notifica al monitoreo
```

**Las seis preguntas que este flujo te obliga a poder responder** (son literalmente tu árbol
de diagnóstico):

1. ¿El evento llegó al topic?
2. ¿El workflow se instanció?
3. ¿La imagen se pudo bajar del registry?
4. ¿El item se posteó al catálogo?
5. ¿El objeto quedó en el bucket?
6. ¿Qué código de salida devolvió?

**Los tres niveles de ingesta** (D2 §3.1.1) — te los van a preguntar:

| Nivel | Qué hace | Dónde queda el dato |
|---|---|---|
| **Registro de metadatos** | Cataloga metadato y punto de acceso | En el origen |
| **Registro + copia** | Descarga, valida checksum, guarda | En S3 de la plataforma |
| **Registro + calibración** | Además preprocesa (georreferenciación, conversión) | En S3, transformado |

---

## 5. Laboratorio

**Bloque 6 de la ruta de práctica — 12 horas** (compartido con [08-argo-events.md](08-argo-events.md)
y [15-cwl-calrissian.md](15-cwl-calrissian.md)).

1. **Instala Argo Workflows** en tu clúster `kind`. Accede a la UI.
2. **Workflow de varios pasos.** Un `steps` con tres pasos que se pasan parámetros. Obsérvalo
   en la UI mientras corre.
3. **Artefactos en MinIO.** Configura el artifact repository apuntando a tu MinIO del
   [bloque 5](06-s3-minio.md). Un paso genera un archivo, el siguiente lo consume. **Esta
   integración es la que más falla en producción; hazla funcionar y documenta cómo.**
4. **DAG.** Convierte el mismo flujo a `dag` con dependencias y observa la paralelización.
5. **Tu flujo de ingesta simulado** — el ejercicio central del bloque:
   ```
   evento → descarga del asset → validación de checksum
          → publicación del STAC Item en la API del bloque 4
          → subida del objeto al bucket del bloque 5
          → mensaje al topic de éxito o de fallo
   ```
   Cinco eslabones reales, con los nombres reales de la plataforma.
6. **Reintentos.** Añade `retryStrategy` a un paso que falla de forma intermitente. Observa
   el backoff.
7. **Limpieza.** Configura `podGC` y `ttlStrategy`. Comprueba que los pods desaparecen.
8. **Plantilla.** Convierte tu workflow en un `WorkflowTemplate` parametrizado por colección
   y lánzalo con dos colecciones distintas.

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Un paso con imagen sin permisos de pull | `ImagePullBackOff` dentro de un workflow: dónde aparece el error realmente |
| Artefacto que no se sube por falta del secreto de MinIO | El fallo más común de la integración con S3 |
| Paso que devuelve exit code ≠ 0 | Cómo se propaga a `Failed` y qué mensaje va al topic de fallo |
| Workflow sin `podGC` | Pods `Completed` acumulados hasta agotar la cuota del namespace |
| Paso sin límite de memoria procesando un raster grande | `OOMKilled` en el paso 3 |
| Parámetro mal referenciado entre pasos | Error de plantilla; cómo leerlo |
| Imagen sin GDAL en un paso que lo necesita | Avería 9 del catálogo |
| `ServiceAccount` sin permisos para crear pods | El workflow queda `Pending` sin explicación obvia |

---

## 7. Averías de producción que este bloque entrena

- **Avería 9:** workflow que falla en el paso 3 — imagen sin GDAL.
- **Avería 8:** ingesta que no arranca — pero ojo, ésa es de Argo Events
  ([08](08-argo-events.md)); saber distinguirlas es parte del ejercicio.
- Contribuye a la **10** (item ingerido que no aparece): si el paso de publicación falló
  silenciosamente, el síntoma aparece en el catálogo.

---

## 8. Árbol de diagnóstico: "la ingesta falló"

Sigue el orden del flujo. **Cada pregunta descarta un eslabón.**

1. **¿Llegó el evento?** → Kafka: ¿hay mensaje en el topic? ¿alguien lo consumió?
   ([20-kafka.md](20-kafka.md))
2. **¿Disparó el sensor?** → `kubectl logs` del Sensor de Argo Events; ¿el filtro coincide?
   ([08-argo-events.md](08-argo-events.md))
3. **¿Se creó el Workflow?** → `argo list -n <ns>`. Si no está, el problema es anterior.
4. **¿En qué paso falló?** → `argo get <wf>` o la UI. El grafo te lo dice de un vistazo.
5. **¿Por qué falló ese paso?** → `argo logs <wf> -c <contenedor>`, y `kubectl describe pod`
   del pod del paso si es un fallo de infraestructura (imagen, recursos, volumen).
6. **¿Qué exit code devolvió?** → determina si el mensaje fue al topic de éxito o de fallo.
7. **¿El item se posteó?** → logs de stac-fastapi, y `GET /collections/{id}/items/{item-id}`
   ([05](05-stac-pgstac-stac-fastapi.md)).
8. **¿El objeto quedó en el bucket?** → `mc stat` ([06](06-s3-minio.md)).
9. **¿Dónde está el dato problemático?** → almacenamiento temporal (D3 §3.5.1).

---

## 9. Comandos de bolsillo

```bash
# Ver qué está pasando
argo list -n <ns>
argo list -n <ns> --status Failed
argo get <workflow> -n <ns>              # el grafo con el estado de cada paso
argo logs <workflow> -n <ns> --follow
argo logs <workflow> -n <ns> -c <contenedor>

# Actuar
argo retry <workflow> -n <ns>            # desde el paso fallido
argo resubmit <workflow> -n <ns>         # desde cero
argo terminate <workflow> -n <ns>        # para ya
argo stop <workflow> -n <ns>             # para tras ejecutar onExit
argo submit plantilla.yaml -p coleccion=sentinel-2 -n <ns> --watch

# Desde kubectl (útil cuando la CLI no está)
kubectl get workflows -n <ns>
kubectl get wf -n <ns> -o custom-columns=NAME:.metadata.name,STATUS:.status.phase
kubectl get pods -n <ns> -l workflows.argoproj.io/workflow=<workflow>
kubectl describe wf <workflow> -n <ns>

# Limpieza de emergencia
kubectl delete pods -n <ns> --field-selector status.phase==Succeeded
```

---

## 10. Criterio de dominio

- [ ] Dibujo el flujo de ingesta completo de memoria, con sus seis preguntas de diagnóstico.
- [ ] Explico los tres niveles de ingesta y qué cambia en el workflow de cada uno.
- [ ] Lanzo, sigo, reintento y depuro un workflow sin consultar nada.
- [ ] Configuro artefactos contra MinIO y diagnostico cuando fallan.
- [ ] Distingo `Failed` (exit code) de `Error` (el sistema no pudo ejecutarlo).
- [ ] Sé la diferencia entre `retry` y `resubmit` y cuándo usar cada uno.
- [ ] Configuro `podGC` y `ttlStrategy`, y explico qué pasa sin ellos.
- [ ] **Rompo cualquiera de los cinco eslabones de mi pipeline y encuentro cuál en menos de 10 minutos.**

---

## 11. Artefactos que produces

1. **El pipeline de ingesta simulado, versionado** en `manifests/ingesta/`.
2. **`runbooks/ingesta-fallida.md`** — el árbol de diagnóstico del §8, con los comandos
   exactos de cada paso: ¿llegó el evento? ¿se creó el workflow? ¿qué paso falló? ¿qué exit
   code? ¿dónde quedó el dato?

**Alimentan:** Producto 2 (runbooks iniciales), Producto 3 (estabilización: la ingesta es
uno de los servicios críticos), Producto 4 (caso práctico de transferencia — es el mejor
ejercicio para enseñar, porque toca cinco componentes a la vez).

---

## 12. Qué preguntar

**A ESA / Terradue:**
1. ¿Dónde viven las `WorkflowTemplate` de ingesta y quién las mantiene? ¿Puedo añadir una para una colección nueva?
2. **¿Cuál es el procedimiento de reprocesamiento cuando una ingesta falla parcialmente?**
3. ¿Dónde está el "almacenamiento temporal" al que van los datos problemáticos, y cuál es el procedimiento de revisión manual?
4. ¿Qué exit codes usan los Application Packages y qué significa cada uno?
5. ¿Qué métricas expone Argo Workflows y hay dashboards de referencia?
6. ¿Qué límites de concurrencia hay configurados y quién los ajusta?
7. ¿La ingesta desde CDSE es por harvesting programado o por notificación? ¿Con qué frecuencia?

---

## 13. Fuentes

**Documentos del proyecto:** D2 §3.1 (Data Ingestion completo: propósito, implementación,
puntos de integración, stack), §3.3.2 (Processing Workflow Engine), §3.3.4 (stack de
procesamiento), §4.1 (tecnologías de ingesta), §4.2 (flujo de ingesta paso a paso y manejo de
errores), §4.3 (selección del Application Package), §4.4 (validación por nivel), §7.7 (Argo
Workflows), §9.3 (optimización con procesamiento paralelo). D3 §3 completo (§3.2.2 validación
inicial, §3.2.3 ejecución, §3.2.4 exit codes, §3.5.1 detección de errores, §3.5.2 logging).
Perfil ESA §1.1 (*Platform Domains Support — Not covered*).

**Documentación oficial:** `argoproj.github.io/argo-workflows` — Walk Through, Fields
reference, Artifact Repository.

---

## 14. Bitácora / hallazgos

*(Plantillas reales, exit codes observados, fallos de artefactos y su causa, tiempos de
ingesta medidos.)*
