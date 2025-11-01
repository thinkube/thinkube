# NATS - Real-time Messaging System

## Overview

NATS is a high-performance messaging system for cloud-native applications and microservices. This deployment includes JetStream for persistent messaging and stream processing.

## Features

- **High Performance**: Low-latency pub/sub messaging
- **JetStream**: Persistent messaging with stream processing
- **Cluster Mode**: 3-node cluster for high availability
- **RAFT Consensus**: Distributed state management
- **Multiple Protocols**: Core NATS, JetStream, Key/Value, Object Store

## Architecture

### Components

- **NATS Server**: Core messaging server (single replica for homelab)
- **JetStream**: Persistent storage layer (10Gi)
- **Monitoring**: Built-in monitoring endpoint on port 8222
- **nats-box**: CLI tool for testing and management

### Ports

- **4222**: Client connections (NATS protocol)
- **6222**: Cluster routing (node-to-node)
- **8222**: HTTP monitoring and metrics

### Storage

JetStream uses persistent volumes for message storage:
- 10Gi persistent volume
- Survives pod restarts
- Single replica (suitable for homelab)

## Deployment

### Prerequisites

- Kubernetes (k8s-snap) cluster running
- Helm installed
- Harbor registry with NATS images

### Install

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/nats/00_install.yaml
```

### Test

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/nats/18_test.yaml
```

### Rollback

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/nats/19_rollback.yaml
```

## Usage

### Service Endpoint

Internal cluster endpoint:
```
nats://nats.nats.svc.cluster.local:4222
```

### Basic Pub/Sub Example

From within the cluster:

```bash
# Subscribe to a subject
nats sub test.subject --server=nats://nats.nats.svc.cluster.local:4222

# Publish a message
nats pub test.subject "Hello World" --server=nats://nats.nats.svc.cluster.local:4222
```

### JetStream Example

Create a stream:
```bash
nats stream add MY_STREAM \
  --subjects="events.>" \
  --storage=file \
  --replicas=1 \
  --server=nats://nats.nats.svc.cluster.local:4222
```

Publish to stream:
```bash
nats pub events.user.login '{"user":"alice"}' \
  --server=nats://nats.nats.svc.cluster.local:4222
```

Create consumer:
```bash
nats consumer add MY_STREAM MY_CONSUMER \
  --filter="events.user.>" \
  --deliver=all \
  --server=nats://nats.nats.svc.cluster.local:4222
```

### Python Example

```python
import asyncio
from nats.aio.client import Client as NATS

async def main():
    nc = NATS()
    await nc.connect("nats://nats.nats.svc.cluster.local:4222")

    # Simple pub/sub
    await nc.publish("test", b"Hello World")

    # JetStream
    js = nc.jetstream()
    await js.publish("events.user.login", b'{"user":"alice"}')

    await nc.close()

if __name__ == '__main__':
    asyncio.run(main())
```

### Using from JupyterHub Notebooks

```python
# Install NATS client
!pip install nats-py

import nats
from nats.errors import TimeoutError

async def example():
    # Connect to NATS
    nc = await nats.connect("nats://nats.nats.svc.cluster.local:4222")

    # Publish messages
    await nc.publish("ai.inference.request", b'{"model":"gpt-4"}')

    # Subscribe to responses
    async def message_handler(msg):
        print(f"Received: {msg.data.decode()}")

    await nc.subscribe("ai.inference.response", cb=message_handler)

    # Keep connection alive
    await asyncio.sleep(60)
    await nc.close()

# Run in notebook
await example()
```

## Integration with Thinkube Services

NATS enables real-time communication between AI services:

### Agent Coordination
```python
# Agent 1 publishes task
await nc.publish("agents.tasks", b'{"task":"analyze","data":"..."}')

# Agent 2 subscribes to tasks
await nc.subscribe("agents.tasks", cb=process_task)
```

### LLM Observability (Langfuse)
```python
# Publish LLM events to Langfuse via NATS
await nc.publish("llm.traces", langfuse_trace_json)
```

### Real-time Model Updates
```python
# Notify when MLflow registers new model
await nc.publish("mlflow.model.registered", model_metadata)
```

### Multi-Agent Systems
```python
# Agents communicate via NATS topics
await nc.publish("agents.chat", agent_message)
await nc.subscribe("agents.chat", cb=handle_agent_message)
```

## Monitoring

### Health Check

```bash
curl http://nats.nats.svc.cluster.local:8222/healthz
```

### Monitoring Endpoint

```bash
curl http://nats.nats.svc.cluster.local:8222/varz
```

### Check Cluster Status

```bash
kubectl exec -n nats nats-0 -- nats server info
```

### JetStream Info

```bash
kubectl exec -n nats nats-0 -- nats account info
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n nats
```

### View Logs

```bash
kubectl logs -n nats nats-0 -f
```

### Check JetStream Storage

```bash
kubectl exec -n nats nats-0 -- df -h /data
```

### Test Connectivity

```bash
kubectl run -i --rm --restart=Never nats-test \
  --image=harbor.example.com/library/nats-box:0.14.5 \
  --namespace=nats \
  -- nats pub test "hello" --server=nats://nats:4222
```

## Use Cases

### Real-time AI Pipelines
- Stream data preprocessing
- Model inference queues
- Result aggregation

### Agent Systems
- Multi-agent coordination
- Message passing between agents
- Task distribution

### Event-Driven ML
- Model retraining triggers
- Data drift alerts
- Performance monitoring

### Microservices Communication
- Service-to-service messaging
- Event sourcing
- CQRS patterns

## Performance

- **Throughput**: Millions of messages per second
- **Latency**: Sub-millisecond delivery
- **Scalability**: Horizontal scaling via clustering
- **Persistence**: JetStream provides at-least-once delivery

## Security

Currently deployed without authentication for internal cluster use. For production:
- Enable TLS encryption
- Configure user authentication
- Implement authorization with accounts

## Resources

- **Official Documentation**: https://docs.nats.io/
- **Helm Chart**: https://github.com/nats-io/k8s
- **JetStream Guide**: https://docs.nats.io/nats-concepts/jetstream
- **Client Libraries**: https://nats.io/download/

## License

NATS is Apache 2.0 licensed, compatible with Thinkube.

🤖 [AI-assisted]