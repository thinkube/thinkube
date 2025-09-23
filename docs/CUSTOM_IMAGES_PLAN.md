# Plan: Custom Image Building Feature for Thinkube Control

## Overview
Add functionality to create, manage, and build custom Docker images through Thinkube Control using the EXACT same patterns as template deployment - with BackgroundTasks, WebSocket streaming, following the existing architecture 100%.

## Architecture Design (Following Template Deployment Pattern)

### 1. Repository Structure
- Working directory: `/home/thinkube/shared-code/dockerfiles/`
- Backup repository: `github.com/{user}/thinkube-dockerfiles` (source of truth)
- Directory structure:
  ```
  dockerfiles/
  ├── .git/           # Git repository
  ├── templates/      # Reusable Dockerfile templates
  └── custom/         # User custom images
      ├── {image-name}/
      │   ├── Dockerfile
      │   ├── README.md
      │   ├── build.yaml  # Build configuration
      │   └── context/    # Additional build files
  ```

### 2. Database Schema (CORRECTED - Matching TemplateDeployment)

**CRITICAL**: Logs are NOT stored in database - they go to `/tmp/thinkube-dockerfiles/{name}/`

Create model in `app/models/custom_images.py`:
```python
class CustomImageBuild(Base):
    """Track custom image builds - exactly like TemplateDeployment"""
    __tablename__ = "custom_image_builds"

    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    dockerfile_path = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, building, success, failed, cancelled
    build_config = Column(JSON)  # Build args, etc.
    output = Column(Text)  # Final output/summary
    registry_url = Column(Text)  # Full URL after push

    # Timestamps - same as TemplateDeployment
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # User tracking
    created_by = Column(String(255), nullable=False)
```

**NO ImageBuildLog table** - logs are streamed via WebSocket and saved to files

### 3. Backend Services (Following Template Pattern)

**`app/services/dockerfile_manager.py`**:
```python
class DockerfileManager:
    """Manages Dockerfile operations in shared-code"""

    async def create_custom_image(self, name: str, template: str, user: str):
        # Create directory structure
        # Initialize with template
        # Commit to local Git

    async def get_dockerfile_content(self, name: str):
        # Read Dockerfile from filesystem

    async def update_dockerfile(self, name: str, content: str):
        # Update and commit changes
```

**`app/services/image_build_executor.py`** (like background_executor.py):
```python
class ImageBuildExecutor:
    """Handles background execution of image builds"""

    async def start_build(self, image_id: str):
        # Create background task for build
        # Similar to BackgroundExecutor.start_deployment()

    async def _execute_build(self, image_id: str):
        # Run podman build
        # Stream logs to database
        # Push to Harbor on success
```

**`app/services/github_sync.py`**:
```python
class GitHubSync:
    """Manages GitHub backup and restore"""

    async def backup_to_github(self):
        # Commit all changes
        # Push to GitHub repository

    async def restore_from_github(self):
        # Pull from GitHub
        # Reset local to match remote
        # Update database records
```

### 4. API Endpoints (Following Template Pattern)

**`app/api/custom_images.py`**:
```python
@router.post("/custom-images/create")
async def create_custom_image(
    request: CreateImageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_dual_auth)
):
    """Create new custom image directory and database record"""
    # Similar to deploy_template_async

@router.post("/custom-images/{image_id}/build")
async def build_image(
    image_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Queue image build - returns immediately with build_id"""
    # Create build record
    # Add background task for build
    # Return WebSocket URL for logs

@router.get("/custom-images/{image_id}/build-logs/{build_id}")
async def get_build_logs(
    image_id: UUID,
    build_id: UUID,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get build logs with pagination"""

@router.get("/custom-images/{image_id}/editor-url")
async def get_editor_url(image_id: UUID, db: Session = Depends(get_db)):
    """Generate direct URL to edit Dockerfile in code-server"""
    # Return URL like: https://code.{domain}/?folder=/home/coder/shared-code/dockerfiles/custom/{name}
    # No authentication needed - SSO handles it via OAuth2 Proxy

@router.post("/custom-images/sync/backup")
async def backup_to_github(background_tasks: BackgroundTasks):
    """Backup all dockerfiles to GitHub"""

@router.post("/custom-images/sync/restore")
async def restore_from_github(background_tasks: BackgroundTasks):
    """Restore dockerfiles from GitHub"""
```

