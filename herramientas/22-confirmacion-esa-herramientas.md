# Confirmación ESA de cada herramienta — qué está en el contrato y qué elegí yo

**Propósito:** saber, para cada herramienta que estudio, si **ESA la nombra** en la
documentación contractual o si es una **elección mía de laboratorio**. La diferencia no es
académica: determina si los comandos que aprendo son trasladables a producción o si parte
del esfuerzo puede resultar específico de un producto que nadie ha contratado.

**Fuentes verificadas** (conteo literal de menciones, 2026-10-07):

| Doc | Archivo |
|---|---|
| **D1** | `T2-ESA-COPLACI-RS-24-028 D1 CopernicusLAC Centre Specification and Performance Requirements v1.4.pdf` |
| **D2** | `T2-ESA-COPLACI-DD-24-029 D2 System Architecture Description v1.3.pdf` |
| **D3** | `T2-ESA-COPLACI-ID-24-030 D3 Interface Control Document v1.3.pdf` |

**La fuente más autoritativa es D2 §7 "Technologies and Frameworks"** (pp. 72-76): un
catálogo nominal de productos. Lo que aparece ahí no admite discusión.

> D2 §7: CWL · Docker · Kubernetes · GitLab · Harbor · Argo Workflows · Kafka ·
> Crossplane · Prometheus · Grafana · ZOO Project · Titiler · PostgreSQL

---

## Estados

| Estado | Significado | Consecuencia para el estudio |
|---|---|---|
| 🟢 **Confirmada** | ESA la nombra por producto | Los comandos son los correctos. Sin riesgo |
| 🟡 **Confirmada con reservas** | Nombrada una sola vez o de forma indirecta | Estudiar, pero preguntar antes de profundizar |
| 🔴 **No confirmada** | ESA solo describe la *función*, no el producto | Separar API estándar de CLI del producto |

---

## Tabla de confirmación

| # | Ficha | Herramienta | D1 | D2 | D3 | Estado | Base |
|---|---|---|---|---|---|---|---|
| 01 | [01-kubernetes.md](01-kubernetes.md) | Kubernetes | 17 | 52 | 2 | 🟢 | D2 §7.4 |
| 02 | [02-helm.md](02-helm.md) | Helm | — | 8 | 1 | 🟢 | D2 §3.6.2, §6.4 |
| 03 | [03-prometheus-grafana.md](03-prometheus-grafana.md) | Prometheus + Grafana | — | 13 / 8 | — | 🟢 | D2 §7.10, §7.11 |
| 04 | [04-fundamentos-linux-git-yaml.md](04-fundamentos-linux-git-yaml.md) | Linux · Git · YAML | — | — | — | 🟢 | Transversal, no es producto |
| 05 | [05-stac-pgstac-stac-fastapi.md](05-stac-pgstac-stac-fastapi.md) | STAC · PgSTAC · stac-fastapi | 9 | 157 | 46 | 🟢 | D2 Fig. 13 "STAC FastAPI Interface"; PgSTAC ×5 |
| 06 | [06-s3-minio.md](06-s3-minio.md) | **S3 / MinIO** | **0** | **0** | **0** | 🔴 | Solo *"S3-compatible object storage"* |
| 07 | [07-argo-workflows.md](07-argo-workflows.md) | Argo Workflows | 2 | 14 | 1 | 🟢 | D2 §7.7 |
| 08 | [08-argo-events.md](08-argo-events.md) | Argo Events | — | 5 | — | 🟢 | D2 §3.3 |
| 09 | [09-keycloak.md](09-keycloak.md) | Keycloak | — | 42 | 3 | 🟢 | D2 §3.5, D3 §6 |
| 10 | [10-harbor.md](10-harbor.md) | Harbor | — | 31 | 1 | 🟢 | D2 §7.6 |
| 11 | [11-gitlab.md](11-gitlab.md) | GitLab | — | 47 | — | 🟢 | D2 §7.5 |
| 12 | [12-argocd.md](12-argocd.md) | **ArgoCD** | — | **1** | — | 🟡 | Una sola mención (D2 §3.6.2) frente a 47 de GitLab |
| 13 | [13-crossplane.md](13-crossplane.md) | Crossplane | — | 19 | 1 | 🟢 | D2 §7.9 |
| 14 | [14-external-secrets-operator.md](14-external-secrets-operator.md) | External Secrets Operator | — | 4 | — | 🟢 | D2 §3.6.2, §3.5.3 |
| 15 | [15-cwl-calrissian.md](15-cwl-calrissian.md) | CWL · cwltool · Calrissian | 6 | 69 / 7 | 4 | 🟢 | D2 §6.2, §7.2; Calrissian ×7 |
| 16 | [16-titiler-cog.md](16-titiler-cog.md) | Titiler + COG | — | 19 | 1 | 🟢 | D2 §7.13 |
| 17 | [17-docker.md](17-docker.md) | Docker / podman / OCI | 3 | 21 | 2 | 🟢 | D2 §7.3; podman citado en §3.3.4 |
| 18 | [18-ingress-tls-cert-manager.md](18-ingress-tls-cert-manager.md) | **Ingress NGINX · cert-manager** | **0** | **0** | **0** | 🔴 | Solo *"load balancers"* y *"TLS 1.2 or later"* |
| 19 | [19-postgresql-postgis.md](19-postgresql-postgis.md) | PostgreSQL + PostGIS | 4 | 18 / 2 | — | 🟢 | D2 §7.14 |
| 20 | [20-kafka.md](20-kafka.md) | Apache Kafka | — | 10 | — | 🟢 | D2 §7.8 |
| 21 | [21-zoo-ogc-api-processes.md](21-zoo-ogc-api-processes.md) | ZOO Project / OGC API–Processes | 6 | 7 | 6 | 🟢 | D2 §7.12 |

