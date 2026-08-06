# Docker / podman / OCI — contenedores

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 3 — base de todo lo que se despliega
**Competencia de la matriz:** 4

---

## 1. Qué es, aquí

Todo lo que corre en CopernicusLAC corre dentro de un contenedor. D2 §7.3:

> *"Docker is a containerization technology that allows the CopernicusLAC platform to
> encapsulate applications and their dependencies into self-contained units… providing a
> standardised runtime environment that includes all necessary libraries and
> configurations."*

Y §3.3.4 añade **podman** junto a Docker en el stack de procesamiento.

D2 §6.3 explica por qué importa especialmente en observación de la Tierra:

> *"In the realm of EO, where **data processing precision and reproducibility are paramount**,
> containerization offers a powerful solution to address the challenges of varying computing
> environments… Consider an EO Application Package that detects land cover changes using
> spectral indices. Such an application necessitates **specialised libraries** for data
> manipulation, image processing, and spectral analysis."*

Traducción: las aplicaciones EO dependen de GDAL, PROJ, rasterio y compañía, con versiones
que se pelean entre sí. El contenedor es lo que hace que un NDVI calculado hoy dé el mismo
resultado dentro de tres años.

Es obligatorio, además: D2 §6.8.3 — *"EO applications **MUST** be encapsulated within Docker
containers."*

---

## 2. La frontera

Tuyo como operador. El runtime de contenedores del nodo (containerd, CRI-O) es del
proveedor; **las imágenes y su contenido** son del Middleware.

Tú no construyes las aplicaciones EO, pero sí necesitas: leer un Dockerfile, entender por
qué una imagen pesa 4 GB, saber si una imagen tiene GDAL, diagnosticar por qué un contenedor
muere al arrancar, y construir imágenes auxiliares cuando haga falta.

---

## 3. Qué debes saber

### Nivel imprescindible

**Conceptos**
- **Imagen vs contenedor vs pod**: los tres niveles. La imagen es la plantilla inmutable, el
  contenedor es una instancia en ejecución, el pod es la unidad de Kubernetes que puede
  contener varios contenedores compartiendo red y volúmenes.
- **Capas**: cada instrucción del Dockerfile crea una. Se cachean y se comparten entre
  imágenes. Por eso el orden de las instrucciones determina el tiempo de build.
- **Tag vs digest**: el tag se mueve, el digest no. Ver [10-harbor.md](10-harbor.md).
- **OCI**: el estándar. Docker y podman producen imágenes compatibles.
- Registro, repositorio, artefacto.

**Dockerfile**
- `FROM`, `RUN`, `COPY`/`ADD`, `WORKDIR`, `ENV`, `ARG`, `EXPOSE`, `USER`,
  `ENTRYPOINT` vs `CMD`, `HEALTHCHECK`.
- **`ENTRYPOINT` vs `CMD`**: la confusión más común. `ENTRYPOINT` es el ejecutable, `CMD` son
  los argumentos por defecto. En Kubernetes, `command:` sobrescribe `ENTRYPOINT` y `args:`
  sobrescribe `CMD`. **Esto explica por qué un contenedor que funciona con `docker run` no
  funciona en un pod.**
- **Multi-stage builds**: construir en una imagen pesada, copiar el resultado a una ligera.
  Es lo que cumple el *"use lightweight base images"* de D2 §6.8.3.
- `.dockerignore` y por qué el contexto de build importa.
- No ejecutar como root (`USER`), y su relación con `securityContext` en Kubernetes.

**Operación básica**
- `build`, `run`, `exec`, `logs`, `ps`, `images`, `inspect`, `history`.
- Puertos, volúmenes, variables de entorno.
- Señales y `PID 1`: por qué un proceso que ignora `SIGTERM` hace que el pod tarde 30
  segundos en morir.

### Nivel operativo

- **Inspeccionar una imagen ajena**, que es lo que más harás:
  `docker history` (¿por qué pesa tanto?), `docker inspect` (entrypoint, env, usuario),
  y entrar con `docker run --rm -it --entrypoint sh <imagen>` para comprobar qué hay dentro.
- **¿Tiene GDAL?** `docker run --rm <imagen> gdalinfo --version`. Esta pregunta concreta
  aparece en la avería 9 del catálogo.
