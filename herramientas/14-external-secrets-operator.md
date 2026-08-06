# External Secrets Operator (ESO)

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 3 — lo tocas al operar workspaces y despliegues
**Competencia de la matriz:** 12

---

## 1. Qué es, aquí

ESO trae secretos desde un almacén externo y los materializa como `Secret` de Kubernetes.
Resuelve el problema que hace incompatibles GitOps y credenciales: **no puedes versionar un
secreto en Git, pero necesitas que el despliegue sea declarativo**.

D2 lo menciona en dos sitios. En el **User Workspace** (§3.6.2):

> *"**Secret Management**: Sensitive information and secrets are managed using the **External
> Secrets Operator (ESO)**, ensuring secure storage and retrieval."*

Y en **Resource Management** (§3.8.2):

> *"The External Secrets Operator (ESO) is used to securely manage and **inject secrets**
> (e.g., API keys, passwords) **into the resource configurations**, ensuring sensitive
> information is handled securely."*

Es una pieza pequeña con un impacto desproporcionado: cuando ESO falla, el síntoma aparece
en otro sitio —un pod que no arranca, una conexión rechazada, un workflow que no puede subir
un artefacto— y la causa está aquí.

---

## 2. La frontera

Tuyo. Es parte del stack del Middleware (*workspace / resource management → Not covered*).

El backend de secretos (Vault, un gestor del proveedor, o el propio Kubernetes) puede ser
frontera compartida: si es un servicio del proveedor, su disponibilidad es suya y su
contenido es tuyo. Confírmalo (§8).

---

## 3. Qué debes saber

### Nivel imprescindible

**Los objetos**
- **`SecretStore`** (namespaced) y **`ClusterSecretStore`** (global): definen **dónde** está
  el almacén externo y **cómo** se autentica ESO contra él.
- **`ExternalSecret`**: define **qué** secreto traer y **cómo** materializarlo. Campos clave:
  - `refreshInterval` — cada cuánto vuelve a leer. Es lo que hace funcionar la rotación.
  - `secretStoreRef` — qué store usar.
  - `target` — nombre del `Secret` resultante, `creationPolicy`, `template`.
  - `data` / `dataFrom` — el mapeo entre claves remotas y claves locales.
- **`PushSecret`**: el camino inverso, menos frecuente.

**El `template`** — lo que más se usa y menos se entiende. Permite construir el Secret con la
forma exacta que la aplicación espera:
```yaml
target:
  name: db-credentials
  template:
    data:
      # construir una URL de conexión a partir de dos claves remotas
      DATABASE_URL: "postgresql://{{ .usuario }}:{{ .clave }}@pg-svc:5432/pgstac"
```
Sin esto, acabas metiendo lógica de composición en la aplicación.

**Estado y diagnóstico**
- Condición `Ready` del `ExternalSecret` y su `SecretSyncedError`.
- Dónde mirar: `kubectl describe externalsecret`, y los logs del operador.
- **La trampa fundamental:** ESO actualiza el `Secret`, pero **un pod que ya montó ese Secret
  como variable de entorno no lo ve cambiar**. Montado como volumen sí se actualiza (con
  retardo); como `env` no, nunca. Esto explica el 90 % de los "roté la credencial y sigue
  fallando".

### Nivel operativo

- Configurar un `SecretStore` contra el backend real.
- Rotación de credenciales de extremo a extremo: rotar en el backend → ESO refresca el
  Secret → **reiniciar los pods que lo consumen como env**. Ese tercer paso es el que se
  olvida.
- `creationPolicy: Owner` vs `Merge` vs `None`.
- Recargar sin reiniciar: `reloader` u otro operador que observe el Secret y haga rollout
  automático. Si no está, el reinicio es manual y debe estar en el runbook.
- Integración con ArgoCD: el `ExternalSecret` **sí** va en Git; el `Secret` resultante no.
  Ésta es la razón de existir de ESO en un entorno GitOps.
  Ver [12-argocd.md](12-argocd.md).