**Resultado: 18 confirmadas · 1 con reservas · 2 no confirmadas.**

---

## Las tres excepciones, en detalle

### 🔴 06 — S3 / MinIO

ESA dice *"S3-compatible object storage"* y *"Managed object storage"*, nunca un producto.
El proveedor puede entregar MinIO, Ceph RGW u otro. MinIO `RELEASE.2025-09-07` es **mi
elección de laboratorio**: es el único endpoint S3 real que corre en WSL2 sin root y sin
coste.

| Lo practicado | Portabilidad |
|---|---|
| Buckets, prefijos, `put`/`get`/`cp`, ETag, media types | **Alta** — API S3 estándar |
| Versionado, delete marker, recuperación por versión | **Alta** — si el servicio lo soporta |
| URLs prefirmadas y expiración (`X-Amz-*`) | **Alta** — estándar |
| Políticas de acceso | **Media** — MinIO usa JSON estilo IAM; otros no |
| `mc admin` (usuarios, políticas, info) | **Baja** — específico de MinIO |
| `mc ilm tier add/check` | **Baja** — específico, y **ya bloqueó una prueba** |

**Mitigación:** redactar runbooks sobre `aws s3api` / SDK y JSON de política estilo AWS;
marcar explícitamente lo específico de MinIO. Pregunta abierta: **S3-00**.

### 🔴 18 — Ingress NGINX + cert-manager

ESA solo dice *"The platform employs load balancers to distribute incoming traffic"*
(D2 §9) y exige *"TLS 1.2 or later"* (D2 §8.3). No nombra controlador de Ingress ni
gestor de certificados. Si el proveedor termina TLS en su propio balanceador,
cert-manager podría no existir en mi plano de responsabilidad.

| Lo practicado | Portabilidad |
|---|---|
| Recurso `Ingress`, `Service`, `NetworkPolicy` | **Alta** — API estándar de Kubernetes |
| Anotaciones `nginx.ingress.kubernetes.io/*` | **Baja** — intransferibles a Traefik o a un LB gestionado |
| CRDs `ClusterIssuer` / `Certificate` de cert-manager | **Baja** — propias del producto |

**Mitigación:** priorizar el recurso `Ingress` estándar y `NetworkPolicy` (que sí es API
de Kubernetes) sobre las anotaciones del controlador.

### 🟡 12 — ArgoCD

Aparece **una sola vez** en 83 páginas de D2 — *"ArgoCD: Synchronises the user repositories
with the Kubernetes cluster"* (§3.6.2) — mientras GitLab aparece 47 veces y tiene sección
propia en §7. Base insuficiente para tratarlo como pieza confirmada. Cabe que el GitOps
real lo hagan los pipelines de GitLab.

**Mitigación:** mantenerlo en Prioridad 3, nivel conceptual, hasta tener respuesta.

---

## Lo que esta tabla NO dice

**Que una herramienta esté nombrada no significa que yo la administre.** El criterio de
inclusión de esta carpeta sigue vigente: Kubernetes está confirmado, pero su plano de
control es del proveedor; PostgreSQL está confirmado, pero el motor es DBaaS. La
confirmación responde *"¿es este el producto?"*, no *"¿es mío?"*. Para lo segundo, la
frontera está en cada ficha y en
[../Guia_Estudio_Administrador_Middleware_Copernicus.md](../Guia_Estudio_Administrador_Middleware_Copernicus.md) §3.

**Que una herramienta no esté nombrada no significa que estudiarla sea inútil.** La
competencia (administrar object storage S3, exponer servicios con TLS) es exigida por ESA
en ambos casos. Lo que está en duda es el CLI, no la materia.

---

## Mantenimiento

Cuando ESA o el proveedor respondan, actualizar la fila **y la fecha**. Las preguntas que
cierran estas dudas viven en
[../preguntas-para-esa.md](../preguntas-para-esa.md): **S3-00** (implementación S3),
y las pendientes de ingress/TLS y ArgoCD.

*Creado el 2026-10-07. Conteos obtenidos por extracción de texto de los tres PDFs y
recuento literal, no por lectura parcial.*
