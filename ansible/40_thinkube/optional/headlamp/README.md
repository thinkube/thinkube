# Headlamp Component

[Headlamp](https://headlamp.dev/) is an easy-to-use, extensible web UI for
Kubernetes. It provides browser-based cluster visibility — pods, logs, events,
workloads, and routine actions — so the operator can inspect and manage the
cluster without juggling a local `kubeconfig`.

In thinkube, Headlamp is deployed as an **optional** component: a single web
dashboard fronted by Keycloak SSO, with full-cluster access for the operator.

## Access

- **URL**: `https://headlamp.{{ domain_name }}`

The dashboard is served through the Envoy Gateway with the wildcard ACME
(TLS) certificate — the same route/cert path every other thinkube service uses.

## Authentication & Authorization

### SSO is the only front door

Headlamp signs in through **Keycloak OIDC** (realm `thinkube`). There is **no**
token- or kubeconfig-paste login path exposed — the route is reachable only
through the Gateway with OIDC:

1. Browse to `https://headlamp.{{ domain_name }}`.
2. An unauthenticated request redirects to Keycloak.
3. Sign in with your thinkube (Keycloak) credentials.
4. Keycloak redirects back to `https://headlamp.{{ domain_name }}/oidc-callback`
   and the dashboard loads.

OIDC wiring (set up by `10_configure_keycloak.yaml`, consumed by `11_deploy.yaml`):

- **Keycloak client**: `headlamp` (confidential)
- **Issuer**: `https://auth.{{ domain_name }}/realms/thinkube`
- **Redirect URI**: `https://headlamp.{{ domain_name }}/oidc-callback`
- **Scopes**: `openid email profile`

### Cluster-admin behind SSO (single-user model)

> ⚠️ **Caveat:** Authorization is **binary**. Headlamp runs as a single
> ServiceAccount bound to **`cluster-admin`**, so **anyone who can sign in via
> Keycloak SSO gets full-cluster (read/write) access**. The SSO front door *is*
> the security boundary — there is no per-user RBAC mapping from Keycloak groups
> to Kubernetes roles. This matches thinkube's single-operator model; do not
> treat Headlamp access as least-privilege.

## Version

This component pins Headlamp **0.43.0** (Helm chart `headlamp`, appVersion
`0.43.0`) — see the `VERSION` file. The image is **mirrored into Harbor** (the
rate-limit-avoidance pattern) rather than pulled from a public registry at
deploy time.

Only Headlamp's **core UI** is shipped; its plugin system is intentionally **not**
enabled (out of scope).

## Installation

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/headlamp/00_install.yaml
```

Headlamp is also listed in the **thinkube-control** optional-component catalog
(registered by `17_configure_discovery.yaml`) and can be installed/uninstalled
from there.

## Components

### Playbooks

- `00_install.yaml` — Installation orchestrator (calls the steps in order)
- `10_configure_keycloak.yaml` — Create/update the Headlamp OIDC client; capture
  issuer + client id/secret
- `11_deploy.yaml` — Helm install from the Harbor-mirrored image; OIDC wiring;
  `cluster-admin` ServiceAccount; wildcard cert copy; `headlamp.{{ domain_name }}`
  HTTPRoute
- `17_configure_discovery.yaml` — Register the optional-service discovery ConfigMap
- `18_test.yaml` — Validate the deployment
- `19_rollback.yaml` — Remove Headlamp from the cluster

### Resources created

- **Namespace**: `headlamp`
- **Deployment**: Headlamp web UI
- **ServiceAccount + ClusterRoleBinding**: bound to `cluster-admin`
- **Service**: internal service
- **HTTPRoute**: HTTPS access at `headlamp.{{ domain_name }}` via the Envoy Gateway
- **Secret**: wildcard TLS certificate copied into the namespace
- **ConfigMap**: service-discovery registration (`thinkube.io/service-type: optional`)

## Testing

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/headlamp/18_test.yaml
```

The test asserts: the Deployment is Available, `headlamp.{{ domain_name }}`
returns HTTP 200 over TLS, the Keycloak OIDC client exists and an unauthenticated
request redirects to Keycloak, the `cluster-admin` ClusterRoleBinding is present,
and the discovery ConfigMap exists.

## Uninstall

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/headlamp/19_rollback.yaml
```

Rollback is clean and idempotent — it Helm-uninstalls the release, deletes the
`headlamp` namespace, and removes the Keycloak client, leaving no residue so a
subsequent `00_install.yaml` succeeds.

## Troubleshooting

### Check pod status

```bash
kubectl get pods -n headlamp
kubectl logs -n headlamp deployment/headlamp
```

### Verify the route

```bash
kubectl get httproute -n headlamp
curl -I https://headlamp.{{ domain_name }}
```

### Sign-in redirect not firing / OIDC errors

```bash
# Confirm the Keycloak client exists in the thinkube realm
# (auth.{{ domain_name }} → realm thinkube → Clients → headlamp)
kubectl get deployment headlamp -n headlamp -o yaml | grep -i oidc
```

Confirm the issuer, client id/secret, scopes, and the redirect URI
(`https://headlamp.{{ domain_name }}/oidc-callback`) match the Keycloak client.

## References

- [Headlamp Documentation](https://headlamp.dev/docs/)
- [Headlamp GitHub](https://github.com/headlamp-k8s/headlamp)
- [Headlamp OIDC Setup](https://headlamp.dev/docs/latest/installation/in-cluster/oidc/)

🤖 [AI-generated]
