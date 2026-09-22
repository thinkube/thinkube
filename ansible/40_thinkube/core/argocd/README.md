# ArgoCD Component

This directory contains playbooks for deploying, configuring, and testing ArgoCD - a GitOps continuous delivery tool for Kubernetes.

## Installation

ArgoCD is a core component. The Thinkube installer installs it by running
`00_install.yaml`, which runs `10_configure_keycloak.yaml`, `11_deploy.yaml`,
`12_get_credentials.yaml`, `13_setup_serviceaccount.yaml` and
`17_configure_discovery.yaml` in that order. It is not installed on its own.

## Security Notice

The ArgoCD server runs in insecure mode (`server.insecure: "true"` in the
Helm values). It serves plain HTTP, and the cluster gateway (Envoy Gateway)
terminates TLS:

1. One HTTPRoute, `argocd-httproute`, sends `argocd.<domain_name>` to the
   `argocd-server` service. The gateway's `https` listener uses the wildcard
   certificate.
2. Envoy Gateway cannot mix TLS passthrough and TLS termination on the same
   port. So ArgoCD cannot keep its own TLS behind the shared gateway.
3. The `argocd-server` service sets `appProtocol: kubernetes.io/h2c`. Envoy
   then talks HTTP/2 cleartext to the backend. gRPC needs HTTP/2; over
   HTTP/1.1 the gRPC calls fail with 404.

The server is still reached only over HTTPS, because TLS ends at the gateway.
See the [official ArgoCD documentation](https://argo-cd.readthedocs.io/en/stable/operator-manual/ingress/).

### ArgoCD CLI Configuration

The UI and the gRPC API share one hostname: `argocd_hostname` and
`argocd_grpc_hostname` are both `argocd.{{ domain_name }}` in the inventory.
The CLI connects over TLS through the gateway, without `--insecure`
(`argocd_cli_insecure: false` in `13_setup_serviceaccount.yaml`):

```bash
argocd login argocd.<domain_name> --username admin --password $ADMIN_PASSWORD
```

## Component Overview

ArgoCD enables declarative, Git-based management of Kubernetes resources. It is used for managing and deploying applications across Kubernetes clusters.

## Features

- Installation via official Helm chart
- TLS-secured web interface and gRPC API
- Integration with Keycloak for Single Sign-On (SSO) authentication
- Dedicated service account for automation
- CLI installation and token generation
- Group-based RBAC for admin access

## Dependencies

- Kubernetes (kubeadm) control plane
- Wildcard TLS certificate (`infrastructure/acme-certificates`) and the Gateway API gateway
- Keycloak (for authentication)

## Playbooks

### 10_configure_keycloak.yaml

Configures Keycloak client for ArgoCD authentication:
- Creates OIDC client with proper redirect URIs
- Adds group membership mapper for RBAC
- Creates ArgoCD admin group
- Adds SSO user to admin group

### 11_deploy.yaml

Deploys ArgoCD via Helm with proper configuration:
- Retrieves client secret from Keycloak
- Creates ArgoCD namespace
- Copies wildcard certificate from default namespace
- Deploys ArgoCD Helm chart with custom admin username
- Creates the HTTPRoute for the web UI and gRPC API
- Sets up OIDC and RBAC configuration

### 12_get_credentials.yaml

Retrieves ArgoCD admin credentials:
- Uses the same admin_username as defined in inventory
- Saves credentials to .env file

### 13_setup_serviceaccount.yaml

Configures service account and installs ArgoCD CLI:
- Installs ArgoCD CLI
- Creates service account for automation
- Updates admin password to match ADMIN_PASSWORD environment variable
- Generates authentication token with secure TLS validation
- Verifies token functionality
- Saves token to .env file

### 17_configure_discovery.yaml

Creates the service-discovery ConfigMap that describes ArgoCD's endpoints.

### 18_test.yaml

Tests ArgoCD deployment:
- Verifies pods are running
- Tests the route and TLS certificate
- Checks OIDC and RBAC configuration
- Validates API access

### 19_rollback.yaml

Removes ArgoCD installation:
- Removes route resources
- Uninstalls Helm release
- Deletes service accounts and bindings
- Cleans up namespace

## Usage

Each playbook can be run individually:

```bash
# Configure Keycloak client
./scripts/run_ansible.sh ansible/40_thinkube/core/argocd/10_configure_keycloak.yaml

# Deploy ArgoCD using Helm
./scripts/run_ansible.sh ansible/40_thinkube/core/argocd/11_deploy.yaml

# Get ArgoCD admin credentials
./scripts/run_ansible.sh ansible/40_thinkube/core/argocd/12_get_credentials.yaml

# Setup service account and install CLI
./scripts/run_ansible.sh ansible/40_thinkube/core/argocd/13_setup_serviceaccount.yaml

# Test deployment
./scripts/run_ansible.sh ansible/40_thinkube/core/argocd/18_test.yaml

# Rollback (remove) ArgoCD
./scripts/run_ansible.sh ansible/40_thinkube/core/argocd/19_rollback.yaml
```

## Environment Variables

- `ADMIN_PASSWORD` - Required for authentication to Keycloak and ArgoCD

## Access Information

- Web UI: https://argocd.[domain_name]
- gRPC API: https://argocd.[domain_name] (same hostname)
- Admin username: `admin` (ArgoCD requires this specific username)
- Admin password: Initially random, then changed to ADMIN_PASSWORD value by 13_setup_serviceaccount.yaml
- SSO User: Realm user in Keycloak with access via argocd-admins group