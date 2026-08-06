# CWL + cwltool + Calrissian — Application Packages

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 3 — lo tocas al operar procesamiento e ingesta
**Competencia de la matriz:** 15

---

## 1. Qué es, aquí

CWL (Common Workflow Language) es **el idioma en el que están escritas todas las
aplicaciones EO** de la plataforma. No es opcional: D2 §6.8.1 lo declara obligatorio.

> *"All EO applications **MUST** be described using the Common Workflow Language (CWL). This
> ensures that workflows are portable and reproducible, enabling consistent execution across
> different environments."*

Un **Application Package** = descripción CWL + contenedores Docker/OCI, siguiendo las
*OGC Best Practices for EO Application Packaging* (**OGC 20-089r1**) y la arquitectura común
**EOEPCA** de la ESA (D2 §6.1).

Los tres ejecutores, y cuándo se usa cada uno (D2 §7.2):

| Ejecutor | Dónde corre | Para qué |
|---|---|---|
| **cwltool** | Máquina local | Referencia, desarrollo, pruebas. *"lacks the scalability required for large, production-grade environments"* |
| **Toil** | HPC / cloud distribuido | Mencionado como opción; no es el de esta plataforma |
| **Calrissian** | **Dentro de Kubernetes** | El de producción: *"harness the power of Kubernetes to execute workflows… run multiple steps in parallel"* |

Calrissian es la pieza que importa operativamente:

> *"Calrissian integrates with Kubernetes, allowing it to handle the orchestration of
> containers that execute individual workflow steps. By leveraging Kubernetes' built-in
> features, such as auto-scaling, load balancing, and fault tolerance, Calrissian ensures
> that workflows are executed with optimal resource utilisation."*

---

## 2. La frontera

Tuyo como **operador**: ejecutar, diagnosticar, entender por qué un paso falló, saber leer un
CWL para localizar el problema.

**No** eres quien escribe las aplicaciones EO —eso lo hacen ESA/Terradue y los usuarios de la
plataforma. Pero sí eres quien recibe el ticket cuando un Application Package no corre, y
para eso necesitas leer CWL con fluidez.

La distinción práctica: *"el algoritmo produce un NDVI incorrecto"* no es tuyo.
*"El paso 3 falla porque la imagen no tiene GDAL"* o *"el stage-in no encuentra el asset"* sí.

---

## 3. Qué debes saber

### Nivel imprescindible — leer CWL

**Las dos clases** (D2 §6.2):

**`CommandLineTool`** — un ejecutable con sus entradas y salidas:
```yaml
cwlVersion: v1.2
class: CommandLineTool
baseCommand: python calculate_ndvi.py
inputs:
  - id: input_image
    type: File
  - id: output_ndvi
    type: File
outputs:
  - id: output_ndvi
    type: File
stdout: output.log
stderr: error.log
```

Componentes que debes reconocer de un vistazo:
- `inputs` — parámetros de entrada (File, string, int, Directory, arrays, opcionales con `?`).
- `outputs` — ficheros o valores producidos.
- `baseCommand` — el comando a ejecutar.
- `arguments` — argumentos adicionales.
- `stdout` / `stderr` — dónde se capturan.

**`Workflow`** — encadena varios tools:
```yaml
cwlVersion: v1.2
class: Workflow
inputs:
  - id: input_image
    type: File
outputs:
  - id: output_ndvi
    type: File
steps:
  preprocess:
    run: preprocess.cwl
    in:
      input_image: input_image
    out: [preprocessed_image]
  calculate_ndvi:
    run: calculate_ndvi.cwl
    in:
      input_image: preprocess/preprocessed_image
    out: [output_ndvi]
```
- `steps` — cada paso con su `run`, `in` y `out`.
- **La conexión entre pasos**: `preprocess/preprocessed_image` es "la salida
  `preprocessed_image` del paso `preprocess`". Si esa referencia está mal, el workflow no
  valida.
- `requirements` — dependencias y recursos.

**Requirements que importan operativamente:**
- `DockerRequirement` con `dockerPull` — **qué imagen usa cada paso**. Es lo primero que
  miras cuando un paso falla por imagen.
- `ResourceRequirement` con `coresMin`, `ramMin`, `outdirMin` — lo que Calrissian traduce a
  requests/limits de Kubernetes. Un `ramMin` mal puesto es un `OOMKilled`.
- `InitialWorkDirRequirement`, `EnvVarRequirement`, `ScatterFeatureRequirement` (paralelismo).

**Entradas y salidas: el fichero de parámetros** (`params.yml` o `job.json`), y cómo se
relaciona con lo que declara `inputs`.

### Nivel operativo

**Stage-in y stage-out** — el concepto clave de esta plataforma (D2 §5.3, D3 §6.1):

> *"For data processing services integrated via the CWL, **there is no need for services to
> generate or manage signed URLs themselves**. Instead, the platform handles data staging
> through a **stage-in mechanism**. This process ensures that input datasets are made
> available as **local file paths inside the containerized service execution environment**."*

