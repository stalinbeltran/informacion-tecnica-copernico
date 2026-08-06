# Ingress NGINX + cert-manager + NetworkPolicy — la red de aplicación

**Nivel exigido:** O — lo haces solo, bajo presión, sin guía
**Prioridad:** 3 — lo tocas al exponer y proteger servicios
**Competencia de la matriz:** 8

---

## 1. Qué es, aquí

Es la capa por la que el Middleware se hace accesible: quién entra, por dónde, con qué
certificado, y qué puede hablar con qué dentro del clúster.

D2 §8.2 fija el marco:

> *"**Data Encryption**: All sensitive data is encrypted both at rest and in transit using
> industry-standard encryption protocols (e.g., **TLS 1.2 or later**)… **Secure Data
> Transfer**: The platform employs secure data transfer protocols, such as **HTTPS and
> SFTP**."*

Y el perfil ESA te asigna la parte lógica (§2.3.2):

> *"Configuration and usage of provider-managed StorageClasses, PersistentVolumes and Claims,
> **Middleware-specific Ingress resources, application-level TLS certificates**, and logical
> use of namespaces, RBAC, quotas, and **network policies**."*

Los servicios expuestos son, como mínimo: el portal, la STAC API, Titiler, el servicio de
URLs firmadas, Keycloak, GitLab, Harbor y ArgoCD. Cada uno con su Ingress y su certificado.

---

## 2. La frontera — leerla bien evita perder horas

| Materia | Proveedor | Tú |
|---|---|---|
| **Ingress Controller** (el software) y su operación | **Sí** | No |
| **Recursos `Ingress`** del Middleware | No | **Sí** |
| **Certificados TLS de aplicación** | No | **Sí** |
| **NetworkPolicies de aplicación** | Aislamiento base entre namespaces | **Sí, dentro de tus namespaces** |
| Balanceador de carga | **Sí** | Consumes y validas su SLA |
| DNS público | Coordinas con AIG/proveedor | Consumes |
| CNI y red de bajo nivel | **Sí** | Nada |

**Regla práctica:** si el problema desaparece cambiando tu recurso `Ingress` o tu `Secret`
de TLS, es tuyo. Si el Ingress Controller entero está caído o el balanceador no enruta, es
del proveedor — y tu trabajo es la evidencia.

**Especificaciones del balanceador contratado (pliego §8.5.14):** HA en 2 zonas,
**≥ 1 Gbps** (D1 pedía ≥ 4 Gbps), **25.000 RPS** pico, **10.000** conexiones simultáneas.
Estos números son tu vara cuando el portal va lento con 3.000 usuarios concurrentes.

---

## 3. Qué debes saber

### Nivel imprescindible — Ingress

- `Ingress`: `ingressClassName`, `rules` (host, paths), `pathType`
  (`Prefix`, `Exact`, `ImplementationSpecific`), `backend.service` con `name` y `port`.
- **La cadena completa**, que debes poder recorrer mentalmente:
  ```
  DNS → balanceador → Service del Ingress Controller → pod del controlador
      → regla Ingress → Service de la aplicación → Endpoints → pod
  ```
  Un 502 significa que la cadena se rompió **después** del controlador. Un 404 del
  controlador significa que ninguna regla casó.
- Anotaciones de NGINX que usarás: `proxy-body-size` (crítico para subidas grandes),
  `proxy-read-timeout` (crítico para consultas STAC lentas o descargas),
  `ssl-redirect`, `rewrite-target`, `backend-protocol`.
- Diferencia entre un 502 (backend no responde), 503 (sin endpoints) y 504 (timeout).

### Nivel imprescindible — TLS

- `Secret` de tipo `kubernetes.io/tls` con `tls.crt` y `tls.key`.
- **SAN** (Subject Alternative Name): el certificado debe cubrir **el nombre exacto** que
  usa el cliente. Un certificado para `api.ejemplo.pa` no vale para `www.api.ejemplo.pa`.
  **Es el fallo de certificado más común.**
- Cadena de confianza: certificado + intermedios. Un certificado válido con la cadena
  incompleta falla en unos clientes y no en otros — diagnóstico infernal si no lo sabes.
- Fechas de validez y por qué la expiración es una avería programada que puedes prevenir.
- TLS 1.2 mínimo, por requisito de D1/D2.

### Nivel imprescindible — cert-manager

- `Issuer` (namespaced) y `ClusterIssuer` (global).
- Tipos: self-signed (laboratorio), CA propia, ACME/Let's Encrypt (HTTP-01 o DNS-01).
- `Certificate`: `secretName`, `dnsNames`, `issuerRef`, `duration`, `renewBefore`.
- Renovación automática y **cómo comprobar que va a renovar** antes de que expire.
- Anotación `cert-manager.io/cluster-issuer` en el Ingress para emisión automática.
- Diagnóstico: `Certificate` → `CertificateRequest` → `Order` → `Challenge`. **Cuando algo
  falla, el error está en el último eslabón**, no en el `Certificate`.

### Nivel operativo — NetworkPolicy

- Modelo: si **ningún** NetworkPolicy selecciona un pod, todo está permitido. En cuanto
  **uno** lo selecciona, solo se permite lo que ese (y otros) declaren.
