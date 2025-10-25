# Cert-Manager Component

This directory contains Ansible playbooks for deploying and managing cert-manager on k8s-snap with an improved workflow that uses Let's Encrypt staging certificates from the start.

## Overview

Cert-manager automatically issues and renews SSL certificates from Let's Encrypt using Cloudflare DNS validation. The new workflow starts with staging certificates (avoiding TLS errors) and allows upgrading to production certificates when ready.

## Certificate Workflow

### Initial Deployment
1. **Automatic Staging Certificates**: When you run `10_deploy.yaml`, it automatically requests Let's Encrypt **staging** certificates
2. **No TLS Errors**: Staging certificates have proper certificate chains (unlike self-signed), avoiding OIDC/OAuth authentication issues
3. **Immediate Availability**: Services can start immediately with valid (though not browser-trusted) certificates
4. **No Rate Limits**: Staging certificates can be requested unlimited times during development

### Production Certificates
1. **When Ready**: After all services are deployed and tested, run `letsencrypt/20_request_production.yaml`
2. **Automatic Propagation**: Certificates are automatically synced to all namespaces
3. **Rate Limited**: Production certificates are limited to 5 per domain per week

## Prerequisites

- k8s-snap control and worker nodes (CORE-001, CORE-002)
- Cloudflare API token with DNS edit permissions
- DNS zones configured in Cloudflare

## Environment Variables

- `CLOUDFLARE_TOKEN`: Required - Your Cloudflare API token with DNS edit permissions

## Directory Structure

```
cert-manager/
├── 10_deploy.yaml                    # Deploy cert-manager with staging certificates
├── 18_test.yaml                      # Test cert-manager functionality
├── 19_rollback.yaml                  # Remove cert-manager
├── letsencrypt/                      # Let's Encrypt specific operations
│   ├── 20_request_production.yaml    # Request production certificates
│   ├── 21_configure_renewal.yaml     # Configure renewal and propagation
│   ├── 22_sync_certificates.yaml     # Manually trigger certificate sync
│   └── 29_rollback_to_staging.yaml   # Emergency rollback to staging
└── README.md                         # This file
```

## Playbooks

### Core Playbooks

#### 10_deploy.yaml
Deploys cert-manager and automatically requests staging certificates.

Features:
- Installs cert-manager with CRDs
- Creates Cloudflare API token secret
- Configures staging and production ClusterIssuers
- **Automatically requests staging wildcard certificates**
- Implements robust monitoring for certificate issuance
- Typical completion time: 5-7 minutes

#### 18_test.yaml
Tests cert-manager installation and certificate status.

#### 19_rollback.yaml
Removes cert-manager and all associated resources.

### Let's Encrypt Operations (letsencrypt/)

#### 20_request_production.yaml
Upgrades from staging to production certificates.

Features:
- Pre-flight checks to ensure readiness
- Monitors production certificate issuance
- Removes TLS workarounds after success
- Backs up production certificates
- **WARNING**: Uses rate-limited production API

#### 21_configure_renewal.yaml
Enhances certificate renewal and propagation.

Features:
- Advanced sync script with change detection
- Optional pod restart on renewal
- Certificate expiry monitoring
- Renewal event detection

#### 22_sync_certificates.yaml
Manually triggers certificate synchronization.

Use when:
- You need immediate propagation
- After manual certificate changes
- For troubleshooting sync issues

#### 29_rollback_to_staging.yaml
Emergency rollback from production to staging certificates.

Use when:
- Production certificates cause issues
- Need to troubleshoot without rate limits
- Testing disaster recovery

## Variables

Key variables (from inventory):
- `domain_name`: Base domain for certificates
- `cert_manager_namespace`: Namespace for cert-manager (default: cert-manager)
- `harbor_registry`: Harbor registry hostname for container images

## Certificate Details

The deployment creates wildcard certificates covering:
- `*.thinkube.com` - For all subdomains
- `*.kn.thinkube.com` - For Knative services

Certificate characteristics:
- **Staging**: Issued by "Fake LE", not browser-trusted but valid chain
- **Production**: Issued by "Let's Encrypt Authority", fully trusted
- **Duration**: 90 days
- **Renewal**: Automatic, 30 days before expiry

