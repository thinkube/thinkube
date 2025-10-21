# Apache Superset - Data Visualization and Exploration

## Overview

Apache Superset is a modern data exploration and visualization platform for metrics, logs, and business intelligence.

**License**: Apache-2.0 ✅

## Components

- **Superset**: Web application for data visualization and dashboards
- **Valkey**: BSD-licensed Redis fork for caching (uses existing Thinkube Valkey deployment)
- **PostgreSQL**: Metadata database (uses existing Thinkube PostgreSQL)
- **Keycloak**: SSO integration for authentication

## Architecture

```
User → Ingress (superset.{{ domain_name }})
          ↓
      Superset Pod
          ├→ PostgreSQL (metadata)
          ├→ Valkey (cache)
          ├→ Keycloak (SSO)
          └→ Data Sources (Prometheus, OpenSearch, etc.)
```

## Playbooks

- `00_install.yaml` - Orchestrator playbook (runs all deployment steps)
- `10_configure_keycloak.yaml` - Configure Keycloak SSO client
- `11_deploy.yaml` - Deploy Apache Superset
- `12_configure_datasources.yaml` - Configure data sources (Prometheus, PostgreSQL, OpenSearch, ClickHouse)
- `17_configure_discovery.yaml` - Configure service discovery
- `18_test.yaml` - Test deployment
- `19_rollback.yaml` - Rollback procedures

## Deployment

**Quick start** (recommended):
```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/superset/00_install.yaml
```

This orchestrator playbook runs all deployment steps automatically:
1. Deploy Superset
2. Configure Keycloak SSO
3. Configure data sources
4. Run tests

**Step-by-step deployment**:
```bash
cd ~/thinkube

# Step 1: Configure Keycloak
./scripts/run_ansible.sh ansible/40_thinkube/optional/superset/10_configure_keycloak.yaml

# Step 2: Deploy Superset
./scripts/run_ansible.sh ansible/40_thinkube/optional/superset/11_deploy.yaml

# Step 3: Configure data sources
./scripts/run_ansible.sh ansible/40_thinkube/optional/superset/12_configure_datasources.yaml

# Step 4: Configure service discovery
./scripts/run_ansible.sh ansible/40_thinkube/optional/superset/17_configure_discovery.yaml

# Step 5: Run tests
./scripts/run_ansible.sh ansible/40_thinkube/optional/superset/18_test.yaml
```

**Rollback**:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/superset/19_rollback.yaml
```

## Access

- **URL**: https://superset.{{ domain_name }}
- **Authentication**: Keycloak SSO
- **Default Admin**: {{ admin_username }}

## Data Sources

Superset automatically configures connections to available Thinkube data sources:

**Always configured:**
- **Prometheus** - Metrics and time-series data
- **PostgreSQL** - Relational database for application data
- **OpenSearch** - Logs, events, and full-text search

**Conditionally configured (if deployed):**
- **ClickHouse** - Analytics database for OLAP queries (detected automatically)

## Features

- ✅ Apache-2.0 license (compatible with commercial use)
- ✅ Rich visualization capabilities
- ✅ Supports multiple data sources
- ✅ SQL Lab for data exploration
- ✅ Custom dashboards and charts
- ✅ Role-based access control
- ✅ Apache Foundation project

## Why Valkey?

Valkey is a high-performance key-value datastore used for Superset caching:
- ✅ BSD-3-Clause license (compatible with commercial use)
- ✅ Redis-protocol compatible (drop-in Redis replacement)
- ✅ Linux Foundation project
- ✅ Backed by AWS, Google, Oracle
- ✅ Active development and community
- ✅ Already deployed in Thinkube for shared use

Superset connects to the existing Valkey deployment at `valkey.valkey.svc.cluster.local:6379`.

## License

Apache-2.0
