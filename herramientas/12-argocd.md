# ArgoCD — GitOps

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 3 — lo tocas al operar workspaces y despliegues
**Competencia de la matriz:** 10

---

## 1. Qué es, aquí

ArgoCD mantiene el clúster sincronizado con lo que dice Git. D2 §3.6.3 lo sitúa en el
**User Workspace**:

> *"**ArgoCD**: Synchronises the user repositories with the Kubernetes cluster to ensure that
> the desired state of resources and applications is consistently applied."*

Y §3.6.2 lo describe como el mecanismo de entrega continua del workspace:

> *"**Synchronisation**: Continuous delivery synchronises the manifests from user
> repositories with the Kubernetes cluster, ensuring the desired state is consistently
> applied."*

Esto es **GitOps aplicado a usuarios finales**: cada usuario tiene un repositorio en GitLab,
y ArgoCD aplica lo que hay ahí a su namespace. Junto con Crossplane y ESO forma el trío que
hace funcionar el componente 6.

**Pregunta abierta importante:** D2 solo menciona ArgoCD para workspaces de usuario. Si el
**Middleware mismo** se despliega también por ArgoCD o por Helm directo es una de las
primeras cosas que debes preguntar a ESA (§10). La respuesta cambia tu forma de trabajar
todos los días.

---

## 2. La frontera

Tuyo. El proveedor no opera GitOps.

Frontera interna a vigilar: si el Middleware se gestiona por ArgoCD, **un cambio manual con
`kubectl` se revierte solo** en la siguiente sincronización. Eso es una virtud (evita
configuraciones fantasma) y una trampa (tu parche de emergencia desaparece). Saber en qué
régimen estás es condición previa a cualquier intervención.

---

## 3. Qué debes saber

### Nivel imprescindible

- **`Application`**: el objeto central. `source` (repo, path, targetRevision), `destination`
  (servidor y namespace), `syncPolicy`.
- **`ApplicationSet`**: genera Applications a partir de un generador (lista, Git,
  clúster). Es lo que permite gestionar **un Application por usuario** sin escribirlos a mano
  — exactamente el caso del workspace.
- **Estados**: `Synced` / `OutOfSync` y `Healthy` / `Progressing` / `Degraded` / `Missing`.
  Son dos ejes independientes: puedes estar `Synced` y `Degraded`.
- **Drift**: qué es y por qué aparece. Un cambio manual, un mutating webhook, un controlador
  que añade campos.
- **Sync manual vs automática**: `syncPolicy.automated` con `prune` y `selfHeal`.
  - `prune: true` — borra lo que ya no está en Git. **Peligroso y necesario.**
  - `selfHeal: true` — revierte cambios manuales. Ésta es la que "deshace" tus parches.

### Nivel operativo

- **Sync waves y hooks**: `argocd.argoproj.io/sync-wave` para ordenar (base de datos antes
  que aplicación), `PreSync`/`Sync`/`PostSync` hooks.
- **Recuperar un estado divergente**: `argocd app diff`, sync selectivo de recursos,
  `--force`, `--replace`. Cuándo cada uno.
- **Ignorar diferencias legítimas**: `ignoreDifferences` para campos que otro controlador
  gestiona (réplicas cuando hay HPA, por ejemplo). Sin esto, vivirás en `OutOfSync`
  permanente y dejarás de mirar el indicador — que es peor que no tenerlo.
- **ArgoCD + Helm**: ArgoCD puede renderizar el chart él mismo (`source.helm.values`) en vez
  de dejarlo a Helm. Consecuencia: **no hay release de Helm en el clúster**, y `helm list` no
  muestra nada. Saberlo evita un diagnóstico perdido. Ver [02-helm.md](02-helm.md).
- **Secretos**: ArgoCD sobrescribe lo que gestiona. Un Secret creado a mano dentro de una
  Application gestionada desaparece. Solución: ESO →
  [14-external-secrets-operator.md](14-external-secrets-operator.md).
- Credenciales de repositorio y acceso a GitLab.

### Nivel avanzado

- Estrategia de repositorios: app-of-apps, monorepo vs multirepo.
- RBAC de ArgoCD y su integración con Keycloak (OIDC).
- ApplicationSet con generador Git para aprovisionar workspaces automáticamente al crear un
  repositorio.
- Ventanas de sincronización (`syncWindows`) para respetar los mantenimientos avisados con
  48 h del pliego.

---

## 4. Laboratorio

Parte del **Bloque 3 — 8 horas**, tras [02-helm.md](02-helm.md).

1. **Instala ArgoCD** en el clúster. Accede a la UI y a la CLI (`argocd login`).
2. **Crea una `Application`** apuntando al repositorio `middleware-lab`, path `manifests/`.
   Sincroniza a mano y observa el resultado.
3. **Provoca drift**: cambia algo directamente en el clúster con `kubectl edit`. Observa
   `OutOfSync` y mira el `diff` en la UI.
