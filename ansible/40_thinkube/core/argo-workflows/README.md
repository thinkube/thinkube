# Argo Workflows & Argo Events

This component deploys [Argo Workflows](https://argoproj.github.io/workflows/) and [Argo Events](https://argoproj.github.io/events/) for workflow automation and event-driven processing in the Thinkube environment.

## Installation

Argo Workflows and Argo Events are a core component. The Thinkube installer
installs them by running `00_install.yaml`, which runs the playbooks listed
under Deployment and then `17_configure_discovery.yaml`. They are not
installed on their own.

## Features

- Full deployment of Argo Workflows and Argo Events with Keycloak SSO integration
- Configuration of artifact storage using S3-compatible storage (SeaweedFS)
- Secure UI and gRPC access with TLS: the gateway terminates TLS with the wildcard certificate
- CLI installation and token-based authentication
- Test workflow execution
- Complete rollback capability

## Prerequisites

- Kubernetes (kubeadm) cluster
- Wildcard TLS certificate in the default namespace (`infrastructure/acme-certificates`)
- Keycloak for SSO authentication
- S3-compatible storage (SeaweedFS) for artifact storage

## Deployment

**IMPORTANT**: The playbooks MUST be executed in the numbered order. Each playbook depends on the successful completion of the previous ones.

The deployment process consists of five sequential stages:

1. **10_configure_keycloak.yaml** - Configure Keycloak Client (MUST be run first)
2. **11_deploy.yaml** - Deploy Argo Workflows & Events (requires Keycloak client from step 1)
3. **12_setup_token.yaml** - Set Up CLI & Token Authentication (requires Argo deployment from step 2)
4. **13_setup_artifacts.yaml** - Configure Artifact Storage (requires Argo deployment from step 2)
5. **15_configure_gitea_events.yaml** - Configure Argo Events for Gitea Webhooks (for CI/CD integration)

### 1. Configure Keycloak Client

```bash
cd ~/thinkube
ADMIN_PASSWORD=your_password ./scripts/run_ansible.sh ansible/40_thinkube/core/argo-workflows/10_configure_keycloak.yaml
```

This creates a new OAuth2/OIDC client in Keycloak for Argo with proper redirect URIs and audience mappings.

### 2. Deploy Argo Workflows & Events

```bash
cd ~/thinkube
ADMIN_PASSWORD=your_password ./scripts/run_ansible.sh ansible/40_thinkube/core/argo-workflows/11_deploy.yaml
```

This installs both Argo Workflows and Argo Events using Helm and configures:
- The wildcard TLS certificate, copied from the default namespace
- OIDC authentication with Keycloak
- Resource limits for all components
- An HTTPRoute for the web UI (`argo_domain`) and a GRPCRoute for the gRPC API (`argo_grpc_domain`)

### 3. Set Up CLI & Token Authentication

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/argo-workflows/12_setup_token.yaml
```

This installs the Argo CLI and configures service account token authentication for programmatic access.

### 4. Configure Artifact Storage

```bash
cd ~/thinkube
ADMIN_PASSWORD=your_password ./scripts/run_ansible.sh ansible/40_thinkube/core/argo-workflows/13_setup_artifacts.yaml
```

This integrates Argo with S3-compatible storage for artifact storage, creating:
- Credentials secret
- Artifact repository configuration
- Test workflow with artifact storage

### 5. Configure Argo Events for Gitea Webhooks

```bash
cd ~/thinkube
ADMIN_PASSWORD=your_password ./scripts/run_ansible.sh ansible/40_thinkube/core/argo-workflows/15_configure_gitea_events.yaml
```

This sets up Argo Events infrastructure to receive webhooks from Gitea:
- Creates EventBus for message processing
- Deploys EventSource to receive webhooks on port 12000
- Creates Service and HTTPRoute for webhook endpoint
- Configures Sensor to trigger Argo Workflows on push events
- Sets up webhook secret for authentication

**Note**: This creates the infrastructure only. Gitea webhook configuration is done separately in the Gitea component.

## Testing

To verify the installation is working correctly:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/argo-workflows/18_test.yaml
```

The test script verifies:
- Argo pods are running
- TLS certificates are valid
- OIDC authentication is configured
- Service account token is working
- Artifact storage is properly configured
- Test workflow executes successfully
- Argo Events components (EventBus, EventSource, Sensor)
- Webhook endpoint accessibility

## Accessing Argo

After deployment, Argo UI is available at: `https://argo.<domain_name>`

The gRPC API endpoint is available at: `https://grpc-argo.<domain_name>`

## Rollback

To completely remove Argo Workflows & Events:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/argo-workflows/19_rollback.yaml
```

This removes:
- Helm releases
- Namespace and all resources
- Route configurations
- All Argo Events resources (EventBus, EventSource, Sensor)
- (Optionally) CLI binary

Note: The Keycloak client is not automatically removed.

## Variables

The following variables are used:

| Variable | Description | Default |
|----------|-------------|---------|
| `domain_name` | Base domain name | set by the installer |
| `admin_username` | Admin username | `tkadmin` |
| `auth_realm_username` | Realm username for SSO | `thinkube` |
| `argo_namespace` | Kubernetes namespace | `argo` |
| `object_storage_s3_hostname` | S3 API hostname | `s3.{{ domain_name }}` |
| `argo_domain` | UI hostname | `argo.{{ domain_name }}` |
| `argo_grpc_domain` | gRPC API hostname | `grpc-argo.{{ domain_name }}` |
| `kubeconfig` | Kubernetes config path | `/home/{{ system_username }}/.kube/config` |
| `kubectl_bin` | Path to kubectl binary | `/home/{{ system_username }}/.local/bin/kubectl` |
| `helm_bin` | Path to helm binary | `/home/{{ system_username }}/.local/bin/helm` |

## Environment Variables

These environment variables are required:

| Variable | Description |
|----------|-------------|
| `ADMIN_PASSWORD` | Admin password for Keycloak and S3 storage |

## Troubleshooting

### Common Issues

1. **OIDC Login Failure**: Verify Keycloak client configuration and redirect URIs
   ```bash
   ./scripts/run_ssh_command.sh tkc "kubectl get secret -n argo argo-server-sso -o yaml"
   ```

2. **Artifact Storage Issues**: Check S3 storage connectivity
   ```bash
   ./scripts/run_ssh_command.sh tkc "mc ls s3/argo-artifacts"
   ```
   Note: 's3' is the mc client alias for the S3 endpoint

3. **Pod Startup Issues**: Check events and logs
   ```bash
   ./scripts/run_ssh_command.sh tkc "kubectl get events -n argo"
   ./scripts/run_ssh_command.sh tkc "kubectl logs -n argo deploy/argo-workflows-server -c argo-workflows-server"
   ```

## References

- [Argo Workflows Documentation](https://argoproj.github.io/argo-workflows/)
- [Argo Events Documentation](https://argoproj.github.io/argo-events/)
- [Argo Helm Charts](https://github.com/argoproj/argo-helm)