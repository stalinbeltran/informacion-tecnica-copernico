# GitLab — control de versiones y CI/CD

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 2 — alto y **desatendido**
**Competencia de la matriz:** 21 (junto con [10-harbor.md](10-harbor.md))

---

## 1. Qué es, aquí

GitLab es la otra mitad del **componente 4** (Application Registry) y, además, el motor de
CI/CD de la plataforma. D2 §7.5:

> *"GitLab serves as the version control system and Continuous Integration/Continuous
> Deployment (CI/CD) platform… The CI/CD pipelines in GitLab automate the process of
> building, testing, and deploying applications."*

Dónde aparece:

| Dónde | Qué guarda o hace |
|---|---|
| **Application Registry** (§3.4.2) | *"GitLab is used to store the application packages as Continuous Integration pipeline artifacts, including the **CWL descriptions, code, and configuration files**"* |
| **Metadatos** (§3.4.2) | Versión, dependencias, parámetros de configuración, instrucciones de uso |
| **Front-end Services** (§3.5.4) | GitLab CI/CD automatiza el despliegue y actualización de los servicios de front-end |
| **User Workspace** (§3.6.2) | **Cada workspace tiene su propia instancia de control de versiones** |
| **Empaquetado** (§6.1, §6.5) | Versionado de código, CWL y Dockerfiles; pipelines que construyen y publican |
| **Control de acceso** (§6.6) | Integrado con Keycloak; ramas protegidas por rol |

Un detalle que conviene retener: **el Application Package no es solo la imagen**. Es el CWL
+ el código + la configuración + los metadatos, y todo eso vive en GitLab. La imagen en
Harbor es solo el runtime.

---

## 2. La frontera

Tuyo. *Platform Domains Support → registry → **Not covered***.

Con un matiz de rol: tú no eres quien desarrolla las aplicaciones EO. Eres quien **opera** el
registro: acceso, ramas protegidas, runners, pipelines que fallan, retención de artefactos,
y el diagnóstico cuando la cadena de publicación se rompe.

La distinción práctica: *"el pipeline falla porque el test unitario de la aplicación no
pasa"* es del desarrollador. *"El pipeline falla porque el runner no tiene permisos para
hacer push a Harbor"* es tuyo.

---

## 3. Qué debes saber

### Nivel imprescindible

**Git como base** — ver [04-fundamentos-linux-git-yaml.md](04-fundamentos-linux-git-yaml.md).
Sin dominar Git, GitLab es una web bonita.

**Modelo de GitLab**
- Grupos, subgrupos y proyectos. La jerarquía que organiza los permisos.
- Roles: `Guest`, `Reporter`, `Developer`, `Maintainer`, `Owner`. D2 §6.6 usa "Developer"
  como ejemplo de rol asignado desde Keycloak.
- **Ramas protegidas**: D2 §6.6 lo destaca —
  *"GitLab allows for protected branches, where only users with specific roles (as determined
  by Keycloak) can push changes or merge code. This ensures that critical branches, such as
  the main or production branches, are safeguarded against unauthorised modifications."*
- **Tags y releases**: D2 §6.5 —
  *"GitLab's tagging feature is used to mark specific points in the application's history…
  These tags allow for easy retrieval and deployment of specific versions."*
- Merge requests, aprobaciones, y por qué son el punto de control de un cambio funcional.

**CI/CD**
- `.gitlab-ci.yml`: `stages`, `jobs`, `script`, `rules`/`only`/`except`, `needs`,
  `artifacts`, `cache`, `variables`.
- **Runners**: shared vs específicos; ejecutores (`docker`, `kubernetes`). En esta
  plataforma lo natural es el ejecutor de Kubernetes, corriendo en el propio clúster.
- Variables de CI y **variables protegidas/enmascaradas** — donde viven las credenciales de
  Harbor.
- Registro de contenedores integrado de GitLab vs Harbor: la plataforma usa **Harbor** como
  registro; el de GitLab puede estar deshabilitado. Confirma cuál es el caso.
