# Orden de estudio — Prioridad 2 (lo que nadie más administra)

Las siete herramientas de Prioridad 2 son las que el análisis de perfil de ESA marca como
**no cubiertas** por el contrato del proveedor. No hay red debajo: si fallan, el responsable
es el Administrador de Middleware.

Este archivo fija **el orden**. No es el orden del índice (que va por número de archivo),
sino por **precedencia real**: si para entender A hace falta A ya conocer B, B va antes.

---

## El orden

| # | Herramienta | Archivo | Nivel | Por qué va aquí |
|---|---|---|---|---|
| 1 | **S3 / MinIO** | [06-s3-minio.md](06-s3-minio.md) | E | Base física de todo. Los otros seis apuntan, escriben o leen aquí. Nada se entiende sin el modelo bucket/key/prefijo/política. |
| 2 | **STAC + PgSTAC + stac-fastapi** | [05-stac-pgstac-stac-fastapi.md](05-stac-pgstac-stac-fastapi.md) | E | El catálogo es la capa de *significado* sobre S3: un asset STAC es un `href` a un objeto S3 con su media type. Sin (1) no se puede diagnosticar un asset roto. |
| 3 | **Argo Workflows** | [07-argo-workflows.md](07-argo-workflows.md) | O | El motor que **produce** lo que hay en (1) y registra en (2). Un workflow fallido se diagnostica leyendo qué escribió en S3 y qué item quedó sin publicar. |
| 4 | **Argo Events** | [08-argo-events.md](08-argo-events.md) | O | Es el **disparador** de (3). Un sensor sin workflow que disparar no significa nada; y la avería típica —"no hay datos nuevos"— se resuelve distinguiendo si falló el evento o el workflow. Imposible sin (3). |
| 5 | **Keycloak / OIDC / JWT** | [09-keycloak.md](09-keycloak.md) | O | Es la puerta de todo lo anterior: protege la API STAC de (2), el servicio de URLs firmadas de (1), y federa la identidad de (6) y (7). Se estudia cuando ya sabes **qué** está protegiendo, o los 401/403 son ruido abstracto. |
| 6 | **Harbor** | [10-harbor.md](10-harbor.md) | O | Registro de imágenes. Cobra sentido tras (3): el `ImagePullBackOff` de un workflow es el síntoma que lo hace importante. Se integra con (5) por OIDC. |
| 7 | **GitLab (repos + CI/CD)** | [11-gitlab.md](11-gitlab.md) | O | Cierra el ciclo: el pipeline construye la imagen y la **publica en (6)**, valida el CWL que ejecuta (3), y autentica contra (5). Es el último porque consume a todos los demás. |

---

## La cadena, en una frase

**S3 guarda → STAC describe → Workflows producen → Events disparan → Keycloak protege →
Harbor sirve las imágenes → GitLab construye y publica.**

Cada eslabón explica una avería del siguiente. Estudiado al revés, cada bloque se convierte
en memorización sin causa.

---

## Reglas de este recorrido

1. **Dos pasadas.** Primera pasada: **visión global de las siete**, una por sesión, en este
   orden. Segunda pasada: laboratorio, sabotajes y criterio de dominio de cada archivo, en
   el mismo orden. Nunca las siete de golpe.
2. **Prioridad 1 es transversal, no previa.** Kubernetes, Helm, Prometheus/Grafana y
   Linux/Git/YAML (archivos 01–04) se usan en los siete bloques. No se estudian antes: se
   refuerzan *dentro* de cada laboratorio.
3. **Dependencias de fuera de P2 que aparecen en el camino:**
   - (2) toca **PostgreSQL/PostGIS** ([19](19-postgresql-postgis.md), P3) — nivel consulta, no administración.
   - (3) y (4) rozan **CWL** ([15](15-cwl-calrissian.md), P3) y **Kafka** ([20](20-kafka.md), P4) — solo vocabulario.
   - (6) y (7) apoyan en **Docker/OCI** ([17](17-docker.md), P3) — conviene leerlo antes del laboratorio de Harbor.
   Ninguna justifica romper el orden: se atienden al llegar, en el bloque que las pide.

---

## Estado

| # | Herramienta | Visión global | Laboratorio | Dominio |
|---|---|---|---|---|
| 1 | S3 / MinIO | ☑ 2026-08-07 | ☐ | ☐ |
| 2 | STAC + PgSTAC | ☑ 2026-08-07 | ☐ | ☐ |
| 3 | Argo Workflows | ☐ | ☐ | ☐ |
| 4 | Argo Events | ☐ | ☐ | ☐ |
| 5 | Keycloak | ☐ | ☐ | ☐ |
| 6 | Harbor | ☐ | ☐ | ☐ |
| 7 | GitLab | ☐ | ☐ | ☐ |

*Marca aquí el avance. Es la única fuente de verdad sobre dónde estás.*
