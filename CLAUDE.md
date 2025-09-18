# CLAUDE.md - Master Documentation

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL REMINDERS - READ FIRST!

**WORKING ENVIRONMENT**: You are working REMOTELY, not on the actual servers
- **microk8s controller**: Located on node1 (NOT vm-2, which no longer exists)
- **thinkube-control**: Runs on control.example.com (deployed on Kubernetes)
- **Deployment logs**: Located on node1 at `/tmp/thinkube-deployments/{app_name}/`
- **NO DIRECT ACCESS**: Cannot SSH or directly access servers - work through APIs and web interfaces

**CURRENT DIRECTORY**: You are likely in `/home/thinkube/thinkube/` or one of its subdirectories
- **ALWAYS run `pwd` FIRST** before attempting any directory navigation
- **thinkube-control** at `/home/thinkube/thinkube/thinkube-control/` has ITS OWN Git repository
- **tkt-webapp-vue-fastapi** at `/home/thinkube/thinkube/tkt-webapp-vue-fastapi/` has ITS OWN Git repository
- When making changes to these directories, commit WITHIN them, not to the parent thinkube repo!

## SESSION START CHECKLIST

1. Run `pwd` to confirm your current location
2. Run `git status` to check which repository you're in
3. If working on thinkube-control:
   - Navigate to `/home/thinkube/thinkube/thinkube-control/`
   - This is the TEMPLATE (not the deployed version)
   - Commit and push changes IN THIS DIRECTORY
   - It has its own GitHub repository
4. Remember: Changes to templates need deployment to take effect

**IMPORTANT**: When starting a new session, first read the [START_HERE.md](/START_HERE.md) document at the project root. This document contains the master task list and tracks implementation progress to ensure continuity between sessions.

**MILESTONE 2 FOCUS**: We are now in Milestone 2 (Core Services). All Kubernetes services should be implemented following the guidelines in this document.

## Project Overview

Thinkube is a home-based development platform built on Kubernetes, designed specifically for AI applications and agents.

## Architecture Documentation

### Infrastructure Documentation (Milestone 1)
- [Variable Handling Policy](/docs/architecture-infrastructure/VARIABLE_HANDLING.md) - **MUST READ: Rules for variable management**
- [Error Handling Standard](/docs/architecture-infrastructure/ERROR_HANDLING.md) - Standardized error handling
- [Ansible Roles](/docs/architecture-infrastructure/ANSIBLE_ROLES.md) - When to use roles

### Kubernetes Documentation (Milestone 2)
- [Component Architecture](/docs/architecture-k8s/COMPONENT_ARCHITECTURE.md) - Kubernetes services architecture
- [Playbook Structure](/docs/architecture-k8s/PLAYBOOK_STRUCTURE.md) - Component-based organization
- [Branching Strategy](/docs/architecture-k8s/BRANCHING_STRATEGY.md) - Git workflow
- [CI/CD Architecture Complete](/docs/architecture-k8s/CI_CD_ARCHITECTURE_COMPLETE.md) - **CURRENT: Comprehensive CI/CD implementation**

## CRITICAL: Repository Management Rules

**NEVER commit thinkube-control or tkt-webapp-vue-fastapi changes to the main thinkube repository!**

1. **thinkube-control** in `/home/thinkube/thinkube/thinkube-control/`:
   - This is a TEMPLATE directory only
   - Has its own independent repository at https://github.com/{github_org}/thinkube-control
   - Changes should be committed and pushed ONLY within that directory to its own repository
   - NEVER add or commit these changes to the main thinkube repository

2. **tkt-webapp-vue-fastapi** in `/home/thinkube/thinkube/tkt-webapp-vue-fastapi/`:
   - This is a TEMPLATE directory only  
   - Has its own independent repository
   - Changes should be committed and pushed ONLY within that directory to its own repository
   - NEVER add or commit these changes to the main thinkube repository

**If you see these directories as modified in `git status` in the main thinkube repo, DO NOT COMMIT THEM!**

## Repository Structure Clarification

**Main thinkube repository** (`/home/thinkube/thinkube/`):
- This is the main infrastructure repository
- Contains Ansible playbooks, scripts, documentation
- Has subdirectories that are SEPARATE repositories (see below)

**Subdirectory repositories** (have their own .git directories):
- `/home/thinkube/thinkube/thinkube-control/` → Separate repo for thinkube-control template
- `/home/thinkube/thinkube/tkt-webapp-vue-fastapi/` → Separate repo for webapp template

**Workflow for subdirectory changes**:
1. `cd` into the subdirectory (e.g., `cd /home/thinkube/thinkube/thinkube-control/`)
2. Make your changes
3. `git add -A && git commit -m "Your message" && git push`
4. DO NOT go back to parent and commit there!

