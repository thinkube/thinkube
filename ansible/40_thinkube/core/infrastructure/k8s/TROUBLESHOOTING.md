# Troubleshooting: Kubernetes (kubeadm)

Each problem below is tied to a check or a task in the playbooks of this folder. Fixes go through the playbooks.

## `10_install_k8s.yaml` stops before it installs anything

**Symptom.** The play fails in the first tasks with one of these messages:

- `This playbook requires Ubuntu 24.04 LTS (found ...)`
- `Minimum 16 CPU cores required (found ...)`
- `Minimum 64GB RAM required (threshold 60GB after kernel reservation) (found ...GB)`
- `Required variable ... is not defined`

**Cause.** The control plane does not meet a checked prerequisite, or the inventory is missing a variable. See the Prerequisites section in [README.md](README.md).

**Fix.** Use a host that meets the minimum, or add the missing variable to the inventory. Then run the install again.

## Worker join stops at "Verify control plane API is reachable through the node-local VIP"

**Symptom.** `20_join_workers.yaml` retries this task 12 times, 5 seconds apart, and then fails. `28_test_worker.yaml` fails at "Verify API server reachable through the node-local VIP" in the same way.

**Cause.** The worker reaches the API at `https://172.16.0.1:6443` through the `k8s0` interface and the `k8s-api-proxy` socket. The proxy forwards to the `lan_ip` of the control plane in the inventory. The call fails if `k8s0` is missing, if the proxy socket is not active, or if the control plane is not reachable at that address.

**Fix.**

1. Check that the control plane's `lan_ip` in the inventory is its current LAN address.
2. Check that the control plane is up.
3. Run `20_join_workers.yaml` again. It rewrites the proxy unit from the inventory.

## Worker does not become Ready after `kubeadm join`

**Symptom.** `20_join_workers.yaml` fails with:

```
Worker <host> did not become Ready within 2 minutes and no wedged Cilium pod was found to self-heal.
```

**Cause.** The playbook waits about 2 minutes for the node to become Ready. It handles one known cause by itself: the `cilium-agent` pod on the new node is not ready and has restarted at least twice. This happens when the agent crashes with `Non-existent configuration directory /tmp/cilium/config-map`. The playbook force-deletes that pod once, and kubelet creates it again. It then waits up to 5 more minutes. The message above means the node is not Ready for another reason.

**Fix.** On the control plane, look at the node and at the Cilium pod on that node:

```
kubectl describe node <host>
kubectl -n kube-system get pod -l k8s-app=cilium --field-selector spec.nodeName=<host>
```

Correct the cause. Then run `28_test_worker.yaml` to check the worker. Running `20_join_workers.yaml` again does not repeat the join or the Ready wait for a node that is already in the cluster.

## A node that was removed from the cluster does not join again

**Symptom.** `kubeadm join` fails its preflight checks on a worker that was part of a cluster before.

**Cause.** The worker still has `/etc/kubernetes/kubelet.conf`, its certificates and a running kubelet. `20_join_workers.yaml` clears this state with `kubeadm reset -f` before the join. It does this only when the control plane answers `NotFound` for that node. If the control plane cannot be reached, the playbook does not reset the node. This protects a healthy node from being wiped during a short API error.

**Fix.** Make sure the control plane API answers. Then run `20_join_workers.yaml` again. To clear the worker completely, run `29_rollback_workers.yaml` first.

## Pods on a new worker have `10.88.x.x` addresses

**Symptom.** Pods on a worker that just joined have IP addresses in `10.88.0.0/16`, outside the pod network `10.244.0.0/16`.

**Cause.** These pods started before Cilium gave the new node its pod address range.

**Fix.** `20_join_workers.yaml` waits for `cilium status` on the new node and then deletes every pod on that node with a `10.88.` address, so the pods start again with a correct address. This cleanup runs only in the run that joins the node. A later run of the playbook skips it, because the node is already in the cluster. If such a pod remains, delete it. Its controller starts it again with an address from Cilium.

## A node goes NotReady after its LAN address changes

**Symptom.** A node's address changed, for example after a DHCP renewal or a move to another network, and the node shows NotReady.

**Cause.** kubelet's `--node-ip` in `/var/lib/kubelet/kubeadm-flags.env` still holds the old address.

**Fix.** `thinkube-node-ip-sync` corrects this at boot and every minute after that. It writes the new address and restarts kubelet. On workers it also points the API proxy at the control plane's new address, which it finds by host name over LLMNR (5355/udp). Check that the timer is active:

```
systemctl status thinkube-node-ip-sync.timer
journalctl -u thinkube-node-ip-sync-watch.service
```

If the timer or the script is missing, run `10_install_k8s.yaml` (control plane) or `20_join_workers.yaml` (workers) again. They install and enable it.

## `16_test_kubelet_protection.yaml` and `18_test_control.yaml` fail on a working cluster

**Symptom.**

- `16_test_kubelet_protection.yaml` fails at "Read kubelet args file".
- `18_test_control.yaml` fails at "Check if k8s-snap is installed".

**Cause.** Both playbooks check files and commands that this install does not create:

- `/var/snap/k8s/common/args/kubelet`
- `snap list k8s` and `k8s status`
- a UFW rule for port 6400

On this install, the kubelet memory settings are in the `KubeletConfiguration` of `templates/kubeadm-init-config.yaml.j2` and `templates/kubeadm-join-config.yaml.j2`.

**Fix.** No playbook fix exists. A failure of these two playbooks says nothing about the health of the cluster. `28_test_worker.yaml` checks workers against this install.
