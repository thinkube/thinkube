# Keycloak Component

## Overview

This component deploys and configures Keycloak as the identity provider for the Thinkube platform. Keycloak provides centralized authentication and authorization services for all platform components.

## Playbooks

### 10_deploy.yaml
- Deploys Keycloak in development mode
- Creates namespace, service, and deployment
- Configures ingress with TLS termination
- Creates custom admin user
- Removes default admin user for security

### 15_configure_realm.yaml
- Creates the "thinkube" realm
- Configures realm settings for platform integration
- Enables unmanaged attributes policy
- Creates cluster-admins group
- Sets up initial admin user with proper group membership

### 18_test.yaml
- Validates all Keycloak resources are deployed correctly
- Tests service availability and health endpoints
- Verifies realm configuration
- Checks authentication functionality

### 19_rollback.yaml
- Removes Keycloak deployment and resources
- Cleans up namespace if empty
- Requires confirmation flag for safety

## Requirements

- Canonical k8s-snap cluster with ingress controller
- Cert-Manager deployed (CORE-003)
- Environment variable: `ADMIN_PASSWORD`

## Variables Required

From `inventory/group_vars/k8s.yml`:
- `domain_name`: Base domain for services
- `keycloak_hostname`: Full hostname for auth service (e.g., auth.thinkube.com)
- `keycloak_url`: Full URL to Keycloak instance
- `keycloak_realm`: Platform realm name (defaults to "thinkube")
- `admin_username`: Admin username (consistent across all components)
- `admin_first_name`: Admin first name
- `admin_last_name`: Admin last name
- `admin_email`: Admin email address
- `kubeconfig`: Path to kubeconfig file
- `thinkube_applications_displayname`: Display name for the realm

## Usage

### Deploy Keycloak

```bash
export ADMIN_PASSWORD='your-secure-password'
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/keycloak/10_deploy.yaml
```

### Configure Kubernetes Realm

```bash
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/keycloak/15_configure_realm.yaml
```

### Configure Custom Theme (Optional)

```bash
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/keycloak/16_configure_theme.yaml
```

This will deploy a custom Thinkube theme for the login pages. To customize:
1. Edit files in `ansible/40_thinkube/core/keycloak/theme/`
2. Re-run the playbook to deploy changes

### Test Deployment

```bash
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/keycloak/18_test.yaml
```

### Rollback

```bash
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/keycloak/19_rollback.yaml -e confirm_rollback=true
```

## Notes

- Currently deployed in development mode (`start-dev`)
- Uses NGINX ingress controller
- TLS certificates are automatically provided by cert-manager
- Admin password is shared between Keycloak admin and realm admin users
- Realm configuration enables unmanaged attributes for Kubernetes integration

## Security Considerations

- Default admin user is deleted after custom admin creation
- TLS is enforced for all connections via cert-manager
- Passwords must be provided via environment variables
- Admin credentials should be stored securely
- Certificates are automatically managed and renewed by cert-manager

## Integration

After deployment, Keycloak can be integrated with:
- Kubernetes API server for authentication
- Harbor registry for user management
- AWX for access control
- Other platform services requiring SSO