#!/bin/bash

# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

###############################################################################
# thinkube-wipe.sh
#
# Returns tkamd1 (the Kubernetes control plane) to a state as close to a
# freshly installed Ubuntu Server as the machine allows, so the Thinkube
# installer can be run against it from scratch with nothing carried over.
#
# Run it ON the machine being wiped. Everything needed to use it is in this
# file; no other notes are required.
#
#
# WHY "AS CLOSE TO FRESH AS POSSIBLE" IS THE GOAL
# -----------------------------------------------
# A reinstall is only a test of the installer if the installer is the only
# thing that put state on the machine. Every file that survives a wipe is a
# file the installer is never forced to produce correctly, and a file whose
# staleness will surface later as a failure that looks like something else.
#
# That is not hypothetical. A public key from an install two rebuilds earlier
# survived in ~/shared-code/.ssh. The installer wrote a fresh private key
# beside it and never touched the public half, so OpenSSH refused to sign
# with the pair and every node the control plane tried to reach was rejected
# with no message. The wipe preserved the directory; the installer only
# overwrote half of it; nothing compared the two.
#
# So the rule this script follows: if the installer creates it, this script
# destroys it. Only what a fresh Ubuntu Server would have is kept.
#
#
# WHAT IS KEPT, AND WHY
# ---------------------
#   Ubuntu itself, its packages from the base install, the kernel, netplan
#   The 'thinkube' account, its home directory, its sudo rights
#   sshd, and password login (checked before any key is removed)
#   /etc/sudoers.d/thinkube and the account's group memberships
#   The NVIDIA driver: it describes the hardware, not the cluster
#
# The home directory is emptied and refilled from /etc/skel, which is what a
# newly created Ubuntu account contains. It is not deleted, because deleting
# it on a headless machine buys nothing and risks the account.
#
# ~/.ssh and ~/.env are copied to /root/thinkube-wipe-keep/ before removal.
# Root-owned, outside the home, so a mistake is recoverable without weakening
# the wipe.
#
#
# WHAT IS DESTROYED
# -----------------
#   Kubernetes      kubeadm reset, purge kubeadm/kubelet/kubectl/containerd.io,
#                   /etc/kubernetes, /var/lib/kubelet, /var/lib/etcd, CNI
#   Container tools podman, buildah, skopeo, podman-compose, podman-toolbox,
#                   qemu-user-static, binfmt-support, and their state
#   Overlay         tailscale logged out of the tailnet, then purged, with
#                   /var/lib/tailscale removed
#   Storage         SeaweedFS, JuiceFS, OpenEBS/rawfile, and their data
#   Thinkube system all thinkube-* units, the k8s0 dummy interface, the
#                   modules-load / sysctl / resolved drop-ins, the Kubernetes
#                   and Tailscale apt repositories and keyrings
#   Home            everything under it, including shared-code, replaced by
#                   the contents of /etc/skel
#
# Logging tailscale out matters. Purging the package alone leaves the node
# registered, so the next install joins as a duplicate and the tailnet fills
# with offline ghosts of previous rebuilds.
#
#
# THE WORK GUARD
# --------------
# shared-code holds every repository this platform is developed in. Because
# this script deletes it, it refuses to run while any repository under it has
# uncommitted changes, commits that are not on a remote, or no remote at all.
# It names them and exits.
#
# --i-have-no-work-to-lose skips the guard. It is the only way to lose work
# with this script, and it has to be typed.
#
#
# WHERE THIS SCRIPT LIVES
# -----------------------
# In the thinkube repository, under scripts/. It installs itself to
# /usr/local/sbin/thinkube-wipe, outside the home, so that wiping the home
# does not delete the script mid-run.
#
#
# DRIVING THE REINSTALL
# ---------------------
# From tkspark, over SSH, in a normal shell. NOT from code-server: that runs
# on tkamd1 and dies the moment kubelet stops, taking the terminal with it.
# tkspark needs the installer .deb and a copy of ~/.env.
#
# tkamd2 and tkspark clean themselves when re-added: the join playbook resets
# orphaned local state once the control plane positively reports the node as
# NotFound. Reboot tkspark before re-adding it — only a reboot clears the
# pinned BPF maps in /sys/fs/bpf.
#
#
# USAGE
# -----
#   ./thinkube-wipe.sh --dry-run                       # print, change nothing
#   sudo ./thinkube-wipe.sh --yes-wipe-this-machine
#   sudo ./thinkube-wipe.sh --yes-wipe-this-machine --reboot
#
#   --keep-home                 empty only Thinkube's own output, leave the
#                               rest of the home alone (the old behaviour)
#   --i-have-no-work-to-lose    skip the uncommitted/unpushed guard
#
# AFTER IT FINISHES
# -----------------
#   1. sudo reboot            (this machine)
#   2. reboot tkspark         (before it is re-added)
#   3. on tkspark: thinkube-installer
#
# The script ends with a survey of anything it recognises as non-fresh and
# could not remove. An empty survey is the pass condition.
#
###############################################################################
set -uo pipefail

