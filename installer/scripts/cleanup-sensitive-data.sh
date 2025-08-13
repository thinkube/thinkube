#!/bin/bash
# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0
#
# Script to clean sensitive data before public release
# This should be run on a COPY of the repository, not the original

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Thinkube Sensitive Data Cleanup ===${NC}"
echo "This script will clean sensitive data from the repository"
echo "Make sure you're running this on a COPY, not the original!"
echo
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Get the repository root (two levels up from installer/scripts)
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo -e "\n${YELLOW}Repository root: $REPO_ROOT${NC}"

# Backup current state
echo -e "\n${GREEN}Creating backup of current state...${NC}"
BACKUP_FILE="../thinkube-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
tar --exclude=.git --exclude=node_modules --exclude=venv -czf "$BACKUP_FILE" .
echo "Backup created: $BACKUP_FILE"

# 1. Replace domain references
echo -e "\n${GREEN}1. Replacing domain references...${NC}"

# Count occurrences first
COUNT=$(grep -r "cmxela\.com" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv 2>/dev/null | wc -l || true)
echo "Found $COUNT occurrences of example.com"

if [ "$COUNT" -gt 0 ]; then
    # Replace in all text files
    find . -type f \( \
        -name "*.md" -o \
        -name "*.yaml" -o \
        -name "*.yml" -o \
        -name "*.sh" -o \
        -name "*.py" -o \
        -name "*.js" -o \
        -name "*.ts" -o \
        -name "*.vue" \
    \) -not -path "./.git/*" -not -path "*/node_modules/*" -not -path "*/venv/*" \
    -exec sed -i 's/cmxela\.com/example.com/g' {} \;
    
    echo "Replaced example.com with example.com"
fi

# 2. Replace private IP addresses
echo -e "\n${GREEN}2. Replacing private IP addresses...${NC}"

# Replace specific BCN IPs in scripts
if [ -f "scripts/10_install-tools.sh" ]; then
    sed -i 's/192\.168\.1\.101/192.0.2.101/g' scripts/10_install-tools.sh
    sed -i 's/192\.168\.1\.102/192.0.2.102/g' scripts/10_install-tools.sh
    sed -i 's/192\.168\.1\.0/192.0.2.0/g' scripts/10_install-tools.sh
    echo "Updated scripts/10_install-tools.sh"
fi

# Replace ZeroTier IPs
if [ -f "scripts/use-zerotier.sh" ]; then
    sed -i 's/192\.168\.191\./192.0.2./g' scripts/use-zerotier.sh
    echo "Updated scripts/use-zerotier.sh"
fi

# Replace in utility scripts
if [ -d "scripts/utilities" ]; then
    find scripts/utilities -name "*.sh" -exec sed -i 's/192\.168\.1\./192.0.2./g' {} \;
    echo "Updated scripts/utilities/*.sh"
fi

# 3. Remove specific server names
echo -e "\n${GREEN}3. Replacing specific server names...${NC}"

# Replace vilanova references with generic names
find . -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" \) \
    -not -path "./.git/*" -not -path "*/node_modules/*" \
    -exec sed -i 's/vilanova1/node1/g; s/vilanova2/node2/g; s/vilanova3/node3/g' {} \;

echo "Replaced vilanova references with generic node names"

# 4. Clean up GitHub issue templates
echo -e "\n${GREEN}4. Cleaning GitHub issue templates...${NC}"

if [ -d ".github/issues" ]; then
    find .github/issues -name "*.md" -exec sed -i 's/registry\.cmxela\.com/registry.example.com/g' {} \;
    echo "Updated GitHub issue templates"
fi

# 5. Remove development documentation
echo -e "\n${GREEN}5. Removing development documentation...${NC}"

# List of files to remove
FILES_TO_REMOVE=(
    "*_MILESTONE*.md"
    "START_HERE*.md"
    "DNS_AND_HARBOR_FIX_SUMMARY.md"
    "LXD_REMOVAL_PROGRESS.md"
    "DEPLOYMENT_REORDER_PLAN.md"
    "REMOTE_*.md"
    "CORE-*.md"
    "*_FIX.md"
    "*_PLAN.md"
    "THINGS_THAT_NEED_TO_BE_FIXED*.md"
    "TEST_DEPLOYMENT_STATE.md"
    "WORKFLOW_PLAN.md"
    "clear_deployment_state.md"
)

for pattern in "${FILES_TO_REMOVE[@]}"; do
    COUNT=$(find . -name "$pattern" -not -path "./.git/*" 2>/dev/null | wc -l || true)
    if [ "$COUNT" -gt 0 ]; then
        find . -name "$pattern" -not -path "./.git/*" -exec rm -v {} \;
    fi
done

# 6. Remove temporary and backup files
echo -e "\n${GREEN}6. Removing temporary files...${NC}"

find . -type f \( \
    -name "*.backup" -o \
    -name "*.bak" -o \
    -name "*.tmp" -o \
    -name "*.swp" -o \
    -name "*~" -o \
    -name ".DS_Store" \
\) -not -path "./.git/*" -exec rm -v {} \;

# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -exec rm -f {} +

echo "Removed temporary and cache files"

# 7. Clean inventory files
echo -e "\n${GREEN}7. Cleaning inventory files...${NC}"

if [ -f "inventory/group_vars/baremetal.yml" ]; then
    # Comment out LXD-specific configurations
    sed -i 's/^lxd_/#lxd_/g' inventory/group_vars/baremetal.yml
    echo "Cleaned inventory/group_vars/baremetal.yml"
fi

# 8. Final verification
echo -e "\n${GREEN}8. Running final verification...${NC}"

echo -e "\n${YELLOW}Checking for remaining sensitive patterns:${NC}"

# Check for domain
REMAINING=$(grep -r "cmxela" --exclude-dir=.git --exclude-dir=node_modules 2>/dev/null | wc -l || true)
if [ "$REMAINING" -gt 0 ]; then
    echo -e "${RED}Warning: Found $REMAINING remaining references to cmxela${NC}"
    grep -r "cmxela" --exclude-dir=.git --exclude-dir=node_modules | head -5
else
    echo -e "${GREEN}✓ No cmxela references found${NC}"
fi

# Check for private IPs
REMAINING=$(grep -r "192\.168\." --exclude-dir=.git --exclude-dir=node_modules 2>/dev/null | wc -l || true)
if [ "$REMAINING" -gt 0 ]; then
    echo -e "${YELLOW}Note: Found $REMAINING references to 192.168.x.x (review if needed)${NC}"
else
    echo -e "${GREEN}✓ No 192.168.x.x references found${NC}"
fi

# Check for vilanova
REMAINING=$(grep -r "vilanova" --exclude-dir=.git --exclude-dir=node_modules 2>/dev/null | wc -l || true)
if [ "$REMAINING" -gt 0 ]; then
    echo -e "${YELLOW}Note: Found $REMAINING references to vilanova (review if needed)${NC}"
else
    echo -e "${GREEN}✓ No vilanova references found${NC}"
fi

echo -e "\n${GREEN}=== Cleanup Complete ===${NC}"
echo "Please review the changes before committing"
echo "Backup saved at: $BACKUP_FILE"
echo
echo "Next steps:"
echo "1. Review all changes with: git diff"
echo "2. Add license headers: ./installer/scripts/add-license-headers.py"
echo "3. Create fresh repository as per CLEAN_RELEASE_STRATEGY.md"