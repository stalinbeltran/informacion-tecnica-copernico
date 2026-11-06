# CopernicusLAC Infrastructure — Training Plan (referencia para Claude)

## Instrucciones para Claude

Este archivo resume el documento **T2-ESA-COPLACI-PL-26-049, Issue 2.4 (2026-10-28)**, "CopernicusLAC Infrastructure Training Plan", preparado por Terradue bajo el contrato ESA 4000144570/24/I-KE. El usuario (Stalin, desarrollador en AIG, Panamá) es participante del programa y te consultará sobre él.

- Responde en español, de forma breve y directa. Mantén en inglés los nombres técnicos (Argo CD, merge request, kubeconfig, etc.).
- Responde solo con lo que está aquí. Si algo no aparece (enlaces de reunión, credenciales, lista de participantes, contenido exacto de los module packs, texto de la Deployment Guide v2.2), dilo y sugiere preguntar al AIG coordinator o a Terradue.
- Cita la sección del plan (p. ej. "§3") cuando ayude a verificar.
- Para preguntas de fechas ("¿qué toca esta semana?", "¿qué debo preparar?"), usa la fecha actual, el calendario (§3) y los plazos de preparación (§2.1).
- Horas siempre en hora de Panamá (UTC−5), salvo que se pida otra.
- Distingue siempre entre lo que el aprendiz **hace** y lo que queda **fuera de alcance** (columna "límite").
- El plan es un documento vivo: si el usuario indica un cambio de fecha o alcance, prevalece lo que diga él.

## 1. Datos generales (§1)

| Campo | Valor |
|---|---|
| Programa | Formación en infraestructura CopernicusLAC para administradores de sistemas e ingenieros de plataforma de AIG |
| Marco | Training, Transfer and Handover Plan (D5) |
| Duración | 6 nov 2026 – 5 feb 2027 |
| Modalidad | Talleres remotos + aprendizaje de fundamentos + evento presencial obligatorio |
| Entorno | Infraestructura objetivo (target) real |
| Participantes | 3 a 5 aprendices |
| Referencia técnica | Deployment Guide v2.2; responsabilidades operativas en el Infrastructure System Design Document (D4) §2.2 |

**Temas prácticos:** acceso e identidad, despliegue y cambio controlado, ingesta y descubrimiento de datos, procesamiento BAS (Burned Area Severity) y DInSAR, operación diaria, diagnóstico de fallos y recuperación acotada.

**Progresión del despliegue:** cambio de configuración controlado (M01) → aplicación pequeña (M05) → servicio representativo de plataforma (M08, presencial).

**Fuera del programa** (se cubre en el handover general, §10): reconstrucción completa de la plataforma, administración de infraestructura, upgrades y recuperación avanzada.

## 2. Método y carga de trabajo (§2)

- Cada taller sigue una historia operativa y un resultado práctico principal. El instructor explica, demuestra una vez, guía la práctica y revisa la evidencia individual.
- Los aprendices reciben instrucciones paso a paso y configuración preparada.
- **Worksheet del participante:** cada uno anota qué hizo, qué resultado obtuvo y qué ayuda necesitó.
- **Preparación previa:** leer las instrucciones del taller, 20–30 min. El aprendizaje de fundamentos es adicional.
- **Problemas técnicos:** se registran con un responsable. Puede sustituirse por una demostración, pero la práctica queda pendiente hasta que el aprendiz la ejecute.
- Talleres remotos: 150 o 180 min, con un descanso de 10 min incluido.
- Materiales publicados al menos 3 días hábiles antes de cada taller.
- No se exigen cursos completos ni certificaciones.
- Presencial: los 3 días completos y la mañana final de 4 horas son obligatorios.

### 2.1 Fundamentos y plazos de preparación

M00 detecta las brechas de cada aprendiz (autoevaluación + pruebas cortas). Instructor y AIG coordinator acuerdan qué estudiar, fechas y verificaciones. AIG garantiza que se cierren antes del taller dependiente. Se aceptan recursos equivalentes.

