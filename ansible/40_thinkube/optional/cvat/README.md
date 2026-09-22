# CVAT - Computer Vision Annotation Tool

Component #45 in the Thinkube Platform stack.

## Installation

CVAT is an optional component. It is installed and removed from the Optional Components page in thinkube-control, not on its own. thinkube-control runs `00_install.yaml` to install, `18_test.yaml` to test and `19_rollback.yaml` to remove it. It runs on amd64 nodes only.

## Overview

CVAT (Computer Vision Annotation Tool) is an open-source web-based annotation platform for computer vision tasks. It provides advanced labeling capabilities for images and videos, supporting object detection, semantic segmentation, instance segmentation, and keypoint annotation. In the Thinkube Platform, CVAT serves as the primary annotation infrastructure for computer vision datasets, enabling teams to create high-quality training data for deep learning models with AI-assisted labeling, automated tracking, and collaborative workflows.

**Key Features**:
- Multi-format annotation (bounding boxes, polygons, polylines, points, cuboids)
- Video annotation with interpolation and tracking
- AI-assisted labeling with automatic annotation and semi-automatic modes
- Collaborative annotation with user roles and task management
- Support for 40+ import/export formats (COCO, YOLO, Pascal VOC, CVAT, Datumaro, etc.)
- Python SDK and CLI for programmatic dataset management
- Integration with popular deep learning frameworks and annotation tools

## Dependencies

CVAT requires the following Thinkube components:

