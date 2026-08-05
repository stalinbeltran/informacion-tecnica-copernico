# Plan Integral de Preparación Técnica
## Pre-entrenamiento ESA — Middleware de la Plataforma Copernicus LAC Panamá

**Elaborado para:** AIG — Autoridad de Innovación Gubernamental de Panamá
**Rol objetivo:** Administrador de Middleware (no Administrador de Infraestructura)
**Perfil de participantes:** Ingenieros con base general en informática/sistemas, sin experiencia previa en Kubernetes ni cloud-native

---

## 1. Análisis del perfil

El perfil de "Administrador de Middleware" está diseñado deliberadamente para **excluir la administración de infraestructura**. Esto cambia por completo qué conocimientos son núcleo y cuáles son accesorios.

### Competencias que SÍ requiere el puesto (núcleo)
- Operar workloads de Kubernetes (Deployments, StatefulSets, Jobs, CronJobs) a nivel de aplicación.
- Usar Helm y/o manifiestos YAML para desplegar y actualizar el Middleware.
- Configurar recursos lógicos sobre Kubernetes ya administrado: ConfigMaps, Secrets, Ingress de aplicación, TLS de aplicación, namespaces, RBAC, network policies, quotas.
- Consumir servicios de almacenamiento gestionados (StorageClasses, PV/PVC) sin administrar el almacenamiento físico.
- Monitorear bases de datos gestionadas (DBaaS) desde la perspectiva de disponibilidad, conectividad y rendimiento — no su administración interna.
- Usar almacenamiento de objetos S3-compatible a nivel de acceso y políticas, no a nivel de infraestructura del proveedor.
- Diagnosticar incidentes funcionales mediante logs, eventos y métricas.
- Documentar procedimientos y coordinar con el proveedor de infraestructura y con ESA.

### Competencias accesorias (útiles pero no núcleo)
- Conocimiento conceptual (no operativo) de CI/CD — ayuda a entender el ciclo de vida del Middleware, pero el rol no exige construir pipelines desde cero.
- Nociones de arquitecturas de microservicios y APIs REST — apoyan el diagnóstico, no son objeto de administración directa.
- Conocimientos generales de seguridad — a nivel de buenas prácticas, no de hardening de infraestructura.

### Conclusión del análisis
El equipo necesita entender Kubernetes **como consumidor avanzado de la capa de aplicación**, no como operador de clúster. Esto acota drásticamente el temario: se puede omitir todo lo relacionado con el plano de control, etcd, networking de bajo nivel del clúster y administración de nodos, y concentrar el esfuerzo en los objetos de la capa de workloads, configuración lógica y observabilidad.

---

## 2. Mapa de conocimientos

| Área | Enfoque para este rol |
|---|---|
| Linux | Uso de CLI, permisos, procesos, redes básicas de cliente |
| Docker | Conceptos de contenedores, imágenes, capas — no gestión de daemon en producción |
| Kubernetes (workloads) | Deployments, StatefulSets, Jobs, CronJobs, Pods |
| Kubernetes (config) | ConfigMaps, Secrets, namespaces, RBAC lógico |
| Kubernetes (storage) | PV, PVC, StorageClass (consumo, no aprovisionamiento físico) |
| Kubernetes (networking) | Service, Ingress, NetworkPolicy — nivel de aplicación |
| Helm | Charts, values, releases, upgrades, rollbacks |
| YAML | Sintaxis, estructura de manifiestos, validación |
| Git | Control de versiones para manifiestos e IaC declarativo |
| Bases de datos (DBaaS) | Conectividad, monitoreo, backups (verificación, no ejecución) |
| Almacenamiento de objetos (S3) | Buckets, políticas, acceso, rendimiento básico |
| Seguridad | RBAC, Secrets, TLS de aplicación, políticas de red lógicas |
| Observabilidad | Logs, eventos, métricas básicas (no diseño de plataforma de monitoreo) |
| Monitoreo | Interpretación de dashboards y alertas existentes |
| DevOps / CI-CD | Conceptos de pipeline, GitOps básico |
| APIs | REST, health checks, endpoints de diagnóstico |
| DNS | Resolución interna de servicios, DNS de aplicación |
| TLS | Certificados de aplicación, terminación en Ingress |
| Gestión de incidentes y documentación | Runbooks, SOPs, checklists, coordinación con terceros |

