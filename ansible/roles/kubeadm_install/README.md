# kubeadm_install

Installs `kubeadm`, `kubelet`, `kubectl` from the upstream `pkgs.k8s.io`
apt repository at a pinned version, applies kubeadm's preflight
requirements, and holds the packages.

## What it provides

- `kubeadm`, `kubelet`, `kubectl` from
  `pkgs.k8s.io/core:/stable:/v<MINOR>/deb/` at the pinned patch (default
  `1.35.5-1.1`)
- `apt-mark hold` on all three
- Swap disabled (runtime + `/etc/fstab` comment)
- Kernel modules `overlay` and `br_netfilter` loaded + persisted via
  `/etc/modules-load.d/thinkube-k8s.conf`
- Networking sysctls (`net.bridge.bridge-nf-call-iptables=1`,
  `net.bridge.bridge-nf-call-ip6tables=1`, `net.ipv4.ip_forward=1`)
  persisted via `/etc/sysctl.d/99-thinkube-k8s.conf`
- `kubelet` systemd unit enabled

## What it does NOT provide

- `kubeadm init` / `kubeadm join` — handled by the orchestrating
  playbooks (`infrastructure/k8s/10_install_k8s.yaml` for control
  plane, `20_join_workers.yaml` for workers)
- containerd — handled by the `containerd_install` role
- Cilium / CoreDNS / GPU operator — separate playbooks

## Why each step

Standard upstream kubeadm requirements. Documented in
<https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/>
and the kubeadm preflight checks themselves. After install, kubelet
enters a crashloop until kubeadm configures it; this is the
upstream-documented behaviour, not a bug.

The apt-pinned versions + `apt-mark hold` exist to neutralise the same
class of failure that canonical/k8s-snap#2529 demonstrated under snap
auto-refresh: version bumps must be explicit and intentional.

## Variables

See `defaults/main.yaml`. The defaults pin to the
`v1.35.5+thinkube.0.1.0` release manifest; in production they should be
overridden by values resolved from `thinkube-metadata` (see
`thinkube-installer/KUBEADM_MIGRATION_PLAN.md` §5.4).

## Usage

```yaml
- import_role:
    name: kubeadm_install
```

Or with overrides:

```yaml
- import_role:
    name: kubeadm_install
  vars:
    kubeadm_k8s_minor: "1.35"
    kubeadm_k8s_patch: "1.35.5"
    kubeadm_k8s_apt_revision: "1.1"
```

## Testing

Standalone test on any Ubuntu 24.04 host (the role does NOT require
containerd to be already installed; kubelet will crashloop without it,
which is expected and harmless):

```bash
ansible-playbook -i 'localhost,' -c local <<'EOF'
- hosts: localhost
  roles:
    - kubeadm_install
EOF
```

After a successful run:

```bash
which kubeadm kubelet kubectl                  # → /usr/bin/...
kubeadm version | grep GitVersion              # → v1.35.5
apt-mark showhold | grep -E 'kubeadm|kubelet|kubectl'   # → all three
swapon --show                                  # → empty
sysctl net.ipv4.ip_forward                     # → 1
lsmod | grep -E 'overlay|br_netfilter'         # → both present
systemctl is-enabled kubelet                   # → enabled
systemctl is-active kubelet                    # → activating/failing (expected — no kubeadm config yet)
```