4. **Sincroniza** y comprueba que tu cambio manual desapareció. **Ése es el aprendizaje
   central del bloque.**
5. **Borra un recurso** con `kubectl delete` y mira cómo se restaura (si `selfHeal` está
   activo) o cómo queda `OutOfSync` (si no).
6. **Activa `prune`**: borra un manifiesto de Git y comprueba que el recurso desaparece del
   clúster.
7. **Sync waves**: haz que un Job de migración corra antes que el Deployment.
8. **Application con Helm**: apunta ArgoCD a tu chart del bloque 3. Comprueba con
   `helm list` que **no hay release** — y entiende por qué.

---

## 5. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Cambio manual sobre un recurso gestionado | Avería 14 del catálogo. Cómo se ve el drift |
| `selfHeal` activo + parche de emergencia | Tu arreglo desaparece en segundos. Cuándo desactivarlo |
| Un Secret creado a mano dentro de una Application | ArgoCD lo sobrescribe. Por qué necesitas ESO |
| `prune: true` con un manifiesto borrado por error | Cómo un commit puede borrar producción |
| HPA + réplicas fijas en Git | `OutOfSync` permanente; para qué sirve `ignoreDifferences` |
| Credencial del repositorio caducada | La Application queda `Unknown`; dónde se ve el error |

---

## 6. Avería de producción que este bloque entrena

**Avería 14:** deployment desincronizado — cambio manual sobre un recurso gestionado por
ArgoCD.

La lección operativa que deja: **en un entorno GitOps, la reparación de un incidente pasa por
Git**, no por `kubectl`. Si necesitas un parche inmediato, desactiva `selfHeal` de forma
consciente, documéntalo, y ábrelo como cambio en Git después. Un parche silencioso es una
bomba de relojería.

---

## 7. Comandos de bolsillo

```bash
argocd login <servidor>
argocd app list
argocd app get <app>
argocd app diff <app>                     # qué difiere entre Git y el clúster
argocd app sync <app>
argocd app sync <app> --resource apps:Deployment:mi-app   # sincronizar solo uno
argocd app history <app>
argocd app rollback <app> <id>
argocd app set <app> --sync-policy none   # desactivar la automática (emergencia)

# Desde kubectl
kubectl get applications -n argocd
kubectl get app -n argocd -o custom-columns=\
NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status
kubectl describe app <app> -n argocd
```

---

## 8. Criterio de dominio

- [ ] Creo una `Application` y la sincronizo, a mano y en automático.
- [ ] Explico la diferencia entre `Synced/OutOfSync` y `Healthy/Degraded`.
- [ ] Provoco drift, lo veo con `diff` y lo resuelvo.
- [ ] Recupero un estado divergente sin borrar y recrear todo.
- [ ] Sé qué hacen `prune` y `selfHeal`, y **cuándo desactivar `selfHeal` durante un incidente**.
- [ ] Uso sync waves para ordenar un despliegue con dependencias.
- [ ] Sé por qué `helm list` puede no mostrar nada aunque haya un chart desplegado.
- [ ] Entiendo que en GitOps la reparación pasa por Git, y actúo en consecuencia.

---

## 9. Artefacto que produces

Sección de **`runbooks/despliegue-y-reversion.md`** dedicada al régimen GitOps: cómo se hace
un cambio, cómo se revierte, y **cuál es el procedimiento de parche de emergencia** (con
desactivación consciente de `selfHeal`, registro y regularización posterior en Git).

**Alimenta:** Producto 2 (despliegues documentados), Producto 6 (SOPs de gestión de cambios).

---

## 10. Qué preguntar

**A ESA / Terradue:**
1. **¿Cuál es el mecanismo oficial de despliegue del Middleware: charts propios, GitOps con ArgoCD, o ambos? ¿Dónde vive el repositorio de referencia?** (La pregunta que define este archivo.)
2. Si es ArgoCD: ¿`selfHeal` y `prune` están activos? ¿Cuál es el procedimiento aprobado para un parche de emergencia?
3. ¿Los workspaces de usuario usan `ApplicationSet`? ¿Con qué generador?
4. ¿Qué diferencias se ignoran deliberadamente (`ignoreDifferences`) y por qué?
5. ¿ArgoCD está integrado con Keycloak para autenticación?

---

## 11. Fuentes

**Documentos del proyecto:** D2 §3.6.2 (sincronización continua de manifiestos), §3.6.3
(ArgoCD como punto de integración del workspace), §3.6.4 (stack del User Workspace).
Perfil ESA §1.1 (*Platform Domains Support: workspace — Not covered*).

**Documentación oficial:** `argo-cd.readthedocs.io` — Core Concepts, Sync Options, Sync
Waves and Hooks, ApplicationSet, Diffing customization.

---

## 12. Bitácora / hallazgos

*(Applications reales, régimen de sync configurado, incidentes de drift y cómo se
resolvieron.)*
