# Public Release Preparation (Weeks 2-5)

This document details the step-by-step plan for preparing Thinkube repositories for public release, culminating in the public installer launch.

## Status: 🚧 Planned

**Timeline**: Weeks 2-5 of Phase 4.5
Last Updated: September 28, 2025

---

## Overview

**Strategy**: Gradual, controlled public exposure
- Week 2: Prepare main repository (PRIVATE)
- Week 3: thinkube-control goes public (FIRST PUBLIC REPO)
- Week 4: Main repository goes public (SECOND PUBLIC REPO)
- Week 5: Installer goes public (🚀 PUBLIC LAUNCH)

---

## Week 2: Main Repository Security and License Audit

**Status**: PRIVATE (no public exposure)
**Risk Level**: LOW
**Repository**: `thinkube/thinkube` (currently private)

### Objectives
1. Add copyright headers to all source files
2. Conduct comprehensive security audit
3. Create public-facing documentation
4. Prepare repository for public visibility

### Task 2.1: Copyright Header Audit

#### Files to Process

**YAML Files** (~274 files in `ansible/`):
```bash
# Most already have headers, verify all
find ansible/ -name "*.yaml" -o -name "*.yml" | wc -l
# Expected: ~274 files
```

**Python Files**:
```bash
find . -name "*.py" -not -path "*/node_modules/*" -not -path "*/venv/*"
```

**Shell Scripts**:
```bash
find . -name "*.sh" -not -path "*/node_modules/*"
```

**Dockerfiles**:
```bash
find . -name "Dockerfile*" -not -path "*/node_modules/*"
```

#### Header Format

Use the format from `COPYRIGHT_HEADER.md`:

**For YAML/Python/Shell**:
```yaml
# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0
```

**For JavaScript/TypeScript/Vue**:
```javascript
/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */
```

#### Automated Tool

Use existing script:
```bash
# Run from code-server or ansible controller
python3 installer/scripts/add-license-headers.py
```

Or create custom script for remaining files:
```bash
#!/bin/bash
# add-headers-to-yaml.sh

HEADER="# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0
"

for file in $(find ansible/ -name "*.yaml" -o -name "*.yml"); do
    # Check if file already has copyright header
    if ! grep -q "Copyright.*Alejandro" "$file"; then
        echo "Adding header to $file"
        # Create temp file with header + original content
        echo "$HEADER" | cat - "$file" > temp && mv temp "$file"
    fi
done
```

#### Manual Review

Some files may need manual review:
- Template files (`.j2`) - add header appropriate to output format
- Configuration files - may not need headers
- Third-party code - DO NOT add headers

### Task 2.2: Security Audit

#### Credential Scan

**Search for passwords**:
```bash
# Search in files
grep -r "password.*=" . \
    --exclude-dir=node_modules \
    --exclude-dir=.git \
    --exclude-dir=venv \
    --exclude="*.md"

# Look for patterns
grep -r "ADMIN_PASSWORD\|admin_password" . \
    --include="*.yaml" \
    --include="*.py"
```

**Expected Findings** (these are OK):
- `lookup('env', 'ADMIN_PASSWORD')` - reading from environment ✅
- `admin_password: "{{ lookup('env', 'ADMIN_PASSWORD') }}"` - using variable ✅

**NOT OK** (must be removed):
- `admin_password: "MySecretPassword123"` - hardcoded password ❌
- `token: "ghp_abc123def456"` - hardcoded token ❌

#### API Token Scan

```bash
# GitHub tokens
grep -r "ghp_\|github_pat_" . --exclude-dir=.git

# Harbor tokens
grep -r "harbor.*token" . --exclude-dir=.git --include="*.yaml"

# Any long base64 strings (potential secrets)
grep -rE "[A-Za-z0-9+/]{40,}" . --include="*.yaml" --include="*.py"
```

#### Git History Scan

```bash
# Check for passwords in commit messages
git log --all --full-history --grep="password" --grep="token" --grep="secret"

# Check for removed secrets
git log --all --full-history -S "ghp_" --source --all

# Use git-secrets (if available)
git secrets --scan-history
```

If secrets found in history:
```bash
# Use BFG Repo-Cleaner to remove from history
# https://rtyley.github.io/bfg-repo-cleaner/

# Or use git filter-branch (last resort)
```