- Reproducibilidad: fijar versiones de base y de dependencias. Una imagen que hace
  `apt-get install gdal-bin` sin versión no es reproducible.
- Tamaño: capas innecesarias, cachés de paquetes no limpiadas, ficheros temporales.
- Escaneo local (`trivy image`) antes de subir a Harbor.
- podman como alternativa sin daemon, y `podman build` compatible con Dockerfile.
- Multi-arquitectura (`linux/amd64`, `linux/arm64`) — relevante si desarrollas en un Mac con
  Apple Silicon y despliegas en x86. **Causa clásica de `exec format error`.**

### Nivel avanzado

- Imágenes base para aplicaciones EO: qué trae cada una (GDAL, PROJ, rasterio, Python).
- Firma de imágenes (Cosign) y verificación en el despliegue.
- Reducir el tiempo de pull sobre los 3 Gbps de conectividad a Europa: capas compartidas,
  proxy cache en Harbor.

---

## 4. Los requisitos que la plataforma impone (D2 §6.8)

Tu lista de verificación al evaluar una imagen:

| § | Requisito | Nivel |
|---|---|---|
| 6.8.3 | Encapsulada en Docker; **imágenes base ligeras**, tamaño y rendimiento optimizados | **MUST** |
| 6.8.5 | **Libre de vulnerabilidades conocidas**, con escaneos regulares | **MUST** |
| 6.8.2 | Ejecución **desatendida**: sin intervención humana una vez desplegada | **MUST** |
| 6.8.7 | Requests y limits definidos; soporte de procesamiento paralelo | SHOULD |

Y D2 §6.3 sobre gestión de dependencias:
> *"Dependency management within containers safeguards against **version conflicts**,
> system-specific adjustments, and other potential pitfalls that might compromise the
> accuracy of EO data processing."*

Esa frase —*"comprometer la exactitud del procesamiento"*— es la razón real de todo esto. No
es higiene de despliegue: es integridad científica.

---

## 5. Laboratorio

**Bloque 1 de la ruta de práctica — 5 horas** (junto con [10-harbor.md](10-harbor.md)).

1. **Construye una imagen mínima** de una app Python que exponga `/health` y `/metrics`.
   Esa app te servirá después en [02-helm.md](02-helm.md) y
   [03-prometheus-grafana.md](03-prometheus-grafana.md).
2. **Inspecciona las capas:** `docker history`. ¿Cuál pesa más? ¿Por qué?
3. **Multi-stage.** Reescríbelo con dos etapas y compara el tamaño final. Anota los dos
   números.
4. **Publica** en un registro local, y luego repite contra **Harbor** con proyecto, cuota y
   escaneo → [10-harbor.md](10-harbor.md).
5. **El experimento del tag.** Cambia el contenido, publica con **el mismo tag**, y observa
   que el digest cambió. Razona por escrito por qué `imagePullPolicy` importa.
6. **Imagen con GDAL.** Construye o descarga una con GDAL y verifica:
   `docker run --rm <imagen> gdalinfo --version`. Úsala en el CWL del
   [bloque 6](15-cwl-calrissian.md).
7. **`ENTRYPOINT` vs `CMD`.** Haz que la imagen funcione con `docker run` y luego
   sobrescribe `command:` en un pod. Observa la diferencia.
8. **Escanea:** `trivy image <imagen>`. Corrige una vulnerabilidad actualizando la base.

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Publicar una imagen con una vulnerabilidad conocida | Cómo se ve el escaneo de Harbor |
| Mismo tag, contenido distinto | Por qué dos pods "iguales" corren código distinto |
| Imagen construida para arm64 desplegada en amd64 | `exec format error`. Desconcertante la primera vez |
| Contenedor que ignora `SIGTERM` | Terminación de 30 s; por qué existe `terminationGracePeriodSeconds` |
| Imagen sin GDAL en un paso que lo necesita | **Avería 9 del catálogo** |
| Ejecutar como root con `securityContext` restrictivo | El pod no arranca; el error de permisos |
| `apt-get install` sin fijar versión | La imagen deja de ser reproducible; reconstruye meses después y cambia |

---

## 7. Averías de producción que este bloque entrena

- **Avería 2:** `ImagePullBackOff` — junto con [10-harbor.md](10-harbor.md).
- **Avería 9:** workflow que falla en el paso 3 — imagen sin GDAL.
- **Avería 3:** `OOMKilled` — una imagen que carga un raster entero en memoria.

