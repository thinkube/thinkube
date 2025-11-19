# CVAT - Computer Vision Annotation Tool

Component #45 in the Thinkube Platform stack.

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
  distribution: k8s-snap
  version: "1.34.0"

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

Deployment is automatically orchestrated by thinkube-control via [00_install.yaml](00_install.yaml:21-25).

### **Deploy CVAT** - [10_deploy.yaml](10_deploy.yaml)

Deploys CVAT with PostgreSQL backend, ClickHouse analytics, Valkey cache, OAuth2 Proxy authentication, and OPA (Open Policy Agent) authorization.

**Step 1: Namespace and Variable Verification** (lines 68-84)
- Creates `cvat` namespace
- Verifies required inventory variables (domain, kubeconfig, Harbor registry, admin credentials)

**Step 2: Secret Generation** (lines 86-108)
- Generates Django secret key (50 characters for session security)
- Creates `cvat-secrets` Kubernetes secret with:
  - `DJANGO_SUPERUSER_USERNAME`: Admin username from inventory
  - `DJANGO_SUPERUSER_PASSWORD`: Admin password from environment
  - `DJANGO_SUPERUSER_EMAIL`: `admin@<domain>`
  - `SECRET_KEY`: Django session encryption key
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: PostgreSQL credentials

**Step 3: Persistent Storage** (lines 110-130)
- Creates 4 PersistentVolumeClaims:
  - `cvat-data-pvc`: 20Gi (annotation data, images, videos)
  - `cvat-keys-pvc`: 1Gi (SSH keys for git integration)
  - `cvat-logs-pvc`: 5Gi (application logs)
  - `cvat-models-pvc`: 10Gi (AI model weights for auto-annotation)

**Step 4: Database Initialization** (lines 132-169)
- Creates one-shot pod `cvat-db-init` with postgres:18-alpine
- Runs PostgreSQL command to create `cvat` database if not exists
- Waits for pod to reach Succeeded state (30 retries, 5s delay)

**Step 5: Valkey Service Discovery** (lines 171-179)
- Queries Kubernetes for `valkey` service in `valkey` namespace
- Validates Valkey is deployed and accessible

**Step 6: CVAT Backend Deployment** (lines 181-413)
- Init containers (3 wait checks):
  - `wait-for-db`: PostgreSQL port 5432
  - `wait-for-valkey`: Valkey port 6379
  - `wait-for-clickhouse`: ClickHouse port 8123
  - `create-superuser`: Runs Django migrations, creates superuser if not exists
- Main container: `cvat-server:latest` from Harbor
  - Port 8080 (HTTP API and Django backend)
  - Command: `./backend_entrypoint.sh init run server`
  - Analytics enabled: `CVAT_ANALYTICS=1`
  - ClickHouse connection: HTTP port 8123, basic auth
  - PostgreSQL connection: `postgresql-official.postgres.svc.cluster.local:5432`
  - Valkey connections (3 separate endpoints for different use cases):
    - `CVAT_REDIS_HOST`: General cache
    - `CVAT_REDIS_INMEM_HOST`: In-memory cache for fast access
    - `CVAT_REDIS_ONDISK_HOST`: Persistent cache
  - Server config: `CVAT_SERVER_HOST=cvat.example.com`, `CVAT_HTTPS=1`
  - OAuth2 integration: Custom Django settings module `cvat.settings.thinkube_sso`
  - OPA integration: `IAM_OPA_BUNDLE=1`
  - Volume mounts:
    - 4 PVCs for data/keys/logs/models
    - OAuth2 middleware ConfigMap at `/home/django/cvat/apps/thinkube_auth`
    - Django settings overlay at `/home/django/cvat/settings/thinkube_sso.py`
  - Probes: `/api/server/about` endpoint (60s liveness initial delay, 15s readiness)
  - Resources: 250m-1 CPU, 512Mi-2Gi memory
  - Security context: `fsGroup: 1000` (Django user permissions)

**Step 7: OAuth2 Middleware ConfigMaps** (lines 415-443)
- Creates `cvat-oauth2-middleware` ConfigMap with:
  - `middleware.py`: OAuth2 Proxy RemoteUser middleware (from template)
  - `__init__.py`: Python package initialization