#### Private Infrastructure References

Search for:
```bash
# Private IP addresses (should be variables)
grep -r "192\.168\.\|10\.\|172\." . \
    --include="*.yaml" \
    --include="*.py" \
    --exclude-dir=.git

# Private hostnames
grep -r "bcn1\|bcn2\|gato-\|vilanova" . \
    --include="*.yaml" \
    --include="*.md" \
    --exclude-dir=.git
```

Replace with:
- Variables: `{{ ansible_host }}`
- Example values: `node1.example.com`
- Documentation placeholders: `<your-server-hostname>`

### Task 2.3: Documentation Creation

#### CONTRIBUTING.md

```markdown
# Contributing to Thinkube

Thank you for your interest in contributing to Thinkube!

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Submit a pull request

## Development Environment

See [CODE_SERVER_ENHANCEMENT_PLAN.md](CODE_SERVER_ENHANCEMENT_PLAN.md) for setting up a complete development environment.

## Code Style

- **YAML**: 2-space indentation
- **Python**: PEP 8 compliance
- **Ansible**: Use fully qualified module names
- **Variables**: snake_case, never hardcode values

## Commit Messages

Follow conventional commit format:
```
<type> CORE-XXX: Short description

- Detailed change 1
- Detailed change 2

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: Implement, Fix, Update, docs, refactor

## Pull Request Process

1. Update documentation if needed
2. Add tests if applicable
3. Ensure all tests pass
4. Link related issues
5. Request review

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
```

#### CODE_OF_CONDUCT.md

Use Contributor Covenant:
```markdown
# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone...

[Full Contributor Covenant 2.1 text]
```

#### SECURITY.md

```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

**Please DO NOT file a public issue for security vulnerabilities.**

Instead, please report security issues to: security@thinkube.com
(or create a private GitHub Security Advisory)

We will acknowledge your report within 48 hours and provide a detailed response within 7 days.

## Security Best Practices

When deploying Thinkube:
1. Use strong passwords for all services
2. Keep all components up to date
3. Use network policies to restrict traffic
4. Enable TLS for all services
5. Regularly backup your data
6. Monitor logs for suspicious activity

## Known Security Considerations

