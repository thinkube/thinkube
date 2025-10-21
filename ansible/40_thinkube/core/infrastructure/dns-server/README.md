# DNS Server Component

This component deploys BIND9 as the network-wide DNS server for Thinkube infrastructure.

## Architecture

The Thinkube platform uses two separate DNS systems:

1. **CoreDNS** (Kubernetes internal)
   - Handles `*.cluster.local` domains
   - Provides service discovery for pods
   - Runs as part of MicroK8s DNS addon
   - ClusterIP: 10.152.183.10

2. **BIND9** (Network DNS) - THIS COMPONENT
   - Handles `*.thinkube.com` domains
   - Forwards external queries to public DNS
   - Provides DNS for all network clients
   - LoadBalancer IP: 10.200.0.205

## Why Separate DNS Systems?

- **Separation of concerns**: Each DNS server handles what it's designed for
- **Reliability**: Kubernetes DNS issues don't affect network DNS and vice versa
- **Proper recursion**: BIND9 handles recursive queries correctly for external domains
- **Proven pattern**: This architecture worked successfully in the pre-LXD setup

## Deployment

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/dns-server/10_deploy.yaml
```

## Configuration

The BIND9 server is configured with:

- **Wildcard domains**:
  - `*.thinkube.com` → 10.200.0.200 (primary ingress)
  - `*.kn.thinkube.com` → 10.200.0.201 (secondary ingress)

- **Specific records**:
  - `dns.thinkube.com` → 10.200.0.205
  - Node hostnames → Their ZeroTier IPs

- **Forwarding**:
  - External queries forwarded to 8.8.8.8, 8.8.4.4
  - Recursion enabled for all clients

## Testing

```bash
# Run test playbook
./scripts/run_ansible.sh ansible/40_thinkube/core/dns-server/18_test.yaml

# Manual tests
dig @10.200.0.205 test.thinkube.com
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
./scripts/run_ansible.sh ansible/40_thinkube/core/dns-server/19_rollback.yaml
```

## Integration with Other Components

After deploying BIND9, update node DNS configuration:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/coredns/15_configure_node_dns.yaml
```

This configures all nodes to use BIND9 for DNS resolution.