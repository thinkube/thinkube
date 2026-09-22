# Knative Deployment

This directory contains playbooks for deploying Knative on the Thinkube platform.

## Installation

Knative is an optional component. It is installed and removed from the
Optional Components page in thinkube-control, not on its own. The page runs
`00_install.yaml` to install, `18_test.yaml` to test and `19_rollback.yaml`
to remove it. `00_install.yaml` runs `10_deploy.yaml` and
`17_configure_discovery.yaml`.

## Overview

Knative provides serverless capabilities for Kubernetes, including:
- **Knative Serving**: Deploy and manage serverless workloads
- **Knative Eventing**: Event-driven architecture support
- **net-gateway-api**: Routing through the main Envoy Gateway via DomainMapping

## Components Deployed

- Knative Serving v1.17.0
- Knative Eventing v1.17.1
- net-gateway-api v1.17.0
- Sample Python-based test service (ARM64 + x86_64 compatible)

## Prerequisites

Before deploying Knative, ensure the following components are installed:
- Kubernetes (kubeadm) cluster
- Gateway API (Envoy Gateway) with `thinkube-gateway`
- CoreDNS properly configured
- Harbor registry deployed and accessible
- ACME certificates deployed with wildcard certificate in default namespace
- `HARBOR_ROBOT_TOKEN` in `~/.env` for registry authentication (`10_deploy.yaml` reads it from there)

## Testing the deployment

```bash
cd ~/thinkube
./scripts/tk_ansible ansible/40_thinkube/optional/knative/18_test.yaml
```

## Configuration

The deployment uses these key variables from inventory:
- `domain_name`: Base domain for the cluster
- `harbor_registry`: Harbor registry URL for container images
- `gateway_name` / `gateway_namespace`: `thinkube-gateway` / `gateway-system`

Knative services use DomainMapping to be accessible at:
- `{name}.{{ domain_name }}` (e.g., `helloworld-python.<domain_name>`)

All traffic routes through the main `thinkube-gateway` in `gateway-system`.

## Testing

The test playbook validates:
- All Knative components are healthy
- DNS resolution works correctly
- Internal connectivity (via ClusterIP)
- External connectivity (via Gateway)
- DomainMapping configuration
- TLS/HTTPS configuration

## Troubleshooting

### Common Issues

1. **Webhook not ready**: The deployment handles webhook readiness checks and will patch the webhook configuration if needed.

2. **Registry authentication fails**: Ensure `HARBOR_ROBOT_TOKEN` is set in `~/.env`:
   ```bash
   source ~/.env
   echo $HARBOR_ROBOT_TOKEN
   ```

3. **DNS resolution issues**: Verify CoreDNS is properly configured and the gateway IP is correct.

4. **Service not accessible externally**: Check DomainMapping status and that the gateway is running.

## Architecture Notes

- Uses net-gateway-api for routing through the main Envoy Gateway
- DomainMapping provides clean URLs: `{name}.{domain}` (no subdomain)
- Configured with mesh compatibility mode disabled for proper DNS resolution
- Supports HTTPS by default with wildcard TLS certificates
- Integrated with Harbor registry for private container images

## Related Documentation

- [Knative Documentation](https://knative.dev/docs/)
- [net-gateway-api Documentation](https://github.com/knative-extensions/net-gateway-api)
- [Thinkube Architecture](../../README.md)
