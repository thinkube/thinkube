# Chroma Vector Database Component

## Overview

Chroma is an open-source embedding database designed to make it easy to build LLM applications by storing, embedding, and searching through embeddings and their metadata. It provides a simple API for adding, updating, and querying vector embeddings.

## Features

- **Vector Storage**: Store embeddings with associated metadata and documents
- **Similarity Search**: Find similar vectors using various distance metrics
- **Collections**: Organize embeddings into collections with custom metadata
- **Filtering**: Query embeddings with metadata filters
- **REST API**: Simple HTTP API for all operations
- **Persistent Storage**: Data persists across restarts
- **Token Authentication**: Secure API access with token-based auth
- **Multi-modal**: Support for text and other embedding types

## Architecture

- **Deployment Type**: StatefulSet (single replica)
- **Persistence**: PersistentVolumeClaim for data storage
- **Authentication**: Token-based authentication using admin credentials
- **Networking**: Exposed via Ingress at `chroma.<domain>`
- **Namespace**: `chroma`

## Installation

### Prerequisites

- MicroK8s cluster with ingress controller
- DNS configured for the domain
- `ADMIN_PASSWORD` environment variable set

### Deploy Chroma

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/chroma/00_install.yaml
```

This will:
1. Create the `chroma` namespace
2. Deploy Chroma with token authentication
3. Configure persistent storage
4. Set up ingress for HTTPS access
5. Register with service discovery

### Verify Installation

```bash
# Run the test playbook
./scripts/run_ansible.sh ansible/40_thinkube/optional/chroma/18_test.yaml

# Check pod status
kubectl -n chroma get pods

# Check service status
kubectl -n chroma get svc
```

## Usage

### API Authentication

All API requests require authentication using the admin password in the `X-Chroma-Token` header:

```bash
# Set your admin password
export ADMIN_PASSWORD="your-admin-password"

# Example API call
curl -H "X-Chroma-Token: ${ADMIN_PASSWORD}" \
     https://chroma.<domain>/api/v1/collections
```

### Python Client Example

```python
import chromadb
from chromadb.config import Settings

# Create client with authentication
client = chromadb.HttpClient(
    host="chroma.<domain>",
    port=443,
    ssl=True,
    headers={"X-Chroma-Token": "your-admin-password"},
    settings=Settings(anonymized_telemetry=False)
)

# Check heartbeat
print(client.heartbeat())

# Create a collection
collection = client.create_collection(
    name="my_collection",
    metadata={"description": "My test collection"}
)

# Add documents with embeddings
collection.add(
    documents=["This is document 1", "This is document 2"],
    metadatas=[{"source": "doc1"}, {"source": "doc2"}],
    ids=["id1", "id2"]
)

# Query the collection
results = collection.query(
    query_texts=["This is a query"],
    n_results=2
)
print(results)
```

### REST API Examples

#### Create a Collection

```bash
curl -X POST https://chroma.<domain>/api/v1/collections \
  -H "X-Chroma-Token: ${ADMIN_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_collection",
    "metadata": {"description": "Test collection"}
  }'
```

#### Add Embeddings

```bash
curl -X POST https://chroma.<domain>/api/v1/collections/my_collection/add \
  -H "X-Chroma-Token: ${ADMIN_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "ids": ["id1", "id2"],
    "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
    "metadatas": [{"type": "doc"}, {"type": "doc"}],
    "documents": ["Document 1", "Document 2"]
  }'
```

#### Query Embeddings

```bash
curl -X POST https://chroma.<domain>/api/v1/collections/my_collection/query \
  -H "X-Chroma-Token: ${ADMIN_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "query_embeddings": [[0.1, 0.2, 0.3]],
    "n_results": 2
  }'
