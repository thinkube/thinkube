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
   - ClusterIP: 10.96.0.10 in both overlay modes. kubeadm gives kube-dns the
     10th address of the service CIDR `10.96.0.0/12` (`service_cidr` in
     `k8s/10_install_k8s.yaml`)

2. **BIND9** (Network DNS) - THIS COMPONENT
   - Handles `*.<domain_name>` domains
   - Forwards external queries to public DNS
   - Provides DNS for all network clients
   - LoadBalancer IP (Service `bind9-external`): depends on `overlay_provider`,
     see [Configuration](#configuration)

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

`10_deploy.yaml` chooses two addresses: the BIND9 address (Service
`bind9-external`, playbook fact `bind9_advertised_ip`) and the gateway address
(the Envoy Gateway Service, playbook fact `effective_gateway_ip`). How it
chooses them depends on `overlay_provider` in the inventory.

| | ZeroTier | Tailscale |
|---|---|---|
| Who assigns the IPs | Cilium L2 load balancer, at the fixed IP the playbook asks for | Tailscale operator (`loadBalancerClass: tailscale`), a tailnet IP (`100.x.y.z`) that it picks |
| BIND9 IP | `overlay_subnet_prefix` + `dns_external_ip_octet` | read from `bind9-external` `status.loadBalancer.ingress` |
| Gateway IP | `overlay_subnet_prefix` + `primary_gateway_ip_octet` | read from the Envoy Gateway Service `status.loadBalancer.ingress` |
| BIND9 tailnet name | none | `<cluster_name>-dns` (annotation `tailscale.com/hostname`) |
| Gateway tailnet name | none | `gateway_hostname` (written by the installer, used by `gateway-api/10_deploy.yaml`) |
| Node A records | each node's `overlay_ip` | each node's `lan_ip` |
| Split DNS | none | Tailscale split DNS sends `<domain_name>` queries to the BIND9 IP (needs `tailscale_api_token`) |

ZeroTier values come from the installer (`inventoryGenerator.js`, ZeroTier
mode only). `overlay_subnet_prefix` is the first three octets of the overlay
CIDR. `primary_gateway_ip_octet` defaults to `200` and
`dns_external_ip_octet` to `205`. With overlay CIDR `10.200.0.0/24` this gives
gateway 10.200.0.200 and BIND9 10.200.0.205. The installer does not write
these variables in Tailscale mode, so no address in the overlay subnet is
used there.

In Tailscale mode the IPs are known only after the operator assigns them. To
see them:

```bash
kubectl get svc -n dns-system bind9-external
kubectl get svc -n envoy-gateway-system \
  -l gateway.envoyproxy.io/owning-gateway-name=thinkube-gateway
```

The BIND9 zone for `<domain_name>` holds:

- **Wildcard domains**:
  - `*.<domain_name>` → the gateway IP (the Envoy Gateway)

- **Specific records**:
  - `ns1.<domain_name>` and `dns.<domain_name>` → the BIND9 IP
  - Node hostnames → their ZeroTier IPs (ZeroTier) or LAN IPs (Tailscale)

- **Forwarding**:
  - External queries forwarded to 8.8.8.8, 8.8.4.4
  - Recursion enabled for all clients

Inside the cluster, BIND9 is also reachable as the `bind9-internal` ClusterIP Service.

## Testing

```bash
# Run test playbook
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/dns-server/18_test.yaml

# Manual tests (<bind9-ip> is the BIND9 IP from the table above)
dig @<bind9-ip> test.<domain_name>
dig @<bind9-ip> google.com
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