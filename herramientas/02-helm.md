# Helm

**Nivel exigido:** E — lo diseñas, lo optimizas y lo enseñas
**Prioridad:** 1 — núcleo diario
**Competencia de la matriz:** 9

---

## 1. Qué es, aquí

Helm es **el mecanismo de despliegue del Middleware**. D2 §6.4 no deja lugar a
interpretación:

> *"Preparing Deployment Configurations: Managed through **Helm charts**, these
> configurations define how the application should be deployed in Kubernetes, including
> resource allocation, environment variables, and network settings."*

Y en el ciclo de actualización (D2 §6.5), Helm es el eslabón entre la imagen nueva y el
clúster:

> *"If the image passes all tests, it is automatically pushed to Harbor and tagged with a new
> version number. **The Helm charts are updated to reflect the new image version**, and
> Kubernetes handles the deployment."*

Aparece además en dos sitios más: en **Resource Management** (§3.8.4, *"Helm: Manages the
deployment and configuration of Kubernetes applications, ensuring consistent and repeatable
setups"*) y en el **User Workspace**, donde Crossplane aprovisiona *Helm releases* dentro del
namespace de cada usuario (§3.6.2).

El perfil ESA lo lista como primera competencia técnica del rol: *"Deployment and operation
of Middleware workloads using **Helm and/or Kubernetes manifests**, including rollouts,
rollbacks, controlled updates"*.

**Consecuencia práctica:** cada cambio que hagas en producción va a pasar por Helm. Si no
dominas `diff` y `rollback`, cada cambio es una apuesta.

---

## 2. La frontera

Helm es **enteramente tuyo**. El proveedor no toca charts ni releases; su responsabilidad
termina en que el API de Kubernetes responda. La tabla de brechas del perfil ESA lo
clasifica en *"Workload Operations — Partial (operations, not advanced engineering)"*: el
proveedor da soporte a las aplicaciones desplegadas, pero la ingeniería de despliegue es tuya.

Corolario incómodo: si un `helm upgrade` deja el release en `pending-upgrade` a las 2 de la
mañana, no hay a quién escalar. Por eso este bloque es nivel E y no O.

---

## 3. Qué debes saber

### Nivel imprescindible

**Anatomía de un chart**
- `Chart.yaml` (`name`, `version`, `appVersion`, `dependencies`), `values.yaml`,
  `templates/`, `charts/`, `.helmignore`, `templates/NOTES.txt`, `templates/_helpers.tpl`.
- Diferencia entre `version` (del chart) y `appVersion` (de la aplicación). Se confunden
  siempre y provoca despliegues de la versión equivocada.
- `helm create` y —muy importante— **cómo limpiarlo**: el scaffold trae mucho ruido que
  luego nadie entiende.

**Plantillas**
- Sintaxis Go template: `{{ .Values.x }}`, `{{ .Release.Name }}`, `{{ .Chart.Name }}`,
  `{{ .Capabilities.KubeVersion }}`.
- Control de flujo: `if`/`else`, `range`, `with`.
- Funciones que usarás a diario: `default`, `quote`, `toYaml`, `nindent`, `required`,
  `tpl`, `lookup`.
- `include` vs `template`, y por qué `include` es el que permite encadenar con `nindent`.
- Espaciado: `{{-` y `-}}`. La causa nº 1 de YAML inválido generado.

**Valores**
- Precedencia: `values.yaml` del chart < `-f valores-extra.yaml` < `--set` < `--set-string`.
  Memorízala; explica el 80 % de los "pero si yo puse ese valor".
- `--set` con tipos: por qué `--set replicas=3` puede llegar como string y romper el
  manifiesto.
- Valores de subcharts: `subchart.clave` y `global.clave`.

**Ciclo de vida de un release**
```bash
helm install <rel> <chart> -n <ns> --create-namespace
helm upgrade <rel> <chart> -n <ns>
helm history <rel> -n <ns>
helm rollback <rel> <revisión> -n <ns>
helm uninstall <rel> -n <ns>
helm list -n <ns> --all          # incluye los que fallaron
```
- Dónde vive el estado: un `Secret` de tipo `helm.sh/release.v1` por revisión, **en el
  propio namespace**. Saberlo te salva cuando un release queda corrupto.

### Nivel operativo

**Ver antes de aplicar — la disciplina que define el nivel E**
```bash
helm template <rel> <chart> -f valores.yaml        # renderiza sin tocar el clúster
helm lint <chart>
helm install <rel> <chart> --dry-run --debug
helm diff upgrade <rel> <chart> -f valores.yaml    # plugin helm-diff, instálalo
```
`helm diff` no viene de fábrica (`helm plugin install https://github.com/databus23/helm-diff`).
Instálalo el primer día. Es lo que convierte un cambio en una decisión informada.

**Upgrades seguros**
```bash
helm upgrade <rel> <chart> -n <ns> \
  --atomic --timeout 5m --wait
```
- `--atomic`: si falla, revierte solo. `--wait`: espera a que los recursos estén listos.
- `--cleanup-on-fail`, `--force` (y por qué `--force` casi nunca es la respuesta).
- Qué hace `--atomic` **exactamente** cuando el timeout expira, y por qué a veces deja el
  release en un estado que hay que resolver a mano.

**Releases atascados**
- `pending-upgrade`, `pending-install`, `pending-rollback`: qué son, por qué ocurren
  (proceso interrumpido, timeout, pérdida de conexión) y cómo salir:
  `helm rollback` a la última revisión `deployed`, o en el peor caso borrar el Secret de la
  revisión pendiente. **Practica esto en el laboratorio, no en producción.**
- `helm get manifest`, `helm get values`, `helm get notes`, `helm get all` — la autopsia.

**Dependencias**
- `Chart.yaml` → `dependencies` con `condition` y `tags`.
- `helm dependency update` / `build`, `Chart.lock`, `charts/` como caché.
- Repositorios: `helm repo add/update/list`, y charts OCI en un registro
  (`helm push oci://…`) — relevante porque **Harbor puede alojar charts OCI**, lo que une
  este archivo con [10-harbor.md](10-harbor.md).

**Hooks**
- `pre-install`, `post-install`, `pre-upgrade`, `post-upgrade`, `pre-delete`,
  `helm.sh/hook-weight`, `helm.sh/hook-delete-policy`.
- Por qué los hooks **no** se revierten con `rollback` — trampa clásica en migraciones de
  base de datos.

### Nivel avanzado

- Escribir un chart para un componente del Middleware con `values` bien tipados y un
  `values.schema.json` que valide la entrada.
- Estrategia de valores por entorno: `values-dev.yaml`, `values-prod.yaml`, sin duplicar.
- Helm bajo ArgoCD: cuándo ArgoCD renderiza el chart él mismo y cuándo delega en Helm — y
  por qué eso cambia dónde vive el estado. Ver [12-argocd.md](12-argocd.md).
- Gestión de secretos en charts sin ponerlos en `values.yaml`: referencias a
  `ExternalSecret` ([14-external-secrets-operator.md](14-external-secrets-operator.md)).
- `helm.sh/resource-policy: keep` para no perder PVCs en un `uninstall`.

---

## 4. Datos de la plataforma que debes tener a mano

**Cadena real de despliegue del Middleware (D2 §6.5), memorízala completa:**

1. El desarrollador hace commit en **GitLab**.
2. El pipeline CI se dispara: pull del código, tests unitarios y de integración.
3. Si pasan, se construye una imagen **Docker** nueva.
4. La imagen se prueba en un entorno de staging.
5. Si pasa, se hace push a **Harbor** con un tag de versión nueva.
6. **Los Helm charts se actualizan para reflejar la nueva versión de imagen.**
7. **Kubernetes** despliega.
8. Si algo falla, el control de versiones permite **rollback rápido a la versión estable
   anterior**, "minimizando el tiempo de caída y la disrupción".

Los pasos 6, 7 y 8 son tuyos. Los 1–5 son de quien desarrolla la aplicación (ESA/Terradue o
usuarios de la plataforma).

**Presupuesto de error para tus ventanas de cambio:**
- Disponibilidad de la plataforma: **99,5 % anual** ≈ 44 h/año de caída admisible.
- Disponibilidad del proveedor: **99,95 % mensual** ≈ 43,2 min/mes.
- MTTR objetivo: **< 1 hora**.

Traducción: un `helm upgrade` fallido que tardes 50 minutos en revertir se come el
presupuesto mensual entero del proveedor. Por eso `--atomic` y `helm diff` no son lujo.

**Helm en el User Workspace:** Crossplane aprovisiona *Helm releases* dentro del namespace
de cada usuario (D2 §3.6.2). Con miles de usuarios, eso son miles de releases que no
gestionas uno a uno — pero cuyos fallos vas a diagnosticar.

---

## 5. Laboratorio

Continúa el laboratorio de [17-docker.md](17-docker.md) (la app mínima con `/health` y
`/metrics`).

1. **Empaqueta.** `helm create middleware-app`, luego **límpialo**: borra lo que no
   entiendas y quédate con un Deployment, un Service y un ConfigMap.
2. **Parametriza.** Réplicas, imagen (repositorio + tag separados), recursos y configuración
   en `values.yaml`. Usa `required` para el tag: que falle rápido si no se lo pasas.
3. **Renderiza antes de tocar nada.** `helm template` y lee el YAML generado línea a línea.
4. **Instala.** `helm install` con `-n copernicus-lab --create-namespace`.
5. **Cambia con red.** Instala `helm-diff`. Cambia un valor, ejecuta `helm diff upgrade`,
   confirma que el diff dice **exactamente** lo que esperabas, y solo entonces
   `helm upgrade --atomic --timeout 2m`.
6. **Provoca un fallo y observa la reversión automática.** Pon una imagen inexistente y
   ejecuta `helm upgrade --atomic --timeout 60s`. Cronometra. Observa cómo vuelve solo.
7. **Rollback manual.** Haz tres upgrades buenos, mira `helm history`, y vuelve a la
   revisión 2. Comprueba con `helm get values` que los valores volvieron también.
8. **Release atascado.** Interrumpe un `helm upgrade` con Ctrl-C a mitad. Observa
   `pending-upgrade` en `helm list`. Sal de ahí. **Documenta cómo lo hiciste.**
9. **Hooks.** Añade un `pre-upgrade` que ejecute un Job. Haz rollback y comprueba que el
   hook no se revirtió.

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| `values.yaml` con un tipo equivocado (`replicas: "3"`) | Cómo se ve un error de tipo en el YAML renderizado |
| Upgrade interrumpido → `pending-upgrade` | El procedimiento de rescate, la avería 18 del catálogo |
| `nindent` mal calculado en un helper | Por qué `helm template` es obligatorio antes de aplicar |
| Un secreto puesto en `values.yaml` y versionado | Por qué necesitas ESO y no valores en Git |
| `helm upgrade` sin `--atomic` que deja réplicas viejas y nuevas conviviendo | Qué significa realmente un rollout a medias |
| Chart con `dependencies` sin `helm dependency update` | El error de subchart ausente |
| Dos releases distintos que crean el mismo recurso | Conflicto de propiedad; por qué los nombres importan |

---

## 7. Averías de producción que este bloque entrena

Avería 18 del catálogo: **upgrade de Helm atascado, release en `pending-upgrade`**. Es la
única avería del catálogo cuya resolución depende exclusivamente de ti; no hay escalamiento
posible.

Indirectamente entrena también la 14 (deployment desincronizado por cambio manual sobre un
recurso gestionado por ArgoCD) — porque el conflicto Helm↔ArgoCD es de esta familia.

---

## 8. Comandos de bolsillo

```bash
# Antes de cambiar nada
helm diff upgrade <rel> <chart> -n <ns> -f valores.yaml
helm template <rel> <chart> -f valores.yaml | less
helm lint <chart>

# Aplicar con red
helm upgrade --install <rel> <chart> -n <ns> -f valores.yaml \
  --atomic --timeout 5m --wait

# Autopsia
helm list -n <ns> --all
helm history <rel> -n <ns>
helm get values <rel> -n <ns>            # valores efectivos
helm get values <rel> -n <ns> --all      # incluidos los del chart
helm get manifest <rel> -n <ns>          # lo que realmente hay en el clúster
helm status <rel> -n <ns>

# Revertir
helm rollback <rel> <revisión> -n <ns> --wait

# Dónde vive el estado
kubectl get secret -n <ns> -l owner=helm,name=<rel>
```

---

## 9. Criterio de dominio

- [ ] Escribo un chart desde cero para un componente del Middleware, sin scaffold.
- [ ] Explico la precedencia de valores y predigo qué gana en un caso dado.
- [ ] Nunca aplico un cambio sin haber visto el `diff` antes. Es un hábito, no una intención.
- [ ] Hago un `upgrade` fallido y lo revierto **sin perder configuración**, explicando cada paso en voz alta.
- [ ] Saco un release de `pending-upgrade` sin buscar en internet.
- [ ] Sé dónde vive el estado del release y cómo inspeccionarlo con `kubectl`.
- [ ] Escribo la ventana, el criterio de éxito y el plan de reversión **antes** del cambio, no después.
- [ ] Enseño este bloque completo a otra persona.

---

## 10. Artefacto que produces

`runbooks/despliegue-y-reversion.md` — con estas secciones obligatorias:
ventana de cambio · comprobaciones previas (`diff`, `template`, `lint`) · comando exacto ·
criterio de éxito medible · plan de reversión con su comando · evidencia posterior.

**Alimenta:** Producto 2 (despliegues documentados) y Producto 6 (SOPs de gestión de
cambios). Es también la plantilla de tu proceso de gestión de cambios funcional —
justamente una de las áreas que el análisis ESA marca como **no cubierta** por el proveedor.

---

## 11. Qué preguntar

**A ESA / Terradue:**
1. ¿Cuál es el mecanismo oficial de despliegue del Middleware: charts propios, GitOps con ArgoCD, o ambos? ¿Dónde vive el repositorio de referencia?
2. ¿Qué versiones exactas de cada componente forman el release desplegado y cómo se anuncian las actualizaciones?
3. ¿Los charts son públicos o están en un registro privado? ¿OCI o repositorio HTTP clásico?
4. ¿Qué valores se espera que ajuste yo por sitio y cuáles no debo tocar nunca?
5. ¿Existe entorno de pruebas o solo producción? ¿Cómo se valida un upgrade antes de aplicarlo?

---

## 12. Fuentes

**Documentos del proyecto:** D2 §6.4 (Deployment — Helm charts), §6.5 (Version Control and
Update Mechanisms — la cadena completa CI → Harbor → Helm → K8s → rollback), §3.6.2 (Helm
releases en el workspace vía Crossplane), §3.8.4 (Helm en Resource Management), §6.1
(tecnologías de empaquetado). D3 §2.3.3: *"Helm charts are used to define deployment
configurations, enabling repeatable and scalable deployment processes"*. Perfil ESA §2.3.1.

**Documentación oficial:** `helm.sh/docs` → Quickstart y **Chart Template Guide** (el
capítulo que de verdad importa). Plugin: `github.com/databus23/helm-diff`.

---

## 13. Bitácora / hallazgos

*(Charts reales del Middleware, valores que ajustaste, releases que se atascaron y cómo
saliste.)*