- `podSelector`, `namespaceSelector`, `ipBlock`, `ports`.
- `policyTypes: [Ingress, Egress]` — y el error de aplicar una política de egress olvidando
  el DNS.
- **El DNS**: CoreDNS vive en `kube-system` y escucha en UDP/TCP 53. Una política de egress
  que no lo permita rompe **toda** resolución de nombres, y el síntoma es
  `connection refused` a nombres pero éxito por IP. **Avería 16 del catálogo.**
- Requiere un CNI que las soporte. Confirmar con el proveedor.

### Nivel avanzado

- TLS entre servicios internos (mTLS), si aplica.
- Rate limiting y protección básica en el Ingress.
- Política de red de mínimo privilegio para el Middleware completo: quién habla con quién.
- Correlación entre 502/504 y los límites del balanceador (25.000 RPS, 10.000 conexiones).

---

## 4. Laboratorio

**Bloque 7 — 8 horas**, junto con [09-keycloak.md](09-keycloak.md).

1. **Instala Ingress NGINX** en tu clúster `kind`.
2. **Expón el catálogo del [bloque 4](05-stac-pgstac-stac-fastapi.md)** por HTTP. Comprueba
   que responde.
3. **Instala cert-manager** y crea un `ClusterIssuer` self-signed.
4. **Emite un certificado** para tu host y añade el bloque `tls` al Ingress. Accede por
   HTTPS.
5. **Inspecciona el certificado**: `openssl s_client`. Lee el SAN, el emisor y las fechas.
6. **Rompe el SAN**: emite un certificado para `otro-nombre.local` y úsalo. Observa el error
   exacto del cliente.
7. **Rompe la clase**: cambia `ingressClassName` a una inexistente. Observa que el Ingress
   se crea pero nada lo atiende — **sin ningún error visible**.
8. **Provoca un 502**: cambia el `port` del backend a uno equivocado. Comprueba con
   `kubectl get endpoints` que el Service sí tiene pods pero el puerto no casa.
9. **NetworkPolicy**: permite que solo el catálogo hable con PostgreSQL. Comprueba desde un
   tercer pod que queda bloqueado.
10. **Rompe el DNS**: añade una política de egress sin permitir UDP 53 a `kube-system`.
    Observa que el pod no resuelve nombres pero sí alcanza IPs. **Arréglalo.**

---

## 5. Sabotajes obligatorios

| Sabotaje | Qué aprendes |
|---|---|
| Certificado con **SAN incorrecto** | El error del cliente y cómo verlo con `openssl` |
| Certificado **expirado** | Avería 6 del catálogo |
| Cadena incompleta (falta el intermedio) | Falla en unos clientes y no en otros |
| `Ingress` con **clase equivocada** | Se crea, nada lo atiende, ningún error. Desconcertante |
| `Service` con `targetPort` equivocado | **502. Avería 5 del catálogo** |
| Service sin endpoints (selector que no casa) | 503, no 502. La diferencia importa |
| **NetworkPolicy que corta el DNS** | **Avería 16.** `connection refused` por nombre, OK por IP |
| `proxy-body-size` por defecto con una subida grande | 413; la anotación que nadie recuerda |
| `proxy-read-timeout` corto con una consulta STAC lenta | 504 intermitente bajo carga |

---

## 6. Averías de producción que este bloque entrena

- **Avería 5:** Ingress responde 502 — Service apuntando a puerto equivocado.
- **Avería 6:** TLS inválido en el portal — certificado expirado o SAN incorrecto.
- **Avería 16:** servicio inalcanzable entre pods — NetworkPolicy que corta el DNS.

---

## 7. Árbol de diagnóstico: "no puedo acceder al servicio"

Recorre la cadena **de fuera hacia dentro**. Cada paso descarta el anterior.

1. **¿DNS resuelve?** `dig <host>` desde fuera. Si no, es DNS público — coordina con AIG.
2. **¿Llega al balanceador?** `curl -v` y mira si conecta. Timeout → red o balanceador
   (proveedor).
3. **¿Es TLS?** Error de handshake o de certificado → `openssl s_client`, mira SAN y fechas.
4. **¿El controlador tiene una regla que case?** 404 del controlador → revisa `host` y
   `path` del Ingress, y `ingressClassName`.
5. **¿El Service tiene endpoints?** `kubectl get endpoints <svc>`.
   - Vacío → el selector no casa con ningún pod, o los pods no están `Ready` → **503**.
   - Con endpoints → sigue.
6. **¿El puerto casa?** `targetPort` del Service vs puerto real del contenedor → **502**.
7. **¿El pod responde?** `port-forward` directo al pod y prueba. Si funciona aquí y no fuera,
   el problema está entre el controlador y el Service.
8. **¿Hay NetworkPolicy bloqueando?** Prueba desde otro pod del mismo namespace y desde uno
   de otro namespace.
9. **¿Es autenticación?** 401/403 → [09-keycloak.md](09-keycloak.md).

