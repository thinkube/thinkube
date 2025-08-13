# CoreDNS Configuration Component (CORE-003b)

This component configures CoreDNS to properly handle ingress hostnames, Knative service resolution, and domain routing.

## Overview

The CoreDNS configuration:
- Enables hairpin routing for ingress controllers with ZeroTier
- Handles internal Kubernetes service resolution
- Routes Knative service domains to the secondary ingress controller
- Forwards domain queries to ZeroTier DNS server
- Configures worker nodes to use ZeroTier DNS for domain resolution

## Directory Structure

```
coredns/
├── 10_deploy.yaml      # Main deployment playbook
├── 18_test.yaml        # Test playbook
├── 19_rollback.yaml    # Rollback procedures
├── README.md           # This file
└── templates/
    └── Corefile.j2     # CoreDNS configuration template
```

## Requirements

### Required Inventory Variables

- `domain_name`: Base domain (e.g., "thinkube.com")
- `dns1`: DNS server host (ZeroTier IP is used as DNS server)
- `zerotier_subnet_prefix`: ZeroTier network prefix
- `secondary_ingress_ip_octet`: Last octet for secondary ingress IP
- `microk8s_workers`: Group containing worker nodes

### Dependencies

- MicroK8s must be installed and running
- Ingress controllers should be deployed
- ZeroTier DNS should be configured

## Deployment

1. Deploy CoreDNS configuration:
   ```bash
   cd ~/thinkube
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/coredns/10_deploy.yaml
   ```

2. Test the deployment:
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/coredns/18_test.yaml
   ```

## Functionality

### DNS Routing

The configuration implements:
1. **Kubernetes Internal**: Routes `*.cluster.local` to internal kubernetes DNS
2. **Domain Forwarding**: Forwards `*.thinkube.com` to ZeroTier DNS server
3. **Knative Routing**: Maps `*.kn.thinkube.com` to secondary ingress IP
4. **Hairpin Support**: Enables external access to route back to internal services
5. **External Domain Resolution**: Ensures external domains resolve correctly

### Worker Node Configuration

Worker nodes are configured with:
- systemd-resolved configuration for domain forwarding
- ZeroTier DNS server for domain resolution

## Testing

The test playbook verifies:
- CoreDNS pods are running
- Internal Kubernetes service resolution
- Domain forwarding to ZeroTier DNS
- Knative domain resolution (if installed)
- Worker node DNS resolution

## Rollback

To rollback to default configuration:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/coredns/19_rollback.yaml
```

This will:
- Restore default CoreDNS configuration
- Remove custom DNS forwarding rules
- Reset worker node DNS configuration
- Remove system certificates ConfigMap

## Implementation Notes

This is a migration from `thinkube-core/playbooks/core/50_setup_coredns.yaml` with:
- All hardcoded values moved to inventory variables
- Compliance with variable handling policy
- Fully qualified module names
- Preserved original functionality

## References

- Original playbook: `thinkube-core/playbooks/core/50_setup_coredns.yaml`
- Issue: #39 (CORE-003b: Configure CoreDNS)