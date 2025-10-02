# Code-Server Developer Workflow

## Quick Reference

### During Development (Fast Iteration)

When working on shell configuration, functions, or templates:

```bash
# Quick refresh - use this most of the time
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/16_refresh_config.yaml
```

This playbook:
- ✅ Clears shell config (functions, aliases, rc files) in both container AND persistent storage
- ✅ Clears VS Code workspace state (last folder, window position)
- ✅ Re-runs shell configuration
- ✅ Restarts pod
- ⚡ **Fast**: No image rebuild, no full redeployment
- 💾 **Keeps**: Extensions, user data, npm/python packages

### When Image Changes (Slower)

When you modify the Dockerfile:

```bash
# 1. Rebuild image
./scripts/run_ansible.sh ansible/40_thinkube/core/harbor/16_build_codeserver_image.yaml

# 2. Delete pod (forces pull of new image)
./scripts/run_ssh_command.sh 192.168.191.100 "microk8s.kubectl delete pod -n code-server -l app=code-server"

# 3. Configure shell (after new pod starts)
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/14_configure_shell.yaml
```

### Full Reset (Clean Slate)

When you need to start completely fresh:

```bash
# 1. Full rollback (removes everything)
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/19_rollback.yaml

# 2. Deploy
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/10_deploy.yaml

# 3. Configure shell
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/14_configure_shell.yaml

# 4. Configure environment
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/15_configure_environment.yaml
```

## Playbook Overview

| Playbook | Purpose | When to Use |
|----------|---------|-------------|
| `10_deploy.yaml` | Deploy code-server to Kubernetes | First time or after rollback |
| `14_configure_shell.yaml` | Configure bash/zsh/fish shells | After deploy or when shell config changes |
| `15_configure_environment.yaml` | Install Claude Code, clone repos, configure VSCode | After deploy |
| `16_refresh_config.yaml` | **Quick refresh during development** | **Most common during development** |
| `19_rollback.yaml` | Complete removal and cleanup | When you need a clean slate |

## Why Use 16_refresh_config.yaml?

### The Problem
- Configuration files can get "stuck" with old values
- VS Code remembers last opened folder even after config changes
- Restarting browser doesn't clear persistent configuration
- Full rollback + redeploy is slow (minutes)

### The Solution
`16_refresh_config.yaml` does targeted cleanup:
1. Clears shell config in running container
2. Clears persistent shell config on host (`/home/thinkube/shared-code/`)
3. Clears VS Code workspace state (last folder, window state, etc.)
4. Re-runs shell configuration
5. Restarts pod

**Result**: Fresh configuration in ~30 seconds instead of 5+ minutes

## Common Development Scenarios

### Scenario 1: Fixed a Bug in a Function

```bash
# Edit the function in tasks/02_functions_system.yml
vim ansible/40_thinkube/core/code-server/tasks/02_functions_system.yml

# Quick refresh
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/16_refresh_config.yaml

# Reload browser
```

### Scenario 2: Added New Aliases

```bash
# Edit the aliases in 14_configure_shell.yaml
vim ansible/40_thinkube/core/code-server/14_configure_shell.yaml

# Quick refresh
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/16_refresh_config.yaml

# Reload browser
```

### Scenario 3: Changed Dockerfile

```bash
# Edit Dockerfile
vim ansible/40_thinkube/core/harbor/base-images/code-server-dev.Dockerfile.j2

# Rebuild image
./scripts/run_ansible.sh ansible/40_thinkube/core/harbor/16_build_codeserver_image.yaml

# Force pod restart with new image
./scripts/run_ssh_command.sh 192.168.191.100 "microk8s.kubectl delete pod -n code-server -l app=code-server"

# Configure shell (wait for pod to be ready first)
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/14_configure_shell.yaml
```

### Scenario 4: Testing Complete Deployment

```bash
# Full rollback
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/19_rollback.yaml

# Full deploy
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/10_deploy.yaml

# Configure shell
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/14_configure_shell.yaml

# Configure environment
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/15_configure_environment.yaml
```

## What Gets Persisted vs Ephemeral

### Persisted (Survives Pod Restart)
- `/home/thinkube/workspace/` - Your code and projects
- `/home/thinkube/.ssh/` - SSH keys
- `/home/thinkube/.kube/` - Kubernetes config
- `/home/thinkube/.local/` - Python packages, npm global, VS Code extensions
- `/home/thinkube/.config/` - Configuration files
- Shell config files (`.bashrc`, `.zshrc`, fish config)

### Ephemeral (Lost on Pod Restart)
- Running processes
- Temporary files in `/tmp`
- System packages installed with `apt` (unless in Dockerfile)
- Environment variables not in shell config

## Debugging Tips

### Check if Functions are Loaded

```bash
# In code-server terminal
list_functions
```

### Check if Pod Has Latest Image

```bash
./scripts/run_ssh_command.sh 192.168.191.100 "microk8s.kubectl describe pod -n code-server -l app=code-server | grep Image:"
```

### View Pod Logs

```bash
./scripts/run_ssh_command.sh 192.168.191.100 "microk8s.kubectl logs -n code-server -l app=code-server --tail=50"
```

### Check Persistent Storage

```bash
./scripts/run_ssh_command.sh 192.168.191.100 "ls -la /home/thinkube/shared-code/"
```

## Best Practices

1. **Use 16_refresh_config.yaml for most development** - It's fast and effective
2. **Commit often** - Test your changes, then commit
3. **Test full deployment before PR** - Run 19_rollback + 10_deploy + configs
4. **Document breaking changes** - If you change persistent storage structure
5. **Keep Dockerfile minimal** - Only system packages, not user config

## Troubleshooting

### Functions Not Loading
→ Run `16_refresh_config.yaml` - clears both container and persistent config

### VS Code Opens Wrong Folder
→ Run `16_refresh_config.yaml` - clears workspace state

### Old Config Values Appearing
→ Run `16_refresh_config.yaml` - clears all shell config

### Extensions Not Working
→ Run `19_rollback.yaml` then full deploy - extensions need clean install

### Pod Won't Start
→ Check logs, may need to rebuild image or check deployment manifest