| Tema | Recurso recomendado | Qué repasar | Listo antes de |
|---|---|---|---|
| Git | GitHub Learn: Introduction to Git | Repositorios, ramas, commits, diffs, recuperación (se aplica en GitLab) | M01 (19 nov) |
| YAML | Documentación de Ansible: YAML Syntax | Mapas, listas, indentación, strings, booleanos (sin formación en Ansible) | M01 (19 nov) |
| Contenedores | Docker: Build and share a containerized application | Imágenes, ejecución, puertos, logs (sin publicar imágenes) | Conceptos básicos: M01 (19 nov); resto: M05 (14 ene) |
| Kubernetes | Linux Foundation LFS158 | Workloads, Services, configuración, almacenamiento persistente | Recursos y estados básicos: M01 (19 nov); despliegue: M05 (14 ene) |
| Linux | Linux Foundation LFS101 | Shell, archivos, permisos, procesos, logs | M02 (26 nov) |
| Redes | Cisco Networking Academy: Networking Basics | IP, puertos, DNS, protocolos de transporte | M02 (26 nov) |
| Identidad | Keycloak Server Administration Guide + Getting Started | Autenticación, autorización, SSO, realms, usuarios, roles, grupos, clients | M03 (3 dic) |
| Object storage | Amazon S3 User Guide + StorageGRID S3 access keys | Buckets, objetos, keys, credenciales, permisos | M04 (17 dic) |

## 3. Calendario (§3)

Sesiones remotas: **09:00 Panamá / 15:00 Roma**.

| Fecha | Día | Sesión | Duración | Modalidad |
|---|---|---|---|---|
| 29 oct 2026 | jue | Plan compartido con ESA y AIG | — | — |
| 6 nov 2026 | vie | Briefing: programa, objetivos, prerrequisitos, participación | 60 min | Remota |
| 12 nov 2026 | jue | M00 Orientación de plataforma y acceso | 150 min | Remota |
| 19 nov 2026 | jue | M01 Propiedad del despliegue y cambio GitOps controlado | 180 min | Remota |
| 26 nov 2026 | jue | M02 Diagnóstico de los fundamentos de la plataforma | 180 min | Remota |
| 3 dic 2026 | jue | M03 Acceso de usuarios y servicios de trabajo | 180 min | Remota |
| 17 dic 2026 | jue | M04 Ingesta y descubrimiento de un dataset pequeño | 180 min | Remota |
| 14 ene 2027 | jue | M05 Despliegue y verificación de una aplicación pequeña | 150 min | Remota |
| 21 ene 2027 | jue | M06 Ejecución de BAS y DInSAR | 150 min | Remota |
| 28 ene 2027 | jue | M07 Operación diaria y preparación para el presencial | 150 min | Remota |
| 2 feb 2027 | mar | M08 Día 1: despliegue de un componente representativo | 6 h | Presencial |
| 3 feb 2027 | mié | M08 Día 2: operación, ejecución de servicios de procesamiento, diagnóstico | 6 h | Presencial |
| 4 feb 2027 | jue | M08 Día 3: diagnóstico, cambio controlado, rollback, recuperación acotada | 6 h | Presencial |
| 5 feb 2027 | vie | M08 Día 4: revisión práctica, feedback individual, repetición dirigida, cierre | 4 h | Presencial |

- **Sin sesión:** 10 dic 2026. **Pausa:** 21 dic 2026 – 10 ene 2027.
- **Total programado: 45 h** = 23 h remotas (1 h briefing + 22 h en 8 talleres) + 22 h presenciales. La preparación y los fundamentos son adicionales.

## 4. Módulos: qué hace el aprendiz, evidencia y límites (§4–§5)

### M00 — Orientación y acceso (12 nov)
- **Hace:** inicia sesión con sus propias cuentas (Keycloak con OTP, kubeconfig de Rancher, GitLab); ejecuta comprobaciones de solo lectura en el clúster; ubica cada componente en su tier de despliegue y nombra a su responsable; completa autoevaluación y pruebas cortas; acuerda su plan personal de preparación.
- **Evidencia:** resultado de cada comprobación de acceso; resultados de la autoevaluación; acciones de aprendizaje con fechas y seguimiento.
- **Límite:** solo lectura, sin cambios en la plataforma.