- **PostgreSQL (#14)** - Primary database for projects, tasks, jobs, annotations metadata
- **Keycloak (#15)** - OAuth2/OIDC authentication for web interface (via OAuth2 Proxy)
- **ClickHouse (#34)** - Analytics database for usage statistics and metrics
- **Valkey (#36)** - Redis-compatible caching for task queues, session storage, and real-time updates

## Prerequisites

```yaml
kubernetes:
  distribution: kubeadm

core_components:
  - name: postgresql
    version: "18"
    status: running
  - name: keycloak
    realm: thinkube
    status: configured
  - name: clickhouse
    version: "24.x"
    status: running
  - name: valkey
    version: "8.x"
    status: running

harbor:
  images:
    - library/cvat-server:latest
    - library/cvat-ui:latest
    - library/opa:0.63.0
  access: required
```

## Playbooks

| Playbook | What it does |
|---|---|
| [00_install.yaml](00_install.yaml) | Runs `10_deploy.yaml`, then `17_configure_discovery.yaml`. |
| [10_deploy.yaml](10_deploy.yaml) | Creates the `cvat` namespace, secrets, four PVCs and the `cvat` database; deploys the backend, UI and OPA with their services; copies the wildcard certificate; deploys an ephemeral Valkey and OAuth2 Proxy; creates the HTTPRoutes `cvat-api-route` (`/api`) and `cvat-main-route` (`/`, `/static`, `/django-rq`); writes the CLI config to `/home/thinkube/.cvat/config.yaml` in the code-server pod. |
| [17_configure_discovery.yaml](17_configure_discovery.yaml) | Creates the `thinkube-service-config` ConfigMap in `cvat` for thinkube-control (endpoints, dependencies `postgresql`, `valkey`, `clickhouse`, variables `CVAT_API_URL`, `CVAT_USERNAME`, `CVAT_PASSWORD`) and updates the code-server environment. |
| [18_test.yaml](18_test.yaml) | Test playbook. Its tasks check the LiteLLM deployment, not CVAT (see Testing). |
| [19_rollback.yaml](19_rollback.yaml) | Deletes the `cvat` namespace and the `cvat` Keycloak client. |

Pods run with the node selector that thinkube-control passes as `component_node_selector` (`kubernetes.io/arch: amd64`).

## Deployment

Automatically deployed via thinkube-control Optional Components interface at https://thinkube.example.com/optional-components.

The web interface provides:
- One-click deployment with real-time progress monitoring
- Automatic dependency verification (PostgreSQL, Keycloak, ClickHouse, Valkey)
- WebSocket-based log streaming during installation
- Health check validation post-deployment
- Rollback capability if deployment fails

CVAT is listed on the Optional Components page. The CVAT images are built for amd64 only. thinkube-control offers the install only when the cluster has an amd64 node, and pins the CVAT pods to amd64 nodes.

## Access Points

### Web Interface

**URL**: https://cvat.example.com

**Authentication**: Keycloak SSO (OAuth2 Proxy)

**Login Flow**:
1. Navigate to https://cvat.example.com
2. OAuth2 Proxy redirects to Keycloak login
3. After SSO authentication, redirected back to CVAT UI
4. Session stored in ephemeral Valkey via secure cookie

**Features**:
- Project and task management dashboard
- Annotation workspace with advanced labeling tools
- Job assignment and tracking
- Dataset import/export
- AI model integration for auto-annotation
- Analytics and metrics dashboards

### API Endpoints

**Base URL**: https://cvat.example.com/api

**Authentication**: Basic auth (username/password) - OAuth2 NOT required for API

**Key Endpoints**:
- Server info: `/api/server/about`
- Projects: `/api/projects`
- Tasks: `/api/tasks`
- Jobs: `/api/jobs`
- Annotations: `/api/tasks/{id}/annotations`
- Users: `/api/users`

**Python SDK**:
```python
from cvat_sdk import make_client

client = make_client(
    host="https://cvat.example.com",
    credentials=("admin", "password")
)
```

**CLI**:
```bash
cvat-cli --auth admin:password --server-host cvat.example.com
```

## Configuration

### Backend Storage

**PostgreSQL**:
```bash
# Database: cvat
# Connection: postgresql-official.postgres.svc.cluster.local:5432
# Schema: Auto-migrated on startup
# Data: Projects, tasks, jobs, annotations metadata, users, organizations
```

**PersistentVolumes**:
```yaml
cvat-data-pvc: 20Gi
  # Annotation data, uploaded images/videos, intermediate results

cvat-keys-pvc: 1Gi
  # SSH keys for git repository integration

cvat-logs-pvc: 5Gi
  # Application logs, Django logs, task execution logs

cvat-models-pvc: 10Gi
  # AI model weights for automatic annotation (YOLO, Mask R-CNN, etc.)
```

**ClickHouse**:
```bash
# Service: clickhouse-clickhouse.clickhouse.svc.cluster.local:8123
# Protocol: HTTP
# Authentication: Basic auth (default user)
# Data: Analytics events, usage statistics, performance metrics
# Enabled via: CVAT_ANALYTICS=1
```

**Valkey (Core)**:
```bash
# Service: valkey.valkey.svc.cluster.local:6379
# Connections:
#   - CVAT_REDIS_HOST: General cache (task metadata, temporary data)
#   - CVAT_REDIS_INMEM_HOST: Fast in-memory cache (session data, real-time updates)
#   - CVAT_REDIS_ONDISK_HOST: Persistent cache (job queues, long-term data)
# Note: All three point to same Valkey instance (different logical databases)
```

**Valkey (Ephemeral - OAuth2 Sessions)**:
```bash
# Service: ephemeral-valkey.cvat.svc.cluster.local
# Purpose: OAuth2 Proxy session storage
# Isolation: Separate from core Valkey to avoid session/cache conflicts
```

### OAuth2 Proxy Integration

CVAT uses custom Django middleware to integrate with OAuth2 Proxy:

**Middleware** (`cvat-oauth2-middleware` ConfigMap):
- `OAuth2ProxyRemoteUserMiddleware`: Extracts user from `X-Auth-Request-User` header
- `OAuth2ProxyRemoteUserBackend`: Django authentication backend for remote user

**Settings Overlay** (`cvat-django-settings-overlay` ConfigMap):
```python
# Extended from base settings
MIDDLEWARE += ['cvat.apps.thinkube_auth.middleware.OAuth2ProxyRemoteUserMiddleware']
AUTHENTICATION_BACKENDS += ['cvat.apps.thinkube_auth.middleware.OAuth2ProxyRemoteUserBackend']
```

**HTTP routes** (Gateway API):
- `/api/*`: Direct to backend (NO OAuth2 - basic auth for CLI/SDK)
- `/`, `/static`, `/django-rq`: OAuth2 Proxy protected (SSO required)

### OPA Authorization

CVAT uses Open Policy Agent for fine-grained access control:

```yaml
Bundle Configuration:
  Service: cvat-backend:8080
  Resource: /api/auth/rules
  Polling: 5-15 seconds
  Persistence: true (bundle caching in /.opa)

Port: 8181
Policy Endpoint: /v1/data/cvat/allow
```

Django backend queries OPA for authorization decisions on all protected resources.

### Resource Limits

```yaml
cvat-backend:
  Replicas: 1
  Resources:
    Requests:
      CPU: 250m
      Memory: 512Mi
    Limits:
      CPU: 1
      Memory: 2Gi

cvat-ui:
  Replicas: 1
  Resources:
    Requests:
      CPU: 100m
      Memory: 128Mi
    Limits:
      CPU: 200m
      Memory: 512Mi

opa:
  Replicas: 1
  Resources:
    Requests:
      CPU: 100m
      Memory: 128Mi
    Limits:
      CPU: 200m
      Memory: 256Mi
```

## Usage

### Python SDK

```python
from cvat_sdk import make_client, models
from PIL import Image

# Initialize client
client = make_client(
    host="https://cvat.example.com",
    credentials=("admin", "password")
)

# Create a project
project = client.projects.create(
    models.ProjectWriteRequest(
        name="Self-Driving Car Dataset",
        labels=[
            models.PatchedLabelRequest(
                name="car",
                color="#FF0000"
            ),
            models.PatchedLabelRequest(
                name="pedestrian",
                color="#00FF00"
            ),
            models.PatchedLabelRequest(
                name="traffic_light",
                color="#0000FF"
            )
        ]
    )
)

# Create a task
task = client.tasks.create(
    models.TaskWriteRequest(
        name="Highway Scenes - Batch 1",
        project_id=project.id,
        labels=project.labels
    )
)

# Upload images
image_paths = ["img_001.jpg", "img_002.jpg", "img_003.jpg"]
client.tasks.create_from_data(
    task.id,
    resources=[open(p, "rb") for p in image_paths],
    image_quality=95
)

# Get annotations (after manual annotation)
annotations = client.tasks.retrieve_annotations(task.id)
for shape in annotations.shapes:
    print(f"Label: {shape.label_id}, BBox: {shape.points}")
```

### Image Annotation Workflow

```python
from cvat_sdk import make_client, models

client = make_client(host="https://cvat.example.com", credentials=("admin", "password"))

# Create task for object detection
task = client.tasks.create(
    models.TaskWriteRequest(
        name="Object Detection - Retail Products",
        labels=[
            models.PatchedLabelRequest(name="bottle", color="#FF0000"),
            models.PatchedLabelRequest(name="can", color="#00FF00"),
            models.PatchedLabelRequest(name="box", color="#0000FF")
        ]
    )
)

# Upload images
client.tasks.create_from_data(
    task.id,
    resources=[open(f"product_{i:03d}.jpg", "rb") for i in range(1, 101)]
)

# Annotate via UI at: https://cvat.example.com/tasks/{task.id}
# Or use automatic annotation with a model:

# Upload annotations programmatically
annotations = models.LabeledDataRequest(
    shapes=[
        models.LabeledShapeRequest(
            type="rectangle",
            frame=0,
            label_id=1,
            points=[100, 100, 200, 200],  # x1, y1, x2, y2
            attributes=[]
        )
    ]
)
client.tasks.update_annotations(task.id, annotations)
```

### Video Annotation with Interpolation

```python
from cvat_sdk import make_client, models

client = make_client(host="https://cvat.example.com", credentials=("admin", "password"))

# Create task for video annotation
task = client.tasks.create(
    models.TaskWriteRequest(
        name="Traffic Video Analysis",
        labels=[
            models.PatchedLabelRequest(name="vehicle", color="#FF0000")
        ]
    )
)

# Upload video
client.tasks.create_from_data(
    task.id,
    resources=[open("traffic.mp4", "rb")],
    use_cache=True
)

# Create tracked annotation with interpolation
track = models.TrackedShapeRequest(
    type="rectangle",
    frame=0,
    label_id=1,
    shapes=[
        models.TrackedShapeRequest.ShapeRequest(
            frame=0,
            points=[50, 50, 150, 150],
            outside=False
        ),
        models.TrackedShapeRequest.ShapeRequest(
            frame=10,
            points=[100, 75, 200, 175],
            outside=False
        ),
        models.TrackedShapeRequest.ShapeRequest(
            frame=20,
            points=[150, 100, 250, 200],
            outside=True  # Object exits frame
        )
    ]
)

# CVAT automatically interpolates intermediate frames
annotations = models.LabeledDataRequest(tracks=[track])
client.tasks.update_annotations(task.id, annotations)
```

### Export Annotations

```python
from cvat_sdk import make_client

client = make_client(host="https://cvat.example.com", credentials=("admin", "password"))

# Export in COCO format
coco_export = client.tasks.retrieve_dataset(
    task_id=123,
    format="COCO 1.0"
)

with open("annotations.json", "wb") as f:
    f.write(coco_export.read())

# Export in YOLO format
yolo_export = client.tasks.retrieve_dataset(
    task_id=123,
    format="YOLO 1.1"
)

# Extract to directory
import zipfile
with zipfile.ZipFile(io.BytesIO(yolo_export.read())) as z:
    z.extractall("yolo_dataset/")
```

### CLI Usage

```bash
# Configure CLI
cvat-cli --auth admin:password --server-host cvat.example.com

# Create task
cvat-cli create task \
  --name "Road Signs Dataset" \
  --labels '[{"name":"stop","attributes":[]},{"name":"yield","attributes":[]}]' \
  --project_id 1

# Upload images
cvat-cli create data 123 \
  --image_quality 95 \
  images/*.jpg

# Download annotations
cvat-cli dump 123 \
  --format "COCO 1.0" \
  --filename annotations.zip

# Auto-annotate with model
cvat-cli auto-annotate 123 \
  --function-file /path/to/detector.py
```

## Integration

### With PyTorch/Detectron2

```python
from cvat_sdk import make_client
import torch
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2 import model_zoo

client = make_client(host="https://cvat.example.com", credentials=("admin", "password"))

# Load pre-trained Mask R-CNN model
cfg = get_cfg()
cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
predictor = DefaultPredictor(cfg)

# Auto-annotate CVAT task
task = client.tasks.retrieve(123)
for frame in range(task.size):
    image = client.tasks.retrieve_frame(task.id, frame)
    outputs = predictor(image)

    # Convert predictions to CVAT format
    shapes = []
    for i, box in enumerate(outputs["instances"].pred_boxes):
        shapes.append({
            "type": "rectangle",
            "frame": frame,
            "label_id": int(outputs["instances"].pred_classes[i]) + 1,
            "points": box.tolist(),
            "attributes": []
        })

    # Upload annotations
    client.tasks.update_annotations(task.id, {"shapes": shapes})
```

### With YOLO for Auto-Annotation

```python
from cvat_sdk import make_client
from ultralytics import YOLO

client = make_client(host="https://cvat.example.com", credentials=("admin", "password"))

# Load YOLOv8 model
model = YOLO("yolov8n.pt")

task = client.tasks.retrieve(456)
for frame_idx in range(task.size):
    image_data = client.tasks.retrieve_frame(task.id, frame_idx)

    # Run inference
    results = model(image_data)[0]

    # Convert to CVAT annotations
    shapes = []
    for box in results.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        shapes.append({
            "type": "rectangle",
            "frame": frame_idx,
            "label_id": int(box.cls) + 1,
            "points": [x1, y1, x2, y2],
            "attributes": []
        })

    client.tasks.update_annotations(task.id, {"shapes": shapes})
```

### With Hugging Face Datasets

```python
from cvat_sdk import make_client
from datasets import load_dataset

client = make_client(host="https://cvat.example.com", credentials=("admin", "password"))

# Load dataset from Hugging Face
hf_dataset = load_dataset("detection-datasets/coco", split="train[:100]")

# Create CVAT task
task = client.tasks.create({
    "name": "COCO Subset Verification",
    "labels": [{"name": cat["name"]} for cat in hf_dataset.features["objects"].feature["category"].names]
})

# Upload images and annotations
for item in hf_dataset:
    # Upload image
    image_data = item["image"]
    # ... upload logic ...

    # Convert annotations
    shapes = []
    for obj in item["objects"]:
        bbox = obj["bbox"]  # [x, y, width, height]
        shapes.append({
            "type": "rectangle",
            "label_id": obj["category"] + 1,
            "points": [bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]]
        })

    client.tasks.update_annotations(task.id, {"shapes": shapes})
```

## Monitoring

### Health Checks

```bash
# Application health (internal)
kubectl exec -n cvat deployment/cvat-backend -- curl -s http://localhost:8080/api/server/about

# Expected response
{"name":"CVAT","description":"...","version":"..."}
```

```bash
# Pod status
kubectl get pods -n cvat

# Check all components
kubectl get pods -n cvat -o wide
# Should show: cvat-backend, cvat-ui, opa, oauth2-proxy, ephemeral-valkey
```

### Logs

```bash
# Backend logs
kubectl logs -n cvat deployment/cvat-backend -f

# UI logs
kubectl logs -n cvat deployment/cvat-ui -f

# OPA logs
kubectl logs -n cvat deployment/opa -f

# OAuth2 Proxy logs
kubectl logs -n cvat deployment/oauth2-proxy -f

# Init container logs (superuser creation)
kubectl logs -n cvat deployment/cvat-backend -c create-superuser
```

### Backend Connectivity

```bash
# Check PostgreSQL connection
kubectl exec -n cvat deployment/cvat-backend -- env | grep CVAT_POSTGRES

# Test connection
kubectl exec -n cvat deployment/cvat-backend -- sh -c 'nc -zv $CVAT_POSTGRES_HOST $CVAT_POSTGRES_PORT'

# Check Valkey connection
kubectl exec -n cvat deployment/cvat-backend -- sh -c 'nc -zv valkey.valkey.svc.cluster.local 6379'

# Check ClickHouse connection
kubectl exec -n cvat deployment/cvat-backend -- curl -s http://clickhouse-clickhouse.clickhouse.svc.cluster.local:8123/ping
```

### Task and Annotation Statistics

```python
from cvat_sdk import make_client

client = make_client(host="https://cvat.example.com", credentials=("admin", "password"))

# List all tasks
tasks = client.tasks.list()
for task in tasks:
    annotations = client.tasks.retrieve_annotations(task.id)

    total_shapes = len(annotations.shapes)
    total_tracks = len(annotations.tracks)

    print(f"Task: {task.name}")
    print(f"  Shapes: {total_shapes}, Tracks: {total_tracks}")
    print(f"  Status: {task.status}, Progress: {task.progress}%")
```

## Troubleshooting

### Database Migration Failures

**Symptom**: Backend pods crash on startup with migration errors

```bash
# Check create-superuser init container logs
kubectl logs -n cvat deployment/cvat-backend -c create-superuser

# Check backend logs for migration errors
kubectl logs -n cvat deployment/cvat-backend | grep -i migration
```

**Fix**: Ensure PostgreSQL is accessible and database exists
```bash
# Verify PostgreSQL connectivity
kubectl exec -n cvat deployment/cvat-backend -- nc -zv postgresql-official.postgres.svc.cluster.local 5432

# Check if database exists
kubectl exec -n postgres statefulset/postgresql-official -- psql -U admin -l | grep cvat

# Manual migration (if needed)
kubectl exec -n cvat deployment/cvat-backend -- python manage.py migrate
```

### OAuth2 Authentication Failures

**Symptom**: Infinite redirect loop or 401 errors on login

```bash
# Check OAuth2 Proxy logs
kubectl logs -n cvat deployment/oauth2-proxy -f

# Verify cookie configuration
kubectl get deployment -n cvat oauth2-proxy -o yaml | grep -A 5 cookie
```

**Fix**: Verify OAuth2 Proxy and Keycloak configuration
```bash
# Check OAuth2 Proxy secret
kubectl get secret -n cvat oauth2-proxy-secret -o yaml

# Verify Keycloak client
ADMIN_TOKEN=$(curl -s -X POST "https://auth.example.com/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" | jq -r '.access_token')

curl -s "https://auth.example.com/admin/realms/thinkube/clients?clientId=cvat" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[0].redirectUris'
```

### CLI Basic Auth Failures

**Symptom**: cvat-cli returns 401 Unauthorized

```bash
# The API route must send /api straight to cvat-backend, not through OAuth2 Proxy
kubectl get httproute -n cvat cvat-api-route -o jsonpath='{.spec.rules[*].matches[*].path.value} -> {.spec.rules[*].backendRefs[*].name}'
# Should show: /api -> cvat-backend
```

**Fix**: Check that the backend accepts basic auth
```bash

# Test API access directly
curl -u admin:password https://cvat.example.com/api/server/about
```

### OPA Authorization Errors

**Symptom**: 403 Forbidden on authorized actions

```bash
# Check OPA logs
kubectl logs -n cvat deployment/opa | grep -i error

# Test OPA policy endpoint
kubectl exec -n cvat deployment/opa -- curl -s http://localhost:8181/v1/data/cvat/allow
```

**Fix**: Verify OPA bundle synchronization
```bash
# Check OPA bundle status
kubectl exec -n cvat deployment/opa -- curl -s http://localhost:8181/v1/status

# Restart OPA to refresh bundle
kubectl rollout restart deployment/opa -n cvat
```

### Video Upload Failures

**Symptom**: Large video uploads timeout or fail

```bash
# Check the request timeout on the routes (10_deploy.yaml sets 1200s)
kubectl get httproute -n cvat cvat-api-route cvat-main-route -o jsonpath='{range .items[*]}{.metadata.name}: {.spec.rules[*].timeouts.request}{"\n"}{end}'
```

**Fix**: Raise `timeouts.request` on the HTTPRoutes in `10_deploy.yaml` and reinstall CVAT from the Optional Components page.

### Storage Full Errors

**Symptom**: PVC full errors, annotation save failures

```bash
# Check PVC usage
kubectl exec -n cvat deployment/cvat-backend -- df -h /home/django/data

# List PVCs
kubectl get pvc -n cvat
```

**Fix**: Expand PVC or clean up old data
```bash
# Expand PVC (if storage class supports it)
kubectl patch pvc cvat-data-pvc -n cvat -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'

# Or delete old tasks via API
from cvat_sdk import make_client
client = make_client(host="https://cvat.example.com", credentials=("admin", "password"))
old_tasks = [t for t in client.tasks.list() if t.updated_date < "2024-01-01"]
for task in old_tasks:
    client.tasks.destroy(task.id)
```

## Testing

thinkube-control runs [18_test.yaml](18_test.yaml) as the CVAT test playbook.

The file is a copy of the LiteLLM test playbook. Its tasks check the `litellm` namespace, deployment, service, HTTPRoute and API. They do not test CVAT.

## Rollback

thinkube-control runs [19_rollback.yaml](19_rollback.yaml) when CVAT is removed from the Optional Components page.

**Rollback Actions**:
- Deletes the `cvat` namespace. This removes everything in it: deployments, services, HTTPRoutes, the service discovery ConfigMap, the ephemeral Valkey and the four PVCs.
- Deletes the Keycloak `cvat` client.
- **Keeps** the PostgreSQL `cvat` database (projects, tasks, annotation metadata).
- **Keeps** ClickHouse analytics data and core Valkey.
- Does not remove the CVAT variables from the code-server environment.

**Note**: The PVCs are deleted with the namespace, so uploaded images, videos and models are lost. Drop the `cvat` database by hand if a full cleanup is needed.

## References

- **Official Documentation**: https://docs.cvat.ai
- **GitHub Repository**: https://github.com/cvat-ai/cvat
- **Python SDK**: https://github.com/cvat-ai/cvat/tree/develop/cvat-sdk
- **CLI Documentation**: https://docs.cvat.ai/docs/manual/advanced/cli/
- **Annotation Formats**: https://docs.cvat.ai/docs/manual/advanced/formats/
- **REST API**: https://docs.cvat.ai/docs/api_sdk/api/
- **Video Tutorial**: https://www.youtube.com/c/CVAT-ai
- **Auto-Annotation**: https://docs.cvat.ai/docs/manual/advanced/ai-tools/

🤖 [AI-assisted]
