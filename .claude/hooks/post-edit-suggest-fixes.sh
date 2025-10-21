#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Post-edit hook that suggests fixes using Claude

if [[ "$1" =~ \.(yaml|yml)$ ]] && [[ "$1" =~ ansible/ ]]; then
    # Check for common issues
    if grep -q "ignore_errors:\|failed_when: false" "$1"; then
        echo "🤖 Detected error suppression. Asking Claude for better approach..."
        
        claude --no-interactive <<EOF
The playbook at $1 uses ignore_errors or failed_when: false.
Suggest a better error handling approach that:
1. Properly handles expected failures
2. Fails fast on unexpected errors
3. Uses proper conditionals or blocks

Context from playbook:
$(grep -B5 -A5 "ignore_errors:\|failed_when: false" "$1")

Provide specific code changes.
EOF
    fi
    
    # Check for complex shell scripts
    if grep -E "bash -c.*\n.*\n.*\n" "$1"; then
        echo "🤖 Complex shell script detected. Claude will suggest template approach..."
        
        claude --no-interactive <<EOF
This playbook has complex embedded shell scripts that should use templates.
Show how to convert this to use an Ansible template instead.

Shell script found:
$(grep -A20 "bash -c" "$1" | head -30)

Provide the template file content and the updated task.
EOF
    fi
fi