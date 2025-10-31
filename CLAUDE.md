# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Thinkube Ansible playbooks repository.

## Project Overview

Thinkube is a collection of Ansible playbooks for deploying a complete Kubernetes homelab platform. The playbooks are designed to be run either:
1. **Via the Thinkube Installer** (GUI desktop app) - Recommended for initial deployments
2. **Manually via command line** - For development, testing, and rollbacks

**Repository**: `~/thinkube/` (source of truth)
**Installer clone**: `/tmp/thinkube-installer/` (temporary, created by installer)

# ⚠️ CRITICAL PATH RULES ⚠️

**BEFORE ANY EDIT/WRITE/GIT OPERATION - CHECK THIS:**

## Allowed Paths for Edits

✅ **ALLOWED** - This is the source of truth:
- `/home/alexmc/thinkube/` - Ansible playbooks repository (edit here!)

❌ **FORBIDDEN** - Changes will be lost:
- `/tmp/thinkube-installer/` - TEMPORARY CLONE by installer, never edit here
- `/tmp/*` - Any temporary files created during deployment

## Pre-Commit Verification Checklist

**Before ANY `git commit` or `git push` command:**

1. ✅ Run `pwd` - Am I in `~/thinkube/`?
2. ❌ If in `/tmp/*` → **STOP IMMEDIATELY**, cd to `~/thinkube/`
3. ✅ If in `~/thinkube/` → Proceed with commit

**Always use full paths in git commands:**
```bash
# CORRECT - Explicit directory change
cd ~/thinkube && git add ... && git commit -m "..." && git push

# WRONG - Uses current directory
git commit -m "..."  # Where am I? /tmp? ~/thinkube? Unknown!
```

---

# Running Playbooks Manually

## Understanding the Two Execution Contexts

### 1. Via Installer (Automatic)
The Thinkube Installer (GUI app) automatically:
- Clones this repo to `/tmp/thinkube-installer/`
- Creates inventory at `/tmp/thinkube-installer/inventory/inventory.yaml`
- Sets up Ansible environment in `~/.thinkube-installer/ansible-venv/`
- Runs playbooks with proper environment variables
- Cleans up `/tmp/` clone after deployment

### 2. Manually (For Development/Rollbacks)
When running playbooks manually, you must:
- Use the installer's temporary clone at `/tmp/thinkube-installer/`
- Provide the inventory path explicitly
- Set required environment variables
- Use the correct Ansible binary

---

## How to Run Playbooks Manually

### Prerequisites

1. **Environment variables** in `~/.env`:
   ```bash
   ADMIN_PASSWORD=your_sudo_password
   # Other vars loaded automatically by playbooks
   ```

2. **Installer has run** at least once to create:
   - `~/.venv/` - Python virtual environment with Ansible
   - `/tmp/thinkube-installer/` - Clone of this repo
   - `/tmp/thinkube-installer/inventory/inventory.yaml` - Inventory file

### Standard Playbook Execution

**Command template:**
```bash
cd /tmp/thinkube-installer
ANSIBLE_BECOME_PASSWORD='your_sudo_password' \
~/.venv/bin/ansible-playbook \
  -i inventory/inventory.yaml \
  ansible/PATH/TO/PLAYBOOK.yaml
```

**Example - Deploy Harbor:**
```bash
cd /tmp/thinkube-installer
ANSIBLE_BECOME_PASSWORD='<your-password-here>' \
~/.venv/bin/ansible-playbook \
  -i inventory/inventory.yaml \
  ansible/40_thinkube/core/harbor/00_install.yaml
```

### Rollback Playbooks

**Purpose**: Rollback playbooks (numbered `19_rollback.yaml`) clean up deployments by:
- Terminating active connections (e.g., database sessions)
- Dropping databases cleanly
- Deleting Kubernetes namespaces and resources
- Leaving system in clean state for redeployment

**Example - Rollback Thinkube Control:**
```bash
cd /tmp/thinkube-installer
ANSIBLE_BECOME_PASSWORD='<your-password-here>' \
~/.venv/bin/ansible-playbook \
  -i inventory/inventory.yaml \
  ansible/40_thinkube/core/thinkube-control/19_rollback.yaml
```

