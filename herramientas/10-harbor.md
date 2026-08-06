# Harbor — el registro de contenedores

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 2 — alto y **desatendido**
**Competencia de la matriz:** 21 (junto con [11-gitlab.md](11-gitlab.md))

---

## 1. Qué es, aquí

Harbor es la mitad del **componente 4 del Middleware** (Application Registry). GitLab guarda
el código y los CWL; **Harbor guarda las imágenes**.

D2 §7.6:

> *"Harbor is an open-source container image registry used by the CopernicusLAC platform to
> store and manage Docker images securely. Harbor provides advanced security features, such
> as **vulnerability scanning, image signing, and access control**, ensuring that only
> trusted and verified images are deployed on the platform. By organising images into
> **projects** and enforcing **role-based access control (RBAC)**, Harbor allows for the
> management of containerized applications."*

Dónde aparece, exactamente:

| Dónde | Qué hace |
|---|---|
| **Application Registry** (§3.4.2) | Almacena las imágenes de los Application Packages |
| **Ingesta** (D3 §3.2.2) | El workflow *"obtains the necessary ingestion images"* del Registry |
| **Procesamiento** (§3.4.3) | El Workflow Engine accede a las imágenes para orquestar |
| **User Workspace** (§3.6.3) | **Cada usuario tiene su propio registro Harbor** |
| **Empaquetado** (§6.1) | Destino del push de la CI: *"Harbor serves as the container registry where Docker images of the packaged applications are stored"* |
| **Despliegue** (§6.4) | *"Once the application package is stored in Harbor, it can be deployed"* |
| **Control de acceso** (§6.6) | Integrado con Keycloak; puede **restringir el acceso a imágenes según el resultado del escaneo** |

Ese último punto merece atención: Harbor no es un almacén pasivo. Es un **control de
calidad** que puede bloquear el despliegue de una imagen vulnerable.

---

## 2. La frontera

Tuyo. *Platform Domains Support → registry → **Not covered***.

El proveedor no sabe qué es un proyecto de Harbor ni por qué un pod no puede hacer pull. Si
escalas un `ImagePullBackOff` sin haber comprobado antes el `imagePullSecret` y la política
de retención de Harbor, vas a quedar mal.

Ojo con una asimetría: **el registro de cada workspace de usuario** también es tuyo en tanto
que operador de la plataforma, aunque el contenido sea de los usuarios. Cuotas, retención y
escaneo son política tuya.

---

## 3. Qué debes saber

### Nivel imprescindible

**Modelo de Harbor**
- **Proyecto**: la unidad de aislamiento. Público o privado. Cada workspace de usuario tiene
  el suyo.
- **Repositorio**: dentro de un proyecto, `proyecto/imagen`.
- **Artefacto**: una imagen (o un chart Helm OCI, o un artefacto OCI cualquiera).
- **Tag vs digest**: un tag se puede mover, un digest no. **Ésta es la distinción que hace
  reproducible un despliegue** — y que explica por qué `imagePullPolicy` importa.
- Roles del proyecto: `Limited Guest`, `Guest`, `Developer`, `Maintainer`, `Project Admin`.
  D2 §6.6 usa "Maintainer" como ejemplo de rol asignado desde Keycloak.

**Autenticación desde Kubernetes**
- `imagePullSecret` de tipo `kubernetes.io/dockerconfigjson`.
- Cómo se crea, cómo se asocia a un `ServiceAccount` (para no repetirlo en cada pod), y qué
  pasa cuando la credencial rota.
- **Robot accounts**: cuentas de máquina con permisos acotados y expiración. Es lo correcto
  para que un workflow haga pull; no uses credenciales de persona.

**Escaneo de vulnerabilidades**
- Trivy (u otro escáner) integrado. Escaneo automático al push, o a demanda.
- Severidades y la política de **bloqueo**: impedir el pull de imágenes con vulnerabilidades
  por encima de un umbral. D2 §6.8.5 lo exige a los desarrolladores:
  *"Developers MUST ensure that their Docker containers are free from known vulnerabilities
  by conducting regular security scans"*.
- El efecto colateral que debes prever: **activar el bloqueo puede romper despliegues
  existentes**. Es un cambio, y merece ventana y plan de reversión.

### Nivel operativo

