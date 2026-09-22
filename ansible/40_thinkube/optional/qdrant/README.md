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
User → Browser → Qdrant Dashboard → OAuth2 Proxy → Keycloak
                      ↓
                 Qdrant API ← Direct API Access (No Auth)
                      ↓
              Vector Storage (150Gi PVC)
```

## Components

1. **Qdrant** - Vector database engine
2. **OAuth2 Proxy** - Authentication layer for dashboard
3. **Valkey** - Redis-compatible session storage
4. **Keycloak Integration** - SSO authentication
5. **Persistent Storage** - 150Gi for vector data

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
- API access is unauthenticated for application integration
- OAuth2 Proxy handles the authentication flow

### Network Configuration

Gateway API HTTPRoutes:
1. **Dashboard** (`https://qdrant-dashboard.<domain_name>`, `qdrant_dashboard_hostname`)
   - Protected by OAuth2 authentication
   - Route `qdrant-root-redirect` redirects `/` to `/dashboard`
2. **API** (`https://qdrant.<domain_name>`, `qdrant_hostname`)
   - Direct access without authentication
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
kubectl -n qdrant logs deployment/oauth2-proxy
kubectl -n qdrant logs deployment/ephemeral-valkey
```

### OAuth2 Proxy Issues
```bash
# Check OAuth2 configuration
kubectl -n qdrant get secret oauth2-proxy -o yaml

# View OAuth2 logs
kubectl -n qdrant logs deployment/oauth2-proxy -f
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