**When to run rollback playbooks:**
- Deployment failed and you want to start fresh
- Database has active connections preventing drop
- Need to completely remove a component
- Testing changes that require clean slate

---

## Common Mistakes and How to Avoid Them

### ❌ MISTAKE #1: Wrong Working Directory

**Wrong:**
```bash
cd ~/thinkube
ansible-playbook ansible/40_thinkube/core/harbor/00_install.yaml
```

**Why wrong:** Inventory file is at `/tmp/thinkube-installer/inventory/inventory.yaml`, not in `~/thinkube/`

**Correct:**
```bash
cd /tmp/thinkube-installer
ANSIBLE_BECOME_PASSWORD='password' ~/.venv/bin/ansible-playbook \
  -i inventory/inventory.yaml \
  ansible/40_thinkube/core/harbor/00_install.yaml
```

---

### ❌ MISTAKE #2: Missing Environment Variables

**Wrong:**
```bash
cd /tmp/thinkube-installer
ansible-playbook -i inventory/inventory.yaml ansible/some/playbook.yaml
```

**Why wrong:** Playbooks expect `ANSIBLE_BECOME_PASSWORD` for sudo operations

**Correct:**
```bash
cd /tmp/thinkube-installer
ANSIBLE_BECOME_PASSWORD='your_password' ~/.venv/bin/ansible-playbook \
  -i inventory/inventory.yaml \
  ansible/some/playbook.yaml
```

---

### ❌ MISTAKE #3: Wrong Inventory Path

**Wrong:**
```bash
ansible-playbook -i ~/.thinkube-installer/inventory.yaml ...
```

**Why wrong:** Inventory is at `/tmp/thinkube-installer/inventory/inventory.yaml` (note the `inventory/` subdirectory)

**Correct:**
```bash
ansible-playbook -i inventory/inventory.yaml ...  # Relative to /tmp/thinkube-installer/
# OR
ansible-playbook -i /tmp/thinkube-installer/inventory/inventory.yaml ...  # Absolute path
```

---

### ❌ MISTAKE #4: Editing /tmp/thinkube-installer/

**Wrong:**
```bash
cd /tmp/thinkube-installer
# Edit ansible/40_thinkube/core/harbor/10_deploy.yaml
git commit -m "Fix Harbor"
```

**Why wrong:** `/tmp/thinkube-installer/` is a temporary clone. Changes will be lost when you restart the installer or reboot.

**Correct:**
```bash
cd ~/thinkube  # Source of truth
# Edit ansible/40_thinkube/core/harbor/10_deploy.yaml
git add ansible/40_thinkube/core/harbor/10_deploy.yaml
git commit -m "Fix Harbor"
git push
# Then pull changes into /tmp/ for testing:
cd /tmp/thinkube-installer && git pull
```

---

### ❌ MISTAKE #5: Using run_ansible.sh from ~/thinkube/

**Wrong:**
```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/harbor/00_install.yaml
```

**Why wrong:** `run_ansible.sh` expects inventory at `inventory/inventory.yaml` (relative path), which doesn't exist in `~/thinkube/`. The inventory is only created by the installer at `/tmp/thinkube-installer/inventory/inventory.yaml`.

**Correct:** Use the direct `ansible-playbook` command from `/tmp/thinkube-installer/` as shown in examples above.

---

## Repository Structure

```
~/thinkube/
├── ansible/
│   ├── 00_initial_setup/        # Bootstrap nodes, install k8s
│   │   ├── 00_install.yaml
│   │   ├── 10_deploy.yaml
│   │   └── 19_rollback.yaml
│   ├── 10_baremetal_infra/      # Storage, networking
│   ├── 30_networking/           # Cert-manager, ingress, Calico
│   ├── 40_thinkube/             # Main platform components
│   │   ├── core/                # Essential services
│   │   │   ├── postgresql/
│   │   │   ├── harbor/
│   │   │   ├── argocd/
│   │   │   ├── thinkube-control/
│   │   │   └── ...
│   │   └── optional/            # Optional services
│   │       ├── litellm/
│   │       ├── cvat/
│   │       └── ...
│   └── roles/                   # Reusable Ansible roles
├── scripts/
│   └── run_ansible.sh           # Helper script (not for manual use)
└── CLAUDE.md                    # This file
```

### Playbook Numbering Convention

