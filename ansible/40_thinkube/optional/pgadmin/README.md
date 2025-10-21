# PgAdmin Component

PgAdmin is a web-based administration tool for PostgreSQL databases. This deployment provides a fully-featured PgAdmin instance with Keycloak OIDC authentication.

## Overview

- **Component Type**: Optional
- **Namespace**: `pgadmin`
- **Default Access**: https://pgadmin.{{ domain_name }}
- **Authentication**: OIDC with Keycloak (single sign-on)

## Deployment Structure

```
10_configure_keycloak.yaml  # Create Keycloak client for PgAdmin
11_deploy_with_oidc.yaml    # Deploy PgAdmin with OIDC authentication
18_test.yaml                # Validate deployment and configuration
19_rollback.yaml            # Remove PgAdmin and cleanup resources
```

## Requirements

- MicroK8s cluster with ingress controller
- Cert-manager with wildcard certificate
- PostgreSQL databases to manage
- Keycloak instance running and accessible
- ADMIN_PASSWORD environment variable set

## Deployment

Deploy PgAdmin with OIDC authentication:

```bash
cd ~/thinkube
# Set admin password
export ADMIN_PASSWORD='your-admin-password'

# Step 1: Create Keycloak client
./scripts/run_ansible.sh ansible/40_thinkube/optional/pgadmin/10_configure_keycloak.yaml

# Step 2: Deploy PgAdmin with OIDC
./scripts/run_ansible.sh ansible/40_thinkube/optional/pgadmin/11_deploy_with_oidc.yaml
```

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
- Service and ingress configured
- TLS certificate present
- HTTP connectivity working
- OIDC configuration (if enabled)

## Configuration Variables

Required inventory variables:
- `domain_name`: Base domain for the cluster
- `admin_username`: Admin username for applications
- `kubectl_bin`: Path to kubectl binary
- `primary_ingress_class`: Ingress class to use

For OIDC configuration:
- `keycloak_url`: Keycloak server URL
- `keycloak_realm`: Keycloak realm name
- `KEYCLOAK_ADMIN_PASSWORD`: Environment variable with admin password

## Features

### Database Management
- Connect to multiple PostgreSQL instances
- Query editor with syntax highlighting
- Visual query builder
- Database schema browser
- User and role management

### Security
- TLS encryption for all connections
- Optional OIDC authentication
- Session management
- Secure cookie configuration

### Integration
- Keycloak SSO support
- Kubernetes-native deployment
- Persistent storage support
- Configurable resource limits

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n pgadmin
kubectl logs -n pgadmin -l app=pgadmin
```

### Verify Ingress
```bash
kubectl get ingress -n pgadmin
kubectl describe ingress pgadmin-ingress -n pgadmin
```

### OIDC Issues
- Verify Keycloak is accessible
- Check client configuration in Keycloak
- Review pod logs for authentication errors
- Ensure redirect URIs are correct

## Rollback

Remove PgAdmin deployment:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/pgadmin/19_rollback.yaml
```

This will:
- Delete all PgAdmin resources
- Remove the namespace
- Clean up Keycloak client (if configured)

## Notes

- Default deployment uses basic authentication
- OIDC configuration replaces basic auth completely
- Database connections are configured through the UI
- Consider persistent volumes for production use