# CopernicusLAC Panamá — Guía de Deployment (base de conocimiento para Claude)

> **Fuente:** *Copernicus LAC Infra – Deployment Guide*, Terradue, ref. `T2-ESA-COPLACI-PR-25-007`, **Issue 2.2**, fecha 2026-10-23, estado *Issued*, 60 páginas. Contrato ESA 4000144570/24/I-KE.
> **Qué es este archivo:** transcripción estructurada y completa del PDF (texto, tablas, comandos, YAML y contenido de las 11 figuras). Los identificadores, nombres de recursos, comandos y mensajes de error están tal cual en el original (inglés); la prosa está en español.
> **Cómo usarlo (Claude):** responder desde aquí citando la sección original (`§x.y`). Los nombres de recursos son los reales del clúster de Panamá. Si algo aparece como *To deploy*, *TBC*, *TBV* o *TEMPORARY*, decirlo: no es un procedimiento validado. Revisar la sección 0.3 (inconsistencias del documento) antes de afirmar fechas o estados.
> **Documento vivo:** Terradue lo irá actualizando; los estados son los del 23-oct-2026 (con algunos datos del 26 y 28-oct).
> **Confidencialidad:** © Terradue 2026; contiene IPs, hostnames y topología interna. No publicar.

---

## 0. Referencia rápida

### 0.1 Datos clave

| Dato | Valor |
|---|---|
| Repositorio de infraestructura | `infra-copernicuslac-panama` (rama `main` = estado deseado) |
| Remote Git (operadores) | `https://git.copernicuslac.aig.gob.pa/copernicuslac/infra-copernicuslac-panama.git` |
| Repo visto por Argo CD (in-cluster) | `http://copernicuslac-gitlab-webservice-default.gitlab-system.svc:8181/copernicuslac/infra-copernicuslac-panama.git` |
| Contexto kubeconfig | `copernicuslac-panama` (override: `export KUBE_CONTEXT=…`) |
| Rancher (management) | `svr-rke-prime-pan.ifxcloud.com` |
| Dominio público | `*.copernicuslac.aig.gob.pa` |
| PostgreSQL gestionado | nodo01 `10.0.0.3` (primary), nodo02 `10.0.0.4` (réplica); clientes desde `192.168.80.0/24` |
| Object storage (StorageGRID S3) | `https://svr-cop-s3-pan.ifxcloud.com:10443` (path-style) |
| Registry de la plataforma (Harbor) | `cr.copernicuslac.aig.gob.pa` |
| Realm Keycloak | `CopernicusLAC-Platform` — issuer `https://iam.copernicuslac.aig.gob.pa/realms/CopernicusLAC-Platform` |
| Namespace de recursos Crossplane (Tier 3) | `platform` |
| Node pool de la plataforma | `nodeSelector: {aig/node-pool: static}` (nodo-worker-11…16) |
| ClusterIssuer | `letsencrypt-prod-contour` (HTTP-01 vía contour-external) |
| ClusterSecretStore | `vault-backend` (Vault KV v2, mount `secrets/`) |
| Soporte Terradue | copernicuslac-support@terradue.com |
| Proveedor de infraestructura / DBaaS | IFX (ifxcloud) |

### 0.2 Reglas de oro

1. **Git es la única vía de escritura.** Nada de `kubectl edit`, `helm upgrade` ni cambios por UI sobre objetos gestionados. Los cambios manuales en Tier 3 se revierten solos (self-heal).
2. **Nada gestiona a su propio gestor.** Argo CD, GitLab y Harbor nunca son recursos Crossplane; Crossplane nunca es una Application de Argo CD.
3. **Nunca desinstalar un provider de Crossplane** ni borrar sus CRDs: se borran todos los managed resources (todo Tier 3).
4. **Nunca borrar CRDs huérfanos** (borra todos los CR): re-anotarlos (§6.3).
5. **Nunca borrar a mano los PVC del namespace `kafka`** (StorageClass con reclaimPolicy Delete).
6. **DNS primero:** el nombre público debe resolver al load balancer externo antes de ejecutar el paso. No usar CoreDNS ni `/etc/hosts` como atajo.
7. **Secretos:** nunca en claro en Git, nunca en chat/ticket/línea de comandos. Un valor expuesto se rota de inmediato. Tier 1–2 → SOPS+age; Tier 3 → Vault.
8. **Versiones fijadas:** sin `latest`, sin rangos, sin tags `-develop`. `chart.version` exactamente como en `Chart.yaml` (sin prefijo `v` añadido).
9. **Ninguna base de datos ni datos masivos dentro del clúster.** Las BD embebidas de los charts siempre deshabilitadas.
10. **UIs administrativas no publicadas:** Argo CD, Vault, consola admin de Keycloak, Kafka UI, Argo Workflows UI → solo `kubectl port-forward`.
11. **Un commit = un componente;** un upgrade cambia una Release a la vez.
12. **Tras reiniciar cualquier pod de Vault → `ops/vault/unseal.sh`.**
13. Paquetes Crossplane: copiar **solo** con `skopeo copy --preserve-digests`.

### 0.3 Inconsistencias detectadas en el PDF (tenerlas en cuenta)

| Tema | Lo que dice el documento | Lectura recomendada |
|---|---|---|
| Fechas | Fecha del documento 2026-10-23, pero §2.5 dice "versiones desplegadas el 28-oct-2026", §4.5 "Tier 1 publicado el 26-oct-2026" y Tabla 14 "shared_buffers subido el 2026-10-26" | El texto fue editado después de la fecha de portada; tomar el estado como "finales de octubre 2026" |
| Publicación de `git.` y `cr.` | Fig. 1 y Fig. 2 los marcan "deployed, not yet published (DNS pending)"; el texto (change record, Tabla 13, §4.5, Anexo A) dice publicados y *Live* | Vale el texto: publicados. Las figuras están desactualizadas |
| Auto-creación de topics Kafka | Leyenda de la Fig. 10: "Auto topic creation is disabled: every destination topic must exist as a KafkaTopic"; §8.1 y §9.2: `auto.create.topics.enable true` (decisión 2026-10-23) | Vale el texto: auto-creación habilitada. Los topics de Argo Events sí se declaran como KafkaTopic |
| Kafka UI | El change record de la 2.0 dice "Kafka UI removed"; en 2.2 está desplegado (chart 1.4.2) | Desplegado |
| Anexo B | El título dice "cambios respecto a Issue 2.1"; §1.5 dice "respecto a Issue 2.0" | El contenido compara contra el clúster/versión anterior |
| DNS de `view`, `dashboards`, `results`, `www`, `apps`, `hub`, `drive` | Tabla 13: DNS *Published*; pero los servicios están *To deploy* | DNS existe, servicio no |
| Referencia cruzada | §5 remite a "public chart repositories of section 4" | Están en §3.6 |
| OPA | Inventario: chart 0.2.5 desplegado, "0.2.6 planned" | — |

---

## 1. Introducción (§1)

### 1.1 Propósito y contexto
- Referencia técnica para **desplegar, configurar y operar** la plataforma CopernicusLAC en Panamá: arquitectura, prerequisitos, tiers, repositorio de entrega y procedimientos de instalación/verificación.
- Se usa junto con el repositorio de entrega (manifiestos, configuración, scripts) y el plan de formación [RD-2].
- **CopernicusLAC**: iniciativa ESA + Comisión Europea (DG-INTPA) + Gobierno de Panamá para un Centro Regional Copernicus en Panamá (hub regional de datos EO para LAC, foco en reducción de riesgo de desastres y recuperación). Parte de la EU-LAC Digital Alliance / estrategia Global Gateway.
- **Audiencia:** administradores de sistemas e ingenieros de plataforma de AIG, personal de Terradue y del proveedor de infraestructura.
- Lectura: capítulos 2–6 antes de cualquier despliegue; 7–10 por componente; 11 operaciones; 12 estado y pendientes.

### 1.2 Alcance
Cubre: arquitectura; infraestructura y prerequisitos externos (RKE2, node pools, Longhorn, DNS, load balancer, PostgreSQL 16 HA gestionado, StorageGRID); paquete de entrega; bootstrap de Tiers 1 y 2; entrega de Tier 3 (capas 10–70); despliegue de cada componente con versiones exactas; modelo de seguridad (Keycloak, OPA, oauth2-proxy, rutas); operaciones día 2; estado, puntos abiertos y ajustes temporales.

**Fuera de alcance:** instalación de Rancher y de las VMs, operación del PostgreSQL y object storage gestionados, zona DNS y load balancer externo, desarrollo de las aplicaciones de procesamiento.

### 1.3 Convenciones (Tabla 1)

| Convención | Significado |
|---|---|
| `TEMPORARY` | Ajuste vigente solo hasta cumplir un prerequisito externo. Marcado con la misma palabra en el repo y listado en §12.3 |
| `TODAY / TARGET` | Diferencia explícita entre lo que corre y el objetivo |
| `DONE WHEN` | Checks que cierran un paso; completo solo si pasan todos |
| `<placeholder>` | Valor que pone el operador (las contraseñas nunca se escriben en comandos ni en Git) |
| `[TBC-n]` | Punto por confirmar; lista en §12.2 |
| Comandos | Desde workstation del operador (macOS o Linux), en la raíz del repo, contexto `copernicuslac-panama` obtenido de Rancher. Los que leen secretos evitan el historial (`read -s`, stdin, archivos que se borran) |
| Shell | Los prompts interactivos (`read -p`) son para **bash**. En macOS (zsh) ejecutarlos dentro de `bash -c '…'` |
| Nombres de recursos | Los reales del clúster y repo de Panamá |

### 1.4 Documentos aplicables y de referencia

| Ref. | Título | Issue |
|---|---|---|
| [SOW] | CopernicusLAC Infrastructure Support (EOP-EOP-SI-SOW-2023-15) | 1.0 |
| [CTR] | ESA Contract No. 4000144570/24/I-KE con Terradue Srl | 01/03/2023 |
| [D1] | CopernicusLAC Centre Specification and Performance Requirements | 1.4 |
| [D2] | System Architecture Description | 1.3 |
| [D3] | Interface Control Document | 1.3 |
| [D11] | Data Exploration and Processing Validation Plan and Report | 1.3 |
| [PROP] | T2-ESA-AO1-11947-OF-23-062 Terradue Offer for CopLAC Infra | 1.0 |
| [RD-2] | T2-ESA-COPLACI-PL-26-049 CopernicusLAC Infra Training Plan | 2.4 |
| [RD-3] | Crossplane docs v2 — docs.crossplane.io | 2.4 |
| [RD-4] | Argo CD docs — argo-cd.readthedocs.io | 3.5 |
| [RD-5] | Longhorn docs — longhorn.io/docs | 1.10 |
| [RD-6] | Strimzi docs — strimzi.io/documentation | 1.1 |
| [RD-7] | Repositorio `infra-copernicuslac-panama` (paquete de entrega, §4.2) | 2026-10-23 |
| [RD-8] | pgSTAC — github.com/stac-utils/pgstac, tag v0.9.12 | 0.9.12 |

### 1.5 Acrónimos
AIG (Autoridad Nacional para la Innovación Gubernamental) · API · CDSE (Copernicus Data Space Ecosystem) · CNI · COG (Cloud Optimized GeoTIFF) · CRD · CWL (Common Workflow Language) · DR · EO · ESA · ESO (External Secrets Operator) · HA · HSTS · JWT · KRaft (Kafka sin ZooKeeper) · KV (motor Key/Value de Vault) · LAC · MR (Managed Resource, Crossplane) · OCI · OGC · OIDC · OPA (Open Policy Agent) · OTP · PVC · RBAC · RKE2 · RWO/RWX · S3 · SOPS (archivos cifrados en Git, con claves age) · SSO · STAC (SpatioTemporal Asset Catalog) · TBC (To Be Confirmed) · TLS · XR/XRD (Composite Resource / Definition, Crossplane). *TBV* = to be validated.

### 1.6 Historial de cambios del documento

| Fecha | Issue | Cambio |
|---|---|---|
| 2025-03-25 | 1.0 | Emisión inicial: prerequisitos y Data Discovery |
| 2025-05-06 | 1.1 | Instalación de TiTiler-pgSTAC |
| 2025-05-21 | 1.2 | Instalación de STAC Browser |
| 2025-07-27 | 1.3 | Separación prerequisitos/componentes; más componentes; automatización |
| 2025-12-28 | 1.4 | Front-end services, User Workspace, estado de despliegue |
| 2026-10-01 | 2.0 | Reescritura para la arquitectura final: GitOps con Argo CD + Crossplane v2 como única vía; tiers; Longhorn, Contour, PostgreSQL 16 HA y StorageGRID fuera del clúster; todos los componentes. Eliminados OpenEBS, NGINX Ingress, Kafka UI y provider-argocd |
| 2026-10-15 | 2.1 | Despliegue de Panamá con el modelo final: tiers redefinidos (Tier 1 como Applications con sync manual, Tier 2 Crossplane con helmfile, Tier 3 capas 10–70); estructura del repo, SOPS/age, `bootstrap.sh`, Harbor y Harbor seed; versiones reales; modelo de seguridad; estado |
| 2026-10-23 | 2.2 | Tier 1 publicado (DNS `git.` y `cr.`): exposición, Harbor seed, login de GitLab y Harbor por Keycloak, robot accounts de Harbor (`harbor-robots`, `harbor-oidc`); paquetes Crossplane y todos los charts servidos desde Harbor; acceso Git de operadores; `shared_buffers` aplicado; issue de StorageGRID 12.0.0 (403 en vez de 404) que bloquea pushes de imágenes a Harbor |

---

## 2. Arquitectura de la plataforma (§2)

### 2.1 Vista funcional (Tabla 5 + Fig. 1)

| Módulo funcional | Implementado por |
|---|---|
| Security and Access Control | Keycloak (identidad, OIDC, OTP), Vault + External Secrets (secretos), OPA (autorización en Envoy), oauth2-proxy (login de navegador en catálogos), cert-manager (TLS) |
| Data Ingestion | Paso *stage-in* del CWL runner, leyendo de CDSE |
| Data Processing | Processing API (OGC API – Processes, `mate-api` sobre Knative), Argo Workflows, plantillas del CWL runner, application packages |
| Data Discovery and Access | STAC API (stac-fastapi sobre pgSTAC), TiTiler-pgSTAC, Geobrowser, STAC Browser, StorageGRID |
| Front-End Services | Portal (landing page, CMS, marketplace, back office) |
| User Workspace | App Hub (JupyterHub), Drive (archivos compartidos), GitLab |
| Application Repository | GitLab (código), Harbor (imágenes, charts, paquetes Crossplane) |
| Resource Management | Clúster RKE2 gestionado por Rancher, Longhorn, Argo CD, Crossplane, Rancher Monitoring |
| Messaging | Kafka (Strimzi, KRaft) y Argo Events, con eventos de estado del procesamiento |

**Fig. 1 (módulos funcionales, estado al 23-oct-2026):** misma agrupación que la tabla. Detalles adicionales que aporta: App Hub = JupyterHub con JupyterLab, VS Code, QGIS; Drive = archivos compartidos sobre StorageGRID; Argo Workflows = motor con archivo en PostgreSQL; CWL runner + Calrissian = motor de ejecución; Results catalogs = uno por tema (`results.`); StorageGRID S3 = resultados COG y artifacts; Contour/Envoy = punto de entrada público. Estados: desplegado (verde) todo lo de seguridad, Processing API, Catalog API, Argo Workflows, Knative, Argo Events+Kafka, STAC API, StorageGRID y Resource Management; *to deploy* (gris): Portal, Geobrowser, STAC Browser, App Hub, Drive, CWL runner, TiTiler, Results catalogs, Application packages, Stage-in.

### 2.2 Capas lógicas (Fig. 2)

Cada capa depende solo de las inferiores. El mismo orden rige el bootstrap (§4.5), las sync waves de Argo CD (§6.1) y el troubleshooting (§11.3). Las carpetas de `platform/` llevan el número de capa.

| Capa | Nombre | Contenido | Estado (23-oct-2026) |
|---|---|---|---|
| 70 | Application packages | Composition `calrimate` · ApplicationPackages (uno por proceso) | to deploy |
| 60 | User services | Portal · App Hub · Drive | to deploy |
| 50 | Processing | Argo Workflows · Argo Events · Kafka event bus · CloudEvents webhook · processing API (mate-api) · CWL runner | deployed · CWL runner to deploy |
| 40 | Data | Strimzi + Kafka (KRaft) · Kafka UI · STAC API · TiTiler-pgSTAC · Geobrowser · STAC Browser | Kafka y STAC API deployed · resto to deploy |
| 30 | Serving | Knative Operator · KnativeServing (Serving + net-contour) | deployed |
| 20 | Identity | Keycloak (HA) · OPA (Envoy external authorisation) | deployed |
| 10 | Core | Vault (HA, Raft) · External Secrets Operator · ClusterSecretStore `vault-backend` | deployed |
| T2 | Crossplane | Crossplane 2.4.2 · provider-kubernetes · provider-helm (Terradue) · ProviderConfigs | deployed |
| T1 | Bootstrap services | Argo CD · cert-manager · Contour (external, internal) · Valkey · GitLab · Harbor | deployed |
| T0 | Infrastructure | RKE2 v1.33.6 · Cilium · Longhorn · Rancher Monitoring · PostgreSQL 16 HA y StorageGRID gestionados fuera del clúster | provided |

La Application de Argo CD de cada capa tiene sync-wave = número de capa: una capa espera a que todas las inferiores estén Synced y Healthy.

### 2.3 La plataforma de un vistazo (Fig. 3)

- Todo el tráfico público entra por **Envoy (Contour, `contour-external`, TLS, en todos los workers)**.
- Usuarios (navegador/API) → Envoy → Portal (`www`, `apps`), App Hub (`hub`), Keycloak (`iam`, OIDC), Drive (`drive`), Processing API (`processing`, Knative), STAC services (`discover`, metadata, `view`).
- Processing API → **Argo Workflows** (Calrissian, CWL) → **Argo Events** (EventSource, Sensor) → **Kafka** (Strimzi, KRaft, 3 nodos).
- Argo Workflows lee/escribe: Object storage (StorageGRID S3, gestionado, externo), PostgreSQL 16 HA (gestionado, todas las BD), CDSE (datos de entrada, externo), Longhorn (`longhorn`, `longhorn-processing` RWX).
- *Platform plumbing:* Vault + External Secrets · cert-manager · Crossplane · Argo CD · Rancher Monitoring.
- Además: Harbor (registry) y Valkey (cachés compatibles con Redis).

### 2.4 Tiers de despliegue y propiedad (Tabla 6, Fig. 4)

