# code-server Enhancement Plan (Week 1)

This document details the implementation plan for transforming code-server into a complete Thinkube development environment using a custom container image.

## Status: 🚧 In Progress

**Timeline**: Week 1 of Phase 4.5
**Risk Level**: LOW (all changes are internal, no public exposure)
**Last Updated**: September 28, 2025

---

## Strategy: Custom Image Approach

**Decision**: Use a custom container image with all tools preinstalled instead of runtime installation.

**Rationale**:
- ✅ Faster pod startup (~30 seconds vs 20 minutes)
- ✅ Reproducible environment
- ✅ Version-controlled tool versions
- ✅ Easier testing during development
- ✅ No complex initialization scripts needed

**Trade-off**: Slightly larger initial pull, but much faster restarts

---

## Current State Analysis

### What We Have
- ✅ code-server deployed with OAuth2 authentication via Keycloak
- ✅ Runs on control plane with hostPath volume to `/home/thinkube/shared-code`
- ✅ Base image: `codercom/code-server:latest`
- ✅ Node.js 20 installed
- ✅ Claude Code integration configured
- ✅ SSH keys configured for GitHub and Thinkube nodes
- ✅ VS Code tasks for Claude Code
- ✅ ServiceAccount with CI/CD monitoring permissions
- ✅ Git configuration

### What We're Adding
- ✅ Ansible + collections for infrastructure automation (via custom image)
- ✅ All Kubernetes tools: kubectl, helm, k9s, stern, kubectx/kubens
- ✅ Container tools: Podman, buildah, skopeo (NOT Docker)
- ✅ Service-specific CLIs: argo, argocd, nats, mlflow, devpi, gh, tea
- ✅ Database clients: psql, valkey-cli (redis-tools)
- ✅ Development utilities: jq, yq, ripgrep, fd, bat, httpie
- ✅ Environment setup scripts with service URLs and aliases
- ❌ Enhanced VS Code configuration (future task)
- ❌ Wrapper scripts for seamless execution (future task)

---

## Implementation Tasks

### Task 1: Create Custom Image ✅ COMPLETE

**File**: `ansible/40_thinkube/core/harbor/base-images/code-server-dev.Dockerfile.j2`

**Status**: ✅ **COMPLETED**

**What was built**:
```dockerfile
FROM codercom/code-server:latest

# System packages + Python development
# Ansible + collections (kubernetes.core, community.general, etc.)
# Container tools (podman, buildah, skopeo)
# Database clients (postgresql-client, redis-tools)
# Modern CLI utilities (jq, yq, ripgrep, fd, bat, httpie)
# Kubernetes tools (kubectl v1.30.0, helm, k9s, stern, kubectx/kubens)
# Argo tools (argo v3.5.5, argocd v2.10.0)
# Git tools (gh, tea 0.9.2)
# Service CLIs (nats)
# Python tools (mlflow, devpi-client, copier, ansible-lint)
# Environment setup script with aliases and service URLs
```

**Image location**: `{{ harbor_registry }}/library/code-server-dev:latest`

**Tools included** (31 total):
1. kubectl v1.30.0
2. helm (latest)
3. k9s v0.32.0
4. stern v1.28.0
5. kubectx / kubens
6. podman
7. buildah
8. skopeo
9. podman-compose
10. ansible-core
11. ansible-galaxy (5 collections)
12. argo v3.5.5
13. argocd v2.10.0
14. gh (GitHub CLI)
15. tea 0.9.2 (Gitea CLI)
16. nats (NATS CLI)
17. jq (JSON processor)
18. yq v4.40.5 (YAML processor)
19. ripgrep (rg)
20. fd-find
21. bat (batcat)
22. httpie
23. psql (postgresql-client)
24. redis-tools (valkey-cli)
25. mlflow (Python)
26. devpi-client (Python)
27. copier (Python)
28. ansible-lint (Python)
29. vim
30. nano
31. gettext-base (envsubst)

**Environment setup** (`/home/coder/.setup-thinkube-env.sh`):
- KUBECONFIG configuration
- Argo server and namespace
- Ansible configuration
- Python tools PATH
- Helpful aliases: k, kgp, kgs, kgn, kd, kl