### 5. WebSocket for Build Logs

**`app/api/websocket_build.py`** (like websocket_executor.py):
```python
@router.websocket("/ws/custom-images/build/{build_id}")
async def websocket_build(
    websocket: WebSocket,
    build_id: str,
    db: Session = Depends(get_db)
):
    """Stream build logs via WebSocket"""
    # Accept connection
    # Start build if pending
    # Stream logs as they're generated
    # Send completion status
```

### 6. Build Process (Using Podman)

The build executor will:
```python
async def _execute_build(self, image_id: str, build_id: str):
    # Get image record from database
    # Read Dockerfile from filesystem

    # Build with Podman
    cmd = [
        "podman", "build",
        "-t", f"registry.{domain}/custom/{image.name}:latest",
        "-f", dockerfile_path,
        context_path
    ]

    # Stream output to database and WebSocket
    async for line in run_command_stream(cmd):
        # Save to ImageBuildLog
        # Send via WebSocket if connected

    # On success, push to Harbor
    if success:
        push_cmd = ["podman", "push", tag]
        await run_command(push_cmd)
```

### 7. Frontend Components (CORRECTED - Extend Existing UI)

**NO NEW VIEWS** - Extend HarborImages.vue with tabs:
- Tab 1: "Mirrored Images" (existing functionality)
- Tab 2: "Custom Images" (new functionality)

The Custom Images tab reuses existing patterns:
- Same table structure as mirrored images
- Same modal patterns
- Same action buttons (Create, Build, Edit, Delete)

**`BuildLogModal.vue`** (copy DeploymentLogModal.vue):
- WebSocket connection for real-time logs
- ANSI color support
- Success/failure indication

### 8. Code-Server Integration (SSO Already Configured)

When user clicks "Edit" button:
1. Frontend opens new tab/window with URL:
   ```
   https://code.{domain}/?folder=/home/coder/shared-code/dockerfiles/custom/{image-name}
   ```
2. User is automatically authenticated via Keycloak SSO (OAuth2 Proxy)
3. Code-server opens directly to the Dockerfile
4. User edits and saves normally
5. File changes are immediately available in shared-code

**No additional authentication needed** - the existing OAuth2 Proxy configuration handles everything.

### 9. Integration with Existing Systems

- **Harbor**: Images pushed to `registry.{domain}/custom/` project
- **Code-server**: Direct file editing via existing SSO setup
- **GitHub**: Backup repository with push/pull operations
- **Database**: Track all images and build history
- **Keycloak**: Existing SSO for all authentication

### 10. Security & Validation

- Dockerfile linting before build
- Base image allowlist in configuration
- Resource limits on build process (CPU, memory, timeout)
- User permissions tracked via `created_by` field
- All operations authenticated via existing SSO

## Implementation Phases (CORRECTED)

### Phase 1: Backend Foundation ✅ COMPLETED
- ✅ Database model (CustomImageBuild)
- ✅ dockerfile_executor.py service
- ✅ CRUD API endpoints
- ✅ Build execution with Podman
- ✅ Log directory structure

### Phase 2: WebSocket & Real-time Streaming (CURRENT)
- WebSocket handler for build logs (copy websocket_executor.py)
- Real-time log streaming during builds
- Build cancellation support

### Phase 3: Frontend Integration
- Extend HarborImages.vue with tabs
- Add Custom Images table
- Create BuildLogModal (copy DeploymentLogModal)
- Wire up all actions

### Phase 4: GitHub Integration (OPTIONAL - Later)
- Backup to GitHub repository
- Restore from GitHub
- This can be added later without breaking existing functionality

## Key Advantages

1. **Uses existing SSO**: No new authentication - OAuth2 Proxy + Keycloak already configured
2. **Consistent patterns**: Same BackgroundTasks/WebSocket approach as template deployment
3. **No new dependencies**: No Celery, uses existing infrastructure
4. **Simple code-server integration**: Just generate URLs, SSO handles the rest
5. **GitHub as backup**: Simple push/pull for backup and restore

This design leverages all existing Thinkube infrastructure without adding complexity.