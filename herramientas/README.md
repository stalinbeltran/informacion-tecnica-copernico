# Herramientas del rol — Administrador de Middleware CopernicusLAC

Una carpeta, un archivo por herramienta. Cada archivo es **autocontenido**: incluye lo
que la plataforma hace con esa herramienta, los datos reales (endpoints, cifras, JSON de
ejemplo, cláusulas del pliego), el laboratorio, las averías a provocar y el criterio de
dominio. No necesitas abrir D1/D2/D3 ni el pliego para estudiar con ellos; las citas están
para cuando quieras el texto original.

**Criterio de inclusión:** solo herramientas que *tú* operas. Las piezas del middleware que
administra el proveedor de infraestructura (plano de control de Kubernetes, motor
PostgreSQL, servicio S3, balanceador, red del clúster) aparecen únicamente como frontera o
vocabulario, nunca como materia de estudio operativo.

---

## Cómo usar esta carpeta

**Para estudiar:** abre el archivo, ve a *Qué debes saber* y empieza por el nivel que te
falte. Cada archivo termina con un laboratorio ejecutable y un criterio de dominio
verificable.

**Para consultarme:** dime el nombre de la herramienta ("guíame con Argo Events",
"¿qué me falta de S3?") y yo tomo el archivo correspondiente como base: te digo qué
estudiar, en qué orden, y te acompaño en el laboratorio y en el diagnóstico. Si me pides
un plan de varias herramientas, uso el orden de prioridad de abajo.

**Para mantener:** cuando aprendas algo que el archivo no dice —una versión real, un
comando que resolvió un incidente, una respuesta de ESA— añádelo a la sección
*Bitácora / hallazgos* del archivo. Estos documentos deben envejecer contigo, no quedar
congelados en la fecha en que se escribieron.

---

## Niveles

| Nivel | Nombre | Qué significa |
|---|---|---|
| **C** | Conceptual | Puedo explicarlo y decidir a quién escalar |
| **O** | Operativo | Lo hago solo, bajo presión, sin guía |
| **E** | Experto | Lo diseño, lo optimizo y lo enseño |

`C→O` no es un nivel intermedio: es una trayectoria. Empieza conceptual, pasa a operativo
cuando lo toques en producción.

---

## Índice por prioridad

### Prioridad 1 — Núcleo diario. Es lo primero que se rompe.

| Archivo | Herramienta | Nivel |
|---|---|---|
| [01-kubernetes.md](01-kubernetes.md) | Kubernetes (workloads, config, storage, red de aplicación) | E |
| [02-helm.md](02-helm.md) | Helm | E |
| [03-prometheus-grafana.md](03-prometheus-grafana.md) | Prometheus + Grafana | E |
| [04-fundamentos-linux-git-yaml.md](04-fundamentos-linux-git-yaml.md) | Linux, Git, YAML | O–E |

### Prioridad 2 — Alto y desatendido. Nadie más los administra.

El análisis de perfil de ESA marca estas áreas como **no cubiertas** por el contrato del
proveedor. Aquí no hay red debajo.

| Archivo | Herramienta | Nivel |
|---|---|---|
| [05-stac-pgstac-stac-fastapi.md](05-stac-pgstac-stac-fastapi.md) | STAC + PgSTAC + stac-fastapi | E |
| [06-s3-minio.md](06-s3-minio.md) | S3 / MinIO — políticas, lifecycle, URLs firmadas | E |
| [07-argo-workflows.md](07-argo-workflows.md) | Argo Workflows | O |
| [08-argo-events.md](08-argo-events.md) | Argo Events | O |
| [09-keycloak.md](09-keycloak.md) | Keycloak / OIDC / JWT | O |
| [10-harbor.md](10-harbor.md) | Harbor | O |
| [11-gitlab.md](11-gitlab.md) | GitLab (repos + CI/CD) | O |

### Prioridad 3 — Medio. Los tocas al operar workspaces, despliegue y visualización.

