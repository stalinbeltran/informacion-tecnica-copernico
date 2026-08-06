# Guía de estudio — Administrador de Middleware, Plataforma Copernicus LAC Panamá

**Para:** Stalin J. Beltrán · **Rol objetivo:** Administrador del Middleware (consultoría individual AIG, 19 meses)
**Fuentes:** TDR de la consultoría · Perfil ESA y análisis de brechas · Pliego de cargos de la infraestructura (Lic. 2025‑1‑46‑01‑08‑LP‑000003) · D1 Centre Specification v1.4 · D2 System Architecture v1.3 · D3 Interface Control v1.3
**Fecha de redacción:** 6 de agosto de 2026

---

## Cómo usar este documento

Está dividido en cuatro partes con propósitos distintos:

| Parte | Qué contiene | Cómo se usa |
|---|---|---|
| I. El encargo | Qué firmaste, qué te van a exigir y dónde termina tu responsabilidad | Se lee una vez completa y se vuelve a ella al preparar cada producto |
| II. La plataforma | Qué es el Middleware, componente por componente, con sus interfaces y sus números | Es material de estudio y de consulta permanente |
| III. Mapa de competencias | Qué debes saber, a qué nivel, y con qué criterio se comprueba | Es tu diagnóstico y tu lista de verificación |
| IV. Plan de aprendizaje haciendo | Laboratorio, ruta de práctica, simulacros y evaluación | Es lo que ejecutas semana a semana |

La documentación original está navegable en [web/index.html](web/index.html) (nivel 1 → documento, nivel 4 → texto íntegro con figuras y tablas). Este documento cita las secciones para que puedas ir a la fuente cuando necesites el detalle exacto.

Existe además [Plan_Preparacion_Tecnica_Middleware_Copernicus.md](Plan_Preparacion_Tecnica_Middleware_Copernicus.md), escrito para preparar a un *equipo* de la AIG antes del entrenamiento de ESA. Esta guía es distinta: es personal, asume que tú eres el responsable técnico del entregable, y **corrige el peso de varios temas** que aquel plan minimiza (ver §12.1).

---

# PARTE I — EL ENCARGO

## 1. Contexto y actores

Panamá alberga el Centro Copernicus LAC. La ESA aporta el **Middleware**: el software central que ingiere, cataloga, procesa, publica y da acceso a datos de observación de la Tierra (EO). Ese software corre sobre Kubernetes; Kubernetes lo entrega un proveedor comercial como servicio administrado, contratado por separado en la licitación de infraestructura.

Tú operas el software. No operas la infraestructura.

| Actor | Qué aporta | Tu relación con él |
|---|---|---|
| **ESA / Terradue** | El Middleware, su arquitectura (D2), sus interfaces (D3), los requisitos del Centro (D1) y la capacitación inicial | Punto focal técnico: recibes capacitación, escalas defectos funcionales, validas alineamiento con estándares |
| **Proveedor de infraestructura** | IaaS, KaaS (Kubernetes administrado), DBaaS (PostgreSQL HA), almacenamiento S3, balanceador, conectividad 3 Gbps, administración operativa con monitoreo 8x5 | Coordinas incidentes y cambios; **validas mensualmente sus entregables y su SLA** |
| **AIG (Dirección de Innovación Gubernamental)** | Supervisión de la consultoría, aprobación de productos, acceso e información | Reportas, entregas productos, conduces las reuniones técnicas operativas |
| **Instituciones usuarias** | Consumen datos y servicios geoespaciales | Soporte técnico especializado cuando se requiera |
| **Recurso designado por AIG** | Persona a la que transfieres conocimiento desde la Fase 3 | Shadowing, sesiones prácticas, operación conjunta |

Financiamiento BID (préstamo 5501/OC‑PN, Programa Panamá Digital). Esto importa: obliga a trazabilidad documental, conservación de registros y cumplimiento de las prácticas prohibidas del Banco.

## 2. El rol: objetivo, alcance y frontera

**Objetivo (TDR, objetivo general):** asegurar la operación, supervisión técnica, configuración lógica y continuidad operativa del Middleware desplegado sobre KaaS, DBaaS y almacenamiento de objetos, **a nivel de aplicación y runtime**, ejerciendo el liderazgo técnico y actuando como referente principal ante AIG, ESA y el proveedor.

**Alcance general (TDR §VI y Perfil ESA):**

1. Operar el Middleware CopernicusLAC a nivel de aplicación y runtime.
2. Configurar y mantener componentes lógicos sobre Kubernetes, excluyendo la administración del clúster base.
3. Diagnosticar incidentes funcionales y técnicos del Middleware.
4. Asegurar el correcto funcionamiento de los servicios KaaS, DBaaS y de almacenamiento.
5. Coordinar incidentes, cambios y mejoras con el proveedor y con ESA.
6. Documentar configuraciones, procedimientos y eventos operativos.
7. Validar técnicamente los entregables del proveedor (informe **mensual** de cumplimiento de SLA, disponibilidad, conectividad, incidentes y métricas).
8. Conducir las reuniones técnicas operativas con registro formal de acuerdos.

### 2.1 La frontera, en una tabla

Esta es la tabla más importante de la guía. Equivocarse de lado cuesta tiempo, credibilidad y SLA.

| Materia | Proveedor (pliego §8.5.3, §8.5.7, §8.5.8) | Tú (TDR §VI, Perfil ESA) |
|---|---|---|
| Clúster K8s | Despliegue, parcheo, upgrades, HA, nodos maestros, ETCD y su respaldo, red interna del clúster, autoescalado | Nada del plano de control |
| Objetos de aplicación | — | Deployments, StatefulSets, Jobs, CronJobs, ConfigMaps, Secrets, rollouts/rollbacks |
| StorageClass | Provisión y gestión | Consumo: PVC, diagnóstico de `Pending`, dimensionamiento lógico |
| Ingress | Ingress Controller y su operación | Recursos `Ingress` del Middleware y certificados TLS de aplicación |
| RBAC | RBAC del clúster, aislamiento de namespaces, autenticación | RBAC lógico dentro de tus namespaces, cuotas, NetworkPolicies de aplicación |
| PostgreSQL | Motor, HA, parches, respaldos automáticos, escalado, cifrado | Conectividad, salud, desempeño básico, **verificación** de respaldos, pruebas de restauración cuando estén definidas, coordinación |
| Object storage S3 | Servicio de almacenamiento, capacidad, latencias | **Buckets, políticas de acceso, integridad, uso y desempeño** — el análisis ESA marca esta área como *no cubierta* por el contrato del proveedor |
| Dominios funcionales (ingesta, catálogo, workflows, registry, workspace) | No incluido | **Enteramente tuyo** |
| Gestión de cambios funcional | Cambios de infraestructura | Cambios en el Middleware |
| Optimización del Middleware | No incluido | **Tuyo**: tuning de desempeño, backpressure, sizing avanzado |
| Observabilidad | Métricas, logs y eventos del clúster; monitoreo 8x5 | Observabilidad del Middleware, correlación y diagnóstico, monitoreo continuo |
| Incidentes | Operación de incidentes de infraestructura, SLA 24/7 | Segundo nivel funcional, análisis post‑incidente, acciones correctivas |

**Regla práctica para clasificar un incidente:** si el síntoma desaparece reinstalando o reconfigurando un objeto dentro de tu namespace, es tuyo. Si persiste con el objeto correcto y el fallo está por debajo del `kubelet`, del motor de base de datos o del servicio S3, es del proveedor — y entonces tu trabajo es la evidencia: qué probaste, qué observaste, a qué hora, con qué comando.

### 2.2 Lo que el contrato del proveedor sí te habilita a pedir

El pliego (§8.5.16) enumera funciones mínimas del servicio administrado sobre KaaS que **el proveedor debe poder ejecutar o habilitar**: configurar StorageClasses, desplegar Ingresses específicos, etiquetar nodos, desplegar custom controllers, editar deployments, conectarse a pods, revisar eventos y métricas para diagnóstico. Y sobre DBaaS: seguimiento técnico, gestión de accesos administrativos, coordinación ante anomalías detectadas por el middleware, verificación periódica de backups, validación de HA funcional, supervisión de recursos y documentación.

