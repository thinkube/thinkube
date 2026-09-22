# Valkey Component

Valkey is an open-source, Redis-compatible in-memory data store. This deployment provides a persistent Valkey instance for infrastructure use. The optional components Argilla and Langfuse require it.

## Installation

Valkey is an optional component. It is installed and removed from the
Optional Components page in thinkube-control, not on its own. The page runs
`00_install.yaml` to install (it runs `10_deploy.yaml` and then
`17_configure_discovery.yaml`), `18_test.yaml` to test and `19_rollback.yaml`
to remove it. The component catalogue lists no required components.

## Overview

- **Component Type**: Optional
- **Namespace**: `valkey`
- **Image**: `{{ harbor_registry }}/library/valkey:7.2-alpine`
- **Access**: Cluster service, plus TCP port 6379 on the gateway at `valkey.{{ domain_name }}`
- **Persistence**: Yes, 5Gi PVC with AOF and snapshot backups

## Deployment Structure

```
00_install.yaml              # Orchestrator playbook
10_deploy.yaml               # Deploy Valkey with persistence
17_configure_discovery.yaml  # Register service in thinkube-control
18_test.yaml                 # Validate deployment and connectivity
19_rollback.yaml             # Remove Valkey and cleanup resources
```

## Requirements

- Kubernetes (kubeadm) cluster
- Storage class: `k8s-hostpath`
- Harbor registry configured (core component), with the `valkey:7.2-alpine` image mirrored into the `library` project
- The gateway's TCP listener and TCPRoute for port 6379 (`infrastructure/gateway-api/10_deploy.yaml`)
- HARBOR_ROBOT_TOKEN in ~/.env (created during Harbor setup)
- ADMIN_PASSWORD set: it becomes the Valkey password

## Image Requirements

`10_deploy.yaml` uses the upstream image `docker.io/valkey/valkey:7.2-alpine`,
mirrored into Harbor from `thinkube-metadata/mirror_images.json`:

```
{{ harbor_registry }}/library/valkey:7.2-alpine
```

`core/harbor-images/14_build_base_images.yaml` also builds a custom
`library/valkey:8.1.0` image from Alpine edge, but this playbook does not use it.

## Service Endpoints

Valkey is accessible within the Kubernetes cluster at:

- **ClusterIP Service**: `valkey.valkey.svc.cluster.local:6379`
- **Headless Service**: `valkey-headless.valkey.svc.cluster.local:6379`
- **External**: `valkey.{{ domain_name }}:6379`, through the gateway's TCPRoute. The deploy creates the ReferenceGrant `allow-gateway-tcp` so the route may reach the Service.

## Persistence Configuration

Valkey is configured with:
- **Append-Only File (AOF)**: Enabled for durability
- **Snapshot saves**: Every 900 seconds if 1+ keys changed
- **Storage**: 5Gi persistent volume
- **Storage class**: k8s-hostpath

## Resource Limits

```yaml
requests:
  memory: 128Mi
  cpu: 100m
limits:
  memory: 256Mi
  cpu: 200m
```

## Testing

Test the Valkey deployment:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/valkey/18_test.yaml
```

The test playbook verifies:
- Namespace exists
- Pods are running
- Services are configured
- PVC is bound
- Valkey responds to PING command

## Rollback

Removing Valkey from the Optional Components page runs `19_rollback.yaml`.
It deletes the PVC and all stored data. Back up data first if needed.

## Usage by Other Services

Services can connect to Valkey using standard Redis clients. Example connection strings:

- **Connection host**: `valkey.valkey.svc.cluster.local`
- **Port**: `6379`
- **Protocol**: Redis/Valkey protocol

Valkey requires a password (`--requirepass`). The password is `ADMIN_PASSWORD`, stored in the Secret `valkey-auth` (key `password`). Protected mode is disabled.

## Notes

- Valkey is Redis-compatible and can be used as a drop-in replacement for Redis
- `maxmemory-policy` is `noeviction`
- Data is persisted across pod restarts and deletions