---

## 3. Nivel requerido por tema

| Tema | Nivel requerido | Justificación |
|---|---|---|
| Linux (CLI, permisos, procesos) | Intermedio | Toda la operación diaria pasa por terminal y logs de sistema |
| Docker (conceptos) | Básico-Intermedio | Necesario para entender qué corre dentro de un Pod, no para administrar el runtime |
| Kubernetes – objetos de workload | Avanzado | Es el corazón operativo del rol: desplegar, actualizar y diagnosticar el Middleware |
| Kubernetes – configuración (ConfigMap/Secret/RBAC) | Avanzado | Configuración lógica es responsabilidad directa y diaria |
| Kubernetes – storage (PV/PVC/StorageClass) | Intermedio | Deben verificar y consumir, no diseñar la capa física |
| Kubernetes – networking (Service/Ingress/NetworkPolicy) | Intermedio-Avanzado | Ingress y TLS de aplicación son de su responsabilidad directa |
| Helm | Avanzado | Es el mecanismo principal de despliegue y actualización del Middleware |
| YAML | Avanzado | Toda la configuración del Middleware se expresa en YAML |
| Git | Intermedio | Necesario para versionar manifiestos y coordinar cambios |
| Bases de datos (DBaaS, operación) | Intermedio | Deben monitorear y diagnosticar, no administrar el motor |
| Almacenamiento de objetos (S3) | Básico-Intermedio | Uso operativo, no diseño de la capa de almacenamiento |
| Seguridad lógica | Intermedio | RBAC y Secrets bien manejados evitan incidentes graves |
| Observabilidad (logs/eventos/métricas) | Avanzado | Es la principal herramienta de diagnóstico diario |
| Monitoreo (dashboards/alertas) | Intermedio | Deben interpretar, no necesariamente diseñar el stack de monitoreo |
| DevOps / CI-CD | Básico | Contexto conceptual suficiente; no construyen pipelines |
| APIs / health checks | Intermedio | Fundamental para diagnóstico funcional del Middleware |
| DNS interno de Kubernetes | Básico-Intermedio | Ayuda a diagnosticar fallos de conectividad entre servicios |
| TLS de aplicación | Intermedio | Configuran certificados a nivel de Ingress, no de infraestructura |
| Gestión de incidentes / documentación | Intermedio-Avanzado | Es la práctica profesional que sostiene la operación diaria |

---

## 4. Qué debe saber hacer (tareas prácticas por área)

**Linux**
- Navegar el sistema de archivos, gestionar permisos, revisar procesos y uso de recursos.
- Usar `journalctl`, `grep`, `tail -f`, `ps`, `top` para diagnóstico básico.

**Docker**
- Explicar qué es una imagen vs. un contenedor y cómo se relaciona con un Pod.
- Inspeccionar una imagen y sus capas (`docker inspect`, `docker history`).

**Kubernetes – workloads**
- Interpretar un Deployment y explicar su estrategia de actualización (rolling update).
- Ejecutar y revisar un rollout y un rollback.
- Leer logs de un Pod (`kubectl logs`, incluyendo contenedores anteriores con `--previous`).
- Interpretar eventos de Kubernetes (`kubectl get events`, `kubectl describe`).
- Diferenciar StatefulSet de Deployment y explicar cuándo se usa cada uno.
- Configurar y entender un CronJob y un Job.

**Configuración**
- Comprender y modificar un ConfigMap sin romper el despliegue.
- Crear y montar un Secret de forma segura (sin exponerlo en logs).
- Aplicar cambios de configuración con reinicio controlado del Pod.

**Storage**
- Verificar el estado de un PVC (`kubectl get pvc`, `describe pvc`).
- Explicar la relación entre PV, PVC y StorageClass sin necesidad de aprovisionar almacenamiento físico.
- Diagnosticar un Pod en estado `Pending` por falta de volumen.

**Networking**
- Comprender un Ingress y su relación con un Service.
- Verificar conectividad entre Pods usando DNS interno de Kubernetes.
- Interpretar una NetworkPolicy básica.

**Helm**
- Instalar, actualizar (`helm upgrade`) y revertir (`helm rollback`) un release.
- Comprender la estructura de un Chart (`values.yaml`, `templates/`).
- Ejecutar `helm diff` o `helm template` para anticipar cambios antes de aplicar.