Conócelas de memoria: son tu palanca cuando necesitas algo que no puedes hacer tú.

## 3. Productos, calendario y qué habilidad exige cada uno

19 meses: 18 de ejecución técnica + 1 de cierre. Diez productos encadenados (cada plazo corre desde la aceptación del anterior).

| # | Producto | Hito | Capacidad técnica que realmente exige |
|---|---|---|---|
| 1 | Plan de trabajo, diagnóstico inicial y puesta en operación | 30 días | Inventariar servicios y dependencias en K8s; validar conectividad, accesos y disponibilidad; montar el repositorio documental |
| 2 | Operación inicial documentada — Fase 1 | 3 meses | Operar despliegues reales; validar conectividad con DBaaS y almacenamiento; levantar arquitectura lógica; primeros runbooks |
| 3 | Estabilización técnica — Fase 2 | 5 meses | Análisis de comportamiento, ajustes de configuración, validación de desempeño de servicios críticos |
| 4 | Transferencia técnica basada en operación real — Fase 3 | 7 meses | Enseñar haciendo: shadowing, casos prácticos, detección de brechas |
| 5 | Habilitación operativa y operación conjunta — Fase 4 | 9 meses | Autonomía parcial del recurso designado; gestión de incidentes documentada |
| 6 | Estandarización de procesos — Fase 5 | 11 meses | SOPs, gestión de incidentes/cambios/problemas, roles operativos, métricas de tiempos de atención |
| 7 | Optimización y mejora continua — Fase 6 | 13 meses | Análisis de tendencias, mejoras implementadas, lecciones aprendidas |
| 8 | Cumplimiento y fortalecimiento operativo — Fase 7 | 15 meses | Auditoría de uso de procedimientos, ajustes lógicos, arquitectura operativa actualizada |
| 9 | Madurez y sostenibilidad — Fase 8 | 17 meses | Indicadores operativos, informe de métricas, recomendaciones de sostenibilidad |
| 10 | Cierre contractual y transferencia final | 18 meses | Consolidación documental, transferencia final (mínimo 20 días calendario), informe acumulativo de validación de entregables del proveedor |

Elementos que se repiten en casi todos los productos y que conviene industrializar desde el día 1:

- **Registro de la operación del período** → bitácora estructurada, no memoria.
- **Repositorio documental** → wiki/Git con estructura fija desde el Producto 1.
- **Recibir y registrar las sesiones de capacitación de ESA** → un formato de acta por sesión, con dudas abiertas y compromisos.
- **Registro y seguimiento de acuerdos de reuniones técnicas** → minutas con identificador, responsable y fecha.
- **Informe mensual de validación del proveedor** → plantilla reutilizable con las métricas del SLA (§10).

**Entrega formal:** impreso y electrónico en formato Microsoft Office (Word/Excel/PowerPoint), en 2 USB a AIG/UCP, más los repositorios que indique la unidad gestora. Diseña la documentación para que exporte limpio a Word desde el principio.

## 4. Riesgos del encargo que debes tener presentes

1. **Brechas declaradas por el propio análisis de perfil.** ESA pide competencias que el contrato del proveedor no cubre: S3 (IAM, lifecycle, retención), los dominios funcionales de la plataforma, gestión avanzada de incidentes, gestión de cambios funcionales y optimización del Middleware. Ahí no hay red debajo: es tu responsabilidad directa.
2. **Dimensionamiento de esfuerzo.** El Anexo B de D1 estima para la operación del Centro ~3,5 FTE en operaciones e infraestructura, 2,0 FTE en soporte y usuarios, 0,5 en seguridad y 1,0 en formación/documentación durante los primeros 12–18 meses. Panamá cubre esto con servicio administrado del proveedor más esta consultoría. Consecuencia práctica: **prioriza y automatiza**; documenta lo que no alcances a hacer para que quede como riesgo registrado, no como omisión.
3. **Diferencias entre lo que D1 especifica y lo que el pliego contrata.** Verifícalas contra el contrato firmado antes de exigir nada:

   | Parámetro | D1 (especificación ESA) | Pliego (contratado) |
   |---|---|---|
   | Nodos del K8s administrado | hasta 1000 | hasta 500 (VMs) |
   | Object storage | 2 PB online + 20 PB frío (mín. 22 PB) | 2 PB acceso rápido + 750 TB frío |
   | Balanceador | ≥ 4 Gbps | ≥ 1 Gbps, HA en 2 zonas, 25.000 RPS pico, 10.000 conexiones |
   | Disponibilidad | 99,5 % anual (≈44 h/año), MTTR < 1 h | 99,95 % mensual (≈43,2 min/mes), excluyendo mantenimientos avisados con 48 h |
   | PostgreSQL | HA, 4 instancias 16 vCPU/64 GB | HA, 2 instancias 16 vCPU/64 GB, PostgreSQL ≥ 13 y PostGIS ≥ 3 (recomendado 16 / 3.5) |

   No son necesariamente errores —el pliego dimensiona la etapa inicial— pero son exactamente el tipo de cosa que debes saber antes de una reunión con ESA.
4. **Monitoreo del proveedor es 8x5; el SLA de incidentes es 24/7.** Hay una franja donde la detección depende de tu observabilidad y de tus alertas.
5. **Dependencia de la capacitación de ESA.** El TDR es explícito: la capacitación "no sustituye los conocimientos técnicos requeridos para el rol". Llegar con el terreno preparado es lo que convierte esas sesiones en transferencia real y no en presentaciones.

---

# PARTE II — LA PLATAFORMA

## 5. Visión general

El Middleware es una **PaaS cloud‑agnóstica para datos EO**, construida sobre Kubernetes, con arquitectura de microservicios y orientada a eventos. Ocho componentes (D2 §2.3 y §3):

| # | Componente | Función | Stack principal |
|---|---|---|---|
| 1 | **Data Ingestion** | Toma datos de fuentes externas (CDSE, Centro de datos en Chile), valida, cataloga y almacena | Kafka (bus de eventos), Argo Events, Argo Workflows, CWL, Python/GDAL, S3, STAC |
| 2 | **Data Discovery and Access** | Indexa metadatos y permite buscar, visualizar y descargar | PostgreSQL + PostGIS + PgSTAC, STAC API sobre FastAPI, Titiler (WMTS), servicio de URLs firmadas, S3 |
| 3 | **Data Processing** | Ejecuta aplicaciones EO y flujos de procesamiento | Argo Workflows, Argo Events, Calrissian (CWL en K8s), ZOO Project (OGC API Processes), Docker/podman, K8s |
| 4 | **Application Registry** | Guarda paquetes de aplicación y sus imágenes | GitLab (código, CWL, CI), Harbor (registro de contenedores), PostgreSQL |
| 5 | **Front‑end Services** | Portal, apps web de casos de uso, notebooks, IDEs | React/Angular, Leaflet/OpenLayers, JupyterHub, VSCode, APIs REST, GitLab CI/CD |
| 6 | **User Workspace** | Espacio personal por usuario con su namespace, repos, registro y buckets | Namespace K8s por usuario, Crossplane, ArgoCD, External Secrets Operator, GitLab, Harbor, API REST de workspace |
| 7 | **Authentication and Authorization** | Identidad, SSO, MFA, RBAC, auditoría | Keycloak, OAuth2/OIDC, JWT, LDAP |
| 8 | **Resource Management** | Aprovisiona y escala recursos declarativamente | Crossplane, Helm, ESO, Prometheus/Grafana, Terraform (opcional) |

**Lo que esto significa para ti:** el Middleware no es "una aplicación". Es un conjunto de servicios acoplados por eventos y por contratos de API. La mayoría de los incidentes que verás serán *de integración*: un flujo que no dispara, un item que no aparece en el catálogo, un token que no autoriza, un bucket sin permiso, un job que muere sin dejar rastro claro.

## 6. Los cuatro flujos que debes saber dibujar de memoria

### 6.1 Ingesta (D2 §3.1, §4; D3 §3)

Tres niveles, según el papel del dataset:

