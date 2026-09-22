# Langflow

This directory contains the playbooks that deploy Langflow, a low-code AI
workflow builder, with Keycloak single sign-on and PostgreSQL storage.

## Installation

Langflow is an optional component. It is installed and removed from the
Optional Components page in thinkube-control, not on its own. The page runs
the playbooks named in `thinkube-metadata/optional_components.json`:

- install: `00_install.yaml`
- test: `18_test.yaml`
- uninstall: `19_rollback.yaml`

It requires the core components `keycloak` and `postgresql`.

## What it deploys

All resources go into the `langflow` namespace.

- **Langflow**: a Deployment with one replica, port 7860. The image is
  `{{ harbor_registry }}/library/langflow:latest`, which Harbor mirrors from
  `docker.io/langflowai/langflow` (`thinkube-metadata/mirror_images.json`).
- **OAuth2 Proxy**: all traffic goes through it. It logs the user in with
  Keycloak and then passes the request to Langflow. Langflow itself runs with
  `LANGFLOW_AUTO_LOGIN=true`.
- **Ephemeral Valkey**: session storage for OAuth2 Proxy.
- **PostgreSQL database** `langflow` in the core PostgreSQL
  (`postgresql-official` in the `postgres` namespace). The connection URL and
  the secret key are in the Secret `langflow-secret`.
- **Two PVCs**: `langflow-data` (10Gi, mounted at
  `/app/data/.cache/langflow`) and `langflow-custom-nodes` (1Gi, mounted at
  `/app/custom_nodes`). The pod sets `fsGroup: 1000`, so template playbooks
  can write node files into `/app/custom_nodes`.
- **HTTPRoute** `langflow-route`: `langflow.{{ domain_name }}` on the
  gateway's `https` listener, to the `oauth2-proxy` service.
- **Service-discovery ConfigMap** `thinkube-service-config`: thinkube-control
  reads it to detect Langflow as installed. It also publishes `LANGFLOW_URL`
  to code-server.

Langflow settings in the Deployment:

| Variable | Value |
|---|---|
| `LANGFLOW_DEVELOPER_API_ENABLED` | `true` (turns on the `/api/v2/workflows` endpoint) |
| `LANGFLOW_COMPONENTS_PATH` | `/app/custom_nodes` |
| `LANGFLOW_VARIABLES_TO_GET_FROM_ENVIRONMENT` | `OLLAMA_BASE_URL` |
| `OLLAMA_BASE_URL` | `http://ollama.ollama.svc.cluster.local:11434` |

Resources: 500m CPU and 1Gi memory requested, 2 CPU and 4Gi memory limit.

## Playbooks

| Playbook | What it does |
|---|---|
| `00_install.yaml` | Runs 11, 17 and 18 in that order |
| `11_deploy.yaml` | Copies the wildcard TLS certificate, creates the database and secret, deploys Valkey, OAuth2 Proxy, the PVCs, Langflow, its Service and the HTTPRoute, then waits for Langflow to be ready |
| `17_configure_discovery.yaml` | Creates the service-discovery ConfigMap and updates the code-server environment variables |
| `18_test.yaml` | Checks the namespace, deployments, services, HTTPRoute, TLS secret, PVCs and Keycloak client, and that the URL redirects to the OAuth2 login |
| `19_rollback.yaml` | Deletes the `langflow` namespace, the Keycloak client and the `langflow` PostgreSQL database |

## Configuration

Inventory variables the playbooks read:

| Variable | Used for |
|---|---|
| `domain_name` | Hostname `langflow.{{ domain_name }}` and the cookie domain |
| `admin_username` | PostgreSQL user and Keycloak admin user |
| `keycloak_url`, `keycloak_realm` | OIDC issuer for OAuth2 Proxy |
| `harbor_registry` | Registry for the Langflow and Valkey images |
| `gateway_name`, `gateway_namespace` | Gateway the HTTPRoute attaches to |
| `kubeconfig`, `kubectl_bin`, `helm_bin` | Cluster access |

Environment variable:

- `ADMIN_PASSWORD`: Keycloak admin password, and the password of the
  Langflow database user.

The namespace (`langflow`), the hostname and the OAuth2 client ID
(`langflow`) are set in `11_deploy.yaml`, not in the inventory.
