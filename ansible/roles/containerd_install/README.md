# containerd_install

Installs the Docker-provided `containerd.io` package at a pinned
version, writes Thinkube's opinionated `/etc/containerd/config.toml`,
enables the service, and holds the package against accidental upgrade.

## What it provides

- `containerd.io` from `download.docker.com/linux/ubuntu` at the pinned
  apt version (default `2.2.4-1`)
- `/etc/containerd/config.toml` with `SystemdCgroup = true` on **both**
  `io.containerd.cri.v1.runtime` (containerd 2.x active CRI plugin) and
  `io.containerd.grpc.v1.cri` (legacy, defensive)
- `imports = ["/etc/containerd/conf.d/*.toml"]` for NVIDIA GPU
  operator's `99-nvidia.toml` to merge cleanly
- `apt-mark hold` on `containerd.io` (no surprise upgrades)
- `systemctl enable --now containerd`
- Verification step that `containerd config dump` reports
  `SystemdCgroup = true` on the active CRI plugin

## Why this exact shape

This role exists because of two specific failures observed under
k8s-snap (canonical/k8s-snap#1991 and #2529):

1. `#1991` — k8s-snap hardcoded the imports path so configs from
   `/etc/containerd/conf.d/` were always read, even with a custom
   `containerd-base-dir`. We avoid that by owning the config file
   ourselves on standard paths.
2. `#2529` — containerd 2.1.5 introduced `io.containerd.cri.v1.runtime`
   as the active CRI plugin, defaulting to `SystemdCgroup = false`,
   while kubelet was launched with `--cgroup-driver=systemd`. runc
   refused to create containers due to the cgroupsPath format mismatch.
   We avoid that by setting `SystemdCgroup = true` on both plugins.

## Variables

See `defaults/main.yaml`. The defaults pin to the
`v1.35.5+thinkube.0.1.0` release manifest; in production they should be
overridden by values resolved from `thinkube-metadata` (see
`thinkube-installer/KUBEADM_MIGRATION_PLAN.md` §5.4).

## Usage

```yaml
- import_role:
    name: containerd_install
```

Or with overrides:

```yaml
- import_role:
    name: containerd_install
  vars:
    containerd_apt_version: "2.2.4-1"
    containerd_sandbox_image: "registry.k8s.io/pause:3.10"
```

## Testing

Standalone test on any Ubuntu 24.04 host:

```bash
ansible-playbook -i 'localhost,' -c local <<'EOF'
- hosts: localhost
  roles:
    - containerd_install
EOF
```

After a successful run:

```bash
systemctl is-active containerd                       # → active
apt-mark showhold | grep containerd.io               # → containerd.io
containerd config dump | grep -A1 'v1\.runtime.*runc.options'   # SystemdCgroup = true
```
