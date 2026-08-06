# Fundamentos — Linux, Git y YAML

**Nivel exigido:** O (Linux, Git) · E (YAML y manifiestos)
**Prioridad:** 1 — es el suelo sobre el que se apoya todo lo demás
**Competencias de la matriz:** 1, 2, 3

---

## 1. Por qué está aquí

Este archivo no describe un componente de la plataforma. Describe **lo que debe dejar de
consumirte atención** para que puedas pensar en el problema real.

Cuando estás diagnosticando por qué un item ingerido no aparece en el catálogo, no puedes
estar recordando la sintaxis de `jq` ni contando espacios de indentación. La misión de este
bloque es que Linux, Git y YAML se vuelvan invisibles.

Es el único bloque de la carpeta que puedes **saltarte si pasas la prueba** del §7.

---

## 2. Dónde aparece en el trabajo real

- **Linux:** todo diagnóstico dentro de un pod es una sesión de shell. `kubectl exec` te deja
  en un contenedor que a menudo no tiene ni `curl`.
- **Git:** el TDR exige un **repositorio documental** desde el Producto 1, y todo tu trabajo
  —manifiestos, charts, runbooks, dashboards, bitácora— vive versionado. Además, GitLab es un
  componente de la plataforma ([11-gitlab.md](11-gitlab.md)) y el Application Registry
  entero se apoya en control de versiones.
- **YAML:** es el idioma de Kubernetes, Helm, Argo, ArgoCD, Crossplane, CWL y las reglas de
  Prometheus. **Todo lo que vas a escribir en 19 meses es YAML.** Por eso es nivel E y no O.

---

## 3. Qué debes saber

### Linux y CLI — nivel O

**Diagnóstico desde dentro de un pod** (el caso de uso real)
- Red: `curl -v`, `wget -O-`, `nc -zv host puerto`, `getent hosts <nombre>`,
  `nslookup`/`dig` si existen, `cat /etc/resolv.conf`.
- Qué hacer cuando **no hay herramientas**: contenedores distroless, `kubectl debug` con un
  contenedor efímero, o desplegar un pod de utilidades a propósito.
- Procesos: `ps aux`, `top`, señales (`SIGTERM` vs `SIGKILL` — importa para entender el
  `terminationGracePeriodSeconds` y el exit code 137 del `OOMKilled`).
- Sistema de archivos: `df -h`, `du -sh`, permisos y `chown` en volúmenes montados, `fsGroup`
  y por qué un pod no puede escribir en su PVC.
- Variables de entorno: `env`, y verificar que un ConfigMap llegó de verdad.

**Manejo de texto y JSON**
- `grep`, `sed`, `awk` a nivel básico — no necesitas ser experto.
- **`jq` sí, a fondo.** Toda esta plataforma habla JSON: STAC items, respuestas de la API,
  `kubectl -o json`. Ejemplos que usarás:
  ```bash
  kubectl get pods -o json | jq -r '.items[] | select(.status.phase!="Running") | .metadata.name'
  curl -s "$STAC/search?limit=1" | jq '.features[0].properties.datetime'
  curl -s "$STAC/collections" | jq -r '.collections[].id'
  cat item.json | jq '.assets | keys'
  ```
- `yq` para lo mismo sobre YAML.
- Redirecciones, tuberías, `xargs`, códigos de salida (`$?`) y por qué importan en los
  Application Packages (D3 §3.2.4: el exit code decide si el mensaje va al topic de éxito o
  al de fallo).

**Scripting mínimo**
- Bucles, condicionales, funciones en `bash` — lo justo para automatizar una comprobación
  repetitiva. No necesitas más.
- Python para lo que sea más largo que 20 líneas: la plataforma ya usa Python y GDAL en los
  pipelines de ingesta (D2 §3.3.4).

**Entorno de trabajo**
- SSH y claves. VPN (el pliego indica **acceso por VPN** a las APIs de Kubernetes y S3).
- Multiplexor de terminal (`tmux` o similar) para no perder una sesión larga.

### Git — nivel O

- Modelo mental: árbol de trabajo → índice → repositorio. Sin esto, todo lo demás es magia.
- Diario: `status`, `add -p` (parcial, muy útil), `commit`, `log --oneline --graph`, `diff`,
  `diff --staged`.
