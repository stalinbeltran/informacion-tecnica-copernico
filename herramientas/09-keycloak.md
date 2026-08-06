# Keycloak — identidad, OIDC y JWT

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 2 — alto y **desatendido**
**Competencia de la matriz:** 20

---

## 1. Qué es, aquí

Keycloak es el **componente 7 del Middleware** (Authentication and Authorization) y la
puerta de entrada a **todo** lo demás. D2 §3.7.4 lo resume sin ambigüedad:

> *"Keycloak: An open-source identity and access management solution providing single
> sign-on, identity brokering, user federation, authentication mechanisms (OAuth, OpenID
> Connect), role-based access control (RBAC), multi-factor authentication (MFA), and audit
> logging."*

Lo notable es su alcance transversal. D2 §3.7.3 lo conecta con **seis** componentes:
User Workspace, Front-end Services, Data Discovery and Access, Data Processing, Application
Registry y Resource Management. Y D2 §6.6 detalla la integración con GitLab y Harbor:

> *"Users log in through Keycloak, which manages their identity and assigns appropriate roles
> and permissions across the platform's various services, including GitLab and Harbor…
> a user might have a 'Developer' role in GitLab and a 'Maintainer' role in Harbor."*

**Consecuencia práctica:** cuando algo devuelve 401 o 403 en esta plataforma, Keycloak es
sospechoso por defecto. Y como toca seis componentes, un problema de identidad se manifiesta
en sitios muy distintos del origen.

---

## 2. La frontera

| Materia | Proveedor | Tú |
|---|---|---|
| Autenticación del **clúster** (kubeconfig, RBAC de K8s) | Sí | Consumes |
| Aislamiento de namespaces | Sí | Consumes |
| **Realms, clients, roles, usuarios del Middleware** | No | **Sí** |
| **Mapeo de roles Keycloak → RBAC de la plataforma** | No | **Sí** |
| **Diagnóstico de tokens rechazados** | No | **Sí** |
| **Integración Keycloak ↔ GitLab ↔ Harbor** | No | **Sí** |
| Federación LDAP con el directorio de AIG | Coordinas | **Configuras** |

La tabla del perfil ESA clasifica *Kubernetes Security* como "Covered" — eso es el RBAC
**del clúster**. La identidad **de la plataforma** cae bajo *Platform Domains Support*, que
está marcado **Not covered**. Son dos sistemas de permisos distintos y vas a tener que
explicar esa diferencia más de una vez.

**No confundas nunca:** `kubectl auth can-i` (RBAC de Kubernetes) con el rol del usuario en
Keycloak (RBAC de la plataforma). Un usuario puede tener todos los roles de Keycloak y
ningún permiso en el clúster, y viceversa.

---

## 3. Qué debes saber

### Nivel imprescindible — el modelo de Keycloak

- **Realm**: el espacio aislado de identidad. Todo cuelga de aquí.
- **Client**: una aplicación que delega la autenticación. Tipos:
  - *Confidential* (tiene secreto; backends como stac-fastapi o el servicio de URLs firmadas).
  - *Public* (sin secreto; SPAs como el portal — usan PKCE).
  - *Bearer-only* (solo valida tokens, no autentica).
- **Roles**: de realm y de client. **Composite roles** (roles que agrupan roles).
- **Groups** y su mapeo a roles. Escalan mucho mejor que asignar roles uno a uno.
- **Client scopes** y **mappers**: cómo un atributo del usuario acaba dentro del token. Es
  lo que necesitas cuando una aplicación espera un claim que no está llegando.
- **Identity providers** y **user federation**: LDAP, que D2 §3.7.4 menciona explícitamente
  (*"Keycloak integrates with LDAP for managing user credentials and profiles"*).

### Nivel imprescindible — OAuth2 / OIDC

- Diferencia entre **autenticación** (OIDC, quién eres) y **autorización** (OAuth2, qué
  puedes hacer). Se confunden constantemente.
