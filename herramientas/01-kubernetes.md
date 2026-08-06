# Kubernetes — workloads, configuración, almacenamiento y red de aplicación

**Nivel exigido:** E (workloads y configuración) · O (almacenamiento y red de aplicación)
**Prioridad:** 1 — núcleo diario
**Competencias de la matriz:** 5, 6, 7, 8

---

## 1. Qué es, aquí

Kubernetes es el sustrato de **todo** el Middleware CopernicusLAC. No es un componente: es
donde viven los ocho. D2 lo describe como la plataforma de orquestación que gestiona
despliegue, escalado y operación de los contenedores, distribuyéndolos sobre la
infraestructura, balanceando carga y reiniciando o relocalizando contenedores que fallan.

El clúster lo entrega el proveedor como **KaaS** (Kubernetes as a Service). D2 §2.5 lo
declara como supuesto de diseño: *"the system will be deployed in an infrastructure that
provides Kubernetes as a Service (KaaS) and Databases as a Service (DBaaS)"*, y advierte la
consecuencia: *"the system's performance and availability are partly contingent on the
reliability and capabilities of the provider"*.

Traducción operativa: **tú no administras Kubernetes, operas dentro de Kubernetes.** Esa
distinción es el eje de tu rol y la fuente de la mitad de los malentendidos que vas a tener
con el proveedor.

---

## 2. La frontera

| Materia | Proveedor (pliego §8.5.3, §8.5.7) | Tú (perfil ESA §2.3.1, §2.3.2) |
|---|---|---|
| Ciclo de vida del clúster | Despliegue, configuración inicial, upgrades, parcheo, HA, ETCD, nodos maestros | Nada |
| Nodos y SO | Aprovisionamiento, parcheo, etiquetado (a petición), autoescalado | Nada |
| Red del clúster | CNI, red interna, topología | Nada |
| StorageClass | Provisión y gestión | Consumo (PVC) |
| Ingress Controller | Operación del controlador | Recursos `Ingress` del Middleware |
| RBAC del clúster | Autenticación, aislamiento de namespaces | RBAC lógico dentro de tus namespaces |
| **Workloads** | — | **Deployments, StatefulSets, Jobs, CronJobs, rollouts, rollbacks** |
| **Configuración** | — | **ConfigMaps, Secrets, montajes, rotación** |
| **Cuotas y NetworkPolicies** | Aislamiento base | **Cuotas y políticas de aplicación** |

El perfil ESA lo dice con esta frase exacta, que conviene memorizar:

> *Includes log inspection, basic diagnostics, and review of events and metrics for
> troubleshooting purposes only. **Excludes cluster upgrades, ETCD management, OS patching,
> or base runtime maintenance.***

### Lo que el pliego te habilita a pedir (§8.5.16)

El proveedor **debe poder ejecutar o habilitar** estas funciones sobre el KaaS. Conócelas de
memoria: son tu palanca cuando necesitas algo que no puedes hacer tú.

- Configurar StorageClasses
- Desplegar Ingresses específicos
- Etiquetar nodos
- Desplegar custom controllers
- Editar deployments
- Conectarse a pods
- Revisar eventos y métricas para diagnóstico

### Cómo accedes

Acceso a la **API de Kubernetes y a la de S3 por VPN** (recomendado en el pliego) o
interfaz web. Confirma con el proveedor qué permisos exactos trae tu `kubeconfig` antes de
planificar cualquier cosa (ver §11).

---

## 3. Qué debes saber

### Nivel imprescindible (sin esto no operas)

**Objetos de carga**
- `Pod`: qué es realmente, por qué casi nunca lo creas directamente, ciclo de vida y fases.
- `Deployment`: réplicas, `strategy` (RollingUpdate vs Recreate), `maxSurge`/`maxUnavailable`,
  ReplicaSets que deja detrás, `revisionHistoryLimit`.
- `StatefulSet`: identidad estable de red y de almacenamiento, `volumeClaimTemplates`,
  `serviceName`, orden de creación y de borrado, `podManagementPolicy`. **Por qué el
  catálogo y las bases de datos usan esto y no un Deployment.**
