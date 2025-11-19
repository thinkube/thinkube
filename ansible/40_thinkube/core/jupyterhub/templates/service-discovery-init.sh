#!/bin/bash
# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Service Discovery Init Script for Jupyter Pods
# Queries all service discovery ConfigMaps and generates environment variable file
# This runs as an init container before the main Jupyter container starts

set -e

OUTPUT_DIR="/service-config"
SERVICE_ENV_FILE="$OUTPUT_DIR/service-env-jh.sh"

echo "========================================"
echo "Thinkube Service Discovery Init"
echo "========================================"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Write header
{
  echo "#!/bin/bash"
  echo "# Auto-generated from service discovery ConfigMaps"
  echo "# DO NOT EDIT MANUALLY - Changes will be overwritten on pod restart"
  echo "# Generated at pod startup"
  echo ""
} > "$SERVICE_ENV_FILE"

# Query all service discovery ConfigMaps
echo "Querying service discovery ConfigMaps..."
CONFIGMAPS=$(kubectl get configmaps --all-namespaces -l thinkube.io/managed=true -o json 2>/dev/null || echo '{"items":[]}')

# Count ConfigMaps found
CONFIGMAP_COUNT=$(echo "$CONFIGMAPS" | jq '.items | length')
echo "Found $CONFIGMAP_COUNT service discovery ConfigMaps"

if [ "$CONFIGMAP_COUNT" -eq 0 ]; then
    echo "# No environment variables defined by services" >> "$SERVICE_ENV_FILE"
    echo "No services found - environment file created with no variables"
    chmod +x "$SERVICE_ENV_FILE"
    exit 0
fi

# Extract and process environment variables
ENV_VAR_COUNT=0

# Process each ConfigMap - use base64 to preserve complete YAML documents
echo "$CONFIGMAPS" | jq -r '.items[] | select(.data."service.yaml" != null) | .data."service.yaml" | @base64' | while IFS= read -r encoded_yaml; do
    # Decode base64 to get complete YAML document
    service_yaml=$(echo "$encoded_yaml" | base64 -d)

    # Get count of environment variables in this ConfigMap
    var_count=$(echo "$service_yaml" | yq eval '.service.environment_variables | length' - 2>/dev/null || echo "0")

    if [ "$var_count" -gt 0 ]; then
        # Process each environment variable
        for i in $(seq 0 $((var_count - 1))); do
            VAR_NAME=$(echo "$service_yaml" | yq eval ".service.environment_variables[$i].name" - 2>/dev/null)

            # Check if it has a direct value
            VAR_VALUE=$(echo "$service_yaml" | yq eval ".service.environment_variables[$i].value" - 2>/dev/null)

            if [ "$VAR_VALUE" != "null" ] && [ -n "$VAR_VALUE" ]; then
                # Direct value - add to env file
                echo "export $VAR_NAME=\"$VAR_VALUE\"" >> "$SERVICE_ENV_FILE"
                ENV_VAR_COUNT=$((ENV_VAR_COUNT + 1))
            else
                # Check if it has valueFrom.secretKeyRef
                SECRET_NAMESPACE=$(echo "$service_yaml" | yq eval ".service.environment_variables[$i].valueFrom.secretKeyRef.namespace" - 2>/dev/null)
                SECRET_NAME=$(echo "$service_yaml" | yq eval ".service.environment_variables[$i].valueFrom.secretKeyRef.name" - 2>/dev/null)
                SECRET_KEY=$(echo "$service_yaml" | yq eval ".service.environment_variables[$i].valueFrom.secretKeyRef.key" - 2>/dev/null)

                if [ "$SECRET_NAME" != "null" ] && [ "$SECRET_KEY" != "null" ]; then
                    # Fetch from secret
                    if [ "$SECRET_NAMESPACE" != "null" ] && [ -n "$SECRET_NAMESPACE" ]; then
                        SECRET_VALUE=$(kubectl get secret -n "$SECRET_NAMESPACE" "$SECRET_NAME" -o jsonpath="{.data.$SECRET_KEY}" 2>/dev/null | base64 -d || true)
                    else
                        SECRET_VALUE=$(kubectl get secret "$SECRET_NAME" -o jsonpath="{.data.$SECRET_KEY}" 2>/dev/null | base64 -d || true)
                    fi

                    if [ -n "$SECRET_VALUE" ]; then
                        echo "export $VAR_NAME=\"$SECRET_VALUE\"" >> "$SERVICE_ENV_FILE"
                        ENV_VAR_COUNT=$((ENV_VAR_COUNT + 1))
                        echo "✅ Fetched $VAR_NAME from secret $SECRET_NAME"
                    else
                        echo "⊘ Skipped $VAR_NAME (secret $SECRET_NAME not found)"
                    fi
                fi
            fi
        done
    fi
done

# Create kubeconfig from pod service account
# NOTE: KUBECONFIG is NOT exported to service-env-jh.sh (environment-specific, not a shared service)
# Instead, it's set directly in the pod's startup command in jupyterhub-values.yaml.j2
echo ""
echo "Configuring Kubernetes access..."
KUBECONFIG_PATH="$OUTPUT_DIR/kube-config"
SERVICEACCOUNT="/var/run/secrets/kubernetes.io/serviceaccount"

if [ -f "$SERVICEACCOUNT/token" ]; then
    KUBE_TOKEN=$(cat $SERVICEACCOUNT/token)
    KUBE_CA=$(cat $SERVICEACCOUNT/ca.crt | base64 -w0)

    # Create kubeconfig without heredoc to avoid indentation issues
    echo "apiVersion: v1" > "$KUBECONFIG_PATH"
    echo "kind: Config" >> "$KUBECONFIG_PATH"
    echo "clusters:" >> "$KUBECONFIG_PATH"
    echo "- cluster:" >> "$KUBECONFIG_PATH"
    echo "    certificate-authority-data: $KUBE_CA" >> "$KUBECONFIG_PATH"
    echo "    server: https://kubernetes.default.svc.cluster.local:443" >> "$KUBECONFIG_PATH"
    echo "  name: default-cluster" >> "$KUBECONFIG_PATH"
    echo "contexts:" >> "$KUBECONFIG_PATH"
    echo "- context:" >> "$KUBECONFIG_PATH"
    echo "    cluster: default-cluster" >> "$KUBECONFIG_PATH"
    echo "    user: default-user" >> "$KUBECONFIG_PATH"
    echo "    namespace: default" >> "$KUBECONFIG_PATH"
    echo "  name: default-context" >> "$KUBECONFIG_PATH"
    echo "current-context: default-context" >> "$KUBECONFIG_PATH"
    echo "users:" >> "$KUBECONFIG_PATH"
    echo "- name: default-user" >> "$KUBECONFIG_PATH"
    echo "  user:" >> "$KUBECONFIG_PATH"
    echo "    token: $KUBE_TOKEN" >> "$KUBECONFIG_PATH"

    # KUBECONFIG is NOT added to SERVICE_ENV_FILE - it's environment-specific
    echo "✅ Created kubeconfig from service account"
else
    echo "⊘ Service account token not found, skipping kubeconfig"
fi

# Make executable
chmod +x "$SERVICE_ENV_FILE"

echo ""
echo "✅ Service discovery complete"
echo "   Environment file: $SERVICE_ENV_FILE"
echo "   Variables configured: $ENV_VAR_COUNT"
echo "========================================"
