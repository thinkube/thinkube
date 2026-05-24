# containerd_install

Installs the Docker-provided `containerd.io` package at a pinned
version, writes Thinkube's opinionated `/etc/containerd/config.toml`,
enables the service, and holds the package against accidental upgrade.

## What it provides

- `containerd.io` from `download.docker.com/linux/ubuntu` at the pinned
  apt version (default `2.2.4-1`)
- `/etc/containerd/config.toml` with `version = 3` (containerd 2.x
  native syntax) configuring `io.containerd.cri.v1.runtime` with
  `SystemdCgroup = true`. Single block — the containerd version is
  pinned (`apt-mark hold containerd.io=2.2.4-1`), so dual-block
  "defensive" configs add inconsistency without safety.
- `imports = ["/etc/containerd/conf.d/*.toml"]` so the NVIDIA GPU
  operator's `99-nvidia.toml` drop-in can register the nvidia runtime
  alongside ours.
- `apt-mark hold` on `containerd.io` (no surprise upgrades).
- `systemctl enable --now containerd`.
- Verification step that `containerd config dump` reports
  `SystemdCgroup = true` on `io.containerd.cri.v1.runtime`.

## Why this exact shape

This role exists because of two specific failures observed under
k8s-snap (canonical/k8s-snap#1991 and #2529):

1. **#1991** — k8s-snap hardcoded the imports path so configs from
   `/etc/containerd/conf.d/` were always read, even with a custom
   `containerd-base-dir`. We avoid that by owning the config file
   ourselves on standard paths.
2. **#2529** — containerd 2.1.5 introduced `io.containerd.cri.v1.runtime`
   as the active CRI plugin, defaulting to `SystemdCgroup = false`,
   while kubelet was launched with `--cgroup-driver=systemd`. runc
   refused to create containers due to the cgroupsPath format mismatch.
   We avoid that by writing `version = 3` config that explicitly
   configures `cri.v1.runtime` with `SystemdCgroup = true`. Pinned
   containerd + matching config = bug class eliminated by construction.

## Open validation item

NVIDIA GPU operator's container toolkit DaemonSet writes
`/etc/containerd/conf.d/99-nvidia.toml`. containerd reads each
imported file by its own `version =` header — a v2-syntax drop-in is
still parsed — but a v2 `grpc.v1.cri`-named runtime block lands in a
different plugin namespace than our `cri.v1.runtime` config and would
not merge into the runtime list.

The toolkit's drop-in format must be confirmed on DGX Spark:
- If it registers the nvidia runtime under `cri.v1.runtime` (modern
  syntax), this config works as-is.
- If it only writes legacy v2 syntax, options are: (a) override the
  toolkit's config-version env var if supported, or (b) invert this
  template to `version = 2` + `grpc.v1.cri` only.

Both fallback options are single-block. Never dual-block — that adds
inconsistency without safety since the containerd version is pinned
and the live plugin behaviour is deterministic.

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