Thinkube is designed for homelab/development environments. For production:
- Review and harden all default configurations
- Implement additional network security
- Use external secrets management
- Enable audit logging
```

#### README.md Updates

Add public-facing content:
```markdown
# Thinkube

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/thinkube/thinkube)](https://github.com/thinkube/thinkube/releases)

A self-hosting AI/ML development platform built on Kubernetes for homelabs.

## ✨ Features

- 🤖 **JupyterHub** with GPU flexibility
- 🐳 **Harbor** container registry
- 🔄 **Argo Workflows** for CI/CD
- 📊 **MLflow** for experiment tracking
- 🧠 **LiteLLM** gateway to external models
- 🏷️ **CVAT** and **Argilla** for data annotation
- 🔐 **Keycloak** SSO for all services
- 💻 **code-server** for browser-based development

## 🚀 Quick Start

Install Thinkube with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/thinkube/thinkube-installer/main/scripts/install.sh | bash
```

See [Installation Guide](INSTALLATION.md) for detailed instructions.

## 📚 Documentation

- [Getting Started](docs/getting-started.md)
- [Architecture Overview](docs/architecture-infrastructure/COMPONENT_ARCHITECTURE.md)
- [Development Guide](CODE_SERVER_ENHANCEMENT_PLAN.md)
- [Contributing](CONTRIBUTING.md)

## 🏗️ Architecture

[Diagram or description of Thinkube architecture]

## 📋 Requirements

- Ubuntu 24.04 LTS
- 2+ nodes (1 control plane, 1+ workers)
- NVIDIA GPUs (optional but recommended)
- 100GB+ storage per node

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with amazing open-source projects:
- Kubernetes & MicroK8s
- JupyterHub
- Argo (Workflows & CD)
- MLflow, LiteLLM, and many more

## 📧 Contact

- GitHub Issues: [Report bugs](https://github.com/thinkube/thinkube/issues)
- Discussions: [Join the conversation](https://github.com/thinkube/thinkube/discussions)
```

### Week 2 Deliverables Checklist

- [ ] All files have copyright headers
- [ ] Security scan completed, no secrets found
- [ ] Git history cleaned (if needed)
- [ ] CONTRIBUTING.md created
- [ ] CODE_OF_CONDUCT.md created
- [ ] SECURITY.md created
- [ ] README.md updated for public audience
- [ ] All private references removed or parameterized
- [ ] Repository READY to be made public (but still private)

---

## Week 3: thinkube-control Repository Migration

**Status**: PRIVATE → PUBLIC (first public repo)
**Risk Level**: MEDIUM
**Repository**: `cmxela/thinkube-control` → `thinkube/thinkube-control`

### Objectives
1. Audit thinkube-control for copyright and security
2. Transfer to thinkube organization
3. Make repository public
4. Update all references

### Task 3.1: thinkube-control Audit

**Current location**: `/home/thinkube/thinkube/thinkube-control/`
**Current remote**: `git@github.com:cmxela/thinkube-control.git`

#### Files to Audit

```bash
cd /home/thinkube/thinkube/thinkube-control/

# Count files needing headers
find . -name "*.py" -o -name "*.vue" -o -name "*.js" -o -name "*.ts" | \
    grep -v node_modules | wc -l
```

#### Add Headers

**Python files**:
```python
# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0
```

**Vue/JS/TS files**:
```javascript
/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */
```

#### Security Check

```bash
# Check for hardcoded secrets
grep -r "password.*=\|token.*=\|secret.*=" . \
    --include="*.py" \
    --include="*.js" \
    --include="*.ts" \
    --include="*.vue" \
    --exclude-dir=node_modules

# Check git history
git log --all --oneline | grep -i "password\|secret\|token"
```

### Task 3.2: Repository Transfer

#### Step 1: Transfer to Organization

Via GitHub Web UI:
1. Go to: `https://github.com/cmxela/thinkube-control/settings`
2. Scroll to "Danger Zone"
3. Click "Transfer ownership"
4. Enter: `thinkube` (organization)
5. Confirm transfer

Or via GitHub CLI:
```bash
gh repo transfer cmxela/thinkube-control thinkube \
    --confirm
```

#### Step 2: Make Public

```bash
# Via GitHub CLI
gh repo edit thinkube/thinkube-control --visibility public

# Or via web UI: Settings → Change visibility → Make public
```

#### Step 3: Update Local Repository

```bash
cd /home/thinkube/thinkube/thinkube-control/

# Update remote URL
git remote set-url origin git@github.com:thinkube/thinkube-control.git

# Verify
git remote -v

# Pull to ensure sync
git pull
```

#### Step 4: Update Documentation References

Files to update:
- `/home/thinkube/thinkube/CLAUDE.md`
- `/home/thinkube/thinkube/README.md`
- Any deployment playbooks referencing the repository

### Week 3 Deliverables Checklist

- [ ] All thinkube-control files have headers
- [ ] Security audit passed
- [ ] LICENSE and NOTICE files verified
- [ ] Repository transferred to thinkube org
- [ ] Repository made public
- [ ] Local repository remote updated
- [ ] Documentation updated with new URL
- [ ] First public repository live! 🎉

---

## Week 4: Main Repository Goes Public

**Status**: PRIVATE → PUBLIC
**Risk Level**: MEDIUM
**Repository**: `thinkube/thinkube`

### Objectives
1. Final review of Week 2 work
2. Configure GitHub repository features
3. Make repository public
4. Monitor for any issues

### Task 4.1: Final Review

```bash
# Re-run security scans
grep -r "password.*=" . --include="*.yaml" | grep -v "lookup\|env"

# Verify all headers present
find ansible/ -name "*.yaml" -exec grep -L "Copyright" {} \; | wc -l
# Should be 0

# Check git status
git status
# Should be clean
```

### Task 4.2: GitHub Configuration

#### Enable Features

Via GitHub web UI or CLI:

```bash
# Enable Issues
gh repo edit thinkube/thinkube --enable-issues

# Enable Discussions
gh repo edit thinkube/thinkube --enable-discussions

# Enable Wiki (optional)
gh repo edit thinkube/thinkube --enable-wiki
```

#### Create Issue Templates

**`.github/ISSUE_TEMPLATE/bug_report.md`**:
```markdown
---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. ...
2. ...

**Expected behavior**
What you expected to happen.

**Environment:**
- Thinkube version:
- OS: [e.g., Ubuntu 24.04]
- Kubernetes: [e.g., MicroK8s 1.30]

**Additional context**
Any other context about the problem.
```

**`.github/ISSUE_TEMPLATE/feature_request.md`**:
```markdown
---
name: Feature request
about: Suggest an idea for Thinkube
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other approaches you considered.

**Additional context**
Any other context or screenshots.
```

#### Configure Branch Protection

```bash
# Protect main branch
gh api repos/thinkube/thinkube/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":[]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions=null
```

### Task 4.3: Basic GitHub Actions

**`.github/workflows/ansible-lint.yml`**:
```yaml
name: Ansible Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run ansible-lint
        uses: ansible/ansible-lint-action@main
        with:
          args: "ansible/"
```

**`.github/workflows/yaml-lint.yml`**:
```yaml
name: YAML Lint

on: [push, pull_request]

jobs:
  yamllint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: yaml-lint
        uses: ibiqlik/action-yamllint@v3
```

### Task 4.4: Make Public

```bash
# Final commit before going public
git add .
git commit -m "docs: Prepare repository for public release

- All copyright headers added
- Security audit completed
- Public documentation created
- GitHub configuration added

Ready for public visibility.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push

# Make repository public
gh repo edit thinkube/thinkube --visibility public
```

### Task 4.5: Monitor Initial Issues

Check for:
- Broken links in documentation
- Missing files or resources
- Community questions in issues
- Any security concerns raised

### Week 4 Deliverables Checklist

- [ ] Final security review completed
- [ ] Issue templates created
- [ ] Branch protection configured
- [ ] GitHub Actions set up
- [ ] Repository made public
- [ ] Documentation verified
- [ ] Initial monitoring completed
- [ ] Main repository is public! 🎉

---

## Week 5: Installer Separation and Public Release

**Status**: → PUBLIC (🚀 LAUNCH)
**Risk Level**: HIGH (this is the public announcement)
**Repository**: Create `thinkube/thinkube-installer`

### Objectives
1. Extract installer to separate repository
2. Set up multi-architecture builds
3. Create public installation script
4. Make installer public (this is the announcement!)

### Task 5.1: Extract Installer Repository

#### Create New Repository

```bash
# Via GitHub CLI
gh repo create thinkube/thinkube-installer \
    --public \
    --description "Official installer for Thinkube platform" \
    --homepage "https://thinkube.com"
```

#### Extract with History

Use `git filter-branch` or `git subtree`:

```bash
# Method 1: git filter-branch (preserves history)
cd /tmp
git clone git@github.com:thinkube/thinkube.git thinkube-installer
cd thinkube-installer

# Keep only installer directory
git filter-branch --prune-empty --subdirectory-filter installer HEAD

# Update remote
git remote set-url origin git@github.com:thinkube/thinkube-installer.git
git push -u origin main

# Method 2: git subtree (simpler, less history)
cd /home/thinkube/thinkube
git subtree split --prefix=installer -b installer-split
cd /tmp
git clone git@github.com:thinkube/thinkube-installer.git
cd thinkube-installer
git pull /home/thinkube/thinkube installer-split
git push origin main
```

### Task 5.2: Set Up CI/CD for Builds

**`.github/workflows/build.yml`**:
```yaml
name: Build Installer

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:

jobs:
  build-amd64:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Build frontend
        run: |
          cd frontend
          npm install
          npm run build

      - name: Build Tauri app (amd64)
        run: |
          cd frontend
          npm run tauri build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: installer-amd64
          path: frontend/src-tauri/target/release/bundle/deb/*.deb

  build-arm64:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Build for ARM64
        run: |
          # Cross-compile for ARM64
          # Similar steps as amd64 but with --target aarch64

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: installer-arm64
          path: frontend/src-tauri/target/aarch64-unknown-linux-gnu/release/bundle/deb/*.deb

  release:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: [build-amd64, build-arm64]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            installer-amd64/*.deb
            installer-arm64/*.deb
          generate_release_notes: true
```

### Task 5.3: Update Installation Script

**`scripts/install.sh`** - Update URLs to new repository:

```bash
#!/bin/bash
# Thinkube Installer
# Usage: curl -sSL https://raw.githubusercontent.com/thinkube/thinkube-installer/main/scripts/install.sh | bash

set -e

REPO="thinkube/thinkube-installer"
ARCH=$(dpkg --print-architecture)

echo "🚀 Installing Thinkube..."
echo "Architecture: $ARCH"

# Get latest release
LATEST_RELEASE=$(curl -s https://api.github.com/repos/$REPO/releases/latest | grep "tag_name" | cut -d '"' -f 4)

if [ -z "$LATEST_RELEASE" ]; then
    echo "❌ Error: Could not determine latest release"
    exit 1
fi

echo "Latest version: $LATEST_RELEASE"

# Download .deb package
DEB_URL="https://github.com/$REPO/releases/download/$LATEST_RELEASE/thinkube-installer_${ARCH}.deb"

echo "Downloading from: $DEB_URL"
curl -LO "$DEB_URL"

# Install
sudo dpkg -i "thinkube-installer_${ARCH}.deb"
sudo apt-get install -f -y

echo "✅ Thinkube installer installed!"
echo ""
echo "To start installation, run:"
echo "  thinkube-installer"
```

### Task 5.4: Remove Installer from Main Repo

```bash
cd /home/thinkube/thinkube

# Remove installer directory
git rm -r installer/

# Update .gitignore if needed
echo "installer/" >> .gitignore

# Update README to point to installer repo
# Update CLAUDE.md

# Commit
git add .
git commit -m "refactor: Move installer to separate repository

Installer now lives at:
https://github.com/thinkube/thinkube-installer

This reduces main repository size and allows independent versioning.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

### Task 5.5: Announcement

When ready to announce:

1. **Create Release** in thinkube-installer with v1.0.0 tag
2. **Update Documentation** with installation instructions
3. **Test Installation** from public URL:
   ```bash
   curl -sSL https://raw.githubusercontent.com/thinkube/thinkube-installer/main/scripts/install.sh | bash
   ```
4. **Announce** (optional):
   - Post on GitHub Discussions
   - Social media (Twitter, LinkedIn, Reddit r/selfhosted)
   - Hacker News Show HN
   - Dev.to or Medium blog post

### Week 5 Deliverables Checklist

- [ ] Installer repository created
- [ ] CI/CD builds working for amd64 and arm64
- [ ] .deb packages available in releases
- [ ] Install script works from public URL
- [ ] Installer removed from main repo
- [ ] Documentation updated
- [ ] v1.0.0 release created
- [ ] 🚀 **THINKUBE IS LAUNCHED!**

---

## Risk Mitigation

### If Issues Found After Going Public

**Week 3-4 (Repos Public, Installer Still Private)**:
- ✅ Can fix issues without public impact
- ✅ Installer not yet public = not advertised
- ✅ Early adopters can test privately

**Week 5 (After Installer Public)**:
- ⚠️ Issues more visible
- ⚠️ Need quick response to community issues
- ⚠️ Monitor GitHub issues/discussions closely

### Contingency Plans

1. **Critical Security Issue Found**:
   - Immediately create private security advisory
   - Fix in private branch
   - Release patch with advisory
   - Notify any known users

2. **Installer Doesn't Work**:
   - Don't announce yet
   - Fix and test
   - Push new release
   - Test again before announcing

3. **Documentation Issues**:
   - Quick fixes via PR
   - Community can help improve
   - Treat as enhancement opportunities

---

## Success Criteria

### Week 2
- [ ] All copyright headers added
- [ ] No secrets in repository or history
- [ ] Public documentation complete
- [ ] Repository ready (but still private)

### Week 3
- [ ] thinkube-control is public
- [ ] All headers present
- [ ] No community issues raised

### Week 4
- [ ] Main repository is public
- [ ] GitHub features configured
- [ ] No critical issues reported

### Week 5
- [ ] Installer works from public URL
- [ ] Builds available for both architectures
- [ ] Documentation complete
- [ ] **Thinkube successfully launched** 🎉

---

## See Also

- [CLI Tools Inventory](CODE_SERVER_CLI_TOOLS.md)
- [code-server Enhancement Plan](CODE_SERVER_ENHANCEMENT_PLAN.md)
- [Phase 4.5 Timeline](PHASE_4_5_TIMELINE.md)
- [MVP Plan](MVP_FINAL_PLAN.md)
