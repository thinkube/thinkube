# Knative Deployment

This directory contains playbooks for deploying Knative on the Thinkube platform.

## Overview

Knative provides serverless capabilities for Kubernetes, including:
- **Knative Serving**: Deploy and manage serverless workloads
- **Knative Eventing**: Event-driven architecture support
- **Kourier**: Lightweight ingress for Knative services

## Components Deployed

- Knative Serving v1.17.0
- Knative Eventing v1.17.1
- Kourier v1.17.0 (ingress controller)
- Sample helloworld-go service for validation

## Prerequisites

Before deploying Knative, ensure the following components are installed:
- MicroK8s cluster (CORE-001)
- Ingress controllers with secondary ingress configured (CORE-002)
- CoreDNS properly configured (CORE-003)
- Harbor registry deployed and accessible (CORE-004)
- Cert-manager deployed with wildcard certificate in default namespace (CORE-005)
- Environment variable `HARBOR_ROBOT_TOKEN` set for registry authentication

## Deployment Instructions

1. **Deploy Knative**:
   ```bash
   cd ~/thinkube
   ./scripts/run_ansible.sh ansible/40_thinkube/optional/knative/10_deploy.yaml
   ```

2. **Test the deployment**:
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/optional/knative/18_test.yaml
   ```

3. **Rollback if needed**:
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/optional/knative/19_rollback.yaml
   ```

## Configuration

The deployment uses these key variables from inventory:
- `domain_name`: Base domain for the cluster
- `harbor_registry`: Harbor registry URL for container images
- `secondary_ingress_ip_octet`: IP octet for Knative ingress

The deployment automatically copies the wildcard TLS certificate from the default namespace (created by cert-manager) to the required namespaces.

Knative services will be accessible at:
- `*.kn.{{ domain_name }}` (e.g., `helloworld-go.kn.thinkube.com`)

## Testing

The test playbook validates:
- All Knative components are healthy
- DNS resolution works correctly
- Internal connectivity (via ClusterIP)
- External connectivity (via Ingress)
- Autoscaling functionality
- TLS/HTTPS configuration

## Troubleshooting

### Common Issues

1. **Webhook not ready**: The deployment handles webhook readiness checks and will patch the webhook configuration if needed.

2. **Registry authentication fails**: Ensure `HARBOR_ROBOT_TOKEN` environment variable is set:
   ```bash
   source ~/.env
   echo $HARBOR_ROBOT_TOKEN
   ```

3. **DNS resolution issues**: Verify CoreDNS is properly configured and the secondary ingress IP is correct.

4. **Service not accessible externally**: Check that the secondary ingress controller is running and the wildcard certificate is properly configured.

## Architecture Notes

- Uses Kourier as the Knative ingress controller
- Configured with mesh compatibility mode disabled for proper DNS resolution
- Supports HTTPS by default with wildcard TLS certificates
- Integrated with Harbor registry for private container images
- Sample service configured with min-scale=1 to prevent cold starts

## Related Documentation

- [Knative Documentation](https://knative.dev/docs/)
- [Kourier Documentation](https://github.com/knative/net-kourier)
- [Thinkube Architecture](../../README.md)