- **Cuotas por proyecto**: límite de almacenamiento. Con un registro por usuario y 2 PB de
  datos, el registro puede crecer sin control si nadie pone límites.
- **Políticas de retención (tag retention)**: reglas del tipo "conserva las 10 últimas
  versiones de cada repositorio" o "conserva las de los últimos 90 días". Sin esto, el
  registro crece indefinidamente.
- **Garbage collection**: la retención marca artefactos para borrar; el GC libera el espacio.
  Son dos cosas distintas y el GC suele requerir una ventana.
- **Immutable tags**: impedir que un tag se sobrescriba. Es la garantía de reproducibilidad
  que D2 §6.7 promete.
- **Replicación**: entre registros, o desde un registro público (proxy cache) para no
  depender de Docker Hub.
- **Firma de imágenes** (Cosign/Notary): D2 §7.6 la menciona. Verificar firmas antes de
  desplegar.
- Integración con Keycloak (OIDC): usuarios y roles desde el proveedor de identidad, no
  locales. Ver [09-keycloak.md](09-keycloak.md).
- Harbor como registro **OCI de charts Helm** — relevante para
  [02-helm.md](02-helm.md) si los charts del Middleware se distribuyen así.

### Nivel avanzado

- Diseño de la estructura de proyectos: uno por componente, uno por equipo, uno por usuario.
- Política de retención que equilibre reproducibilidad (poder volver a una versión de hace 6
  meses) con espacio.
- Webhooks de Harbor hacia Argo Events: disparar un flujo cuando se publica una imagen nueva.
- Proxy cache para reducir el consumo de los **3 Gbps** de conectividad a Europa.

---

## 4. Datos de la plataforma que debes tener a mano

**La cadena de publicación (D2 §6.5)** — Harbor es el paso 5 de 8:

```
commit en GitLab → CI: tests → build de la imagen Docker → pruebas en staging
  → push a HARBOR con tag de versión nueva
  → los charts de Helm se actualizan con la nueva versión
  → Kubernetes despliega
  → si falla: rollback a la versión estable anterior
```

**Los requisitos que la plataforma impone a las imágenes (D2 §6.8):**
- §6.8.3 — *"EO applications **MUST** be encapsulated within Docker containers… Developers
  are encouraged to use **lightweight base images** and to optimise container size and
  performance."*
- §6.8.5 — *"Developers **MUST** ensure that their Docker containers are **free from known
  vulnerabilities** by conducting regular security scans."*
- §6.8.2 — ejecución desatendida, sin intervención humana.

Estos "MUST" son tu criterio cuando tengas que decir que no a una imagen.

**El workspace de usuario (D2 §3.4.3):**

> *"Each user workspace has dedicated software repositories in GitLab and a **dedicated
> Harbor based container registry** to manage private and operational packages and
> associated container registries."*

Con miles de usuarios potenciales, eso son miles de proyectos de Harbor. La política de
cuotas y retención no es opcional: es la diferencia entre un registro sano y 2 PB de imágenes
olvidadas.

**Control de acceso (D2 §6.6):**

> *"Harbor integrates with vulnerability scanning tools and **can restrict access to
> container images based on scan results**. This ensures that only secure and validated
> images are available for deployment."*

---

## 5. Laboratorio

Parte del **Bloque 1 — 5 horas** (junto con [17-docker.md](17-docker.md)).

1. **Empieza con un registro local** (`registry:2`) para entender el mecanismo básico: push,
   pull, tag, digest.
2. **Levanta Harbor** en tu clúster o con Docker Compose.
3. **Crea un proyecto** `copernicus-lab` con **cuota** de almacenamiento.
4. **Push de tu imagen** del bloque 1. Observa el escaneo automático.
5. **Publica una imagen con una vulnerabilidad conocida** (una base antigua sirve) y observa
   el resultado del escaneo. Activa el **bloqueo por severidad** y comprueba que el pull
   falla.
6. **El experimento del tag**: haz push de una imagen nueva con **el mismo tag**. Observa que
   el digest cambia. Ahora razona —y escríbelo— por qué `imagePullPolicy: IfNotPresent` con
   tags móviles produce despliegues no reproducibles, y por qué desplegar por digest lo
   resuelve.