Cómo funciona:
- **Stage-in**: la plataforma parte de un **STAC Catalog** (un JSON con enlaces a STAC Items
  y sus assets), descarga o monta los assets, y se los da a la aplicación como **rutas
  locales**. La aplicación no sabe nada de S3 ni de URLs firmadas.
- **Stage-out**: al terminar, la aplicación genera **nuevos STAC Items** apuntando a los
  resultados, que se almacenan y se registran en el catálogo.

D2 §5.3 lo describe con un ejemplo: bandas `coastal`, `blue`, `green` referenciadas desde el
catálogo, procesadas, y devueltas como items nuevos.

También menciona **fan-in** (varios datasets agregados en una tarea) y **fan-out** (un
dataset que genera varias tareas paralelas), ambos manejados con STAC Catalogs como
manifiesto.

**Ejecución**
- `cwltool` local: `cwltool --validate`, `cwltool app.cwl params.yml`, `--debug`,
  `--outdir`, `--tmpdir-prefix`.
- Calrissian en Kubernetes: se lanza como un pod que a su vez crea pods por paso. Necesita
  un PVC compartido (`ReadWriteMany`) para el directorio de trabajo — **y ése es el punto que
  más falla**, porque no todas las StorageClasses soportan RWX.
- Cómo se relaciona con Argo Workflows: Argo orquesta el flujo general; Calrissian ejecuta la
  parte CWL. Ver [07-argo-workflows.md](07-argo-workflows.md).

**Requisitos de la plataforma para las aplicaciones (D2 §6.8)** — tu lista de verificación
cuando alguien te pida desplegar un package:

| § | Requisito | Nivel |
|---|---|---|
| 6.8.1 | Descrita en CWL | **MUST** |
| 6.8.2 | Ejecución desatendida, sin intervención humana | **MUST** |
| 6.8.3 | Encapsulada en contenedores Docker, imágenes base ligeras | **MUST** |
| 6.8.4 | Salidas conformes al perfil de metadatos y catalogadas en STAC | **MUST** |
| 6.8.5 | Contenedores libres de vulnerabilidades conocidas | **MUST** |
| 6.8.6 | Código, CWL y Dockerfiles en GitLab, con tags de release | SHOULD |
| 6.8.7 | `resources` requests y limits definidos, procesamiento paralelo | SHOULD |
| 6.8.8 | Documentación completa (funcionalidad, E/S, ejemplos, despliegue) | SHOULD |
| 6.8.9 | Pruebas: unitarias, integración, benchmarks, datasets de prueba | SHOULD |

### Nivel avanzado

- Escribir un CWL nuevo para una ingesta de una colección no cubierta.
- Depurar un paso que falla solo con datos reales (y no con los de prueba).
- Dimensionar `ResourceRequirement` contra los objetivos de **≥ 0,350 TB/h** y latencia
  **< 1 h**.
- La relación con OGC API – Processes: el mismo package se despliega como proceso web →
  [21-zoo-ogc-api-processes.md](21-zoo-ogc-api-processes.md).

---

## 4. Los tres modos de ejecución (D2 §6.4)

Debes saber explicarlos porque definen cómo se prueba un cambio:

| Modo | Propósito | Cómo |
|---|---|---|
| **Local Computer** | Desarrollo y pruebas. *"Fast feedback loops, easy debugging"* | `cwltool` |
| **Kubernetes Cluster** | Producción distribuida. *"Automatic scaling, load balancing"* | Calrissian |
| **Execution as a Service** | Expuesto como servicio web vía **OGC API – Processes** | ZOO Project |

El mismo Application Package funciona en los tres. Esa es la promesa de CWL, y es lo que
te permite reproducir un fallo de producción en tu portátil.

---

## 5. Laboratorio

Parte del **Bloque 6 — 12 horas**.

1. **Escribe un `CommandLineTool` mínimo.** Una entrada File, una salida File, un comando
   simple. Valídalo: `cwltool --validate mi-tool.cwl`.
2. **Ejecútalo con `cwltool`** y un fichero de parámetros. Observa el directorio de salida.
3. **Añade `DockerRequirement`** con una imagen que tenga GDAL. Ejecuta un `gdalinfo` sobre
   un COG real.
4. **Escribe un `Workflow`** de dos pasos donde la salida del primero alimenta al segundo.
   Ejecútalo. **Comprueba que entiendes la sintaxis `paso/salida`.**
5. **Añade `ResourceRequirement`** y observa qué cambia.
6. **Ejecuta el mismo CWL con Calrissian** dentro del clúster. Necesitarás un PVC `RWX`.
   Compara la experiencia con `cwltool`: mismos ficheros, orquestación distinta.
7. **Simula stage-in**: parte de un STAC Catalog local que apunte a un asset, y haz que tu
   tool lo lea como ruta local. Genera un STAC Item de salida.
