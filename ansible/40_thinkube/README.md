# 40 Thinkube - Component-Based Deployment

This directory contains the component-based deployment structure for the Thinkube platform, migrated from the thinkube-core repository as part of Milestone 2.

## Directory Structure

```
40_thinkube/
├── core/                           # Essential platform components
│   ├── infrastructure/            # MicroK8s, ingress, cert-manager, coredns
│   ├── keycloak/                 # SSO and authentication
│   ├── postgresql/               # Database services
│   ├── harbor/                   # Container registry
│   ├── minio/                    # Object storage
│   ├── argo-workflows/           # Workflow automation
│   ├── argocd/                   # GitOps deployment
│   ├── devpi/                    # Python package repository
│   ├── awx/                      # Ansible automation
│   ├── mkdocs/                   # Documentation platform
│   └── thinkube-dashboard/       # Main dashboard
└── optional/                      # AWX-deployed components
    ├── prometheus/               # Metrics collection
    ├── grafana/                  # Metrics visualization
    ├── opensearch/               # Log aggregation
    ├── jupyterhub/               # Data science notebooks
    ├── code-server/              # VS Code in browser
    ├── mlflow/                   # ML experiment tracking
    ├── knative/                  # Serverless platform
    ├── qdrant/                   # Vector database
    ├── pgadmin/                  # PostgreSQL admin
    ├── penpot/                   # Design platform
    └── valkey/                   # Cache service
```

## Development Approach

Each component follows the standard playbook numbering convention:
- `10_*.yaml` - Primary deployment
- `15_*.yaml` - Configuration
- `18_*.yaml` - Testing
- `19_*.yaml` - Rollback

## Migration from thinkube-core

Components are being migrated from the thinkube-core repository to this structure following these principles:
1. Preserve all original functionality
2. Update to use proper host groups (microk8s_workers, microk8s_control_plane)
3. Migrate from hardcoded values to inventory variables
4. Replace manual cert configuration with cert-manager

## GitHub Issue Tracking

Each component has a corresponding GitHub issue:
- Infrastructure components: CORE-001 to CORE-003
- Core services: CORE-004 to CORE-014
- Optional services: OPT-001 to OPT-011

See [/docs/architecture-k8s/COMPONENT_ARCHITECTURE.md](/docs/architecture-k8s/COMPONENT_ARCHITECTURE.md) for the complete component architecture and deployment sequence.