- `Job` y `CronJob`: `completions`, `parallelism`, `backoffLimit`, `activeDeadlineSeconds`,
  `ttlSecondsAfterFinished`, `concurrencyPolicy`, `successfulJobsHistoryLimit`. Los
  workflows de Argo se materializan como pods; los pods `Completed` acumulados son un
  problema real.
- `DaemonSet`: qué es y por qué normalmente no es tuyo.

**Configuración**
- `ConfigMap`: montaje como volumen vs. como variable de entorno. Diferencia clave: el
  volumen se actualiza solo (con retardo), la variable de entorno **no** — requiere reinicio.
- `Secret`: tipos (`Opaque`, `kubernetes.io/dockerconfigjson`, `kubernetes.io/tls`),
  codificación base64 (que **no** es cifrado), montaje, rotación sin exponer valores.
- `imagePullSecrets` y su relación con Harbor.
- Precedencia: `env` > `envFrom` > valor en la imagen.

**Recursos y salud**
- `resources.requests` vs `resources.limits`; qué significa cada uno para el scheduler y
  para el kernel. D2 §6.8.7 lo exige explícitamente:
  *"developers SHOULD define resource requests and limits within their Kubernetes deployment
  configurations"*.
- Clases de QoS: `Guaranteed`, `Burstable`, `BestEffort`, y cuál se desaloja primero.
- `livenessProbe`, `readinessProbe`, `startupProbe`: qué hace cada una al fallar,
  `initialDelaySeconds`, `periodSeconds`, `failureThreshold`. **El error más común es usar
  liveness donde correspondía readiness y provocar reinicios en cascada.**

**Diagnóstico**
- Estados y su causa: `Pending`, `ContainerCreating`, `CrashLoopBackOff`, `ImagePullBackOff`,
  `ErrImagePull`, `OOMKilled`, `Evicted`, `Error`, `Completed`, `Terminating` colgado.
- Secuencia fija de comandos (§8).
- Leer `kubectl describe` de verdad: sección `Events`, `Last State`, `Exit Code`, `Reason`.

### Nivel operativo (lo haces bajo presión)

**Almacenamiento**
- `PersistentVolumeClaim`: `accessModes` (`ReadWriteOnce`, `ReadWriteMany`, `ReadOnlyMany`),
  `storageClassName`, `resources.requests.storage`.
- `StorageClass`: `provisioner`, `reclaimPolicy`, `volumeBindingMode`
  (`Immediate` vs `WaitForFirstConsumer` — causa frecuente de `Pending`),
  `allowVolumeExpansion`.
- Expansión de un PVC en caliente y sus límites.
- Diagnóstico de `Pending`: ¿no existe la StorageClass? ¿no hay capacidad? ¿el modo de
  acceso no lo soporta el provisionador? ¿`WaitForFirstConsumer` esperando un pod
  programable?
- Contexto: hay **25 TB de block storage SSD** contratados para PVC. No es infinito.

**Red de aplicación**
- `Service`: `ClusterIP`, `NodePort`, `LoadBalancer`, `ExternalName`, `headless`
  (`clusterIP: None`, el que usan los StatefulSets). `targetPort` vs `port` — el 502 más
  común del mundo vive aquí.
- DNS interno: `<svc>.<ns>.svc.cluster.local`, resolución entre namespaces.
- `Endpoints`/`EndpointSlice`: cómo comprobar que un Service **realmente** apunta a pods.
- `NetworkPolicy`: `podSelector`, `ingress`/`egress`, política por defecto deny, y el error
  clásico de cortar el DNS (kube-dns/CoreDNS vive en `kube-system`).
- `Ingress`: `ingressClassName`, `rules`, `paths`, `pathType`, `tls`. Detalle en
  [18-ingress-tls-cert-manager.md](18-ingress-tls-cert-manager.md).

**Seguridad lógica**
- `ServiceAccount`, `Role`, `RoleBinding`, `ClusterRole`, `ClusterRoleBinding`. Cuál usar
  dentro de tu namespace.