1. **Registro de metadatos**: solo se cataloga el metadato y su punto de acceso; el dato sigue en el origen.
2. **Registro + copia**: se descarga, se valida integridad (checksum) y se guarda en S3.
3. **Registro + calibración**: además se aplica preprocesamiento (georreferenciación, conversión de formato) antes de registrar.

Secuencia: llega el evento al **Event Bus** (Kafka, topic de nueva adquisición) → el **Workflow Engine** (Argo) lee la plantilla del workflow desde el **Registry** y obtiene las imágenes → se instancia y ejecuta la aplicación de ingesta → se calcula/enriquece y se **publica el STAC Item en la STAC FastAPI** → el producto se guarda en el **bucket S3 de datos** → se emite código de salida: éxito → mensaje al topic de éxito; fallo → mensaje al topic de fallo, el dato problemático se mueve a almacenamiento temporal y se notifica al monitoreo.

Entrada esperada: un **STAC Item** con campos obligatorios (extensión espacial y temporal, referencias de assets válidas) y assets en GeoTIFF/COG u otros formatos definidos.

**Preguntas de diagnóstico que este flujo te obliga a poder responder:** ¿el evento llegó al topic? ¿el workflow se instanció? ¿la imagen se pudo bajar del registry? ¿el item se posteó al catálogo? ¿el objeto quedó en el bucket? ¿qué código de salida devolvió?

### 6.2 Descubrimiento y acceso (D2 §5; D3 §4, §6)

- Catálogo **STAC** servido por `stac-fastapi` con backend **PgSTAC** sobre PostgreSQL/PostGIS (colecciones e items como JSONB).
- Endpoints clave: `GET /collections`, `GET /collections/{id}`, `GET /collections/{id}/items`, `GET /collections/{id}/items/{item-id}`, `GET /collections/{id}/queryables`, `GET /search` (CQL2‑TEXT) y `POST /search` (CQL2‑JSON).
- Filtros típicos: temporal (`T_INTERSECTS` sobre `datetime`), espacial (`S_INTERSECTS` sobre `geometry` con un polígono) y por propiedad (`eo:cloud_cover < 10`), combinables con `and`.
- **Descarga con URL firmada**: el asset declara `auth:refs: [signed_url_auth]`; el cliente hace `POST` al endpoint de autorización con la URL `s3://…` y un `Authorization: Bearer <token>`; la respuesta trae `signed_url` (con `X-Amz-Algorithm`, `X-Amz-Expires`, `X-Amz-Signature`…) o un `302` con `Location` si se pidió redirección. Es acceso temporal, sin credenciales de larga vida.
- Para servicios de procesamiento integrados vía CWL no se usan URLs firmadas: la plataforma hace **stage‑in** y entrega los datos como rutas locales dentro del contenedor.

### 6.3 Visualización (D3 §5)

- **Overview images**: asset con `role: "overview"` que apunta a un PNG generado con parámetros (`color_formula`, `rescale`, `resampling`, `max_size`).
- **Tiles XYZ/WMTS** servidos por **Titiler** desde COGs: enlaces con `rel: "xyz"` y plantilla `…/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=red&assets=green&assets=blue&color_formula=…&rescale=…`. Varias visualizaciones por producto (color verdadero, falso color).

Cuando "el mapa no carga", el árbol de causas es: item sin links de tiles → Titiler caído o sin acceso al bucket → COG mal formado → parámetros de `rescale`/`assets` incorrectos → CDN/Ingress/TLS.

### 6.4 Procesamiento y ciclo de vida de aplicaciones (D2 §3.3, §6, §7.2)

- Las aplicaciones EO se empaquetan como **Application Package**: descripción en **CWL** + contenedores **Docker/OCI**, siguiendo *OGC Best Practices for EO Application Package* (OGC 20‑089r1).
- Se versionan en **GitLab**; las imágenes viven en **Harbor** (con escaneo de vulnerabilidades, firma y RBAC).
- **Despliegue** y **ejecución** se exponen como **OGC API – Processes** (Parte 2 y Parte 1 respectivamente), implementado con **ZOO Project**.
- **Argo Workflows** orquesta; **Calrissian** ejecuta CWL nativamente en Kubernetes, paralelizando pasos; **Argo Events** dispara por evento.
- Ejecución posible en tres modos: computadora local (cwltool), clúster Kubernetes, y "Execution as a Service".

### 6.5 Workspace de usuario (D2 §3.6)

Cada usuario obtiene: un **namespace propio** en Kubernetes gestionado por **Crossplane** (que le aprovisiona buckets S3 y releases de Helm), repositorios en GitLab, registro Harbor propio, secretos vía **External Secrets Operator**, sincronización continua de manifiestos con **ArgoCD**, y una **API REST de workspace** para bootstrap y consulta de recursos aprovisionados.

Esto es GitOps aplicado a usuarios finales. Si no dominas ArgoCD y Crossplane, este componente será una caja negra — y es uno de los que nadie más administra.

## 7. Seguridad e identidad (D1 §3.2.2; D2 §3.7, §8)

- **Keycloak** centraliza identidad: OAuth2/OpenID Connect, JWT, SSO, MFA, federación LDAP, RBAC y *audit logging*.
- Cifrado en tránsito y en reposo; TLS 1.2 o superior; HTTPS y SFTP para transferencias.
- Principio de mínimo privilegio, revisión periódica de accesos, trazas de auditoría.
- Cumplimiento del **ESA Personal Data Protection Framework** y GDPR: minimización de datos, limitación de propósito, derechos del interesado, notificación de incidentes con datos personales al DPO de ESA (y art. 33 del GDPR cuando aplique).
- Plan de respuesta a incidentes: detección automatizada → contención (aislar, revocar accesos, parchear) → recuperación (restauración y pruebas) → notificación y reporte con lecciones aprendidas.

## 8. Observabilidad (D2 §7.10–7.11, §9.4)

**Prometheus** recolecta métricas de los componentes; **Grafana** las visualiza en dashboards. Se espera monitoreo continuo de CPU, memoria, red, tiempos de respuesta y tasas de error, con alertas para detección temprana. La plataforma también contempla pruebas de carga y *benchmarking* periódicos contra métricas de referencia.

Tu trabajo aquí no es diseñar la plataforma de monitoreo, pero sí: instrumentar lo que falte del Middleware, construir los dashboards operativos que usarás a diario, definir umbrales de alerta con sentido, y correlacionar métrica + log + evento para llegar a la causa.

## 9. Estándares que la plataforma da por sentados

| Estándar | Para qué | Dónde lo verás |
|---|---|---|
| **STAC** (SpatioTemporal Asset Catalog) | Describir e indexar productos EO | Toda la ingesta, el catálogo, los assets, las extensiones `eo`, Web Map Links, Rendering |
| **CQL2** (JSON y TEXT) | Filtrar en `/search` | Consultas del catálogo |
| **OGC API – Features** | Acceso estandarizado a features | Catálogo |
| **OGC API – Processes** (Parte 1 y 2) | Ejecutar y desplegar procesos | ZOO Project, ejecución de aplicaciones |
| **OGC WMTS / XYZ** | Servir teselas | Titiler, visualización |
| **CWL** | Describir workflows portables | Ingesta y procesamiento |
| **OGC 20‑089r1** (EO Application Package) | Empaquetar aplicaciones EO | Registry, despliegue |
| **COG** (Cloud‑Optimized GeoTIFF) | Formato de raster con lectura parcial | Almacenamiento y visualización |
| **S3 API** | Almacenamiento de objetos | Todo el dato pesado |
| **OCI / Docker** | Imágenes de contenedor | Harbor, ejecución |

## 10. Los números que debes memorizar

**Compromisos de la plataforma (D1 §3.2.1, §6):**