WIPE_USER="${SUDO_USER:-thinkube}"
HOME_DIR="/home/${WIPE_USER}"
KEEP_DIR="/root/thinkube-wipe-keep"
DRY=0
CONFIRMED=0
DO_REBOOT=0
KEEP_HOME=0
SKIP_WORK_GUARD=0

for a in "$@"; do
    case "$a" in
        --dry-run)                 DRY=1 ;;
        --yes-wipe-this-machine)   CONFIRMED=1 ;;
        --reboot)                  DO_REBOOT=1 ;;
        --keep-home)               KEEP_HOME=1 ;;
        --i-have-no-work-to-lose)  SKIP_WORK_GUARD=1 ;;
        -h|--help)                 sed -n '2,140p' "$0"; exit 0 ;;
        *) echo "unknown argument: $a" >&2; exit 2 ;;
    esac
done

if [ "$DRY" -eq 0 ] && [ "$CONFIRMED" -eq 0 ]; then
    echo "Refusing to run without --yes-wipe-this-machine (or --dry-run)." >&2
    echo "Run '$0 --help' for the full explanation." >&2
    exit 2
fi
if [ "$DRY" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then
    echo "Must run as root (use sudo)." >&2
    exit 2
fi

run() {
    if [ "$DRY" -eq 1 ]; then echo "  [dry-run] $*"; else "$@" >/dev/null 2>&1 || true; fi
}
say() { echo; echo "── $*"; }

say "Preflight"
echo "  host:  $(hostname)"
echo "  user:  ${WIPE_USER}"
echo "  home:  ${HOME_DIR}  ($([ "$KEEP_HOME" -eq 1 ] && echo "kept, Thinkube output only" || echo "emptied to /etc/skel"))"
[ "$DRY" -eq 1 ] && echo "  MODE:  DRY RUN — nothing will be changed"

if [ "$(hostname)" != "tkamd1" ]; then
    echo
    echo "  WARNING: this script is written for tkamd1, the control plane."
    echo "  tkamd2 and tkspark clean themselves when re-added by the join"
    echo "  playbook — they only need a reboot. Continue only if you mean to."
    if [ "$DRY" -eq 0 ]; then
        read -r -p "  type the hostname to continue: " ans
        [ "$ans" = "$(hostname)" ] || { echo "  aborted"; exit 1; }
    fi
fi

###############################################################################
# Password login must work before any key is removed, or a headless machine
# becomes unreachable the moment this finishes.
###############################################################################
say "Checking password login is available"
if [ "$(id -u)" -ne 0 ]; then
    echo "  skipped: 'sshd -T' needs root, and this is a dry run as ${WIPE_USER}"
elif sshd -T 2>/dev/null | grep -qi '^passwordauthentication yes'; then
    echo "  sshd: passwordauthentication yes"
else
    echo "  sshd does NOT accept passwords."
    echo "  Removing the SSH keys would leave this machine unreachable."
    echo "  Enable PasswordAuthentication, or run with --keep-home."
    [ "$KEEP_HOME" -eq 0 ] && exit 1
fi

###############################################################################
# Nothing under shared-code may be lost.
###############################################################################
if [ "$KEEP_HOME" -eq 0 ] && [ "$SKIP_WORK_GUARD" -eq 0 ]; then
    say "Checking every repository under shared-code is committed and pushed"
    unsaved=0
    while IFS= read -r gitdir; do
        d=$(dirname "$gitdir")
        dirty=$(git -C "$d" status --porcelain 2>/dev/null | wc -l)
        unpushed=$(git -C "$d" log --branches --not --remotes --oneline 2>/dev/null | wc -l)
        remotes=$(git -C "$d" remote 2>/dev/null | wc -l)
        if [ "$dirty" -gt 0 ] || [ "$unpushed" -gt 0 ] || [ "$remotes" -eq 0 ]; then
            printf "  %-58s dirty=%s unpushed=%s remotes=%s\n" \
                   "${d#"${HOME_DIR}/shared-code/"}" "$dirty" "$unpushed" "$remotes"
            unsaved=$((unsaved + 1))
        fi
    done < <(find "${HOME_DIR}/shared-code" -maxdepth 4 -name .git \
                  -not -path "*/node_modules/*" 2>/dev/null)

    if [ "$unsaved" -gt 0 ]; then
        echo
        echo "  ${unsaved} repositories hold work that only exists on this machine."
        echo "  This script deletes shared-code. Commit and push them first."
        echo "  A repository with no remote cannot be pushed anywhere — move it,"
        echo "  or accept the loss with --i-have-no-work-to-lose."
        [ "$DRY" -eq 0 ] && exit 1
        echo "  [dry-run] a real run would stop here"
    else
        echo "  clean: every repository is committed and pushed"
    fi
fi

###############################################################################
# Kubernetes layer. Reset first: kubeadm is gone after the purge.
###############################################################################
say "Stopping kubelet and the control-plane static pods"
run systemctl stop kubelet
run systemctl disable kubelet
run rm -f /etc/kubernetes/manifests/kube-apiserver.yaml \
          /etc/kubernetes/manifests/kube-controller-manager.yaml \
          /etc/kubernetes/manifests/kube-scheduler.yaml \
          /etc/kubernetes/manifests/etcd.yaml

if command -v crictl >/dev/null 2>&1; then
    say "Force-stopping pods (crictl)"
    run crictl -r unix:///run/containerd/containerd.sock rmp -fa
fi

say "kubeadm reset"
if command -v kubeadm >/dev/null 2>&1; then
    run kubeadm reset -f
else
    echo "  kubeadm not installed; nothing to reset"
fi

###############################################################################
# Leave the tailnet before the client is removed, or the node stays registered
# and the next install joins as a duplicate.
###############################################################################
say "Leaving the Tailscale network"
if command -v tailscale >/dev/null 2>&1; then
    run tailscale logout
    run tailscale down
else
    echo "  tailscale not installed"
fi

say "Purging packages the installer added"
PURGE_PKGS="kubeadm kubelet kubectl containerd.io \
            podman podman-compose podman-toolbox buildah skopeo \
            qemu-user-static binfmt-support \
            tailscale tailscale-archive-keyring \
            sshpass s3cmd apache2-utils"
run apt-mark unhold ${PURGE_PKGS}
if [ "$DRY" -eq 1 ]; then
    echo "  [dry-run] apt-get purge -y ${PURGE_PKGS}"
    echo "  [dry-run] apt-get autoremove --purge -y"
else
    DEBIAN_FRONTEND=noninteractive apt-get purge -y ${PURGE_PKGS} >/dev/null 2>&1 || true
    DEBIAN_FRONTEND=noninteractive apt-get autoremove --purge -y >/dev/null 2>&1 || true
fi

say "Unmounting leftover kubelet pod volumes"
if [ "$DRY" -eq 1 ]; then
    awk '/\/var\/lib\/kubelet/ {print "  [dry-run] umount -l " $2}' /proc/mounts
else
    awk '/\/var\/lib\/kubelet/ {print $2}' /proc/mounts | sort -r \
        | xargs -r umount -l 2>/dev/null || true
fi

say "Removing cluster and runtime state"
for d in /etc/kubernetes /etc/cni /etc/containerd \
         /var/lib/kubelet /var/lib/containerd /var/lib/etcd \
         /var/lib/tailscale /var/lib/cni /var/lib/containers \
         /var/openebs /var/lib/rawfile-localpv /var/csi /var/local/openebs \
         /opt/cni /opt/containerd; do
    echo "  rm -rf $d"; run rm -rf "$d"
done

say "Removing SeaweedFS / JuiceFS data and build caches"
for d in /ssd/object_store /ssd/seaweed-master /storage/filer_store /storage/logs \
         /var/lib/juicefs /var/jfsCache \
         /var/lib/jupyterhub-venvs /var/lib/thinkube; do
    echo "  rm -rf $d"; run rm -rf "$d"
done

###############################################################################
# Thinkube-owned system configuration
###############################################################################
say "Removing Thinkube systemd units, dummy interface and drop-ins"
run systemctl disable --now k8s-api-proxy.socket k8s-api-proxy.service \
    thinkube-node-ip-sync.timer thinkube-node-ip-sync.service \
    thinkube-node-ip-sync-watch.service \
    thinkube-link-watchdog.timer thinkube-link-watchdog.service
run rm -f /etc/systemd/system/k8s-api-proxy.socket \
          /etc/systemd/system/k8s-api-proxy.service \
          /etc/systemd/system/thinkube-node-ip-sync.timer \
          /etc/systemd/system/thinkube-node-ip-sync.service \
          /etc/systemd/system/thinkube-node-ip-sync-watch.service \
          /etc/systemd/system/thinkube-link-watchdog.timer \
          /etc/systemd/system/thinkube-link-watchdog.service \
          /usr/local/bin/thinkube-node-ip-sync \
          /usr/local/bin/thinkube-link-watchdog \
          /etc/systemd/network/10-k8s-dummy.netdev \
          /etc/systemd/network/10-k8s-dummy.network \
          /etc/modules-load.d/thinkube-k8s.conf \
          /etc/sysctl.d/99-thinkube-k8s.conf \
          /etc/systemd/resolved.conf.d/10-thinkube.conf
run systemctl daemon-reload

say "Removing the apt repositories and keyrings the installer added"
run rm -f /etc/apt/sources.list.d/kubernetes.list \
          /etc/apt/sources.list.d/docker.list \
          /etc/apt/sources.list.d/tailscale.list \
          /etc/apt/keyrings/kubernetes-apt-keyring.gpg \
          /etc/apt/keyrings/tailscale-archive-keyring.gpg \
          /usr/share/keyrings/tailscale-archive-keyring.gpg
run apt-get update

say "Resetting UFW to its packaged state"
run ufw --force disable
run ufw --force reset

###############################################################################
# The home directory
###############################################################################
if [ "$KEEP_HOME" -eq 1 ]; then
    say "Removing Thinkube leftovers from ${HOME_DIR} (--keep-home)"
    for p in "${HOME_DIR}/.kube" \
             "${HOME_DIR}/.ansible" \
             "${HOME_DIR}/.ansible_async" \
             "${HOME_DIR}/.thinkube-installer" \
             "${HOME_DIR}/.local/bin/kubectl" \
             "${HOME_DIR}/.local/bin/helm" \
             "${HOME_DIR}/.ssh/thinkube_cluster_key" \
             "${HOME_DIR}/.ssh/thinkube_cluster_key.pub" \
             "${HOME_DIR}/shared-code/.ssh" \
             "${HOME_DIR}/shared-code/.ansible" \
             "${HOME_DIR}/shared-code/.kube" \
             "${HOME_DIR}/shared-code/conformance-results"; do
        echo "  rm -rf $p"; run rm -rf "$p"
    done
    echo "  kept: ~/.env, ~/shared-code and every repository under it"
else
    say "Preserving credentials outside the home"
    echo "  ${KEEP_DIR}/"
    run mkdir -p "${KEEP_DIR}"
    run chmod 700 "${KEEP_DIR}"
    [ -d "${HOME_DIR}/.ssh" ] && run cp -a "${HOME_DIR}/.ssh" "${KEEP_DIR}/ssh"
    [ -f "${HOME_DIR}/.env" ] && run cp -a "${HOME_DIR}/.env" "${KEEP_DIR}/env"

    say "Emptying ${HOME_DIR} and refilling it from /etc/skel"
    if [ "$DRY" -eq 1 ]; then
        echo "  [dry-run] rm -rf ${HOME_DIR}/* ${HOME_DIR}/.[!.]*"
        echo "  [dry-run] cp -a /etc/skel/. ${HOME_DIR}/"
    else
        find "${HOME_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
        cp -a /etc/skel/. "${HOME_DIR}/" 2>/dev/null || true
        chown -R "${WIPE_USER}:${WIPE_USER}" "${HOME_DIR}"
        chmod 750 "${HOME_DIR}"
    fi
    echo "  a copy of the old ~/.ssh and ~/.env is in ${KEEP_DIR}"
fi

###############################################################################
# Survey. An empty survey is the pass condition.
###############################################################################
say "Survey of state this script recognises as non-fresh"
left=0
note() { echo "  $*"; left=$((left + 1)); }

for d in /etc/kubernetes /etc/cni /etc/containerd /var/lib/kubelet \
         /var/lib/containerd /var/lib/etcd /var/lib/tailscale \
         /var/lib/containers /var/local/openebs /opt/cni /opt/containerd \
         /ssd/object_store /storage/filer_store; do
    [ -e "$d" ] && note "still present: $d"
done

for p in kubeadm kubelet kubectl containerd.io podman buildah skopeo tailscale; do
    dpkg -l "$p" 2>/dev/null | grep -q '^ii' && note "still installed: $p"
done

for u in k8s-api-proxy thinkube-node-ip-sync thinkube-link-watchdog; do
    systemctl list-unit-files 2>/dev/null | grep -q "^${u}" && note "unit still known: $u"
done

if [ "$KEEP_HOME" -eq 0 ]; then
    while IFS= read -r e; do
        b=$(basename "$e")
        [ -e "/etc/skel/$b" ] || note "not in /etc/skel: ~/$b"
    done < <(find "${HOME_DIR}" -mindepth 1 -maxdepth 1 2>/dev/null)
fi

# Any private key whose public half does not match it will break SSH
# silently, exactly as it did before this check existed.
while IFS= read -r key; do
    [ -f "${key}.pub" ] || continue
    if [ "$(ssh-keygen -y -f "$key" 2>/dev/null | awk '{print $1" "$2}')" \
       != "$(awk '{print $1" "$2}' "${key}.pub" 2>/dev/null)" ]; then
        note "key pair does not match: $key"
    fi
done < <(find "${HOME_DIR}" /root -maxdepth 4 -name '*_key' -o -name 'id_*' 2>/dev/null | grep -v '\.pub$')

if [ "$left" -eq 0 ]; then
    echo "  nothing found — the machine matches the fresh-Ubuntu checklist"
fi

###############################################################################
say "Complete"
cat <<EOF

  Still present: Ubuntu, the '${WIPE_USER}' account, its home, sudo, sshd,
  password login, netplan, and the NVIDIA driver.

  NOT cleared by this script — only a reboot clears them:
    pinned BPF maps in /sys/fs/bpf
    the cilium_* and k8s0 interfaces
    tmpfs runtime directories

  Next:
    1. sudo reboot                 (this machine)
    2. reboot tkspark              (before it is re-added; its BPF state is
                                    the fault this rebuild exists to escape)
    3. on tkspark: thinkube-installer
       tkamd2 and tkspark are reset automatically by the join playbook.
EOF

if [ "$DO_REBOOT" -eq 1 ] && [ "$DRY" -eq 0 ]; then
    echo
    echo "  rebooting in 5s (Ctrl-C to cancel)"
    sleep 5
    reboot
fi
