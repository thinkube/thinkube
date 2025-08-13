#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# ansible/40_thinkube/core/gitea/deploy_unattended.sh
# Description:
#   Deploy Gitea with fully unattended installation
#   Creates admin user, configures OAuth2, and sets up default repositories
#
# Usage:
#   cd ~/thinkube
#   export ADMIN_PASSWORD="your-secure-password"
#   ./ansible/40_thinkube/core/gitea/deploy_unattended.sh
#
# 🤖 [AI-assisted]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Starting Gitea Unattended Installation${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"

# Check environment variable
if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${RED}ERROR: ADMIN_PASSWORD environment variable must be set${NC}"
    echo -e "${YELLOW}Please run: export ADMIN_PASSWORD='your-secure-password'${NC}"
    exit 1
fi

# Change to project root
cd ~/thinkube

# Step 1: Deploy Gitea
echo -e "\n${GREEN}Step 1: Deploying Gitea...${NC}"
./scripts/run_ansible.sh ansible/40_thinkube/core/gitea/10_deploy.yaml

# Step 2: Run tests
echo -e "\n${GREEN}Step 2: Running deployment tests...${NC}"
./scripts/run_ansible.sh ansible/40_thinkube/core/gitea/18_test.yaml

# Step 3: Configure unattended
echo -e "\n${GREEN}Step 3: Configuring Gitea (unattended)...${NC}"
./scripts/run_ansible.sh ansible/40_thinkube/core/gitea/16_configure_unattended.yaml

echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Gitea Unattended Installation Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "\nGitea is available at: ${YELLOW}https://git.thinkube.com${NC}"
echo -e "Login with Keycloak SSO or use the admin API token:"
echo -e "${YELLOW}kubectl get secret -n gitea gitea-admin-token -o jsonpath='{.data.token}' | base64 -d${NC}"
echo -e "\n${GREEN}Default repositories created in 'thinkube-deployments' organization${NC}"