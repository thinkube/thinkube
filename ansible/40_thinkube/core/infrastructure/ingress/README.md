# Ingress Controllers

This component deploys dual Ingress Controllers for the Thinkube infrastructure to handle incoming traffic routing.

## Overview

The deployment includes:
- **Primary Ingress Controller**: For general services
- **Secondary Ingress Controller**: For specialized workloads (like Knative)

Both controllers use NGINX Ingress Controller deployed via Helm with MetalLB for LoadBalancer services.

## Architecture

```
                    Internet
                        |
                   DNS Resolution
                    /         \
           Primary IP      Secondary IP
                |               |
        Primary Ingress    Secondary Ingress
        (nginx class)     (nginx-kn class)
                |               |
        General Services   Knative Services
```

## Prerequisites

1. MicroK8s cluster deployed and running
2. Control plane and worker nodes joined  
3. CoreDNS configured for proper DNS resolution
4. Cert-manager installed (required for TLS certificate creation)
5. MetalLB addon available
6. Network connectivity between nodes

## Playbooks

### 10_deploy.yaml
Deploys both ingress controllers with the following configuration:
- Disables MicroK8s built-in ingress addon
- Enables MetalLB with configured IP range
- Deploys primary ingress controller in `ingress` namespace
- Deploys secondary ingress controller in `ingress-kn` namespace
- Configures IngressClass resources

### 18_test.yaml
Tests the deployment by verifying:
- MetalLB is enabled
- Namespaces exist
- Pods are running
- Services have correct external IPs
- IngressClass resources are configured
- Health endpoints are responding

### 19_rollback.yaml
Removes the deployed ingress controllers:
- Uninstalls Helm releases
- Deletes IngressClass resources
- Removes namespaces
- Optionally re-enables built-in ingress

## Configuration

Key variables from inventory:
```yaml
# IP Configuration
metallb_ip_range: "10.0.191.100-10.0.191.110"
primary_ingress_ip: "10.0.191.100"
secondary_ingress_ip: "10.0.191.102"

# Namespace Configuration
ingress_namespace: "ingress"
ingress_kn_namespace: "ingress-kn"

# IngressClass Configuration
primary_ingress_class: "nginx"      # Set as default
secondary_ingress_class: "nginx-kn"
```

## Usage

### Deploy Ingress Controllers
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/ingress/10_deploy.yaml
```

### Test Deployment
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/ingress/18_test.yaml
```

### Rollback (if needed)
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/ingress/19_rollback.yaml
```

## DNS Configuration

After deployment, configure DNS to point to the external IPs:
- Primary services: `*.k8s.domain.com` → `10.0.191.100`
- Knative services: `*.kn.domain.com` → `10.0.191.102`

## Integration with Cert-Manager

The ingress controllers are configured to work with cert-manager:
- TLS certificates can be automatically managed
- Use appropriate annotations in Ingress resources
- ClusterIssuer will handle certificate requests

## Troubleshooting

### Check Pod Status
```bash
microk8s kubectl get pods -n ingress
microk8s kubectl get pods -n ingress-kn
```

### View Service External IPs
```bash
microk8s kubectl get svc -n ingress
microk8s kubectl get svc -n ingress-kn
```

### Check IngressClass Configuration
```bash
microk8s kubectl get ingressclass
```

### View Controller Logs
```bash
# Primary controller
microk8s kubectl logs -n ingress -l app.kubernetes.io/name=ingress-nginx

# Secondary controller
microk8s kubectl logs -n ingress-kn -l app.kubernetes.io/name=ingress-nginx
```

### Verify MetalLB Configuration
```bash
microk8s kubectl get configmap -n metallb-system config -o yaml
```

## Next Steps

After successful deployment:
1. Deploy cert-manager for TLS certificate management
2. Configure DNS records for your domain
3. Deploy services with appropriate IngressClass annotations
4. Monitor ingress controller metrics

## Migration Notes

This component migrates from `thinkube-core/playbooks/core/40_setup_ingress.yaml` with:
- Updated to use MicroK8s kubectl and helm binaries
- Removed hardcoded IPs and domains
- Simplified configuration using inventory variables
- Removed cert validation dependencies (handled by cert-manager)
- Updated to use current ingress-nginx Helm chart