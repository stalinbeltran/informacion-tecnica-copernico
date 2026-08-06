# Crossplane — aprovisionamiento declarativo

**Nivel exigido:** C→O — empieza conceptual, pasa a operativo cuando lo toques en producción
**Prioridad:** 3 — lo tocas al operar workspaces
**Competencia de la matriz:** 11

---

## 1. Qué es, aquí

Crossplane es el **componente 8 del Middleware** (Resource Management) y el motor que crea
los workspaces de usuario. D2 §7.9:

> *"Crossplane is an open-source control plane that **extends Kubernetes to manage cloud-based
> infrastructure and services**… used to provision and manage cloud resources dynamically,
> such as databases, storage, and networking components, as part of the application deployment
> process."*

La frase que más te importa está en D2 §3.6.2, sobre el User Workspace:

> *"Each user has a **dedicated namespace** on the Kubernetes cluster **managed by
> Crossplane**, which provisions necessary resources such as **S3 buckets and Helm
> releases**."*

Es decir: cuando un usuario nuevo entra a la plataforma, Crossplane le crea su namespace, su
bucket, sus releases de Helm y sus recursos asociados. **Sin intervención humana** — hasta
que algo falla, y entonces te llaman a ti.

D2 §3.8.2 le asigna además: provisionamiento de infraestructura, configuración de recursos,
escalado dinámico, monitoreo de recursos, gestión de secretos (vía ESO) y aplicación de
políticas.

---

## 2. La frontera — matiz importante

Crossplane vive en una zona ambigua y conviene resolverla explícitamente.

- **La infraestructura base** (VMs, red, el clúster mismo) la provisiona el proveedor. Ahí
  Crossplane no manda.
- **Los recursos lógicos del Middleware** (namespaces, buckets, releases) los provisiona
  Crossplane, y esa capa es tuya: *Platform Domains Support → workspace → **Not covered***.

D2 §3.8.4 menciona *"Cloud Provider APIs: Interfaces with cloud service providers (e.g.,
AWS, Azure, GCP)"* y Terraform como opción. En Panamá, con un proveedor local y servicios
administrados, **el alcance real de Crossplane hay que confirmarlo con ESA** (§9). Puede ser
mucho menor de lo que D2 sugiere — o puede gestionar los buckets de S3 vía el proveedor
compatible.

Ésta es la razón de que el nivel sea C→O y no O: hasta que no sepas qué aprovisiona
realmente, estudiar a fondo sería apostar.

---

## 3. Qué debes saber

### Nivel conceptual (esto sí, desde ya)

**El modelo**
- **Provider**: el paquete que enseña a Crossplane a hablar con una API externa
  (AWS S3, Helm, Kubernetes, un S3 compatible…). Se instala como un `Provider` y despliega
  su propio pod.
- **ProviderConfig**: las credenciales y el endpoint que usa un Provider.
- **Managed Resource (MR)**: un recurso externo representado como objeto de Kubernetes
  (`Bucket`, `Release`, `Object`). Cluster-scoped.
- **Composition** (`XRD` + `Composition`): la plantilla que agrupa varios MRs en una unidad
  de mayor nivel. Es cómo se define "qué es un workspace".
- **Claim**: la petición que hace un usuario ("quiero un workspace"), namespaced. Instancia
  una Composite Resource que a su vez crea los MRs.

**La cadena que debes saber recorrer:**
```
Claim (namespaced)  →  Composite Resource (XR)  →  Managed Resources  →  API externa
```
Cuando algo no se aprovisiona, el diagnóstico es recorrer esa cadena de arriba abajo y
encontrar dónde se detuvo.

**Condiciones y estado**
- `Ready`, `Synced` — y qué significa cada una. `Synced: False` = Crossplane no consiguió
  hablar con la API. `Ready: False` = habló, pero el recurso aún no está listo.
- Dónde aparece el error real: en el `status.conditions` del Managed Resource, y en los
  eventos. Casi nunca en el Claim, que solo dice "no está listo".