- `kubectl auth can-i` — tu herramienta de verificación, incluida `--as` para suplantar.
- `ResourceQuota` y `LimitRange`: por qué un namespace rechaza pods.
- Mínimo privilegio: es principio explícito de D1 §3.2.2 y de D2 §8.4.

### Nivel avanzado (lo diseñas)

- `PodDisruptionBudget` y su relación con los mantenimientos del proveedor (los avisados con
  48 h del pliego).
- Afinidad, antiafinidad y `topologySpreadConstraints` para HA real entre zonas.
- `HorizontalPodAutoscaler` sobre métricas de Prometheus.
- `initContainers` y sidecars: dónde encajan en los flujos de ingesta.
- Terminación limpia: `terminationGracePeriodSeconds`, `preStop`, señales.
- Presupuesto de recursos por namespace frente a los **496 vCPU / 1.984 GB RAM** totales
  contratados.

---

## 4. Datos de la plataforma que debes tener a mano

**Infraestructura contratada (Anexo I del pliego):**

| Recurso | Cantidad |
|---|---|
| Nodos del K8s administrado | hasta 500 VMs (D1 pedía 1000) |
| VMs para componentes | 10 × 4 vCPU/16 GB + 15 × 8 vCPU/32 GB |
| VMs para procesamiento | 8 × 8/32 + 8 × 16/64 + 4 × 32/128 |
| Block storage SSD (PVC) | 25 TB |
| Total | 50 recursos, 496 vCPU, 1.984 GB RAM, 40,3 TB SSD |
| Balanceador | HA ≥ 1 Gbps, 25.000 RPS pico, 10.000 conexiones |

**Objetivos que el clúster debe sostener (D1):** 3.000 usuarios concurrentes, respuesta
media < 5 s y ≤ 7,5 s en pico, utilización de recursos objetivo **50–70 %**, disponibilidad
99,5 % anual con MTTR < 1 h.

**Dónde aparece Kubernetes en cada componente (D2 §3):**

- **Data Ingestion** (§3.1.4): *"Kubernetes is used for deploying and managing the
  containerized ingestion pipelines"*.
- **Data Processing** (§3.3.4): *"Manages and orchestrates the execution of containerized
  processing tasks, providing dynamic scaling and reliability"*. Calrissian ejecuta CWL
  nativamente sobre K8s.
- **User Workspace** (§3.6.2): *"Each user has a dedicated namespace on the Kubernetes
  cluster managed by Crossplane, which provisions necessary resources such as S3 buckets and
  Helm releases"*. **Un namespace por usuario** — esto escala a miles de namespaces.
- **Resource Management** (§3.8.4): Crossplane + Helm + ESO sobre Kubernetes.
- **Deployment** (§6.4): *"The application is deployed as Kubernetes pods, with each pod
  running a containerized version of the application"*, con configuraciones vía Helm charts.

---

## 5. Laboratorio

**Maqueta:** `kind` o `k3d` local = el KaaS del proveedor.

```bash
kind create cluster --name copernicus-lab
kubectl cluster-info --context kind-copernicus-lab
```

1. **Deployment con todo lo que importa.** 3 réplicas, `resources` (requests y limits),
   `livenessProbe` y `readinessProbe` sobre `/health`, un `ConfigMap` montado como volumen y
   una variable desde `envFrom`. Escríbelo **a mano**, no lo generes.
2. **Rollout.** Cambia la imagen. Observa `kubectl rollout status`, `kubectl rollout history`,
   `kubectl get rs` (verás el ReplicaSet viejo con 0 réplicas). Revierte con
   `kubectl rollout undo` y comprueba que volviste.
3. **StatefulSet.** Convierte un caso a `StatefulSet` con `volumeClaimTemplates` y un
   Service headless. Escala a 3, borra el pod `-1` y observa que vuelve con el **mismo**
   nombre y el **mismo** volumen. Explica en voz alta por qué el catálogo lo necesita.
4. **Job y CronJob.** Crea un `Job` que falle, observa `backoffLimit`. Crea un `CronJob`
   cada minuto, revisa `successfulJobsHistoryLimit` y qué pasa si no lo limitas.