- Disponibilidad objetivo: **99,5 % anual** (≈44 h de caída máxima al año). MTTR objetivo **< 1 hora**.
- Throughput de ingesta y procesamiento: **≥ 0,350 TB/h**, escalable a picos de **3,5 TB/h**.
- Latencia de procesamiento extremo a extremo: **< 1 hora** para productos estándar. Flujos en tiempo real: **≤ 5 minutos** desde ingesta hasta disponibilidad.
- Capacidad: **hasta 3.000 usuarios concurrentes**; tiempo de respuesta medio **< 5 s** en carga normal y **≤ 7,5 s** en pico; utilización de recursos objetivo **50–70 %**.
- KPIs propuestos: disponibilidad del sistema (ligada a ingesta, catálogo y acceso), oportunidad de la ingesta (*Data Ingestion Timeliness*), capacidad/escalabilidad de usuarios y **completitud de la oferta de datos** (% de solicitudes de items exitosas).

**Compromisos del proveedor (pliego §8.5.17):**

| Severidad | Respuesta máx. | Resolución máx. |
|---|---|---|
| Crítico | 15 min | 2 h |
| Alto | 1 h | 4 h |
| Medio | 2 h | 8 h |
| Normal | 4 h | 24 h |

- Aplican **24/7**, incluidos fines de semana y festivos.
- Disponibilidad **99,95 % mensual** (≈43,2 min), excluyendo mantenimientos notificados con ≥ 48 h.
- **RTO < 24 h**, **RPO < 1 h**.
- Penalidad: 4 % de la mensualidad ÷ 30 por cada día calendario o proporcional de afectación.
- Escalamiento en 3 niveles; canales: teléfono 24/7 (crítico/alto), correo y portal de tickets.
- Monitoreo **8x5** de SO, Kubernetes y aplicaciones; reportes mensuales de disponibilidad, incidentes y uso; punto de contacto técnico asignado y reuniones mensuales/semanales.

**Infraestructura contratada (Anexo I del pliego):** K8s administrado HA (hasta 500 nodos); 10 VM 4 vCPU/16 GB y 15 VM 8 vCPU/32 GB para componentes; 8 VM 8/32, 8 VM 16/64 y 4 VM 32/128 para procesamiento; LB dedicado HA ≥ 1 Gbps; 2 PostgreSQL HA 16 vCPU/64 GB/800 GB; 25 TB de block storage SSD (PVC); total 50 recursos, 496 vCPU, 1.984 GB RAM, 40,3 TB SSD. Object storage: 2 PB caliente + 750 TB frío, S3‑compatible, con latencias máximas de **100 ms lectura / 200 ms escritura** en caliente. Rotación anual de caliente a frío. Objetos típicos de 100 MB–1 GB (máx. 8 GB), lecturas parciales frecuentes de 16 KB–1 MB. Recuperación típica desde frío: 20 TB por solicitud. Data center Tier III (TCCF o TCOS vigente) ubicado en Panamá. Conectividad: 3 Gbps a Europa (RedCLARA o internet dedicado) y ≥ 1 Gbps de salida para usuarios finales. Acceso del operador a las APIs de Kubernetes y S3 por **VPN** (recomendado) o interfaz web.

Estos números son tu vara de medir en el informe mensual de validación. Apréndelos; los vas a citar mucho.

---

# PARTE III — MAPA DE COMPETENCIAS

## 11. Matriz: qué saber, a qué nivel, con qué evidencia

Nivel: **C** = conceptual (puedo explicarlo y decidir a quién escalar) · **O** = operativo (lo hago solo, bajo presión, sin guía) · **E** = experto (lo diseño, lo optimizo y enseño).

| # | Competencia | Nivel | Evidencia de que ya lo tienes |
|---|---|---|---|
| 1 | Linux, CLI, permisos, procesos, redes de cliente | O | Diagnosticas conectividad y permisos desde un pod sin buscar comandos |
| 2 | Git y flujo de trabajo declarativo | O | Versionas manifiestos, comparas, revocas, y sabes qué provocó un cambio |
| 3 | YAML y manifiestos K8s | E | Escribes desde cero un StatefulSet con volúmenes, probes y recursos, y lo validas antes de aplicar |
| 4 | Contenedores (Docker/podman, OCI) | O | Explicas capas, construyes una imagen reproducible, la firmas/escaneas y la subes a un registro privado |
| 5 | Kubernetes — workloads | E | Rollout, rollback, escalado, `Job`/`CronJob`, y diagnóstico de `CrashLoopBackOff`, `ImagePullBackOff`, `OOMKilled`, `Pending`, `Evicted` |
| 6 | Kubernetes — configuración y secretos | E | ConfigMaps/Secrets, montajes, recarga controlada, rotación sin exponer valores |
| 7 | Kubernetes — almacenamiento | O | PVC, StorageClass, modos de acceso, expansión, diagnóstico de volúmenes |
| 8 | Kubernetes — red de aplicación | O | Service, Ingress, DNS interno, NetworkPolicy, terminación TLS |
| 9 | Helm | E | Charts, values, `template`, `diff`, `upgrade --atomic`, `rollback`, gestión de releases |
| 10 | GitOps con ArgoCD | O | Sincronización, drift, hooks, orden de sincronización, recuperación de un estado divergente |
| 11 | Crossplane | C→O | Entiendes claims/compositions; sabes leer por qué un recurso no se aprovisiona |
| 12 | External Secrets Operator | O | Configuras un `ExternalSecret` y diagnosticas fallos de sincronización |
| 13 | Argo Workflows + Argo Events | O | Lanzas, sigues, reintentás y depuras un workflow; entiendes sensores, triggers y event bus |
| 14 | Kafka (nivel operativo) | C→O | Topics, consumer groups, lag; sabes ver si un evento llegó y si alguien lo consumió |
| 15 | CWL y Application Packages | O | Lees un CWL, entiendes entradas/salidas y stage‑in/out, ejecutas con cwltool y con Calrissian |
| 16 | STAC + PgSTAC + stac-fastapi | E | Cargas colecciones e items, consultas con CQL2, diagnosticas por qué un item no aparece |
| 17 | PostgreSQL/PostGIS (operación) | O | Conectividad, sesiones, bloqueos, consultas lentas, verificación de respaldo y prueba de restauración |
| 18 | S3 (políticas, lifecycle, presigned) | E | Buckets, políticas, versionado, reglas de ciclo de vida hot→cold, URLs firmadas, medición de latencia |
| 19 | Titiler / COG / WMTS | O | Verificas un COG, generas una tesela, diagnosticas una visualización rota |
| 20 | Keycloak y OIDC | O | Realms, clients, roles, mapeo a RBAC, depuración de un token rechazado |
| 21 | Harbor y GitLab (registry + CI) | O | Proyectos, cuotas, escaneo, retención de imágenes, pipelines que publican paquetes |
| 22 | Observabilidad (Prometheus/Grafana/logs) | E | Consultas PromQL útiles, dashboards propios, alertas con umbral justificado, correlación log‑métrica‑evento |
| 23 | Gestión de incidentes y problemas | E | Clasificas por severidad, contienes, comunicas, documentas causa raíz y acción correctiva |
| 24 | Gestión de cambios | O | Ventana, plan de reversión, criterio de éxito, evidencia posterior |
| 25 | Documentación operativa | E | Runbooks ejecutables por otro, SOPs, checklists, inventario y arquitectura vigente |
| 26 | Validación de SLA y de entregables | E | Informe mensual con evidencia propia, no solo con el reporte del proveedor |
| 27 | Conducción de reuniones técnicas y transferencia | O | Agenda, acuerdos con responsable y fecha, seguimiento, enseñanza por shadowing |

### 11.1 Lo que NO debes estudiar (y por qué)

Cuesta tiempo y no es tuyo: instalación y upgrade del clúster, `etcd`, kubeadm, administración de nodos y del SO, CNI y red de bajo nivel, hipervisores, tuning interno del motor PostgreSQL, ejecución de respaldos, hardening físico del almacenamiento, diseño de la topología de red del proveedor, certificaciones tipo CKA/CKS completas.

Excepción: necesitas el **vocabulario** de todo esto para dialogar y para escalar bien. Nivel conceptual, no operativo.

## 12. Diagnóstico de brechas y prioridad

### 12.1 Corrección de énfasis respecto del plan previo

