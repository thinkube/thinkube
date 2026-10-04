# 40 Thinkube - platform components

One folder of playbooks per component of the Thinkube platform.

- **core/**: installed by the Thinkube installer, in the order it sets.
- **optional/**: installed and removed from the Optional Components page in
  thinkube-control. The catalogue of optional components is
  `optional_components.json` in the thinkube-metadata repository.

## Directory Structure

```
40_thinkube/
├── core/
│   ├── infrastructure/
│   │   ├── k8s/                  # Kubernetes (kubeadm) on control plane and workers
│   │   ├── gateway-api/          # Gateway API ingress
│   │   ├── acme-certificates/    # TLS certificates
│   │   ├── coredns/              # Cluster DNS
│   │   ├── dns-server/           # BIND9 DNS for the platform domain
│   │   ├── gpu_operator/         # NVIDIA GPU operator
│   │   ├── tailscale-operator/   # Tailscale operator
│   │   └── paused-backend/       # Page shown while a scaled-to-zero service is paused
│   ├── postgresql/               # Database
│   ├── keycloak/                 # SSO and authentication
│   ├── seaweedfs/                # Object storage (S3-compatible)
│   ├── juicefs/                  # POSIX filesystem over SeaweedFS
│   ├── harbor/                   # Container registry
│   ├── harbor-images/            # Mirrored public images and Thinkube base images
│   ├── gitea/                    # Git server
│   ├── argo-workflows/           # Workflows and image builds
│   ├── argocd/                   # GitOps deployment
│   ├── devpi/                    # Python package index
│   ├── mlflow/                   # Experiment tracking and model registry
│   ├── jupyterhub/               # Notebooks
│   ├── code-server/              # VS Code in the browser
│   ├── thinkube-control/         # The platform's control plane
│   └── gpu_operator/             # VERSION file only; the playbooks are in infrastructure/gpu_operator
└── optional/
    ├── argilla/                  # Data annotation and curation for model training
    ├── chroma/                   # Embedding database
    ├── clickhouse/               # Analytics database
    ├── cvat/                     # Image and video annotation
    ├── knative/                  # Serverless workloads that scale to zero
    ├── langflow/                 # Low-code builder for RAG and LLM workflows
    ├── langfuse/                 # LLM tracing and monitoring
    ├── litellm/                  # LLM API proxy
    ├── nats/                     # Messaging with JetStream
    ├── ollama/                   # Local LLM inference for quantized models
    ├── opensearch/               # Search and analytics
    ├── perses/                   # Dashboards
    ├── pgadmin/                  # PostgreSQL administration
    ├── prometheus/               # Metrics collection
    ├── qdrant/                   # Vector database
    ├── valkey/                   # In-memory data store, Redis-compatible
    └── weaviate/                 # Vector database
```

Three optional components have no folder here, because they are templates:
`vllm` (tkt-vllm-gradio), `tensorrt` (tkt-tensorrt-llm-harmony) and
`text-embeddings` (tkt-text-embeddings). thinkube-control deploys them from
their repositories.

## Playbook numbering

Each component folder follows the same numbering:
- `00_install.yaml` - Runs the component's playbooks in order
- `10_*.yaml` - Deployment
- `15_*.yaml` - Configuration
- `17_configure_discovery.yaml` - ConfigMap describing the component's service endpoints
- `18_test.yaml` - Tests
- `19_rollback.yaml` - Rollback