5. **Secret.** Créalo, móntalo como archivo y como variable, y **verifica que no aparece en
   los logs ni en `kubectl describe`**. Rótalo y observa qué pasa con el pod (spoiler: nada,
   hasta que reinicies — ese es el aprendizaje).
6. **PVC.** Pide un volumen, móntalo, escribe, borra el pod, comprueba que el dato sigue.
7. **RBAC.** Crea un `ServiceAccount` con un `Role` de solo lectura sobre pods y verifica
   con `kubectl auth can-i get pods --as=system:serviceaccount:<ns>:<sa>`.
8. **NetworkPolicy.** Permite solo que el catálogo hable con la base de datos; comprueba
   desde un tercer pod que lo demás queda bloqueado.

Sugerencia: instala `k9s`. Reduce a la mitad el tiempo de lectura del clúster.

---

## 6. Sabotajes obligatorios

Uno por sesión. **Provocarlo tú vale diez veces más que leerlo.**

| Sabotaje | Qué aprendes a leer |
|---|---|
| Imagen inexistente o tag equivocado | `ImagePullBackOff` vs `ErrImagePull`, eventos del pod |
| `imagePullSecret` borrado | El mismo síntoma, causa distinta — cómo distinguirlos |
| Límite de memoria demasiado bajo | `OOMKilled`, `Last State`, `Exit Code: 137` |
| Probe apuntando al puerto equivocado | Reinicios eternos con la app sana; `Liveness probe failed` |
| `ConfigMap` renombrado | `CreateContainerConfigError`, pod que nunca arranca |
| PVC con StorageClass inexistente | `Pending` con evento `no persistent volumes available` |
| Réplicas que exceden la `ResourceQuota` | El Deployment no crea pods y el error está en el ReplicaSet, no en el pod |
| `Service` con `targetPort` equivocado | 502 desde el Ingress, `Endpoints` vacío |
| `NetworkPolicy` que corta el DNS | `connection refused` a nombres, funciona por IP |
| `RoleBinding` en el namespace equivocado | `Forbidden` con mensaje que nombra el SA correcto |

---

## 7. Averías de producción que este bloque entrena

Del catálogo de averías (§16 de la guía): 1 (`CrashLoopBackOff` por ConfigMap renombrado),
2 (`ImagePullBackOff` por credenciales), 3 (`OOMKilled`), 4 (PVC `Pending`), 5 (Ingress 502),
15 (namespace que rechaza pods por cuota), 16 (servicio inalcanzable por NetworkPolicy que
corta DNS), 17 (base de datos inalcanzable por credencial rotada sin actualizar el Secret).

---

## 8. Secuencia de diagnóstico (memorízala)

```bash
kubectl get pods -o wide -n <ns>                    # ¿qué estado, en qué nodo, cuántos reinicios?
kubectl describe pod <pod> -n <ns>                  # eventos, Last State, Exit Code, Reason
kubectl logs <pod> -n <ns>                          # el error de la app
kubectl logs <pod> -n <ns> --previous               # el error del contenedor MUERTO (clave)
kubectl get events -n <ns> --sort-by=.lastTimestamp # el orden real de los hechos
kubectl exec -it <pod> -n <ns> -- sh                # conectividad, DNS, permisos desde dentro
kubectl top pod -n <ns>                             # consumo real vs límites
```

Qué descarta cada uno:

| Comando | Si sale limpio, descarta |
|---|---|
| `get pods -o wide` | Que el problema sea de programación o de nodo |
| `describe pod` | Que sea imagen, montaje, cuota, probe o desalojo |
| `logs --previous` | Que sea un fallo de arranque de la aplicación |
| `get events` | Que sea el scheduler, el kubelet o el provisionador de volúmenes |
| `exec` + `nslookup`/`curl` | Que sea DNS, red o política de red |
| `top pod` | Que sea presión de memoria o CPU |

Complementos útiles:

```bash
kubectl get endpoints <svc> -n <ns>                 # ¿el Service apunta a algo?
kubectl auth can-i <verbo> <recurso> -n <ns>        # ¿es RBAC?
kubectl describe quota -n <ns>                      # ¿es cuota?
kubectl get pvc -n <ns> && kubectl describe pvc <pvc> -n <ns>
kubectl apply --dry-run=server -f manifiesto.yaml   # valida contra el API, no solo sintaxis
kubectl diff -f manifiesto.yaml                     # qué cambiaría exactamente
```

