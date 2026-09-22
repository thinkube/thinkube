# CoreDNS Configuration Component (CORE-003b)

This component configures CoreDNS for cluster DNS and domain routing.

## Installation

CoreDNS configuration is a core component. The Thinkube installer runs
`10_deploy.yaml` and then `15_configure_node_dns.yaml` in this folder,
after the DNS server (`../dns-server`). It is not installed on its own.

## Overview

The CoreDNS configuration for the kubeadm cluster:
- Handles internal Kubernetes service resolution (`cluster.local`)
- Forwards every other query to BIND9 (the `bind9-external` Service IP)
- Pins CoreDNS to the control plane node
- Configures worker nodes' systemd-resolved to send `~<domain_name>` queries to BIND9
- Deploys the `dns-probe` DaemonSet (see below)

## Directory Structure

```
coredns/
├── 10_deploy.yaml               # Main deployment playbook
├── 15_configure_node_dns.yaml   # Points every node's resolver at BIND9
├── 18_test.yaml                 # Test playbook
├── 19_rollback.yaml             # Rollback procedures
├── README.md                    # This file
└── templates/
    ├── Corefile.j2              # CoreDNS configuration template
    └── dns-probe.yaml.j2        # DNS probe DaemonSet
```

## Requirements

### Required Inventory Variables

- `domain_name`: Base domain
- `network_mode`, `overlay_provider`: network settings written by the installer
- `k8s_workers`: Group containing worker nodes
- ZeroTier mode only: `overlay_subnet_prefix`, `primary_gateway_ip_octet`, `dns_external_ip_octet`

### Dependencies

- Kubernetes (kubeadm) must be installed and running
- The BIND9 DNS server (`../dns-server/10_deploy.yaml`) must be deployed, and
  `bind9-external` must have a LoadBalancer IP

## Deployment

1. Deploy CoreDNS configuration:
   ```bash
   cd ~/thinkube
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/coredns/10_deploy.yaml
   ```

2. Configure node DNS:
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/coredns/15_configure_node_dns.yaml
   ```

3. Test the deployment:
   ```bash
   ./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/coredns/18_test.yaml
   ```

## Functionality

### DNS Routing

The configuration implements:
1. **Kubernetes Internal**: Routes `*.cluster.local` to internal kubernetes DNS
2. **Forwarding**: Forwards all other names, `*.<domain_name>` and external domains, to BIND9

### Worker Node Configuration

Worker nodes are configured with:
- systemd-resolved configuration (`/etc/systemd/resolved.conf.d/coredns-external.conf`) that sends `~<domain_name>` to the BIND9 address

## Testing

The test playbook verifies:
- CoreDNS pods are running
- Internal Kubernetes service resolution
- The `dns-probe` DaemonSet runs on every node
- Platform domain forwarding through kube-dns to BIND9
- Platform service names resolve to the wildcard address
- Platform domain resolution on every node

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

## DNS probe

The deploy runs a DaemonSet `dns-probe` in kube-system: one pod per node
resolves names from the pod network every five seconds over five checks and
logs one line per failure, with the time, node, path, server and the
resolver's own message.

| Path | Server | Name |
|---|---|---|
| `resolver` | the pod's resolv.conf, search list included | the registry's name |
| `kube-dns` | kube-dns ClusterIP | `kubernetes.default.svc.cluster.local` and the registry's name |
| `bind9-internal` | bind9-internal ClusterIP | the registry's name |
| `bind9-external` | the address CoreDNS forwards to | the registry's name |

Each pod logs a start line with its addresses and a summary line every hour,
so a quiet log means nothing failed.

```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=dns-probe --prefix --tail=-1 | grep result=fail
```

CoreDNS itself logs failed answers only (`log . { class error }`), so its log
covers days rather than minutes. When the Prometheus component is installed,
it adds a per-node blackbox DNS probe with the same paths as a time series.
