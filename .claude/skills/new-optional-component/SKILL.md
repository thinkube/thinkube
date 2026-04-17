---
description: Scaffold a new optional component under ansible/40_thinkube/optional/ — adds image(s) to the Harbor mirror list, generates the full playbook lifecycle (00 orchestrator, 10_configure_keycloak, 11_deploy, 17_configure_discovery, 18_test, 19_rollback), and registers the component with thinkube-control.
allowed-tools: [Read, Grep, Glob, Write, Edit, Bash]
---

# Creating a new optional component

Optional components live at `ansible/40_thinkube/optional/<name>/` and are installed via the thinkube-control UI. Every new component must follow the patterns below — the UI, service discovery, and rollback flow all depend on them.

**Before writing anything, always read two or three existing components** to copy their structure. Good references by shape of problem:

- Stateless web app + OIDC + PostgreSQL: `optional/langfuse/` or `optional/argilla/`
- OIDC via oauth2-proxy sidecar: `optional/pgadmin/` (uses `11_deploy_with_oidc.yaml`)
- Backing service, no web UI: `optional/valkey/`, `optional/nats/`, `optional/opensearch/`
- Multiple deploy steps (split 11/12/13): `optional/cvat/`, `optional/knative/`
- Keycloak OIDC client shape: `optional/langfuse/10_configure_keycloak.yaml` is the cleanest template

## Required file layout

```
ansible/40_thinkube/optional/<name>/
  00_install.yaml              # orchestrator — imports the others in order
  10_configure_keycloak.yaml   # OIDC client in realm "thinkube" (skip if no SSO)
  11_deploy.yaml               # k8s resources, Gateway/HTTPRoute, TLS
  17_configure_discovery.yaml  # thinkube-service-config ConfigMap (REQUIRED)
  18_test.yaml                 # health checks
  19_rollback.yaml             # clean removal (namespace + DB drop if any)
  README.md
  VERSION                      # single line, e.g. "0.1.0" — read by 17_configure_discovery
  templates/                   # j2 files if needed
```

Naming: all playbooks start with `---` + the Apache 2.0 / SPDX header (copy from an existing component). End every playbook's leading comment with `# 🤖 [AI-assisted]`.

## Step 1 — Mirror the image(s) to Harbor FIRST

**Do this before writing any playbook.** Deployments must pull from `{{ harbor_registry }}/library/...`, never from Docker Hub / Quay / GCR directly (rate limits, air-gap support).

Edit `ansible/40_thinkube/core/harbor-images/13_mirror_public_images.yaml` and add an entry under the appropriate comment section of `mirror_images`:

```yaml
- source: "docker.io/vendor/app:TAG"
  destination: "{{ harbor_registry }}/{{ library_project }}/app:TAG"
  description: "App — short purpose (license)"
```

Source-registry shortcuts already defined in that file: `{{ gcr_mirror }}`, `{{ quay_registry }}`, `{{ github_registry }}`, `{{ aws_ecr }}`, `{{ k8s_registry }}`. Prefer GCR mirror (`mirror.gcr.io/library/...`) over `docker.io/library/...` when the image exists there — no rate limits.