Cada objeto tiene exactamente un dueño, y cada dueño está en un tier inferior al de lo que gestiona → sin dependencias circulares.

| Tier | Contiene | Instalado por | Se cambia mediante |
|---|---|---|---|
| **0** | Clúster RKE2, node pools, Cilium, Longhorn, Rancher Monitoring | Rancher | Rancher UI / configuración del clúster |
| **1** | Argo CD; cert-manager; Contour (external, internal); Valkey para GitLab; GitLab; Valkey para Harbor; Harbor; exposición de GitLab y Harbor (ClusterIssuer, Certificates, HTTPProxies) | Operador: helmfile (Argo CD), Applications de Argo CD con **sync manual** (los demás), kubectl (exposición) — todo vía `bootstrap/bootstrap.sh` | Merge request en `bootstrap/`, luego el paso correspondiente de `bootstrap.sh` (kubectl apply + diff + sync manual) |
| **2** | Crossplane core, provider-kubernetes, provider-helm (fork Terradue), DeploymentRuntimeConfig, ProviderConfigs | Operador: **helmfile (nunca Argo CD)** | Merge request en `bootstrap/`, `helmfile diff` / `apply` |
| **3** | Todo lo demás (capas 10–70): Releases y Objects de Crossplane en namespace `platform` | Argo CD (root Application → una Application por capa) + Crossplane | Merge request en `platform/` — sync automático, prune y self-heal |

**Regla:** si Crossplane falla, Argo CD aún repara Tier 3 desde Git; si Argo CD falla, se reinstala con helmfile; si GitLab cae, Argo CD conserva el último estado y nada se desinstala.

- **Por qué Tier 1 no tiene sync automático:** GitLab puede alojar el repo que lee Argo CD y Harbor aloja los paquetes de Crossplane; un upgrade automático que los rompa no podría revertirse por GitOps.
- **Por qué Crossplane no lo entrega Argo CD:** quitar un provider o sus CRDs borra todos los managed resources y desinstala Tier 3. En helmfile, ese radio de impacto queda limitado a una acción deliberada del operador.

**Actores (Fig. 4):** *Infra repository* (GitLab in-cluster, `main` = estado deseado) · *Operator* (kubeconfig vía Rancher, clave SOPS/age, `bootstrap.sh`) · *Argo CD* (apps Tier 1: sync manual; Tier 3: root app, automático) · *Crossplane* (Releases/Objects → servicios).

**Ubicación de cada componente (Tabla 7)**

| Componente | Tier | Razón |
|---|---|---|
| Argo CD | 1 | Entrega Tier 3; no debe depender de lo que entrega. Instalación con helmfile, solo port-forward |
| cert-manager, Contour | 1 | Harbor (`cr.`) y GitLab (`git.`) deben publicarse con TLS antes de que Crossplane pueda bajar sus paquetes de Harbor; Knative reutiliza el mismo Contour |
| Valkey (×2), GitLab, Harbor | 1 | Fuente de la configuración y de los artefactos de los demás tiers |
| Crossplane + providers | 2 | Radio de impacto; upgrades controlados |
| Knative Serving | 3 (capa 30) | No lo necesitan Tiers 1–2; lo entrega el chart del Knative Operator |
| Vault, ESO | 3 (capa 10) | Solo los necesitan los secretos de Tier 3; los de Tier 1–2 son archivos SOPS |

### 2.5 Inventario de componentes (Tabla 8)

Estado: **Deployed** (corriendo y verificado), **Partial** (corriendo con ajustes temporales o checks pendientes), **To deploy** (manifiestos o insumos incompletos).

| Componente | Namespace | Versión (chart / app) | Tier · capa | Estado |
|---|---|---|---|---|
| RKE2, Cilium, CoreDNS | kube-system | v1.33.6+rke2r1 · Cilium 1.18.3 | 0 | Provided |
| Longhorn | longhorn-system | 1.10.2 | 0 | Provided |
| Rancher Monitoring | cattle-monitoring-system | 107.2.1+up69.8.2 | 0 | Provided |
| Argo CD | argocd | chart 10.10.5 / v3.5.5 | 1 | Deployed |
| cert-manager | cert-manager | v1.21.0 | 1 | Deployed |
| Contour external + internal | contour-external, contour-internal | net-contour knative-v1.20.1 (Contour 1.33.1, Envoy 1.35.8) | 1 | Deployed |
| Valkey para GitLab | gitlab-system | valkey-helm @e840544 (Valkey 9.1.2) | 1 | Deployed |
| GitLab | gitlab-system | chart 9.11.13 / 18.11.12 | 1 | Deployed |
| Valkey para Harbor | harbor-system | valkey-helm @e840544 | 1 | Deployed |
| Harbor | harbor-system | chart 1.19.4 / 2.15.4 | 1 | Deployed |
| Crossplane | crossplane-system | 2.4.2 | 2 | Deployed |
| provider-kubernetes | crossplane-system | v1.4.1 (community) | 2 | Deployed |
| provider-helm (Terradue) | crossplane-system | v1.0.0 | 2 | Deployed |
| Vault | secret-management | chart 0.34.1 / 2.0.4, 3 pods Raft | 3 · 10 | Deployed |
| External Secrets Operator | eso | 2.13.0 | 3 · 10 | Deployed |
| Keycloak (keycloakx) | iam | 7.4.0 / 26.8.1, 2 réplicas | 3 · 20 | Deployed |
| OPA | opa | chart 0.2.5, imagen 1.21.2-envoy-3 | 3 · 20 | Deployed (0.2.6 planned) |
| Knative Operator + Serving | knative-operator, knative-serving | chart 1.20.1 / Serving 1.20.1 | 3 · 30 | Deployed |
| Strimzi operator | kafka-operator | 1.1.0 | 3 · 40 | Deployed |
| Kafka cluster | kafka | Kafka 4.2.1 (KRaft), 3 nodos | 3 · 40 | Deployed |
| Kafka UI | kafka-ui | chart 1.4.2 | 3 · 40 | Deployed |
| STAC API (discover) | catalog | chart 2.0.7 / stac-fastapi-pgstac 6.2.1, pgSTAC 0.9.12 | 3 · 40 | Deployed |
| TiTiler-pgSTAC | catalog | chart 3.0.6 / 2.1.0 (planned) | 3 · 40 | To deploy |
| Geobrowser | geobrowser | chart 1.0.0 / 2.1.7 (planned) | 3 · 40 | To deploy |
| STAC Browser, results catalogs | catalog | — | 3 · 40 | To deploy |
| Argo Workflows | processing | chart 0.45.26 / v3.7.2 | 3 · 50 | Deployed |
| Argo Events | processing | chart 2.4.27 | 3 · 50 | Deployed |
| Kafka event bus, CloudEvents webhook | processing | 0.1.0 · 0.3.0 | 3 · 50 | Deployed |
| Processing API (mate-api) | mate-api | chart 1.2.2, functions 1.2.0 | 3 · 50 | Deployed |
| CWL runner templates | processing | — | 3 · 50 | To deploy |
| Portal, App Hub, Drive | portal, app-hub, drive | — | 3 · 60 | To deploy |
| Composition calrimate, application packages | crossplane-system, processing | — | 3 · 70 | To deploy |
| PostgreSQL (gestionado) | fuera del clúster | 16 + PostGIS 3.6.1, HA | proveedor | Provided |
| Object storage (gestionado) | fuera del clúster | StorageGRID S3 | proveedor | Provided |

### 2.6 Decisiones clave de diseño (Tabla 9)

| Decisión | Razón |
|---|---|
| Git es la única vía de escritura | Todo cambio revisado, versionado y reversible; el historial es la auditoría. Los cambios manuales en Tier 3 se revierten (self-heal) |
| Tiers con un único dueño | Sin dependencia circular en bootstrap, upgrade o reparación |
| Tier 1 como Applications con sync manual | Valores revisados en Git y con diff de Argo CD, pero nada cambia GitLab, Harbor o el ingress sin un operador |
| Crossplane en helmfile, no en Argo CD | Un commit erróneo no puede quitar los providers y con ellos todo Tier 3 |
| Managed resources namespaced de Crossplane v2 | Releases y Objects (grupos API `*.m.*`) viven en namespace `platform` junto a sus ProviderConfigs |
| Fork Terradue de provider-helm | Detección de drift sobre los objetos renderizados por el chart (`enableDriftDetection`), no solo versión y values |
| Una Application de Argo CD por capa | Las capas arrancan en orden; un componente roto bloquea solo su capa y las superiores; `ApplyOutOfSyncOnly` mantiene los syncs pequeños |
| Secretos: SOPS para Tiers 1–2, Vault para Tier 3 | Los de Tier 1–2 se necesitan antes de que exista Vault (también en DR); los de Tier 3 nunca entran a Git |
| Harbor como registry de la plataforma | Imágenes, charts y paquetes Crossplane servidos desde la propia plataforma; cargados con un seed reproducible (§5.7) |
| Sin BD ni datos masivos en el clúster | Toda BD relacional en PostgreSQL 16 HA gestionado, todo archivo en StorageGRID |
| HTTPProxy de Contour para routing, OPA en Envoy | Un HTTPProxy por host con TLS de cert-manager; OPA autoriza antes de que la petición llegue al servicio |
| UIs administrativas no publicadas | Solo `kubectl port-forward` |
| Kafka en modo KRaft | Sin ZooKeeper; 3 nodos como controller y broker |
| Componentes de plataforma en el pool static | `nodeSelector aig/node-pool=static` para que la carga de procesamiento nunca desaloje los servicios de control |

---

## 3. Infraestructura (§3)

### 3.1 Clúster Kubernetes (Tabla 10)

Clúster RKE2 aprovisionado y gestionado por Rancher (`svr-rke-prime-pan.ifxcloud.com`). Rancher es dueño del ciclo de vida: upgrades de Kubernetes, alta/baja de nodos, snapshots de etcd y system charts.

| Ítem | Valor |
|---|---|
| Distribución | RKE2 v1.33.6+rke2r1 |
| Container runtime | containerd 2.1.5 |
| CNI | Cilium 1.18.3 (rke2-cilium) |
| Control plane | 7 nodos con roles control-plane y etcd, con taint (sin workloads) |
| Workers | 26 nodos; los servicios de plataforma corren en el pool static `nodo-worker-11…16` |
| Sistema operativo | Ubuntu 22.04 (workers y control-plane antiguos), Ubuntu 24.04 (control-plane nuevos) |
| Kubeconfig | Personal, descargado de Rancher; contexto `copernicuslac-panama` (override `export KUBE_CONTEXT=…`) |
| Upgrades | Planes de Rancher vía system-upgrade-controller |

> **IMPORTANTE — Compatibilidad:** todos los charts e imágenes se eligieron para Kubernetes 1.33. Antes de un upgrade *minor* de Kubernetes, revisar las APIs eliminadas de cada chart en `bootstrap/` y `platform/`.
> **etcd y zonas:** 7 miembros etcd de tamaño mixto en dos zonas de disponibilidad; la zona con la mayoría es punto único de fallo del control plane.

### 3.2 Node pools (Tabla 11)

| Pool | Nodos | Ejecuta | Label / taint |
|---|---|---|---|
| Control plane | `cp-cluster-k8s-copernicus-226 … 233` (7) | API server, etcd | Default de RKE2, tainted |
| Static (plataforma) | `nodo-worker-11 … 16` (6) | Argo CD, Crossplane, GitLab, Harbor, Valkey, Vault, ESO, Keycloak, OPA, control plane de Knative, Kafka, STAC, control plane de procesamiento | `aig/node-pool=static` (aplicado); sin taint |
| Processing | `nodo-worker-17 … 29` (13) | Pods de workflows y steps | por etiquetar y poner taint [TBC-6] |
| Storage | `nodo-worker-30 … 35` (6) | Réplicas de Longhorn (disco de datos de 10.4 TB cada uno) | `longhorn-storage=true` |
| Sin asignar | `nodo-worker-36` (1) | — | por decidir |

```bash
for n in 11 12 13 14 15 16; do
  kubectl label node nodo-worker-$n aig/node-pool=static --overwrite
done
```

- Todo componente de plataforma declara `nodeSelector: {aig/node-pool: static}` en la(s) clave(s) que ofrezca el chart (`global.nodeSelector`, controller/webhook/cainjector, claves por componente).
- Los DaemonSets que deben correr en todos lados (Envoy, Longhorn manager y CSI plugin, Cilium, exporters de monitoring) no llevan node selector.
- Los labels deben aplicarse también en los *machine pools* de Rancher para sobrevivir al reemplazo de nodos [TBC-6].

### 3.3 Almacenamiento (Tabla 12)

Longhorn 1.10.2 (app de Rancher) provee todo el almacenamiento persistente in-cluster. Capacidad del pool de storage: 6 × 10.4 TB brutos.

| StorageClass | Réplicas | Acceso | Usado por |
|---|---|---|---|
| `longhorn` (default) | 3 | RWO, RWX | Vault (data y audit), temas de Keycloak (RWX), ambos Valkey, GitLab, Harbor; Portal / App Hub / Drive (planificado) |
| `longhorn-processing` | 1 | RWO, RWX | Kafka (decisión 2026-10-23: Kafka ya replica 3×, una réplica de Longhorn evita 9 copias); directorios de trabajo de workflows |

> **IMPORTANTE:** `longhorn-processing` tiene reclaimPolicy **Delete**: los datos de Kafka solo están protegidos por `deleteClaim: false` en el node pool. **Nunca borrar a mano los PVC del namespace `kafka`.**

### 3.4 Red, DNS e Ingress (Fig. 5, Tabla 13)