El plan existente clasifica **S3 como "básico‑intermedio"**, **DevOps/CI‑CD como "básico"** y no menciona Argo Workflows/Events, Kafka, STAC/PgSTAC, Keycloak, Crossplane, ArgoCD ni Harbor. Eso es coherente para preparar a un equipo *antes* de la capacitación de ESA, pero **no** para el titular del rol: precisamente esas piezas son las que el análisis de perfil marca como *no cubiertas* por el proveedor. Reordena tu esfuerzo así:

| Prioridad | Bloques | Razón |
|---|---|---|
| **1 — Crítico** | K8s workloads/config, Helm, observabilidad y diagnóstico, incidentes | Es la operación diaria y lo primero que se rompe |
| **2 — Alto (y desatendido)** | STAC/PgSTAC, Argo Workflows/Events, S3 con políticas y lifecycle, Keycloak, Harbor/GitLab | Nadie más los administra; el contrato del proveedor no los cubre |
| **3 — Medio** | ArgoCD, Crossplane, ESO, CWL/Calrissian, Titiler/COG | Los tocas al operar workspaces, despliegues y visualización |
| **4 — Contexto** | Kafka interno, PostgreSQL avanzado, redes del clúster, IaC del proveedor | Para dialogar y escalar, no para operar |

### 12.2 Autodiagnóstico rápido (hazlo antes de planificar)

Responde con honestidad — sí / a medias / no:

1. ¿Puedo desplegar una aplicación con Helm, cambiar un valor, ver el diff y revertir sin consultar nada?
2. Ante un pod que reinicia, ¿tengo una secuencia fija de comandos y sé qué descarta cada uno?
3. ¿Sé leer un manifiesto de `StatefulSet` y explicar por qué usa volúmenes por réplica?
4. ¿Puedo montar un catálogo STAC local y cargar un item?
5. ¿Puedo escribir una política de bucket S3 que dé acceso de solo lectura a un prefijo?
6. ¿Puedo explicar qué hace un `Sensor` de Argo Events y cómo compruebo que disparó?
7. ¿Sé qué es un JWT, cómo se valida y por qué un token puede ser rechazado?
8. ¿Puedo escribir una consulta PromQL que muestre la tasa de error 5xx de un servicio?
9. ¿Puedo redactar un runbook que otra persona ejecute sin preguntarme nada?
10. ¿Puedo sostener una reunión con el proveedor citando su SLA y mi evidencia?

Cada "no" es un bloque de la Parte IV que no puedes saltarte. Cada "a medias" es un laboratorio, no una lectura.

---

# PARTE IV — PLAN DE APRENDIZAJE HACIENDO

## 13. El método: siete principios

Aprendes haciendo. Eso no significa "leer poco": significa **invertir el orden** y usar la lectura para desatascar, no para preparar.

1. **Primero el intento, después la explicación.** Enfrenta la tarea antes de leer la documentación. El intento fallido crea los ganchos donde la explicación se engancha. Regla de los 15 minutos: si te atascas, consulta; no antes.
2. **Rómpelo a propósito.** El diagnóstico solo se aprende diagnosticando. Cada laboratorio tiene una fase de sabotaje deliberado (§16). Un fallo provocado por ti se entiende diez veces mejor que uno leído.
3. **El artefacto es la evidencia.** Cada bloque termina en algo que existe: un manifiesto, un dashboard, un runbook, un informe. Si no queda artefacto, no cuenta como estudiado. Beneficio doble: esos artefactos son la materia prima de los Productos 1 a 3 del contrato.
4. **Recuperación espaciada, no relectura.** Al empezar cada sesión, dedica 10 minutos a rehacer *de memoria* algo del bloque anterior (un manifiesto, una consulta, una secuencia de diagnóstico). Es incómodo y es exactamente por eso que funciona.
5. **Práctica deliberada en el borde.** Trabaja siempre en el punto donde fallas ~30 % de las veces. Si todo sale, sube la dificultad (más réplicas, menos recursos, un componente caído). Si nada sale, baja un escalón.
6. **Aprendizaje contextual.** Todo laboratorio replica una pieza *real* de CopernicusLAC, con sus nombres reales. No practiques con `nginx-demo`: practica con un catálogo STAC, un bucket de productos, un workflow de ingesta. La transferencia al puesto es directa.
7. **Enseña temprano.** Desde la semana 4, explica en voz alta lo que hiciste como si formaras al recurso designado por AIG. Enseñar expone los huecos que la práctica silenciosa esconde — y es literalmente el Producto 4 del contrato.

**Bitácora.** Un solo archivo por día, tres líneas: qué intenté, qué falló, qué comando/idea lo resolvió. Es tu futuro banco de runbooks y tu evidencia de progreso.

## 14. El laboratorio: una maqueta de CopernicusLAC en tu máquina

La idea rectora: **no montes "un laboratorio de Kubernetes"; monta una réplica reducida del Middleware**. Cada pieza que instales corresponde a una pieza real.

### 14.1 Requisitos

- Máquina con 16 GB de RAM (32 GB es cómodo) y ~60 GB libres. Con 8 GB, monta los bloques por separado y no todo a la vez.
- Docker Desktop o podman + `kind` o `k3d` para el clúster, `kubectl`, `helm`, `git`, `k9s` (opcional pero acelera mucho la lectura del clúster), `jq`, `curl`.
- Alternativa sin instalación: **Killercoda** y **Play with Kubernetes** para los bloques 2 y 3, si necesitas empezar hoy mismo.

### 14.2 Correspondencia maqueta ↔ plataforma real

| Pieza de tu laboratorio | Corresponde a | Componente D2 |
|---|---|---|
| `kind`/`k3d` local | KaaS del proveedor | Infraestructura |
| MinIO | Object storage S3 (2 PB caliente + frío) | Almacenamiento |
| PostgreSQL + PostGIS + PgSTAC (en clúster o contenedor) | DBaaS PostgreSQL HA | §3.2 |
| `stac-fastapi-pgstac` | Catálogo STAC | §3.2 |
| Titiler | Servicio de teselas WMTS | §3.2 |
| Argo Workflows + Argo Events | Motor de flujos de ingesta y procesamiento | §3.1, §3.3 |
| Calrissian + cwltool | Ejecución de Application Packages | §3.3, §7.2 |
| Harbor (o registry local) | Registro de contenedores | §3.4 |
| Keycloak | Autenticación y autorización | §3.7 |
| kube-prometheus-stack (Prometheus + Grafana) | Observabilidad | §7.10–7.11 |
| ArgoCD | Sincronización GitOps de workspaces | §3.6 |
| cert-manager + Ingress NGINX | TLS de aplicación e Ingress | Configuración lógica |
| Crossplane (opcional, bloque avanzado) | Resource Management | §3.8 |

> Verifica el nombre y la versión de cada chart/imagen al momento de instalarlos: los repositorios y las convenciones cambian con el tiempo. Si un chart que citas aquí ya no existe con ese nombre, buscar el sustituto **es parte del ejercicio** — es exactamente lo que harás en el puesto.

### 14.3 Datos de práctica

Usa una imagen Sentinel‑2 pública en formato COG y su STAC Item (por ejemplo, de catálogos abiertos como Earth Search o Planetary Computer). Con **un solo item bien cargado** puedes practicar catálogo, filtros CQL2, teselas, URLs firmadas y ciclo de vida de objetos. No necesitas volumen; necesitas fidelidad.

## 15. Ruta de práctica: nueve bloques

Cadencia sugerida: **6 semanas a ~10 h/semana** para los bloques 0–7, y el bloque 8 continuo. Si el arranque es inminente, ve a §17.

Formato de cada bloque: **Misión** (qué logras) · **Laboratorio** (qué haces) · **Sabotaje** (qué rompes) · **Artefacto** (qué queda) · **Criterio** (cómo sabes que terminaste).

---

### Bloque 0 — Terreno firme (4 h, sáltalo si pasas la prueba)