| Archivo | Herramienta | Nivel |
|---|---|---|
| [12-argocd.md](12-argocd.md) | ArgoCD | O |
| [13-crossplane.md](13-crossplane.md) | Crossplane | C→O |
| [14-external-secrets-operator.md](14-external-secrets-operator.md) | External Secrets Operator | O |
| [15-cwl-calrissian.md](15-cwl-calrissian.md) | CWL + cwltool + Calrissian | O |
| [16-titiler-cog.md](16-titiler-cog.md) | Titiler + COG + WMTS/XYZ | O |
| [17-docker.md](17-docker.md) | Docker / podman / OCI | O |
| [18-ingress-tls-cert-manager.md](18-ingress-tls-cert-manager.md) | Ingress NGINX + cert-manager + NetworkPolicy | O |
| [19-postgresql-postgis.md](19-postgresql-postgis.md) | PostgreSQL + PostGIS (operación) | O |

### Prioridad 4 — Contexto. Para dialogar y escalar, no para operar.

| Archivo | Herramienta | Nivel |
|---|---|---|
| [20-kafka.md](20-kafka.md) | Apache Kafka | C→O |
| [21-zoo-ogc-api-processes.md](21-zoo-ogc-api-processes.md) | ZOO Project / OGC API – Processes | C |

---

## La frontera, en una tabla

La tabla que decide de quién es cada incidente. Vale para todos los archivos de esta carpeta.

| Materia | Proveedor de infraestructura | Tú |
|---|---|---|
| Clúster K8s | Despliegue, parcheo, upgrades, HA, nodos maestros, ETCD y su respaldo, red interna, autoescalado | Nada del plano de control |
| Objetos de aplicación | — | Deployments, StatefulSets, Jobs, CronJobs, ConfigMaps, Secrets, rollouts/rollbacks |
| StorageClass | Provisión y gestión | Consumo: PVC, diagnóstico de `Pending`, dimensionamiento lógico |
| Ingress | Ingress Controller y su operación | Recursos `Ingress` del Middleware y certificados TLS de aplicación |
| RBAC | RBAC del clúster, aislamiento de namespaces, autenticación | RBAC lógico dentro de tus namespaces, cuotas, NetworkPolicies de aplicación |
| PostgreSQL | Motor, HA, parches, respaldos automáticos, escalado, cifrado | Conectividad, salud, desempeño básico, **verificación** de respaldos, pruebas de restauración, coordinación |
| Object storage S3 | Servicio, capacidad, latencias | **Buckets, políticas, integridad, uso y desempeño** — *no cubierto* por el contrato |
| Dominios funcionales (ingesta, catálogo, workflows, registry, workspace) | No incluido | **Enteramente tuyo** |
| Gestión de cambios | Cambios de infraestructura | Cambios en el Middleware |
| Optimización del Middleware | No incluido | **Tuyo**: tuning, backpressure, sizing avanzado |
| Observabilidad | Métricas, logs y eventos del clúster; monitoreo 8x5 | Observabilidad del Middleware, correlación y diagnóstico, monitoreo continuo |
| Incidentes | Infraestructura, SLA 24/7 | Segundo nivel funcional, post-incidente, acciones correctivas |

**Regla práctica:** si el síntoma desaparece reinstalando o reconfigurando un objeto dentro
de tu namespace, es tuyo. Si persiste con el objeto correcto y el fallo está por debajo del
`kubelet`, del motor de base de datos o del servicio S3, es del proveedor — y entonces tu
trabajo es la evidencia: qué probaste, qué observaste, a qué hora, con qué comando.

---

## Los números, en un solo lugar

Cada archivo repite los que le competen, pero esta es la referencia común.

**Compromisos de la plataforma (D1):**

- Disponibilidad **99,5 % anual** (≈44 h/año). MTTR objetivo **< 1 h**.
- Throughput de ingesta/procesamiento **≥ 0,350 TB/h**, picos **3,5 TB/h**.
- Latencia extremo a extremo **< 1 h** productos estándar; **≤ 5 min** flujos en tiempo real.
- **3.000 usuarios concurrentes**; respuesta media **< 5 s**, pico **≤ 7,5 s**; utilización objetivo **50–70 %**.
- KPIs: disponibilidad del sistema (ingesta + catálogo + acceso), *Data Ingestion Timeliness*, capacidad de usuarios, completitud de la oferta de datos.

**Compromisos del proveedor (pliego §8.5.17):**

| Severidad | Respuesta máx. | Resolución máx. |
|---|---|---|
| Crítico | 15 min | 2 h |
| Alto | 1 h | 4 h |
| Medio | 2 h | 8 h |
| Normal | 4 h | 24 h |