7. **Activa immutable tags** e intenta sobrescribir. Observa el rechazo.
8. **Robot account.** Crea uno con permiso de solo pull, genera el `imagePullSecret` y
   despliega un pod que use ese secret.
9. **Política de retención.** Configura "conserva las 3 últimas" y ejecútala. Luego ejecuta
   el garbage collection y comprueba que el espacio se libera **después**, no antes.
10. **Rompe la credencial.** Borra el `imagePullSecret` y observa el `ImagePullBackOff`.
    Compáralo con el que produce un tag inexistente. **Son idénticos a primera vista.**

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Borrar el `imagePullSecret` | `ImagePullBackOff` por credenciales — avería 2 del catálogo |
| Tag inexistente | El **mismo** síntoma, causa distinta. Distinguirlos es el ejercicio |
| Registro inalcanzable (DNS o red) | El **tercer** `ImagePullBackOff`. Tres causas, un síntoma |
| Imagen con vulnerabilidad + bloqueo activo | Pull rechazado por política, no por credenciales |
| Mismo tag, digest distinto | Por qué dos pods de la "misma versión" corren código distinto |
| Cuota de proyecto agotada | El push falla; dónde se ve |
| Retención agresiva que borra la versión en producción | **Por qué la política de retención es un cambio, no una tarea de limpieza** |

---

## 7. Averías de producción que este bloque entrena

**Avería 2:** `ImagePullBackOff` por credenciales del registro (secret de pull borrado).

Y su generalización, que es lo que de verdad debes dominar: **saber distinguir las tres
causas de `ImagePullBackOff`** —credenciales, tag inexistente, registro inalcanzable— porque
el síntoma en `kubectl get pods` es idéntico y la solución es completamente distinta.

Contribuye también a la **9** (workflow que falla en el paso 3): si el paso no puede bajar
su imagen, el fallo aparece en Argo pero la causa está aquí.

---

## 8. Cómo distinguir las tres causas de `ImagePullBackOff`

```bash
kubectl describe pod <pod> -n <ns> | grep -A5 Events
```

| Mensaje en los eventos | Causa | Qué haces |
|---|---|---|
| `unauthorized` / `authentication required` | **Credenciales** | Verifica el `imagePullSecret` y que esté referenciado |
| `manifest unknown` / `not found` | **Tag o repositorio inexistente** | Comprueba el tag en Harbor |
| `no such host` / `connection refused` / `i/o timeout` | **Registro inalcanzable** | DNS, red, ¿está Harbor vivo? |
| `denied` con credenciales válidas | **Política de escaneo** o permisos del proyecto | Mira el resultado del escaneo y el rol |

Comprobaciones:
```bash
# ¿Existe el secret y está bien formado?
kubectl get secret <pull-secret> -n <ns> -o jsonpath='{.data.\.dockerconfigjson}' \
  | base64 -d | jq

# ¿Está referenciado en el pod o en el ServiceAccount?
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.imagePullSecrets}'
kubectl get sa <sa> -n <ns> -o jsonpath='{.imagePullSecrets}'

# ¿Existe el tag en Harbor?
curl -s -u "$USER:$PASS" \
  "https://$HARBOR/api/v2.0/projects/copernicus/repositories/mi-app/artifacts?page_size=20" \
  | jq -r '.[].tags[].name'

# ¿Alcanzo el registro desde un pod?
kubectl run tmp --rm -it --image=nicolaka/netshoot -- \
  curl -s -o /dev/null -w '%{http_code}\n' https://$HARBOR/v2/
```

---

## 9. Comandos de bolsillo