**Misión:** que Linux, Git y YAML dejen de consumir atención.
**Laboratorio:** crea un repositorio `middleware-lab`; estructura `manifests/`, `charts/`, `runbooks/`, `bitacora/`. Escribe a mano un manifiesto de Pod con `resources`, `livenessProbe` y `readinessProbe`. Valídalo con `kubectl apply --dry-run=client -f`.
**Sabotaje:** rompe la indentación, invierte dos niveles, quita un campo obligatorio. Aprende a leer el mensaje de error.
**Artefacto:** el repositorio inicializado y tu primer manifiesto versionado.
**Criterio:** escribes 30 líneas de YAML válido sin copiar de ningún lado.

---

### Bloque 1 — Contenedores e imágenes (5 h)

**Misión:** entender qué corre realmente dentro de un pod.
**Laboratorio:** construye una imagen mínima de una app Python que exponga `/health` y `/metrics`; inspecciona capas (`docker history`, `docker inspect`); publica en un registro local; luego levanta **Harbor** y repite con proyecto, cuota y escaneo de vulnerabilidades.
**Sabotaje:** publica una imagen con una vulnerabilidad conocida y observa el escaneo; cambia el tag sin cambiar el digest y razona por qué `imagePullPolicy` importa.
**Artefacto:** `Dockerfile` versionado + nota de una página "imagen vs contenedor vs pod" con tus palabras.
**Criterio:** explicas por qué un `ImagePullBackOff` puede ser credenciales, tag inexistente, o registro inalcanzable — y sabes distinguirlos.

---

### Bloque 2 — Kubernetes: workloads, configuración y diagnóstico (12 h) ⭐ núcleo

**Misión:** operar cargas y diagnosticar fallos sin ayuda.
**Laboratorio:**
1. Crea el clúster (`kind create cluster --name copernicus-lab`).
2. Despliega un `Deployment` con 3 réplicas, `resources`, probes y `ConfigMap` montado.
3. Haz `rollout` de una versión nueva; observa `kubectl rollout status`, `kubectl rollout history`, y revierte con `rollout undo`.
4. Convierte un caso a `StatefulSet` con `volumeClaimTemplates` y explica la diferencia con el `Deployment`.
5. Crea un `Job` y un `CronJob`; revisa historial y política de reintentos.
6. Crea un `Secret`, móntalo como archivo y como variable, y verifica que no aparece en logs.
**Sabotaje (obligatorio, uno por sesión):** imagen inexistente · límite de memoria demasiado bajo (`OOMKilled`) · probe con puerto equivocado · `ConfigMap` renombrado · `PVC` con StorageClass inexistente · réplicas que exceden la cuota del namespace.
**Artefacto:** `runbooks/diagnostico-pod.md` — tu secuencia fija: `get pods -o wide` → `describe pod` → `logs` (+`--previous`) → `get events --sort-by=.lastTimestamp` → `exec` → `top pod`. Con la interpretación de cada estado.
**Criterio:** un compañero te da un clúster roto y localizas la causa en menos de 10 minutos usando solo tu runbook.

---

### Bloque 3 — Helm y GitOps (8 h) ⭐ núcleo

**Misión:** desplegar y revertir el Middleware como lo harás en producción.
**Laboratorio:** empaqueta tu app del bloque 1 como chart (`helm create`, luego límpialo); parametriza réplicas, imagen y config en `values.yaml`; instala, `helm template` y `helm diff` antes de cada cambio; `helm upgrade --atomic --timeout`; provoca un fallo y observa la reversión automática; `helm rollback` manual; `helm history`.
Luego instala **ArgoCD**, apunta una `Application` a tu repositorio, cambia algo directamente en el clúster y observa el *drift*; sincroniza; borra un recurso y mira cómo se restaura.
**Sabotaje:** un `values.yaml` con un tipo equivocado; un upgrade que deja el release en `pending-upgrade`; un secreto que ArgoCD sobrescribe.
**Artefacto:** chart versionado + `runbooks/despliegue-y-reversion.md` con la ventana, el criterio de éxito y el plan de reversión.
**Criterio:** haces un upgrade fallido y lo revierte sin perder configuración, explicando en voz alta cada paso.

---

### Bloque 4 — Catálogo: PostgreSQL, PostGIS, PgSTAC y STAC API (10 h) ⭐ desatendido

**Misión:** poseer el componente de descubrimiento, que nadie más administra.
**Laboratorio:**
1. Levanta PostgreSQL con PostGIS y la extensión **PgSTAC** (imagen `pgstac` o migraciones con `pypgstac`).
2. Levanta `stac-fastapi-pgstac` apuntando a esa base.
3. Carga una colección y varios items reales con `pypgstac load`.
4. Consulta: `GET /collections`, `/collections/{id}/queryables`, `GET /search` con CQL2‑TEXT y `POST /search` con CQL2‑JSON. Filtra por `datetime` (`T_INTERSECTS`), por polígono (`S_INTERSECTS`) y por `eo:cloud_cover`.
5. Mide: ¿cuánto tarda una búsqueda espacial sin índice? Crea el índice y compara.
**Sabotaje:** carga un item sin `datetime` o con `bbox` inválido y observa el rechazo; apunta la API a una base sin migrar; agota las conexiones de PostgreSQL con un pool mal configurado.
**Artefacto:** colección de consultas CQL2 comentadas (`runbooks/consultas-catalogo.md`) + nota sobre por qué un item ingerido puede no aparecer en búsqueda.
**Criterio:** explicas la ruta completa desde "el workflow posteó el item" hasta "el usuario lo ve en el portal", y sabes dónde mirar en cada salto.

---

### Bloque 5 — Objetos: S3, políticas, ciclo de vida y URLs firmadas (8 h) ⭐ brecha declarada

**Misión:** cubrir el área que el análisis ESA marca explícitamente como *no cubierta* por el proveedor.
**Laboratorio:**
1. Levanta **MinIO**; crea buckets `productos`, `staging`, `frio`.
2. Crea usuarios/políticas: solo lectura sobre un prefijo, escritura sobre otro, y verifica con `mc` o el SDK que el acceso denegado *realmente* se deniega.
3. Activa versionado; borra un objeto y recupéralo.
4. Configura una **regla de ciclo de vida** que mueva objetos de más de N días a otro bucket/clase — es exactamente el esquema de rotación anual caliente→frío del pliego.
5. Genera una **URL prefirmada** con expiración corta; úsala; espera a que expire; observa el error. Compara con el esquema `signed_url_auth` de D3 §6.2.
6. Mide latencia de lectura parcial (rangos de 16 KB–1 MB, como especifica el pliego) sobre un objeto grande.
**Sabotaje:** política con un `Resource` mal escrito; URL firmada de un objeto que no existe; lifecycle que borra en vez de mover.
**Artefacto:** `runbooks/almacenamiento-objetos.md` con las políticas comentadas, el procedimiento de verificación de acceso y el de rotación.
**Criterio:** puedes auditar en 15 minutos quién tiene acceso a qué bucket y demostrarlo con evidencia.

---

### Bloque 6 — Flujos: Argo Workflows, Argo Events y CWL (12 h) ⭐ desatendido

**Misión:** operar la ingesta y el procesamiento, el corazón funcional de la plataforma.
**Laboratorio:**
1. Instala **Argo Workflows**; ejecuta un workflow de varios pasos con artefactos en MinIO.
2. Instala **Argo Events**: `EventBus`, `EventSource` (webhook), `Sensor` que dispara el workflow. Emite el evento con `curl` y comprueba la cadena completa.
3. Construye tu **flujo de ingesta simulado**: evento → descarga del asset → validación de checksum → publicación del STAC Item en la API del bloque 4 → subida del objeto al bucket del bloque 5 → mensaje al topic de éxito o fallo.
4. Escribe un **CWL** mínimo (un `CommandLineTool` con entradas/salidas), ejecútalo con `cwltool` local y luego con **Calrissian** dentro del clúster.
**Sabotaje:** un paso con imagen sin permisos de pull; un artefacto que no se sube porque falta el secreto de MinIO; un sensor que no dispara porque el filtro no coincide; un workflow que deja pods `Completed` acumulados.
**Artefacto:** el pipeline completo versionado + `runbooks/ingesta-fallida.md` con el árbol de diagnóstico del flujo (¿llegó el evento? ¿se creó el workflow? ¿qué paso falló? ¿qué exit code? ¿dónde quedó el dato?).
**Criterio:** rompes cualquiera de los cinco eslabones y encuentras cuál en menos de 10 minutos.