**Deployed versions** (DO NOT MODIFY DIRECTLY):
- `/home/thinkube/shared-code/thinkube-control/` on control plane node → Deployed version
- These are updated via deployment playbooks, not manual edits

## Document Management Guidelines

**IMPORTANT**: Follow these rules for document versioning and archival:

1. **Never create "OLD" files**: Use Git for version control. Files like `README_OLD.md` or `START_HERE_OLD.md` should not exist.
2. **Milestone documentation is historical**: Files like `CLAUDE_MILESTONE1.md` preserve important context from completed milestones and must be retained.
3. **Use proper renaming**:
   - If updating a document for a new phase: create the new version and delete the old one
   - If preserving milestone context: rename with the milestone identifier (e.g., `START_HERE.md` → `START_HERE_MILESTONE1.md`)
4. **Git is the archive**: Previous versions can always be retrieved from Git history
5. **Keep the repository clean**: Remove temporary or backup files immediately

## Code Style Guidelines

- **YAML**: 2-space indentation, use list format for tasks with clear names
- **Variables**: 
  - Use snake_case for all variable names
  - Installation-specific variables MUST be defined in inventory, NEVER in playbooks
  - Only technical/advanced variables MAY have defaults in playbooks  
  - All playbooks MUST verify required variables exist before proceeding
  - **Admin Credentials**: Always use `admin_username` and `admin_password` (not component-specific variants like `keycloak_admin_username`)
  - **Environment Variables**: Use `ADMIN_PASSWORD` for admin credentials (not `KEYCLOAK_ADMIN_PASSWORD`)
  - Default `admin_username` is `tkadmin` for neutral cross-application use
- **Module Names**: Use fully qualified names (e.g., `ansible.builtin.command` not `command`)
- **Tasks**: Always include descriptive name field
- **Facts**: Default to `gather_facts: true`
- **Error Handling**: Always fail fast on critical errors
- **Become**: Never use become at playbook level, only for specific tasks
- **DNS Usage**: Use DNS hostnames, eliminate hardcoded IPs

## Deployment Procedures

### Updating thinkube-control

**IMPORTANT**: When thinkube-control template changes need to be deployed to the running instance:
1. **DO NOT** directly interact with the control plane node or attempt manual deployment
2. **DO NOT** SSH to the control plane to update the deployed code
3. **ALWAYS** inform the user to manually run the deployment playbook
4. The approved message is: "To deploy these thinkube-control changes, please run the deployment playbook manually."

This ensures proper deployment procedures are followed and maintains system integrity.

## Command Execution Reference

### Running Commands in Kubernetes Control Node

**Note**: Use these commands only for troubleshooting and monitoring, NOT for deployment.

To run commands in the Kubernetes control node, use the `run_ssh_command.sh` script with the control plane hostname from your inventory:

```bash
# General syntax
./scripts/run_ssh_command.sh <control-plane-host> "command_to_run"

# Example: Check pod status (replace <control-plane-host> with actual hostname)
./scripts/run_ssh_command.sh <control-plane-host> "microk8s.kubectl get pods -n registry"

# Example: Check logs
./scripts/run_ssh_command.sh <control-plane-host> "microk8s.kubectl logs -n registry deploy/harbor-core -c harbor-core --tail 50"
```

**To find your control plane hostname:**
```bash
grep -A2 "microk8s_control_plane:" inventory/inventory.yaml
```

Key kubectl commands for troubleshooting:
- List pods: `microk8s.kubectl get pods -n <namespace>`
- Check logs: `microk8s.kubectl logs -n <namespace> <pod-name> -c <container-name> --tail <number>`
- Describe pod: `microk8s.kubectl describe pod -n <namespace> <pod-name>`
- Check services: `microk8s.kubectl get svc -n <namespace>`
- Check ingress: `microk8s.kubectl get ingress -n <namespace>`

## CRITICAL: Debugging Failed Deployments

**STOP assuming code isn't deployed!** When something fails:

1. **ASSUME the code IS deployed** - The CI/CD pipeline works. Stop questioning it.
2. **Check the ACTUAL problem**:
   - Is the database empty? (most common)
   - Is a service not registered in the router?
   - Are credentials missing?
   - Is there a configuration mismatch?
3. **NEVER spend more than 1 check** verifying deployment status
4. **Focus on the runtime issue**, not deployment status

### Common False Alarms
- **"API returns 404"** → Usually means database is empty or route not registered, NOT that code isn't deployed
- **"Service unavailable"** → Usually means pods are crashing due to missing config/data, NOT deployment issues
- **"Import error"** → Usually means missing dependencies, NOT deployment issues

