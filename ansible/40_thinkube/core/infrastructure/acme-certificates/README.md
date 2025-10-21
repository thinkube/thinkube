# ACME Certificates Component

This component manages SSL/TLS certificates using acme.sh and Let's Encrypt with Cloudflare DNS validation.

## Overview

This is an alternative to cert-manager that provides:
- Simple file-based certificate management
- Rate limit protection (checks before issuing)
- Support for base domain + wildcards
- Drop-in replacement for cert-manager secrets

## Requirements

1. **Cloudflare API Token** with DNS edit permissions
2. **Required inventory variables**:
   ```yaml
   domain_name: thinkube.com
   cloudflare_api_token: your-token-here
   admin_email: admin@example.com
   ```
3. **Optional variables** for GitHub backup:
   ```yaml
   github_org: your-github-org                      # Already required by installer
   github_token: ghp_...                           # Already required by installer
   github_certificates_repo: thinkube-certificates  # Repo name (default)
   cert_backup_password: your-password              # Encryption password (defaults to admin_password)
   ```

## Certificate Coverage

The playbook requests a single certificate covering:
- `thinkube.com` (base domain)
- `*.thinkube.com` (wildcard)
- `*.kn.thinkube.com` (Knative services)

## Usage

### Deploy certificates:
```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/acme-certificates/10_deploy.yaml
```

### Migration from cert-manager:

1. First ensure you have the required variable in inventory:
   ```yaml
   cloudflare_api_token: "your-cf-api-token"
   ```

2. Run the acme.sh deployment:
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/acme-certificates/10_deploy.yaml
   ```

3. Verify the secret was created:
   ```bash
   microk8s kubectl get secret -n default thinkube-com-tls
   ```

4. Remove cert-manager (optional):
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/cert-manager/19_rollback.yaml
   ```

## How it Works

1. **Installation**: Installs acme.sh in the user's home directory
2. **Certificate Check**: Verifies if existing certificate is valid and has correct domains
3. **Rate Limit Protection**: Only requests new certificate if:
   - No certificate exists
   - Certificate expires within 30 days
   - Domain list has changed
4. **Kubernetes Integration**: Creates the same secret format as cert-manager
5. **GitHub Backup** (optional): If github_org and github_token are defined:
   - Creates private repository for certificate backups
   - Encrypts certificates before storing
   - Automatically backs up when certificates are issued/renewed
6. **Auto-renewal**: Sets up cron job for automatic renewal

## Certificate Locations

- **Files**: `/etc/ssl/thinkube/thinkube.com/`
- **Kubernetes Secret**: `default/thinkube-com-tls`

## Advantages over cert-manager

1. **Rate limit friendly**: Checks before issuing
2. **Simpler**: No CRDs, operators, or complex configurations
3. **Base domain support**: Can issue certificates for base domain
4. **File backup**: Certificates exist on filesystem for easy backup
5. **Proven reliability**: acme.sh is battle-tested

## Troubleshooting

### Check certificate status:
```bash
openssl x509 -in /etc/ssl/thinkube/thinkube.com/fullchain.cer -text -noout
```

### Manual renewal:
```bash
sudo -u <system_username> ~/.acme.sh/acme.sh --renew -d thinkube.com --force
```

### View acme.sh logs:
```bash
tail -f ~/.acme.sh/acme.sh.log
```

## 🤖 [AI-assisted]