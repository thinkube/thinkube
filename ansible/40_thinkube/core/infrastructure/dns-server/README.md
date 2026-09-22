# DNS Server Component

This component deploys BIND9 as the network-wide DNS server for Thinkube infrastructure.

## Installation

The DNS server is a core component. The Thinkube installer installs it by
running `10_deploy.yaml` in this folder. It is not installed on its own.

## Architecture

The Thinkube platform uses two separate DNS systems:

1. **CoreDNS** (Kubernetes internal)
   - Handles `*.cluster.local` domains
   - Provides service discovery for pods
   - Runs as the kubeadm `kube-dns` Service in `kube-system`
   - ClusterIP: 10.96.0.10 (service CIDR `10.96.0.0/12`, set in `k8s/10_install_k8s.yaml`)

2. **BIND9** (Network DNS) - THIS COMPONENT
   - Handles `*.<domain_name>` domains
   - Forwards external queries to public DNS
   - Provides DNS for all network clients
   - LoadBalancer IP (Service `bind9-external`): 10.200.0.205 in the example below

## Why Separate DNS Systems?

- **Separation of concerns**: Each DNS server handles what it's designed for
- **Reliability**: Kubernetes DNS issues don't affect network DNS and vice versa
- **Proper recursion**: BIND9 handles recursive queries correctly for external domains

## Deployment

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/dns-server/10_deploy.yaml
```

## Configuration

The addresses depend on `overlay_provider`:

- **ZeroTier**: each address is the overlay subnet prefix plus an octet from
  the inventory. `primary_gateway_ip_octet` (installer default `200`) is the
  gateway. `dns_external_ip_octet` (installer default `205`) is BIND9. With
  prefix `10.200.0.` this gives 10.200.0.200 and 10.200.0.205.
- **Tailscale**: the Tailscale operator assigns both IPs. The playbook reads
  them from the Service status. It also sets Tailscale split DNS so that
  `<domain_name>` queries go to BIND9.

The BIND9 server is configured with (ZeroTier example):

- **Wildcard domains**:
  - `*.<domain_name>` → 10.200.0.200 (primary gateway: the Envoy Gateway)

- **Specific records**:
  - `ns1.<domain_name>` and `dns.<domain_name>` → 10.200.0.205
  - Node hostnames → their ZeroTier IPs (ZeroTier) or LAN IPs (Tailscale)

- **Forwarding**:
  - External queries forwarded to 8.8.8.8, 8.8.4.4
  - Recursion enabled for all clients

Inside the cluster, BIND9 is also reachable as the `bind9-internal` ClusterIP Service.

## Testing

```bash
# Run test playbook
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/dns-server/18_test.yaml

# Manual tests
dig @10.200.0.205 test.<domain_name>
dig @10.200.0.205 google.com
```

## Troubleshooting

### DNS not responding

1. Check if BIND9 pod is running:
   ```bash
   kubectl get pods -n dns-system
   ```

2. Check BIND9 logs:
   ```bash
   kubectl logs -n dns-system deploy/bind9
   ```

3. Verify LoadBalancer IP is assigned:
   ```bash
   kubectl get svc -n dns-system bind9-external
   ```

### Wrong IP resolution

1. Check ConfigMaps:
   ```bash
   kubectl describe cm -n dns-system bind9-zones
   ```

2. Restart BIND9:
   ```bash
   kubectl rollout restart -n dns-system deploy/bind9
   ```

## Rollback

If needed, remove the DNS server:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/dns-server/19_rollback.yaml
```

## Integration with Other Components

After deploying BIND9, the installer updates node DNS configuration:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/coredns/15_configure_node_dns.yaml
```

This configures all nodes to use BIND9 for DNS resolution.