- Artefactos de pipeline y su expiración. D2 §3.4.2 dice que los Application Packages se
  guardan **como artefactos de pipeline de CI** — así que la política de expiración de
  artefactos afecta a la disponibilidad de los paquetes.

### Nivel operativo

- Diagnosticar un pipeline fallido: ¿es el código, el runner, las credenciales, la red, la
  cuota?
- Operar runners en Kubernetes: el chart de `gitlab-runner`, concurrencia, recursos por job,
  y el `ServiceAccount` que necesita.
- Configurar el pipeline que publica a Harbor: login con robot account, build, push con tag
  de versión.
- Integración con Keycloak (OIDC) para autenticación. Ver [09-keycloak.md](09-keycloak.md).
- Backups de GitLab: **pregunta de frontera**. Si GitLab corre en el clúster, sus datos están
  en un PVC y en PostgreSQL. ¿Quién respalda qué?
- Retención de artefactos y control del crecimiento del almacenamiento.
- Webhooks hacia Argo Events: disparar un flujo cuando se publica un tag.

### Nivel avanzado

- Diseño del flujo de trabajo: ramas, entornos, quién aprueba qué. Esto **es** tu proceso de
  gestión de cambios funcional — una de las áreas que ESA marca como no cubierta.
- Pipelines que validan CWL antes de publicar (`cwltool --validate`).
- Firma de commits y trazabilidad para el requisito documental del BID.
- Estrategia de workspaces: cada usuario tiene su GitLab; ¿cómo se les provisiona? Es
  Crossplane quien lo hace → [13-crossplane.md](13-crossplane.md).

---

## 4. Datos de la plataforma que debes tener a mano

**La cadena completa (D2 §6.5)** — GitLab es el origen y el disparador:

```
1. Code Commit          — el desarrollador sube cambios (código o configuración)
2. CI Pipeline          — pull del código, tests unitarios e integración
3. Build                — si pasan, se construye una imagen Docker nueva
4. Testing & Validation — la imagen se prueba en un entorno de staging
5. Deployment           — push a Harbor con tag de versión nueva
                          los charts de Helm se actualizan
                          Kubernetes despliega
6. Rollback Mechanism   — si falla, vuelta rápida a la versión estable anterior
```

**Qué se versiona exactamente (D2 §6.5):**
> *"All application code, workflows, and **Dockerfiles** are stored in GitLab repositories."*

Y con qué obligación (D2 §6.8.6):
> *"The source code, **CWL workflows**, and Dockerfiles for EO applications **SHOULD** be
> managed using GitLab. Developers should follow best practices for version control,
> including **tagging releases** and maintaining clear documentation of changes. GitLab's
> CI/CD pipelines **should** be used to automate the build, test, and deployment processes."*

**Por qué importa la reproducibilidad (D2 §6.7):**
> *"By maintaining strict version control through GitLab, the platform ensures that
> applications can be reliably reproduced across different environments and over time."*

Esto conecta con una obligación contractual tuya: el financiamiento **BID** (préstamo
5501/OC-PN) obliga a trazabilidad documental y conservación de registros. Un repositorio con
historia limpia no es una preferencia estética; es cumplimiento.

**El workspace de usuario (D2 §3.6.2):**
> *"Each workspace has its own instance of version control (GitLab) and container registry
> (Harbor)."*

---

## 5. Laboratorio

No necesitas desplegar GitLab entero para aprender lo que te toca. Dos caminos:

**Camino corto (recomendado para empezar):** usa GitLab.com gratuito o Gitea local para los
ejercicios 1–4, y céntrate en el pipeline.

**Camino completo:** despliega GitLab en el clúster con su chart. Es pesado (necesitarás
memoria) pero te enseña la parte que de verdad vas a operar: runners, PVC, PostgreSQL,
Ingress.

1. **Repositorio con estructura de Application Package**: `Dockerfile`, `app.cwl`, el código,
   y un `README` con entradas y salidas.
2. **Rama protegida.** Protege `main`. Intenta hacer push directo. Observa el rechazo.
   Haz el cambio por merge request.
