# ZOO Project / OGC API – Processes

**Nivel exigido:** C — puedo explicarlo y decidir a quién escalar
**Prioridad:** 4 — contexto para dialogar y escalar
**Competencia relacionada:** 15 (a través de [15-cwl-calrissian.md](15-cwl-calrissian.md))

---

## 1. Qué es, aquí

ZOO Project es la implementación de **OGC API – Processes** que expone las aplicaciones EO
como servicios web. Es la puerta por la que un usuario del portal —o un sistema externo—
lanza un procesamiento sin saber nada de Kubernetes ni de CWL.

D2 §7.12:

> *"The ZOO Project is an open-source platform that provides a framework for implementing and
> deploying Web Processing Services (WPS)… utilised to handle geospatial processing tasks,
> allowing EO applications to be **exposed as web services** that can be accessed and executed
> via standard protocols."*

Y D2 §3.3.2 le asigna dos funciones bien delimitadas dentro del **Application Execution
Engine**:

| Función | Estándar | Qué hace |
|---|---|---|
| **Deployment** | **OGC API – Processes, Parte 2** | *"handles the submission of EO application packages described using CWL. This involves specifying parameters, software items, executables, dependencies, and metadata."* |
| **Execution** | **OGC API – Processes, Parte 1** | *"initiates and manages the processing jobs… providing necessary input parameters… Handles task scheduling, monitoring, and the retrieval of outputs."* |

Su lugar en la cadena:

```
Front-end / cliente externo
        │  (OGC API – Processes)
        ▼
   ZOO Project  ──▶  Argo Workflows  ──▶  Calrissian  ──▶  pods de cada paso
                          │
                          └── Application Package (CWL + imagen de Harbor)
```

---

## 2. Por qué es nivel C y no O

Porque es una **fachada**. Cuando algo falla en un procesamiento lanzado por ZOO, la causa
casi nunca está en ZOO: está en el workflow, en la imagen, en los datos de entrada o en los
permisos. ZOO te dirá que el job falló; el diagnóstico ocurre aguas abajo.

Lo que necesitas de este archivo es: **saber leer la API lo suficiente para localizar el job,
ver su estado y su error, y saltar al componente correcto.** Eso es nivel conceptual con una
pizca de operación.

Si en la operación real resulta que ZOO da problemas propios (configuración, autenticación,
despliegue de procesos), sube este archivo a nivel O y añádelo a tu plan.

---

## 3. Qué debes saber

### Nivel conceptual

**El modelo de OGC API – Processes**
- **Process**: una capacidad de procesamiento publicada, con sus entradas y salidas
  descritas.
- **Job**: una ejecución concreta de un process, con su identificador y su estado.
- **Estados de un job**: `accepted`, `running`, `successful`, `failed`, `dismissed`.
- **Modos de ejecución**: síncrono (respuesta inmediata, para procesos rápidos) y asíncrono
  (devuelve un job ID y consultas después). En EO, **casi todo es asíncrono**.
- **Results**: cómo se recuperan las salidas. En esta plataforma, las salidas son **STAC
  Items nuevos** registrados en el catálogo → [05](05-stac-pgstac-stac-fastapi.md).

**Los endpoints estándar** (Parte 1):
```
GET  /processes                    # qué procesos hay publicados
GET  /processes/{processId}        # descripción: entradas, salidas, formatos
POST /processes/{processId}/execution   # lanzar un job
GET  /jobs                         # todos los jobs
GET  /jobs/{jobId}                 # estado y progreso
GET  /jobs/{jobId}/results         # las salidas
DELETE /jobs/{jobId}               # cancelar
```

**Parte 2 — despliegue** (*Deploy, Replace, Undeploy*):
```
POST   /processes                  # desplegar un Application Package (CWL)
PUT    /processes/{processId}      # reemplazar
DELETE /processes/{processId}      # retirar
```

Ésta es la parte que convierte un Application Package de GitLab+Harbor en un proceso
invocable. Es la unión entre [15-cwl-calrissian.md](15-cwl-calrissian.md),
[11-gitlab.md](11-gitlab.md) y [10-harbor.md](10-harbor.md).

**La relación con los tres modos de ejecución** (D2 §6.4): éste es el tercero,
*"Execution as a Service"*:

> *"applications are deployed as services that can be accessed via APIs, particularly through
> the OGC API Processes interface… enabling integration with other geospatial services and
> tools. Advantages: **broad accessibility, interoperability** with other platforms, and the
> ability to offer EO applications as a service to a wide audience."*

### Nivel operativo mínimo

- Listar procesos y ver la descripción de uno.
- Lanzar un job de prueba y seguir su estado.
- **Correlacionar un job de ZOO con su workflow de Argo** — la habilidad clave de este
  archivo, porque es el salto al diagnóstico real.
- Autenticación: los endpoints están protegidos por Keycloak →
  [09-keycloak.md](09-keycloak.md).

---

## 4. Laboratorio (opcional, 2 horas)

Este es el laboratorio menos prioritario de la carpeta. Hazlo si sobra tiempo, o cuando
llegues a operar el componente de procesamiento.

**Alternativa barata y suficiente:** en vez de desplegar ZOO, **estudia la API contra una
instancia pública** de OGC API – Processes (varias plataformas EO exponen una) y practica
los verbos. Lo que necesitas es fluidez con el modelo, no con la instalación.