### The Right Approach
```bash
# WRONG: Spending 10 minutes checking if code is deployed
# RIGHT: One quick check, then move to the actual problem

# Quick deployment verification (MAX 1 command):
kubectl describe pod <pod> | grep Image:

# Then immediately check the REAL issues:
- Database content
- Service registration
- Configuration values
- Dependencies
```

## Playbook Numbering Convention

- **10-17**: Main component setup and configuration
- **18**: Testing and validation
- **19**: Rollback and recovery procedures

## Milestone 2: Core Services Guidelines

### Component Directory Structure

```
ansible/40_thinkube/
├── core/                           # Essential platform components
│   ├── infrastructure/            # MicroK8s, ingress, cert-manager, coredns
│   ├── keycloak/                 # Each service gets its own directory
│   ├── postgresql/
│   └── ...
└── optional/                      # AWX-deployed components
    ├── prometheus/
    └── ...
```

Each component directory contains:
- `10_deploy.yaml` - Main deployment playbook
- `15_configure_*.yaml` - Additional configuration (if needed)
- `18_test.yaml` - Test playbook
- `19_rollback.yaml` - Rollback playbook
- `README.md` - Component documentation

### Migration Requirements from thinkube-core

When migrating playbooks from thinkube-core:

**CRITICAL**: Preserve ALL original functionality while making minimal changes. The goal is compliance with guidelines, not rewriting working code.

1. **Functionality Preservation Check**
   - Document all features in the original playbook
   - Ensure migrated version maintains exact same functionality
   - Make ONLY the minimum changes required for compliance
   - If uncertain about a change, preserve the original approach
   - Test that the service behaves identically after migration

2. **Host Group Updates**
   - Replace `gato-p` with `microk8s_control_plane` (NOT `k8s-control-node`)
   - Replace `gato-w1` with `microk8s_workers` (NOT `k8s-worker-nodes`)
   
   **CRITICAL: Host Group Reference**
   - `microk8s_control_plane`: Control plane node (host defined in inventory)
   - `microk8s_workers`: Worker nodes (hosts defined in inventory)
   - `microk8s`: All Kubernetes nodes (both control plane and workers)
   
   **NEVER use incorrect group names like:**
   - `gato-p` (old name from thinkube-core)
   - `k8s-control-node` (incorrect name)
   - `gato-w1` (old name from thinkube-core)
   - `k8s-worker-nodes` (incorrect name)

3. **Variable Compliance**
   - Move ALL hardcoded values to inventory variables
   - No defaults in playbooks
   - Common migrations:
     - `example.com` → `{{ domain_name }}`
     - `10.200.0.100` → `{{ primary_ingress_ip }}`
     - `admin` → `{{ admin_username }}`

4. **TLS Certificate Migration**
   - **CRITICAL: ALWAYS copy the wildcard certificate from default namespace**
   - The source certificate name is `thinkube-com-tls` in the `default` namespace
   - Components must copy this certificate to their namespaces
   - Follow the naming convention `{{ component_namespace }}-tls-secret`
   - Example of the correct approach:
     ```yaml
     - name: Get wildcard certificate from default namespace
       kubernetes.core.k8s_info:
         kubeconfig: "{{ kubeconfig }}"
         api_version: v1
         kind: Secret
         namespace: default
         name: thinkube-com-tls
       register: wildcard_cert
       failed_when: wildcard_cert.resources | length == 0

     - name: Copy wildcard certificate to component namespace
       kubernetes.core.k8s:
         kubeconfig: "{{ kubeconfig }}"
         state: present
         definition:
           apiVersion: v1
           kind: Secret
           metadata:
             name: "{{ component_namespace }}-tls-secret"
             namespace: "{{ component_namespace }}"
           type: kubernetes.io/tls
           data:
             tls.crt: "{{ wildcard_cert.resources[0].data['tls.crt'] }}"
             tls.key: "{{ wildcard_cert.resources[0].data['tls.key'] }}"
     ```
   - **NEVER** create TLS secrets from certificate files on disk

5. **Module Name Compliance**
   - Use fully qualified collection names
   - `kubernetes.core.k8s` not `k8s`

### Migration Validation Checklist

Before considering a migration complete:
- [ ] All original features are preserved
- [ ] Service configuration is identical
- [ ] Same ports, protocols, and endpoints
- [ ] Authentication/authorization unchanged
- [ ] Resource limits/requests preserved
- [ ] Environment variables maintained
- [ ] Volume mounts and storage identical
- [ ] Network policies preserved
- [ ] Service dependencies respected

### Development Workflow