3. **Pipeline básico.** `.gitlab-ci.yml` con tres stages: `validate` (lint del CWL con
   `cwltool --validate`), `build` (imagen Docker), `publish` (push a Harbor).
4. **Credenciales.** Configura el robot account de Harbor como variable protegida y
   enmascarada. Comprueba que **no aparece en los logs del job**.
5. **Tag y release.** Etiqueta `v1.0.0` y haz que el pipeline solo publique en tags
   (`rules: - if: $CI_COMMIT_TAG`).
6. **Runner en Kubernetes** (si vas por el camino completo): despliega `gitlab-runner` con
   ejecutor de Kubernetes y observa cómo cada job crea un pod.
7. **Rompe el pipeline** de cuatro formas distintas (§6) y aprende a leer cada fallo.

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Credencial de Harbor mal configurada | El pipeline falla en `publish` con `unauthorized` |
| Variable **no** marcada como enmascarada | El secreto aparece en el log del job. **Hazlo una vez para no olvidarlo** |
| Runner sin recursos suficientes | El job queda en cola o el pod muere por OOM |
| Push directo a rama protegida | El rechazo y su mensaje |
| Artefacto expirado que otro job necesita | Por qué la política de expiración importa |
| `.gitlab-ci.yml` con YAML inválido | El error de validación de pipeline |
| CWL inválido publicado sin validar | Por qué el stage `validate` existe |

---

## 7. Averías de producción que este bloque entrena

No hay una avería del catálogo §16 exclusiva de GitLab, pero es el **origen** de dos:

- **Avería 2** (`ImagePullBackOff`): si el pipeline no publicó la imagen, el tag no existe.
- **Avería 9** (workflow que falla en el paso 3, imagen sin GDAL): la imagen se construyó
  mal, y eso se arregla en el Dockerfile, en GitLab.

La avería propia de GitLab —*"el pipeline lleva 40 minutos en cola"*— es de disponibilidad de
runners y suele ser cuota o recursos.

---

## 8. Árbol de diagnóstico: "el pipeline falla"

1. **¿En qué stage?** El log del job te lo dice. Empieza por ahí, no por el principio.
2. **¿Es el código o es la infraestructura?** Si el fallo es un test, es del desarrollador.
   Si es `unauthorized`, `no space left`, `timeout` o `pod evicted`, es tuyo.
3. **¿Hay runner disponible?** Un job en `pending` eterno es falta de runner, no fallo.
   `kubectl get pods -n gitlab-runner`.
4. **¿Las credenciales llegaron?** ¿La variable está protegida y la rama es protegida?
   Una variable protegida **no se expone en ramas no protegidas** — causa clásica de
   "funciona en main pero no en mi rama".
5. **¿El runner alcanza Harbor?** Prueba desde un pod en el mismo namespace.
6. **¿Cuota o espacio?** Almacenamiento de artefactos, cuota del proyecto de Harbor.
7. **¿Es el `.gitlab-ci.yml`?** Usa el validador de CI de la propia interfaz.

---

## 9. Comandos de bolsillo

```bash
# API de GitLab (con token personal)
curl -s -H "PRIVATE-TOKEN: $GL_TOKEN" \
  "$GITLAB/api/v4/projects?membership=true&per_page=100" | jq -r '.[].path_with_namespace'

# Últimos pipelines de un proyecto
curl -s -H "PRIVATE-TOKEN: $GL_TOKEN" \
  "$GITLAB/api/v4/projects/$PID/pipelines?per_page=10" \
  | jq -r '.[] | "\(.id) \(.ref) \(.status) \(.created_at)"'

# Jobs de un pipeline y por qué falló
curl -s -H "PRIVATE-TOKEN: $GL_TOKEN" \
  "$GITLAB/api/v4/projects/$PID/pipelines/$PIPE/jobs" \
  | jq -r '.[] | "\(.stage)/\(.name) \(.status)"'

# Runners registrados
curl -s -H "PRIVATE-TOKEN: $GL_TOKEN" "$GITLAB/api/v4/runners/all" \
  | jq -r '.[] | "\(.description) \(.status) \(.online)"'

# Runners en el clúster
kubectl get pods -n gitlab-runner
kubectl logs -n gitlab-runner -l app=gitlab-runner --tail=50

# Validar CWL antes de publicar (el stage que evita disgustos)
cwltool --validate app.cwl
```

