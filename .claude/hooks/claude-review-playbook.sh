#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Claude Code hook that uses Claude to review Ansible playbooks

# Check if the edited file is an Ansible playbook
if [[ "$1" =~ \.(yaml|yml)$ ]] && [[ "$1" =~ ansible/ ]]; then
    echo "🤖 Requesting Claude review of Ansible playbook: $1"
    
    # Create a review prompt
    REVIEW_PROMPT="Please review this Ansible playbook for:
1. Syntax errors or potential runtime failures
2. Use of ignore_errors or failed_when: false
3. Hardcoded values that should be variables (domains, IPs)
4. Improper use of become at playbook level
5. Missing error handling
6. Complex shell scripts that should use templates
7. Any other Ansible best practices violations

Focus on issues that would cause failures or maintenance problems.
Be concise - list only actual problems found.

Playbook content:
$(cat "$1")"

    # Call Claude for review
    claude --no-interactive <<< "$REVIEW_PROMPT" | tee /tmp/playbook-review-$$.txt
    
    # Check if Claude found any issues
    if grep -iE "(error|warning|issue|problem|should|must)" /tmp/playbook-review-$$.txt; then
        echo ""
        echo "⚠️  Claude found potential issues in the playbook!"
        echo "Would you like to address these before committing? (y/n)"
        read -r response
        if [[ "$response" == "y" ]]; then
            echo "Opening playbook for editing..."
            code "$1"
            exit 1  # Prevent commit
        fi
    else
        echo "✅ Claude review passed - no issues found"
    fi
    
    # Cleanup
    rm -f /tmp/playbook-review-$$.txt
fi