# Knative Deployment

This directory contains playbooks for deploying Knative on the Thinkube platform.

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
- Kubernetes (k8s-snap) cluster
- Gateway API (Envoy Gateway) with `thinkube-gateway`
- CoreDNS properly configured
- Harbor registry deployed and accessible
- ACME certificates deployed with wildcard certificate in default namespace
- Environment variable `HARBOR_ROBOT_TOKEN` set for registry authentication

## Deployment Instructions

1. **Deploy Knative**:
   ```bash
   cd ~/thinkube
   ./scripts/tk_ansible ansible/40_thinkube/optional/knative/10_deploy.yaml
   ```

2. **Test the deployment**:
   ```bash
   ./scripts/tk_ansible ansible/40_thinkube/optional/knative/18_test.yaml
   ```

3. **Rollback if needed**:
   ```bash
   ./scripts/tk_ansible ansible/40_thinkube/optional/knative/19_rollback.yaml
   ```

## Configuration

The deployment uses these key variables from inventory:
- `domain_name`: Base domain for the cluster
- `harbor_registry`: Harbor registry URL for container images

Knative services use DomainMapping to be accessible at:
- `{name}.{{ domain_name }}` (e.g., `helloworld-python.thinkube.com`)

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

2. **Registry authentication fails**: Ensure `HARBOR_ROBOT_TOKEN` environment variable is set:
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