- Flujos:
  - **Authorization Code + PKCE** — el del portal y las aplicaciones web.
  - **Client Credentials** — el de máquina a máquina, el que usarás en scripts y en los
    componentes internos.
  - *Implicit* y *Password grant*: obsoletos, sabe por qué.
- Los tres tokens: **access token** (corto, para llamar APIs), **refresh token** (renovar),
  **ID token** (identidad del usuario, no para autorizar).
- Endpoints del realm (memorízalos, los vas a usar a mano):
  ```
  /realms/{realm}/.well-known/openid-configuration
  /realms/{realm}/protocol/openid-connect/auth
  /realms/{realm}/protocol/openid-connect/token
  /realms/{realm}/protocol/openid-connect/userinfo
  /realms/{realm}/protocol/openid-connect/certs        ← las claves públicas (JWKS)
  /realms/{realm}/protocol/openid-connect/logout
  ```

### Nivel imprescindible — JWT

Esto es lo que de verdad tienes que dominar, porque es donde ocurre el diagnóstico.

- Estructura: `header.payload.signature`, en base64url. **Se puede decodificar sin ninguna
  clave** — decodificar no es validar.
- Claims que importan:

| Claim | Qué es | Por qué falla |
|---|---|---|
| `exp` | Expiración | El token caducó — **causa nº 1** |
| `iat` / `nbf` | Emitido en / no antes de | Reloj desincronizado entre servicios |
| `iss` | Emisor | La URL del realm no coincide con la que espera el servicio |
| `aud` | Audiencia | **Causa nº 2**: el token es válido pero no *para ese servicio* |
| `azp` | Parte autorizada | El client que lo pidió |
| `sub` | Sujeto | El ID del usuario |
| `realm_access.roles` | Roles de realm | Falta el rol → 403, no 401 |
| `resource_access.{client}.roles` | Roles de client | Ídem, pero por cliente |
| `scope` | Ámbitos concedidos | El servicio exige un scope que no está |

- **La distinción que resuelve la mitad de los incidentes:**
  **401 = no sé quién eres** (token ausente, malformado, expirado, firma inválida, `iss`/`aud`
  incorrectos). **403 = sé quién eres y no puedes** (falta el rol o el scope).
  Si confundes las dos, buscas en el sitio equivocado durante media hora.
- Validación: firma con la clave pública del JWKS, `exp`, `iss`, `aud`. Rotación de claves
  (`kid` en el header) y por qué un servicio que cachea el JWKS puede rechazar tokens tras
  una rotación.

### Nivel operativo

- Crear un realm, un client confidencial, roles y usuarios — a mano y de forma reproducible.
- Obtener un token por client credentials y por authorization code.
- Configurar un mapper para que un rol aparezca en el token con el nombre que la aplicación
  espera.
- Configurar la audiencia: por defecto Keycloak no siempre incluye el `aud` que un servicio
  espera. **Éste es el error de configuración más frecuente en integraciones nuevas.**
- MFA: configurar OTP como requerido para roles administrativos. D2 §8.4 lo exige.
- Federación LDAP: mapeo de atributos, sincronización, y qué pasa cuando el directorio
  cambia.
