# ClickHouse

Component #34 in the Thinkube Platform stack.

## Overview

ClickHouse is a high-performance columnar database management system optimized for online analytical processing (OLAP). Deployed via the Altinity Kubernetes operator, ClickHouse provides real-time analytics capabilities for CVAT annotation tracking, Langfuse LLM observability, and other data-intensive workloads.

**Key Features**:
- **Columnar Storage**: Optimized for analytical queries on large datasets
- **High Performance**: Processes billions of rows per second
- **SQL Interface**: Standard SQL with ClickHouse extensions
- **Real-time Analytics**: Sub-second query response times
- **Dual Protocol Access**: HTTP (port 8123) and native TCP (port 9000)
- **External Access**: HTTPS for HTTP interface, TCP passthrough for native protocol
- **Horizontal Scalability**: Supports sharding and replication (single node in homelab)

## Dependencies

This component depends on the following Thinkube components:

- **Kubernetes (#6)** - Provides the container orchestration platform
- **ACME Certificates (#12)** - Secures HTTPS connections
- **Ingress (#13)** - NGINX Ingress Controller with TCP passthrough

## Prerequisites

```yaml
requirements:
  kubernetes:
    version: "1.34.0"
    provider: "k8s-snap"

  helm:
    repository: "https://helm.altinity.com"
    chart: "altinity/clickhouse"

  storage:
    persistence: true
    size: "10Gi"
    storage_class: "k8s-hostpath"

  networking:
    http_port: 8123
    native_port: 9000
    tcp_passthrough: true

  resources:
    replicas: 1
    shards: 1

  authentication:
    default_user: "default"
    password_source: "ADMIN_PASSWORD environment variable"
```

## Playbooks

### **Main Deployment**
**File**: [10_deploy.yaml](10_deploy.yaml)

Deploys ClickHouse with dual-protocol external access:

- **Variable Validation**
  - Verifies `domain_name`, `kubeconfig`, `admin_username` are defined
  - Checks `admin_password` from `ADMIN_PASSWORD` environment variable
  - Fails deployment if password not set

- **Namespace Creation**
  - Creates `clickhouse` namespace

- **Helm Repository Configuration**
  - Adds Altinity Helm repository: `https://helm.altinity.com`
  - Provides ClickHouse Kubernetes Operator and chart

- **ClickHouse Deployment via Helm**
  - Chart: `altinity/clickhouse`
  - Release name: `clickhouse`
  - Configuration:
    - Replicas: 1 (single node)
    - Shards: 1 (no horizontal partitioning)
    - Default user password: from `ADMIN_PASSWORD`
    - External access: enabled
    - Persistence: 10Gi PVC with `k8s-hostpath` storage class
  - **Note**: Homelab single-node configuration; production should use multiple replicas

- **Pod Readiness Wait**
  - Waits for ClickHouse pod to reach `Running` state
  - Label selector: `app.kubernetes.io/name=clickhouse`
  - Retries: 30 attempts with 10s delay (5 minutes total)

- **TLS Certificate Setup**
  - Retrieves wildcard certificate from `default` namespace
  - Copies certificate to `clickhouse` namespace as `clickhouse-tls-secret`

- **HTTP Ingress Creation**
  - Creates `clickhouse-http-ingress` in `clickhouse` namespace
  - Host: `clickhouse.example.com`
  - Backend: `clickhouse-clickhouse` service on port 8123
  - Annotations:
    - Backend protocol: HTTP
    - Proxy body size: unlimited (for large result sets)
  - TLS termination with wildcard certificate

- **TCP Passthrough Configuration**
  - Patches NGINX Ingress ConfigMap `primary-ingress-ingress-nginx-tcp`
  - Maps port 9000 to `clickhouse/clickhouse-clickhouse:9000`
  - Enables external native protocol access for high-performance clients

- **Code-Server CLI Configuration**
  - Generates ClickHouse CLI config from [templates/clickhouse-config.xml.j2](templates/clickhouse-config.xml.j2)
  - Template contains:
    - Host: `clickhouse-clickhouse-cluster.clickhouse.svc.cluster.local`
    - Port: 9000 (native protocol)
    - User: `default`
    - Password: from `ADMIN_PASSWORD`
  - Writes config to `/tmp/clickhouse-config.xml` (mode 0600)
  - Gets code-server pod name
  - Copies config to code-server: `/home/thinkube/.clickhouse-client/config.xml`
  - Sets permissions: 600 (user read/write only)
  - Removes temporary file
  - **Result**: `clickhouse-client` CLI works without authentication prompts in code-server

- **Connection Information Display**
  - External HTTPS URL
  - Native TCP endpoint
  - Internal cluster service name
  - Port numbers (8123 HTTP, 9000 native)
  - Default user and password source

### **Service Discovery**
**File**: [17_configure_discovery.yaml](17_configure_discovery.yaml)

Registers ClickHouse with Thinkube service discovery system:

- **ConfigMap Creation** (`thinkube-service-config` in `clickhouse` namespace)
  - Service type: `optional`
  - Category: `data`
  - Icon: `/icons/tk_data.svg`
  - Component version: `0.1.0` (from VERSION file)

- **Endpoints Registered**:
  - Primary: External HTTP (HTTPS) at `https://clickhouse.example.com` (health: `/ping`)
  - External native TCP at `clickhouse.example.com:9000`
  - Internal HTTP at `http://clickhouse-clickhouse.clickhouse.svc.cluster.local:8123` (health: `/ping`)
  - Internal native TCP at `clickhouse-clickhouse.clickhouse.svc.cluster.local:9000`

- **Features Documented**:
  - Real-time analytics
  - SQL interface
  - High performance OLAP
  - Columnar storage

- **Scaling Configuration**:
  - Resource type: StatefulSet `chi-clickhouse-clickhouse-0-0`
  - Min replicas: 1
  - Can disable: true

- **Environment Variables**:
  - `CLICKHOUSE_HOST`: `clickhouse.example.com`
  - `CLICKHOUSE_HTTP_PORT`: `443`
  - `CLICKHOUSE_NATIVE_PORT`: `9000`
  - `CLICKHOUSE_USER`: `default`
  - `CLICKHOUSE_PASSWORD`: from `ADMIN_PASSWORD`
  - `CLICKHOUSE_URL`: `https://clickhouse.example.com`

- **Code-Server Integration**
  - Updates code-server environment variables via `code_server_env_update` role
  - Makes ClickHouse connection details available to development environment

## Deployment

This component is automatically deployed via the **thinkube-control Optional Components interface**:

1. Navigate to https://thinkube.example.com/optional-components
2. Locate the **ClickHouse** card in the **Data** section
3. Click **Install** to deploy the component
4. Monitor real-time deployment progress via WebSocket streaming
5. Verify deployment status in the dashboard

The deployment executes the orchestrator playbook at `/ansible/40_thinkube/optional/clickhouse/00_install.yaml`.

**Deployment Sequence**:
1. Validate environment variables (`ADMIN_PASSWORD` required)
2. Create namespace
3. Add Altinity Helm repository
4. Deploy ClickHouse via Helm (single replica, 10Gi storage)
5. Wait for pod to be running
6. Configure HTTP ingress with TLS
7. Configure TCP passthrough for native protocol
8. Setup ClickHouse CLI in code-server
9. Register with service discovery

**Important**: Set `ADMIN_PASSWORD` environment variable before deployment. This password protects the `default` user account.

## Access Points

### External HTTP Interface (HTTPS)

```
https://clickhouse.example.com
```

Health check:
```bash
curl https://clickhouse.example.com/ping
```

Query via HTTP:
```bash
curl -u default:$ADMIN_PASSWORD "https://clickhouse.example.com/?query=SELECT+version()"
```

### External Native Protocol (TCP)

```
clickhouse.example.com:9000
```

Connect with ClickHouse client:
```bash
clickhouse-client --host clickhouse.example.com --port 9000 --user default --password $ADMIN_PASSWORD
```

### Internal Cluster Access

**HTTP Interface**:
```
http://clickhouse-clickhouse.clickhouse.svc.cluster.local:8123
```

**Native Protocol**:
```
clickhouse-clickhouse.clickhouse.svc.cluster.local:9000
```

**Cluster Service** (for distributed queries):
```
clickhouse-clickhouse-cluster.clickhouse.svc.cluster.local:9000
```

### Code-Server CLI Access

From code-server terminal, ClickHouse CLI is pre-configured:

```bash
clickhouse-client
# Connects automatically with credentials from ~/.clickhouse-client/config.xml
```

## Configuration

### Database and Tables

ClickHouse does not create application-specific databases automatically. Applications create their own:

**Langfuse** creates:
- Database: `langfuse`
- Tables for LLM traces, observations, scores, etc.

**CVAT** creates:
- Database: `cvat`
- Tables for annotation events, analytics, task metrics

### Storage Configuration

Default storage uses `k8s-hostpath` storage class with 10Gi:

To increase storage, edit the Helm values before deployment or upgrade:

```bash
helm upgrade clickhouse altinity/clickhouse \
  -n clickhouse \
  --set clickhouse.persistence.size=50Gi
```

### Replication and Sharding

Current deployment: 1 replica, 1 shard (single node)

For production with high availability:

```yaml
clickhouse:
  replicasCount: 3
  shardsCount: 2
```

**Note**: Requires distributed configuration and ZooKeeper/ClickHouse Keeper for coordination.

### User Management

Default user: `default` (superuser)

Create additional users:

```sql
CREATE USER analyst IDENTIFIED BY 'secure_password';
GRANT SELECT ON langfuse.* TO analyst;
```

Create read-only user:

```sql
CREATE USER readonly IDENTIFIED BY 'password';
GRANT SELECT ON *.* TO readonly;
```

### Query Performance

ClickHouse automatically indexes data. Optimize query performance:

1. **Use appropriate table engines**:
   - `MergeTree` for general purpose
   - `SummingMergeTree` for aggregations
   - `ReplacingMergeTree` for upserts

2. **Partition large tables**:
```sql
CREATE TABLE events (
    date Date,
    user_id UInt32,
    event String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, user_id);
```

3. **Use materialized views** for pre-aggregations

4. **Optimize column order** in ORDER BY (put most selective columns first)

## Usage

### Connect via HTTP

```bash
# Query with curl
curl -u default:$ADMIN_PASSWORD "https://clickhouse.example.com/?query=SHOW+DATABASES"

# Insert data
echo "2025-01-18,user123,page_view" | curl -u default:$ADMIN_PASSWORD \
  "https://clickhouse.example.com/?query=INSERT+INTO+events+FORMAT+CSV" \
  --data-binary @-
```

### Connect via Native Protocol

```bash
# From external client
clickhouse-client --host clickhouse.example.com --port 9000 --user default --password $ADMIN_PASSWORD

# From code-server (pre-configured)
clickhouse-client
```

### Python Client Example

```python
import clickhouse_connect

# Connect via HTTPS
client = clickhouse_connect.get_client(
    host='clickhouse.example.com',
    port=443,
    username='default',
    password='your_password',
    secure=True
)

# Execute query
result = client.query('SELECT version()')
print(result.result_rows)

# Insert data
client.insert('events', [[datetime.now(), 123, 'login']], column_names=['date', 'user_id', 'event'])
```

### Create Database and Table

```sql
-- Connect first
clickhouse-client

-- Create database
CREATE DATABASE analytics;

-- Use database
USE analytics;

-- Create table
CREATE TABLE events (
    timestamp DateTime,
    user_id UInt32,
    event_type String,
    properties String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, user_id);

-- Insert sample data
INSERT INTO events VALUES
    (now(), 1, 'login', '{"ip":"192.168.1.1"}'),
    (now(), 2, 'page_view', '{"page":"/home"}');

-- Query data
SELECT event_type, count() FROM events GROUP BY event_type;
```

### Advanced Queries

```sql
-- Window functions
SELECT
    user_id,
    event_type,
    timestamp,
    lagInFrame(timestamp) OVER (PARTITION BY user_id ORDER BY timestamp) AS prev_event_time
FROM events
LIMIT 10;

-- Aggregations
SELECT
    toDate(timestamp) AS date,
    event_type,
    count() AS event_count,
    uniq(user_id) AS unique_users
FROM events
GROUP BY date, event_type
ORDER BY date DESC, event_count DESC;

-- JSON extraction
SELECT
    user_id,
    JSONExtractString(properties, 'ip') AS ip_address
FROM events
WHERE event_type = 'login';
```

## Integration

### Langfuse LLM Observability

Langfuse uses ClickHouse for high-performance trace storage:

Connection configured via environment variables:
- `CLICKHOUSE_URL=https://clickhouse.example.com`
- `CLICKHOUSE_USER=default`
- `CLICKHOUSE_PASSWORD` from secret

Langfuse creates database `langfuse` with tables:
- `traces` - LLM execution traces
- `observations` - Individual LLM calls
- `scores` - Evaluation results

### CVAT Annotation Analytics

CVAT uses ClickHouse for annotation event analytics:

- Database: `cvat`
- Tracks annotation events, task progress, user activity
- Provides real-time dashboards for annotation metrics

### Custom Application Integration

From JupyterHub notebooks:

```python
# Install client
!pip install clickhouse-connect

import clickhouse_connect

# Use internal endpoint for best performance
client = clickhouse_connect.get_client(
    host='clickhouse-clickhouse.clickhouse.svc.cluster.local',
    port=8123,
    username='default',
    password='password'
)

# Analyze data
df = client.query_df('SELECT * FROM analytics.events WHERE date = today()')
print(df.head())
```

## Monitoring

### Health Checks

External:
```bash
curl https://clickhouse.example.com/ping
```

Internal:
```bash
kubectl exec -n clickhouse chi-clickhouse-clickhouse-0-0-0 -- clickhouse-client --query "SELECT 1"
```

### System Tables

ClickHouse exposes extensive monitoring via system tables:

```sql
-- Check running queries
SELECT query, elapsed, query_id FROM system.processes;

-- View query log
SELECT query, query_duration_ms FROM system.query_log ORDER BY event_time DESC LIMIT 10;

-- Check table sizes
SELECT
    database,
    table,
    formatReadableSize(sum(bytes)) AS size
FROM system.parts
WHERE active
GROUP BY database, table
ORDER BY sum(bytes) DESC;

-- Monitor replication lag (if replicated)
SELECT * FROM system.replicas;

-- Check disk usage
SELECT * FROM system.disks;
```

### Performance Metrics

```sql
-- Queries per second
SELECT
    toStartOfMinute(event_time) AS minute,
    count() AS queries
FROM system.query_log
WHERE event_time > now() - INTERVAL 1 HOUR
GROUP BY minute
ORDER BY minute;

-- Slow queries
SELECT
    query,
    query_duration_ms,
    read_rows,
    result_rows
FROM system.query_log
WHERE query_duration_ms > 1000
ORDER BY query_duration_ms DESC
LIMIT 10;
```

## Troubleshooting

### Verify Deployment Status

Check StatefulSet:
```bash
kubectl get statefulset -n clickhouse
kubectl describe statefulset chi-clickhouse-clickhouse-0-0 -n clickhouse
```

Check pods:
```bash
kubectl get pods -n clickhouse
kubectl describe pod chi-clickhouse-clickhouse-0-0-0 -n clickhouse
```

### Check Logs

View ClickHouse logs:
```bash
kubectl logs -n clickhouse chi-clickhouse-clickhouse-0-0-0 -f
```

View operator logs (if using ClickHouse operator):
```bash
kubectl logs -n kube-system -l app=clickhouse-operator -f
```

### Test Connectivity

From within cluster:
```bash
kubectl run clickhouse-test --rm -it --restart=Never \
  --image=clickhouse/clickhouse-client \
  -- clickhouse-client --host clickhouse-clickhouse.clickhouse.svc.cluster.local --query "SELECT version()"
```

From external (HTTP):
```bash
curl -v https://clickhouse.example.com/ping
```

From external (native):
```bash
clickhouse-client --host clickhouse.example.com --port 9000 --user default --password $ADMIN_PASSWORD --query "SELECT 1"
```

### Verify TCP Passthrough

Check Ingress ConfigMap:
```bash
kubectl get configmap primary-ingress-ingress-nginx-tcp -n ingress -o yaml | grep 9000
```

Should show:
```yaml
data:
  "9000": "clickhouse/clickhouse-clickhouse:9000"
```

### Authentication Issues

Reset default user password:

```bash
# Connect to pod
kubectl exec -it -n clickhouse chi-clickhouse-clickhouse-0-0-0 -- bash

# Connect as default user
clickhouse-client

# Change password
ALTER USER default IDENTIFIED BY 'new_password';
```

Update password in service discovery ConfigMap and code-server config.

### Storage Issues

Check PVC status:
```bash
kubectl get pvc -n clickhouse
kubectl describe pvc -n clickhouse
```

Check disk usage:
```sql
SELECT * FROM system.disks;
```

Free up space by dropping old partitions:
```sql
ALTER TABLE events DROP PARTITION '202401';
```

### Query Performance Issues

Enable query profiling:
```sql
SET send_logs_level = 'trace';
SELECT ... -- your slow query
```

Check query execution plan:
```sql
EXPLAIN SELECT ... -- your query
```

Analyze table structure:
```sql
DESCRIBE TABLE events;
SHOW CREATE TABLE events;
```

### Common Issues

**Issue**: Cannot connect externally
- **Solution**: Verify ingress and TCP passthrough configuration
- **Solution**: Check firewall allows port 9000 traffic

**Issue**: Slow queries
- **Solution**: Optimize table ORDER BY columns
- **Solution**: Use appropriate partition key
- **Solution**: Create materialized views for common aggregations

**Issue**: Out of memory
- **Solution**: Increase pod memory limits
- **Solution**: Reduce `max_memory_usage` setting
- **Solution**: Optimize queries to use less memory

**Issue**: Disk full
- **Solution**: Increase PVC size
- **Solution**: Drop old partitions
- **Solution**: Enable compression: `CODEC(ZSTD)`

**Issue**: Authentication failures in code-server
- **Solution**: Check `/home/thinkube/.clickhouse-client/config.xml` exists and has correct password
- **Solution**: Regenerate config by re-running deployment playbook

## Testing

The test playbook [18_test.yaml](18_test.yaml) verifies:
- ClickHouse pod is running
- HTTP interface responds to ping
- Native protocol accepts connections
- Can create database and table
- Can insert and query data
- External access works via both protocols
- Code-server CLI is configured correctly

## Rollback

To uninstall ClickHouse:

```bash
cd ~/thinkube
./scripts/tk_ansible ansible/40_thinkube/optional/clickhouse/19_rollback.yaml
```

**Warning**: This will delete all ClickHouse data including databases created by Langfuse, CVAT, and custom applications. Backup important data before uninstalling.

### Backup Data

Before rollback, export databases:

```bash
# Backup all databases
clickhouse-client --query "SHOW DATABASES" | while read db; do
  if [[ "$db" != "system" && "$db" != "information_schema" && "$db" != "INFORMATION_SCHEMA" ]]; then
    clickhouse-client --query "BACKUP DATABASE $db TO Disk('backups', '$db.zip')"
  fi
done
```

Or export specific tables:
```bash
clickhouse-client --query "SELECT * FROM langfuse.traces FORMAT Native" > traces_backup.native
```

## Performance Considerations

- **Columnar Storage**: Optimized for analytical queries, not transactional workloads
- **Query Parallelization**: Automatically uses all CPU cores
- **Compression**: Achieves 10-20x compression for typical datasets
- **Memory Usage**: Configurable via `max_memory_usage` setting
- **Disk I/O**: Performs best with SSD storage
- **Network**: Native protocol (port 9000) is faster than HTTP for large result sets

## Security Considerations

**Current Configuration**:
- Default user with password from `ADMIN_PASSWORD`
- TLS enabled for external HTTP access
- Native protocol (TCP) uses unencrypted connection

**For Production**:
1. Create dedicated users with minimal privileges for each application
2. Enable TLS for native protocol (requires certificate configuration)
3. Use IP allow lists to restrict access
4. Enable query logging and audit trail
5. Implement row-level security with SQL policies
6. Rotate passwords regularly

## References

- [ClickHouse Official Documentation](https://clickhouse.com/docs/)
- [Altinity Kubernetes Operator](https://github.com/Altinity/clickhouse-operator)
- [ClickHouse Python Client](https://github.com/ClickHouse/clickhouse-connect)
- [SQL Reference](https://clickhouse.com/docs/en/sql-reference/)
- [Performance Optimization Guide](https://clickhouse.com/docs/en/operations/performance/)
- [Best Practices](https://clickhouse.com/docs/en/guides/best-practices/)

🤖 [AI-assisted]