**YAML**
- Leer y modificar manifiestos sin romper la indentación ni la sintaxis.
- Validar un manifiesto antes de aplicarlo (`kubectl apply --dry-run`).

**Git**
- Clonar, versionar, comparar (`diff`) y revertir cambios en manifiestos.
- Trabajar con ramas para separar cambios de configuración por ambiente.

**Bases de datos (DBaaS)**
- Verificar conectividad y estado de salud de una base de datos gestionada.
- Revisar métricas básicas de rendimiento (conexiones activas, latencia).
- Verificar (no ejecutar) que un backup se haya completado correctamente.

**Almacenamiento de objetos (S3)**
- Verificar acceso, políticas de bucket y permisos.
- Revisar métricas básicas de uso y rendimiento.

**Seguridad**
- Aplicar el principio de mínimo privilegio en RBAC de namespace.
- Rotar y gestionar Secrets sin exponerlos.
- Configurar TLS de aplicación en un Ingress.

**Observabilidad / monitoreo**
- Leer e interpretar dashboards existentes (sin diseñarlos).
- Correlacionar logs, eventos y métricas para diagnosticar un incidente.

**Gestión de incidentes / documentación**
- Redactar un runbook básico para un procedimiento operativo.
- Documentar un incidente siguiendo una estructura estándar (causa, impacto, resolución).

---

## 5. Qué NO necesita aprender

Corresponde exclusivamente al proveedor de infraestructura (KaaS/DBaaS) y **no debe incluirse** en la preparación:

- Administración del plano de control de Kubernetes (API server, scheduler, controller manager).
- Gestión de ETCD.
- Actualizaciones de versión del clúster.
- Configuración y mantenimiento de nodos (SO, kernel, parches).
- Networking físico o de bajo nivel del clúster (CNI, routing entre nodos).
- Infraestructura física o de nube subyacente (cómputo, hipervisores).
- Administración del motor de base de datos (instalación, HA, tuning interno, patching).
- Ejecución de backups (solo verificación/restore-test cuando esté definido).
- Administración del almacenamiento físico o del servicio de storage como tal.
- Configuración de alta disponibilidad de infraestructura.
- Diseño de la plataforma de observabilidad (solo consumo/interpretación).

---

## 6. Temario recomendado (de básico a avanzado)

| Módulo | Objetivo | Temas | Duración | Nivel |
|---|---|---|---|---|
| M0. Fundamentos Linux/CLI | Manejo fluido de terminal | Filesystem, permisos, procesos, logs de sistema | 3h | Básico |
| M1. Contenedores con Docker | Entender qué es un contenedor | Imágenes, capas, ciclo de vida, diferencia con VM | 2h | Básico |
| M2. Git esencial | Versionar manifiestos | Clone, commit, branch, diff, revert | 2h | Básico |
| M3. YAML y manifiestos | Leer/escribir YAML válido | Sintaxis, indentación, validación, dry-run | 2h | Básico |
| M4. Kubernetes — conceptos base | Entender el modelo de objetos | Pod, Namespace, Service, arquitectura general (solo lo necesario) | 4h | Básico-Intermedio |
| M5. Kubernetes — workloads | Operar cargas de trabajo | Deployment, StatefulSet, Job, CronJob, rollout/rollback | 6h | Intermedio |
| M6. Configuración en Kubernetes | Gestionar config y secretos | ConfigMap, Secret, montaje en Pods | 3h | Intermedio |
| M7. Storage en Kubernetes | Consumir almacenamiento gestionado | PV, PVC, StorageClass, diagnóstico de Pending | 3h | Intermedio |
| M8. Networking en Kubernetes | Exponer y conectar servicios | Service, Ingress, DNS interno, NetworkPolicy básica | 4h | Intermedio |
| M9. Helm | Desplegar y actualizar vía Charts | Estructura de Chart, values, upgrade, rollback, template | 4h | Intermedio-Avanzado |
| M10. Seguridad lógica | Aplicar controles a nivel de aplicación | RBAC, mínimo privilegio, TLS de aplicación en Ingress | 3h | Intermedio |
| M11. Observabilidad y diagnóstico | Diagnosticar incidentes funcionales | Logs, eventos, métricas, correlación de causas | 4h | Avanzado |
| M12. DBaaS — operación | Monitorear bases de datos gestionadas | Conectividad, salud, métricas, verificación de backups | 3h | Intermedio |
| M13. Object Storage S3 | Operar almacenamiento de objetos | Buckets, políticas, accesos, métricas básicas | 2h | Básico-Intermedio |
| M14. DevOps/CI-CD (conceptual) | Entender el ciclo de entrega | Pipeline, GitOps, entornos, promoción de cambios | 2h | Básico |
| M15. Gestión de incidentes y documentación | Operar con disciplina profesional | Runbooks, SOPs, checklists, coordinación con terceros | 3h | Intermedio-Avanzado |

