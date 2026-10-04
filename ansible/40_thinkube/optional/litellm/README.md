# LiteLLM Component

LiteLLM is a unified LLM API proxy that provides a single interface for multiple LLM providers with load balancing, cost tracking, and rate limiting capabilities.

## Features

- **Multi-Provider Support**: OpenAI, Anthropic, Azure, Google, Cohere, and 100+ LLM providers
- **Load Balancing**: Distribute requests across multiple models/providers
- **Cost Tracking**: Monitor and control API usage costs
- **Rate Limiting**: Prevent API abuse and manage quotas
- **API Key Management**: Secure key storage and rotation
- **OIDC Authentication**: Integrated with Keycloak for SSO
- **Admin Dashboard**: Web UI for configuration and monitoring

## Installation

LiteLLM is an optional component. It is installed and removed from the
Optional Components page in thinkube-control, not on its own. The page runs
`00_install.yaml` to install, `18_test.yaml` to test and `19_rollback.yaml`
to remove it. It requires Harbor, Keycloak, PostgreSQL and SeaweedFS.

## Components

### Playbooks

- `00_install.yaml` - Main installation orchestrator: runs 10, 11 and 17
- `10_configure_keycloak.yaml` - Configure OIDC authentication
- `11_deploy.yaml` - Deploy LiteLLM on Kubernetes
- `17_configure_discovery.yaml` - Register service discovery
- `18_test.yaml` - Verify deployment
- `19_rollback.yaml` - Remove LiteLLM from cluster

### Resources Created

- **Namespace**: `litellm`
- **Deployment**: LiteLLM proxy server
- **Service**: Internal service on port 80 (container port 4000)
- **HTTPRoute**: HTTPS access at `litellm.{{ domain_name }}` through the Gateway API gateway
- **PVC**: `litellm-data-pvc`, 5Gi, mounted at `/app/data`
- **ConfigMap**: LiteLLM configuration
- **Secret**: `litellm-secrets`, with the master key and credentials

LiteLLM uses these core services:
- **PostgreSQL**: database `litellm` on `postgresql-official.postgres.svc.cluster.local`
- **SeaweedFS S3**: response cache in bucket `litellm-cache`

## Access

- **Dashboard**: `https://litellm.{{ domain_name }}/ui`
- **API Endpoint**: `https://litellm.{{ domain_name }}/v1`
- **API Docs**: `https://litellm.{{ domain_name }}/docs`

## Authentication

### Admin Access
- Username: `{{ admin_username }}`
- Password: `{{ admin_password }}`
- Master Key: Generated during deployment (shown in output)

### OIDC/JWT
- Keycloak client: `litellm`
- Admin scope: `litellm_proxy_admin`
- Admin role: `AI_ADMIN`
- User role: `AI_USER`

## Configuration

### Adding LLM Providers

1. Access the dashboard at `https://litellm.{{ domain_name }}/ui`
2. Login with admin credentials
3. Navigate to "Models" section
4. Add your API keys for providers (OpenAI, Anthropic, etc.)
5. Configure model routing and load balancing

### API Usage

```bash
# Using the master key
curl -X POST https://litellm.{{ domain_name }}/v1/chat/completions \
  -H "Authorization: Bearer sk-YOUR-MASTER-KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Using JWT token from Keycloak
curl -X POST https://litellm.{{ domain_name }}/v1/chat/completions \
  -H "Authorization: Bearer YOUR-JWT-TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Testing

Run the test playbook to verify the deployment:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/litellm/18_test.yaml
```

## Uninstall

LiteLLM is removed from the Optional Components page, which runs
`19_rollback.yaml`.

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n litellm
kubectl logs -n litellm deployment/litellm
```

### Verify Route
```bash
kubectl get httproute -n litellm
curl -I https://litellm.{{ domain_name }}/health/readiness
```

### Reset Master Key
If you need to reset the master key, update the secret and restart the deployment:
```bash
kubectl delete secret -n litellm litellm-secrets
```
Then reinstall LiteLLM from the Optional Components page. `11_deploy.yaml`
generates a new master key.

## References

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
- [OpenAI API Compatibility](https://docs.litellm.ai/docs/providers)

🤖 [AI-generated]