- Aplican **24/7**. Disponibilidad **99,95 % mensual** (≈43,2 min), excluyendo mantenimientos avisados con ≥ 48 h.
- **RTO < 24 h**, **RPO < 1 h**. Penalidad 4 % de la mensualidad ÷ 30 por día de afectación.
- Monitoreo **8x5** de SO, Kubernetes y aplicaciones. Escalamiento en 3 niveles.

**Infraestructura contratada (Anexo I):** K8s administrado HA hasta 500 nodos; 10 VM 4/16 y
15 VM 8/32 para componentes; 8 VM 8/32, 8 VM 16/64 y 4 VM 32/128 para procesamiento; LB HA
≥ 1 Gbps (25.000 RPS pico, 10.000 conexiones); 2 PostgreSQL HA 16 vCPU/64 GB/800 GB
(PostgreSQL ≥ 13, PostGIS ≥ 3); 25 TB SSD para PVC; total 496 vCPU, 1.984 GB RAM.
Object storage 2 PB caliente + 750 TB frío, latencias **100 ms lectura / 200 ms escritura**.
Objetos 100 MB–1 GB (máx. 8 GB), lecturas parciales 16 KB–1 MB. Rotación anual caliente→frío.
Conectividad 3 Gbps a Europa, ≥ 1 Gbps de salida. Acceso a las APIs de K8s y S3 por **VPN**.

**Diferencias D1 ↔ pliego que debes conocer antes de una reunión con ESA:**

| Parámetro | D1 (especificación ESA) | Pliego (contratado) |
|---|---|---|
| Nodos K8s | hasta 1000 | hasta 500 |
| Object storage | 2 PB + 20 PB frío (mín. 22 PB) | 2 PB + 750 TB frío |
| Balanceador | ≥ 4 Gbps | ≥ 1 Gbps |
| Disponibilidad | 99,5 % anual, MTTR < 1 h | 99,95 % mensual |
| PostgreSQL | 4 instancias 16/64 | 2 instancias 16/64 |

---

## Los ocho componentes del Middleware y sus herramientas

| # | Componente | Herramientas | Archivos |
|---|---|---|---|
| 1 | Data Ingestion | Kafka, Argo Events, Argo Workflows, CWL, Python/GDAL, S3, STAC | 08, 20, 07, 15, 06, 05 |
| 2 | Data Discovery and Access | PostgreSQL + PostGIS + PgSTAC, stac-fastapi, Titiler, servicio de URLs firmadas, S3 | 19, 05, 16, 06 |
| 3 | Data Processing | Argo Workflows, Argo Events, Calrissian, ZOO Project, Docker, K8s | 07, 08, 15, 21, 17, 01 |
| 4 | Application Registry | GitLab, Harbor, PostgreSQL | 11, 10, 19 |
| 5 | Front-end Services | React/Angular, Leaflet/OpenLayers, JupyterHub, VSCode, GitLab CI/CD | 11, 16 |
| 6 | User Workspace | Namespace K8s, Crossplane, ArgoCD, ESO, GitLab, Harbor, API REST | 01, 13, 12, 14, 11, 10 |
| 7 | Authentication and Authorization | Keycloak, OAuth2/OIDC, JWT, LDAP | 09 |
| 8 | Resource Management | Crossplane, Helm, ESO, Prometheus/Grafana | 13, 02, 14, 03 |

---

## Lo que NO está en esta carpeta, y por qué

Instalación y upgrade del clúster, `etcd`, `kubeadm`, administración de nodos y del sistema
operativo, CNI y red de bajo nivel, hipervisores, tuning interno del motor PostgreSQL,
ejecución de respaldos, hardening físico del almacenamiento, diseño de la topología de red
del proveedor, certificaciones tipo CKA/CKS completas.

Cuesta tiempo y no es tuyo. Necesitas el **vocabulario** de todo esto para dialogar y para
escalar bien —nivel conceptual, no operativo— y ese vocabulario está repartido en las
secciones *Frontera* de cada archivo.

---

*Fuente de la selección y los niveles: `Guia_Estudio_Administrador_Middleware_Copernicus.md`
(§11 matriz de competencias, §12.1 prioridades, §16 catálogo de averías). Fuente de los
datos técnicos: D1 v1.4, D2 v1.3, D3 v1.3, pliego Lic. 2025-1-46-01-08-LP-000003, TDR y
análisis de perfil ESA — todos navegables en [../web/index.html](../web/index.html).*
