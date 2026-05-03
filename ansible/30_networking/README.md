# Overlay Networks (ZeroTier / Tailscale)

Playbooks that install and configure the cluster's overlay network on each
host before Kubernetes is brought up. The overlay choice is driven by the
inventory variable `overlay_provider` (`zerotier` or `tailscale`),
collected from the user by the installer.

> **Note on naming:** despite this directory's history (it was originally
> ZeroTier-and-DNS-only), DNS is no longer here — BIND9 and CoreDNS are in
> `../40_thinkube/core/infrastructure/dns-server/` and `coredns/` because
> they need a working Kubernetes cluster.

## Playbook Overview

### `05_install_zerotier.yaml`
- **When:** `overlay_provider == 'zerotier'`
- Installs the ZeroTier package on every node in `overlay_nodes`, joins
  them to the configured ZeroTier network, and authorises each node via
  the ZeroTier Central API.

### `06_install_tailscale.yaml`
- **When:** `overlay_provider == 'tailscale'`
- Installs the Tailscale package on every node in `overlay_nodes` and
  brings each one up against the configured tailnet using the
  `tailscale_auth_key` from inventory.

### `10_setup_zerotier.yaml`
- **When:** `overlay_provider == 'zerotier'`
- Configures routing and firewall rules for the ZeroTier overlay on
  every node. Adds the Cilium load balancer IP range
  (`lb_ip_start_octet` … `lb_ip_end_octet`) as additional IPs on the
  control plane node so Cilium L2 mode can announce them. Processes one
  node at a time (`serial: 1`).

### `11_setup_tailscale.yaml`
- **When:** `overlay_provider == 'tailscale'`
- Verifies that every node in `overlay_nodes` is in
  `BackendState=Running` on the tailnet and fails fast otherwise.
  Mostly a sanity check between `06_install_tailscale.yaml` and the k8s
  install — the previous subnet-route workaround was removed in favour
  of the Tailscale Kubernetes Operator (see below).

### `18_test_zerotier.yaml`
- Tests ZeroTier connectivity between nodes and reports diagnostics.

### `19_reset_zerotier.yaml`
- Leaves the ZeroTier network on the selected nodes and optionally
  uninstalls the package. Used when a deployment failed and you need a
  clean slate; preserves the ZeroTier network for any other members.

### `25_configure_remote_controller.yaml`
- Configures the installer host (the "controller", run on a machine
  separate from the cluster) to reach the cluster over the overlay.
  Both providers supported.

## Order of Execution

The installer's deploy queue (`deploy.tsx`) drives the order. Roughly:

```
... env / SSH setup ...
05_install_zerotier.yaml      OR   06_install_tailscale.yaml
10_setup_zerotier.yaml        OR   11_setup_tailscale.yaml
... k8s install ...
40_thinkube/core/infrastructure/k8s/10_install_k8s.yaml
40_thinkube/core/infrastructure/tailscale-operator/10_deploy.yaml  (Tailscale only)
40_thinkube/core/infrastructure/acme-certificates/10_deploy.yaml
40_thinkube/core/infrastructure/gateway-api/10_deploy.yaml
40_thinkube/core/infrastructure/dns-server/10_deploy.yaml
40_thinkube/core/infrastructure/coredns/10_deploy.yaml
40_thinkube/core/infrastructure/coredns/15_configure_node_dns.yaml
... services ...
```

`gateway-api` runs before `dns-server` because in Tailscale mode the
dns-server playbook reads the operator-assigned tailnet IP from the
Envoy Gateway Service status.

## Provider-Specific Notes

### ZeroTier mode
- Cilium's k8s-snap built-in load balancer (L2 mode) claims static IPs
  from the user-defined overlay subnet. The control plane advertises
  the load-balancer IP range so the rest of the network can route to it.
- Inventory carries `overlay_cidr`, `overlay_subnet_prefix`,
  `lb_ip_start_octet` / `lb_ip_end_octet`,
  `primary_gateway_ip_octet`, `dns_external_ip_octet`, per-host
  `overlay_ip`.

### Tailscale mode
- Cilium L2 LB is **disabled** at install time (it can't traverse
  Tailscale's L3 mesh).
- The Tailscale Kubernetes Operator
  (`../40_thinkube/core/infrastructure/tailscale-operator/`) is
  installed inside the cluster. Services that need a public-ish IP get
  `tailscale.com/expose: "true"` + `tailscale.com/hostname` annotations
  and the operator provisions a tailnet device for each. The Envoy
  Gateway Service and `bind9-external` are exposed this way; their IPs
  are discovered at deploy time from
  `Service.status.loadBalancer.ingress`.
- Inventory carries `tailscale_auth_key`, `tailscale_api_token`,
  `tailscale_oauth_client_id`, `tailscale_oauth_client_secret`, and an
  optional `gateway_hostname` (defaults to `<cluster_name>-gw`).

The full design + status is tracked in
`thinkube-installer/TAILSCALE_OPERATOR_MIGRATION.md`.

## Environment Variables

The installer writes credentials into `~/.env` for you. If you're
running these playbooks by hand, set the relevant ones for your
provider:

ZeroTier:
```bash
export ZEROTIER_NETWORK_ID=...
export ZEROTIER_API_TOKEN=...
```

Tailscale:
```bash
export TAILSCALE_AUTH_KEY=tskey-auth-...
export TAILSCALE_API_TOKEN=tskey-api-...
export TAILSCALE_OAUTH_CLIENT_ID=...
export TAILSCALE_OAUTH_CLIENT_SECRET=tskey-client-...
```

## Known Issues

### ZeroTier
- ICMP between members may be blocked depending on UFW config; allow
  UDP 9993 if peers can't see each other.
- `zerotier-cli listnetworks` should show `OK` for every assigned IP.

### Tailscale
- The OAuth client *cannot* be created via the Tailscale API — that's
  the one manual step in the configuration flow. The installer
  surfaces a guided walkthrough.
- If the operator never assigns the Gateway IP, check
  `kubectl logs -n tailscale deployment/operator` and verify the OAuth
  client has `Devices/Core` (R+W) and `Keys/Auth Keys` (R+W) scopes
  with the `tag:k8s-operator` tag.