### M01 — Propiedad del despliegue y cambio GitOps (19 nov)
- **Hace:** explica los tiers y quién cambia cada uno; modifica un campo permitido (un campo de mensaje) mediante un merge request en GitLab; verifica que Argo CD y Crossplane lo aplicaron; restaura el valor original con un revert.
- **Tiers:** Tier 1 = aplicaciones manuales; Tier 2 = componentes gestionados con helmfile (incluye los componentes Crossplane); Tier 3 = recursos automatizados (vía Argo CD; el ejercicio de M01 es un cambio Tier 3).
- **Evidencia:** referencia del merge request y del commit; estado de la Application de Argo CD y del Object de Crossplane; valor del ConfigMap antes, después y tras el revert.
- **Límite:** solo el repositorio y la Application de formación; no se instala ni reconfigura ningún controlador o servicio existente.

### M02 — Diagnóstico de fundamentos (26 nov)
- **Hace:** diagnostica un fallo preparado en una ruta de formación (secret, certificado, routing o workload) con comprobaciones de solo lectura, de las capas inferiores hacia arriba, y nombra al responsable.
- **Evidencia:** condición observada, capa probable, siguiente comprobación y responsable.
- **Límite:** el instructor planta y repara el fallo; los aprendices no cambian nada en el clúster.

### M03 — Acceso de usuarios y servicios (3 dic)
- **Hace:** añade un rol o grupo a su propio usuario de prueba; verifica el efecto con un login nuevo en App Hub (inicia un notebook) y Drive (abre un archivo); lo retira y confirma que el acceso se deniega.
- **Evidencia:** usuario de prueba, rol cambiado, resultados del login, restauración.
- **Límite:** solo usuarios de prueba; sin cambios de realm, client, políticas ni servicios. OPA se explica solo como dependencia de autorización.
- **Nota:** la disponibilidad de App Hub y Drive se verifica antes; lo que no esté disponible se reprograma y queda pendiente.

### M04 — Ingesta y descubrimiento (17 dic)
- **Hace:** sigue una ingesta real iniciada por el operador asignado; busca personalmente el nuevo ítem en el catálogo, revisa sus metadatos y abre su asset.
- **Evidencia:** operador e identificador de la ingesta; búsqueda, identificador del ítem, metadatos revisados y resultado de acceso al asset de cada aprendiz.
- **Límite:** un ítem sintético por sí solo no demuestra la ingesta.

### M05 — Despliegue de una aplicación pequeña (14 ene)
- **Hace:** despliega una aplicación preparada (workload + Service) por la ruta GitOps aprobada; verifica que está lista y devuelve el resultado esperado; la elimina por el proceso documentado.
- **Evidencia:** referencias de merge requests; workload listo; salida funcional; eliminación confirmada.
- **Límite:** se usan los controladores existentes, no se reinstalan.
- **Nota:** incluye el *integration checkpoint* operativo y prepara el despliegue presencial.

### M06 — BAS y DInSAR (21 ene)
- **Hace:** lanza al menos una ejecución de referencia por la processing API con su propia cuenta; la sigue hasta que termina; explica cómo llegan los resultados de BAS y DInSAR al almacenamiento y al catálogo.
- **Evidencia:** identificadores de ejecución, estado final, ubicación de la salida e ítem de catálogo; explicación de ambas rutas de resultados.
- **Límite:** las salidas aún pendientes se cierran en M07.

### M07 — Operación diaria y preparación presencial (28 ene)
- **Hace:** ejecuta los health checks diarios; hace el triage de un incidente a partir de la evidencia; redacta una nota de traspaso (handoff) con responsable de escalamiento; cierra la evidencia pendiente de M06.
- **Evidencia:** registro de comprobaciones diarias; evidencia del triage; nota de handoff; salidas de M06 cerradas.
- **Límite:** las comprobaciones privilegiadas puede ejecutarlas el instructor e interpretarlas el aprendiz.