### Nivel avanzado

- Un `ClusterSecretStore` con credenciales por namespace, para que cada workspace lea solo
  lo suyo.
- Auditoría: quién lee qué secreto y cuándo (depende del backend).
- Estrategia de rotación periódica alineada con el requisito de **revisión periódica de
  accesos** de D1 §3.2.2 y D2 §8.4.

---

## 4. Dónde se manifiestan los fallos de ESO

Ésta es la tabla que hace útil este archivo, porque **el síntoma nunca dice "ESO"**:

| Síntoma observado | Componente donde aparece | Causa en ESO |
|---|---|---|
| Pod en `CreateContainerConfigError` | Cualquiera | El `Secret` no existe: el `ExternalSecret` nunca sincronizó |
| `ImagePullBackOff` por credenciales | Cualquier pod | El pull secret de Harbor no se materializó → [10](10-harbor.md) |
| Workflow que no sube el artefacto | Argo Workflows | Credenciales de MinIO ausentes → [07](07-argo-workflows.md) |
| `FATAL: password authentication failed` | stac-fastapi | Credencial de PostgreSQL rotada, Secret desactualizado → [19](19-postgresql-postgis.md) |
| 401 del componente contra Keycloak | Cualquiera | Client secret rotado sin propagar → [09](09-keycloak.md) |
| Descarga que falla al firmar | Servicio de URLs firmadas | Credenciales S3 caducadas → [06](06-s3-minio.md) |

**Regla de diagnóstico:** ante cualquier fallo de autenticación entre componentes, comprueba
el `ExternalSecret` **antes** de investigar el servicio destino. Cuesta 20 segundos y
descarta la causa más probable.

---

## 5. Laboratorio

1. **Instala ESO** en el clúster.
2. **`SecretStore` simple.** El backend más fácil para aprender es `kubernetes` (leer
   secretos de otro namespace) o un Vault en modo dev. No necesitas una nube.
3. **`ExternalSecret`** que traiga una credencial y la materialice como `Secret`. Comprueba
   con `kubectl get secret` que aparece.
4. **Usa el `template`** para construir una `DATABASE_URL` a partir de usuario y contraseña
   separados.
5. **Rotación — el ejercicio central:**
   - Cambia el valor en el backend.
   - Espera el `refreshInterval` y comprueba que el `Secret` cambió.
   - Comprueba que **el pod que lo tiene como `env` sigue con el valor viejo**.
   - Reinicia el pod y comprueba que ahora sí.
   - **Escribe esto en el runbook.** Es la lección del bloque.
6. **Monta el mismo secreto como volumen** y repite. Observa la diferencia.
7. **Rompe el `SecretStore`** (credencial inválida) y lee el error en
   `describe externalsecret`.
8. **Con ArgoCD**: pon el `ExternalSecret` en Git, sincroniza, y comprueba que el `Secret`
   resultante no genera drift.

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| `SecretStore` con credencial inválida | `SecretSyncedError`; dónde leerlo |
| Clave remota inexistente en `data` | El `ExternalSecret` falla entero, no parcialmente |
| Rotar la credencial y **no** reiniciar el pod | **La avería 17 del catálogo**, en directo |
| `refreshInterval` muy largo | Rotación que tarda horas en propagarse |
| Backend caído | Los Secrets existentes siguen; los nuevos no se crean. Fallo silencioso |
| `creationPolicy: Owner` sobre un Secret preexistente | ESO lo sobrescribe |

---

## 7. Avería de producción que este bloque entrena

**Avería 17:** base de datos inalcanzable — credencial rotada sin actualizar el Secret.

Es la avería que mejor ilustra por qué ESO existe y por qué su fallo es difícil de
diagnosticar: **nada en el mensaje de error menciona secretos**. Solo dice "authentication
failed", y tú tienes que saber remontar la cadena.

---

## 8. Comandos de bolsillo