---

### Bloque 7 — Identidad, TLS y red de aplicación (8 h)

**Misión:** que "no me autoriza" y "el certificado no sirve" dejen de ser callejones sin salida.
**Laboratorio:**
1. Instala **Ingress NGINX** y **cert-manager**; expón el catálogo del bloque 4 por HTTPS con un emisor self‑signed; inspecciona el certificado.
2. Instala **Keycloak**: crea un realm, un client OIDC confidencial, roles y un usuario; obtén un token; decodifica el JWT (claims, `exp`, `aud`, `iss`).
3. Protege un endpoint con ese token; prueba con token expirado, con audiencia equivocada y sin rol.
4. Crea un `Role`/`RoleBinding` de Kubernetes de mínimo privilegio y verifica con `kubectl auth can-i`.
5. Aplica una `NetworkPolicy` que solo permita al catálogo hablar con la base de datos; comprueba que lo demás queda bloqueado.
**Sabotaje:** certificado con SAN incorrecto; `Ingress` con la clase equivocada; `RoleBinding` en el namespace equivocado; NetworkPolicy que corta el DNS.
**Artefacto:** `runbooks/acceso-denegado.md` — el árbol: ¿es red, es TLS, es token, es RBAC de K8s, es política de la aplicación?
**Criterio:** ante un 401, un 403 y un `connection refused`, sabes cuál investigar dónde y no confundes los tres.

---

### Bloque 8 — Observabilidad y operación (continuo, 10 h iniciales) ⭐ núcleo

**Misión:** ver antes de que te llamen, y sostener la operación con disciplina.
**Laboratorio:**
1. Instala **kube-prometheus-stack**; explora los dashboards que trae.
2. Escribe tus propias consultas PromQL: tasa de error 5xx, latencia p95, reinicios de pods, saturación de CPU/memoria, `kube_persistentvolumeclaim_status_phase`.
3. Construye **tu dashboard operativo**: una sola pantalla con la salud de ingesta, catálogo y acceso — los tres servicios a los que D1 liga la disponibilidad.
4. Define 3 alertas con umbral justificado por escrito (por qué ese número y qué acción dispara).
5. Calcula el presupuesto de error: con 99,5 % anual dispones de ~44 h; con 99,95 % mensual del proveedor, ~43 min. Traduce ambos a "cuánto puede durar este incidente antes de que sea un incumplimiento".
6. Redacta la **plantilla del informe mensual de validación del proveedor**: disponibilidad medida por ti vs. reportada, incidentes por severidad con tiempos de respuesta/resolución reales frente a la tabla del SLA, conectividad, métricas de rendimiento, hallazgos y solicitudes.
**Sabotaje:** provoca una caída de 20 minutos del catálogo y practica el ciclo completo: detectar por alerta → clasificar severidad → contener → comunicar → documentar causa raíz.
**Artefacto:** dashboard exportado (JSON versionado), reglas de alerta, plantilla del informe mensual, y `runbooks/gestion-incidentes.md`.
**Criterio:** te enteras de un fallo por tu alerta y no por un usuario; y produces el informe mensual en menos de 2 horas.

---

## 16. Catálogo de averías para practicar (chaos drills)

Guarda esta lista. Cuando termines los bloques, elige una al azar cada semana, provócala en tu maqueta y cronométrate. Estas son —textualmente— las averías que verás en producción.

| # | Avería | Dónde la provocas | Habilidad que entrena |
|---|---|---|---|
| 1 | Pod en `CrashLoopBackOff` por variable de entorno faltante | ConfigMap renombrado | Logs + eventos |
| 2 | `ImagePullBackOff` por credenciales del registro | Secret de pull borrado | Registry / Harbor |
| 3 | `OOMKilled` bajo carga | Límite de memoria bajo | Recursos y métricas |
| 4 | PVC en `Pending` | StorageClass inexistente | Almacenamiento |
| 5 | Ingress responde 502 | Service apuntando a puerto equivocado | Red de aplicación |
| 6 | TLS inválido en el portal | Certificado expirado o SAN incorrecto | cert-manager |
| 7 | 401 en la STAC API | Token expirado / audiencia incorrecta | Keycloak / OIDC |
| 8 | Ingesta que no arranca | Sensor con filtro que no coincide | Argo Events |
| 9 | Workflow que falla en el paso 3 | Imagen sin GDAL | Argo Workflows / CWL |
| 10 | Item ingerido que no aparece en búsqueda | Item sin `datetime` o colección incorrecta | STAC / PgSTAC |
| 11 | Catálogo lento | Índice espacial ausente / pool agotado | PostgreSQL |
| 12 | Descarga que devuelve 403 | Política de bucket o URL firmada expirada | S3 |
| 13 | Mapa en blanco | COG mal formado o `rescale` incorrecto | Titiler / visualización |
| 14 | Deployment desincronizado | Cambio manual sobre recurso gestionado por ArgoCD | GitOps |
| 15 | Namespace que rechaza pods | ResourceQuota agotada | Cuotas |
| 16 | Servicio inalcanzable entre pods | NetworkPolicy que corta DNS | Red / DNS interno |
| 17 | Base de datos inalcanzable | Credencial rotada sin actualizar el Secret | Secretos / DBaaS |
| 18 | Upgrade de Helm atascado | Release en `pending-upgrade` | Helm |

Para cada una, tu meta no es "arreglarla": es **llegar a la causa con evidencia y decidir si es tuya o del proveedor**.

## 17. Si el arranque es inminente: ruta de 10 días

Si tienes menos de dos semanas antes de empezar, este es el orden de máximo retorno:

| Día | Foco | Resultado mínimo |
|---|---|---|
| 1 | Documentos: TDR + Perfil ESA + §2.1 de esta guía | La frontera de responsabilidad memorizada |
| 2 | D2 §2–3 y §7 | Poder dibujar los 8 componentes y nombrar su stack |
| 3–4 | Bloque 2 (workloads y diagnóstico) | `runbooks/diagnostico-pod.md` funcionando |
| 5 | Bloque 3 (Helm + rollback) | Un upgrade fallido revertido |
| 6 | Bloque 4 (STAC/PgSTAC) reducido: levantar y consultar | Entender la ruta ingesta → catálogo → usuario |
| 7 | Bloque 5 reducido: MinIO, políticas y URL firmada | Saber auditar accesos |
| 8 | Bloque 8 reducido: Prometheus + un dashboard + 1 alerta | Ver el estado del sistema |
| 9 | §10 completo + plantilla del informe mensual | Números del SLA memorizados |
| 10 | Simulacro: 3 averías del §16, cronometradas | Confianza operativa |

Lo demás se aprende en la operación real — que es, de hecho, la mejor escuela disponible, siempre que lleves bitácora.

## 18. Cómo convertir el estudio en entregables del contrato

No estudies aparte del trabajo: estudia **produciendo** los entregables. Correspondencia directa:

| Artefacto del laboratorio | Alimenta |
|---|---|
| Inventario de la maqueta y diagrama de componentes | Producto 1 (diagnóstico e inventario preliminar), Producto 2 (arquitectura lógica) |
| `runbooks/diagnostico-pod.md`, `ingesta-fallida.md`, `acceso-denegado.md` | Producto 2 (runbooks iniciales), Producto 3 (ajustados a escenarios reales) |
| `despliegue-y-reversion.md` | Producto 2 (despliegues documentados), Producto 6 (SOPs) |
| Dashboard y reglas de alerta | Producto 1 (validaciones técnicas), Producto 9 (informe de métricas) |
| Plantilla de informe mensual del proveedor | Obligación mensual del TDR, Producto 10 (informe acumulativo) |
| Bitácora diaria | Registro de operación de todos los períodos |
| Casos prácticos del §16 | Producto 4 (casos prácticos y transferencia), Producto 5 (operación conjunta) |
| Estructura del repositorio documental | Producto 1 y todos los siguientes |

## 19. Evaluación: cómo sabes que estás listo

