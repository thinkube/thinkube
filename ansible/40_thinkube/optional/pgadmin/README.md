# PgAdmin Component

PgAdmin is a web-based administration tool for PostgreSQL databases. This deployment provides a fully-featured PgAdmin instance with Keycloak OIDC authentication.

## Installation

PgAdmin is an optional component. It is installed and removed from the
Optional Components page in thinkube-control, not on its own. The page runs
`00_install.yaml` to install, `18_test.yaml` to test and `19_rollback.yaml`
to remove it. It requires the `postgresql` and `keycloak` components.

## Overview

- **Component Type**: Optional
- **Namespace**: `pgadmin`
- **Default Access**: https://pgadmin.{{ domain_name }} (`pgadmin_hostname`)
- **Authentication**: OIDC with Keycloak (single sign-on)

## Deployment Structure

```
00_install.yaml             # Runs 10, 11 and 17 in order
10_configure_keycloak.yaml  # Create Keycloak client for PgAdmin
11_deploy_with_oidc.yaml    # Deploy PgAdmin with OIDC authentication
17_configure_discovery.yaml # Create the service-discovery ConfigMap
18_test.yaml                # Validate deployment and configuration
19_rollback.yaml            # Remove PgAdmin and cleanup resources
```

## Requirements

- Kubernetes (kubeadm) cluster with the Gateway API gateway
- Wildcard TLS certificate (`infrastructure/acme-certificates`)
- PostgreSQL databases to manage
- Keycloak instance running and accessible
- ADMIN_PASSWORD environment variable set

## PostgreSQL Configuration

If PostgreSQL is deployed in the cluster, PgAdmin will automatically be configured with the connection details during deployment.

The Thinkube PostgreSQL server will appear in the server list with:
- Automatic connection parameters
- Pre-configured credentials
- No manual configuration needed

After deployment:
- Users authenticate via Keycloak SSO
- Auto-creation of users on first login
- No local authentication required
- Initial login creates a master password for encrypting saved passwords

## Testing

Validate the deployment:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/pgadmin/18_test.yaml
```

Tests verify:
- Namespace and resources exist
- Pods are running
- Service and HTTPRoute (`pgadmin-httproute`) configured
- TLS certificate present
- HTTP connectivity working

## Configuration Variables

Required inventory variables:
- `domain_name`: Base domain for the cluster
- `admin_username`: Admin username for applications
- `kubectl_bin`: Path to kubectl binary
- `pgadmin_hostname`: `pgadmin.{{ domain_name }}` in `inventory/group_vars/k8s.yml`

For OIDC configuration:
- `keycloak_url`: Keycloak server URL
- `keycloak_realm`: Keycloak realm name
- `ADMIN_PASSWORD`: Environment variable with the Keycloak admin password

## Features

### Database Management
- Connect to multiple PostgreSQL instances
- Query editor with syntax highlighting
- Visual query builder
- Database schema browser
- User and role management

### Security
- TLS encryption for all connections
- OIDC authentication
- Session management
- Secure cookie configuration

### Integration
- Keycloak SSO support
- Kubernetes-native deployment
- Configurable resource limits

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n pgadmin
kubectl logs -n pgadmin -l app=pgadmin
```

### Verify HTTPRoute
```bash
kubectl get httproute -n pgadmin
kubectl describe httproute pgadmin-httproute -n pgadmin
```

### OIDC Issues
- Verify Keycloak is accessible
- Check client configuration in Keycloak
- Review pod logs for authentication errors
- Ensure redirect URIs are correct

## Rollback

Removing PgAdmin from the Optional Components page runs `19_rollback.yaml`.
It:
- Deletes the HTTPRoute, Service, Deployment, ConfigMaps and TLS secret
- Removes the namespace
- Does not remove the `pgadmin` Keycloak client

## Notes

- OIDC is the only login; there is no basic authentication
- Database connections are configured through the UI
- PgAdmin data is in `emptyDir` volumes, so it is lost when the pod restarts