- `00_install.yaml` - Meta-playbook that includes sub-playbooks
- `10_*.yaml` - Deployment/configuration playbooks
- `11_*.yaml`, `12_*.yaml` - Additional deployment steps
- `17_configure_discovery.yaml` - Service discovery setup
- `18_test.yaml` - Testing/validation playbook
- `19_rollback.yaml` - Cleanup/removal playbook

---

## Environment Variables

### Required Variables

- **ANSIBLE_BECOME_PASSWORD** - Sudo password for the remote host
  - Must be set when running playbooks manually
  - Automatically loaded from `~/.env` by installer

### Optional Variables (loaded from ~/.env)

- **ADMIN_PASSWORD** - Admin password for services (fallback for ANSIBLE_BECOME_PASSWORD)
- **ADMIN_USERNAME** - Admin username (default: tkadmin)
- **GITHUB_TOKEN** - GitHub personal access token
- **GITHUB_ORG** - GitHub organization name
- **CLOUDFLARE_TOKEN** - Cloudflare API token
- **ZEROTIER_NETWORK_ID** - ZeroTier network ID
- **CLUSTER_NAME** - Kubernetes cluster name
- **DOMAIN_NAME** - Domain name for services

---

## Troubleshooting

### "database is being accessed by other users"

**Problem:** Trying to drop a database that has active connections.

**Solution:** Run the rollback playbook to terminate connections and clean up:
```bash
cd /tmp/thinkube-installer
ANSIBLE_BECOME_PASSWORD='password' ~/.venv/bin/ansible-playbook \
  -i inventory/inventory.yaml \
  ansible/40_thinkube/core/SERVICE_NAME/19_rollback.yaml
```

Example services with rollback playbooks:
- `thinkube-control/19_rollback.yaml`
- `argocd/19_rollback.yaml`

### "Unable to parse inventory"

**Problem:** Inventory file path is wrong or doesn't exist.

**Check:**
```bash
ls -la /tmp/thinkube-installer/inventory/inventory.yaml
```

**Solution:** Ensure you're using the correct path:
- Relative: `inventory/inventory.yaml` (when cd'd to `/tmp/thinkube-installer/`)
- Absolute: `/tmp/thinkube-installer/inventory/inventory.yaml`

### "ANSIBLE_BECOME_PASSWORD not set"

**Problem:** Environment variable not set.

**Solution:** Set it before running:
```bash
ANSIBLE_BECOME_PASSWORD='your_password' ansible-playbook ...
```

Or load from `~/.env`:
```bash
source ~/.env
export ANSIBLE_BECOME_PASSWORD=$ADMIN_PASSWORD
ansible-playbook ...
```

---

## Quick Reference

### Most Common Commands

**Run a deployment playbook:**
```bash
cd /tmp/thinkube-installer && \
ANSIBLE_BECOME_PASSWORD='password' ~/.venv/bin/ansible-playbook \
  -i inventory/inventory.yaml \
  ansible/40_thinkube/core/SERVICE/00_install.yaml
```

**Run a rollback playbook:**
```bash
cd /tmp/thinkube-installer && \
ANSIBLE_BECOME_PASSWORD='password' ~/.venv/bin/ansible-playbook \
  -i inventory/inventory.yaml \
  ansible/40_thinkube/core/SERVICE/19_rollback.yaml
```

**Get password from ~/.env:**
```bash
grep ADMIN_PASSWORD ~/.env
# ADMIN_PASSWORD=<your-password-here>
```

**Check if /tmp clone exists:**
```bash
ls -la /tmp/thinkube-installer/
```

**Pull latest changes into /tmp clone:**
```bash
cd /tmp/thinkube-installer && git pull
```

---

## Summary: Golden Rules

1. **Edit in `~/thinkube/`** - Never edit in `/tmp/`
2. **Run from `/tmp/thinkube-installer/`** - Working directory matters
3. **Use `inventory/inventory.yaml`** - Relative to `/tmp/thinkube-installer/`
4. **Set ANSIBLE_BECOME_PASSWORD** - Required for sudo operations
5. **Use `~/.venv/bin/ansible-playbook`** - Correct Ansible binary
6. **Commit from `~/thinkube/`** - Check `pwd` before committing
7. **Rollback playbooks clean databases** - Use `19_rollback.yaml` for fresh start

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