**Camino de una petición (Fig. 5):** Usuario (navegador) → DNS (zona pública) → LBaaS (firewall, HTTPS 443, fuera del clúster) → Envoy (`contour-external`) → HTTPProxy (TLS, host → ruta) → Service (ClusterIP) → Pod. TLS termina en Envoy con certificados de cert-manager (Let's Encrypt).

- `contour-external` sirve todos los hosts públicos; `contour-internal` sirve las rutas cluster-local que Knative crea para las funciones de procesamiento. Ambos son Tier 1.
- Todo HTTPProxy lleva la anotación `projectcontour.io/ingress.class: contour-external`, `permitInsecure: false` y un Certificate del ClusterIssuer `letsencrypt-prod-contour` (HTTP-01).
- El Service de Envoy tipo LoadBalancer queda en `<pending>`: el balanceador se gestiona fuera del clúster. Argo CD está configurado para considerarlo Healthy (§5.2).
- **El puerto 80 debe ser alcanzable desde Internet** para el challenge HTTP-01 de cada certificado nuevo.

> **REGLA — DNS primero:** el nombre público de un servicio debe resolver al load balancer externo **antes** de ejecutar su paso; si no, el certificado no se emite. No suplir un registro DNS faltante con entradas de CoreDNS ni `/etc/hosts`: el kubelet de cada nodo resuelve nombres de registry con el DNS del nodo y necesita un certificado válido.

| Nombre (`.copernicuslac.aig.gob.pa`) | Servicio | DNS |
|---|---|---|
| `iam` | Keycloak | Published |
| `processing` | Processing API | Published |
| `discover` | STAC API (catálogo main) | Published |
| `git` | GitLab | Published |
| `cr` | Harbor | Published |
| `view` | TiTiler | Published |
| `dashboards` | Geobrowser | Published |
| `download` | download | **Pending** |
| `results`, `www`, `apps`, `hub`, `drive` | Results catalogs, Portal, App Hub, Drive | Published |

### 3.5 Servicios de datos gestionados (Fig. 6)

Datos relacionales y archivos masivos nunca se guardan en el clúster. Dos servicios gestionados externos, alcanzados por red privada.

**Fig. 6:** *Servicios con BD* (Keycloak, archivo de Argo Workflows, STAC API/pgSTAC, Portal, App Hub, GitLab, Drive) → *PostgreSQL endpoint* (una dirección, sigue al primary) → Primary (PostgreSQL 16 + PostGIS) ⇄ sync ⇄ Secondary (réplica síncrona) → Backups (repositorio del proveedor, 30 días). *Servicios con object storage* (Workflows: artifacts y resultados; TiTiler; Drive; GitLab; backups de Longhorn y etcd) → enlace 10 Gbps → *S3 endpoint* `svr-cop-s3-pan:10443` → StorageGRID (3 storage nodes, 2.75 PB, un bucket y una key por servicio). Longhorn solo guarda cachés, colas y estado local.

#### 3.5.1 PostgreSQL (Tablas 14 y 15)

| Aspecto | Valor |
|---|---|
| Servicio | PostgreSQL 16 con PostGIS 3.6.1, btree_gist, unaccent (disponibles en `template1`) |
| Topología | nodo01 `10.0.0.3` (primary) y nodo02 `10.0.0.4` (réplica). Hoy los servicios se conectan a la dirección del primary |
| Red cliente | Los pods llegan desde `192.168.80.0/24` (direcciones de los nodos) |
| Administración | pgAdmin con la cuenta DBA (CREATEDB, CREATEROLE — **no superuser**). El equipo DBaaS (contacto: IFX) es dueño de `postgresql.conf`, reinicios y backups |
| `max_connections` | 500 en ambos nodos (la réplica debe ser ≥ el primary) |
| `shared_buffers` / `effective_cache_size` | 8 GB en ambos nodos (~13 % de 62 GB RAM, subido el 2026-10-26) / 16 GB en nodo01, 8 GB en nodo02 (por alinear, TBC-2) |

| Servicio | Base de datos / rol | Connection limit (rol) | Credenciales |
|---|---|---|---|
| GitLab | `gitlabhq_production` / `gitlab` (+ BD `postgres` en pg_hba) | — | SOPS `gitlab-postgres` |
| Harbor | `registry` / `harbor` | — | SOPS `harbor-postgres` |
| Keycloak | `keycloak` / `keycloak` | 30 | Vault `secrets/iam/keycloak-external-db` |
| Archivo de Argo Workflows | `argowf` / `argowf` | 25 | Vault `secrets/processing/argo-postgres` |
| STAC API (+ TiTiler) | `pgstac` / `pgstac` (pgSTAC 0.9.12) | 50 | Vault `secrets/catalog/pgstac` |
| Portal, App Hub, Drive, results catalogs | por crear | — | — |

**Procedimiento para una BD nueva (igual para todo servicio):**

1. Generar la contraseña en la workstation y escribirla **primero en su destino** (Vault para Tier 3, archivo SOPS para Tiers 1–2), para no teclearla dos veces:
   ```bash
   P=$(openssl rand -base64 24 | tr -d '/+=')
   vault kv put secrets/<component>/<name> username=<role> password="$P"
   printf '%s' "$P" | pbcopy; unset P
   ```
2. En pgAdmin, sobre la BD `postgres`, **sin nada seleccionado en el editor** (pgAdmin ejecuta solo la selección) y **una sentencia a la vez** (CREATE/DROP DATABASE no puede correr dentro de la transacción que pgAdmin abre para un bloque):
   ```sql
   CREATE ROLE <role> LOGIN PASSWORD '<paste>' CONNECTION LIMIT <n>;
   CREATE DATABASE <db> OWNER <role>;
   REVOKE ALL ON DATABASE <db> FROM PUBLIC;
   ```
   Después, limpiar la contraseña del editor y del portapapeles.
3. Añadir en `pg_hba.conf` **en ambos nodos** (el archivo no se replica) y recargar:
   ```
   host <db> <role> 192.168.80.0/24 scram-sha-256
   ```
   ```bash
   sudo -u postgres psql -c 'SELECT pg_reload_conf();'
   ```
4. Verificar en cada nodo (la columna `error` debe estar vacía):
   ```sql
   SELECT line_number, error FROM pg_hba_file_rules WHERE '<db>' = ANY(database);
   ```

> **IMPORTANTE — Presupuesto de conexiones:** la suma de los pools máximos de todos los servicios (todas las réplicas) debe quedar por debajo de `max_connections`. Uso actual:
> `SELECT count(*), current_setting('max_connections') FROM pg_stat_activity;`
> Comprobar que hubo reinicio (debe dar `pending_restart = false` en ambos nodos):
> `SELECT name, setting, pending_restart FROM pg_settings WHERE name IN ('max_connections','shared_buffers');`

Pools conocidos: Keycloak 10 por réplica × 2; Harbor maxIdle 10 / maxOpen 50; STAC API 4 workers × 10 = 40; Argo Workflows 2 idle / 10 open; TiTiler (planificado) 2 × 2 = 4.

#### 3.5.2 Object storage (Tablas 16 y 17)

| Aspecto | Valor |
|---|---|
| Servicio | StorageGRID privado, API S3, gestionado fuera del clúster |
| Endpoint | `https://svr-cop-s3-pan.ifxcloud.com:10443` — URLs de bucket **path-style** (sin virtual hosting) |
| Modelo de acceso | Un usuario de tenant por servicio, en un grupo cuya política S3 se limita a los buckets de ese servicio; una access key por usuario, guardada en SOPS (Tiers 1–2) o Vault (Tier 3) |

| Bucket(s) | Usado por | Política en el repo |
|---|---|---|
| `copernicuslac-gitlab-{lfs, artifacts, uploads, packages, mr-diffs, ci-secure-files, dependency-proxy, registry, backups, tmp}` | GitLab (versionado solo en `-backups`, expiración de versiones antiguas a 30 días) | `bootstrap/gitlab/storagegrid-policy.json` |
| `copernicuslac-harbor-registry` | Almacenamiento del registry de Harbor | `bootstrap/harbor/storagegrid-policy.json` |
| `copernicuslac-argo-artifacts` | Artifacts y logs de Argo Workflows (grupo/usuario `argowf`) | `ops/storagegrid/argowf-group-policy.json` |
| por crear | TiTiler (solo lectura sobre buckets de resultados), Drive, results | — |

**Crear un usuario de servicio:** Tenant Manager → Groups → crear grupo local sin permisos de tenant-management y con la política S3 custom del repo; Users → crear el usuario en ese grupo con "Deny access to Tenant Manager"; crear una access key y escribirla directamente en SOPS o Vault (nunca en chat ni ticket).

> **IMPORTANTE — Issue conocido de StorageGRID 12.0.0 a 12.0.0.4** (NetApp KB: *"StorageGRID returns incorrect 403 responses instead of 404 for HEAD/GET requests on non-existent objects"*). Un HEAD o GET sobre una key inexistente devuelve **403 AccessDenied en vez de 404**, aunque el usuario tenga `s3:ListBucket`. Panamá corre 12.0.0; el upgrade está solicitado a IFX (**TBC-1**).
> **Efecto en Harbor:** el registry depende del 404 para detectar un objeto faltante; hacer push de una imagen que comparte capas con una imagen ya existente en otro repositorio falla con HTTP 500 (log del registry: `s3aws: AccessDenied`). Paquetes, charts e imágenes con capas nuevas **no** se ven afectados.
> **Verificación tras el upgrade:** `s3cmd info s3://copernicuslac-harbor-registry/docker/does-not-exist` debe responder 404; luego re-ejecutar `./bootstrap.sh harbor-seed`.

### 3.6 Otras dependencias externas (Tabla 18)

| Dependencia | Usada por | Si no está disponible |
|---|---|---|
| CDSE | Datos de entrada del procesamiento | Las ejecuciones nuevas fallan en stage-in |
| Let's Encrypt (ACME v2) | Todos los certificados públicos (HTTP-01) | Fallan las renovaciones; los certificados expiran a los 90 días |
| Repos de charts y registries públicos (argoproj.github.io, charts.jetstack.io, charts.gitlab.io, helm.goharbor.io, charts.crossplane.io, codecentric, knative.github.io, quay.io, ghcr.io, docker.io, xpkg.upbound.io, github.com) | Instalaciones y upgrades | Lo que corre no se afecta; las instalaciones fallan |
| `cr.terradue.com` (**TEMPORARY**) | Imágenes de las funciones del processing API hasta copiarlas a Harbor (§12.3) | Los pods nuevos de las funciones no pueden bajar sus imágenes |

### 3.7 Acceso y herramientas (Tabla 19)

La API de Kubernetes solo es alcanzable vía Rancher desde máquinas autorizadas. Cada operador usa un kubeconfig personal (acciones atribuibles).

| Herramienta | Versión | Uso |
|---|---|---|
| kubectl | 1.32–1.34 (skew con el server 1.33) | Inspección, bootstrap, recuperación |
| helm + plugin helm-diff | ≥ 3.14 | Inspección de charts, `helmfile diff` |
| helmfile | v1 | Argo CD (Tier 1) y Crossplane (Tier 2) |
| argocd CLI | mismo minor que el server (3.5) | Diff y sync de Applications Tier 1; `argocd --core` necesita el namespace del contexto en `argocd` |
| sops + age | actual | Secretos Tier 1–2 |
| vault CLI | 2.x | Escribir secretos Tier 3 por port-forward |
| skopeo, oras | actual | Harbor seed: imágenes y paquetes Crossplane (skopeo), charts (oras) |
| yq, jq, curl, openssl | actual | Scripts y checks |
| pgAdmin | actual | BD en el PostgreSQL gestionado |

---

## 4. Paquete de entrega y repositorio (§4)

### 4.1 Principios
- **Git es la única vía de escritura.** `main` de `infra-copernicuslac-panama` es el estado deseado. Tier 3 solo por merge request; Tiers 1–2 por merge request y luego aplicado por un operador con el paso documentado.
- **Todo es reproducible desde el paquete.** Repo + guía reconstruyen la plataforma; los únicos insumos externos son los valores secretos (claves age, claves de Vault, contraseñas), los servicios gestionados y el DNS.
- **Versiones fijadas** (charts, tags de imagen, revisiones Git, tags de paquetes).
- **Los secretos nunca entran en claro a Git.**
- **Pull, no push.** Argo CD lee el repo desde el GitLab in-cluster; nada externo empuja al clúster.

**Los dos lazos de control de Tier 3 (Tabla 20)**

| | Lazo 1 — Argo CD | Lazo 2 — Crossplane |
|---|---|---|
| Compara | Git ↔ Releases y Objects en namespace `platform` | spec de Release/Object ↔ release Helm y objetos |
| Disparado por | Poll del repositorio (3 minutos) | Eventos watch y poll periódico (~10 minutos para provider-helm) |
| Ante drift | `selfHeal` re-aplica; `prune` borra lo que salió de Git | Re-aplica el manifiesto; ejecuta `helm upgrade` |
| Reporta | Sync status y Health de la Application de cada capa | Condiciones `Synced` y `Ready` |

### 4.2 El paquete de entrega (Tablas 21 y 22)

El equipo de operaciones recibe un zip del repo `infra-copernicuslac-panama`.

| Ítem | Contenido |
|---|---|
| `bootstrap/` | Tiers 1–2: `bootstrap.sh`, `helmfile.yaml.gotmpl`, values y Applications de cada componente Tier 1, manifiestos de exposición, charts de Crossplane, secretos SOPS y sus plantillas, SQL y políticas S3 de GitLab y Harbor, `harbor/seed.yaml` |
| `apps/` | Una Application de Argo CD por capa de Tier 3 |
| `platform/` | Releases y Objects de Tier 3: una carpeta por capa y una subcarpeta por componente, cada una con README |
| `ops/` | Scripts y referencias operativas: Vault init/unseal/configure, export del realm de Keycloak, políticas de StorageGRID, tests de seguridad |
| `docs/` | Notas de despliegue (decisiones e incidencias), fuente de esta guía |
| `.sops.yaml` | Reglas SOPS: qué archivos se cifran (`path_regex \.sops\.yaml$`), qué campos (`encrypted_regex ^(data|stringData)$`), claves age públicas |

**Entregado aparte (nunca en el zip, nunca en Git):**

| Ítem | Cómo se entrega |
|---|---|
| Claves privadas age (`.sops/age.key`, `keys.txt`) y la clave de disaster recovery del equipo | Gestor de contraseñas del equipo, fuera de banda |
| Unseal keys de Vault (5) y root token (`ops/vault/vault-init.sops.yaml`, git-ignored) | Gestor de contraseñas; el archivo se borra de la workstation tras guardarlo |
| `.envrc` (entorno local) | Cada operador crea el suyo |
| `bootstrap/harbor/archives/` (copias locales git-ignored de paquetes y charts para el Harbor seed) | Se recrea con los comandos documentados en `harbor/seed.yaml`, o se entrega como archivo aparte |
| Contraseñas de los servicios gestionados (cuenta DBA, tenant de StorageGRID) | Proveedor / gestor de contraseñas |

> **IMPORTANTE — antes de crear el zip:** `grep -L 'ENC\[' bootstrap/secrets/*.sops.yaml` no debe imprimir nada, y `git status --ignored` debe mostrar `.sops/`, `.envrc` y `harbor/archives/` como ignorados.

### 4.3 Estructura del repositorio

```
infra-copernicuslac-panama/
├── README.md                    # tiers, punto de entrada
├── .sops.yaml                   # reglas SOPS + claves age públicas
├── bootstrap/                   # Tiers 1–2 — aplicado por el operador, nunca leído por Argo CD
│   ├── bootstrap.sh             # todos los pasos, idempotente (§5.1)
│   ├── helmfile.yaml.gotmpl     # Argo CD (tier=1), Crossplane + packages + configs (tier=2)
│   ├── argocd/values.yaml       # health checks para Crossplane, override de Service, nodeSelector
│   ├── cert-manager/application.yaml
│   ├── contour/application.yaml # net-contour config/contour @ knative-v1.20.1
│   ├── valkey/application.yaml  # Valkey para GitLab (valkey-helm @ commit)
│   ├── gitlab/                  # application.yaml, database.sql, storagegrid-policy.json
│   ├── harbor/                  # application, valkey, database.sql, storagegrid-policy,
│   │                            # seed.yaml, archives/ (git-ignored)
│   ├── exposure/                # cluster-issuer, gitlab, harbor (Certificate + HTTPProxy)
│   ├── crossplane/values.yaml
│   ├── crossplane-packages/     # chart local: Providers, DeploymentRuntimeConfig, RBAC
│   ├── crossplane-providerconfigs/
│   ├── root-app.yaml            # punto de entrada de Tier 3
│   └── secrets/                 # *.sops.yaml, templates/, gen-harbor-secrets.sh, README
├── apps/                        # 10-core … 70-application-packages (una Application cada una)
├── platform/                    # Tier 3 — Releases y Objects, namespace platform
│   ├── _template/               # convenciones + componente de ejemplo (nunca se sincroniza)
│   ├── 10-core/                 # vault/, external-secrets/
│   ├── 20-identity/             # keycloak/, opa/
│   ├── 30-serving/              # knative-operator/, knative-serving/
│   ├── 40-data/                 # kafka/, kafka-ui/, stac-api/, titiler-pgstac/, stac-browser/
│   ├── 50-processing/           # namespaces, argo-workflows, argo-events, event-bus, mate-api
│   ├── 60-user-services/
│   └── 70-application-packages/
├── ops/
│   ├── vault/                   # init.sh, unseal.sh, configure.sh, lib.sh, README.md
│   ├── keycloak/                # CopernicusLAC-Platform-realm.json (export parcial)
│   ├── storagegrid/             # argowf-group-policy.json
│   └── tests/                   # opa-negative-tests.sh
└── docs/deployment-notes.md
```

- Un recurso por archivo en `platform/`; el nombre del archivo es el nombre del recurso.
- `bootstrap/` nunca lo lee Argo CD desde Git: la root Application apunta solo a `apps/`.
- Quitar un archivo de `platform/` borra el recurso (prune), **excepto** los anotados `Prune=false` (los que guardan datos: Vault, Kafka, KnativeServing, releases de Argo).
- Archivos terminados en `.disabled` quedan en Git pero no se sincronizan (Argo CD solo lee `.yaml/.yml/.json`): se usan para configuración preparada pero inactiva (SSO de Argo Workflows).
- Cada carpeta de componente tiene un README con prerequisitos (BD, rutas de Vault, DNS) y checks.

### 4.4 Modelo de secretos (Tablas 23 y 24)

| Secretos de | Viven en | Aplicados por |
|---|---|---|
| Tiers 1–2 (Argo CD, Valkey, GitLab, Harbor, Crossplane) | `bootstrap/secrets/*.sops.yaml`, cifrados con SOPS + age | `./bootstrap.sh secrets` (`sops -d | kubectl apply`) |
| Tier 3 (todo en `platform/`) | Vault KV v2, mount `secrets/` | External Secrets Operator, vía ClusterSecretStore `vault-backend`; solo namespaces con label `eso=enabled` |

Los secretos de Tier 1–2 no pueden venir de Vault (es Tier 3; no existe cuando se necesitan, tampoco en DR). Cada operador tiene una clave age; el equipo tiene además una clave de disaster recovery cuya parte privada vive solo en el gestor de contraseñas. Cada archivo se cifra para todas las claves públicas listadas en `.sops.yaml`.

```bash
# una vez, por operador (ruta macOS; Linux: ~/.config/sops/age/keys.txt)
age-keygen -y "$HOME/Library/Application Support/sops/age/keys.txt"   # → añadir a .sops.yaml
sops updatekeys bootstrap/secrets/*.sops.yaml        # tras un cambio de .sops.yaml

# crear un secreto desde su plantilla
cp bootstrap/secrets/templates/gitlab-postgres.yaml bootstrap/secrets/gitlab-postgres.sops.yaml
$EDITOR bootstrap/secrets/gitlab-postgres.sops.yaml      # reemplazar cada CHANGE-ME
sops --encrypt --in-place bootstrap/secrets/gitlab-postgres.sops.yaml

# cambiar un campo de un archivo cifrado (editar el texto cifrado a mano rompe el MAC)
sops set bootstrap/secrets/helm-repo-harbor.sops.yaml \
  '["metadata"]["namespace"]' '"platform"'

# check antes de cada commit: no debe imprimir nada
grep -L 'ENC\[' bootstrap/secrets/*.sops.yaml
```

**Inventario de secretos Tier 1–2**

| Archivo | Namespace / Secret | Contenido |
|---|---|---|
| `gitlab-postgres` | gitlab-system / `gitlab-postgres` | contraseña del rol `gitlab` |
| `gitlab-initial-root-password` | gitlab-system | primer login de root |
| `gitlab-object-storage`, `-plain`, `gitlab-registry-storage` | gitlab-system | key StorageGRID del usuario `gitlab` (Rails, backups, registry) |
| `gitlab-valkey-users` | gitlab-system | contraseñas ACL de Valkey (`default`, `replicator`) y de Sentinel |
| `gitlab-keycloak` | gitlab-system | proveedor OIDC de GitLab (client `gitlab`, realm `CopernicusLAC-Platform`) |
| `gitlab-rails-secret` | gitlab-system / `copernicuslac-gitlab-rails-secret` | generado por GitLab, exportado tras la primera instalación (§5.4) — **sin él, restaurar la BD es inútil** |
| `argocd-repo-infra` | argocd | deploy token de GitLab (`read_repository`) de este repo |
| `harbor-internal`, `harbor-token-service`, `harbor-valkey-sentinel` | harbor-system | generados por `secrets/gen-harbor-secrets.sh` (contraseña admin, secretos internos, clave PKCS#1 del token-service) |
| `harbor-postgres`, `harbor-registry-storage` | harbor-system | contraseña del rol `harbor`, key StorageGRID del usuario `harbor` |
| `harbor-crossplane-pull` | crossplane-system | `robot$crossplane+pull` (robot de proyecto, solo pull, proyecto `crossplane`) — lo escribe `./bootstrap.sh harbor-robots` |
| `helm-repo-harbor` | platform | `robot$helm-pull` (solo pull, proyectos de charts `opa-authz`, `strimzi-kafka`, `mate`, `seda`, `stac-utils`): el `pullSecretRef` de las Releases — lo escribe `./bootstrap.sh harbor-robots` |
| `harbor-oidc` | harbor-system | client secret del client Keycloak `harbor`, leído por `./bootstrap.sh harbor-oidc` |

> **REGLA:** nunca hacer commit de un archivo de `templates/` con valores reales ni de un `*.sops.yaml` sin cifrar. Nunca poner secretos de Tier 3 en `bootstrap/secrets/`. Nunca pegar un secreto en chat, ticket o línea de comandos: un valor así expuesto se rota de inmediato.

### 4.5 Secuencia de extremo a extremo (Tabla 25)

De clúster vacío a totalmente entregado; el mismo orden se usa en disaster recovery. Cada paso depende solo de los anteriores y es idempotente.

| # | Paso | Cómo | § | Hecho cuando |
|---|---|---|---|---|
| 1 | Clúster, node pools, label static, Longhorn, Monitoring | Rancher; `kubectl label` | 3.2 | Nodos Ready, label puesto |
| 2 | Prerequisitos externos: BD, pg_hba, buckets, usuarios, DNS de `git.` y `cr.` | pgAdmin, StorageGRID, DNS | 3.5 | Checks de §3.5 |
| 3 | Namespaces y secretos SOPS | `./bootstrap.sh namespaces` · `secrets` | 5.1 | Secrets presentes |
| 4 | Argo CD | `./bootstrap.sh argocd` | 5.2 | `argocd-server` Running |
| 5 | cert-manager, Contour | `./bootstrap.sh cert-manager` · `contour` | 5.3 | Applications Synced/Healthy |
| 6 | Valkey y GitLab | `./bootstrap.sh valkey` · `gitlab` | 5.4 | Login en GitLab; rails secret exportado |
| 7 | Repositorio en GitLab; deploy token | `git push`; SOPS `argocd-repo-infra` | 5.4 | Repo legible desde el clúster |
| 8 | Valkey para Harbor y Harbor | `./bootstrap.sh harbor-valkey` · `harbor` | 5.5 | La API de Harbor responde |
| 9 | Exposición de GitLab y Harbor | `./bootstrap.sh exposure` | 5.6 | Certificates Ready, HTTPS responde |
| 10 | Harbor seed y robot accounts | `./bootstrap.sh harbor-seed` · `harbor-robots` | 5.7 | Artefactos en Harbor, anotaciones xpkg presentes; secretos de robots en SOPS |
| 11 | Crossplane (Tier 2) | `./bootstrap.sh crossplane` | 5.8 | Providers Installed/Healthy |
| 12 | Root Application de Tier 3 | `./bootstrap.sh root-app` | 6.1 | Applications de capa creadas |
| 13 | Capa 10: Vault init, unseal, configure | `ops/vault/*.sh` | 7.1 | `vault-backend` Ready |
| 14 | Capas 20–70, cada una con sus prerequisitos | Secretos en Vault, BD, clients de Keycloak, luego Git; tras la capa 20: `./bootstrap.sh harbor-oidc` | 7–10 | Cada capa Synced/Healthy |

> **TODAY:** en Panamá está hecho todo hasta la capa 50 (Tier 1 publicado el 26-oct-2026). Las imágenes de las funciones del processing API aún se bajan de `cr.terradue.com`: copiarlas a Harbor está bloqueado por el issue de StorageGRID (TBC-1).

---

## 5. Tiers 1 y 2 — Bootstrap (§5)

Todo lo de este capítulo lo aplica el operador desde `bootstrap/`; nunca se sincroniza automáticamente desde Git. Prerequisitos en la workstation: herramientas de §3.7, contexto `copernicuslac-panama`, una clave age capaz de descifrar `bootstrap/secrets/`, y acceso de red del clúster a los repos públicos de charts (§3.6).

### 5.1 `bootstrap.sh` (Tabla 26)

`bootstrap/bootstrap.sh` envuelve toda operación de Tier 1–2. Cada paso comprueba sus prerequisitos (secretos, salud del paso previo), es idempotente y re-ejecutable. Como las Applications de Tier 1 no tienen sync automático, el script lanza el sync y espera a Synced + Healthy.

| Paso | Qué hace | Requiere |
|---|---|---|
| `namespaces` | Crea `argocd`, `gitlab-system`, `harbor-system`, `crossplane-system`, `platform` | — |
| `secrets` | Descifra y aplica cada `secrets/*.sops.yaml` | sops, clave age |
| `argocd` | `helmfile -l name=argocd apply`; espera a `argocd-server` | secrets |
| `cert-manager` | Aplica la Application, sincroniza, espera Healthy (adopta una instalación existente con los mismos nombres) | argocd |
| `contour` | Igual para `contour-external` y `contour-internal` | argocd |
| `valkey` | Valkey para GitLab; espera Healthy | secret `gitlab-valkey-users` |
| `gitlab` | Application de GitLab y primer sync (15–25 min) | Valkey Healthy, secretos de GitLab |
| `harbor-valkey` | Valkey para Harbor; espera Healthy | secret `harbor-valkey-sentinel` |
| `harbor` | Application de Harbor y primer sync (5–10 min) | Valkey de Harbor Healthy, secretos de Harbor |
| `exposure` | ClusterIssuer, Certificates y HTTPProxies de `git.` y `cr.`; espera los certificados | cert-manager y Contour Healthy; DNS |
| `harbor-seed` | Copia los artefactos de `harbor/seed.yaml` a Harbor | Harbor; skopeo, oras, yq, curl |
| `harbor-robots` | Crea los robots de solo lectura `robot$crossplane+pull` y `robot$helm-pull` y escribe sus secretos directo en los archivos SOPS (se muestran una sola vez); los robots existentes se conservan, `ROTATE=1` los regenera | Harbor publicado; sops, yq, curl |
| `harbor-oidc` | Login de Harbor por Keycloak: escribe la configuración OIDC (client `harbor`, claim `groups`, grupo admin `admin`) por la API de Harbor; el admin local queda como cuenta *break-glass* | Harbor publicado; Keycloak (capa 20); `secrets/harbor-oidc.sops.yaml` |
| `crossplane` | `helmfile -l tier=2 apply` (Crossplane, packages, ProviderConfigs) | pull secrets de los paquetes |
| `root-app` | Aplica `bootstrap/root-app.yaml` (Tier 3) | providers Healthy, secret `argocd-repo-infra` |
| `status` | Imprime el estado de cada componente Tier 1–2 | — |
| `all` | namespaces → secrets → argocd → cert-manager → contour → valkey → gitlab → harbor-valkey → harbor | — |

```bash
cd bootstrap
./bootstrap.sh namespaces && ./bootstrap.sh secrets
./bootstrap.sh argocd
./bootstrap.sh cert-manager && ./bootstrap.sh contour
./bootstrap.sh valkey && ./bootstrap.sh gitlab
./bootstrap.sh harbor-valkey && ./bootstrap.sh harbor
./bootstrap.sh exposure        # necesita DNS de git. y cr.
./bootstrap.sh harbor-seed
./bootstrap.sh harbor-robots   # hacer commit de los secrets/*.sops.yaml cambiados
./bootstrap.sh crossplane
./bootstrap.sh root-app
./bootstrap.sh harbor-oidc     # cuando Keycloak (capa 20) esté arriba
./bootstrap.sh status
```

### 5.2 Argo CD (Tablas 27 y 28)

| Aspecto | Valor |
|---|---|
| Release | `argocd` — chart `argo/argo-cd` 10.10.5 (Argo CD v3.5.5), helmfile (`bootstrap/helmfile.yaml.gotmpl`, label `tier=1`) |
| Namespace | `argocd`, todo en el pool static (`global.nodeSelector`) |
| Acceso | **No expuesto.** `kubectl -n argocd port-forward svc/argocd-server 8080:80`; contraseña inicial en el Secret `argocd-initial-admin-secret` (rotarla y luego borrar el Secret) |
| Repositorio | `http://copernicuslac-gitlab-webservice-default.gitlab-system.svc:8181/copernicuslac/infra-copernicuslac-panama.git` (GitLab in-cluster), credenciales en el Secret `argocd-repo-infra` (deploy token, SOPS) |
| Cambios | `helmfile -l name=argocd diff`, luego `apply` |

`bootstrap/argocd/values.yaml` añade los health checks que hacen que Argo CD entienda la plataforma:

| Ajuste | Por qué |
|---|---|
| Health de `Release`, `Object`, `ApplicationPackage` (Lua) | Healthy solo cuando Crossplane reporta `Synced=True` y `Ready=True`; Degraded con `Synced=False`. Sin esto, una Release es Healthy apenas existe, aunque Helm haya fallado |
| Health de `argoproj.io/Application` (Lua) | La root Application espera a que cada Application de capa esté Healthy antes de la siguiente sync wave |
| Health de `Service` | El load balancer es externo: los Services tipo LoadBalancer quedan `<pending>` y dejarían a Contour en Progressing para siempre. Un Service es Healthy en cuanto existe |
| `global.nodeSelector aig/node-pool: static` | Ubicación de plataforma |

> **NOTA:** el CLI en modo core (`argocd --core app get …`) habla directo con el API server y necesita que el namespace del contexto sea `argocd`:
> `kubectl config set-context --current --namespace argocd`

### 5.3 cert-manager y Contour (Tabla 29)

| Aspecto | cert-manager | Contour |
|---|---|---|
| Application | `bootstrap/cert-manager/application.yaml` | `bootstrap/contour/application.yaml` |
| Fuente | chart `jetstack/cert-manager` v1.21.0, values inline | `github.com/knative-extensions/net-contour`, path `config/contour`, targetRevision `knative-v1.20.1` (Contour 1.33.1, Envoy 1.35.8), archivos `external.yaml` e `internal.yaml` |
| Ajustes | CRDs instalados y conservados; `startupapicheck` off; controller, webhook, cainjector en el pool static | ServerSideApply; `ignoreDifferences` sobre CRD `/spec/preserveUnknownFields`; dos instalaciones `contour-external` y `contour-internal`; DaemonSet de Envoy en todos los workers |
| Upgrade | Cambiar `targetRevision`, diff, sync; leer las release notes | Junto con Knative Serving (mismo minor): `targetRevision` aquí, luego Knative Operator y KnativeServing (§7.7) |

> **NOTA:** Argo CD reporta `RepeatedResourceWarning` en la Application de Contour (los CRDs y un ClusterRole están en ambos archivos). Es esperado e inofensivo.

### 5.4 Valkey y GitLab (Tablas 30 y 31)

**Valkey para GitLab**

| Aspecto | Valor |
|---|---|
| Fuente | `github.com/valkey-io/valkey-helm` en el commit `e840544` (Valkey 9.1.2): 3 nodos Valkey, 3 Sentinels, 3 HAProxy |
| Seguridad | Usuarios ACL `default` (GitLab) y `replicator`, contraseña de Sentinel — Secret `gitlab-valkey-users` (SOPS) |
| Disponibilidad | PodDisruptionBudget; `preStop` pide a Sentinel un failover coordinado antes de detener un master |
| Check | `valkey-cli -h gitlab-valkey-haproxy --user default --pass "$PW" info replication` → `role:master`, `connected_slaves:2` |

**GitLab**

| Aspecto | Valor |
|---|---|
| Fuente | chart `gitlab/gitlab` 9.11.13 (GitLab 18.11.12), Application desde el repo Helm público, values inline |
| Por qué no 19.x | GitLab 19 (chart 10.x) requiere PostgreSQL 17; el servicio gestionado es PostgreSQL 16. Camino: PostgreSQL 17 por el proveedor → upgrade 18.11 → 19.x siguiendo el upgrade path de GitLab, tras un backup |
| Base de datos | `gitlabhq_production` en el PostgreSQL gestionado (`bootstrap/gitlab/database.sql`); pg_hba debe permitir también la BD `postgres` (checks de GitLab) |
| Object storage | Buckets `copernicuslac-gitlab-*` |
| Redis | El Valkey anterior (sin Redis embebido) |
| Identidad | Keycloak OIDC (Secret `gitlab-keycloak`, client `gitlab`, realm `CopernicusLAC-Platform`) |
| Hostnames | `git.copernicuslac.aig.gob.pa` (publicado), `registry.copernicuslac.aig.gob.pa` (registry habilitado, **no expuesto**: sin Certificate/HTTPProxy aún) |
| Diff conocido | `ignoreDifferences` sobre `volumeClaimTemplates` del StatefulSet de Gitaly (apiVersion, kind, status); si no, OutOfSync para siempre |

**Tras la primera instalación:**

1. **Exportar el Rails secret** (cifra variables de CI, semillas 2FA y tokens; sin él, restaurar la BD es inútil):
   ```bash
   kubectl -n gitlab-system get secret copernicuslac-gitlab-rails-secret -o yaml \
     | yq 'del(.metadata.uid, .metadata.resourceVersion, .metadata.creationTimestamp,
               .metadata.managedFields, .metadata.annotations, .metadata.labels,
               .metadata.ownerReferences)' > secrets/gitlab-rails-secret.sops.yaml
   sops --encrypt --in-place secrets/gitlab-rails-secret.sops.yaml
   # y commit
   ```
2. Login por port-forward: `kubectl -n gitlab-system port-forward svc/copernicuslac-gitlab-webservice-default 8181:8181` (`http://localhost:8181`, usuario `root`, contraseña inicial de SOPS). Hasta publicar `git.`, el login por navegador puede fallar por las cookies Secure sobre HTTP plano: usar la API o HTTPS.
3. Crear el grupo `copernicuslac` y el proyecto privado `infra-copernicuslac-panama`, hacer push del repo, crear un deploy token con `read_repository` y guardarlo como `secrets/argocd-repo-infra.sops.yaml`.
4. Tras `./bootstrap.sh exposure`, entrar con el botón **CopernicusLAC** (Keycloak). Los usuarios se crean en Keycloak con un **username corto, no el e-mail**: GitLab enlaza la cuenta por `preferred_username`. El primer login crea el usuario de GitLab **bloqueado** (`blockAutoCreatedUsers`): aprobarlo en *Admin → Users → Pending approval*. Un segundo login antes de la aprobación falla con 422 "Email has already been taken".
5. **Acceso Git para operadores:** miembro del grupo `copernicuslac` (Developer para abrir merge requests, Maintainer para mergear al `main` protegido) y un *personal access token* (scope `write_repository`) usado como contraseña Git sobre HTTPS, remote `https://git.copernicuslac.aig.gob.pa/copernicuslac/infra-copernicuslac-panama.git`. SSH no está expuesto; el port-forward del paso 2 es solo para bootstrap y disaster recovery.

**Cambiar GitLab:** merge request sobre `gitlab/application.yaml`; backup con toolbox antes de un upgrade; aplicar; diff; sync; rollback si hace falta (funciona con GitLab caído):
```bash
kubectl -n gitlab-system exec deploy/copernicuslac-gitlab-toolbox -- backup-utility
kubectl apply -f gitlab/application.yaml
argocd app diff gitlab
argocd app sync gitlab
argocd app rollback gitlab     # si es necesario
```

### 5.5 Harbor (Tabla 32)

| Aspecto | Valor |
|---|---|
| Fuente | chart `harbor/harbor` 1.19.4 (Harbor 2.15.4), Application desde helm.goharbor.io, values inline |
| URL externa | `https://cr.copernicuslac.aig.gob.pa` (`registry.` pertenece a GitLab) |
| Base de datos | `registry` en el PostgreSQL gestionado (`bootstrap/harbor/database.sql`); pool maxIdle 10 / maxOpen 50 |
| Almacenamiento | Bucket `copernicuslac-harbor-registry`, path-style |
| Redis | Valkey dedicado `harbor-valkey` (`bootstrap/harbor/valkey.yaml`), **sin contraseña de datos** (ver nota) |
| Secretos | Todos los valores generados como Secrets existentes: `harbor-internal`, `harbor-token-service` (clave PKCS#1), `harbor-postgres`, `harbor-registry-storage` (`secrets/gen-harbor-secrets.sh` + plantillas) |
| Identidad | Keycloak OIDC (client `harbor`, confidential, redirect `https://cr.copernicuslac.aig.gob.pa/c/oidc/callback`, client scope `groups` con full path off, grupo admin `admin`, user claim `preferred_username`, auto-onboard), guardado en la BD de Harbor y escrito por `./bootstrap.sh harbor-oidc`; admin local como break-glass |
| Robot accounts | `robot$crossplane+pull` (robot de proyecto, proyecto `crossplane`: aparece en *Projects → crossplane → Robot Accounts*, no en Administration) y `robot$helm-pull` (robot de sistema, proyectos de charts), ambos solo pull, creados por `./bootstrap.sh harbor-robots` |
| Ubicación | Todos los componentes en el pool static |

> **NOTA — Por qué todo secreto de Harbor es un Secret existente y Valkey no tiene contraseña:** Argo CD renderiza charts sin `lookup` de Helm: los valores generados por el chart cambiarían en cada render, y el chart escribe la contraseña de Redis en ConfigMaps. Por eso el endpoint de datos de Valkey es alcanzable sin contraseña desde los pods del clúster (sin NetworkPolicy, decisión del equipo de plataforma).
> **Clave del token-service en PKCS#1:** OpenSSL 3 genera PKCS#8 por defecto y Harbor responde 500 a toda petición de token; `gen-harbor-secrets.sh` usa `openssl rsa -traditional`.

> **DONE WHEN:** `argocd app get harbor-valkey` y `argocd app get harbor` → Synced / Healthy; la API responde en `kubectl -n harbor-system port-forward svc/harbor 8282:80` con la contraseña admin de SOPS. Los pushes de imágenes se validan solo por HTTPS, tras el paso de exposición.

### 5.6 Exposición de los servicios Tier 1

`bootstrap/exposure/` contiene el ClusterIssuer `letsencrypt-prod-contour` (Let's Encrypt, HTTP-01 vía contour-external, Secret de la clave de cuenta `issuer-account-key-copernicuslac`) y, para `git.` y `cr.`, un Certificate (ECDSA P-256, clave rotada en cada renovación) y un HTTPProxy. **Argo CD deliberadamente no está en esta carpeta.**

```yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: harbor
  namespace: harbor-system
  annotations:
    projectcontour.io/ingress.class: contour-external
spec:
  virtualhost:
    fqdn: cr.copernicuslac.aig.gob.pa
    tls: {secretName: harbor-tls}
  routes:
    - conditions: [{prefix: /}]
      permitInsecure: false
      services: [{name: harbor, port: 80}]
      timeoutPolicy: {response: infinity, idle: 5m}     # capas de imagen grandes
```

Ejecutar `./bootstrap.sh exposure` cuando existan los registros DNS; el paso espera los certificados. Verificar con `kubectl get certificate -A` (READY True) y `curl -sI https://cr.copernicuslac.aig.gob.pa`.

### 5.7 Harbor seed (Tabla 33)

Harbor debe contener los paquetes Crossplane, charts e imágenes que la plataforma descarga. `bootstrap/harbor/seed.yaml` los lista; `./bootstrap.sh harbor-seed` crea los proyectos privados que falten y copia cada artefacto faltante (los existentes se saltan).

| Tipo | Proyecto Harbor | Artefactos |
|---|---|---|
| Paquetes Crossplane | `crossplane` | `provider-helm-terradue:v1.0.0` (copia local `dir:`), `provider-kubernetes:v1.4.1` (xpkg.upbound.io) |
| Charts (OCI) | `opa-authz` | `opa` 0.2.5 |
| | `strimzi-kafka` | `kafka-ui` 1.4.2 |
| | `mate` | `mate-api` 1.2.2 |
| | `seda` | `kafka-event-bus` 0.1.0, `cloud-event-webhook` 0.3.0 |
| | `stac-utils` | `stac-fastapi-pgstac` 2.0.7 |
| Por añadir | `mate`, `stac-utils`, `glowstac` | Imágenes de funciones mate 1.2.0 (listadas; copia bloqueada por el issue de StorageGRID, TBC-1), titiler-pgstac, geobrowser |

> **REGLA:** copiar paquetes Crossplane **solo** con `skopeo copy --preserve-digests` desde `docker://…` o desde una copia local `dir:`. `docker save/load/push`, `oci-archive:` y `docker-archive:` descartan las anotaciones de capa `io.crossplane.xpkg` y el paquete ya no se puede instalar; las entradas del seed con `xpkg: true` se verifican tras la copia. Los charts se suben con **oras** usando los media types OCI de Helm.

Si `cr.` no es alcanzable (DNS o certificado no listos, disaster recovery), el paso cambia el `externalURL` de Harbor a `http://localhost:8282`, copia por port-forward y **siempre restaura** `externalURL` (también ante error o Ctrl-C). Para añadir un artefacto: merge request sobre `seed.yaml` (y el archivo local en `harbor/archives/` si aplica), luego re-ejecutar el paso.

### 5.8 Crossplane — Tier 2 (Tabla 34)

| Release (helmfile, label `tier=2`) | Contenido | Versión |
|---|---|---|
| `crossplane` | Crossplane core, 2 réplicas, pool static (`crossplane/values.yaml`) | chart `crossplane-stable/crossplane` 2.4.2 |
| `crossplane-packages` | Providers, DeploymentRuntimeConfig (nodeSelector static en el contenedor `package-runtime`), binding cluster-admin de las ServiceAccounts de los providers | provider-kubernetes v1.4.1, provider-helm (Terradue) v1.0.0 |
| `crossplane-providerconfigs` | ProviderConfigs `kubernetes-provider` y `helm-provider` en namespace `platform` (hook presync que espera a que los providers estén Healthy) | — |

```bash
./bootstrap.sh crossplane                       # = helmfile -l tier=2 apply
kubectl get providers.pkg.crossplane.io         # INSTALLED True, HEALTHY True
kubectl -n platform get providerconfigs.helm.m.terradue.crossplane.io \
  providerconfigs.kubernetes.m.crossplane.io
```

> **NOTA:** ambos providers se bajan de Harbor: `cr.copernicuslac.aig.gob.pa/crossplane/…`, pull secret `harbor-crossplane-pull` (`robot$crossplane+pull`). Para un disaster recovery antes de que Harbor vuelva, `crossplane-packages/values.yaml` lista en un comentario las fuentes upstream: `xpkg.upbound.io` (público) y `cr.terradue.com` (robot de solo lectura, Secret desde `secrets/templates/cr-terradue-pull.yaml`). Cambiar la fuente solo cambia de dónde se baja el paquete, no los providers.

**Upgrade de Crossplane o de un provider:** un componente a la vez, `helmfile -l name=<release> diff`, `apply`, y esperar a que la nueva ProviderRevision esté Healthy antes del siguiente. **Nunca desinstalar un provider.**

---

## 6. Tier 3 — Entrega de la plataforma (§6)

### 6.1 Root Application y capas (Tabla 35)

`bootstrap/root-app.yaml` (aplicado una vez con `./bootstrap.sh root-app`) lee `apps/` y crea una Application por capa. Cada una sincroniza todo lo que hay bajo `platform/<layer>/` en el namespace `platform`.

| Application | Wave | Contenido |
|---|---|---|
| `10-core` | 10 | Vault, External Secrets Operator, ClusterSecretStore |
| `20-identity` | 20 | Keycloak, OPA |
| `30-serving` | 30 | Knative Operator, KnativeServing |
| `40-data` | 40 | Strimzi + Kafka, Kafka UI, STAC API, TiTiler-pgSTAC, Geobrowser, STAC Browser |
| `50-processing` | 50 | Argo Workflows, Argo Events, event bus, CloudEvents webhook, processing API, CWL runner |
| `60-user-services` | 60 | Portal, App Hub, Drive |
| `70-application-packages` | 70 | Composition calrimate, ApplicationPackages |

- **Sync policy de cada capa:** automated, prune, selfHeal; opciones `CreateNamespace=false`, `ApplyOutOfSyncOnly` (un commit que toca un componente re-aplica solo ese), `ServerSideApply`, `SkipDryRunOnMissingResource` (CRDs instalados por una Release de la misma capa); retry 5 veces con backoff 30 s → 5 min.
- **Sin `resources-finalizer`** en la root y las de capa: borrar una Application por error nunca desinstala su capa.
- La root espera a que cada capa esté Healthy antes de la siguiente wave; un componente fallido bloquea solo su capa y las superiores.
- **Dentro de una capa**, la anotación `argocd.argoproj.io/sync-wave` ordena: **−1** namespaces, **0** secretos y prerequisitos, **1** Releases, **2** Objects que usan los CRDs o Services de las Releases.

### 6.2 Convenciones de autoría (Tabla 36)

`platform/_template/` contiene las reglas y un componente de ejemplo (nunca sincronizado). Copiar `example/` a `platform/<layer>/<component>/`, renombrar y adaptar.

| Regla | Detalle |
|---|---|
| Kinds | Charts: `Release` (`helm.m.terradue.crossplane.io/v1beta1`, ProviderConfig `helm-provider`). Todo lo demás (Namespace, Certificate, HTTPProxy, ExternalSecret, CR de un operador): `Object` (`kubernetes.m.crossplane.io/v1alpha1`, ProviderConfig `kubernetes-provider`). Todo recurso en namespace `platform`; un recurso por archivo |
| Namespace | Un Object con el Namespace, sync-wave −1, `managementPolicies [Observe, Create, Update, LateInitialize]` (nunca se borra). Label `eso: enabled` si el namespace contiene un ExternalSecret |
| Secretos | Nunca en values. Un ExternalSecret (Object) que lee `secrets/<component>/<name>` vía `vault-backend`, `refreshInterval 15s`; los charts usan `existingSecret` |
| Exposición | Certificate (`letsencrypt-prod-contour`) + HTTPProxy con anotación `projectcontour.io/ingress.class: contour-external` y `permitInsecure: false`, ambos Objects; OPA y el patrón de rutas de §7.6 para todo lo que no sea público |
| Ubicación | `nodeSelector {aig/node-pool: static}` en toda clave del chart que lo permita |
| Versiones | `chart.version` exactamente como en el `Chart.yaml` (sin prefijo `v` añadido); tags de imagen fijados |
| Charts privados | Solo `chart.pullSecretRef: {name: …}` — el Secret debe estar en namespace `platform` (las Releases namespaced no pueden referenciar otro namespace) |
| Drift detection | `enableDriftDetection: true` por defecto; `false` para charts de operadores que mutan sus propios objetos y para charts que renderizan objetos namespaced sin `metadata.namespace` (§6.3) |
| Data holders | `argocd.argoproj.io/sync-options: Prune=false` en Releases/Objects que guardan datos (Vault, Kafka, KnativeServing, releases de Argo); Objects de CRs de operadores **sin `Delete`** en managementPolicies |
| Metadata | labels `ops.copernicuslac.io/component: <layer>`, `ops.copernicuslac.io/resource-name: <name>` (≤ 63 caracteres), `ops.copernicuslac.io/provider: ifxcloud`; annotations `ops.copernicuslac.io/source-path: <path>`, `ops.copernicuslac.io/resource-type: <apiVersion/Kind o helm-release>` |
| Tamaño del cambio | Un commit, un componente; un upgrade cambia una Release a la vez |

**Ejemplo — Certificate envuelto en un Object** (`platform/20-identity/keycloak/iam-tls.yaml`):

```yaml
apiVersion: kubernetes.m.crossplane.io/v1alpha1
kind: Object
metadata:
  name: iam-tls
  namespace: platform
  labels:
    ops.copernicuslac.io/component: 20-identity
    ops.copernicuslac.io/resource-name: iam-tls
    ops.copernicuslac.io/provider: ifxcloud
  annotations:
    ops.copernicuslac.io/source-path: platform/20-identity/keycloak/iam-tls.yaml
    ops.copernicuslac.io/resource-type: cert-manager.io/v1/Certificate
    argocd.argoproj.io/sync-wave: "2"
spec:
  forProvider:
    manifest:
      apiVersion: cert-manager.io/v1
      kind: Certificate
      metadata: {name: iam-tls, namespace: iam}
      spec:
        secretName: iam-tls
        dnsNames: [iam.copernicuslac.aig.gob.pa]
        issuerRef: {kind: ClusterIssuer, name: letsencrypt-prod-contour}
        privateKey: {algorithm: ECDSA, size: 256, rotationPolicy: Always}
  providerConfigRef: {name: kubernetes-provider, kind: ProviderConfig}
```

**Ejemplo — esqueleto de una Release:**

```yaml
apiVersion: helm.m.terradue.crossplane.io/v1beta1
kind: Release
metadata:
  name: opa
  namespace: platform
  labels: {...}                         # como arriba
  annotations: {argocd.argoproj.io/sync-wave: "1", ...}
spec:
  forProvider:
    enableDriftDetection: true
    wait: true
    waitTimeout: 5m
    chart:
      name: opa
      # chart desde el Harbor de esta plataforma
      repository: oci://cr.copernicuslac.aig.gob.pa/opa-authz
      version: "0.2.5"
      pullSecretRef: {name: helm-repo-harbor}     # Secret en namespace platform
    namespace: opa
    skipCreateNamespace: true                     # el namespace es su propio Object
    values: {...}
  providerConfigRef: {name: helm-provider, kind: ProviderConfig}
```

### 6.3 Comportamiento de provider-helm (Tabla 37)

| Comportamiento | Síntoma | Regla |
|---|---|---|
| Hace poll de una Release sincronizada cada ~10 min | Release Ready solo tras hasta 10 min | Forzar un check: `kubectl -n platform annotate releases.helm.m.terradue.crossplane.io <name> reconcile-at="$(date +%s)" --overwrite` |
| Con `wait: true`, los values nuevos se aplican solo después de que la instalación en curso alcance `waitTimeout` | Un fix en Git (p. ej. tag de imagen) parece ignorado | Esperar a `waitTimeout`; una primera instalación fallida se desbloquea borrando la Release en Argo CD y sincronizando de nuevo — **nunca para charts que instalan CRDs** (knative-operator, Strimzi, Argo) |
| Compara `chart.version` como string | `"v1.20.1"` vs `1.20.1` → `helm upgrade` en cada poll, Ready=False | Escribir la versión exactamente como en `Chart.yaml` |
| Drift detection sobre objetos mutados por un operador | Nueva revisión Helm cada ~10 min, Ready=False "Unavailable" (knative-operator, EventSource/Sensor/EventBus de Argo Events) | `enableDriftDetection: false` |
| Drift detection sobre objetos sin `metadata.namespace` | "an empty namespace may not be set when a resource name is provided", Degraded (strimzi-kafka-operator) | `enableDriftDetection: false` |
| `pullSecretRef` de una Release namespaced no tiene campo namespace | Error de schema en `namespace` | Secret en namespace `platform` |
| CRDs huérfanos de una instalación anterior (helm keep) | "CustomResourceDefinition … exists and cannot be imported into the current release: invalid ownership metadata" | **Nunca borrar los CRDs.** Re-anotarlos: `meta.helm.sh/release-name=<new>`, `meta.helm.sh/release-namespace=<ns>`, label `app.kubernetes.io/managed-by=Helm`, luego `reconcile-at` |

```bash
# reasignar CRDs huérfanos a una release nueva (ejemplo: Argo Workflows)
for c in $(kubectl get crd -o json | jq -r '.items[] |
     select(.metadata.annotations["meta.helm.sh/release-name"]=="<old>") | .metadata.name'); do
  kubectl annotate crd $c meta.helm.sh/release-name=argo-workflows \
     meta.helm.sh/release-namespace=processing --overwrite
  kubectl label crd $c app.kubernetes.io/managed-by=Helm --overwrite
done
```

### 6.4 Añadir un componente

1. **Revisar el chart:** descargarlo en `bootstrap/harbor/archives/charts/` (`helm pull … -d …`), leer `values.yaml` y las plantillas, verificar compatibilidad con Kubernetes 1.33 y el último patch de la línea de versión en uso.
2. **Preparar los prerequisitos externos:** BD y pg_hba (§3.5.1), bucket y usuario (§3.5.2), DNS, client de Keycloak.
3. **Escribir los secretos en Vault** (§7.1).
4. Crear `platform/<layer>/<component>/` desde la plantilla: Object del namespace, ExternalSecrets, Release, Certificate, HTTPProxy, README con prerequisitos y checks.
5. **Validar en local:**
   ```bash
   python3 -c "import yaml,glob; [list(yaml.safe_load_all(open(f))) for f in glob.glob('platform/**/*.yaml', recursive=True)]"
   ```
   y, donde sea posible, `helm template` con los values de la Release.
6. Añadir el chart a `harbor/seed.yaml` y ejecutar `./bootstrap.sh harbor-seed`; la Release usa `oci://cr.copernicuslac.aig.gob.pa/<project>` con `pullSecretRef helm-repo-harbor` (el proyecto debe estar entre los de `robot$helm-pull`).
7. Merge request, merge, seguir la Application de la capa; comprobar la Release (Synced, Ready), pods, Certificate y HTTPProxy.
8. Registrar decisiones e incidencias en `docs/deployment-notes.md`.

---

## 7. Seguridad y fundamentos de la plataforma (§7)

Capas 10 a 30 y el modelo de seguridad de todo servicio público.

### 7.1 Vault (Tablas 38 y 39)

| Aspecto | Valor |
|---|---|
| Release | `copernicuslac-vault` — chart `hashicorp/vault` 0.34.1, Vault 2.0.4, `Prune=false` (`platform/10-core/vault/`) |
| Topología | HA con integrated storage (Raft), 3 pods; volúmenes de data y audit de 10 Gi cada uno en `longhorn` |
| Namespace | `secret-management`; el Service `copernicuslac-vault-active` apunta al líder |
| Exposición | **No expuesto.** UI y CLI por `kubectl -n secret-management port-forward svc/copernicuslac-vault-active 8200:8200` |
| Readiness | probe `/v1/sys/health?standbyok=true&sealedcode=204&uninitcode=204` (los pods sellados no bloquean el rollout); Vault solo es usable cuando está *unsealed* |
| Engines | KV v2 montado en `secrets/`; auth Kubernetes; policy `external-secrets-read` (solo lectura sobre `secrets/`) |
| Unseal | **Manual** (sin KMS cloud ni HSM): todo pod reiniciado vuelve sellado |

| Cuándo | Script (`ops/vault/`) | Necesita |
|---|---|---|
| Primera instalación, o reconstrucción con storage vacío | `init.sh` | nada: crea 5 unseal keys (umbral 3) y el root token |
| Tras init, cualquier reinicio de pod, drain de nodo, reinicio del clúster | `unseal.sh` | 3 de las 5 unseal keys |
| Tras init o una reconstrucción, para restaurar la configuración | `configure.sh` | root token |

> **IMPORTANTE:** `init.sh` escribe las keys y el root token, cifrados con SOPS, en `ops/vault/vault-init.sops.yaml` (git-ignored). Guardarlos en el gestor de contraseñas del equipo (o repartir las keys entre personas) y luego **borrar el archivo de la workstation**. Sin el archivo, los scripts piden las keys y el token. Las unseal keys se pasan a los pods por stdin, nunca en la línea de comandos.
> **Tras reiniciar cualquier pod de Vault, ejecutar `ops/vault/unseal.sh`:** hasta entonces los ExternalSecrets no se refrescan (los Secrets existentes siguen funcionando).

```bash
# esperado: Sealed false, HA Mode active|standby
kubectl -n secret-management exec copernicuslac-vault-0 -- vault status
kubectl get clustersecretstore vault-backend                 # READY True

# escribir un secreto de plataforma (valor oculto, nunca en el historial)
kubectl -n secret-management port-forward svc/copernicuslac-vault-active 8200:8200 \
  >/dev/null 2>&1 &
export VAULT_ADDR=http://localhost:8200; vault login
bash -c 'read -rsp "value: " V </dev/tty; echo
  vault kv put secrets/<component>/<name> <key>="$V"'
vault kv get -format=json secrets/<component>/<name> | jq -c '.data.data | keys'
vault kv patch secrets/<component>/<name> <key>=<new value>  # cambia una key, conserva las demás
```

### 7.2 External Secrets Operator (Fig. 7)

ESO 2.13.0 (Release `eso`, namespace `eso`, 2 réplicas de controller, webhook y cert-controller) copia valores de Vault a Secrets de Kubernetes y los mantiene refrescados.

**Cadena de entrega de secretos (Fig. 7):** Vault (`secret-management`) → ClusterSecretStore (`vault-backend`, ESO) → ExternalSecret (declarado en Git) → Secret (Kubernetes) → Pod (env, archivos, image pulls). Git solo guarda referencias (rutas de Vault). Si Vault está caído o sellado, los Secrets existentes siguen funcionando pero nada se refresca ni se crea.

```yaml
apiVersion: external-secrets.io/v1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  conditions:
    - namespaceSelector:
        matchLabels: {eso: enabled}           # solo namespaces etiquetados pueden usar el store
  provider:
    vault:
      server: http://copernicuslac-vault-active.secret-management:8200
      path: secrets
      version: v2
      auth:
        kubernetes:
          mountPath: kubernetes
          role: external-secrets
          serviceAccountRef: {name: eso-external-secrets, namespace: eso}
```

- Todo ExternalSecret tiene `refreshInterval: 15s`: un valor cambiado en Vault llega al Secret en 15 s. Los pods que leen el Secret como variables de entorno ven el valor nuevo solo tras `kubectl -n <ns> rollout restart deploy/<name>`.
- Forzar refresh inmediato: `kubectl -n <ns> annotate externalsecret <name> force-sync="$(date +%s)" --overwrite`.
- Si el store se validó antes de configurar Vault, queda *not ready*: la misma anotación sobre el ClusterSecretStore fuerza una nueva validación.
- Inventario de rutas de Vault y ExternalSecrets: Anexo C (§14).

### 7.3 TLS y patrón de exposición (Tabla 40)

cert-manager y Contour son Tier 1; los componentes de Tier 3 solo declaran un Certificate y un HTTPProxy como Objects. El HTTPProxy de Keycloak muestra las reglas para rutas administrativas:

```yaml
spec:
  virtualhost:
    fqdn: iam.copernicuslac.aig.gob.pa
    tls: {secretName: iam-tls, minimumProtocolVersion: "1.2"}
  routes:
    - conditions: [{prefix: /admin}]               # consola admin: nunca en Internet
      directResponsePolicy: {statusCode: 404}
    - conditions: [{prefix: /realms/master}]       # realm master: nunca en Internet
      directResponsePolicy: {statusCode: 404}
    - conditions: [{prefix: /}]
      permitInsecure: false
      services: [{name: iam-keycloakx-http, port: 80}]
      responseHeadersPolicy:
        set: [{name: Strict-Transport-Security, value: "max-age=31536000; includeSubDomains"}]
```

**Servicios no publicados (solo port-forward)**

| Servicio | Comando | URL |
|---|---|---|
| Argo CD | `kubectl -n argocd port-forward svc/argocd-server 8080:80` | http://localhost:8080 |
| Vault | `kubectl -n secret-management port-forward svc/copernicuslac-vault-active 8200:8200` | http://localhost:8200 |
| Consola admin de Keycloak | `kubectl -n iam port-forward svc/iam-keycloakx-http 8080:80` | http://localhost:8080/admin |
| Kafka UI | `kubectl -n kafka-ui port-forward svc/copernicuslac-kafka-ui 8080:80` | http://localhost:8080 |
| Argo Workflows UI | `kubectl -n processing port-forward svc/argo-workflows-server 2746:2746` | http://localhost:2746 |
| GitLab, Harbor (solo bootstrap / recuperación) | `svc/copernicuslac-gitlab-webservice-default 8181:8181` · `svc/harbor 8282:80` | http://localhost:8181 · :8282 |

### 7.4 Keycloak (Tablas 41 y 42)

| Aspecto | Valor |
|---|---|
| Release | `iam` — chart codecentric `keycloakx` 7.4.0, Keycloak 26.8.1, 2 réplicas, clustering por la base de datos (`jdbc-ping`) |
| Base de datos | `keycloak` en el PostgreSQL gestionado, rol `keycloak` CONNECTION LIMIT 30, contraseña de Vault `secrets/iam/keycloak-external-db`; pool `--db-pool-max-size=10` por réplica |
| Host | `https://iam.copernicuslac.aig.gob.pa` (`--hostname`, `--hostname-strict=true`); consola admin en `--hostname-admin=http://localhost:8080` por port-forward |
| Temas | PVC 1 Gi RWX en `longhorn` (`keycloak-themes-pvc`) |
| Management | `/health` y `/metrics` en el puerto 9000, solo interno al clúster |

**Prerequisitos** (de `platform/20-identity/keycloak/README.md`):

```sql
-- pgAdmin, en el primary, una sentencia a la vez
CREATE ROLE keycloak WITH LOGIN PASSWORD '<password>' CONNECTION LIMIT 30;
GRANT keycloak TO CURRENT_USER;
CREATE DATABASE keycloak OWNER keycloak ENCODING 'UTF8' TEMPLATE template0;
REVOKE ALL ON DATABASE keycloak FROM PUBLIC;
-- pg_hba.conf en ambos nodos: host keycloak keycloak 192.168.80.0/24 scram-sha-256
```
```bash
vault kv put secrets/iam/keycloak-external-db password='<same password>'
vault kv put secrets/iam/keycloak-admin username=bootstrap-admin \
  password="$(openssl rand -base64 24)"
```

**Tras el primer arranque:**

1. Entrar como bootstrap admin por el port-forward, crear administradores personales con OTP en el realm master y luego **borrar el bootstrap admin** (se quitan de la Release el ExternalSecret y las variables `KC_BOOTSTRAP_*`; un comentario en `iam.yaml` explica cómo reponerlas para una instalación nueva).
2. Poner el **Frontend URL del realm master en `http://localhost:8080`** (con `kcadm` en el pod): `/realms/master` no está publicado y sin esto la consola admin falla con "Timeout when waiting for 3rd party check iframe message".
3. Crear y endurecer el realm de plataforma. Hay un export parcial en `ops/keycloak/CopernicusLAC-Platform-realm.json`.

**Realm `CopernicusLAC-Platform`**

| Ajuste | Valor |
|---|---|
| Issuer | `https://iam.copernicuslac.aig.gob.pa/realms/CopernicusLAC-Platform` |
| Registro | Sin auto-registro; sin forgot-password ni verify-email hasta configurar un relay SMTP [TBC-7] |
| Segundo factor | **OTP obligatorio para todos:** flujo de navegador "Browser - Conditional 2FA" y "OTP Form" en Required |
| Fuerza bruta | Detección activa, bloqueo tras 5 fallos |
| Política de contraseñas | Longitud 12, mayúscula, dígito, carácter especial, distinta del username, distinta del e-mail, no usada recientemente (5) |
| Sesiones y tokens | SSO idle 30 min, SSO max 10 h, access token 5 min |
| Eventos | Eventos de usuario y admin guardados 30 días |
| Clients | `gitlab` (configurado), `discover` (oauth2-proxy del catálogo), `argo-workflows` (preparado), clients de procesamiento `processing-coplac` / `results-coplac`, `stac-browser`, Portal, App Hub, Drive (por crear) — redirect URIs sin wildcards. También `harbor` (§5.5) |
| Grupos | `main`, `sysadmin`, `admin`, `Operator`, `writers-processing` y un grupo por namespace de procesamiento (por crear, §12.2); claim `groups` con nombres planos (mapper Group Membership, full path OFF) en el ID token |

### 7.5 OPA (Tablas 43, 44 y 45)

| Aspecto | Valor |
|---|---|
| Release | `opa` — chart `opa` 0.2.5 (Terradue, desde `oci://cr.copernicuslac.aig.gob.pa/opa-authz`), imagen `openpolicyagent/opa:1.21.2-envoy-3`, 2 réplicas, PodDisruptionBudget minAvailable 1, root filesystem de solo lectura |
| Integración | External authorisation de Envoy por gRPC 9191; ExtensionService de Contour `opa/opa-authz`; todo HTTPProxy que ponga `virtualhost.authorization.extensionRef {name: opa-authz, namespace: opa}` es autorizado por OPA |
| Policy | `files/policy.rego` del chart (package `envoy.authz`, query `data.envoy.authz.result`) — **no se puede sobrescribir por values** |
| Tags de imagen | Los tags `-envoy` siguen los releases de **opa-envoy-plugin** (`1.21.2-envoy-3`), no los de OPA: `1.21.3-envoy` no existe |

**Datos de la policy (values `data.authz`)**

| Clave | Valor en Panamá |
|---|---|
| `iss` / `aud` / `azp` | issuer del realm `CopernicusLAC-Platform` / `account` / `discover` |
| `cert_pem` | certificado público de firma del realm (RS256, use=sig) — cambia al rotar la clave del realm: `curl -s <issuer>/protocol/openid-connect/certs | yq -p json '.keys[] | select(.alg == "RS256" and .use == "sig") | .x5c[0]'` |
| `processing_host` / `processing_allowed_clients` | `processing.copernicuslac.aig.gob.pa` / `results-coplac`, `discover`, `processing-coplac` |
| `catalog_hosts` / `catalog_allowed_clients` | `results.`, `discover.` / `stac-browser` |
| `titiler_hosts`, `download_host` | `view.`, `download.` |
| admin bypass | `enable_admin_bypass true`, `admin_groups admin, sysadmin` |

**Decisión de la policy por host (chart 0.2.5)**

| Tipo de host | Sin header Authorization | Con Bearer token válido |
|---|---|---|
| processing | Solo OPTIONS (preflight CORS); todo lo demás 403 | azp/aud en `processing_allowed_clients`; el namespace (primer segmento del path) en los grupos del usuario; las escrituras requieren `writers-processing` y permiso de escritura sobre el namespace |
| catalog (`discover`, `results`) | Cualquier método permitido — diseñado para ir seguido de oauth2-proxy (§7.6) | Grupo `Operator`: todos los métodos; si no, check de audience/azp, grupo del namespace, permiso de escritura para escrituras |
| download | GET y OPTIONS (pass-through a oauth2-proxy) | GET con audience de processing y acceso al namespace; PUT para `writers-processing` con permiso de escritura |
| otros hosts (p. ej. `view`) | Permitido (pass-through a oauth2-proxy) | Check de audience; el GET de TiTiler necesita un client de processing |

Tests negativos: `ops/tests/opa-negative-tests.sh`.

### 7.6 Proteger un servicio público (Tabla 46)

Un HTTPProxy público que sirve datos a usuarios autenticados sigue un único patrón (hoy usado por el catálogo `discover`): **OPA** (clientes API con Bearer token) + **oauth2-proxy** (usuarios de navegador).

```yaml
virtualhost:                        # HTTPProxy raíz
  fqdn: discover.copernicuslac.aig.gob.pa
  tls: {secretName: discover-tls}
  authorization:
    extensionRef: {name: opa-authz, namespace: opa}
routes:                             # HTTPProxy hijo del workload (/main)
  - conditions:                     # 1. un Bearer token REAL → API, decide OPA
      - prefix: /
      - header: {name: authorization, regex: '(?i)bearer\s+\S+'}
    services: [{name: nginx-stripper-catalog-main, port: 80}]
  - authPolicy: {disabled: true}    # 2. endpoints de oauth2-proxy (callback de login)
    conditions: [{prefix: /oauth2}]
    services: [{name: oauth2-proxy-main, port: 80}]
  - conditions: [{prefix: /}]       # 3. todo lo demás → oauth2-proxy (login), NUNCA la API
    services: [{name: oauth2-proxy-main, port: 80}]
```

| Ajuste de oauth2-proxy | Valor |
|---|---|
| Imagen | `quay.io/oauth2-proxy/oauth2-proxy:v7.12.0`, provider `keycloak-oidc`, un Deployment por workload |
| Client | Client Keycloak confidential (`discover` para el catálogo main), solo standard flow, redirect `https://<host>/<ns>/oauth2/callback` |
| Grupos | allowed groups `<ns>,sysadmin`; el claim `groups` debe estar en el ID token con nombres planos (mapper en un Default client scope; oauth2-proxy solo pide el scope `openid`) |
| Secretos | Vault `secrets/catalog/oauth2-proxy`: `OAUTH2_PROXY_CLIENT_ID`, `OAUTH2_PROXY_CLIENT_SECRET`, `OAUTH2_PROXY_COOKIE_SECRET` |
| Cookie secret | Debe ser de 16, 24 o 32 bytes: `openssl rand -hex 16` (32 caracteres). Si no: "cookie_secret must be 16, 24, or 32 bytes to create an AES cipher" |
| Escrituras | Con token: lo que decida OPA. Con sesión de navegador: cualquier miembro de los grupos permitidos (OPA no está en ese camino) — los grupos permitidos son, por tanto, los dueños del catálogo |

### 7.7 Knative Serving (Tabla 47)

| Aspecto | Valor |
|---|---|
| Operator | Release `knative-operator` — chart `knative-operator` 1.20.1 (`https://knative.github.io/operator`), `enableDriftDetection false` (el operador parchea sus propios certificados de webhook y CRDs), `Prune=false` |
| Serving | Object `KnativeServing` 1.20.1 en `knative-serving`: high availability 2, ingress contour, `config-network` ingress-class `contour.ingress.networking.knative.dev`, feature `kubernetes.podspec-nodeselector: enabled` (requerida por el nodeSelector de las funciones de procesamiento), workloads activator, autoscaler, autoscaler-hpa, controller, webhook, net-contour-controller en el pool static; managementPolicies sin Delete, readiness `DeriveFromObject`, `Prune=false` |
| Por qué el operador | Los manifiestos de release de Knative son assets generados, no archivos de un repo Git; el operador se instala por chart y toma un único recurso KnativeServing pequeño |
| Upgrade | Un minor a la vez: `targetRevision` de Contour (Tier 1), chart del operador, luego `spec.version` de KnativeServing |

Check: `kubectl -n knative-serving get knativeserving` (Ready True) y `kubectl get ksvc -A`. Knative crea HTTPProxies llamados `<function>-contour-internal-*` por cada servicio; son cluster-local y esperados.

---

## 8. Servicios de datos — capa 40 (§8)

`platform/40-data/`. Kafka y STAC API desplegados; TiTiler, Geobrowser, STAC Browser y results catalogs por desplegar.

**Fig. 8 (de una ejecución al catálogo y al mapa):** *Produce:* Argo Workflow (CWL sobre Calrissian) → `map-item` (stac-postman). *Store and index:* `map-item` escribe el item en la STAC API (stac-fastapi, pgSTAC en PostgreSQL externo) y los archivos COG en Object storage (bucket processing). *Discover and view:* Usuario (navegador, Portal) → STAC Browser (búsqueda, metadata) y TiTiler-pgSTAC (map tiles, `view`). TiTiler encuentra el item en pgSTAC y lee los píxeles directamente del COG. **Un resultado que no está en el catálogo no existe para los usuarios.**

### 8.1 Kafka (Tabla 48)

| Aspecto | Valor |
|---|---|
| Operator | Release `copernicuslac-strimzi-operator` — chart `strimzi-kafka-operator` 1.1.0 (`oci://quay.io/strimzi-helm`), namespace `kafka-operator`, observando solo el namespace `kafka`, 2 réplicas con leader election y PodDisruptionBudget, `enableDriftDetection false` |
| Clúster | `copernicuslac-kafka`, Kafka 4.2.1, metadataVersion 4.2-IV1, KRaft (API Strimzi 1.x `kafka.strimzi.io/v1`) |
| Nodos | KafkaNodePool `dual-role`: 3 × (controller + broker), uno por nodo (pod anti-affinity), pool static, 20 Gi cada uno en `longhorn-processing`, `deleteClaim false`, JVM heap 1 Gi |
| Listeners | plain 9092 y tls 9093, solo internos; bootstrap `copernicuslac-kafka-kafka-bootstrap.kafka:9092` |
| Durabilidad | `default.replication.factor 3`, `min.insync.replicas 2` — un nodo puede caer sin perder escrituras |
| Topics | `auto.create.topics.enable true`, `num.partitions 3` (decisión 2026-10-23); los topics con ajustes específicos se declaran como KafkaTopic |
| Protección | Object de Kafka `Prune=false`, managementPolicies sin Delete, readiness `DeriveFromObject` |

> **NOTA — Por qué está habilitada la auto-creación de topics:** el Sensor de CloudEvents publica cada evento en el topic indicado en el header `X-Kafka-Topic` que envía el processing API; los nombres dependen del proceso y no se conocen de antemano.

- Reinicios y upgrades pasan por el recurso Kafka; **nunca borrar pods de brokers en bloque ni editar los StrimziPodSets**.
- Strimzi instala sus CRDs solo en la primera instalación del chart: **aplicar los CRDs nuevos antes de cada upgrade de Strimzi**, luego el operador, luego `spec.kafka.version`.
- El listener plain **no tiene autenticación**: cualquier pod puede producir y consumir. Objetivo: SCRAM y autorización en el listener TLS, un KafkaUser por servicio con su contraseña en Vault, y luego quitar el listener plain (TBC-8).
- Check: `kubectl -n kafka get kafka,kafkanodepool,kafkatopic` (Ready True).

### 8.2 Kafka UI
Release `copernicuslac-kafka-ui` — chart `kafka-ui` 1.4.2 (kafbat, desde `oci://cr.copernicuslac.aig.gob.pa/strimzi-kafka`), namespace `kafka-ui`, 1 réplica, clúster `copernicuslac-kafka` vía el Service bootstrap de Strimzi.
Acceso: `kubectl -n kafka-ui port-forward svc/copernicuslac-kafka-ui 8080:80`.

### 8.3 STAC API — catálogo main (Tabla 49)

| Aspecto | Valor |
|---|---|
| Release | `copernicuslac-stac-api` — chart `stac-fastapi-pgstac` 2.0.7 (desde `oci://cr.copernicuslac.aig.gob.pa/stac-utils`), imagen `ghcr.io/stac-utils/stac-fastapi-pgstac:6.2.1` (pública), `Prune=false` |
| Namespace | `catalog` (workload key `catalog`; label `eso=enabled`) |
| URL pública | `https://discover.copernicuslac.aig.gob.pa/main` (Certificate `discover-tls`); HTTPProxy raíz `stac-fastapi-main-root` con OPA, HTTPProxy hijo `stac-fastapi-child-main` con el patrón de 3 rutas de §7.6 |
| Contenedores | `stac-fastapi-pgstac` (uvicorn con `--root-path /main` y proxy headers) + nginx stripper `1.28-alpine` que quita `/main` (Service `nginx-stripper-catalog-main`) |
| Base de datos | `pgstac` en el PostgreSQL gestionado, pgSTAC 0.9.12; credenciales Vault `secrets/catalog/pgstac` (username, password) → Secret `pgstac-secret` (`POSTGRES_USER`, `POSTGRES_PASS`) |
| Transacciones | `enable_transactions true`: escrituras solo con token decidido por OPA, o con sesión de navegador de un miembro de `main` / `sysadmin` |
| Login | `oauth2-proxy-main`, client `discover`, allowed groups `main,sysadmin`, secretos Vault `secrets/catalog/oauth2-proxy` |
| Conexiones | 4 workers uvicorn × pool 10 = 40 (`web_concurrency 4`, `db_max_conn_size 10`) |
| Otros | `reload false`, `use_api_hydrate true`, tuning HTTP de GDAL, pool static, securityContext restringido |

**Procedimiento de base de datos** (pgAdmin en nodo01 con la cuenta DBA; PostGIS, btree_gist y unaccent disponibles en `template1`):

1. Generar la contraseña y escribirla primero en Vault: `vault kv put secrets/catalog/pgstac username=pgstac password="$P"`.
2. Sobre la BD `postgres`, una sentencia a la vez:
   ```sql
   CREATE ROLE pgstac LOGIN PASSWORD '<paste>' CONNECTION LIMIT 50;
   CREATE DATABASE pgstac;                         -- owner: la cuenta DBA, nunca el usuario de aplicación
   REVOKE ALL ON DATABASE pgstac FROM PUBLIC;
   GRANT CONNECT ON DATABASE pgstac TO pgstac;
   ```
3. En una primera instalación, crear los roles de pgSTAC para poder otorgarlos antes del script:
   ```sql
   CREATE ROLE pgstac_admin; CREATE ROLE pgstac_read; CREATE ROLE pgstac_ingest;
   GRANT CONNECT, TEMPORARY ON DATABASE pgstac TO pgstac_admin, pgstac_read, pgstac_ingest;
   ```
   Sin `TEMPORARY` el script falla con 42501 "permission denied to create temporary tables" (el REVOKE también quita TEMPORARY).
4. Sobre la BD `pgstac`, ejecutar `https://raw.githubusercontent.com/stac-utils/pgstac/v0.9.12/src/pgstac/pgstac.sql` (extensiones, roles, schema `pgstac` propiedad de `pgstac_admin`, tabla de migraciones).
5. El script deja la sesión con `SET ROLE`: ejecutar `RESET ROLE;` (o abrir un Query Tool nuevo) antes de las siguientes sentencias; si no, fallan con 42501 ("must be owner", "only roles with ADMIN option").
6. ```sql
   GRANT pgstac_ingest TO pgstac;                  -- lectura y escritura, no pgstac_admin
   ALTER ROLE pgstac SET search_path TO pgstac, public;
   SELECT pgstac.get_version();                    -- → 0.9.12
   ```
   Los upgrades de schema los hace el operador con un `pgstac.sql` nuevo.
7. Línea de pg_hba `host pgstac pgstac 192.168.80.0/24 scram-sha-256` en ambos nodos y reload.

### 8.4 TiTiler-pgSTAC — *por desplegar* (Tabla 50)

TiTiler renderiza map tiles desde los COG referenciados por los items STAC. Configuración planificada:

| Aspecto | Panamá |
|---|---|
| Namespace | `catalog` (reutiliza `pgstac-secret` de la STAC API) |
| Host | `view.copernicuslac.aig.gob.pa/main` + Certificate `view-tls` |
| Peticiones sin token | oauth2-proxy, grupos `main,sysadmin`; ruta 1 con el regex de Bearer |
| Conexiones a BD | 2 workers × pool 2 = 4 |
| Caché de tiles | Propuesto: 2 GB, PVC 10 Gi `longhorn`, 2–3 Gi RAM; revisar la imagen de Redis del chart (las imágenes de Bitnami ya no son públicas) |
| Object storage | StorageGRID, path-style, usuario de solo lectura sobre los buckets de resultados |
| Ubicación | `aig/node-pool: static` |

Chart planificado 3.0.6 / app 2.1.0. Pendientes: chart, DNS `view.`, usuario S3 de solo lectura, client Keycloak, secretos en Vault (TBC-5: buckets a leer, imagen y tamaño de Redis).

### 8.5 Geobrowser — *por desplegar* (Tabla 51)

El Geobrowser (**glowstac**) es el cliente de mapas. **Sin OPA en el host:** la aplicación autentica a los usuarios con Keycloak en el navegador. Chart planificado 1.0.0 / app 2.1.7, namespace `geobrowser`, host `dashboards.`.

Correcciones a la configuración de runtime (`config.dat`):

| Clave | Panamá |
|---|---|
| `stacApiEndpoint` | `https://discover.copernicuslac.aig.gob.pa/main` |
| `stacApiProtectedList` | `"https://discover.copernicuslac.aig.gob.pa"` |
| `auth.clientId` | `processing-coplac`, o añadir processing a OPA (decisión pendiente, TBC-4) |
| Client Keycloak | client público, redirect `https://<host>/main/*`, web origin `https://<host>` |
| Otros endpoints | se conservan; activos cuando existan los servicios |

### 8.6 STAC Browser — *por desplegar*
Front end estático; si se expone en un host de catálogo sigue las mismas reglas de OPA (client `stac-browser`). Results catalogs (6): patrón de rutas de §7.6.

---

## 9. Servicios de procesamiento — capas 50 y 70 (§9)

`platform/50-processing/` y capa 70. Los workflows corren en el namespace `processing`; el processing API en `mate-api`. **El primer segmento del path de la API es el namespace de los workflows:** `https://processing.copernicuslac.aig.gob.pa/processing/…`.

**Fig. 9 (una petición de procesamiento de extremo a extremo; el CWL runner aún no está desplegado):**
1. *Client* (Portal o usuario de API) → 2. *Processing API* (Knative, función `execute`) → 3. *Argo Workflows* (server → controller), con *wdir volume* (RWX, `longhorn-processing`).
Pasos del workflow: 4. `init` (eoap-cwlwrap, stage-in) → 5. `runner` (Calrissian, CWL) → 6. `reducer-pre` (recoge outputs) → 7. `map-item` (stac-postman) → 8. `reducer` (finaliza) → 9. `patch-workflow` (resultado).
Salidas: Object storage (COG outputs, logs, artifacts), STAC API (items en pgSTAC), Kafka (topic `processing.<id>.workflow.<type>`).
Tipos de evento: `prepared · staged · piped · completed · failed`. Los steps hacen POST de CloudEvents al EventSource webhook; el Sensor los publica en el topic del header `X-Kafka-Topic`. El cliente sigue el job con `get-status` y obtiene resultados con `get-result`. Tipos de evento y nombres de topic vienen de las anotaciones del WorkflowTemplate.

### 9.1 Argo Workflows (Tabla 52)

| Aspecto | Valor |
|---|---|
| Release | `argo-workflows` — chart `argo-workflows` 0.45.26 (Argo Workflows v3.7.2), `Prune=false`. **El nombre es fijo:** el processing API alcanza el server como `argo-workflows-server.<namespace>:2746` |
| Scope | singleNamespace (`processing`); CRDs instalados y conservados; aggregate roles; clusterWorkflowTemplates habilitados |
| Controller | 2 réplicas (leader election), pool static; defaults de workflow: `serviceAccountName argo-sa`, `ttlStrategy` 1800 s tras completar, `podGC deleteDelayDuration 5 s`, `artifactGC OnWorkflowDeletion` con `argo-sa` |
| Artifacts | Bucket `copernicuslac-argo-artifacts` (`svr-cop-s3-pan.ifxcloud.com:10443`, path-style), logs archivados; key del usuario `argowf` de Vault `secrets/processing/argo-artifacts` (accesskey, secretkey) → `argo-artifacts-creds` |
| Archive | BD PostgreSQL `argowf` en `10.0.0.3`, tabla `argo_workflows`, archiveTTL 90 días, nodeStatusOffLoad; credenciales Vault `secrets/processing/argo-postgres` → `argo-postgres-config`; pool 2 idle / 10 open. Argo crea sus tablas en el primer arranque |
| Server | 2 réplicas; authModes **server + client** (TEMPORARY, §12.3); UI solo por port-forward |
| Identidad de los workflows | ServiceAccount `argo-sa` con Role `argo-sa-role` (pods, logs, PVCs, ConfigMaps, jobs, workflows, templates, cron workflows, leases, task results, artifact GC tasks); token de larga duración en el Secret `argo-sa.service-account-token`, usado por el processing API |

**Prerequisitos:** BD `argowf` (rol `argowf`, CONNECTION LIMIT 25) con el procedimiento de §3.5.1; bucket `copernicuslac-argo-artifacts` y usuario `argowf` con `ops/storagegrid/argowf-group-policy.json` (list y location sobre el bucket; get, put, delete y multipart solo sobre sus objetos); secretos en Vault.

```bash
kubectl -n processing get externalsecret                     # SecretSynced
kubectl -n processing logs deploy/argo-workflows-workflow-controller \
  | grep -iE 'persist|archive|migrat|error' | head
kubectl -n processing port-forward svc/argo-workflows-server 2746:2746      # UI
```

### 9.2 Argo Events, Event Bus y Webhook (Fig. 10, Tabla 53)

**Fig. 10 (eventos de estado):** Workflow step (HTTP POST `/cloud-events`) → EventSource (webhook `:12000`, 2 réplicas) → EventBus (respaldado por Kafka) → Sensor (transform Lua, trigger Kafka) → Status topic (uno por proceso y estado) → Consumers (Portal, monitoring, …). Topic del EventBus: `processing-kafka-event-bus`.

| Release | Chart | Crea |
|---|---|---|
| `argo-events` | `argo-events` 2.4.27 (argo-helm) | Controller de Argo Events restringido al namespace `processing`, 2 réplicas, CRDs conservados |
| `kafka-event-bus` | `kafka-event-bus` 0.1.0 (seda, desde `oci://cr.copernicuslac.aig.gob.pa/seda`) | EventBus `kafka-event-bus` sobre `copernicuslac-kafka-kafka-bootstrap.kafka:9092` |
| `cloud-event-webhook` | `cloud-event-webhook` 0.3.0 (seda, mismo origen) | EventSource `cloud-events-webhook` (Service `cloud-events-webhook-eventsource-svc:12000`, path `/cloud-events`) y Sensor `cloud-events-webhook-sensor` con trigger Kafka; ServiceAccount `argo-sa`; debug logging off |

- Ambas Releases seda tienen `enableDriftDetection false` (el controller de Argo Events añade defaults a EventBus, EventSource y Sensor; con drift detection se actualizarían cada 10 min → Ready=False "Unavailable").
- Argo Events nombra sus topics `<namespace>-<eventbus>[-<sensor>-trigger|-action]`. Están declarados como KafkaTopic en `platform/50-processing/event-bus/kafka-topics.yaml` (3 particiones, replicación 3, 7 días): `processing-kafka-event-bus`, `processing-kafka-event-bus-cloud-events-webhook-sensor-trigger` y `…-action`. **Cada Sensor nuevo en este EventBus necesita sus propios topics `-trigger` y `-action`.**
- Los nombres de los Objects de los topics están acortados (`kafka-topic-webhook-sensor-trigger` …): un valor de label no puede superar 63 caracteres; el nombre completo del topic queda en el manifiesto.
- El Sensor lee el topic destino del header `X-Kafka-Topic` y publica ahí el CloudEvent (auto-creado, §8.1).
- Check: `kubectl -n processing get eventbus,eventsource,sensor` y la línea "Consuming" en el log del Sensor.

### 9.3 Processing API — mate-api (Tabla 54)

| Aspecto | Valor |
|---|---|
| Release | `mate-api` — chart `mate-api` 1.2.2 (desde `oci://cr.copernicuslac.aig.gob.pa/mate`), namespace `mate-api` |
| Funciones | 10 Knative Services, imágenes `cr.terradue.com/mate/<function>:1.2.0` (**TEMPORARY:** copia a Harbor bloqueada, TBC-1), min 1 / max 10, puerto 8090: `get-api`, `get-conformance-classes`, `get-processes`, `get-process-description`, `execute`, `get-jobs`, `get-status`, `get-result`, `get-logs`, `get-package` |
| Exposición | Creada por el chart: Certificate `processing-tls` (`letsencrypt-prod-contour`) y HTTPProxy `mate-api-routing` (contour-external, autorización OPA, CORS, una ruta regex por función) |
| Identidad | ServiceAccount `mate-api-sa` (pull secret `cr-terradue-pull`); solo puede leer el Secret `argo-sa.service-account-token` en `processing` (Role `mate-api-token-reader`) |
| Ajustes | `ARGO_SERVER_HOST http://argo-workflows-server.{namespace}:2746`, `AUTH_TOKEN_NAME argo-sa.service-account-token`, `cloudEventsWebhook http://cloud-events-webhook-eventsource-svc.{namespace}.svc.cluster.local:12000/cloud-events`, `operatorProcessingSecretName operator-processing` (opcional, leído por `execute`) |
| Security context | non-root (1001:100), sin escalada de privilegios, todas las capabilities eliminadas, seccomp RuntimeDefault |
| Ubicación | pool static — requiere la feature de Knative `kubernetes.podspec-nodeselector` (§7.7) |

### 9.4 CWL Runner y Application Packages — *por desplegar*
- **Plantillas del CWL runner** (WorkflowTemplates estándar para stage-in, ejecución con Calrissian, publicación STAC, eventos de estado): retiradas de la primera entrega; se desplegarán en la capa 50 con imágenes en Harbor y los secretos de S3, registry y `operator-processing` en Vault.
- **Application packages (capa 70):** la composition `calrimate` (`function-calrimate` en Crossplane) convierte un `ApplicationPackage` en el WorkflowTemplate, el ConfigMap de CWL y el semáforo de un proceso. Prerequisitos: el paquete de la función en Harbor, el CWL runner, los topics de Kafka o la auto-creación (ya disponible).

---

## 10. Servicios de cara al usuario — capa 60 (§10)

**Portal, App Hub y Drive — por desplegar.** La capa 60 está vacía. Sigue vigente la descripción funcional de la issue 2.0: Portal (landing page, CMS, marketplace, back office); App Hub (JupyterHub con perfiles generados por el Portal); Drive (archivos compartidos sobre StorageGRID). Cada servicio sigue el procedimiento de §6.4. Correcciones ya identificadas:

- Cada servicio en el PostgreSQL gestionado con su propio rol, CONNECTION LIMIT y líneas de pg_hba.
- **Drive:** StorageClass `longhorn` en lugar de la eliminada `longhorn-perf-r1`, probes habilitados, relay SMTP o correo deshabilitado, HTTPProxy con la anotación de ingress-class, sin override de `POSTGRES_SSLMODE`.
- **App Hub:** OAuth contra el realm `CopernicusLAC-Platform` (no un realm externo de desarrollo); revisar el bucle de drift de la Release antes de adoptarla.
- **Portal:** sin Service NodePort; front ends alcanzables solo a través de Envoy.

---

## 11. Operaciones (§11)

### 11.1 Entregar un cambio (Fig. 11, Tabla 55)

**Flujo Tier 3 (Fig. 11):** Merge request (rama, revisión, CI) → `main` (estado deseado, auditoría) → Argo CD (sync, health) → Crossplane (apply, helm upgrade) → Servicio (Ready, Healthy). Una edición manual se revierte.

| Tier | Cambio | Aplicar | Verificar |
|---|---|---|---|
| 3 | Merge request en `platform/` (un componente) | Merge: Argo CD sincroniza la capa en ≤ 3 min; Crossplane aplica | Application de la capa Synced/Healthy; Release Ready; el servicio responde |
| 2 | Merge request en `bootstrap/` (values de helmfile) | `helmfile -l name=<release> diff`, luego `apply` | Providers Healthy |
| 1 | Merge request en `bootstrap/<component>/` | `kubectl apply -f` la Application; `argocd app diff`; `argocd app sync` (o el paso de `bootstrap.sh`) | Application Synced/Healthy |
| Secretos | Vault (Tier 3) o sops (Tiers 1–2) | Refresh de ESO en 15 s / `./bootstrap.sh secrets` | Rollout restart de los pods que leen el Secret como variable de entorno |

**Rollback:** mismo camino — `git revert`, merge, y ambos lazos convergen al estado anterior. Los charts con migraciones de datos (GitLab, Keycloak, Harbor) necesitan un backup antes del upgrade.

### 11.2 Health check diario (Tabla 56)

Ejecutar de abajo hacia arriba; un fallo en una línea puede explicar todo lo que está debajo.

| # | Check | Comando | Esperado |
|---|---|---|---|
| 1 | Nodos | `kubectl get nodes` | todos Ready |
| 2 | Storage | `kubectl -n longhorn-system get volumes.longhorn.io` | robustness healthy |
| 3 | Tiers 1–2 | `cd bootstrap && ./bootstrap.sh status` | todo Synced/Healthy, providers Healthy |
| 4 | Vault | `kubectl -n secret-management get pods` · `vault status` | 3/3 Running, Sealed false |
| 5 | Cadena de secretos | `kubectl get clustersecretstore vault-backend` · `kubectl get externalsecret -A` | Ready · SecretSynced |
| 6 | Entrega Tier 3 | `kubectl -n argocd get applications` | Synced, Healthy |
| 7 | Recursos Crossplane | `kubectl -n platform get releases.helm.m.terradue.crossplane.io,objects.kubernetes.m.crossplane.io` | SYNCED True, READY True |
| 8 | Rutas y TLS | `kubectl get httpproxies,certificates -A` | valid · Ready |
| 9 | Procesamiento | `kubectl -n mate-api get ksvc` · `kubectl -n processing get workflows,eventsource,sensor` | READY True · sin workflows atascados |
| 10 | Kafka | `kubectl -n kafka get kafka,kafkatopic` | Ready |
| 11 | Bases de datos | `SELECT count(*) FROM pg_stat_activity;` | muy por debajo de `max_connections` |

### 11.3 Troubleshooting (Tabla 57)

Depurar a lo largo de la cadena de entrega: ¿llegó Git al clúster (Argo CD)? ¿actuó Crossplane (condiciones de la Release u Object)? ¿arrancó el workload (pods, eventos)? El mensaje de `status.conditions` de una Release suele contener el error exacto de Helm:

```bash
kubectl -n platform describe releases.helm.m.terradue.crossplane.io <name> | tail -30
```

| Síntoma | Causa | Solución |
|---|---|---|
| Migraciones de GitLab "could not find database" | Typo en pg_hba o línea faltante en un nodo; BD `postgres` no permitida | Corregir pg_hba en ambos nodos, reload, revisar `pg_hba_file_rules` |
| Servicios fallan con "too many clients" | `max_connections` agotado (p. ej. el HPA de GitLab escaló Sidekiq a 8) | Pools dentro del presupuesto de conexiones (§3.5.1) |
| Peticiones de token de Harbor devuelven 500 | Clave del token-service en PKCS#8 | Generar PKCS#1 (`gen-harbor-secrets.sh`) |
| Login a la UI de GitLab/Harbor falla por port-forward | Cookies Secure sobre HTTP plano | Usar `https://git.` y `https://cr.` |
| Paquete Crossplane no instalable tras una copia | Anotaciones xpkg perdidas (docker save, oci-archive) | Copiar con skopeo `dir:`/`docker://` `--preserve-digests` |
| Application de Contour OutOfSync | `preserveUnknownFields` del CRD | `ignoreDifferences` (ya aplicado) |
| `vault operator unseal` no lee "-" | Limitación del CLI | Pasar la key por stdin con `sh -c 'read -r k; vault operator unseal "$k"'` (`unseal.sh`) |
| ClusterSecretStore not ready tras configurar Vault | Validado antes de `configure.sh` | Anotación `force-sync` sobre el store |
| Consola admin de Keycloak: timeout "3rd party check iframe" | `/realms/master` no publicado | Frontend URL de master = `http://localhost:8080` |
| OPA ImagePullBackOff | Tag `x.y.z-envoy` inexistente | Usar tags de opa-envoy-plugin (`1.21.2-envoy-3`) |
| Fix de una Release no se aplica | `wait: true`, instalación corriendo hasta `waitTimeout` | Esperar, o borrar la Release en Argo CD y sincronizar (no en charts con CRDs) |
| Release actualizada cada 10 min, Ready=False | `chart.version` no coincide como string, o drift en objetos mutados por un operador | Versión exacta; `enableDriftDetection false` |
| Release Degraded "an empty namespace may not be set…" | Drift detection sobre objetos sin namespace | `enableDriftDetection false` |
| "CustomResourceDefinition … cannot be imported" | CRDs huérfanos de una release anterior | Re-anotar los CRDs (§6.3) |
| Knative rechaza un Service con nodeSelector | Feature `podspec-nodeselector` deshabilitada | Habilitarla en KnativeServing (ya aplicado) |
| Namespace atascado en Terminating | Objeto residual con finalizer (p. ej. endpoints tras quitar Knative a mano) | Encontrar el objeto con `kubectl api-resources --namespaced -o name | xargs kubectl get -n <ns>`, quitar su finalizer |
| Sensor fatal "Topics do not exist" | Topics de Argo Events no declarados | KafkaTopics (ya aplicado) o auto-create |
| Object SyncFailed "must be no more than 63 characters" | Valor de label demasiado largo | Nombre de Object más corto |
| Script de pgSTAC falla 42501 en tablas temporales | El REVOKE quitó TEMPORARY | `GRANT CONNECT, TEMPORARY` a los roles de pgSTAC |
| GRANT / ALTER fallan 42501 tras `pgstac.sql` | Sesión aún con SET ROLE | `RESET ROLE` |
| oauth2-proxy "cookie_secret must be 16, 24, or 32 bytes" | Longitud del secreto incorrecta | `openssl rand -hex 16` |
| Una petición anónima llega a una API protegida | Ruta sin token no va a oauth2-proxy, o `present: true` en la ruta 1 | Patrón de §7.6 |
| Cambio manual revertido | Esperado (self-heal) | Hacer el cambio en Git |
| GitLab "422: Sign-in using CopernicusLAC auth failed … already been taken" | Usuario creado en el primer login, aún pendiente de aprobación | Aprobarlo (Admin → Users → Pending approval) |
| `git push` rechazado "not allowed to push code to protected branches" | El usuario no es Maintainer del proyecto (ser admin de la instancia no basta) | Rol Maintainer u Owner en el grupo `copernicuslac`, o merge request |
| La Release mantiene el repo de chart antiguo tras cambiar la fuente | provider-helm solo hace upgrade cuando cambian versión del chart o values | Esperado: la fuente nueva se usa en el siguiente upgrade; verificar el pull con `helm registry login` + `helm pull` |
| Push a Harbor falla: "trying to reuse blob … 500 Internal Server Error" | StorageGRID 12.0.0 devuelve 403 en vez de 404 en keys inexistentes (log del registry `s3aws: AccessDenied`) | Upgrade de StorageGRID (TBC-1); comprobar con `s3cmd info` sobre una key inexistente (§3.5.2) |

### 11.4 Backup y recuperación — **TBV por IFX** (sección vacía en el documento)
### 11.5 Disaster recovery — **TBV por IFX** (sección vacía en el documento)

Lo que el documento sí dice, disperso, y aplica a backup/DR:
- DR sigue la misma secuencia de §4.5.
- Imprescindibles fuera de Git: claves age (incl. la clave DR del equipo), unseal keys y root token de Vault, contraseñas de servicios gestionados.
- `gitlab-rails-secret` exportado a SOPS: sin él, restaurar la BD de GitLab es inútil.
- Backup de GitLab antes de upgrades: `backup-utility` en el toolbox (bucket `copernicuslac-gitlab-backups`, versionado).
- PostgreSQL: backups en repositorio del proveedor, 30 días (Fig. 6); los gestiona el equipo DBaaS (IFX).
- Vault reconstruido con storage vacío: `init.sh` → `unseal.sh` → `configure.sh`, y **re-introducir todos los valores del Anexo C**. Snapshots de Raft: pendiente.
- Crossplane antes de que Harbor vuelva: fuentes upstream comentadas en `crossplane-packages/values.yaml`.
- Harbor seed sin `cr.` accesible: modo port-forward automático.
- Tras DR hay que re-entrar: port-forward de GitLab (`8181`) para subir el repo.

---

## 12. Estado del despliegue y puntos abiertos (§12)

### 12.1 Estado por componente (23-oct-2026, Tabla 58)

| Tier / capa | Componente | Estado | Siguiente acción |
|---|---|---|---|
| T1 | Argo CD, cert-manager, Contour, Valkey ×2 | Deployed | — |
| T1 | GitLab | Deployed | Publicar `registry.` (Certificate + HTTPProxy) si se necesita el container registry de GitLab |
| T1 | Harbor | Deployed | Copiar las imágenes de mate-api tras el upgrade de StorageGRID (TBC-1) |
| T2 | Crossplane, providers | Deployed | — |
| 10 | Vault, ESO, ClusterSecretStore | Deployed | Snapshots de Raft |
| 20 | Keycloak | Deployed | Clients y grupos de los servicios (processing, Portal…) |
| 20 | OPA | Deployed | — |
| 30 | Knative | Deployed | — |
| 40 | Strimzi, Kafka, Kafka UI | Deployed | — |
| 40 | STAC API discover/main | Deployed | Test de login por navegador con grupos |
| 40 | TiTiler-pgSTAC | To deploy | Chart, DNS `view.`, usuario S3 de solo lectura, client Keycloak, secretos en Vault |
| 40 | Geobrowser | To deploy | Chart, DNS, client Keycloak público, decisión del client id (§8.5) |
| 40 | STAC Browser, results catalogs (6) | To deploy | Patrón de rutas de §7.6 |
| 50 | Argo Workflows, Argo Events, event bus, webhook | Deployed | SSO en lugar del modo server |
| 50 | Processing API | Deployed | Test end-to-end con token (grupos/clients de Keycloak) |
| 50 | CWL runner templates | To deploy | Imágenes en Harbor, secretos en Vault |
| 60 | Portal, App Hub, Drive | To deploy | BD, buckets, clients de Keycloak, correcciones del capítulo 10 |
| 70 | Composition calrimate, application packages | To deploy | Paquete `function-calrimate`, CWL runner |

### 12.2 Puntos abiertos (Tabla 59)

| Ref. | Punto | Responsable | Prioridad |
|---|---|---|---|
| **TBC-1** | StorageGRID 12.0.0 devuelve 403 en vez de 404 en objetos inexistentes (issue conocido de NetApp, corregido después de 12.0.0.4): actualizar el grid; bloquea los pushes de imágenes a Harbor | IFX | High |
| **TBC-2** | `effective_cache_size` 16 GB en nodo01 y 8 GB en nodo02: alinear ambos nodos (solo reload) | IFX | Low |
| **TBC-3** | Grupos y clients de Keycloak para procesamiento (`processing-coplac`, `results-coplac`), grupos de catálogo, `Operator`, `writers-processing`; tests end-to-end con tokens reales | Equipo de plataforma | High |
| **TBC-4** | Geobrowser: client id (`processing-coplac` vs añadir processing a OPA), hostname | Plataforma / equipo de procesamiento | Medium |
| **TBC-5** | TiTiler: buckets a leer, imagen y tamaño de Redis | Equipo de plataforma | Medium |
| **TBC-6** | Labels y taints de los pools de processing y storage en los machine pools de Rancher | Equipo de plataforma | Medium |
| **TBC-7** | Relay SMTP para Keycloak (forgot password, verify e-mail) y Drive | AIG | Low |
| **TBC-8** | Listener plain de Kafka sin autenticación: SCRAM y autorización en el listener TLS, un KafkaUser por servicio con contraseña en Vault, luego quitar el listener plain | Equipo de plataforma | Medium |

### 12.3 Ajustes temporales a revertir (Tabla 60)

Cada uno está marcado `TEMPORARY` en el repo. Revertir en el commit que siga al evento indicado.

| Ajuste | Revertir cuando | Objetivo |
|---|---|---|
| Imágenes desde `cr.terradue.com` (`cr-terradue-pull` en `processing`, `mate-api`) | Imágenes copiadas a Harbor (tras el upgrade de StorageGRID, TBC-1) | Pull secret de Harbor |
| Argo Workflows authModes server + client | Client Keycloak `argo-workflows` | sso + client (archivos `.disabled`) |
| Listener plain de Kafka sin autenticación (puerto 9092) | KafkaUsers y clientes en SCRAM sobre TLS (TBC-8) | Solo listener TLS con SCRAM |

---

## 13. Anexo A — Endpoints públicos (Tabla 61)

| Host (`*.copernicuslac.aig.gob.pa`) | Servicio | Namespace | Certificate | Protección | Estado |
|---|---|---|---|---|---|
| `iam` | Keycloak (realm `CopernicusLAC-Platform`) | iam | `iam-tls` | `/admin` y `/realms/master` → 404 | Live |
| `processing` | Processing API | mate-api | `processing-tls` | OPA | Live |
| `discover` | STAC API (catálogo `/main`) | catalog | `discover-tls` | OPA + oauth2-proxy | Live |
| `git` | GitLab | gitlab-system | `gitlab-tls` | Login de GitLab, SSO Keycloak | Live |
| `cr` | Harbor | harbor-system | `harbor-tls` | Login de Harbor | Live |
| `view` | TiTiler | catalog | `view-tls` | OPA + oauth2-proxy | To deploy |
| `dashboards` | Geobrowser | geobrowser | por crear | Keycloak en el navegador | To deploy |
| `results`, `download` | Results catalogs, descargas | — | — | OPA + oauth2-proxy | To deploy |
| `www`, `apps`, `hub`, `drive` | Portal, App Hub, Drive | — | — | Keycloak | To deploy |

## 14. Anexo C — Rutas de Vault y ExternalSecrets (Tabla 63)

Checklist de los secretos Tier 3 (KV v2, mount `secrets/`). Cada valor debe existir **antes** de sincronizar su capa, y debe re-introducirse si Vault se reconstruye con storage vacío.

| Ruta de Vault | Keys | ExternalSecret (namespace) | Usado por |
|---|---|---|---|
| `iam/keycloak-external-db` | password | `keycloak-external-db` (iam) | BD de Keycloak |
| `iam/keycloak-admin` | username, password | eliminado tras el primer arranque | Bootstrap admin (solo instalación nueva) |
| `registry/cr-terradue` | dockerconfigjson | `cr-terradue-pull` (processing, mate-api) | Pulls de imágenes TEMPORARY |
| `processing/argo-artifacts` | accesskey, secretkey | `argo-artifacts-creds` (processing) | Artifacts de Argo (usuario `argowf`) |
| `processing/argo-postgres` | username, password | `argo-postgres-config` (processing) | Archivo de Argo |
| `processing/argo-sso` | client-id, client-secret | `argo-workflows-sso-secret` (`.disabled`) | SSO de Argo (objetivo) |
| `catalog/pgstac` | username, password | `external-secret-pgstac` → `pgstac-secret` (catalog) | STAC API (TiTiler planificado) |
| `catalog/oauth2-proxy` | `OAUTH2_PROXY_CLIENT_ID`, `_CLIENT_SECRET`, `_COOKIE_SECRET` | `oauth2-proxy-client-secret-main` (catalog) | oauth2-proxy de discover |
| `catalog/titiler-s3`, `titiler-redis`, `oauth2-proxy-view` | — | planificado | TiTiler |

```bash
# escribir un dockerconfigjson sin exponer la contraseña (funciona desde zsh)
bash -c '
read -rp "registry user: " U </dev/tty; read -rsp "password: " P </dev/tty; echo
kubectl create secret docker-registry x --docker-server=cr.terradue.com --docker-username="$U" \
  --docker-password="$P" --dry-run=client -o jsonpath="{.data.\.dockerconfigjson}" | base64 -d \
  | vault kv put secrets/registry/cr-terradue dockerconfigjson=-'

# comprobar todas las rutas de una capa
for k in processing/argo-postgres processing/argo-artifacts registry/cr-terradue; do
  printf '%-28s ' $k
  out=$(vault kv get -format=json secrets/$k 2>&1) \
     && echo "$out" | jq -c '.data.data | keys' || echo "MISSING: ${out%%$'\n'*}"
done
```

## 15. Anexo B — Cambios respecto a la issue anterior (Tabla 62)

| Antes | Issue 2.2 | Razón |
|---|---|---|
| Describe el clúster observado en septiembre de 2026 y un objetivo | Describe la plataforma reconstruida en octubre de 2026; todos los procedimientos ejecutados | Traspaso a operaciones |
| Tier 1: Argo CD y GitLab con Helm; Tier 2: Crossplane como Applications de Argo CD | Tier 1: Argo CD (helmfile), cert-manager, Contour, Valkey ×2, GitLab, Harbor como Applications con sync manual; Tier 2: Crossplane solo con helmfile | Radio de impacto, sin dependencia circular |
| `platform/` agrupado por función, una Application | Capas 10–70, una Application por capa, sync-wave = número de capa | Orden, aislamiento |
| Releases en namespace `default` | Namespace `platform` | Un único lugar para Tier 3 |
| Secretos del bootstrap creados a mano | SOPS + age en Git, entrega de claves fuera de banda | Bootstrap reproducible |
| Registry `cr.copernicuslac` con paquetes no resolubles | Harbor en Tier 1 con seed scriptado y robot accounts; paquetes y charts servidos desde Harbor | Plataforma autocontenida |
| Crossplane 2.3.2, provider-kubernetes v1.2.1, provider-helm `:test` | Crossplane 2.4.2, v1.4.1, provider-helm v1.0.0 | Fijado, actual |
| Vault 1 pod, unseal TBC | Vault HA Raft 3 pods, init/unseal/configure scriptados, claves en custodia | Disponibilidad, operabilidad |
| Keycloak 26.5, acceso superuser a la BD | Keycloak 26.8.1, rol dedicado, admin no publicado, realm endurecido (OTP) | Seguridad |
| OPA preparado, no conectado | OPA en hosts de processing y catálogo, oauth2-proxy, patrón de rutas | Seguridad |
| Knative desde manifiestos | Knative Operator + KnativeServing | GitOps |
| Kafka en `longhorn`, solo topics declarados | Kafka en `longhorn-processing`, auto-creación para topics de eventos | Capacidad, topics dinámicos |
| Argo en `processing` | Release `argo-workflows`, namespace de API `mate-api`, archivo `argowf` | Nombres limpios |
| Servicios STAC como instalaciones manuales | STAC API como Release, procedimiento pgSTAC 0.9.12 | GitOps |
| Issues conocidos del clúster antiguo | Estado de despliegue, puntos abiertos, ajustes temporales | Lista de trabajo |

---

## 16. Índices de consulta rápida

### 16.1 Namespaces

| Namespace | Qué contiene |
|---|---|
| `argocd` | Argo CD |
| `cert-manager` | cert-manager |
| `contour-external`, `contour-internal` | Contour + Envoy |
| `gitlab-system` | GitLab + su Valkey |
| `harbor-system` | Harbor + su Valkey |
| `crossplane-system` | Crossplane, providers (y composition calrimate, futura) |
| `platform` | **Todas** las Releases y Objects de Tier 3 + ProviderConfigs + Secret `helm-repo-harbor` |
| `secret-management` | Vault |
| `eso` | External Secrets Operator |
| `iam` | Keycloak |
| `opa` | OPA |
| `knative-operator`, `knative-serving` | Knative |
| `kafka-operator`, `kafka`, `kafka-ui` | Strimzi, clúster Kafka, Kafka UI |
| `catalog` | STAC API, oauth2-proxy (TiTiler, STAC Browser, futuros) |
| `geobrowser` | Geobrowser (futuro) |
| `processing` | Argo Workflows, Argo Events, EventBus, webhook, workflows |
| `mate-api` | Processing API (10 ksvc) |
| `portal`, `app-hub`, `drive` | Capa 60 (futuro) |
| `kube-system`, `longhorn-system`, `cattle-monitoring-system` | Tier 0 |

### 16.2 Services y endpoints internos

| Qué | Dirección |
|---|---|
| GitLab webservice | `copernicuslac-gitlab-webservice-default.gitlab-system.svc:8181` |
| Valkey de GitLab (HAProxy) | `gitlab-valkey-haproxy` (gitlab-system) |
| Harbor | `svc/harbor` (harbor-system), puerto 80 |
| Vault (líder) | `http://copernicuslac-vault-active.secret-management:8200` |
| Keycloak | `svc/iam-keycloakx-http` (iam), puerto 80; management 9000 |
| OPA ext_authz | ExtensionService `opa/opa-authz`, gRPC 9191 |
| Kafka bootstrap | `copernicuslac-kafka-kafka-bootstrap.kafka:9092` (plain) / `:9093` (tls) |
| Kafka UI | `svc/copernicuslac-kafka-ui` (kafka-ui), puerto 80 |
| Argo Workflows server | `argo-workflows-server.processing:2746` |
| CloudEvents webhook | `http://cloud-events-webhook-eventsource-svc.processing.svc.cluster.local:12000/cloud-events` |
| STAC API (tras nginx stripper) | `nginx-stripper-catalog-main` (catalog), puerto 80 |
| oauth2-proxy del catálogo | `oauth2-proxy-main` (catalog), puerto 80 |
| PostgreSQL | `10.0.0.3` (primary), `10.0.0.4` (réplica) |
| S3 | `https://svr-cop-s3-pan.ifxcloud.com:10443` |

### 16.3 Comandos más usados

```bash
# Estado general
cd bootstrap && ./bootstrap.sh status
kubectl -n argocd get applications
kubectl -n platform get releases.helm.m.terradue.crossplane.io,objects.kubernetes.m.crossplane.io

# Diagnóstico de una Release
kubectl -n platform describe releases.helm.m.terradue.crossplane.io <name> | tail -30

# Forzar reconciliación de una Release (si no, hasta 10 min)
kubectl -n platform annotate releases.helm.m.terradue.crossplane.io <name> \
  reconcile-at="$(date +%s)" --overwrite

# Forzar refresh de un ExternalSecret / revalidar el store
kubectl -n <ns> annotate externalsecret <name> force-sync="$(date +%s)" --overwrite

# Argo CD CLI en modo core
kubectl config set-context --current --namespace argocd
argocd --core app get <app>

# Vault
kubectl -n secret-management exec copernicuslac-vault-0 -- vault status
ops/vault/unseal.sh        # tras cualquier reinicio de pod de Vault

# Tier 2
helmfile -l name=<release> diff && helmfile -l name=<release> apply

# Check SOPS antes de commit (no debe imprimir nada)
grep -L 'ENC\[' bootstrap/secrets/*.sops.yaml

# Conexiones PostgreSQL
# SELECT count(*), current_setting('max_connections') FROM pg_stat_activity;
```

### 16.4 Quién es dueño de qué

| Actor | Responsabilidad |
|---|---|
| **Terradue** | Autor de la guía y del repo; fork de provider-helm; charts opa, mate-api, seda; soporte (copernicuslac-support@terradue.com) |
| **IFX (ifxcloud)** | Proveedor de infraestructura: Rancher, VMs, PostgreSQL gestionado (DBaaS: `postgresql.conf`, reinicios, backups), StorageGRID, DNS/LB; TBC-1, TBC-2; validación de backup/DR (§11.4–11.5) |
| **AIG** | Administradores y equipo de plataforma/operaciones que reciben el traspaso; TBC-7 (SMTP) |
| **Equipo de plataforma** | TBC-3, 4, 5, 6, 8 |
| **ESA / DG-INTPA / Gobierno de Panamá** | Promotores de la iniciativa |
