# Langfuse - LLM Observability Platform

## Overview

Langfuse is an open-source LLM engineering platform for tracing, evaluating, and monitoring LLM applications. It provides observability into production LLM applications with detailed trace analysis, cost tracking, and performance metrics.

## Features

- **LLM Tracing**: Detailed traces for LLM calls with input/output logging
- **Cost Tracking**: Monitor API costs across different LLM providers
- **Performance Metrics**: Latency, token usage, and error rates
- **Prompt Management**: Version control for prompts and templates
- **User Feedback**: Collect and analyze user feedback on generations
- **Dataset Management**: Create and manage evaluation datasets
- **Integration**: Works with LangChain, LlamaIndex, and custom applications

## Architecture

### Components

- **Web Application**: Next.js application (port 3000)
- **PostgreSQL Database**: Persistent storage for traces and metadata
- **Keycloak OIDC**: Single sign-on authentication

### Storage

- **PostgreSQL**: Stores all traces, prompts, datasets, and user data
- **No additional storage**: All data in PostgreSQL

## Deployment

### Prerequisites

- Kubernetes (k8s-snap) cluster running
- PostgreSQL deployed (core component)
- Keycloak deployed (core component)
- Harbor registry with Langfuse image

### Install

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/langfuse/00_install.yaml
```

### Test

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/langfuse/18_test.yaml
```

### Rollback

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/langfuse/19_rollback.yaml
```

## Usage

### Access Langfuse

URL: `https://langfuse.thinkube.com`
Authentication: Keycloak SSO

### Python SDK Example

```python
from langfuse import Langfuse

# Initialize Langfuse client
langfuse = Langfuse(
    public_key="your-public-key",
    secret_key="your-secret-key",
    host="https://langfuse.thinkube.com"
)

# Create a trace
trace = langfuse.trace(name="llm-call")

# Log an LLM generation
generation = trace.generation(
    name="openai-completion",
    model="gpt-4",
    input={"messages": [{"role": "user", "content": "Hello"}]},
    output={"content": "Hi there!"},
    usage={"promptTokens": 10, "completionTokens": 5}
)
```

### LangChain Integration

```python
from langchain.callbacks import LangfuseCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain

# Initialize callback handler
langfuse_handler = LangfuseCallbackHandler(
    public_key="your-public-key",
    secret_key="your-secret-key",
    host="https://langfuse.thinkube.com"
)

# Use with LangChain
llm = ChatOpenAI()
chain = LLMChain(llm=llm, callbacks=[langfuse_handler])
chain.run("Tell me a joke")
```

### LlamaIndex Integration

```python
from llama_index.callbacks import CallbackManager, LangfuseCallbackHandler
from llama_index import VectorStoreIndex

# Initialize callback handler
langfuse_handler = LangfuseCallbackHandler(
    public_key="your-public-key",
    secret_key="your-secret-key",
    host="https://langfuse.thinkube.com"
)

# Use with LlamaIndex
callback_manager = CallbackManager([langfuse_handler])
index = VectorStoreIndex.from_documents(documents, callback_manager=callback_manager)
```

## Integration with Thinkube Services

Langfuse integrates with other Thinkube AI services:

### With NATS
```python
# Subscribe to LLM events from NATS and log to Langfuse
import nats
from langfuse import Langfuse

async def log_llm_event(msg):
    data = json.loads(msg.data.decode())
    langfuse.trace(
        name=data['operation'],
        input=data['input'],
        output=data['output']
    )

nc = await nats.connect("nats://nats.nats.svc.cluster.local:4222")
await nc.subscribe("llm.events", cb=log_llm_event)
```

### With LiteLLM
```python
# LiteLLM automatically logs to Langfuse if configured
import litellm

litellm.success_callback = ["langfuse"]
litellm.set_verbose = True

response = litellm.completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    metadata={
        "langfuse_public_key": "your-public-key",
        "langfuse_secret_key": "your-secret-key",
        "langfuse_host": "https://langfuse.thinkube.com"
    }
)
```

### With MLflow
```python
# Log Langfuse trace IDs to MLflow experiments
import mlflow
from langfuse import Langfuse

with mlflow.start_run():
    trace = langfuse.trace(name="model-training")
    mlflow.log_param("langfuse_trace_id", trace.id)
    # ... training code ...
```

## API Keys

Generate API keys in the Langfuse UI:
1. Navigate to Settings → API Keys
2. Create new public/secret key pair
3. Use in your applications

**Note**: API keys are scoped to projects. Create separate keys for different environments.

## Monitoring

### Health Check

```bash
curl https://langfuse.thinkube.com/api/public/health
```

### Check Pod Status

```bash
kubectl get pods -n langfuse
```

### View Logs

```bash
kubectl logs -n langfuse deployment/langfuse -f
```

### Database Connection

Langfuse automatically runs migrations on startup. Check logs for migration status.

## Troubleshooting

### Database Connection Issues

Check PostgreSQL connectivity:
```bash
kubectl exec -n langfuse deployment/langfuse -- env | grep DATABASE_URL
```

### OIDC Authentication Issues

Verify Keycloak client configuration:
```bash
kubectl get secret -n langfuse langfuse-oauth-secret -o yaml
```

### Slow Performance

Langfuse performance depends on trace volume:
- Small projects (< 100K traces): Single replica sufficient
- Large projects: Scale horizontally with multiple replicas

## Use Cases

### Development & Testing
- Debug LLM application behavior
- Analyze prompt performance
- Track costs during development
- A/B test different prompts

### Production Monitoring
- Real-time observability of LLM calls
- Cost tracking and optimization
- Error monitoring and alerts
- User feedback collection

### Evaluation & Testing
- Create evaluation datasets from production traces
- Run evaluations on prompt versions
- Compare model performance

## Resources

- **Official Documentation**: https://langfuse.com/docs
- **GitHub Repository**: https://github.com/langfuse/langfuse
- **Python SDK**: https://pypi.org/project/langfuse/
- **LangChain Integration**: https://langfuse.com/docs/integrations/langchain
- **LlamaIndex Integration**: https://langfuse.com/docs/integrations/llama-index

## License

Langfuse is MIT licensed, compatible with Thinkube.

🤖 [AI-assisted]