### M08 — Taller presencial (2–5 feb)
- **Hace:** en grupo, despliega y verifica un servicio de plataforma seleccionado, con un paso asignado a cada aprendiz; opera la plataforma; diagnostica fallos; hace un cambio con rollback; participa en una recuperación acotada y verifica el resultado; completa un intento individual observado el Día 4.
- **Servicio candidato:** STAC API + TiTiler sobre pgSTAC, con un PostgreSQL externo preparado. El alcance se confirma antes del evento según la Deployment Guide v2.2, la duración y el aislamiento requerido.
- **Evidencia:** paso de despliegue por aprendiz; evidencia de configuración, salud y funcionamiento; nivel de asistencia por tarea.
- **Límite:** las cuatro fechas son obligatorias; no se infiere competencia en reconstrucción completa de la plataforma.
- **Dinámica:** los aprendices rotan entre ejecutar, seguir el procedimiento y revisar resultados.

**Agenda del Día 1 (6 h, descansos aparte):**

| Bloque | Duración |
|---|---|
| Secuencia y responsables | 45 min |
| Configuración preparada y dependencias | 45 min |
| Instalación guiada | 120 min |
| Verificación funcional | 60 min |
| Cambio y rollback dirigidos por aprendices | 60 min |
| Evidencia y correcciones al runbook | 30 min |

**Día 4 (4 h):** con hasta 5 aprendices, cada uno tiene un intento observado de unos 30 min mientras los demás hacen revisiones de solo lectura; el resto del tiempo es para feedback y acciones residuales.

## 5. Preparación del entorno (§6)

Antes de cada taller, Terradue coordina con AIG (y con Ifx-Ufinet cuando aplique) estas verificaciones, solo para las actividades de ese taller:

| Verificación | Qué se comprueba |
|---|---|
| Acceso del aprendiz | Puede iniciar sesión y hacer las tareas autorizadas |
| Servicios requeridos | Componentes y conexiones disponibles y funcionando |
| Recursos del ejercicio | Cuentas, configuración, datos y capacidad de almacenamiento/cómputo |
| Validación del ejercicio | Instrucciones probadas en el entorno objetivo, con resultados esperados y duración adecuada |
| Ejecución segura y limpieza | Límites que protegen los servicios operativos y procedimiento para revertir; los ejercicios de recuperación exigen backup utilizable y procedimiento probado |
| Soporte técnico | Contactos y ruta de escalamiento identificados |

Si algo no se cumple, se resuelve o se reprograma. Una demostración cuenta como "aprendizaje observado"; el resultado práctico sigue pendiente. Los problemas técnicos se registran aparte de las brechas de preparación del aprendiz.

## 6. Cobertura de infraestructura (§7)

Aparecer en la tabla no implica que los aprendices instalen o administren el componente.