### Task 2: Create Build Playbook ✅ COMPLETE

**File**: `ansible/40_thinkube/core/harbor/16_build_codeserver_image.yaml`

**Status**: ✅ **COMPLETED**

**What it does**:
1. Templates the Dockerfile with Harbor registry variables
2. Builds image with podman
3. Pushes to `{{ harbor_registry }}/library/code-server-dev:latest`
4. Creates image manifest for tracking
5. Displays completion message with tool inventory

**Usage**:
```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/harbor/16_build_codeserver_image.yaml
```

**Build time**: ~10-15 minutes (one-time, then cached)

### Task 3: Update Deployment ✅ COMPLETE

**File**: `ansible/40_thinkube/core/code-server/10_deploy.yaml`

**Change**: Line 774
```yaml
# Before:
image: "{{ harbor_registry }}/library/code-server:latest"

# After:
image: "{{ harbor_registry }}/library/code-server-dev:latest"
```

**Status**: ✅ **COMPLETED**

**Effect**: code-server pods will now use custom image with all tools preinstalled

### Task 4: Documentation Updates ✅ COMPLETE

**Files Updated**:
1. ✅ `CODE_SERVER_CLI_TOOLS.md` - Changed Docker → Podman references
2. ✅ `CODE_SERVER_ENHANCEMENT_PLAN.md` - This file (strategy pivot)
3. ✅ `ansible/40_thinkube/core/custom-images/DEPRECATED.md` - Added deprecation notice

**Key Changes**:
- All references to "Docker" changed to "Podman"
- Documented custom image approach
- Updated installation instructions to reflect preinstalled tools
- Added note about Dockerfile location

### Task 5: Split Image Build Playbooks ✅ COMPLETE

**Goal**: Separate image builds for faster iteration

**Created**:
1. ✅ `ansible/40_thinkube/core/harbor/14_build_base_images.yaml` - Foundation images (already existed, now base only)
2. ✅ `ansible/40_thinkube/core/harbor/15_build_jupyter_images.yaml` - Jupyter notebook images (extracted)
3. ✅ `ansible/40_thinkube/core/harbor/16_build_codeserver_image.yaml` - code-server dev image (new)

**Benefit**: Only rebuild changed components, not everything

---

## Testing Checklist

### Phase 1: Build Testing
- [ ] Build custom image successfully
- [ ] Push to Harbor registry
- [ ] Verify image size is reasonable (<2GB)
- [ ] Check all tools are present in image

### Phase 2: Deployment Testing
- [ ] Redeploy code-server with new image
- [ ] Pod starts successfully (~30 seconds)
- [ ] Can access code-server via browser
- [ ] OAuth2 authentication works

### Phase 3: Tool Verification
- [ ] kubectl connects to cluster
- [ ] helm lists releases
- [ ] k9s launches and shows pods
- [ ] ansible --version shows correct version
- [ ] ansible-galaxy collection list shows 5 collections
- [ ] argo version works
- [ ] argocd version --client works
- [ ] gh --version works
- [ ] nats --version works
- [ ] psql --version works
- [ ] podman --version works
- [ ] jq --version works
- [ ] yq --version works

### Phase 4: Complete Workflows
- [ ] Run Ansible playbook from code-server
- [ ] Execute kubectl commands
- [ ] Build and push container image with podman
- [ ] Access PostgreSQL database
- [ ] Use NATS CLI
- [ ] Check MLflow experiments
- [ ] Push to Gitea with tea CLI
- [ ] Interact with GitHub via gh CLI

### Phase 5: Environment Setup
- [ ] `.setup-thinkube-env.sh` sources correctly
- [ ] Environment variables set properly
- [ ] Aliases work (k, kgp, kgs, etc.)
- [ ] PATH includes all tool locations

---

## What Changed from Original Plan

### Original Plan (Runtime Installation)
- Install tools via kubectl exec during deployment
- 15-20 minute setup time
- Complex initialization scripts
- Harder to test and reproduce

### New Plan (Custom Image)
- Tools preinstalled in container image
- ~30 second pod startup
- Simple, reproducible
- Easy to version control