Si decides desplegarlo:
1. Instala ZOO Project en el clúster.
2. `GET /processes` y `GET /processes/{id}` para ver la descripción.
3. Lanza un job asíncrono y sigue `GET /jobs/{jobId}` hasta `successful`.
4. Recupera los resultados y comprueba que aparecen como STAC Items.
5. **Correlaciona**: encuentra el workflow de Argo que ese job creó.
6. Despliega un Application Package con la Parte 2 y comprueba que aparece en
   `GET /processes`.

---

## 5. Contribución al diagnóstico

Cuando un usuario dice *"mi procesamiento falló"*:

1. **`GET /jobs/{jobId}`** — ¿en qué estado está? ¿hay mensaje de error?
2. **¿Es `failed` o nunca llegó a `running`?**
   - Nunca arrancó → problema de despliegue del proceso, de permisos, o de validación de
     entradas. Mira los logs de ZOO.
   - Falló ejecutando → **el problema está aguas abajo**.
3. **Salta a Argo Workflows** → [07-argo-workflows.md](07-argo-workflows.md): localiza el
   workflow, mira qué paso falló y su exit code.
4. **Desde ahí**, sigue el árbol de siempre: ¿imagen ([10](10-harbor.md),
   [17](17-docker.md))? ¿recursos ([01](01-kubernetes.md))? ¿datos de entrada
   ([06](06-s3-minio.md))? ¿CWL ([15](15-cwl-calrissian.md))?

**La regla:** ZOO te da el *qué* (el job falló) y el *cuándo*. El *por qué* está siempre en
otro sitio.

---

## 6. Comandos de bolsillo

```bash
# Qué procesos hay
curl -s "$ZOO/processes" -H "Authorization: Bearer $TOKEN" | jq -r '.processes[].id'

# Descripción de uno: entradas y salidas
curl -s "$ZOO/processes/ndvi" -H "Authorization: Bearer $TOKEN" \
  | jq '{id, inputs: (.inputs|keys), outputs: (.outputs|keys)}'

# Lanzar un job asíncrono
curl -s -X POST "$ZOO/processes/ndvi/execution" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Prefer: respond-async" \
  -d '{"inputs":{"stac_item":"https://.../items/S2A_..."}}' -i

# Estado del job
curl -s "$ZOO/jobs/$JOB" -H "Authorization: Bearer $TOKEN" \
  | jq '{status, progress, message}'

# Todos los jobs fallidos
curl -s "$ZOO/jobs" -H "Authorization: Bearer $TOKEN" \
  | jq -r '.jobs[] | select(.status=="failed") | "\(.jobID) \(.message)"'

# Resultados
curl -s "$ZOO/jobs/$JOB/results" -H "Authorization: Bearer $TOKEN" | jq

# El salto al diagnóstico real
argo list -n <ns> --since 1h
kubectl logs -n <ns> -l app=zoo-project --tail=100
```

---

## 7. Criterio de dominio

- [ ] Explico qué es OGC API – Processes y la diferencia entre Parte 1 (ejecución) y Parte 2 (despliegue).
- [ ] Nombro los endpoints principales y los estados de un job.
- [ ] Lanzo un job y sigo su estado hasta el final.
- [ ] **Correlaciono un job de ZOO con su workflow de Argo** y salto al diagnóstico real.
- [ ] Explico dónde encaja ZOO en la cadena front-end → ZOO → Argo → Calrissian → pods.
- [ ] Sé que ZOO rara vez es la causa, y no pierdo tiempo buscando ahí.

---

## 8. Qué preguntar

**A ESA / Terradue:**
1. ¿ZOO Project está desplegado y expuesto públicamente, o solo lo consume el portal?
2. ¿Qué procesos están publicados actualmente?
3. ¿El despliegue de procesos (Parte 2) está habilitado? ¿Quién puede desplegar?
4. ¿Cómo se correlaciona un `jobID` de ZOO con un workflow de Argo? Necesito ese mapeo para diagnosticar.
5. ¿Los resultados se registran automáticamente como STAC Items en el catálogo?
6. ¿Qué autenticación exige y con qué roles de Keycloak?

---

## 9. Fuentes

**Documentos del proyecto:** D2 §7.12 (ZOO Project), **§3.3.2 (Application Execution Engine:
deployment con Parte 2 y execution con Parte 1)**, §3.3.4 (ZOO en el stack de procesamiento),
§6.4.3 (Execution as a Service). D1 §3.2.3 (cumplimiento de estándares OGC).
Guía de estudio §9 (tabla de estándares).

**Documentación oficial:** OGC API – Processes (Parte 1: Core; Parte 2: Deploy, Replace,
Undeploy) en `ogcapi.ogc.org/processes`. `zoo-project.org`.

**Lo que de verdad tienes que dominar está en:**
[15-cwl-calrissian.md](15-cwl-calrissian.md) (el Application Package) y
[07-argo-workflows.md](07-argo-workflows.md) (donde ocurre la ejecución y el diagnóstico).

---

## 10. Bitácora / hallazgos

*(Procesos publicados, mapeo jobID ↔ workflow, incidentes y dónde estaba realmente la causa.)*