### Nivel operativo (cuando lo toques)

- Leer por qué un recurso no se aprovisiona: recorrer Claim → XR → MR → eventos → logs del
  pod del Provider.
- `deletionPolicy` (`Delete` vs `Orphan`): qué pasa con el bucket real cuando se borra el
  claim. **Con datos de usuarios dentro, esto no es un detalle.**
- Credenciales del ProviderConfig y su rotación (vía ESO).
- Actualizar un Provider sin romper los recursos existentes.
- `connectionSecretRef`: cómo las credenciales del bucket llegan al namespace del usuario.

### Nivel avanzado

- Escribir o modificar una Composition para el workspace.
- Cuotas: cuántos recursos puede pedir un usuario.
- Qué pasa cuando se borra un usuario: limpieza de bucket, repositorio, registro.

---

## 4. Datos de la plataforma que debes tener a mano

**Lo que Crossplane aprovisiona por usuario (D2 §3.6.2 y §3.6.3):**
- Un **namespace** dedicado en Kubernetes.
- **Buckets S3** → [06-s3-minio.md](06-s3-minio.md).
- **Helm releases** → [02-helm.md](02-helm.md).
- Coordinado con **ArgoCD** (sincroniza los manifiestos del usuario) →
  [12-argocd.md](12-argocd.md) y **ESO** (secretos) →
  [14-external-secrets-operator.md](14-external-secrets-operator.md).

**El stack del componente 8 (D2 §3.8.4):** Crossplane, Kubernetes, External Secrets Operator,
Terraform (opcional), Prometheus y Grafana, Helm, APIs del proveedor cloud.

**Su papel en la escalabilidad (D2 §9.2, §9.5):**
> *"The platform leverages cloud-native technologies like Crossplane to provision and manage
> cloud resources dynamically… enabling the platform to scale infrastructure components such
> as databases, storage, and compute resources in response to increasing demands."*

Con el objetivo de **3.000 usuarios concurrentes** de D1, esto significa potencialmente miles
de namespaces y miles de buckets. La operación a esa escala es automática por diseño; tu
trabajo es que siga siéndolo.

---

## 5. Laboratorio (bloque avanzado, opcional)

Este es el laboratorio menos urgente de la carpeta. Hazlo cuando los bloques 1–8 estén
cerrados, o antes si ESA confirma que Crossplane gestiona algo que vas a tocar.

1. **Instala Crossplane** en el clúster.
2. **Instala el `provider-kubernetes`** — el más simple para entender el modelo sin
   depender de una nube.
3. **Crea un Managed Resource** (`Object`) que cree un ConfigMap. Observa `Synced` y `Ready`.
4. **Rompe el ProviderConfig** (credencial errónea) y **lee dónde aparece el error**: en el
   `status.conditions` del MR, no en el Claim.
5. **Instala el `provider-helm`** y crea un `Release` declarativamente. Compáralo con hacer
   `helm install` a mano.
6. **Escribe una Composition mínima** que agrupe un namespace + un ConfigMap, y un XRD que
   la exponga. Crea un Claim. **Recorre la cadena completa** con `kubectl` hasta ver los MRs.
7. **`deletionPolicy: Orphan`**: borra el Claim y comprueba que el recurso externo sobrevive.
   Entiende cuándo eso es lo que quieres.
8. **Si tienes MinIO**: prueba un provider de S3 apuntándolo a MinIO y crea un bucket
   declarativamente. Es lo más cercano al caso real.

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| ProviderConfig con credencial inválida | `Synced: False`; dónde está el error real |
| Provider sin instalar para un MR que lo necesita | El MR queda sin reconciliar; error de CRD desconocido |
| Composition con una referencia rota | El XR se crea pero no genera MRs |
| Borrar un Claim con `deletionPolicy: Delete` | El recurso externo desaparece. **Hazlo una vez, con un bucket de prueba** |
| Pod del Provider caído | Todo queda congelado sin error visible en los objetos |