---

## 8. Comandos de bolsillo

```bash
# Construir e inspeccionar
docker build -t mi-app:1.0 .
docker history mi-app:1.0                    # ¿por qué pesa tanto?
docker inspect mi-app:1.0 --format='{{.Config.Entrypoint}} {{.Config.Cmd}}'
docker inspect mi-app:1.0 --format='{{.Config.User}}'
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}'

# Explorar una imagen ajena (lo que más harás)
docker run --rm -it --entrypoint sh <imagen>
docker run --rm <imagen> gdalinfo --version
docker run --rm <imagen> python -c "import rasterio; print(rasterio.__version__)"

# El digest, que es lo que identifica de verdad
docker inspect --format='{{index .RepoDigests 0}}' <imagen>

# Escanear
trivy image <imagen>
trivy image --severity HIGH,CRITICAL <imagen>

# Multi-arquitectura
docker buildx build --platform linux/amd64,linux/arm64 -t mi-app:1.0 --push .
docker image inspect <imagen> --format='{{.Architecture}}'

# Desde el clúster: ¿qué imagen corre de verdad?
kubectl get pod <pod> -n <ns> -o jsonpath='{.status.containerStatuses[*].imageID}'
```

Ese último comando resuelve una discusión frecuente: `spec.image` dice qué **pediste**;
`status.containerStatuses[].imageID` dice qué **está corriendo**, con su digest.

---

## 9. Criterio de dominio

- [ ] Construyo una imagen reproducible, la firmo/escaneo y la subo a un registro privado.
- [ ] **Explico capas, imagen, contenedor y pod** con mis palabras.
- [ ] Explico por qué un `ImagePullBackOff` puede ser credenciales, tag inexistente o registro inalcanzable — y sé distinguirlos.
- [ ] Reduzco el tamaño de una imagen con multi-stage y mido la diferencia.
- [ ] Inspecciono una imagen ajena y averiguo qué hay dentro sin documentación.
- [ ] Explico `ENTRYPOINT` vs `CMD` y cómo los sobrescribe Kubernetes.
- [ ] Sé qué imagen está corriendo realmente en un pod, por digest.
- [ ] Nombro los requisitos MUST de D2 §6.8 sobre contenedores.

---

## 10. Artefactos que produces

1. **`Dockerfile` versionado** de tu app de laboratorio, en dos versiones (simple y
   multi-stage) con la comparación de tamaños.
2. **Nota de una página: "imagen vs contenedor vs pod"**, con tus palabras. Parece trivial;
   es el documento que vas a usar para explicárselo al recurso designado por AIG.

**Alimentan:** Producto 2 (documentación técnica), Producto 4 (material de transferencia).

---

## 11. Qué preguntar

**A ESA / Terradue:**
1. ¿Qué imágenes base están aprobadas para los Application Packages?
2. ¿Hay una imagen de referencia con GDAL/rasterio que se deba usar?
3. ¿Se firman las imágenes y se verifica la firma en el despliegue?
4. ¿Qué arquitecturas se soportan?

**Al proveedor:**
1. ¿Qué runtime de contenedores usan los nodos (containerd, CRI-O) y qué versión?
2. ¿Hay `PodSecurityStandards` o políticas que restrinjan ejecutar como root?

---

## 12. Fuentes

**Documentos del proyecto:** D2 §6.3 (Containers — containerización en EO, gestión de
dependencias, integración con CWL), §6.1 (Docker en el empaquetado), §6.4 (despliegue como
pods), §6.5 (build de la imagen en el pipeline CI), §6.7 (beneficios de contenedores +
Kubernetes), §6.8.3 y §6.8.5 (requisitos MUST), §7.3 (Docker), §3.3.4 (Docker y podman en el
stack de procesamiento), §3.5.4 (Docker en front-end). D3 §2.3.3 (aplicaciones empaquetadas
como contenedores Docker con manifiesto CWL). D1 §3.2.3.

**Documentación oficial:** `docs.docker.com` — Dockerfile reference, Multi-stage builds,
Best practices. `podman.io`. Escáner: `trivy`.

---

## 13. Bitácora / hallazgos

*(Imágenes base aprobadas, tamaños medidos, vulnerabilidades encontradas, incidentes de
arquitectura.)*