| Componente (secciones Deployment Guide) | Módulos | Alcance práctico | Fuera de alcance |
|---|---|---|---|
| RKE2, Rancher, Cilium, CoreDNS (§§3.1–3.2) | M00, M07, M08 | Identificar responsabilidades, inspeccionar indicadores de salud, comprobaciones en presencial | Aprovisionamiento del clúster y recuperación de infraestructura (Ifx-Ufinet) |
| Longhorn, monitoring, DNS, load balancing (§§2.5, 3.3–3.4, 11.2) | M02, M07, M08 | Inspeccionar indicadores y dependencias en diagnóstico y operación | Instalación y administración |
| PostgreSQL, PostGIS, StorageGRID (§3.5) | M03–M07; M08 si el despliegue lo requiere | Usar los servicios existentes, verificar acceso de aplicaciones, identificar fallos de dependencias | Despliegue y recuperación de los servicios externos |
| Harbor y registries (§§3.6–3.7, 5.5, 5.7) | M05, M08 | Usar el registry configurado y verificar acceso a imágenes | Instalación y administración; correo solo como dependencia |
| GitLab, Argo CD, Crossplane (§§2.4, 5.1–5.8, 6.1–6.2) | M01, M05, M08 | Seguir la ruta de despliegue, cambio controlado, inspeccionar la reconciliación, desplegar la aplicación o servicio | Reinstalar los controladores |
| SOPS/age, Vault, External Secrets Operator, certificados (§§4.4, 5.3, 7.1–7.3) | M02; M05 y M08 como dependencias | Inspeccionar configuración y estado permitidos para diagnosticar secrets o certificados | Configuración y administración privilegiada de secretos |
| Contour, Envoy, Knative (§§5.3, 7.3, 7.6–7.7) | M02; M05 y M08 si aplica | Diagnosticar dependencias de routing y verificar acceso | Instalar controladores compartidos o cambiar el routing compartido |
| Keycloak y OPA (§§7.4–7.6) | M03 | Cambio de rol en usuario de prueba, verificar y restaurar | Configuración de realm, autoría de políticas, administración amplia de identidad |

## 7. Cobertura de aplicaciones e integration checkpoint (§8)

| Componente (secciones) | Cobertura | Observación requerida |
|---|---|---|
| Portal, App Hub, Drive (§§10.1, 12.1) | M03 | Notebook y acceso a archivos funcionando en los servicios objetivo |
| GitLab, Harbor, SSO (§§5.4–5.7, 12.1–12.3) | M01 | Login en GitLab por su dirección HTTPS y acceso al repositorio del ejercicio |
| STAC, pgSTAC, TiTiler, browsers (§§8.3–8.6) | M04, M06, candidato M08 | Ítem real, metadatos y acceso autorizado al asset |
| Argo Workflows, CWL, Calrissian (§§9.1, 9.4) | M04 (estado), M06 (procesamiento), M07 (diagnóstico) | Runner disponible y ruta real de salida completada |
| Processing API y paquetes (§§9.3–9.4) | M06 | Paquetes disponibles; ruta end-to-end verificada con token real |
| Argo Events, CloudEvents, Kafka (§§8.1, 9.2) | Inspección de la ruta de eventos de la tarea | Evidencia ensayada; sin instalar mensajería compartida |

**Integration checkpoint (antes de M06):** verifica runners y paquetes, autenticación con cuentas de los aprendices, ejecución de BAS y DInSAR, salidas accesibles, y cuotas y tiempos de ejecución adecuados (Deployment Guide v2.2 §§9.4 y 12.1–12.2). Lo que no esté disponible se registra con responsable y fecha. La aceptación formal de la plataforma va por la gobernanza del proyecto, no por este programa.

## 8. Evaluación y registros (§9)

- **Sin examen formal ni calificación numérica.** El progreso se revisa a través de las prácticas.
- Se puede usar la Deployment Guide, los worksheets y los runbooks, y pedir ayuda.
- Por cada taller se guarda un registro breve: actividades completadas, temas a reforzar e incidencias técnicas.

| Estado | Significado |
|---|---|
| Activity completed | El aprendiz hizo la tarea y comprobó el resultado (con documentación y apoyo si hizo falta) |
| Further practice recommended | Participó, pero conviene repetir o aclarar pasos |
| Activity pending | No se realizó (problema técnico o falta de tiempo); se define una acción de seguimiento |

Al cierre, Terradue entrega un **resumen de finalización**: participación, prácticas completadas, acciones recomendadas y actividades no realizadas. AIG lo usa para asignar responsabilidades operativas.

## 9. Responsabilidades y handover (§10)