**Total estimado:** ~46 horas de formación estructurada.

---

## 7. Plan intensivo (preparación acelerada, 3–4 semanas)

Orden recomendado priorizando lo que ESA dará por sentado que el equipo ya domina:

| Semana | Módulos | Horas | Enfoque |
|---|---|---|---|
| 1 | M0, M1, M2, M3 | 9h | Bases: CLI, Docker, Git, YAML |
| 1–2 | M4, M5 | 10h | Kubernetes conceptual + workloads (núcleo del rol) |
| 2 | M6, M7 | 6h | Configuración y storage lógico |
| 2–3 | M8, M9 | 8h | Networking de aplicación + Helm |
| 3 | M10, M11 | 7h | Seguridad lógica + observabilidad/diagnóstico |
| 3–4 | M12, M13 | 5h | DBaaS y object storage (operación) |
| 4 | M14, M15 | 5h | DevOps conceptual + incidentes/documentación |

**Horas totales del plan intensivo:** 50 horas (incluye margen de refuerzo y laboratorios), distribuibles en sesiones de 3–4 horas, 3–4 veces por semana durante 3 a 4 semanas.

> Nota: M5, M9 y M11 son los módulos de mayor peso porque representan el corazón operativo diario del Administrador de Middleware. Si el tiempo se reduce aún más, estos tres no deben recortarse.

---

## 8. Recursos de aprendizaje (gratuitos y oficiales)

**Linux / CLI**
- Linux Foundation — "Introduction to Linux" (edX, gratuito en modo audit)

**Docker**
- Docker Docs — "Docker Overview" y "Get Started" (docs.docker.com)

**Git**
- Documentación oficial de Git — "Git Basics" (git-scm.com/book)

**Kubernetes (workloads, configuración, storage, networking)**
- Kubernetes Official Documentation — sección "Concepts → Workloads" (kubernetes.io/docs/concepts/workloads)
- Kubernetes Official Documentation — "Configuration" y "Storage" (mismas secciones de concepts)
- CNCF — "Kubernetes and Cloud Native Associate (KCNA)" material de estudio gratuito

**Helm**
- Helm Official Documentation — "Quickstart Guide" y "Chart Template Guide" (helm.sh/docs)

**Networking/DNS/TLS**
- Kubernetes Docs — "Service", "Ingress", "DNS for Services and Pods" (kubernetes.io/docs/concepts/services-networking)

**Seguridad**
- Kubernetes Docs — "RBAC Authorization" y "Secrets" (sección Concepts → Security)

**Observabilidad**
- Kubernetes Docs — "Logging Architecture" y "Application Introspection and Debugging"

**DevOps/CI-CD**
- Microsoft Learn — "DevOps Foundations" (módulo introductorio, gratuito)

**Laboratorios interactivos**
- Killercoda — escenarios interactivos de Kubernetes en navegador (killercoda.com), gratuitos y sin instalación.
- Play with Kubernetes (labs.play-with-k8s.com) para practicar comandos rápidamente.

**Recomendación general:** priorizar siempre la documentación oficial y evitar cursos de certificación completos (tipo CKA), ya que exceden el alcance del rol; usarlos solo como referencia puntual de un tema específico.

---

## 9. Laboratorios prácticos por módulo