- Ramas: `switch -c`, `merge`, `rebase`, y **cuándo no rebasar** (nada publicado).
- Deshacer: `restore`, `reset --soft/--mixed/--hard`, `revert`, `reflog`. **`reflog` es la
  red de seguridad que casi nadie conoce**; apréndela antes de necesitarla.
- Historia: `log -p <archivo>`, `blame`, `log -S "texto"` (buscar cuándo entró una línea).
  Esto es lo que responde *"¿qué provocó este cambio?"* — la evidencia que exige el nivel O.
- Remotos: `fetch` vs `pull`, `push`, resolución de conflictos.
- Tags y releases: la plataforma los usa para versionar Application Packages (D2 §6.5).
- `.gitignore` y —crítico— **nunca versionar secretos**. Si ocurre, el secreto está
  comprometido aunque borres el commit.

### YAML — nivel E

Aquí sí necesitas dominio, no familiaridad.

- Indentación con **espacios**, nunca tabuladores. Dos espacios por convención.
- Escalares, listas (`-`) y mapas. Listas de mapas (la estructura de `containers:`).
- Bloques de texto: `|` (literal, conserva saltos), `>` (plegado), con sus modificadores
  `|-`, `|+`, `>-`. Los usarás en ConfigMaps con ficheros dentro.
- Tipado implícito y sus trampas: `yes`/`no`/`on`/`off` se convierten en booleanos;
  `1.10` es un float y pierde el cero; una versión sin comillas se convierte en número.
  **Cita siempre los tags de imagen y las versiones.**
- Anclas (`&`) y alias (`*`), y `<<:` para fusión. Útiles en Argo Workflows.
- Multi-documento con `---` — cómo Kubernetes lee varios objetos de un archivo.
- Comentarios: `#`. Un manifiesto sin comentarios es un manifiesto que nadie mantendrá.

**Validar antes de aplicar** (el hábito que define el nivel E):
```bash
kubectl apply --dry-run=client -f manifiesto.yaml    # sintaxis y esquema local
kubectl apply --dry-run=server -f manifiesto.yaml    # valida contra el API real
kubectl diff -f manifiesto.yaml                      # qué cambiaría exactamente
yq eval '.' manifiesto.yaml                          # ¿parsea?
```

---

## 4. Laboratorio

**Bloque 0 de la ruta de práctica — 4 horas.**

1. **Crea el repositorio.** `middleware-lab`, con esta estructura desde el primer día:
   ```
   middleware-lab/
   ├── manifests/        # manifiestos K8s, agrupados por componente
   ├── charts/           # tus charts de Helm
   ├── runbooks/         # los procedimientos, uno por archivo
   ├── dashboards/       # JSON exportado de Grafana
   ├── queries/          # PromQL y CQL2 comentadas
   ├── bitacora/         # un archivo por día
   └── README.md
   ```
   Esta estructura no es decorativa: **es el esqueleto del repositorio documental que exige
   el Producto 1 del contrato.**
2. **Escribe a mano** un manifiesto de Pod con `resources`, `livenessProbe` y
   `readinessProbe`. Sin copiar de ningún lado. Valídalo con `--dry-run=client`.
3. **Rómpelo a propósito** (§5) y aprende a leer cada mensaje de error.
4. **Versiona.** Commit, rama, cambio, merge, y `git log -p` para leer tu propia historia.
5. **Practica `jq`** contra un STAC Item real descargado de un catálogo público
   (Earth Search o Planetary Computer). Extrae: el `datetime`, las claves de `assets`, el
   `bbox`, y la lista de `stac_extensions`.
6. **Practica el diagnóstico desde un pod.** Levanta un pod con `curl` y comprueba DNS,
   conectividad a un Service y resolución entre namespaces.

---

## 5. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Rompe la indentación de un manifiesto | Cómo se ve un error de parseo vs uno de esquema |
| Invierte dos niveles de anidación | Que el YAML es válido pero el objeto no — el error más difícil de ver |
| Quita un campo obligatorio | El mensaje del validador del API |
| Usa un tabulador | El error críptico que produce |
| Escribe `image: nginx:1.10` sin comillas para el tag `1.10` | Cómo el tipado implícito te cambia el valor |
| Escribe `enabled: yes` esperando la cadena `"yes"` | Lo mismo con booleanos |
| Haz `git reset --hard` perdiendo un commit | Recupéralo con `reflog`. Hazlo ahora, en el laboratorio |

