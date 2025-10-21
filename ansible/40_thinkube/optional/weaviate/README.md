# Weaviate Vector Database Component

## Overview

Weaviate is an open-source vector database designed for AI applications. It provides vector search capabilities, allowing you to store and query data objects and their vector representations efficiently.

## Features

- **Vector Search**: Semantic search using vector embeddings
- **Hybrid Search**: Combine vector and keyword search
- **GraphQL & REST APIs**: Flexible query interfaces
- **Schema Management**: Define data models with properties and relationships
- **Scalability**: Designed to handle billions of vectors
- **Module System**: Extensible with vectorization and other modules
- **CRUD Operations**: Full support for Create, Read, Update, Delete
- **Authentication**: API key-based authentication with admin user

## Architecture

- **Deployment Type**: StatefulSet (single replica)
- **Persistence**: PersistentVolumeClaim for data storage
- **Authentication**: API key authentication using admin credentials
- **Networking**: Exposed via Ingress at `weaviate.<domain>`
- **Namespace**: `weaviate`

## Installation

### Prerequisites

- MicroK8s cluster with ingress controller
- DNS configured for the domain
- `ADMIN_PASSWORD` environment variable set

### Deploy Weaviate

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/weaviate/00_install.yaml
```

This will:
1. Create the `weaviate` namespace
2. Deploy Weaviate with API key authentication
3. Configure persistent storage
4. Set up ingress for HTTPS access
5. Register with service discovery

### Verify Installation

```bash
# Run the test playbook
./scripts/run_ansible.sh ansible/40_thinkube/optional/weaviate/18_test.yaml

# Check pod status
kubectl -n weaviate get pods

# Check service status
kubectl -n weaviate get svc
```

## Usage

### API Authentication

All API requests require authentication using the admin password as a Bearer token:

```bash
# Set your admin password
export ADMIN_PASSWORD="your-admin-password"

# Example API call
curl -H "Authorization: Bearer ${ADMIN_PASSWORD}" \
     https://weaviate.<domain>/v1/schema
```

### Python Client Example

```python
import weaviate

client = weaviate.Client(
    url="https://weaviate.<domain>",
    auth_client_secret=weaviate.AuthApiKey(api_key="your-admin-password")
)

# Check if Weaviate is ready
print(client.is_ready())

# Create a schema
schema = {
    "class": "Article",
    "properties": [
        {
            "name": "title",
            "dataType": ["text"]
        },
        {
            "name": "content",
            "dataType": ["text"]
        }
    ]
}
client.schema.create_class(schema)

# Add data
client.data_object.create(
    {
        "title": "Introduction to Weaviate",
        "content": "Weaviate is a vector database..."
    },
    "Article"
)
```

### GraphQL Example

```bash
curl -X POST https://weaviate.<domain>/v1/graphql \
  -H "Authorization: Bearer ${ADMIN_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{
      Get {
        Article {
          title
          content
        }
      }
    }"
  }'
```

## Configuration

### Environment Variables

The deployment sets the following key environment variables:

- `AUTHENTICATION_APIKEY_ENABLED`: `true`
- `AUTHORIZATION_ADMINLIST_ENABLED`: `true`
- `AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED`: `false`
- `DEFAULT_VECTORIZER_MODULE`: `none` (can be changed if needed)
- `PERSISTENCE_DATA_PATH`: `/var/lib/weaviate`

### Storage

- **PVC Size**: 10Gi (configurable in playbook)
- **Storage Class**: `microk8s-hostpath`
- **Mount Path**: `/var/lib/weaviate`

### Resource Limits

- **Memory**: 512Mi (request) / 2Gi (limit)
- **CPU**: 250m (request) / 1 (limit)

## Maintenance

### Backup Data

Since Weaviate uses a PersistentVolumeClaim, data persists across pod restarts. For backups:

```bash
# Create a backup pod to access the PVC
kubectl -n weaviate run backup --image=busybox --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"backup","image":"busybox","command":["sleep","3600"],"volumeMounts":[{"name":"data","mountPath":"/data"}]}],"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"weaviate-data-pvc"}}]}}'

# Copy data out
kubectl -n weaviate cp backup:/data ./weaviate-backup

# Clean up
kubectl -n weaviate delete pod backup
```

### Update Weaviate

To update the Weaviate version:

1. Edit the `weaviate_image` variable in `10_deploy.yaml`
2. Re-run the deployment playbook
3. Verify with the test playbook

### Rollback

To remove Weaviate while preserving data:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/weaviate/19_rollback.yaml
```

To completely remove Weaviate including data:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/weaviate/19_rollback.yaml -e remove_data=true
```

## Troubleshooting

### Check Logs

```bash
# View Weaviate logs
kubectl -n weaviate logs statefulset/weaviate

# Follow logs
kubectl -n weaviate logs -f statefulset/weaviate
```

### Common Issues

1. **Authentication Errors**: Ensure `ADMIN_PASSWORD` is set correctly
2. **Connection Refused**: Check ingress and DNS configuration
3. **Out of Memory**: Increase memory limits in the deployment
4. **Data Loss**: Ensure PVC is not deleted during rollback

### Health Checks

```bash
# Check readiness
curl https://weaviate.<domain>/v1/.well-known/ready

# Check liveness
curl https://weaviate.<domain>/v1/.well-known/live

# Get OpenAPI spec
curl https://weaviate.<domain>/v1/.well-known/openapi
```

## Integration

### With AI/ML Frameworks

Weaviate integrates well with:
- LangChain for RAG applications
- OpenAI embeddings (requires configuration)
- Hugging Face models
- Custom vectorizers

### Service Discovery

Weaviate registers with thinkube-control for service discovery:
- **Category**: AI
- **Type**: Optional
- **Primary Endpoint**: `https://weaviate.<domain>`
- **GraphQL Endpoint**: `https://weaviate.<domain>/v1/graphql`

## License

Weaviate is licensed under the BSD 3-Clause License, which is compatible with Apache 2.0.

## Support

- [Official Documentation](https://weaviate.io/developers/weaviate)
- [GitHub Repository](https://github.com/weaviate/weaviate)
- [Community Forum](https://forum.weaviate.io/)

## 🤖 AI-assisted

This component was configured with AI assistance.