Pin tags (e.g. `3.113.0`) for anything production-critical; `:latest` is acceptable for dev-only components. After editing, run the mirror playbook to actually copy the image into Harbor (it's idempotent — skips images already present):

```bash
./scripts/tk_ansible ansible/40_thinkube/core/harbor-images/13_mirror_public_images.yaml
```

You can scope to just the new image with `--tags mirror` if iterating.

## Step 2 — 00_install.yaml (orchestrator)

Imports the other playbooks in order. Exactly this shape:

```yaml
- name: <Name> - Configure Keycloak OIDC
  import_playbook: 10_configure_keycloak.yaml

- name: <Name> - Deploy
  import_playbook: 11_deploy.yaml

- name: <Name> - Configure Service Discovery
  import_playbook: 17_configure_discovery.yaml
```

Do NOT import `18_test.yaml` or `19_rollback.yaml` from the orchestrator.

## Step 3 — 10_configure_keycloak.yaml

Uses the `keycloak/keycloak_setup` role. Creates the OIDC client in realm `thinkube` and writes a Kubernetes Secret with the client credentials into the component's namespace. Canonical pattern (from `optional/langfuse/10_configure_keycloak.yaml`):

```yaml
- name: Configure Keycloak "<name>" OIDC client
  hosts: k8s_control_plane
  gather_facts: false
  vars:
    keycloak_admin_user: "{{ admin_username }}"
    keycloak_admin_username: "{{ admin_username }}"
    keycloak_admin_password: "{{ lookup('env', 'ADMIN_PASSWORD') }}"
    keycloak_validate_certs: false

    <name>_client_id: "<name>"
    <name>_namespace: "<name>"
    <name>_hostname: "<name>.{{ domain_name }}"
    <name>_k8s_secret_name: "<name>-oauth-secret"

  tasks:
    - name: Ensure namespace exists
      kubernetes.core.k8s:
        kubeconfig: "{{ kubeconfig }}"
        name: "{{ <name>_namespace }}"
        api_version: v1
        kind: Namespace
        state: present

    - name: Setup Keycloak integration
      ansible.builtin.include_role:
        name: keycloak/keycloak_setup
      vars:
        keycloak_setup_client_id: "{{ <name>_client_id }}"
        keycloak_setup_client_body:
          clientId: "{{ <name>_client_id }}"
          enabled: true
          protocol: "openid-connect"
          standardFlowEnabled: true
          publicClient: false
          redirectUris:
            - "https://{{ <name>_hostname }}/*"
          webOrigins:
            - "https://{{ <name>_hostname }}"
        keycloak_setup_k8s_secret:
          namespace: "{{ <name>_namespace }}"
          name: "{{ <name>_k8s_secret_name }}"
          kubeconfig: "{{ kubeconfig }}"
```

Adjust `redirectUris` / `webOrigins` to match what the app requires (e.g. Langfuse needs `/api/auth/callback/keycloak`). If the app doesn't speak OIDC natively, deploy an `oauth2-proxy` sidecar instead — see `optional/pgadmin/11_deploy_with_oidc.yaml` and the `oauth2_proxy` role.

Skip this playbook entirely for components without a user-facing UI (databases, message brokers). Still create the namespace elsewhere.

## Step 4 — 11_deploy.yaml

Deploys the app. Key conventions:

- `hosts: k8s_control_plane`
- Image reference: `{{ harbor_registry }}/library/<image>:<tag>` (the image mirrored in Step 1)
- TLS: reuse the per-namespace wildcard secret. Copy from `tls-cmxela-com` in another namespace, or let the existing playbook pattern handle it — search `tls_secret_name` in sibling components.
- Ingress: use Gateway API `HTTPRoute` bound to `thinkube-gateway` in `envoy-gateway` namespace, hostname `<name>.{{ domain_name }}`. **Do not use `Ingress` resources** — the platform is Gateway API only.
- DB: if the app needs PostgreSQL, create the database and user against `postgres_hostname` using `psql` as `{{ admin_username }}` with `ADMIN_PASSWORD`. Always drop it in `19_rollback.yaml`.
- No `cert-manager` annotations — cert-manager has been removed; leftover annotations in code are stale.

## Step 5 — 17_configure_discovery.yaml (REQUIRED)

Writes the `thinkube-service-config` ConfigMap in the component's namespace. Thinkube-control reads this to render the service card in the UI. The ConfigMap is labeled and its `data.service.yaml` describes endpoints, dependencies, scaling, and any env vars to export into code-server.

Copy the exact structure from `optional/langfuse/17_configure_discovery.yaml`. Key fields in `service.yaml`:

- `service.name` — slug, must match directory name
- `service.display_name`, `description`, `category` (`ai` | `data` | `monitoring` | `infrastructure`)
- `service.icon` — pick an existing one under `/icons/tk_*.svg` (e.g. `tk_observability.svg`, `tk_data.svg`, `tk_vector.svg`, `tk_devops.svg`)
- `service.component_version` — read from the `VERSION` file: `{{ lookup('file', playbook_dir + '/VERSION') }}`
- `endpoints[].primary: true` for the main URL
- `dependencies` — list of other components needed (`postgresql`, `keycloak`, etc.)
- `scaling` — let users turn the service off via the UI (`can_disable: true`, `min_replicas: 1`)
- `environment_variables` — exposed to code-server via the `code_server_env_update` role (call the role at the end of this playbook)

Labels on the ConfigMap itself must include:
```yaml
thinkube.io/managed: "true"
thinkube.io/service-type: "optional"
thinkube.io/service-name: "<name>"
thinkube.io/component-version: "{{ component_version }}"
```

## Step 6 — 18_test.yaml

Assert pods are `Running`, the Service exists, and (if applicable) the public URL returns 2xx/3xx. Don't fail the test on auth redirects — a 302 to Keycloak counts as healthy.

## Step 7 — 19_rollback.yaml

1. Delete the component's namespace (cascades everything inside — Gateways, Services, Secrets, PVCs).
2. If the component used PostgreSQL: `DROP DATABASE IF EXISTS <db_name>;` as admin. Use `failed_when: false` on deletes so rollback is idempotent.
3. Do NOT delete the Keycloak client — it's cheap to leave and safe to re-run `10_configure_keycloak.yaml` which upserts it.

## Step 8 — Register in thinkube-metadata (so the UI shows it)

The thinkube-control backend fetches the optional-components catalog from **`thinkube-metadata/optional_components.json` on GitHub** (`https://raw.githubusercontent.com/thinkube/thinkube-metadata/main/optional_components.json`), cached for 5 minutes. If a component isn't in that file, it won't appear in the UI — regardless of whether the playbooks exist on disk. See `thinkube-control/backend/app/services/optional_components.py` (`get_components_catalog`).

**Primary registration** — edit `/home/thinkube/thinkube-platform/thinkube-metadata/optional_components.json` and add:

```json
"<name>": {
  "display_name": "<Display Name>",
  "description": "<One-line description>",
  "category": "ai|data|monitoring|infrastructure",
  "icon": "/icons/tk_*.svg",
  "requirements": ["keycloak", "postgresql"],
  "namespace": "<name>",
  "playbooks": {
    "install": "00_install.yaml",
    "test": "18_test.yaml",
    "uninstall": "19_rollback.yaml"
  }
}
```

Then commit and push the `thinkube-metadata` repo to GitHub:

```bash
cd /home/thinkube/thinkube-platform/thinkube-metadata
git add optional_components.json
git commit -m "Add <name> optional component"
git push origin main
```

The running backend picks it up on the next catalog refresh (≤5 min), or sooner if the pod restarts. No thinkube-control redeploy is needed — the file is fetched at runtime.

**Bundled fallback** — there's also a bundled copy at `thinkube-control/backend/app/data/optional_components.json` used only when the GitHub fetch fails (air-gapped clusters, GitHub outage). Keep it in sync: edit the same JSON in thinkube-control, then follow the control deploy workflow (commit/push thinkube-control, then `./scripts/tk_ansible ansible/40_thinkube/core/thinkube-control/12_deploy_dev.yaml`). Never edit `/home/thinkube/thinkube-control/` directly — Copier overwrites it.

## Checklist before handing off

- [ ] Image(s) added to `core/harbor-images/13_mirror_public_images.yaml`
- [ ] `00_install.yaml` imports 10 → 11 → 17 in order
- [ ] `10_configure_keycloak.yaml` creates client + Kubernetes secret (or skipped with note)
- [ ] `11_deploy.yaml` pulls from `{{ harbor_registry }}/library/...`, uses Gateway API HTTPRoute
- [ ] `17_configure_discovery.yaml` writes ConfigMap with required labels + calls `code_server_env_update` role
- [ ] `18_test.yaml` checks pods + endpoint
- [ ] `19_rollback.yaml` deletes namespace + drops DB
- [ ] `VERSION` file exists (e.g. `0.1.0`)
- [ ] `README.md` documents requirements, variables, and UI visibility
- [ ] Entry added to `thinkube-metadata/optional_components.json` and pushed to GitHub (authoritative — the UI reads this at runtime)
- [ ] Entry mirrored into `thinkube-control/backend/app/data/optional_components.json` (air-gap fallback) and deployed via `12_deploy_dev.yaml`
- [ ] SPDX/Apache 2.0 header at top of every `.yaml`, `# 🤖 [AI-assisted]` comment present

## What NOT to do

- Do not `kubectl apply`/`patch` by hand during development — fix the playbook and re-run it. Everything must be reproducible.
- Do not use `Ingress` resources; Gateway API (`HTTPRoute`) only.
- Do not add `cert-manager.io/*` annotations — cert-manager was removed.
- Do not import `18_test.yaml` from `00_install.yaml`.
- Do not trigger template builds or touch template namespaces — those are UI-only operations.