---

## 6. Comandos de bolsillo

```bash
# Diagnóstico dentro de un pod sin herramientas
kubectl debug -it <pod> --image=nicolaka/netshoot --target=<contenedor>

# Un pod de utilidades a demanda
kubectl run tmp --rm -it --image=nicolaka/netshoot -- bash

# ¿Qué pods no están Running?
kubectl get pods -A -o json | jq -r '
  .items[] | select(.status.phase!="Running" and .status.phase!="Succeeded")
  | "\(.metadata.namespace)/\(.metadata.name) \(.status.phase)"'

# Historia de un archivo
git log --oneline --follow -- runbooks/diagnostico-pod.md
git log -S "signed_url" --oneline        # cuándo entró esa cadena
git blame runbooks/diagnostico-pod.md

# Recuperar lo perdido
git reflog
git switch -c rescate <hash-del-reflog>

# Validar
kubectl apply --dry-run=server -f .
yq eval-all '.' manifests/*.yaml > /dev/null && echo OK
```

---

## 7. La prueba para saltarte este bloque

Hazla ahora. Si la pasas entera, ve directo a [01-kubernetes.md](01-kubernetes.md).

1. Escribes **30 líneas de YAML válido** de un manifiesto de Kubernetes **sin copiar de
   ningún lado**, y pasa `--dry-run=server`.
2. Explicas por qué `version: 1.10` sin comillas puede romperte un despliegue.
3. Extraes con `jq` el `datetime` y las claves de `assets` de un STAC Item, a la primera.
4. Recuperas un commit perdido con `reflog` sin buscar cómo.
5. Diagnosticas si un pod resuelve DNS y alcanza un Service de otro namespace, desde dentro
   del pod, sin buscar los comandos.

---

## 8. Criterio de dominio

- [ ] Escribo 30 líneas de YAML válido sin copiar.
- [ ] Diagnostico conectividad y permisos desde un pod sin buscar comandos.
- [ ] Versiono manifiestos, comparo, revoco, y **sé qué provocó un cambio**.
- [ ] Uso `jq` sobre respuestas de la STAC API sin pensarlo.
- [ ] Recupero de un `reset --hard` con `reflog`.
- [ ] Valido con `--dry-run=server` **antes** de aplicar. Siempre.

---

## 9. Artefactos que produces

1. **El repositorio `middleware-lab` inicializado** con la estructura del §4 — que es la
   estructura del repositorio documental del Producto 1.
2. **Tu primer manifiesto versionado.**
3. **La bitácora diaria**: un archivo por día, tres líneas — *qué intenté, qué falló, qué
   comando o idea lo resolvió*. Es tu futuro banco de runbooks y tu evidencia de progreso
   para el "registro de la operación del período" que piden casi todos los productos del
   contrato.

---

## 10. Qué preguntar

**A la AIG:**
1. ¿Dónde vive el repositorio documental oficial y qué estructura debe respetar? ¿Git, wiki, SharePoint?
2. ¿La entrega formal en Word/Excel/PowerPoint (2 USB) convive con el repositorio o lo sustituye?

La segunda pregunta importa más de lo que parece: el TDR exige entrega en **formato
Microsoft Office**, así que **diseña la documentación en Markdown para que exporte limpio a
Word desde el principio**. Tablas simples, sin HTML embebido, encabezados jerárquicos
consistentes.

---

## 11. Fuentes

**Documentos del proyecto:** TDR (repositorio documental desde el Producto 1; entrega en
formato Office). D3 §3.2.4 (exit codes de las aplicaciones). D2 §3.3.4 (Python y GDAL en los
pipelines). Guía de estudio §11 (competencias 1, 2, 3), Bloque 0.

**Documentación oficial:** `yaml.org/spec` (o cualquier referencia de las trampas de tipado),
`git-scm.com/book` (capítulos 2, 3 y 7), `jqlang.github.io/jq/manual`.

---

## 12. Bitácora / hallazgos

*(Comandos que te resultaron útiles, trampas de YAML que te costaron tiempo, convenciones
del repositorio documental que acuerdes con AIG.)*
