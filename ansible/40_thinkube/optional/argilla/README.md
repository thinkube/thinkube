# Argilla - AI Data Annotation Platform

Component #44 in the Thinkube Platform stack.

## Overview

Argilla is an open-source data annotation and curation platform for AI projects. It provides collaborative annotation tools for NLP and LLM tasks, enabling teams to create high-quality training datasets, collect human feedback, and implement active learning workflows. In the Thinkube Platform, Argilla serves as the data labeling infrastructure for supervised learning, RLHF (Reinforcement Learning from Human Feedback), and dataset quality improvement.

**Key Features**:
- Multi-task annotation (text classification, NER, question answering, ranking)
- Human feedback collection for LLM outputs
- Active learning workflows with model-in-the-loop
- Dataset versioning and management
- Collaboration tools with user roles and workspaces
- Python SDK for programmatic dataset creation
- Integration with Hugging Face, spaCy, and major NLP frameworks

## Dependencies

Argilla requires the following Thinkube components:

- **Keycloak (#15)** - OIDC authentication for web interface and API
- **OpenSearch (#35)** - Primary backend for dataset storage and search
- **Valkey (#36)** - Redis-compatible caching for session management and task queues

## Prerequisites

```yaml
kubernetes:
  distribution: k8s-snap
  version: "1.34.0"

core_components:
  - name: keycloak
    realm: thinkube
    status: configured
  - name: opensearch
    version: "2.x"
    ssl_enabled: true
    status: running
  - name: valkey
    version: "8.x"
    status: running

harbor:
  image: library/argilla:latest
  access: required
```

## Playbooks

Deployment is automatically orchestrated by thinkube-control via [00_install.yaml](00_install.yaml:20-27).

### **Configure Keycloak OIDC** - [10_configure_keycloak.yaml](10_configure_keycloak.yaml)

Creates Keycloak OIDC client for Argilla authentication using the standardized `keycloak_setup` role. Argilla uses custom OAuth2 provider integration with OIDC endpoint configuration.

**Client Configuration**:
- Client ID: `argilla`
- Protocol: `openid-connect`
- Flow: Standard flow + direct access grants
- Public client: `false` (confidential)
- Redirect URIs: `/oauth/keycloak/callback`, wildcard
- Default scopes: `email`, `profile`, `openid`, `offline_access`
- Access token lifespan: 3600s
- No custom roles (Argilla manages permissions internally via workspaces and user roles)

**Kubernetes Secret**: Client ID and secret stored in `argilla-oauth-secret` in `argilla` namespace.

### **Deploy Argilla** - [11_deploy.yaml](11_deploy.yaml)

Deploys Argilla with OpenSearch backend, Valkey cache, and Keycloak OIDC authentication.

**Step 1: Namespace and Variable Verification** (lines 43-59)
- Creates `argilla` namespace
- Verifies required inventory variables (domain, kubeconfig, Harbor registry, admin credentials)

**Step 2: API Key Generation** (lines 61-81)
- Generates random API key with format `argilla.apikey.<32-chars>`
- Creates `argilla-secrets` Kubernetes secret with:
  - `ARGILLA_API_KEY`: Generated API key for SDK/API access
  - `DEFAULT_USER_ENABLED`: `true` (creates default admin user)
  - `DEFAULT_USER_USERNAME`: Admin username from inventory
  - `DEFAULT_USER_PASSWORD`: Admin password from environment
  - `DEFAULT_USER_API_KEY`: Same as `ARGILLA_API_KEY`

**Step 3: OpenSearch Service Discovery** (lines 83-91)
- Queries Kubernetes for `opensearch-cluster-master` service in `opensearch` namespace
- Validates OpenSearch is deployed and accessible

**Step 4: Deployment** (lines 93-180)
- Init container: Waits for OpenSearch on port 9200 (busybox netcat)
- Main container: Argilla latest from Harbor
  - Port 6900 (HTTP API and web interface)
  - Search engine: `opensearch`
  - OpenSearch connection: HTTPS with basic auth (`admin:<password>`), SSL verification disabled
  - Valkey connection: `redis://valkey.valkey.svc.cluster.local:6379/0` (database 0)
  - Home path: `/var/lib/argilla` (internal data directory)
  - OAuth configuration: Mounted from ConfigMap at `/app/.oauth.yml`
  - Environment from secrets: `USERNAME`, `PASSWORD`, `API_KEY`
  - Keycloak OIDC endpoint: `https://auth.example.com/realms/thinkube`
  - Probes: `/api/status` endpoint (60s liveness initial delay, 30s readiness)
  - Resources: 250m-1 CPU, 512Mi-2Gi memory

**Step 5: Service** (lines 182-198)
- ClusterIP service on port 6900
- Internal-only (no external LoadBalancer)

**Step 6: TLS Certificate** (lines 200-223)
- Copies wildcard TLS certificate from `default` namespace
- Creates `argilla-tls-secret` in `argilla` namespace

**Step 7: OAuth Configuration** (lines 225-255)
- Retrieves OAuth client credentials from `argilla-oauth-secret`
- Creates `.oauth.yml` ConfigMap with Keycloak provider configuration:
  - Provider name: `keycloak`
  - Client ID and secret from Keycloak setup

**Step 8: Ingress** (lines 257-286)
- NGINX ingress with TLS
- Hostname: `argilla.example.com`
- Annotations: 100m max body size (for large dataset uploads)
- Path: `/` (all routes to Argilla service port 6900)

**Step 9: Readiness Check and CLI Configuration** (lines 288-333)
- Waits for deployment to have all replicas ready (30 retries, 10s delay)
- Creates config template at `/tmp/argilla-config.yaml`
- Copies to code-server pod at `/home/thinkube/.argilla/config.yaml`
- Sets permissions to 600
- Displays access information: URL, admin username/password, API key

### **Configure Service Discovery** - [17_configure_discovery.yaml](17_configure_discovery.yaml)

Registers Argilla with thinkube-control service discovery system.

**Metadata Extraction** (lines 38-51)
- Reads `argilla-secrets` Kubernetes secret
- Extracts `ARGILLA_API_KEY` for environment injection

**ConfigMap Creation** (lines 53-116)
- Name: `thinkube-service-config` in `argilla` namespace
- Labels: `thinkube.io/managed`, `thinkube.io/service-type: optional`, `thinkube.io/service-name: argilla`
- Service metadata:
  - Display name: "Argilla"
  - Description: "Data annotation and curation platform for AI"
  - Category: `ai`
  - Icon: `/icons/tk_design.svg`
  - Primary endpoint: Dashboard (`https://argilla.example.com`)
  - API endpoint: `/api`
  - Health URL: `/api/status`
  - Dependencies: `opensearch`, `valkey`
  - Scaling: Deployment `argilla`, min 1 replica, can disable
  - Authentication: `jwt_oidc`, OIDC client ID `argilla`
  - Features: Data annotation, dataset curation, active learning, human feedback collection
  - Environment variables: `ARGILLA_API_URL`, `ARGILLA_API_KEY`

**Environment Update** (line 133): Updates code-server environment with Argilla API URL and key via `code_server_env_update` role.

## Deployment

Automatically deployed via thinkube-control Optional Components interface at https://thinkube.example.com/optional-components.

The web interface provides:
- One-click deployment with real-time progress monitoring
- Automatic dependency verification (Keycloak, OpenSearch, Valkey)
- WebSocket-based log streaming during installation
- Health check validation post-deployment
- Rollback capability if deployment fails

## Access Points

### Web Interface

**URL**: https://argilla.example.com

**Authentication**: Keycloak SSO (OAuth2/OIDC)

**Login Methods**:
1. **OAuth Login**: Click "Login with Keycloak" → redirects to Keycloak → SSO authentication
2. **Direct Login**: Use default admin credentials (username/password from inventory)

**Features**:
- Dataset browser and explorer
- Annotation workspaces with task-specific interfaces
- User and workspace management
- Dataset settings and configuration
- Metrics and progress tracking dashboards

### API Endpoints

**Base URL**: https://argilla.example.com/api

**Authentication**: API key via `X-Argilla-API-Key` header

**Key Endpoints**:
- Health: `/api/status`
- Datasets: `/api/v1/datasets`
- Records: `/api/v1/datasets/{dataset_id}/records`
- Users: `/api/v1/users`
- Workspaces: `/api/v1/workspaces`

## Configuration

### Backend Storage

**OpenSearch**:
```bash
# Service: opensearch-cluster-master.opensearch.svc.cluster.local:9200
# Protocol: HTTPS
# Authentication: Basic auth (admin user)
# SSL Verification: Disabled (internal cluster trust)
# Data: All datasets, records, annotations, and metadata
```

**Valkey (Redis-compatible)**:
```bash
# Service: valkey.valkey.svc.cluster.local:6379
# Database: 0
# Purpose: Session caching, task queue, real-time updates
# Authentication: None (internal cluster traffic)
```

### OAuth Configuration

Argilla uses a YAML-based OAuth configuration mounted from ConfigMap:

```yaml
# /app/.oauth.yml
providers:
  - name: keycloak
    client_id: argilla
    client_secret: <from-secret>
```

Environment variable points to config file:
```bash
ARGILLA_AUTH_OAUTH_CFG=/app/.oauth.yml
SOCIAL_AUTH_KEYCLOAK_OIDC_ENDPOINT=https://auth.example.com/realms/thinkube
```

### Default User

```yaml
Username: admin  # From inventory
Password: <ADMIN_PASSWORD>  # From environment variable
API Key: argilla.apikey.<32-random-chars>
Role: Owner (full permissions)
```

The default user is automatically created on first startup when `DEFAULT_USER_ENABLED=true`.

### Resource Limits

```yaml
Deployment:
  Replicas: 1
  Resources:
    Requests:
      CPU: 250m
      Memory: 512Mi
    Limits:
      CPU: 1
      Memory: 2Gi
```

## Usage

### Python SDK

```python
import argilla as rg

# Initialize client
rg.init(
    api_url="https://argilla.example.com",
    api_key="argilla.apikey.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)

# Create a text classification dataset
dataset = rg.FeedbackDataset(
    fields=[
        rg.TextField(name="text", title="Text to classify")
    ],
    questions=[
        rg.LabelQuestion(
            name="sentiment",
            title="What is the sentiment?",
            labels=["positive", "negative", "neutral"]
        )
    ]
)

# Add records
records = [
    rg.FeedbackRecord(
        fields={"text": "This product is amazing!"},
        suggestions=[{"question_name": "sentiment", "value": "positive"}]
    ),
    rg.FeedbackRecord(
        fields={"text": "Terrible experience, very disappointed."},
        suggestions=[{"question_name": "sentiment", "value": "negative"}]
    )
]

dataset.add_records(records)
dataset.push_to_argilla(name="sentiment-analysis", workspace="demo")
```

### Text Classification Workflow

```python
import argilla as rg
from transformers import pipeline

# Initialize Argilla
rg.init(api_url="https://argilla.example.com", api_key="<api-key>")

# Load a pre-trained model for suggestions
classifier = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# Prepare records with model suggestions
texts = [
    "This movie was fantastic!",
    "Worst film I've ever seen.",
    "It was okay, nothing special."
]

records = []
for text in texts:
    prediction = classifier(text)[0]
    record = rg.FeedbackRecord(
        fields={"text": text},
        suggestions=[{
            "question_name": "sentiment",
            "value": prediction["label"],
            "score": prediction["score"]
        }]
    )
    records.append(record)

# Push to Argilla for human review
dataset = rg.FeedbackDataset.from_argilla("sentiment-review", workspace="nlp")
dataset.add_records(records)
```

### Named Entity Recognition (NER)

```python
import argilla as rg

rg.init(api_url="https://argilla.example.com", api_key="<api-key>")

# Create NER dataset
dataset = rg.FeedbackDataset(
    fields=[
        rg.TextField(name="text", title="Text for NER annotation")
    ],
    questions=[
        rg.SpanQuestion(
            name="entities",
            title="Select named entities",
            labels=["PERSON", "ORG", "LOC", "DATE"]
        )
    ]
)

# Add records
records = [
    rg.FeedbackRecord(
        fields={"text": "Elon Musk founded Tesla in California in 2003."}
    )
]

dataset.add_records(records)
dataset.push_to_argilla(name="ner-annotation", workspace="nlp")
```

### LLM Human Feedback Collection

```python
import argilla as rg

rg.init(api_url="https://argilla.example.com", api_key="<api-key>")

# Create dataset for LLM output evaluation
dataset = rg.FeedbackDataset(
    fields=[
        rg.TextField(name="prompt", title="User prompt"),
        rg.TextField(name="response", title="LLM response")
    ],
    questions=[
        rg.RatingQuestion(
            name="quality",
            title="Rate response quality",
            values=[1, 2, 3, 4, 5]
        ),
        rg.MultiLabelQuestion(
            name="issues",
            title="Select any issues",
            labels=["factual_error", "toxic", "off_topic", "incomplete"]
        ),
        rg.TextQuestion(
            name="feedback",
            title="Provide detailed feedback"
        )
    ]
)

# Add LLM outputs for review
llm_interactions = [
    {
        "prompt": "Explain quantum entanglement",
        "response": "Quantum entanglement is a phenomenon where particles..."
    }
]

records = [
    rg.FeedbackRecord(fields=interaction)
    for interaction in llm_interactions
]

dataset.add_records(records)
dataset.push_to_argilla(name="llm-feedback", workspace="ai-quality")
```

### Active Learning Loop

```python
import argilla as rg
from sklearn.linear_model import LogisticRegression
from transformers import AutoTokenizer, AutoModel

rg.init(api_url="https://argilla.example.com", api_key="<api-key>")

# Fetch annotated records
dataset = rg.FeedbackDataset.from_argilla("sentiment-analysis", workspace="nlp")
annotated = [rec for rec in dataset if rec.responses]

# Train model on annotated data
# (simplified - actual implementation would use embeddings)
X_train = [rec.fields["text"] for rec in annotated]
y_train = [rec.responses[0].values["sentiment"].value for rec in annotated]

model = LogisticRegression()
# ... feature extraction and training ...

# Predict on unannotated data
unannotated = [rec for rec in dataset if not rec.responses]
predictions = model.predict_proba([rec.fields["text"] for rec in unannotated])

# Select uncertain samples (low confidence)
uncertain_indices = [i for i, pred in enumerate(predictions) if max(pred) < 0.7]

# Push uncertain samples back for annotation
uncertain_records = [unannotated[i] for i in uncertain_indices]
dataset.add_records(uncertain_records)
```

## Integration

### With Hugging Face Hub

```python
import argilla as rg
from datasets import load_dataset

rg.init(api_url="https://argilla.example.com", api_key="<api-key>")

# Load dataset from Hugging Face
hf_dataset = load_dataset("imdb", split="train[:100]")

# Convert to Argilla format
records = [
    rg.FeedbackRecord(
        fields={
            "text": item["text"],
            "original_label": item["label"]
        }
    )
    for item in hf_dataset
]

# Push to Argilla for verification/correction
dataset = rg.FeedbackDataset(
    fields=[
        rg.TextField(name="text"),
        rg.TextField(name="original_label")
    ],
    questions=[
        rg.LabelQuestion(
            name="verified_label",
            labels=["positive", "negative"]
        )
    ]
)
dataset.add_records(records)
dataset.push_to_argilla(name="imdb-verification", workspace="nlp")

# After annotation, push back to Hub
verified_dataset = rg.FeedbackDataset.from_argilla("imdb-verification", workspace="nlp")
verified_dataset.push_to_huggingface(repo_id="org/imdb-verified")
```

### With spaCy

```python
import argilla as rg
import spacy
from spacy.training import Example

rg.init(api_url="https://argilla.example.com", api_key="<api-key>")

# Fetch NER annotations from Argilla
dataset = rg.FeedbackDataset.from_argilla("ner-annotation", workspace="nlp")

# Convert to spaCy training format
nlp = spacy.blank("en")
ner = nlp.add_pipe("ner")

training_data = []
for record in dataset:
    if record.responses:
        text = record.fields["text"]
        entities = record.responses[0].values["entities"].value

        # Convert Argilla span format to spaCy format
        ents = [(span["start"], span["end"], span["label"]) for span in entities]
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, {"entities": ents})
        training_data.append(example)

# Train spaCy model
nlp.begin_training()
for epoch in range(10):
    for example in training_data:
        nlp.update([example])
```

### With LangChain for RLHF

```python
import argilla as rg
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

rg.init(api_url="https://argilla.example.com", api_key="<api-key>")

# Generate LLM responses
llm = ChatOpenAI(model="gpt-4")
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{question}")
])

questions = [
    "What is machine learning?",
    "Explain neural networks.",
    "How does backpropagation work?"
]

# Collect responses for human feedback
records = []
for question in questions:
    response = llm.invoke(prompt_template.format(question=question))

    record = rg.FeedbackRecord(
        fields={
            "prompt": question,
            "response": response.content
        }
    )
    records.append(record)

# Push to Argilla for RLHF annotation
dataset = rg.FeedbackDataset.from_argilla("rlhf-feedback", workspace="ai-quality")
dataset.add_records(records)

# Retrieve feedback after annotation
annotated_dataset = rg.FeedbackDataset.from_argilla("rlhf-feedback", workspace="ai-quality")
for record in annotated_dataset:
    if record.responses:
        quality_rating = record.responses[0].values["quality"].value
        feedback_text = record.responses[0].values["feedback"].value
        # Use feedback for model fine-tuning or prompt engineering
```

## Monitoring

### Health Checks

```bash
# Application health
curl https://argilla.example.com/api/status

# Expected response
{"status":"ok"}
```

```bash
# Pod status
kubectl get pods -n argilla

# Check readiness
kubectl get pods -n argilla -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}'
```

### Logs

```bash
# Main application logs
kubectl logs -n argilla deployment/argilla -f

# Filter for errors
kubectl logs -n argilla deployment/argilla | grep -E "(ERROR|CRITICAL)"

# Init container logs (OpenSearch wait)
kubectl logs -n argilla deployment/argilla -c wait-for-opensearch
```

### Backend Connectivity

```bash
# Check OpenSearch connection
kubectl exec -n argilla deployment/argilla -- curl -sk https://admin:password@opensearch-cluster-master.opensearch.svc.cluster.local:9200

# Check Valkey connection
kubectl exec -n argilla deployment/argilla -- sh -c 'nc -zv valkey.valkey.svc.cluster.local 6379'
```

### Dataset Statistics

```python
import argilla as rg

rg.init(api_url="https://argilla.example.com", api_key="<api-key>")

# List all datasets
datasets = rg.list_datasets()
for dataset_name in datasets:
    dataset = rg.FeedbackDataset.from_argilla(dataset_name)

    total_records = len(dataset)
    annotated = len([r for r in dataset if r.responses])
    pending = total_records - annotated

    print(f"Dataset: {dataset_name}")
    print(f"  Total: {total_records}, Annotated: {annotated}, Pending: {pending}")
```

## Troubleshooting

### OpenSearch Connection Failures

**Symptom**: Pods fail to start or crash with OpenSearch connection errors

```bash
# Check init container logs
kubectl logs -n argilla deployment/argilla -c wait-for-opensearch

# Check OpenSearch service
kubectl get svc -n opensearch opensearch-cluster-master
```

**Fix**: Verify OpenSearch is running and accessible
```bash
# Test OpenSearch connectivity from within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl -sk https://admin:password@opensearch-cluster-master.opensearch.svc.cluster.local:9200

# Check OpenSearch health
kubectl exec -n opensearch statefulset/opensearch-cluster-master -- \
  curl -sk https://admin:password@localhost:9200/_cluster/health
```

### OAuth/OIDC Login Failures

**Symptom**: Unable to login via Keycloak SSO

```bash
# Check OAuth secret
kubectl get secret -n argilla argilla-oauth-secret -o yaml

# Verify OAuth ConfigMap
kubectl get configmap -n argilla argilla-oauth-config -o yaml
```

**Fix**: Verify Keycloak client configuration
```bash
# Get Keycloak admin token
ADMIN_TOKEN=$(curl -s -X POST "https://auth.example.com/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" | jq -r '.access_token')

# Check client redirect URIs
curl -s "https://auth.example.com/admin/realms/thinkube/clients?clientId=argilla" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[0].redirectUris'
```

### API Key Authentication Issues

**Symptom**: API calls return 401 Unauthorized

```bash
# Verify API key in secret
kubectl get secret -n argilla argilla-secrets -o jsonpath='{.data.ARGILLA_API_KEY}' | base64 -d
```

**Fix**: Use correct API key format
```python
# Correct format
api_key = "argilla.apikey.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Test API key
import requests
response = requests.get(
    "https://argilla.example.com/api/status",
    headers={"X-Argilla-API-Key": api_key}
)
print(response.status_code)  # Should be 200
```

### Slow Dataset Loading

**Symptom**: Web interface or API slow when loading large datasets

```bash
# Check OpenSearch query performance
kubectl exec -n opensearch statefulset/opensearch-cluster-master -- \
  curl -sk https://admin:password@localhost:9200/_nodes/stats/indices/search

# Check Argilla memory usage
kubectl top pods -n argilla
```

**Fix**: Increase resources for large datasets
```bash
# Scale up memory limits
kubectl patch deployment -n argilla argilla -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "argilla",
          "resources": {
            "limits": {
              "memory": "4Gi"
            },
            "requests": {
              "memory": "1Gi"
            }
          }
        }]
      }
    }
  }
}'
```

### Dataset Import Failures

**Symptom**: Large dataset uploads fail with 413 or timeout errors

```bash
# Check ingress body size limit
kubectl get ingress -n argilla argilla-dashboard -o jsonpath='{.metadata.annotations}'
```

**Fix**: Increase body size limit for large uploads
```bash
# Patch ingress annotation
kubectl patch ingress -n argilla argilla-dashboard -p '
{
  "metadata": {
    "annotations": {
      "nginx.ingress.kubernetes.io/proxy-body-size": "500m",
      "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
      "nginx.ingress.kubernetes.io/proxy-send-timeout": "300"
    }
  }
}'
```

## Testing

Tests are defined in [18_test.yaml](18_test.yaml):

```bash
# Run test playbook
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/argilla/18_test.yaml
```

**Test Coverage**:
- Health endpoint responds 200
- OpenSearch backend connectivity
- Valkey cache connectivity
- Keycloak OIDC authentication flow
- API key authentication
- Dataset creation via API
- Record ingestion via SDK
- Annotation workflow via UI

## Rollback

Rollback is defined in [19_rollback.yaml](19_rollback.yaml):

```bash
# Rollback Argilla deployment
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/argilla/19_rollback.yaml
```

**Rollback Actions**:
- Deletes Argilla deployment, service, ingress
- Removes `argilla` namespace
- Deletes Keycloak `argilla` client
- **Preserves** OpenSearch indices (data retention - datasets and annotations remain)
- **Does not affect** Valkey (shared cache, no Argilla-specific data persistence)
- Removes service discovery ConfigMap
- Updates code-server environment to remove Argilla variables

**Note**: OpenSearch index preservation allows re-deployment without data loss. Manual cleanup required if full data deletion is desired.

## References

- **Official Documentation**: https://docs.argilla.io
- **GitHub Repository**: https://github.com/argilla-io/argilla
- **Python SDK**: https://docs.argilla.io/latest/reference/python-sdk/
- **Tutorials**: https://docs.argilla.io/latest/tutorials/
- **Hugging Face Integration**: https://docs.argilla.io/latest/how-to-guides/huggingface/
- **Active Learning**: https://docs.argilla.io/latest/how-to-guides/active-learning/
- **Dataset Management**: https://docs.argilla.io/latest/how-to-guides/dataset/
- **API Reference**: https://docs.argilla.io/latest/reference/api-reference/

🤖 [AI-assisted]