```bash
# Login y push
docker login $HARBOR
docker tag mi-app:1.0 $HARBOR/copernicus/mi-app:1.0
docker push $HARBOR/copernicus/mi-app:1.0

# Ver el digest (lo que de verdad identifica la imagen)
docker inspect --format='{{index .RepoDigests 0}}' $HARBOR/copernicus/mi-app:1.0

# Desplegar por digest, no por tag (reproducible)
# image: harbor.ejemplo/copernicus/mi-app@sha256:abc123...

# API de Harbor
curl -s -u "$USER:$PASS" "https://$HARBOR/api/v2.0/projects" | jq -r '.[].name'
curl -s -u "$USER:$PASS" "https://$HARBOR/api/v2.0/projects/copernicus/summary" | jq
curl -s -u "$USER:$PASS" \
  "https://$HARBOR/api/v2.0/projects/copernicus/repositories/mi-app/artifacts?with_scan_overview=true" \
  | jq '.[] | {tags: [.tags[].name], scan: .scan_overview}'

# Crear el imagePullSecret
kubectl create secret docker-registry harbor-pull \
  --docker-server=$HARBOR --docker-username=robot\$copernicus+ci \
  --docker-password="$ROBOT_TOKEN" -n <ns>

# Asociarlo al ServiceAccount (mejor que repetirlo en cada pod)
kubectl patch sa default -n <ns> \
  -p '{"imagePullSecrets":[{"name":"harbor-pull"}]}'
```

---

## 10. Criterio de dominio

- [ ] Creo un proyecto con cuota, subo una imagen y verifico su escaneo.
- [ ] **Distingo las tres causas de `ImagePullBackOff` leyendo los eventos, sin adivinar.**
- [ ] Explico la diferencia entre tag y digest y por qué importa para la reproducibilidad.
- [ ] Configuro un robot account y su `imagePullSecret` asociado a un ServiceAccount.
- [ ] Configuro retención de tags y sé que el GC es un paso aparte.
- [ ] Activo el bloqueo por vulnerabilidad **entendiendo que es un cambio con impacto**.
- [ ] Consulto la API de Harbor para saber qué tags existen sin abrir la UI.
- [ ] Explico cómo Keycloak gobierna los roles de Harbor.

---

## 11. Artefactos que produces

1. **Nota de una página**: *"imagen vs contenedor vs pod"*, con tus palabras — junto con
   [17-docker.md](17-docker.md).
2. **Sección de `runbooks/diagnostico-pod.md`** dedicada a `ImagePullBackOff`, con la tabla
   del §8.
3. **Política de proyectos, cuotas y retención** documentada — parte de la arquitectura
   operativa del Producto 8.

**Alimentan:** Producto 2 (runbooks), Producto 6 (SOPs), Producto 8 (arquitectura operativa
actualizada).

---

## 12. Qué preguntar

**A ESA / Terradue:**
1. **¿Qué parte del ciclo de vida de aplicaciones (GitLab, Harbor, workspaces de usuario) administro yo y qué parte administran ustedes?** (La pregunta clave de este bloque.)
2. ¿Cómo se estructuran los proyectos de Harbor: por componente, por equipo, por usuario?
3. ¿Hay política de retención y cuotas definida, o la defino yo?
4. ¿Está activo el bloqueo de pull por resultado de escaneo? ¿Con qué umbral de severidad?
5. ¿Se firman las imágenes? ¿Se verifica la firma en el despliegue?
6. ¿Harbor aloja también los charts de Helm como artefactos OCI?
7. ¿Hay proxy cache configurado hacia registros externos, o cada pull sale a internet?

**Al proveedor:**
1. ¿Harbor corre dentro del clúster o es un servicio aparte? ¿Qué almacenamiento consume?
2. Si Harbor está dentro del clúster, ¿qué pasa con su PVC en un mantenimiento?

---

## 13. Fuentes

**Documentos del proyecto:** D2 §3.4 completo (Application Registry: propósito,
implementación con GitLab y Harbor, integración con Application Execution Engine, Workflow
Engine y User Workspace, stack), §6.1 (Harbor en el empaquetado), §6.4 (despliegue desde
Harbor), §6.5 (la cadena CI → Harbor → Helm → K8s), §6.6 (Harbor Access Management vía
Keycloak, restricción por escaneo), §6.7 (beneficios), §6.8.3 y §6.8.5 (requisitos MUST
sobre contenedores), §7.6 (Harbor), §3.6.2 y §3.6.3 (registro propio por workspace). D3
§2.2 y §2.3.3 (Application Packaging and Deployment).

**Documentación oficial:** `goharbor.io/docs` — Working with Projects, Vulnerability
Scanning, Tag Retention, Robot Accounts, OIDC Authentication.

---

## 14. Bitácora / hallazgos

*(Proyectos reales, cuotas aplicadas, imágenes bloqueadas por escaneo, incidentes de pull y
su causa.)*
