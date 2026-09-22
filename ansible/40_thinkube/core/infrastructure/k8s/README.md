# Kubernetes (kubeadm)

This folder installs the Thinkube Kubernetes cluster with kubeadm: containerd, kubeadm, kubelet and kubectl on every node, Cilium as the network, and OpenEBS Rawfile CSI for storage.

## How it is run

The Thinkube installer runs these playbooks as a core component:

1. `10_install_k8s.yaml` on the control plane.
2. `20_join_workers.yaml`, only when the cluster has worker nodes.
3. `12_configure_resource_policies.yaml`, after the GPU operator step.

If step 1 fails, the installer offers `19_rollback_control.yaml`. If step 2 fails, it offers `29_rollback_workers.yaml`.

thinkube-control also runs `20_join_workers.yaml` when a node is added to a running cluster.

The GPU operator is a separate component. See [`../gpu_operator/`](../gpu_operator/README.md). This folder does not install it.

## Playbooks

| Playbook | What it does |
|----------|--------------|
| `10_install_k8s.yaml` | Control plane. Checks the host, sets up the `k8s0` interface and UFW, installs containerd and kubeadm, runs `kubeadm init`, installs kubectl and helm for the user, then Cilium and OpenEBS Rawfile CSI. |
| `12_configure_resource_policies.yaml` | Creates four PriorityClasses: `thinkube-critical` (1000000), `thinkube-platform` (100000), `thinkube-workload` (10000, the cluster default) and `thinkube-batch` (1000). |
| `13_test_resource_policies.yaml` | Checks the four PriorityClasses and that `thinkube-workload` is the default. Checks LimitRanges and ResourceQuotas in the gateway, PostgreSQL, Harbor and Argo CD namespaces, so it passes only after those components are installed. Creates a test pod to confirm a LimitRange applies its default memory limit. |
| `16_test_kubelet_protection.yaml` | Reads kubelet arguments from `/var/snap/k8s/common/args/kubelet`. This install does not create that file, so the playbook fails. |
| `18_test_control.yaml` | Checks the control plane with `snap list k8s`, `k8s status` and a UFW rule for port 6400. This install uses none of these, so the playbook fails. |
| `19_rollback_control.yaml` | Removes the cluster from the control plane. See [Rollback](#rollback). |
| `20_join_workers.yaml` | Workers. Sets up UFW, the `k8s0` interface and a local API proxy, the node-ip sync and the link watchdog, installs containerd and kubeadm, and runs `kubeadm join`. Then pins CoreDNS to the control plane and adds the workers to the SSH config used by code-server. |
| `28_test_worker.yaml` | Checks each worker: kubelet active, kubeadm installed, `k8s0` carries `172.16.0.1`, the API answers through the local proxy, `kubelet.conf` points at `https://172.16.0.1:6443`, node Ready, node InternalIP equals `lan_ip`, Cilium running, UFW forward policy ACCEPT. Then runs a test pod on each worker and calls the in-cluster API from it. |
| `29_rollback_workers.yaml` | Drains and deletes the workers, then wipes them. See [Rollback](#rollback). |

## What the install sets up

Versions are pinned in the playbooks and in the role defaults:

| Part | Version | Where |
|------|---------|-------|
| Kubernetes (kubeadm, kubelet, kubectl) | `1.36.4-1.1`, held with `apt-mark hold` | role `kubeadm_install`, from `pkgs.k8s.io` |
| containerd.io | `2.2.4-1`, held with `apt-mark hold` | role `containerd_install`, from `download.docker.com` |
| Cilium chart | `1.20.1` | `10_install_k8s.yaml` |
| OpenEBS Rawfile CSI chart | `0.13.1` | `10_install_k8s.yaml` |
| helm | `v3.16.4` | `10_install_k8s.yaml`, `20_join_workers.yaml` |

The role READMEs explain why the versions are pinned and held:

- `../../../../roles/kubeadm_install/README.md`
- `../../../../roles/containerd_install/README.md`

### Stable API address

- Every node has a dummy interface `k8s0` with the address `172.16.0.1/32`.
- The API server endpoint, its certificate and Cilium all use `https://172.16.0.1:6443`. So the cluster does not depend on the LAN address of any node.
- On workers, a systemd socket proxy (`k8s-api-proxy.socket` and `k8s-api-proxy.service`) listens on `172.16.0.1:6443` and forwards to the control plane's `lan_ip`.
- kubelet's `--node-ip` is the node's real LAN address (`lan_ip`). Cilium traffic between nodes and API server calls to kubelet use this address.

### Network changes

- `thinkube-node-ip-sync` runs at boot, before kubelet, and every minute after that through a timer.
- If the node's LAN address changed, it writes the new address into `/var/lib/kubelet/kubeadm-flags.env` and restarts kubelet.
- On workers it also looks up the control plane by host name (LLMNR) and points the API proxy at the new address.
- When no Cilium agent is running and `/var/run/cilium/deleteQueue` holds 200 or more entries, it empties that directory.
- The playbooks turn on LLMNR in systemd-resolved (`/etc/systemd/resolved.conf.d/10-thinkube-llmnr.conf`) on every node.

### Link watchdog (workers only)

- `thinkube-link-watchdog` checks every minute that the default route exists and the gateway answers.
- After 3 failed checks in a row it restarts the interface. After 6 it re-probes the PCI device. After 12 it reboots the worker, but not in the first 600 seconds after boot.
- It only checks the local link. It does not react when the control plane is down.
- The four limits can be changed in the inventory with `link_watchdog_reset_after_override`, `link_watchdog_rebind_after_override`, `link_watchdog_reboot_after_override` and `link_watchdog_boot_grace_seconds_override`.

### Cluster settings

- `kubeadm init` skips kube-proxy. Cilium runs with `kubeProxyReplacement: true`.
- Pod network `10.244.0.0/16`, service network `10.96.0.0/12`. Cilium gives each node a `/23`.
- kubelet: `maxPods: 500`, `systemReserved` 4Gi memory and 500m CPU, `kubeReserved` 2Gi memory and 500m CPU, hard eviction at 2Gi free memory, soft eviction at 4Gi free memory. Control plane and workers use the same values.
- The control-plane `NoSchedule` taint is removed. Platform workloads run on the control plane.
- Cilium attaches only to `k8s0 en+ eth+ wl+ bond+`. The ZeroTier interfaces are left out.
- ZeroTier mode only: Cilium L2 announcements hand out LoadBalancer addresses from `overlay_subnet_prefix` + `lb_ip_start_octet` to `lb_ip_end_octet`. In Tailscale mode this is off.
- Storage classes: `csi-rawfile-default` and `k8s-hostpath`. `k8s-hostpath` uses the same provisioner (`rawfile.csi.openebs.io`) and is marked as the default class.
- After workers join, CoreDNS is pinned to the control plane.

### User tools

- kubectl (from `dl.k8s.io`) and helm in `~/.local/bin`. No sudo is needed.
- kubeconfig in `~/.kube/config` on the control plane only. Workers get kubectl and helm but no kubeconfig.
- If `~/.thinkube_shared_shell` exists, kubectl and helm aliases are written to `aliases/k8s_aliases.sh` and `aliases/k8s_aliases.fish`.

## Prerequisites

`10_install_k8s.yaml` stops if one of these checks fails on the control plane:

- Ubuntu 24.04.
- At least 16 CPU cores.
- At least 60 GB of RAM as reported by the kernel. This is the check for a 64 GB machine.
- Inventory variables `system_username`, `domain_name`, `cluster_name`, `overlay_provider`. In ZeroTier mode also `overlay_subnet_prefix`, `lb_ip_start_octet`, `lb_ip_end_octet`.

`20_join_workers.yaml` checks only the inventory variables `system_username` and `overlay_provider`, plus `overlay_subnet_prefix` in ZeroTier mode.

The playbook headers also state a 1 TB disk minimum. No playbook checks the disk size.

### System settings made by the roles

The `kubeadm_install` role, on every node:

- Turns swap off and comments out swap lines in `/etc/fstab`.
- Loads the kernel modules `overlay` and `br_netfilter`, and lists them in `/etc/modules-load.d/thinkube-k8s.conf`.
- Writes `/etc/sysctl.d/99-thinkube-k8s.conf` with:
  - `net.ipv4.ip_forward = 1`
  - `net.bridge.bridge-nf-call-iptables = 1`
  - `net.bridge.bridge-nf-call-ip6tables = 1`
  - `fs.inotify.max_user_instances = 1024`
  - `fs.inotify.max_user_watches = 524288`

The `containerd_install` role writes `/etc/containerd/config.toml` with `SystemdCgroup = true`. It also imports `/etc/containerd/conf.d/*.toml`, so the GPU operator can add its NVIDIA runtime there.

### UFW

Both playbooks install UFW, set `DEFAULT_FORWARD_POLICY="ACCEPT"` in `/etc/default/ufw`, add the rules below and enable UFW. The playbooks mark the ACCEPT forward policy as required for Kubernetes networking, and both test playbooks check it.

| Port or interface | Control plane | Worker | Purpose |
|-------------------|:-:|:-:|---------|
| 22/tcp | yes | yes | SSH |
| 6443/tcp | yes | yes | API server (worker: the local API proxy) |
| 2379-2380/tcp | yes | | etcd |
| 10250/tcp | yes | yes | kubelet |
| 10257/tcp | yes | | controller-manager |
| 10259/tcp | yes | | scheduler |
| 4240/tcp | yes | yes | Cilium health |
| 8472/udp | yes | yes | Cilium VXLAN |
| 9962/tcp | yes | yes | Cilium agent metrics |
| 5355/udp | yes | yes | LLMNR |
| `cilium_host` in and out | yes | yes | Cilium |
| `k8s0` in and out | yes | | API server on the dummy interface |
| `zt+` in and out | ZeroTier only | ZeroTier only | ZeroTier overlay |
| 22/tcp from `overlay_subnet_prefix`.0/24 | ZeroTier only | ZeroTier only | SSH over ZeroTier |

The playbooks add no rules for Tailscale.

## Rollback

Both rollback playbooks delete data. The installer or the person who runs them is responsible for confirmation. The playbooks do not ask.

### `19_rollback_control.yaml`

It removes:

- The cluster. It stops kubelet, removes the static pod manifests, stops all containers, restarts containerd, then runs `kubeadm reset`.
- The packages `kubeadm`, `kubelet`, `kubectl` and `containerd.io`. They are unheld and purged.
- `/etc/kubernetes`, `/etc/cni/net.d`, `/etc/containerd`, `/var/lib/kubelet`, `/var/lib/containerd`, `/var/lib/etcd`, `/var/openebs`, `/var/lib/rawfile-localpv`, `/var/csi`. All volume data on `csi-rawfile-default` and `k8s-hostpath` is lost.
- `~/.kube`, `~/.local/bin/kubectl`, `~/.local/bin/helm` and the k8s alias files.
- `/etc/modules-load.d/thinkube-k8s.conf` and `/etc/sysctl.d/99-thinkube-k8s.conf`.
- The Kubernetes and Docker apt sources and keys.
- Network interfaces whose names contain `cilium` or `lxc`.
- The UFW rules for 6443, 2379-2380, 10257, 10259, 10250, 4240 and 8472/udp. Then it disables UFW.
- `/etc/systemd/resolved.conf.d/10-thinkube.conf`.
- In Tailscale mode, when `tailscale_api_token` is set: the Tailscale split DNS entry for `domain_name`.
- Last, it flushes all iptables and ip6tables rules and sets the default policies to ACCEPT.

It leaves in place:

- The `k8s0` interface configuration in `/etc/systemd/network/`.
- The node-ip sync script, its units and its timer.
- The LLMNR drop-in `10-thinkube-llmnr.conf`.
- The UFW rules for 22, 9962, 5355, `cilium_host`, `k8s0` and ZeroTier. UFW itself is disabled.
- `DEFAULT_FORWARD_POLICY="ACCEPT"` in `/etc/default/ufw`.
- Swap stays off. The `/etc/fstab` lines stay commented out.

### `29_rollback_workers.yaml`

On the control plane, it drains each worker (timeout 300 s, `--force`) and deletes the node.

On each worker, it removes:

- The cluster state, with `kubeadm reset`.
- The packages `kubeadm`, `kubelet`, `kubectl` and `containerd.io`. They are unheld and purged.
- `/etc/kubernetes`, `/etc/cni/net.d`, `/etc/containerd`, `/var/lib/kubelet`, `/var/lib/containerd`, `/var/openebs`, `/var/lib/rawfile-localpv`.
- `~/.local/bin/kubectl` and `~/.local/bin/helm`.
- The API proxy, node-ip sync and link watchdog units and scripts.
- The `k8s0` configuration and the `k8s0` interface.
- The kernel module and sysctl files, and the Kubernetes and Docker apt sources and keys.
- Network interfaces whose names contain `cilium` or `lxc`.

It leaves in place:

- All UFW rules. UFW stays enabled.
- The iptables rules. They are not flushed.
- The LLMNR drop-in, and the `iw` package if it was installed.
- The worker entries in the code-server SSH config.
- Swap stays off.

It does not reboot the worker.

## Running a playbook by hand (maintainers)

Run from `core/thinkube`:

- In code-server: `./scripts/tk_ansible <playbook>`. It uses the inventory in `/home/thinkube/.ansible/inventory`.
- On a machine with the repository inventory: `./scripts/run_ansible.sh <playbook>`. It uses `inventory/inventory.yaml`.

`<playbook>` is the path from `core/thinkube`, for example `ansible/40_thinkube/core/infrastructure/k8s/28_test_worker.yaml`.

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for known problems.