```bash
# Estado de los ExternalSecrets
kubectl get externalsecrets -A
kubectl get es -n <ns> -o custom-columns=\
NAME:.metadata.name,STORE:.spec.secretStoreRef.name,READY:.status.conditions[0].status

# Por qué falla
kubectl describe externalsecret <nombre> -n <ns>
kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets --tail=100

# ¿Se materializó el Secret? ¿Con qué claves?
kubectl get secret <nombre> -n <ns> -o jsonpath='{.data}' | jq 'keys'

# Ver un valor (con cuidado: no lo dejes en el historial)
kubectl get secret <nombre> -n <ns> -o jsonpath='{.data.password}' | base64 -d

# Forzar refresco
kubectl annotate externalsecret <nombre> -n <ns> \
  force-sync=$(date +%s) --overwrite

# El paso que se olvida: reiniciar quien lo consume
kubectl rollout restart deployment/<nombre> -n <ns>

# ¿Quién consume este Secret?
kubectl get pods -n <ns> -o json | jq -r '
  .items[] | select(
    (.spec.volumes[]?.secret.secretName == "<nombre>") or
    (.spec.containers[].envFrom[]?.secretRef.name == "<nombre>")
  ) | .metadata.name'
```

Esa última consulta es oro puro durante un incidente: te dice exactamente qué reiniciar.

---

## 9. Criterio de dominio

- [ ] Configuro un `ExternalSecret` y lo veo materializarse.
- [ ] Diagnostico un fallo de sincronización leyendo `describe` y los logs del operador.
- [ ] Uso `template` para construir un secreto compuesto.
- [ ] **Explico por qué un secreto rotado no llega a un pod que lo tiene como `env`.**
- [ ] Ejecuto una rotación completa: backend → ESO → reinicio de consumidores.
- [ ] Sé identificar qué pods consumen un Secret dado.
- [ ] Entiendo por qué ESO es imprescindible en un entorno GitOps.
- [ ] Ante un fallo de autenticación entre componentes, compruebo ESO primero.

---

## 10. Artefacto que produces

**`runbooks/rotacion-de-credenciales.md`** — el procedimiento completo, con los tres pasos
explícitos (rotar en el backend, verificar el `Secret`, reiniciar consumidores) y la lista de
qué credenciales existen, dónde viven y quién las consume.

**Alimenta:** Producto 2 (runbooks), Producto 6 (SOPs de seguridad operativa). Y responde
directamente a una pregunta que ESA espera que sepas contestar: *"¿cómo se gestionan los
secretos y la rotación de credenciales entre componentes?"*

---

## 11. Qué preguntar

**A ESA / Terradue:**
1. **¿Cómo se gestionan los secretos y la rotación de credenciales entre componentes (ESO, backend de secretos)?**
2. ¿Qué backend de secretos se usa: Vault, un servicio del proveedor, secretos de Kubernetes?
3. ¿Qué `refreshInterval` está configurado y con qué política de rotación?
4. ¿Hay un mecanismo de recarga automática (reloader) o el reinicio es manual?
5. ¿Qué credenciales existen entre componentes y cuál es su ciclo de vida?

**Al proveedor:**
1. ¿Ofrecen un gestor de secretos como servicio? ¿Cuál es su SLA?
2. ¿Con qué frecuencia rotan las credenciales de acceso a S3 y a PostgreSQL, y cómo lo notifican?

---

## 12. Fuentes

**Documentos del proyecto:** D2 §3.6.2 (Secret Management en el User Workspace), §3.6.4
(ESO en el stack del workspace), §3.8.2 (ESO inyectando secretos en configuraciones de
recursos), §3.8.4 (ESO en el stack de Resource Management), §8.4 (control de accesos y
revisión periódica). D1 §3.2.2 (requisitos de seguridad, mínimo privilegio).

**Documentación oficial:** `external-secrets.io` — API reference (`SecretStore`,
`ExternalSecret`), Providers, Templating.

---

## 13. Bitácora / hallazgos

*(Backend real, credenciales inventariadas, rotaciones ejecutadas, incidentes causados por
secretos desactualizados.)*