**Los códigos, en una línea:** `timeout`/`refused` = red · `502` = backend no responde ·
`503` = sin endpoints · `504` = timeout del backend · `404` del controlador = ninguna regla
casó · `401`/`403` = identidad, no red.

---

## 8. Comandos de bolsillo

```bash
# Inspeccionar el certificado servido (el comando del bloque)
openssl s_client -connect api.ejemplo.pa:443 -servername api.ejemplo.pa </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName

# ¿Cuándo expira? (ponlo en una alerta)
echo | openssl s_client -connect api.ejemplo.pa:443 -servername api.ejemplo.pa 2>/dev/null \
  | openssl x509 -noout -enddate

# Ingress y su clase
kubectl get ingress -A
kubectl describe ingress <nombre> -n <ns>
kubectl get ingressclass

# ¿El Service apunta a algo?
kubectl get endpoints <svc> -n <ns>
kubectl get svc <svc> -n <ns> -o yaml | yq '.spec.ports'

# Saltarse el Ingress para aislar el problema
kubectl port-forward -n <ns> svc/<svc> 8080:80
curl -v http://localhost:8080/

# cert-manager: la cadena de diagnóstico
kubectl get certificate -A
kubectl describe certificate <nombre> -n <ns>
kubectl get certificaterequest,order,challenge -n <ns>
kubectl describe challenge <nombre> -n <ns>      # ← aquí suele estar el error real
kubectl logs -n cert-manager -l app=cert-manager --tail=100

# Logs del Ingress Controller (los 502 aparecen aquí)
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller --tail=100 | grep ' 50[0-9] '

# NetworkPolicy
kubectl get networkpolicy -n <ns>
kubectl describe networkpolicy <nombre> -n <ns>

# Probar conectividad y DNS desde dentro
kubectl run tmp --rm -it --image=nicolaka/netshoot -n <ns> -- bash
  # dentro:  nslookup pg-svc ; curl -v http://stac-api:8080/ ; nc -zv pg-svc 5432
```

---

## 9. Criterio de dominio

- [ ] Expongo un servicio por HTTPS con certificado, de principio a fin.
- [ ] Inspecciono un certificado y leo su SAN, emisor y fechas en 10 segundos.
- [ ] **Distingo 502, 503, 504, 404 del controlador y `connection refused`**, y sé dónde investigar cada uno.
- [ ] Compruebo endpoints antes de culpar al pod.
- [ ] Diagnostico la cadena de cert-manager hasta el `Challenge`.
- [ ] Escribo una `NetworkPolicy` que **no rompe el DNS**.
- [ ] Sé qué parte es mía y qué parte es del proveedor, y lo justifico con la tabla del §2.
- [ ] Tengo una alerta sobre la expiración de certificados **antes** de que expiren.

---

## 10. Artefacto que produces

Parte de **`runbooks/acceso-denegado.md`** (ver [09-keycloak.md](09-keycloak.md)): las ramas
*red* y *TLS* del árbol, con el mapa de códigos del §7.

Añade una **alerta de expiración de certificados** a tus reglas de Prometheus (30 días
antes). Es la avería más evitable del catálogo.

**Alimenta:** Producto 2 (runbooks), Producto 6 (SOPs).

---

## 11. Qué preguntar

**Al proveedor:**
1. ¿Qué Ingress Controller está desplegado, en qué versión, y cuál es su `ingressClassName`?
2. ¿Qué CNI usan y **soporta NetworkPolicies**?
3. ¿Cómo se solicita una regla nueva en el balanceador o una IP pública?
4. ¿Cómo se miden y reportan los 25.000 RPS y las 10.000 conexiones del balanceador?
5. ¿Hay WAF o rate limiting delante del Ingress?
6. ¿Quién gestiona el DNS público de los servicios?

**A ESA / Terradue:**
1. ¿Qué servicios se exponen públicamente y con qué nombres?
2. ¿Cómo se emiten los certificados: cert-manager con ACME, CA de AIG, certificados
   comerciales?
3. ¿Hay NetworkPolicies definidas por el Middleware o las defino yo?

---

## 12. Fuentes

**Documentos del proyecto:** D2 §8.2 (cifrado en tránsito, TLS 1.2+, HTTPS y SFTP), §9.3
(load balancing), §3.8.3 (recursos de red para front-end). D1 §3.2.2 (requisitos de
seguridad), §4.4. Pliego §8.5.14 (especificaciones del balanceador: HA 2 zonas, ≥ 1 Gbps,
25.000 RPS, 10.000 conexiones), §8.5.3 y §8.5.16 (el proveedor despliega Ingresses
específicos a petición). **Perfil ESA §2.3.2** (Ingress del Middleware y certificados TLS de
aplicación son tuyos) y tabla §1.1 (*Ingress / Networking — Covered* para el controlador).

**Documentación oficial:** `kubernetes.io/docs` → Services, Load Balancing, and Networking;
Network Policies. `kubernetes.github.io/ingress-nginx` (anotaciones). `cert-manager.io/docs`
(Troubleshooting es el capítulo útil).

---

## 13. Bitácora / hallazgos

*(Hosts reales, emisores de certificados, políticas de red aplicadas, incidentes de acceso y
su causa.)*
