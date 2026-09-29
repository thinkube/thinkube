# Qdrant Deployment

Qdrant is a vector database for semantic search and AI applications, providing high-performance similarity search capabilities.

## Installation

Qdrant is an optional component. It is installed and removed from the
Optional Components page in thinkube-control, not on its own. The page runs
`00_install.yaml` to install (it runs `10_deploy.yaml` and then
`17_configure_discovery.yaml`), `18_test.yaml` to test and `19_rollback.yaml`
to remove it. The component catalogue lists no required components; the
playbook uses Keycloak and Harbor, which are core components.

## Overview

Qdrant is designed for:
- Vector similarity search
- Semantic search applications
- Machine learning model serving
- AI-powered recommendation systems
- Neural search applications

## Architecture

```
User → Browser → Gateway (Keycloak login) → Qdrant Dashboard
                      ↓
                 Qdrant API ← API access (api-key header)
                      ↓
              Vector Storage (150Gi PVC)
```

## Components

1. **Qdrant** - Vector database engine
2. **Gateway login** - Envoy Gateway `SecurityPolicy` `qdrant-dashboard-oidc` on the dashboard routes (role `gateway_oidc`)
3. **Keycloak Integration** - SSO authentication
4. **Persistent Storage** - 150Gi for vector data

## Deployment

### Prerequisites

1. Kubernetes (kubeadm) must be deployed
2. Keycloak must be deployed
3. The wildcard TLS certificate must exist (`infrastructure/acme-certificates`)
4. Set environment variable:
   ```bash
   export ADMIN_PASSWORD='your-admin-password'
   ```

### Test the deployment

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/qdrant/18_test.yaml
```

### Rollback

Removing Qdrant from the Optional Components page runs `19_rollback.yaml`.
It deletes the `qdrant` namespace (with the data volume) and the `qdrant` Helm
repository.

## Configuration

### Resource Allocation

Default resources:
- CPU: 2 cores (request), 4 cores (limit)
- Memory: 4Gi (request), 8Gi (limit)
- Storage: 150Gi persistent volume

### Authentication

- Dashboard access requires Keycloak authentication
- API access requires the API key in the `api-key` header. The key is
  created once in the `qdrant-auth` Secret and reaches the IDE and notebooks
  as `QDRANT_API_KEY` through service discovery
- The dashboard asks for the same API key after the Keycloak login
- The gateway handles the login on both dashboard routes, and handles the
  callback at `/oauth2/callback`

### Network Configuration

Gateway API HTTPRoutes:
1. **Dashboard** (`https://qdrant-dashboard.<domain_name>`, `qdrant_dashboard_hostname`)
   - Requires a Keycloak login at the gateway
   - Route `qdrant-root-redirect` redirects `/` to `/dashboard`
2. **API** (`https://qdrant.<domain_name>`, `qdrant_hostname`)
   - Requires the API key (`api-key` header); `/healthz` is open for health checks
   - REST API, backend port 6333
   - gRPC is enabled on the service, port 6334, inside the cluster only; no route exposes it

## API Usage

### REST API Examples

```bash
# Check health
curl https://qdrant.<domain_name>/health

# List collections
curl https://qdrant.<domain_name>/collections

# Create a collection
curl -X PUT https://qdrant.<domain_name>/collections/my_collection \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 768,
      "distance": "Cosine"
    }
  }'

# Insert vectors
curl -X PUT https://qdrant.<domain_name>/collections/my_collection/points \
  -H "Content-Type: application/json" \
  -d '{
    "points": [
      {
        "id": 1,
        "vector": [0.1, 0.2, ..., 0.768],
        "payload": {"text": "example"}
      }
    ]
  }'

# Search vectors
curl -X POST https://qdrant.<domain_name>/collections/my_collection/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, ..., 0.768],
    "limit": 10
  }'
```

### gRPC API

The gRPC API is available inside the cluster at `qdrant.qdrant.svc.cluster.local:6334`. It has no external route.

## Access

Once deployed, Qdrant is available at:
- **Dashboard**: `https://qdrant-dashboard.<domain_name>`
- **REST API**: `https://qdrant.<domain_name>`
- **gRPC API**: `qdrant.qdrant.svc.cluster.local:6334` (inside the cluster)

## Troubleshooting

### Check Pod Status
```bash
kubectl -n qdrant get pods
kubectl -n qdrant describe pod <pod-name>
```

### View Logs
```bash
kubectl -n qdrant logs statefulset/qdrant
```

### Login Issues
```bash
kubectl -n qdrant get securitypolicy qdrant-dashboard-oidc -o yaml
```

### API Key
```bash
kubectl -n qdrant get secret qdrant-auth -o jsonpath='{.data.api-key}' | base64 -d
```

```python
from qdrant_client import QdrantClient
import os
client = QdrantClient(url=os.environ["QDRANT_URL"], port=443, https=True,
                      api_key=os.environ["QDRANT_API_KEY"])
```

### Storage Issues
```bash
# Check PVC status
kubectl -n qdrant get pvc

# Check PV status
kubectl get pv
```

## Integration Examples

### Python Client
```python
from qdrant_client import QdrantClient

client = QdrantClient(
    url="https://qdrant.<domain_name>",
    prefer_grpc=False
)

# Create collection
client.create_collection(
    collection_name="my_collection",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)
```

### JavaScript Client
```javascript
import { QdrantClient } from '@qdrant/js-client-rest';

const client = new QdrantClient({
    url: 'https://qdrant.<domain_name>',
});

// Create collection
await client.createCollection('my_collection', {
    vectors: {
        size: 768,
        distance: 'Cosine',
    },
});
```

## Next Steps

1. **Create Collections** for your vector data
2. **Configure Indexing** parameters for performance
3. **Set up Backups** for vector data
4. **Monitor Performance** metrics
5. **Integrate with AI Models** for embeddings

## Related Components

- **JupyterHub** - For AI model development
- **SeaweedFS** - For model and data storage (S3-compatible)
- **Argo Workflows** - For ML pipeline orchestration
- **Harbor** - Holds the Qdrant image (`library/qdrant:v1.18.0`)

---
*Component of the Thinkube Platform - Optional Services*