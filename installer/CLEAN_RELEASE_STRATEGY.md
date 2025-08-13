# Clean Release Strategy for Thinkube Public Repository

## Overview
Create a fresh public repository without git history to ensure no sensitive data leaks.

## Strategy: Fresh Repository with Clean History

### Why Fresh Start?
1. **Security**: Absolute certainty no credentials/secrets in history
2. **Clean slate**: No development experiments or failed attempts
3. **Professional**: Clean commit history from day one
4. **Size**: Smaller repository without historical baggage

### Process

## Phase 1: Documentation Cleanup

### Documents to KEEP (essential for users)
```
Core Documentation:
- README.md (updated for public)
- LICENSE
- COPYRIGHT_HEADER.md
- CONTRIBUTING.md (new)
- CODE_OF_CONDUCT.md (new)
- SECURITY.md (new)

Architecture & Specs:
- docs/specs/*.md (all specification documents)
- docs/architecture-infrastructure/VARIABLE_HANDLING.md
- docs/architecture-infrastructure/ERROR_HANDLING.md
- docs/architecture-k8s/COMPONENT_ARCHITECTURE.md

User Guides:
- docs/user_guide/*.md (all user guides)
- installer/README.md
- thinkube-control/README.md

Development:
- .claude/agents/*.md (AI assistant configs)
- CLAUDE.md (for Claude Code users)
```

### Documents to ARCHIVE (move to private wiki/docs)
```
Development History:
- *_MILESTONE*.md files
- START_HERE*.md (development tracking)
- DNS_AND_HARBOR_FIX_SUMMARY.md
- LXD_REMOVAL_PROGRESS.md
- DEPLOYMENT_REORDER_PLAN.md
- REMOTE_*.md files

Work-in-Progress:
- installer/DEPLOYMENT_STATE_FIX.md
- installer/THINGS_THAT_NEED_TO_BE_FIXED_IN_INSTALLER.md
- installer/TEST_DEPLOYMENT_STATE.md
- installer/WORKFLOW_PLAN.md
- All FIX/PLAN documents

Internal Architecture:
- docs/architecture-k8s/MIGRATION_*.md
- docs/architecture-k8s/UNUSED_PLAYBOOKS.md
- CORE-*.md files (issue-specific docs)
```

### Documents to CREATE for public
```
- CONTRIBUTING.md - How to contribute
- CODE_OF_CONDUCT.md - Community standards
- SECURITY.md - Security policy
- CHANGELOG.md - Version history
- docs/INSTALLATION.md - Getting started guide
- docs/FAQ.md - Frequently asked questions
```

## Phase 2: Code Cleanup

### Security Audit Checklist
```bash
# Search for sensitive patterns
grep -r "example.com" --exclude-dir=.git
grep -r "password\|token\|secret\|key" --exclude-dir=.git
grep -r "192\.168\|10\.0\|172\." --exclude-dir=.git

# Files to review carefully
- inventory/group_vars/all.yml
- Any .env files
- Configuration templates
```

### Replace Sensitive Data
- `example.com` → `example.com` or `{{ domain_name }}`
- Private IPs → Documentation ranges (192.0.2.0/24)
- Remove any hardcoded credentials
- Remove personal information

## Phase 3: Fresh Repository Creation

### Step 1: Prepare Clean Export
```bash
# Create a clean working directory
mkdir ~/thinkube-public
cd ~/thinkube-public

# Export current code WITHOUT history
cd ~/thinkube
git archive --format=tar HEAD | (cd ~/thinkube-public && tar xf -)

# Remove unwanted files
cd ~/thinkube-public
rm -rf .git
rm -f .env* 
rm -rf */venv */node_modules
rm -f *_MILESTONE*.md
rm -f START_HERE*.md
# ... remove other development docs

# Add license headers
./installer/scripts/add-license-headers.py .
```

### Step 2: Initialize New Repository
```bash
cd ~/thinkube-public
git init
git add .
git commit -m "Initial public release of Thinkube

Thinkube is a home-based development platform built on Kubernetes,
designed specifically for AI applications and agents.

Features:
- Kubernetes-based infrastructure
- AI/ML workload support with GPU
- GitOps deployment workflow
- Professional installer with GUI
- Multi-architecture support (AMD64/ARM64)

Licensed under Apache 2.0"
```

### Step 3: Create GitHub Repository
1. Create new PUBLIC repository: `github.com/thinkube/thinkube`
2. Do NOT import from existing repository
3. Push clean repository:
```bash
git remote add origin https://github.com/thinkube/thinkube.git
git branch -M main
git push -u origin main
```

### Step 4: Archive Private Repository
1. Rename current private repo to `thinkube-private-archive`
2. Keep for reference and history
3. Mark as archived in GitHub

## Phase 4: Release Preparation

### Pre-Release Tasks
1. **Legal**
   - [x] Add license headers to all files
   - [ ] Create NOTICE file with attributions
   - [ ] Verify LICENSE file

2. **Documentation**
   - [ ] Update README for public audience
   - [ ] Create installation guide
   - [ ] Add contribution guidelines
   - [ ] Write security policy

3. **Build Artifacts**
   - [ ] Build Debian packages (AMD64/ARM64)
   - [ ] Create checksums
   - [ ] Test installation process

### Release v1.0.0
```bash
# Tag the release
git tag -a v1.0.0 -m "First public release"
git push origin v1.0.0

# GitHub Release includes:
- thinkube-installer_1.0.0_amd64.deb
- thinkube-installer_1.0.0_arm64.deb
- SHA256SUMS
- Release notes
```

## Phase 5: Public Launch

### Soft Launch (Week 1)
- Limited announcement
- Monitor for issues
- Quick fixes if needed

### Full Launch (Week 2+)
- Announce on:
  - Reddit (r/selfhosted, r/kubernetes)
  - Hacker News
  - Twitter/X
  - LinkedIn
- Create demo video
- Write blog post

## Benefits of Clean Release

1. **No Historical Baggage**
   - No leaked secrets in history
   - No embarrassing commits
   - Clean, professional history

2. **Smaller Repository**
   - No binary blobs in history
   - No large deleted files
   - Faster to clone

3. **Clear Licensing**
   - All files have proper headers from commit #1
   - Clean copyright history
   - No ambiguity

4. **Professional Appearance**
   - Looks like established project
   - No "work in progress" feel
   - Ready for contributors

## Maintaining Both Repositories

### Private Archive (thinkube-private-archive)
- Keep all history
- Reference for development decisions
- Internal documentation
- Development experiments

### Public Repository (thinkube)
- Clean, professional codebase
- Public-safe documentation
- Community-focused
- Regular releases

## Checklist Before Going Public

- [ ] All sensitive data removed
- [ ] License headers added
- [ ] Documentation cleaned up
- [ ] Fresh git repository created
- [ ] Debian packages built and tested
- [ ] Installation guide written
- [ ] Community files added (CONTRIBUTING, etc.)
- [ ] Security audit complete
- [ ] Domain references genericized
- [ ] First release tagged

## Alternative: BFG Repo-Cleaner

If you prefer to keep some history:
```bash
# Clean sensitive data from history
bfg --replace-text passwords.txt repo.git
bfg --delete-files "*.env" repo.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**Recommendation**: Fresh start is safer and cleaner for public release.

---
*Last updated: January 2025*