- Creates `cvat-django-settings-overlay` ConfigMap with Django settings extension (from template)

**Step 8: CVAT Backend Service** (lines 445-461)
- ClusterIP service on port 8080
- Selector: `app=cvat-backend`

**Step 9: OPA (Open Policy Agent) Deployment** (lines 463-530)
- Deployment with 1 replica
- Image: `opa:0.63.0` from Harbor
- Configuration:
  - Server mode with error-level logging
  - CVAT service: `http://cvat-backend:8080`
  - Bundle polling: 5-15 seconds
  - Resource endpoint: `/api/auth/rules`
  - Persistence: `true` (bundle caching)
- Port 8181 (HTTP API)
- Resources: 100m-200m CPU, 128Mi-256Mi memory
- EmptyDir volume for OPA data persistence

**Step 10: OPA Service** (lines 514-530)
- ClusterIP service on port 8181

**Step 11: CVAT UI Deployment** (lines 532-582)
- Deployment with 1 replica
- Image: `cvat-ui:latest` from Harbor
- Port 8000 (static React frontend)
- Resources: 100m-200m CPU, 128Mi-512Mi memory

**Step 12: CVAT UI Service** (lines 566-582)
- ClusterIP service on port 80 → 8000

**Step 13: TLS Certificate** (lines 584-607)
- Copies wildcard TLS certificate from `default` namespace
- Creates `cvat-tls-secret` in `cvat` namespace

**Step 14: Ephemeral Valkey Deployment** (lines 609-613)
- Deploys ephemeral Valkey instance for OAuth2 Proxy sessions
- Uses `valkey/ephemeral_valkey` role
- Separate from core Valkey (session isolation)

**Step 15: OAuth2 Proxy Deployment** (lines 615-617)
- Deploys OAuth2 Proxy with Keycloak integration
- Uses `oauth2_proxy` role
- Configuration:
  - Client ID: `cvat`
  - OIDC issuer: `https://auth.example.com/realms/thinkube`
  - Cookie domain: `.example.com`
  - Redirect URL: `https://cvat.example.com/oauth2/callback`
  - Session store: Redis (ephemeral Valkey)
  - Cookie SameSite: `none` (cross-site compatibility)

**Step 16: API Ingress (No OAuth2)** (lines 619-653)
- NGINX ingress for `/api` path
- **NO OAuth2 authentication** (allows cvat-cli basic auth)
- Annotations:
  - Body size: 1024m (large video uploads)
  - Timeouts: 1200s (long-running annotation jobs)
  - Buffer size: 16k
- Backend: `cvat-backend:8080`
- TLS termination with wildcard certificate

**Step 17: Main Ingress (OAuth2 Protected)** (lines 655-705)
- NGINX ingress for `/`, `/static`, `/django-rq` paths
- OAuth2 Proxy annotations:
  - `auth-url`: `https://$host/oauth2/auth`
  - `auth-signin`: `https://$host/oauth2/start?rd=$escaped_request_uri`
  - Response headers: User, Email, Access-Token, Groups
- Backends:
  - `/static`, `/django-rq`: `cvat-backend:8080`
  - `/`: `cvat-ui:80`
- Annotations: Same body size and timeout as API ingress

**Step 18: Readiness Check and CLI Configuration** (lines 710-755)
- Waits for CVAT backend deployment to have all replicas ready (30 retries, 10s delay)
- Creates config template at `/tmp/cvat-config.yaml`
- Copies to code-server pod at `/home/thinkube/.cvat/config.yaml`
- Sets permissions to 600
- Displays access information: URL, admin username/password, SSO note, computer vision features

### **Configure Service Discovery** - [17_configure_discovery.yaml](17_configure_discovery.yaml)

Registers CVAT with thinkube-control service discovery system.

**Credentials Extraction** (lines 31-34)
- Retrieves admin username from inventory
- Retrieves admin password from `ADMIN_PASSWORD` environment variable