1. **Create GitHub Issue**: Use component requirement template
2. **Create Feature Branch**: Per branching strategy
3. **Create Test First**: Write `18_test.yaml` before implementation
4. **Implement Migration**: Follow all compliance rules
5. **Verify Tests Pass**: Run test playbook
6. **Create PR**: Link to issue, include test results
7. **Merge to Main**: After review and approval

### GitHub Issue Retrieval

To retrieve GitHub issues for implementation:

```bash
# View a specific issue
gh issue view <issue-number> --repo thinkube/thinkube

# List all open issues
gh issue list --repo thinkube/thinkube

# Search for specific issues
gh issue list --repo thinkube/thinkube --search "CORE"
```

**ALWAYS** use the GitHub CLI (`gh`) to retrieve issue details rather than searching files or using web searches, as this repository is private.

**CRITICAL: Never Commit Without Testing**
- **NEVER commit without successfully RUNNING 10_deploy.yaml and 18_test.yaml**
- Syntax checking (--syntax-check) is NOT sufficient
- All code MUST be deployed and tested in a real environment before commit
- At minimum, execute with actual deployment and verify:
  1. `10_deploy.yaml` - Successful real deployment (not just syntax check)
  2. `18_test.yaml` - All tests pass in the live environment

**IMPORTANT**: "Run" always means actual execution against the infrastructure, not syntax validation

### AI-Generated Content

Mark all AI-generated or AI-assisted content:
- Use 🤖 emoji in comments and code
- Add footer to commit messages (see Commit Message Format below)
- Track major contributions in AI_CONTRIBUTIONS.md
- Clearly separate AI analysis from human decisions

## Commit Message Format

Follow this format for all commits:

```
Type CORE-XXX: Short description

- Bullet point explaining change
- Another bullet point
- Continue as needed

[Optional: Fixes #XXX or Closes #XXX]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Where Type is one of:
- `Implement` - New feature or component
- `Fix` - Bug fix
- `Update` - Enhancement or modification
- `docs` - Documentation only changes
- `refactor` - Code refactoring

## Playbook Header Guidelines

All playbooks MUST include a standardized header:

```yaml
---
# ansible/path/to/playbook.yaml
# Description:
#   Brief description of what this playbook does
#   Additional details about its purpose
#
# Requirements:
#   - List prerequisites (e.g., MicroK8s must be installed)
#   - Required variables from inventory
#   - Environment variables needed
#
# Usage:
#   cd ~/thinkube
#   ./scripts/run_ansible.sh ansible/path/to/playbook.yaml
#
# Variables from inventory:
#   - variable_name: Description of variable
#   - another_var: What this variable controls
#
# Dependencies:
#   - Component dependencies (e.g., CORE-001 must be complete)
#   - External services required
#
# [Optional for AI-generated playbooks]
# 🤖 [AI-assisted]
```

Test and rollback playbooks can use a simplified header focusing on their specific purpose.

## GitOps Workflow with Gitea

Thinkube uses Gitea to solve the domain configuration problem in GitOps deployments:

### The Problem
- Templates in GitHub use variables like `{{ domain_name }}`
- ArgoCD needs actual values like `registry.thinkube.com`
- We cannot hardcode domains as each installation is different

### The Solution
1. **GitHub** → Contains templates with variables (.jinja files)
2. **Ansible** → Processes templates during deployment
3. **Gitea** → Hosts processed manifests with actual domain values
4. **ArgoCD** → Deploys from Gitea repositories

### Development Workflow

When deploying applications that need domain-specific configuration:

1. **Use the git_push role** to push to Gitea:
   ```yaml
   - name: Push to Gitea
     include_role:
       name: container_deployment/git_push
     vars:
       gitea_org: "thinkube-deployments"
       gitea_repo_name: "{{ app_name }}-deployment"
       local_repo_path: "{{ temp_dir }}"
   ```

2. **Repository includes**:
   - Git hooks for auto-processing templates
   - Helper scripts for development
   - Auto-generated warnings on processed files

3. **Developer workflow**:
   - Edit `.jinja` templates (NOT processed `.yaml` files)
   - Commit changes (hook auto-processes)
   - Push to Gitea → ArgoCD deploys

4. **Contributing back**:
   - Run `./prepare-for-github.sh`
   - Push to GitHub (only templates)

### Template Processing

- **Ansible templates** (`.j2`) - For deployment configuration
- **Application templates** (`.jinja`) - For GitOps workflow

Never confuse these two types!

## Memory Section

- Never use docker
- Always use Gitea for domain-specific deployments
- Templates (.jinja) are source of truth, not processed files
- to access vilanova1 with ssh_run_command you must use the ip 192.168.191.100