### 19.1 Examen práctico (hazlo sin ayuda, cronometrado)

1. **90 min.** Desde un repositorio vacío, despliega en tu maqueta: catálogo STAC con base de datos, bucket de objetos y un Ingress con TLS. Todo por Helm, todo versionado.
2. **45 min.** Recibe un clúster con tres averías del §16 inyectadas. Encuéntralas, documenta causa y solución, y clasifica cada una como "mía" o "del proveedor" con su justificación.
3. **30 min.** Ejecuta un `helm upgrade` que rompe el servicio y revierte sin pérdida de configuración; documenta la ventana, el criterio de éxito y la evidencia.
4. **45 min.** Redacta el informe mensual de validación del proveedor con datos simulados, citando la tabla de severidades, el 99,95 % mensual y el RTO/RPO.
5. **30 min.** Explica en voz alta, a alguien no técnico, qué es el Middleware, qué hace la ingesta y por qué un dato tarda en aparecer en el portal.

### 19.2 Lista de verificación final

- [ ] Explico la frontera Middleware ↔ infraestructura sin dudar y con ejemplos.
- [ ] Dibujo los 8 componentes y nombro su stack.
- [ ] Recorro el flujo de ingesta de punta a punta y sé dónde mirar en cada salto.
- [ ] Consulto el catálogo con CQL2 en sus dos formas.
- [ ] Genero y verifico una URL firmada; audito políticas de bucket.
- [ ] Opero Helm con confianza, incluida la reversión.
- [ ] Diagnostico las 18 averías del §16 con mi propio runbook.
- [ ] Interpreto y construyo dashboards y alertas.
- [ ] Cito de memoria los SLA, KPIs y capacidades del §10.
- [ ] Produzco el informe mensual de validación con evidencia propia.
- [ ] Documento un incidente con causa, impacto, resolución y acción correctiva.
- [ ] Enseño cualquiera de los bloques anteriores a otra persona.

## 20. Qué preguntar (y a quién) en las primeras semanas

Llevar buenas preguntas es la diferencia entre recibir una capacitación y aprovecharla.

**A ESA / Terradue:**
1. ¿Cuál es el mecanismo oficial de despliegue del Middleware: charts propios, GitOps con ArgoCD, o ambos? ¿Dónde vive el repositorio de referencia?
2. ¿Qué versiones exactas de cada componente componen el release desplegado y cómo se anuncian las actualizaciones?
3. ¿Qué métricas expone cada componente y existe un conjunto de dashboards y alertas de referencia?
4. ¿Cuál es el procedimiento de reprocesamiento cuando una ingesta falla parcialmente?
5. ¿Cómo se gestionan los secretos y la rotación de credenciales entre componentes (ESO, backend de secretos)?
6. ¿Qué canal y qué SLA aplica para reportar defectos funcionales del Middleware?
7. ¿Qué parte del ciclo de vida de aplicaciones (GitLab, Harbor, workspaces de usuario) administro yo y qué parte administran ustedes?
8. ¿Existe entorno de pruebas o solo producción? ¿Cómo se valida un cambio antes de aplicarlo?

**Al proveedor de infraestructura:**
1. ¿Qué acceso tendré a la API de Kubernetes y a la de S3, por qué vía (VPN o web) y con qué permisos exactos?
2. ¿Qué StorageClasses existen, con qué parámetros y cuál es el procedimiento para pedir una nueva?
3. ¿Cómo accedo a métricas, logs y eventos del clúster, y con qué retención?
4. ¿Cuál es el procedimiento y el canal de escalamiento por severidad, y quién es el punto de contacto técnico asignado?
5. ¿Con qué frecuencia y con qué evidencia se verifican los respaldos de PostgreSQL, y cuándo se puede hacer una prueba de restauración?
6. ¿Qué contiene exactamente el reporte mensual de disponibilidad, incidentes y uso, y en qué formato lo entregan?
7. ¿Cómo se notifican los mantenimientos programados (las 48 h del pliego) y por qué canal?
8. Durante la franja fuera del monitoreo 8x5, ¿cómo se detecta y se abre un incidente crítico?

**A la AIG:**
1. ¿Dónde vive el repositorio documental oficial y qué estructura debe respetar?
2. ¿Quién es el recurso designado para la transferencia y desde cuándo se incorpora?
3. ¿Cuál es la cadencia y el formato de las reuniones técnicas operativas?
4. ¿Qué instituciones usuarias existen ya y qué tipo de soporte esperan?

## 21. Recursos de referencia

Prioriza documentación oficial. Estos son los sitios de origen; entra a buscar cuando te atasques, no antes (principio 1).

| Tema | Fuente |
|---|---|
| Kubernetes | `kubernetes.io/docs` — Concepts → Workloads, Configuration, Storage, Services/Networking, Security; y "Application Introspection and Debugging" |
| Helm | `helm.sh/docs` — Quickstart y Chart Template Guide |
| ArgoCD | `argo-cd.readthedocs.io` |
| Argo Workflows / Events | `argoproj.github.io/argo-workflows`, `argoproj.github.io/argo-events` |
| CWL | `commonwl.org` — User Guide; Calrissian: `github.com/Duke-GCB/calrissian` |
| STAC | `stacspec.org`; `stac-utils` (stac-fastapi, pgstac, pypgstac) |
| OGC | OGC API – Features, OGC API – Processes, WMTS; OGC 20‑089r1 (EO Application Package) |
| COG / Titiler | `cogeo.org`, `developmentseed.org/titiler` |
| PostGIS | `postgis.net/documentation` |
| MinIO / S3 | `min.io/docs`; referencia de políticas y lifecycle de S3 |
| Keycloak | `keycloak.org/documentation` |
| Harbor | `goharbor.io/docs` |
| Prometheus / Grafana | `prometheus.io/docs` (PromQL), `grafana.com/docs` |
| Crossplane | `docs.crossplane.io` |
| Práctica sin instalación | Killercoda, Play with Kubernetes |
| Gestión de servicio | Prácticas de incidentes, problemas y cambios de ITIL 4 (nivel conceptual: vocabulario y estructura de proceso) |

Evita cursos completos de certificación de administrador de clúster (CKA/CKS): cubren el plano de control, que no es tuyo. Úsalos solo como referencia puntual.

## 22. Glosario mínimo

**AIG** Autoridad Nacional para la Innovación Gubernamental · **CDSE** Copernicus Data Space Ecosystem · **COG** Cloud‑Optimized GeoTIFF · **CQL2** Common Query Language v2 · **CWL** Common Workflow Language · **DBaaS** Database as a Service · **EO** Earth Observation · **ESO** External Secrets Operator · **FTE** Full‑Time Equivalent · **IaaS** Infrastructure as a Service · **KaaS** Kubernetes as a Service · **MFA** Multi‑Factor Authentication · **MTTR** Mean Time To Repair · **OGC** Open Geospatial Consortium · **PDP** (ESA) Personal Data Protection Framework · **PgSTAC** backend PostgreSQL para STAC · **PV/PVC** PersistentVolume / PersistentVolumeClaim · **RBAC** Role‑Based Access Control · **RPO/RTO** Recovery Point/Time Objective · **SLA** Service Level Agreement · **SOP** Standard Operating Procedure · **SSO** Single Sign‑On · **STAC** SpatioTemporal Asset Catalog · **WMTS** Web Map Tile Service.

---

## Cierre

Tres ideas para llevarte:

1. **Tu valor no está en administrar Kubernetes** — eso lo hace el proveedor. Está en ser la única persona que entiende el Middleware de punta a punta y puede decir, con evidencia, dónde está el problema.
2. **Las áreas que nadie más cubre** (STAC/catálogo, flujos de Argo, S3 con políticas y ciclo de vida, identidad, gestión funcional de cambios y optimización) son donde debe ir tu esfuerzo desproporcionado de estudio, aunque parezcan menos "de Kubernetes".
3. **Documenta mientras aprendes.** En este encargo, el runbook no es la consecuencia del conocimiento: es la forma que toma. Cada laboratorio que cierras con un artefacto es simultáneamente aprendizaje y entregable contractual.
