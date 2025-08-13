#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Pre-commit hook that uses Claude to review changed playbooks

# Get list of staged Ansible playbooks
PLAYBOOKS=$(git diff --cached --name-only | grep -E "ansible/.*\.(yaml|yml)$")

if [ -n "$PLAYBOOKS" ]; then
    echo "🤖 Claude reviewing staged Ansible playbooks..."
    
    for playbook in $PLAYBOOKS; do
        echo "Reviewing: $playbook"
        
        # Get the staged content (not working directory)
        CONTENT=$(git show ":$playbook")
        
        claude --no-interactive <<EOF | tee /tmp/review-$$.txt
Review this Ansible playbook for critical issues only:
- ignore_errors or failed_when: false
- Syntax errors
- Hardcoded secrets or passwords
- Missing variable validation
- Shell scripts that need templates

Be brief - only mention actual problems.

$CONTENT
EOF
        
        if grep -iE "(critical|error|password|secret|ignore_errors)" /tmp/review-$$.txt; then
            echo "❌ Critical issues found. Fix before committing."
            rm -f /tmp/review-$$.txt
            exit 1
        fi
    done
    
    echo "✅ All playbooks passed Claude review"
    rm -f /tmp/review-$$.txt
fi