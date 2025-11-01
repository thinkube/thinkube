# Valkey Component

Valkey is an open-source, Redis-compatible in-memory data store. This deployment provides a persistent Valkey instance for infrastructure use, primarily as a backend for Penpot and other services requiring Redis-compatible storage.

## Overview

- **Component Type**: Optional
- **Namespace**: `valkey`
- **Version**: 8.1.0 (built from Alpine edge)
- **Access**: Internal cluster service only
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

- Kubernetes (k8s-snap) cluster
- Storage class: `k8s-hostpath`
- Harbor registry configured (core component)
- Custom Valkey image built and available in Harbor registry
- HARBOR_ROBOT_TOKEN in ~/.env (created during Harbor setup)

## Image Requirements

Valkey uses a custom Docker image built from Alpine Linux with Valkey installed from Alpine edge repository. The image is built in Harbor's base images playbook:

```
ansible/40_thinkube/core/harbor/14_build_base_images.yaml
```

Expected image location:
```
{{ harbor_registry }}/library/valkey:8.1.0
```

## Deployment

Deploy Valkey:

```bash
cd ~/thinkube

# Run orchestrator (recommended)
./scripts/run_ansible.sh ansible/40_thinkube/optional/valkey/00_install.yaml

# Or run individually:
# Step 1: Deploy Valkey
./scripts/run_ansible.sh ansible/40_thinkube/optional/valkey/10_deploy.yaml

# Step 2: Configure service discovery
./scripts/run_ansible.sh ansible/40_thinkube/optional/valkey/17_configure_discovery.yaml
```

## Service Endpoints

Valkey is accessible within the Kubernetes cluster at:

- **ClusterIP Service**: `valkey.valkey.svc.cluster.local:6379`
- **Headless Service**: `valkey-headless.valkey.svc.cluster.local:6379`

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

Remove Valkey deployment:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/valkey/19_rollback.yaml
```

**Warning**: Rollback deletes the PVC and all stored data. Backup data before rollback if needed.

## Usage by Other Services

Services can connect to Valkey using standard Redis clients. Example connection strings:

- **Connection host**: `valkey.valkey.svc.cluster.local`
- **Port**: `6379`
- **Protocol**: Redis/Valkey protocol

No authentication is configured (protected-mode is disabled) as Valkey is only accessible within the cluster network.

## Notes

- Valkey is Redis-compatible and can be used as a drop-in replacement for Redis
- Version 8.1 is from Alpine Linux edge repository
- The deployment uses a custom-built image to ensure compatibility with Harbor's base images
- Data is persisted across pod restarts and deletions