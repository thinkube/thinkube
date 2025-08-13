# ArgoCD Component

This directory contains playbooks for deploying, configuring, and testing ArgoCD - a GitOps continuous delivery tool for Kubernetes.

## Security Notice

The ArgoCD deployment uses TLS for secure connections:

1. ArgoCD server is configured with TLS termination at the Ingress level
2. The wildcard certificate from the default namespace is used for TLS
3. CLI commands connect securely through the gRPC Ingress

**Important Note on Ingress Configuration:**

According to the [official ArgoCD documentation](https://argo-cd.readthedocs.io/en/stable/operator-manual/ingress/), when using separate Ingress resources for HTTP and gRPC (as we do in this deployment), the ArgoCD server must run in insecure mode. This is a requirement for the gRPC API to work properly with Nginx Ingress.

The server is still accessible only via HTTPS because TLS termination happens at the Ingress level:
- The HTTP/HTTPS Ingress uses the `nginx.ingress.kubernetes.io/backend-protocol: "HTTP"` annotation
- The gRPC Ingress uses the `nginx.ingress.kubernetes.io/backend-protocol: "GRPC"` annotation
- Both Ingresses use the same TLS certificate

For more details, see [How to eat the gRPC cake and have it too!](https://blog.argoproj.io/how-to-eat-the-grpc-cake-and-have-it-too-77bc4ed555f6) from the ArgoCD team.

### ArgoCD CLI Configuration

The ArgoCD CLI must use the `--insecure` flag when connecting to the ArgoCD API server because:

1. The server is running in insecure mode (required for the gRPC ingress to work)
2. The gRPC connection between CLI and server requires this special handling
3. This does not compromise security as TLS termination happens at the Ingress level

As explained in the [official ArgoCD documentation](https://argo-cd.readthedocs.io/en/stable/operator-manual/ingress/):

> When using separate hostnames for the UI and gRPC API, the API server should be run with TLS disabled. This is because the gRPC API server and the UI server cannot share the same TLS certificate if they each have their own hostname.

This is why the following configuration is used:
- The ArgoCD server runs with the `--insecure` flag in the Helm chart
- The `argocd_cli_insecure` variable is set to `true` in the service account setup playbook
- API calls to the server use the `-k` flag with curl

If you're using the ArgoCD CLI manually, you'll need to include the `--insecure` flag:

```bash
argocd login argocd-grpc.thinkube.com --insecure --username admin --password $ADMIN_PASSWORD
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

- CORE-001: MicroK8s Control Node
- CORE-003: Cert-Manager (for TLS certificates)
- CORE-004: Keycloak (for authentication)

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
- Configures ingress for both web UI and gRPC API
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

### 18_test.yaml

Tests ArgoCD deployment:
- Verifies pods are running
- Tests ingress and TLS certificates
- Checks OIDC and RBAC configuration
- Validates API access

### 19_rollback.yaml

Removes ArgoCD installation:
- Removes ingress resources
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
- gRPC API: https://argocd-grpc.[domain_name]
- Admin username: `admin` (ArgoCD requires this specific username)
- Admin password: Initially random, then changed to ADMIN_PASSWORD value by 13_setup_serviceaccount.yaml
- SSO User: Realm user in Keycloak with access via argocd-admins group