- **M0/M1:** Crear un contenedor local, inspeccionar sus capas, revisar logs y procesos.
- **M2:** Clonar un repositorio de manifiestos, crear una rama, modificar un valor y hacer commit/diff.
- **M3:** Escribir un manifiesto YAML desde cero y validarlo con `kubectl apply --dry-run=client`.
- **M4/M5:** Crear un Deployment, escalarlo, realizar un rollout de nueva versión y ejecutar un rollback.
- **M5 (extra):** Crear un CronJob que ejecute una tarea simple y revisar su historial de ejecuciones.
- **M6:** Crear un ConfigMap y un Secret, montarlos en un Pod y verificar que el cambio se refleje tras un reinicio.
- **M7:** Crear un PVC, asociarlo a un Pod y provocar intencionalmente un estado `Pending` para diagnosticarlo.
- **M8:** Exponer un Deployment mediante un Service y un Ingress; verificar resolución DNS entre dos Pods.
- **M9:** Instalar una aplicación de ejemplo con Helm, modificar `values.yaml`, hacer `helm upgrade` y luego `helm rollback`.
- **M10:** Configurar un Role y RoleBinding con permisos mínimos; configurar TLS en un Ingress con un certificado de prueba.
- **M11:** Provocar un fallo intencional (por ejemplo, imagen incorrecta) y diagnosticarlo únicamente con logs, eventos y métricas.
- **M12:** Conectarse a una base de datos gestionada de prueba y verificar métricas de conexión/latencia.
- **M13:** Crear un bucket S3 de prueba, configurar una política de acceso y verificar permisos.
- **M15:** Redactar un runbook para el incidente simulado del M11.

---

## 10. Evaluación final

**Preguntas prácticas (ejemplos)**
1. Dado un Deployment que falla al iniciar, ¿qué comandos usarías para diagnosticarlo y en qué orden?
2. ¿Qué diferencia hay entre un PVC en estado `Bound` y uno en `Pending`, y qué acción tomarías ante cada uno?
3. Explica el flujo completo de un `helm upgrade` fallido y cómo revertirlo de forma segura.

**Escenarios**
- Escenario A: Un Pod del Middleware reinicia constantemente (`CrashLoopBackOff`). El participante debe diagnosticar la causa usando solo logs y eventos.
- Escenario B: La aplicación no puede conectarse a la base de datos gestionada. El participante debe distinguir si el problema es de configuración (Secret/ConfigMap), de red (Service/DNS) o corresponde escalarlo al proveedor de DBaaS.
- Escenario C: Un Ingress no enruta correctamente el tráfico. El participante debe identificar si el problema es de configuración de aplicación o si debe escalarse a infraestructura.

**Ejercicios**
- Desplegar, actualizar y revertir una aplicación de ejemplo usando Helm sin asistencia.
- Redactar un runbook completo para un incidente simulado.

**Lista de competencias mínimas para aprobar**
- [ ] Puede leer y modificar un manifiesto YAML sin errores de sintaxis.
- [ ] Puede realizar un rollout y un rollback de un Deployment.
- [ ] Puede diagnosticar un Pod fallido usando logs y eventos.
- [ ] Puede instalar, actualizar y revertir un release con Helm.
- [ ] Puede identificar si un incidente corresponde al Middleware o a infraestructura.
- [ ] Puede documentar un incidente siguiendo un formato estándar.

---

## 11. Checklist final de disposición para el entrenamiento ESA

- [ ] Domina comandos básicos de Linux (permisos, procesos, logs).
- [ ] Entiende la diferencia entre imagen, contenedor y Pod.
- [ ] Puede versionar cambios de configuración con Git.
- [ ] Escribe y valida manifiestos YAML sin asistencia.
- [ ] Comprende y opera Deployments, StatefulSets, Jobs y CronJobs.
- [ ] Gestiona ConfigMaps y Secrets de forma segura.
- [ ] Verifica el estado de PVCs y entiende su relación con StorageClass.
- [ ] Comprende Service, Ingress, DNS interno y NetworkPolicy básica.
- [ ] Despliega, actualiza y revierte aplicaciones con Helm.
- [ ] Aplica RBAC de mínimo privilegio y configura TLS de aplicación.
- [ ] Diagnostica incidentes correlacionando logs, eventos y métricas.
- [ ] Monitorea salud y conectividad de bases de datos gestionadas.
- [ ] Opera almacenamiento de objetos S3 a nivel de acceso y políticas.
- [ ] Redacta runbooks y documenta incidentes con estructura clara.
- [ ] Distingue con claridad qué es responsabilidad del Middleware y qué corresponde escalar al proveedor de infraestructura o a ESA.

Si un participante marca todos los puntos anteriores, está listo para aprovechar al máximo el entrenamiento oficial de ESA sobre el Middleware de Copernicus.