## Usage

### Initial Deployment (with Staging Certificates)

1. Set the Cloudflare API token:
   ```bash
   export CLOUDFLARE_TOKEN='your-token-here'
   ```

2. Deploy cert-manager (automatically gets staging certificates):
   ```bash
   cd ~/thinkube
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/cert-manager/10_deploy.yaml
   ```

3. Test the installation:
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/cert-manager/18_test.yaml
   ```

### Upgrade to Production Certificates (When Ready)

1. Ensure all services are working with staging certificates
2. Request production certificates:
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/cert-manager/letsencrypt/20_request_production.yaml
   ```

3. Monitor certificate propagation:
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/cert-manager/letsencrypt/22_sync_certificates.yaml
   ```

### Certificate Management

Configure enhanced renewal monitoring:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/cert-manager/letsencrypt/21_configure_renewal.yaml
```

Force certificate sync:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/cert-manager/letsencrypt/22_sync_certificates.yaml
```

Emergency rollback to staging:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/cert-manager/letsencrypt/29_rollback_to_staging.yaml
```

## Certificate Synchronization

Certificates are automatically synchronized across namespaces:
- **Automatic**: CronJob runs every hour
- **On-Renewal**: DaemonSet detects renewals and triggers sync
- **Manual**: Use `22_sync_certificates.yaml` for immediate sync

The sync process:
1. Reads certificate from default namespace
2. Finds all namespaces with TLS secrets
3. Updates only changed certificates
4. Optionally restarts pods mounting certificates

## Using Certificates in Services

For any service, copy the certificate to its namespace:

```yaml
- name: Get wildcard certificate from default namespace
  kubernetes.core.k8s_info:
    kubeconfig: "{{ kubeconfig }}"
    api_version: v1
    kind: Secret
    namespace: default
    name: "{{ domain_name.replace('.', '-') }}-tls"
  register: wildcard_cert

- name: Copy wildcard certificate to service namespace
  kubernetes.core.k8s:
    kubeconfig: "{{ kubeconfig }}"
    state: present
    definition:
      apiVersion: v1
      kind: Secret
      metadata:
        name: "{{ service_namespace }}-tls-secret"
        namespace: "{{ service_namespace }}"
      type: kubernetes.io/tls
      data:
        tls.crt: "{{ wildcard_cert.resources[0].data['tls.crt'] }}"
        tls.key: "{{ wildcard_cert.resources[0].data['tls.key'] }}"
```

## Troubleshooting

### Certificate Not Issuing
```bash
# Check certificate status
kubectl describe certificate thinkube-com-tls -n default

# Check certificate request
kubectl get certificaterequest -n default

# Check ACME order
kubectl get order -n default

# Check DNS challenges
kubectl get challenges -n default
```

### Staging vs Production Detection
```bash
# Check current certificate type
kubectl get secret thinkube-com-tls -n default -o jsonpath='{.data.tls\.crt}' | \
  base64 -d | openssl x509 -issuer -noout
```

### Certificate Sync Issues
```bash
# Check sync job logs
kubectl logs -n cert-manager -l job-name -f

# Check renewal monitor
kubectl logs -n cert-manager -l app=cert-renewal-monitor

# View sync history
kubectl get jobs -n cert-manager | grep cert-sync
```

### Common Issues

1. **DNS Validation Failing**:
   - Verify Cloudflare API token permissions
   - Check DNS propagation timeout (default: 180s)
   - Monitor challenge: `kubectl describe challenge -n default`

2. **Services Not Using New Certificate**:
   - Check if namespace has certificate
   - Verify secret name matches service configuration
   - Force sync with `22_sync_certificates.yaml`
   - Some services may need pod restart

3. **Rate Limit Hit**:
   - Use staging certificates for testing
   - Check weekly limit: 5 certificates per domain
   - Wait for limit reset (weekly)

## Migration Notes

This replaces manual certificate management with:
- Automatic renewal (no cron jobs)
- Native Kubernetes integration
- Better error handling with staging certificates
- No filesystem access required
- Centralized certificate management

## 🤖 AI-Generated Enhancements

The staging certificate workflow and monitoring improvements were developed with AI assistance to solve TLS verification issues with self-signed certificates.