**ConfigMap Creation** (lines 43-111)
- Name: `thinkube-service-config` in `cvat` namespace
- Labels: `thinkube.io/managed`, `thinkube.io/service-type: optional`, `thinkube.io/service-name: cvat`
- Service metadata:
  - Display name: "CVAT"
  - Description: "Computer Vision Annotation Tool for image and video labeling"
  - Category: `ai`
  - Icon: `/icons/tk_design.svg`
  - Primary endpoint: Dashboard (`https://cvat.example.com`) - internal health check via backend
  - API endpoint: `/api`
  - Health URL: Internal service endpoint (not exposed externally)
  - Dependencies: `postgresql`, `valkey`, `clickhouse`
  - Scaling: Deployment `cvat-backend`, min 1 replica, can disable
  - Authentication: `jwt_oidc`, OIDC client ID `cvat`
  - Features: Image annotation, video annotation, object detection, semantic segmentation, AI-assisted labeling
  - Environment variables: `CVAT_API_URL`, `CVAT_USERNAME`, `CVAT_PASSWORD`

**Environment Update** (line 129): Updates code-server environment with CVAT API URL and credentials via `code_server_env_update` role.

## Deployment

Automatically deployed via thinkube-control Optional Components interface at https://thinkube.example.com/optional-components.

The web interface provides:
- One-click deployment with real-time progress monitoring
- Automatic dependency verification (PostgreSQL, Keycloak, ClickHouse, Valkey)
- WebSocket-based log streaming during installation
- Health check validation post-deployment
- Rollback capability if deployment fails

**Note**: CVAT is marked as hidden in v0.1.0 release but remains fully functional for early adopters.

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

**Ingress Routing**:
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
# Verify API ingress does NOT have OAuth2 annotations
kubectl get ingress -n cvat cvat-api-ingress -o yaml | grep -E "(auth-url|auth-signin)"
# Should return nothing
```

**Fix**: Ensure API ingress bypasses OAuth2
```bash
# Check ingress path routing
kubectl get ingress -n cvat cvat-api-ingress -o jsonpath='{.spec.rules[0].http.paths[*].path}'
# Should show: /api

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
# Check ingress body size limit
kubectl get ingress -n cvat cvat-api-ingress -o jsonpath='{.metadata.annotations}'
```

**Fix**: Increase timeouts and body size
```bash
# Patch ingress annotations
kubectl patch ingress -n cvat cvat-api-ingress -p '
{
  "metadata": {
    "annotations": {
      "nginx.ingress.kubernetes.io/proxy-body-size": "2048m",
      "nginx.ingress.kubernetes.io/proxy-read-timeout": "1800",
      "nginx.ingress.kubernetes.io/proxy-send-timeout": "1800"
    }
  }
}'
```

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

Tests are defined in [18_test.yaml](18_test.yaml):

```bash
# Run test playbook
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/cvat/18_test.yaml
```

**Test Coverage**:
- Backend health endpoint responds
- PostgreSQL database connectivity
- Valkey cache connectivity
- ClickHouse analytics connectivity
- OAuth2 Proxy authentication flow
- OPA authorization policy evaluation
- Task creation via API
- Image upload and annotation workflow
- Annotation export in multiple formats

## Rollback

Rollback is defined in [19_rollback.yaml](19_rollback.yaml):

```bash
# Rollback CVAT deployment
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/cvat/19_rollback.yaml
```

**Rollback Actions**:
- Deletes CVAT deployments (backend, UI, OPA, OAuth2 Proxy, ephemeral Valkey)
- Deletes CVAT services and ingresses
- Removes `cvat` namespace
- Deletes Keycloak `cvat` client
- **Preserves** PostgreSQL `cvat` database (data retention - projects, tasks, annotations)
- **Preserves** PersistentVolumeClaims (cvat-data, cvat-keys, cvat-logs, cvat-models)
- **Preserves** ClickHouse analytics data
- **Does not affect** core Valkey (shared cache)
- Removes service discovery ConfigMap
- Updates code-server environment to remove CVAT variables

**Note**: Database and PVC preservation allows re-deployment without data loss. Manual cleanup required if full data deletion is desired.

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