---

## 7. Árbol de diagnóstico: "el workspace del usuario no se creó"

```bash
# 1. ¿Existe el Claim y qué dice?
kubectl get <claim-kind> -n <ns-usuario>
kubectl describe <claim-kind> <nombre> -n <ns-usuario>

# 2. ¿Se creó el Composite Resource?
kubectl get composite
kubectl describe <xr-kind> <nombre>

# 3. ¿Se crearon los Managed Resources? ← aquí suele estar la respuesta
kubectl get managed
kubectl describe bucket <nombre>          # o release, object, etc.

# 4. ¿Qué dicen las condiciones?
kubectl get managed -o custom-columns=\
KIND:.kind,NAME:.metadata.name,SYNCED:.status.conditions[?\(@.type==\"Synced\"\)].status,\
READY:.status.conditions[?\(@.type==\"Ready\"\)].status

# 5. ¿El Provider está vivo y qué dice?
kubectl get providers
kubectl get pods -n crossplane-system
kubectl logs -n crossplane-system -l pkg.crossplane.io/provider=<provider> --tail=100

# 6. ¿El ProviderConfig tiene credenciales válidas?
kubectl describe providerconfig <nombre>
```

**Regla:** el Claim casi nunca te dice el porqué. Baja hasta el Managed Resource y lee sus
`conditions`. Ahí está el mensaje de la API externa.

---

## 8. Criterio de dominio

- [ ] Explico la cadena Claim → Composite → Managed Resource → API externa.
- [ ] Distingo `Synced: False` (no pude hablar con la API) de `Ready: False` (hablé, aún no está listo).
- [ ] **Sé leer por qué un recurso no se aprovisiona**, bajando hasta el MR y sus conditions.
- [ ] Entiendo qué aprovisiona Crossplane en el workspace de usuario: namespace, buckets, releases.
- [ ] Conozco `deletionPolicy` y sus consecuencias sobre datos reales.
- [ ] Sé quién hace qué en el trío Crossplane / ArgoCD / ESO.

---

## 9. Qué preguntar

**A ESA / Terradue** — este archivo depende más que ningún otro de estas respuestas:
1. **¿Qué aprovisiona Crossplane realmente en el despliegue de Panamá?** ¿Solo recursos lógicos (namespaces, buckets, releases) o también infraestructura del proveedor?
2. ¿Qué Providers están instalados y contra qué APIs hablan?
3. ¿Existen Compositions propias para el workspace? ¿Puedo verlas y modificarlas?
4. ¿Qué `deletionPolicy` se usa? ¿Qué pasa con los datos de un usuario que se da de baja?
5. ¿Cómo se aprovisiona un usuario nuevo: por API REST del workspace, por Claim manual, automático desde Keycloak?
6. ¿Hay cuotas por usuario y quién las define?

**Al proveedor:**
1. ¿La API de S3 admite creación de buckets programática con las credenciales que me den? (De eso depende que Crossplane pueda hacer su trabajo.)

---

## 10. Fuentes

**Documentos del proyecto:** D2 §3.8 completo (Resource Management: propósito,
implementación con Crossplane, integración con seis componentes, stack), §3.6.2 y §3.6.3
(Crossplane en el User Workspace: namespace, buckets, Helm releases), §3.6.4, §7.9
(Crossplane), §9.2 (estrategias de escalabilidad), §9.5 (aprovisionamiento dinámico).
D3 §2.2 y §2.3.5 (Resource Management y escalabilidad).

**Documentación oficial:** `docs.crossplane.io` — Concepts (Managed Resources, Composite
Resources, Compositions, Providers), Troubleshooting.

---

## 11. Bitácora / hallazgos

*(Providers instalados, Compositions reales, fallos de aprovisionamiento y su causa,
respuesta de ESA sobre el alcance real.)*