- Audit logging: D2 §3.7.2 y §6.6 lo mencionan explícitamente
  (*"Keycloak provides logging and auditing features that track user activity across the
  platform"*). Saber dónde están esos logs y cómo consultarlos.
- Duración de tokens: equilibrio entre seguridad y usabilidad. Un access token de 5 minutos
  con un servicio que no refresca = usuarios enfadados.

### Nivel avanzado

- Diseño del modelo de roles de la plataforma: qué roles existen, qué puede hacer cada uno,
  cómo se mapean a GitLab y a Harbor.
- Revisión periódica de accesos — principio explícito de D1 §3.2.2 y D2 §8.4
  (*"regular audits of access permissions"*).
- Integración con el servicio de URLs firmadas: el `Authorization: Bearer <token>` del
  esquema `signed_url_auth` es un token de Keycloak. Ver [06-s3-minio.md](06-s3-minio.md).
- Alta disponibilidad de Keycloak: si Keycloak cae, **cae el acceso a todo**. Es un punto
  único de fallo por diseño.

---

## 4. Datos de la plataforma que debes tener a mano

**Requisitos de seguridad (D1 §3.2.2, D2 §8.2 y §8.4):**
- Cifrado en tránsito y en reposo. **TLS 1.2 o superior.**
- HTTPS y SFTP para transferencias.
- **RBAC** con principio de **mínimo privilegio**.
- **MFA** obligatorio para acceso a partes sensibles.
- **Audit logging** de todos los intentos de acceso, revisados periódicamente.
- Cumplimiento del **ESA Personal Data Protection Framework (PDP)** y GDPR: minimización de
  datos, limitación de propósito, derechos del interesado, consentimiento gestionado.
- Notificación de incidentes con datos personales al **DPO de ESA** (y art. 33 del GDPR
  cuando aplique).

**El token en el flujo de descarga (D3 §6.2)** — el caso concreto donde verás Keycloak
funcionando:

```bash
curl -X 'POST' \
  'https://<sign-url>?url=s3%3A%2F%2Fsentinel-2%2Fred.tif' \
  -H 'Authorization: Bearer eyJ...cmQ' \
  -d ''
```

Si eso devuelve **401**, el problema es Keycloak (token expirado, audiencia equivocada,
firma inválida). Si devuelve **403**, el usuario está autenticado pero no tiene el rol.
Si devuelve la URL firmada y **la descarga posterior** da 403, el problema es la política de
S3 → [06-s3-minio.md](06-s3-minio.md). **Tres 403 distintos con tres causas distintas.**

**Integración con GitLab y Harbor (D2 §6.6):**
- GitLab: autenticación vía Keycloak; los roles determinan quién puede hacer push y quién
  puede mergear en ramas protegidas.
- Harbor: acceso a imágenes según rol; puede restringir el acceso a imágenes según el
  resultado del escaneo de vulnerabilidades.
- Un mismo usuario tiene roles distintos en cada servicio, todos gobernados desde Keycloak.

**Plan de respuesta a incidentes (D2 §8.6):** detección automatizada → contención (aislar,
**revocar accesos**, parchear) → recuperación → notificación y reporte con lecciones
aprendidas. La revocación de accesos es una acción de Keycloak: **ten el procedimiento
escrito antes de necesitarlo.**

---

## 5. Laboratorio

Parte del **Bloque 7 — 8 horas**, compartido con [18-ingress-tls-cert-manager.md](18-ingress-tls-cert-manager.md).

1. **Instala Keycloak** en tu clúster. Accede a la consola de administración.
2. **Crea un realm** `copernicus-lab`.
3. **Crea un client OIDC confidencial** para tu API. Anota el client ID y el secreto.
4. **Crea roles y un usuario**, asigna el rol.
5. **Obtén un token** por client credentials:
   ```bash
   curl -s -X POST \
     "$KC/realms/copernicus-lab/protocol/openid-connect/token" \
     -d "grant_type=client_credentials" \
     -d "client_id=stac-api" \
     -d "client_secret=$SECRET" | jq -r .access_token
   ```
6. **Decodifica el JWT** y lee sus claims:
   ```bash
   echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq
   ```
   Identifica `exp`, `iss`, `aud`, `realm_access.roles`. **Este comando es el que más vas a
   usar en incidentes reales.**
7. **Protege un endpoint** con ese token — el catálogo del [bloque 4](05-stac-pgstac-stac-fastapi.md)
   detrás de un proxy que valide JWT.
8. **Prueba los tres fallos**, y observa que dan códigos distintos:
   - Token **expirado** → espera a que caduque o pon una duración de 30 s.
   - **Audiencia equivocada** → pide el token con otro client.
   - **Sin el rol** → quita el rol al usuario.
9. **RBAC de Kubernetes**, para contrastar: crea un `Role`/`RoleBinding` de mínimo
   privilegio y verifica con `kubectl auth can-i`. **Comprueba en voz alta que has entendido
   que son dos sistemas distintos.**
10. **MFA:** activa OTP para el usuario administrador y pásalo.

---

## 6. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Token expirado | 401 con `exp` en el pasado. Cómo verlo en 5 segundos |
| Audiencia (`aud`) equivocada | 401 con un token perfectamente válido. **El más desconcertante** |
| `iss` incorrecto (URL interna vs externa del realm) | Falla solo desde fuera del clúster |
| Usuario sin el rol requerido | **403**, no 401. La distinción que ahorra media hora |
| Mapper mal configurado | El rol existe en Keycloak pero no aparece en el token |
| Reloj del pod desincronizado | `nbf` en el futuro; token rechazado sin razón aparente |
| Rotación de claves con JWKS cacheado | Tokens nuevos rechazados por firma |
| Client secret rotado sin actualizar el Secret de Kubernetes | El componente deja de autenticarse |

---

## 7. Averías de producción que este bloque entrena

- **Avería 7:** 401 en la STAC API — token expirado o audiencia incorrecta.
- Contribuye a la **12** (descarga que devuelve 403): distinguir si el 403 es de Keycloak o
  de la política de bucket.

---

## 8. Árbol de diagnóstico: "acceso denegado"

Ésta es la pregunta madre del bloque 7. Cinco capas posibles; identifica la correcta antes
de tocar nada.

```
¿Es RED?          → ¿el servicio responde?  curl -v, nc -zv, ¿hay Endpoints?
                    Síntoma: connection refused / timeout
                    → 01-kubernetes.md, 18-ingress-tls-cert-manager.md

¿Es TLS?          → ¿el certificado es válido, tiene el SAN correcto, está expirado?
                    Síntoma: error de handshake, "certificate verify failed"
                    → 18-ingress-tls-cert-manager.md

¿Es TOKEN?        → 401. Decodifica el JWT: exp, iss, aud, firma
                    → este archivo

¿Es ROL?          → 403 desde la aplicación. Mira realm_access.roles y resource_access
                    → este archivo

¿Es RBAC de K8s?  → 403 de kubectl o del API de Kubernetes
                    kubectl auth can-i <verbo> <recurso> --as=<sa>
                    → 01-kubernetes.md

¿Es POLÍTICA DE APLICACIÓN? → 403 de S3 con token válido
                    → 06-s3-minio.md
```

**Regla:** `connection refused` ≠ `401` ≠ `403`. Los tres se investigan en sitios distintos.
Si sabes cuál es cuál, ya has hecho la mitad del trabajo.

---

## 9. Comandos de bolsillo

```bash
# Configuración del realm (empieza siempre aquí)
curl -s "$KC/realms/$REALM/.well-known/openid-configuration" | jq

# Token por client credentials (máquina a máquina)
TOKEN=$(curl -s -X POST "$KC/realms/$REALM/protocol/openid-connect/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=$CLIENT" -d "client_secret=$SECRET" | jq -r .access_token)

# Token por usuario y contraseña (solo laboratorio)
TOKEN=$(curl -s -X POST "$KC/realms/$REALM/protocol/openid-connect/token" \
  -d "grant_type=password" -d "client_id=$CLIENT" \
  -d "username=$U" -d "password=$P" | jq -r .access_token)

# Decodificar el JWT — EL comando del bloque
echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq

# Solo lo que importa en un incidente
echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | \
  jq '{exp, iss, aud, azp, roles: .realm_access.roles}'

# ¿Cuándo expira, en tiempo humano?
date -d @$(echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq -r .exp)

# ¿Sigue vivo el token?
curl -s "$KC/realms/$REALM/protocol/openid-connect/userinfo" \
  -H "Authorization: Bearer $TOKEN" | jq

# Claves públicas (para entender un fallo de firma)
curl -s "$KC/realms/$REALM/protocol/openid-connect/certs" | jq '.keys[].kid'

# Usar el token contra la API
curl -s "$STAC/search" -H "Authorization: Bearer $TOKEN" -w '\n%{http_code}\n'

# El otro RBAC — no confundir
kubectl auth can-i create workflows -n <ns> --as=system:serviceaccount:<ns>:<sa>
```

---

## 10. Criterio de dominio

- [ ] Creo un realm, un client confidencial, roles y un usuario, de memoria.
- [ ] Obtengo un token por client credentials sin consultar nada.
- [ ] **Decodifico un JWT y leo `exp`, `iss`, `aud` y roles en menos de 30 segundos.**
- [ ] Explico qué es un JWT, cómo se valida, y **por qué un token puede ser rechazado** — al menos cuatro causas distintas.
- [ ] Distingo 401 de 403 y sé dónde investigar cada uno.
- [ ] Ante un 401, un 403 y un `connection refused`, **no confundo los tres**.
- [ ] Configuro la audiencia de un client correctamente a la primera.
- [ ] Sé cómo revocar el acceso de un usuario durante un incidente de seguridad.
- [ ] Explico la diferencia entre el RBAC de Keycloak y el RBAC de Kubernetes con un ejemplo.

---

## 11. Artefacto que produces

**`runbooks/acceso-denegado.md`** — el árbol del §8: ¿es red, es TLS, es token, es RBAC de
Kubernetes, es política de la aplicación? Con los comandos exactos de cada rama y el código
de error que corresponde a cada capa.

Es uno de los tres runbooks fundacionales de tu operación, junto con `diagnostico-pod.md` y
`ingesta-fallida.md`.

**Alimenta:** Producto 2 (runbooks), Producto 6 (SOPs de seguridad operativa), y el
procedimiento de contención del plan de respuesta a incidentes (D2 §8.6).

---

## 12. Qué preguntar

**A ESA / Terradue:**
1. ¿Cuántos realms hay y cómo se organizan? ¿Uno por entorno, uno para toda la plataforma?
2. ¿Cuál es el modelo de roles de la plataforma y cómo se mapea a GitLab y a Harbor?
3. ¿Qué clients existen, cuáles son confidenciales y qué audiencias esperan?
4. **¿Cómo se gestionan los secretos y la rotación de credenciales entre componentes** (ESO, backend de secretos)?
5. ¿Qué duración tienen los access tokens y los refresh tokens?
6. ¿El servicio de URLs firmadas valida el token localmente (JWKS) o consulta a Keycloak?
7. ¿Hay federación con un directorio de AIG prevista? ¿LDAP o Active Directory?
8. ¿Dónde están los audit logs de Keycloak y con qué retención?

**A la AIG:**
1. ¿Existe un directorio corporativo con el que federar? ¿Quién lo administra?
2. ¿Qué instituciones usuarias existen ya y cómo se les dará de alta?

---

## 13. Fuentes

**Documentos del proyecto:** D2 §3.7 completo (Authentication and Authorization: propósito,
implementación, integración con seis componentes, stack), §6.6 (Access Control — la
integración detallada con GitLab y Harbor, token-based auth, MFA, role assignment,
monitoring y auditing), §8.2 (marco de seguridad, TLS 1.2+), §8.3 (protección de datos, ESA
PDP, GDPR), §8.4 (RBAC, MFA, audit logging y los beneficios de Keycloak), §8.6 (respuesta a
incidentes: revocación de accesos), §3.5.4 (OAuth/OIDC en front-end). D3 §2.3.4 (seguridad y
control de acceso centralizado), §3.4.2 (control de acceso a la ingesta, OAuth2), §6.2
(el Bearer token en el flujo de URLs firmadas). D1 §3.2.2 (requisitos de seguridad), §8.1.4.

**Documentación oficial:** `keycloak.org/documentation` — Server Administration Guide
(realms, clients, roles, mappers) y Securing Applications. Complemento útil: `jwt.io` para
inspeccionar tokens (**nunca pegues un token de producción en un sitio web**; usa el comando
local del §9).

---

## 14. Bitácora / hallazgos

*(Realms y clients reales, mappers configurados, tokens rechazados y su causa exacta,
procedimiento de revocación acordado.)*