---

## 10. Criterio de dominio

- [ ] Creo un repositorio con la estructura de un Application Package (código + CWL + Dockerfile).
- [ ] Escribo un `.gitlab-ci.yml` con validate / build / publish.
- [ ] Configuro credenciales como variables protegidas y enmascaradas, y **verifico que no se filtran al log**.
- [ ] Protejo `main` y explico cómo Keycloak determina quién puede mergear.
- [ ] Diagnostico un pipeline fallido y **sé decir si el problema es del desarrollador o mío**.
- [ ] Explico la cadena completa commit → CI → Harbor → Helm → Kubernetes → rollback.
- [ ] Sé qué se versiona en GitLab (código, CWL, Dockerfiles) y qué en Harbor (imágenes).
- [ ] Opero runners en Kubernetes y sé por qué un job queda en cola.

---

## 11. Artefactos que produces

1. **Un pipeline de referencia** versionado, que sirva de plantilla para Application
   Packages nuevos.
2. **Documentación del flujo de cambios**: ramas, aprobaciones, quién puede mergear qué.
   Este documento **es** tu proceso de gestión de cambios funcional.

**Alimentan:** Producto 6 (estandarización de procesos: gestión de cambios), Producto 8
(auditoría de uso de procedimientos). Y cubren directamente una de las brechas del análisis
ESA: *Functional Change Management — Not covered*.

---

## 12. Qué preguntar

**A ESA / Terradue:**
1. **¿Qué parte del ciclo de vida de aplicaciones (GitLab, Harbor, workspaces) administro yo y qué parte administran ustedes?**
2. ¿Dónde vive el repositorio de referencia del Middleware? ¿Es el mismo GitLab de la plataforma o uno externo?
3. ¿Los Application Packages operativos se mantienen en un grupo común? ¿Quién aprueba una versión nueva?
4. ¿Qué pipelines existen ya y cuál es el estándar que debe seguir uno nuevo?
5. ¿Se usa el registro de contenedores de GitLab o solo Harbor?
6. ¿Cuál es la política de expiración de artefactos de pipeline, dado que los Application Packages se guardan como tales?

**Al proveedor:**
1. ¿GitLab corre dentro del clúster? Entonces sus datos están en PVC y en PostgreSQL — **¿qué entra en el respaldo del DBaaS y qué no?**
2. ¿Los runners consumen del mismo pool de nodos que el Middleware? ¿Hay riesgo de que un build agote recursos de producción?

---

## 13. Fuentes

**Documentos del proyecto:** D2 §3.4.2 y §3.4.4 (GitLab en el Application Registry: paquetes
como artefactos de CI, metadatos, control de versiones, control de acceso, búsqueda),
§3.4.3 (integración con el Execution Engine, el Workflow Engine y los workspaces), §3.5.4
(GitLab CI/CD en front-end), §3.6.2 y §3.6.4 (control de versiones por workspace), §6.1
(GitLab en el empaquetado), **§6.5 (Version Control and Update Mechanisms — repositorios,
branching, tagging, CI, y el ejemplo completo de la cadena)**, §6.6 (GitLab Access Controls y
ramas protegidas), §6.7 (reproducibilidad, colaboración, automatización), §6.8.6 (requisito
SHOULD sobre GitLab), §7.5 (GitLab).

**Documentación oficial:** `docs.gitlab.com` — CI/CD (`.gitlab-ci.yml` reference), Runners
(Kubernetes executor), Protected branches, CI/CD variables.

---

## 14. Bitácora / hallazgos

*(Repositorios reales, pipelines de referencia, fallos recurrentes y su causa, acuerdos sobre
quién aprueba cambios.)*