---

## 9. Criterio de dominio

- [ ] Escribo desde cero un `StatefulSet` con volúmenes, probes y recursos, y lo valido antes de aplicar.
- [ ] Explico la diferencia entre `Deployment` y `StatefulSet` con un ejemplo de la plataforma.
- [ ] Hago rollout, veo el historial y revierto sin consultar nada.
- [ ] Ante un pod que reinicia, tengo una secuencia fija y sé qué descarta cada paso.
- [ ] Distingo `ImagePullBackOff` por credenciales, por tag inexistente y por registro inalcanzable.
- [ ] Diagnostico un PVC `Pending` y sé si la causa es mía o del proveedor.
- [ ] Sé por qué un `Service` devuelve 502 y lo compruebo con `get endpoints`.
- [ ] Escribo una `NetworkPolicy` que no rompe el DNS.
- [ ] Verifico permisos con `kubectl auth can-i` antes de afirmar que "no tengo acceso".
- [ ] Un compañero me da un clúster roto y localizo la causa en **menos de 10 minutos** usando solo mi runbook.

---

## 10. Artefacto que produces

`runbooks/diagnostico-pod.md` — la secuencia fija de §8 con la interpretación de cada estado.

**Alimenta:** Producto 2 del contrato (runbooks iniciales) y Producto 3 (ajustados a
escenarios reales). Es también la base del Producto 4 (transferencia): es el primer
documento que le vas a enseñar al recurso designado por AIG.

---

## 11. Qué preguntar

**Al proveedor:**
1. ¿Qué acceso tendré a la API de Kubernetes, por qué vía (VPN o web) y con qué permisos exactos? ¿Me pasan el `kubeconfig` o lo genero yo?
2. ¿Qué StorageClasses existen, con qué parámetros (`volumeBindingMode`, `allowVolumeExpansion`, `reclaimPolicy`) y cuál es el procedimiento para pedir una nueva?
3. ¿Cómo accedo a métricas, logs y eventos del clúster, y con qué retención?
4. ¿Qué versión de Kubernetes corre y cuál es la política de upgrades? ¿Cómo se notifican?
5. ¿Hay `PodSecurityStandards` o admission controllers que restrinjan lo que puedo desplegar?

**A ESA / Terradue:**
1. ¿Cuál es el mecanismo oficial de despliegue: charts propios, GitOps con ArgoCD, o ambos? ¿Dónde vive el repositorio de referencia?
2. ¿Qué namespaces usa el Middleware y cuál es el mapa de qué corre dónde?
3. ¿Existe entorno de pruebas o solo producción? ¿Cómo se valida un cambio antes de aplicarlo?

---

## 12. Fuentes

**Documentos del proyecto:** D2 §2.5 (supuestos KaaS/DBaaS), §3.1.4, §3.3.4, §3.6.2, §3.8.4
(stacks por componente), §6.4 (despliegue), §6.8.7 (recursos), §7.4 (Kubernetes), §9.2
(escalabilidad). Pliego §8.5.3, §8.5.7 (responsabilidades del proveedor), §8.5.16
(funciones mínimas del KaaS administrado), Anexo I (infraestructura). Perfil ESA §2.3.1,
§2.3.2 y tabla §1.1.

**Documentación oficial:** `kubernetes.io/docs` → Concepts (Workloads, Configuration,
Storage, Services/Networking, Security) y *"Application Introspection and Debugging"*, que
es literalmente el capítulo de tu trabajo.

**Deliberadamente fuera:** instalación del clúster, `kubeadm`, `etcd`, CNI, administración
de nodos. Es del proveedor. Necesitas el vocabulario, no la práctica. Evita CKA/CKS
completos por la misma razón.

---

## 13. Bitácora / hallazgos

*(Añade aquí lo que aprendas en la operación real: versiones, StorageClasses reales,
límites que descubras, comandos que resolvieron un incidente.)*