| Parte | Durante la formación | En operación y handover |
|---|---|---|
| AIG coordinator | Coordina participación, accesos, asistencia y prerrequisitos; da seguimiento a pendientes | Coordina la asignación de roles operativos y acciones de seguimiento |
| AIG Platform Operations | Participa en despliegue, comprobaciones de rutina, diagnóstico y cambios controlados | Opera la plataforma dentro de su autoridad; mantiene procedimientos y runbooks |
| AIG Technical Support and Data Management | Participa en soporte a usuarios, incidentes, ingesta y acceso a datos | Mantiene las actividades de soporte y gestión de datos asignadas |
| Terradue | Prepara e imparte la formación, guía, da feedback y registra seguimiento | **3 meses de soporte post-handover** garantizados; completa el handover técnico |
| Ifx-Ufinet | Apoya accesos y dependencias de infraestructura; participa en M08 | Mantiene y recupera la infraestructura y servicios gestionados por el proveedor |
| Project management | Coordina alcance, calendario y cambios que requieran decisión | Revisa acciones pendientes y determina la aceptación formal |

- El periodo de soporte, los contactos y la forma de abrir solicitudes se registran en el handover.
- **Ejercicio de recuperación:** antes, Terradue, AIG e Ifx-Ufinet confirman roles y verifican que haya procedimiento documentado, backup utilizable y entorno de recuperación aislado. Incluye comprobar que lo recuperado es utilizable.

## 10. Hitos de preparación (§11)

| Cuándo | Entregable | Responsable |
|---|---|---|
| Antes del programa | Lista de participantes, calendario, responsabilidades, asistencia | AIG y autoridad del proyecto con Terradue |
| Antes de M00 | Comprobación de acceso individual, asignación de ejercicios, entorno de orientación | Instructor y responsables de acceso |
| Antes de M01 | Configuración validada, acceso al repositorio, ruta de cambio autorizada, procedimiento de reset | Instructor y platform owner |
| Antes de cada publicación | Instrucciones verificadas, servicios disponibles, módulo listo | Instructor |
| ≥ 3 días hábiles antes | Worksheet, slides, instrucciones y asignaciones | Instructor, por el canal acordado |
| Antes de M06 | Paquetes de procesamiento, runner, autenticación, salidas BAS/DInSAR y duración verificados | Instructor y service owner |
| Antes del viaje presencial | M07 listo; servicio seleccionado con configuración y reset probados; escenarios de fallo; backup real y runbook de restore; agenda de 4 días | AIG, instructor e infrastructure owner |
| Después de cada sesión | Evidencia consolidada, entorno restaurado, acciones asignadas | Instructor y AIG coordinator |

- Cada pack del participante trae slides, worksheet, instrucciones prácticas y las secciones relevantes de la Deployment Guide.
- Las credenciales se entregan por separado. Las respuestas de evaluación y los escenarios de fallo los conserva Terradue.
- Pueden programarse sesiones adicionales de cierre, coordinadas entre Terradue y AIG.

## 11. Historial del documento

| Fecha | Issue | Cambio |
|---|---|---|
| 2026-10-01 | 1.0 | Borrador inicial |
| 2026-10-12 | 2.0 | Objetivos, enfoque de entrega y perfil del participante |
| 2026-10-22 | 2.1 | Estructura del material y presentación |
| 2026-10-23 | 2.2 | Actualización para Deployment Guide v2.2 |
| 2026-10-26 | 2.3 | Guía didáctica, ejemplos prácticos y referencias |
| 2026-10-28 | 2.4 | Revisión del equipo: calendario revisado, fundamentos, despliegue presencial, evaluación individual y soporte de handover |

## Glosario

- **BAS:** Burned Area Severity (severidad de áreas quemadas).
- **DInSAR:** interferometría diferencial de radar de apertura sintética.
- **D4 / D5:** Infrastructure System Design Document / Training, Transfer and Handover Plan.
- **GitOps:** los cambios se hacen en Git (merge request) y un controlador (Argo CD) los aplica al clúster.
- **Tier 1 / 2 / 3:** niveles de despliegue: manual / helmfile / automatizado.
- **STAC / pgSTAC / TiTiler:** catálogo de datos geoespaciales, su backend PostgreSQL y el servidor de tiles.
- **CWL / Calrissian:** Common Workflow Language y su runner sobre Kubernetes.
- **Ifx-Ufinet:** proveedor de la infraestructura.