### Why We Changed
**User feedback**: "One of the tradeoffs of current system is that if it takes very long to start is also making testing more painful... I would like to start directly with the custom image process"

**Benefits realized**:
- Much faster iteration during development
- Easier to test changes
- Version-controlled environment
- Reproducible across deployments

---

## Next Steps After Week 1

### Week 2+: Enhancement Opportunities (Optional)

1. **VS Code Extensions** (Medium Priority)
   - Ansible extension
   - Kubernetes extension
   - YAML extension
   - Docker/Podman extension
   - Python extension

2. **Wrapper Scripts** (Low Priority)
   - `tk-ansible` - Run playbooks with Thinkube defaults
   - `tk-kubectl` - kubectl with Thinkube context
   - `tk-deploy` - Quick deploy to cluster
   - `tk-logs` - Easy log viewing

3. **Additional Tools** (Low Priority)
   - clickhouse-client (for Langfuse)
   - kubectx/kubens completion
   - just (command runner)
   - pnpm (Node package manager)

4. **Documentation**
   - Create video walkthrough of development workflow
   - Write blog post about developing Thinkube from Thinkube
   - Update README with development instructions

---

## Success Criteria

**Week 1 is successful when**:
1. ✅ Custom image builds successfully
2. ✅ Image pushed to Harbor
3. ✅ code-server deployment uses new image
4. [ ] Pod starts in ~30 seconds (not 20 minutes)
5. [ ] All High Priority tools are functional
6. [ ] Can run Ansible playbooks from code-server
7. [ ] Can manage Kubernetes cluster
8. [ ] Can build and push images with podman
9. [ ] Can interact with all Thinkube services

**Definition of "functional"**: Tool runs, connects to service, performs basic operations

---

## Risk Assessment

### Low Risk
- ✅ All changes are internal (no public exposure)
- ✅ Can easily rollback to previous image
- ✅ No data loss possible (hostPath volume unchanged)
- ✅ OAuth2 authentication unchanged

### Potential Issues

**Issue 1: Image size too large**
- **Mitigation**: Multi-stage build if needed
- **Fallback**: Remove low-priority tools

**Issue 2: Tool compatibility**
- **Mitigation**: Use specific versions in Dockerfile
- **Fallback**: Test each tool individually

**Issue 3: Permission issues**
- **Mitigation**: Run as coder user (UID 1000)
- **Fallback**: Adjust securityContext in deployment

**Issue 4: Pod startup slow despite custom image**
- **Investigation**: Check image pull time, pod scheduling
- **Mitigation**: Pre-pull image to node

---

## Resource Requirements

### Build Time
- **Initial build**: 10-15 minutes
- **Subsequent builds**: 2-5 minutes (layer caching)
- **Push to registry**: 1-2 minutes

### Image Size
- **Base image**: ~500MB (codercom/code-server)
- **Custom image**: ~1.5GB (estimated with all tools)
- **Acceptable**: <2GB total

### Runtime Resources
- **CPU**: 2 cores (same as before)
- **Memory**: 4Gi (same as before)
- **Storage**: 20Gi hostPath volume (unchanged)

---

## Conclusion

Week 1 transforms code-server from a basic IDE into a complete Thinkube development platform by using a custom container image with all necessary CLI tools preinstalled. This approach provides:

1. **Speed**: 30-second startup vs 20-minute installation
2. **Reliability**: Reproducible environment
3. **Maintainability**: Version-controlled tools
4. **Developer Experience**: Instant productivity

The custom image approach enables developing Thinkube from within Thinkube itself, demonstrating the platform's self-hosting capabilities while providing a professional development experience.

---

## See Also

- [CLI Tools Inventory](CODE_SERVER_CLI_TOOLS.md) - Complete list of 31 tools
- [Phase 4.5 Timeline](PHASE_4_5_TIMELINE.md) - Overall schedule
- [Public Release Preparation](PUBLIC_RELEASE_PREPARATION.md) - Weeks 2-5 plan
- [MVP Final Plan](MVP_FINAL_PLAN.md) - Overall project status
