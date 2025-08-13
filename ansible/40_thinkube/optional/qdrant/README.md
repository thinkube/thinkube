# Qdrant Deployment

Qdrant is a vector database for semantic search and AI applications, providing high-performance similarity search capabilities.

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

1. MicroK8s must be deployed
2. Keycloak must be deployed (CORE-006)
3. TLS certificates must be configured (CORE-004)
4. Set environment variable:
   ```bash
   export ADMIN_PASSWORD='your-admin-password'
   ```

### Deploy Qdrant

```bash
cd ~/thinkube

# Deploy Qdrant with OAuth2 authentication
./scripts/run_ansible.sh ansible/40_thinkube/optional/qdrant/10_deploy.yaml

# Test the deployment
./scripts/run_ansible.sh ansible/40_thinkube/optional/qdrant/18_test.yaml
```

### Rollback

```bash
# Remove Qdrant and all resources
./scripts/run_ansible.sh ansible/40_thinkube/optional/qdrant/19_rollback.yaml
```

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

Two ingress configurations:
1. **Dashboard** (`https://qdrant-dashboard.thinkube.com`)
   - Protected by OAuth2 authentication
   - Redirects `/` to `/dashboard`
2. **API** (`https://qdrant.thinkube.com`)
   - Direct access without authentication
   - Supports REST API on port 6333
   - gRPC API on port 6334

## API Usage

### REST API Examples

```bash
# Check health
curl https://qdrant.thinkube.com/health

# List collections
curl https://qdrant.thinkube.com/collections

# Create a collection
curl -X PUT https://qdrant.thinkube.com/collections/my_collection \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 768,
      "distance": "Cosine"
    }
  }'

# Insert vectors
curl -X PUT https://qdrant.thinkube.com/collections/my_collection/points \
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
curl -X POST https://qdrant.thinkube.com/collections/my_collection/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, ..., 0.768],
    "limit": 10
  }'
```

### gRPC API

The gRPC API is available at `qdrant.thinkube.com:6334` for high-performance applications.

## Access

Once deployed, Qdrant is available at:
- **Dashboard**: `https://qdrant-dashboard.thinkube.com`
- **REST API**: `https://qdrant.thinkube.com`
- **gRPC API**: `qdrant.thinkube.com:6334`

## Troubleshooting

### Check Pod Status
```bash
kubectl -n qdrant get pods
kubectl -n qdrant describe pod <pod-name>
```

### View Logs
```bash
kubectl -n qdrant logs deployment/qdrant
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
    url="https://qdrant.thinkube.com",
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
    url: 'https://qdrant.thinkube.com',
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
- **MinIO** (CORE-007) - For model and data storage
- **Argo Workflows** (CORE-010) - For ML pipeline orchestration
- **Harbor** (CORE-005) - For ML container images

---
*Component of the Thinkube Platform - Optional Services*