8. **Rompe cosas** (§6) y aprende a leer cada error.

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| **Imagen sin GDAL** en un paso que lo necesita | **Avería 9 del catálogo.** El error llega como exit code, no como mensaje claro |
| Referencia `paso/salida` mal escrita | Falla en validación, antes de ejecutar |
| `ramMin` demasiado bajo | `OOMKilled` en Calrissian; cómo se ve desde el workflow |
| PVC sin `ReadWriteMany` para Calrissian | El pod queda `Pending`; el error más común al empezar |
| Salida declarada que la aplicación no produce | Error en el stage-out; el paso "termina bien" pero el workflow falla |
| CWL con `cwlVersion` incompatible con el runner | Error de parseo; por qué la versión importa |

---

## 7. Averías de producción que este bloque entrena

**Avería 9:** workflow que falla en el paso 3 — imagen sin GDAL.

Es la avería que enseña a leer la frontera entre "el algoritmo está mal" (del
desarrollador) y "el entorno de ejecución está mal" (tuyo).

---

## 8. Comandos de bolsillo

```bash
# Validar SIEMPRE antes de ejecutar
cwltool --validate app.cwl

# Ejecutar en local
cwltool --outdir ./salida app.cwl params.yml
cwltool --debug --leave-tmpdir app.cwl params.yml    # cuando falla y no sabes por qué

# Ver qué imagen usa cada paso (lo primero en un fallo de imagen)
yq '.. | select(has("dockerPull")) | .dockerPull' app.cwl
grep -r dockerPull *.cwl

# Ver los recursos declarados
yq '.. | select(has("ramMin"))' app.cwl

# Calrissian dentro del clúster
kubectl logs -n <ns> <pod-calrissian> --follow
kubectl get pods -n <ns> -l calrissian.io/job    # los pods de cada paso
kubectl describe pvc <pvc-calrissian> -n <ns>   # ¿es RWX? ¿está Bound?

# Inspeccionar un STAC Catalog de stage-in
jq '.links[] | select(.rel=="item")' catalog.json
```

---

## 9. Criterio de dominio

- [ ] Leo un CWL y entiendo sus entradas, salidas y la conexión entre pasos.
- [ ] Distingo `CommandLineTool` de `Workflow` y sé cuándo se usa cada uno.
- [ ] Localizo en un CWL qué imagen usa cada paso y qué recursos declara.
- [ ] **Explico qué es stage-in/stage-out y por qué las aplicaciones CWL no usan URLs firmadas.**
- [ ] Ejecuto un CWL con `cwltool` en local **y** con Calrissian en el clúster.
- [ ] Diagnostico un paso fallido: ¿imagen, recursos, entrada ausente, salida no producida?
- [ ] Nombro los nueve requisitos de D2 §6.8 y sé cuáles son MUST.
- [ ] Explico los tres modos de ejecución y por qué el mismo package funciona en los tres.

---

## 10. Artefacto que produces

Un **Application Package mínimo completo**, versionado: CWL + Dockerfile + parámetros de
ejemplo + README con entradas y salidas. Es tu referencia para evaluar los packages de otros
y tu material didáctico para la transferencia.

Contribuye a **`runbooks/ingesta-fallida.md`**: la rama "¿por qué falló este paso?".

**Alimenta:** Producto 2 (arquitectura lógica), Producto 4 (casos prácticos de
transferencia).

---

## 11. Qué preguntar

**A ESA / Terradue:**
1. ¿Qué versión de CWL usan los Application Packages y qué versión de Calrissian está desplegada?
2. ¿Cómo se configura el PVC compartido de Calrissian y con qué StorageClass?
3. ¿Cómo funciona exactamente el stage-in: descarga a disco, montaje, o acceso directo?
4. ¿Qué imágenes base están aprobadas para los Application Packages?
5. ¿Dónde están los Application Packages operativos y cuál es el procedimiento para añadir uno?
6. ¿Cómo se valida un package nuevo antes de que entre en producción?
7. ¿Qué exit codes usan y qué significa cada uno?

---

## 12. Fuentes

**Documentos del proyecto:** D2 §6.1 (empaquetado, OGC 20-089r1, EOEPCA), **§6.2 (CWL en
detalle: CommandLineTool y Workflow con los ejemplos de NDVI)**, §6.3 (contenedores y gestión
de dependencias), §6.4 (los tres modos de ejecución), §6.8 (los nueve requisitos de
cumplimiento), §7.2 (cwltool, Toil, Calrissian), §3.3.2 y §3.3.4 (Calrissian en el stack de
procesamiento), §4.1 y §4.3 (CWL en la ingesta y selección del Application Package), §5.3
(STAC como manifiesto de stage-in/stage-out, fan-in y fan-out). D3 §2.3.3 (despliegue y
ejecución de aplicaciones), §6.1 (por qué CWL no usa URLs firmadas). D1 §3.2.3 (cumplimiento
de estándares).

**Documentación oficial:** `commonwl.org` — User Guide.
Calrissian: `github.com/Duke-GCB/calrissian`.
OGC 20-089r1: `docs.ogc.org/bp/20-089r1.html`. EOEPCA: `eoepca.org`.

---

## 13. Bitácora / hallazgos

*(Packages reales, imágenes aprobadas, fallos de stage-in, configuración de Calrissian.)*