```

## Configuration

### Environment Variables

The deployment sets the following key environment variables:

- `CHROMA_SERVER_AUTH_CREDENTIALS_PROVIDER`: Token authentication provider
- `CHROMA_SERVER_AUTH_PROVIDER`: Token auth server provider
- `CHROMA_SERVER_AUTH_TOKEN_TRANSPORT_HEADER`: `X_CHROMA_TOKEN`
- `IS_PERSISTENT`: `True`
- `PERSIST_DIRECTORY`: `/chroma/chroma`
- `ANONYMIZED_TELEMETRY`: `False`
- `CHROMA_SERVER_CORS_ALLOW_ORIGINS`: `["*"]`

### Storage

- **PVC Size**: 10Gi (configurable in playbook)
- **Storage Class**: `microk8s-hostpath`
- **Mount Path**: `/chroma/chroma`

### Resource Limits

- **Memory**: 512Mi (request) / 2Gi (limit)
- **CPU**: 250m (request) / 1 (limit)

## Maintenance

### Backup Data

Since Chroma uses a PersistentVolumeClaim, data persists across pod restarts. For backups:

```bash
# Create a backup pod to access the PVC
kubectl -n chroma run backup --image=busybox --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"backup","image":"busybox","command":["sleep","3600"],"volumeMounts":[{"name":"data","mountPath":"/data"}]}],"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"chroma-data-pvc"}}]}}'

# Copy data out
kubectl -n chroma cp backup:/data ./chroma-backup

# Clean up
kubectl -n chroma delete pod backup
```

### Update Chroma

To update the Chroma version:

1. Edit the `chroma_image` variable in `10_deploy.yaml`
2. Re-run the deployment playbook
3. Verify with the test playbook

### Rollback

To remove Chroma while preserving data:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/chroma/19_rollback.yaml
```

To completely remove Chroma including data:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/chroma/19_rollback.yaml -e remove_data=true
```

## Troubleshooting

### Check Logs

```bash
# View Chroma logs
kubectl -n chroma logs statefulset/chroma

# Follow logs
kubectl -n chroma logs -f statefulset/chroma
```

### Common Issues

1. **Authentication Errors**: Ensure `ADMIN_PASSWORD` is set and used in `X-Chroma-Token` header
2. **Connection Refused**: Check ingress and DNS configuration
3. **Out of Memory**: Increase memory limits in the deployment
4. **Data Loss**: Ensure PVC is not deleted during rollback
5. **CORS Issues**: The deployment allows all origins by default

### Health Checks

```bash
# Check heartbeat
curl https://chroma.<domain>/api/v1/heartbeat

# Check version
curl -H "X-Chroma-Token: ${ADMIN_PASSWORD}" \
     https://chroma.<domain>/api/v1/version

# List collections
curl -H "X-Chroma-Token: ${ADMIN_PASSWORD}" \
     https://chroma.<domain>/api/v1/collections
```

## Integration

### With AI/ML Frameworks

Chroma integrates well with:
- LangChain for RAG applications
- LlamaIndex for document processing
- OpenAI embeddings
- Hugging Face models
- Custom embedding models

### Example with LangChain

```python
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# Initialize Chroma with LangChain
vectorstore = Chroma(
    client=client,
    collection_name="langchain_collection",
    embedding_function=OpenAIEmbeddings()
)

# Add documents
vectorstore.add_texts(
    texts=["Document 1", "Document 2"],
    metadatas=[{"source": "file1"}, {"source": "file2"}]
)

# Similarity search
results = vectorstore.similarity_search("query text", k=2)
```

### Service Discovery

Chroma registers with thinkube-control for service discovery:
- **Category**: AI
- **Type**: Optional
- **Primary Endpoint**: `https://chroma.<domain>`
- **Health Endpoint**: `https://chroma.<domain>/api/v1/heartbeat`

## License

Chroma is licensed under the Apache 2.0 License.

## Support

- [Official Documentation](https://docs.trychroma.com/)
- [GitHub Repository](https://github.com/chroma-core/chroma)
- [Discord Community](https://discord.gg/chroma)

## 🤖 AI-assisted

This component was configured with AI assistance.