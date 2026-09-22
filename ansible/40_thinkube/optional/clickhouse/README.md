# ClickHouse

Component #34 in the Thinkube Platform stack.

## Installation

ClickHouse is an optional component. It is installed and removed from the
Optional Components page in thinkube-control. It is not installed on its own.

- Install: [00_install.yaml](00_install.yaml)
- Test: [18_test.yaml](18_test.yaml)
- Uninstall: [19_rollback.yaml](19_rollback.yaml)
- Required components: none listed

The playbooks read the `ADMIN_PASSWORD` environment variable. It becomes the
password of the ClickHouse `default` user.

## Overview

ClickHouse is a high-performance columnar database management system optimized for online analytical processing (OLAP). Deployed via the Altinity Kubernetes operator, ClickHouse provides real-time analytics capabilities for CVAT annotation tracking, Langfuse LLM observability, and other data-intensive workloads.

**Key Features**:
- **Columnar Storage**: Optimized for analytical queries on large datasets
- **High Performance**: Processes billions of rows per second
- **SQL Interface**: Standard SQL with ClickHouse extensions
- **Real-time Analytics**: Sub-second query response times
- **Dual Protocol Access**: HTTP (port 8123) and native TCP (port 9000)
- **External Access**: HTTPS for HTTP interface, TCP passthrough for native protocol
- **Horizontal Scalability**: Supports sharding and replication (single node in this deployment)

## Dependencies

This component depends on the following Thinkube components:

- **Kubernetes (#6)** - Provides the container orchestration platform
- **ACME Certificates (#12)** - Secures HTTPS connections
- **Gateway API** - Envoy Gateway: an HTTPRoute for HTTPS and a TCP listener on port 9000 for the native protocol

## Prerequisites

```yaml
requirements:
  kubernetes:
    provider: "kubeadm"

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

| Playbook | What it does |
|---|---|
| [00_install.yaml](00_install.yaml) | Runs 10 and 17 in order. |
| [10_deploy.yaml](10_deploy.yaml) | Checks `ADMIN_PASSWORD`, creates the `clickhouse` namespace, installs the `altinity/clickhouse` Helm chart (release `clickhouse`, 1 replica, 1 shard, 10Gi on `k8s-hostpath`), waits for the pod, copies the TLS secret, creates the `clickhouse-route` HTTPRoute and the `allow-gateway-tcp` ReferenceGrant, and writes `~/.clickhouse-client/config.xml` into the code-server pod. |
| [17_configure_discovery.yaml](17_configure_discovery.yaml) | Creates the `thinkube-service-config` ConfigMap for thinkube-control and adds the `CLICKHOUSE_*` variables to the code-server environment. |
| [18_test.yaml](18_test.yaml) | Checks the namespace, StatefulSet, pod and service, then runs `clickhouse-client` in the pod to create a database and a table, insert and query a row, and drop the test database. |
| [19_rollback.yaml](19_rollback.yaml) | Deletes the ClickHouseInstallation resources (removing their finalizers), then the `clickhouse` namespace, forcing its finalizers off if it is stuck. |

The code-server CLI config points at
`clickhouse-clickhouse-cluster.clickhouse.svc.cluster.local:9000`, user
`default`, with the admin password.

Environment variables that service discovery gives to code-server:

- `CLICKHOUSE_HOST`: `clickhouse.example.com`
- `CLICKHOUSE_HTTP_PORT`: `443`
- `CLICKHOUSE_NATIVE_PORT`: `9000`
- `CLICKHOUSE_USER`: `default`
- `CLICKHOUSE_PASSWORD`: from `ADMIN_PASSWORD`
- `CLICKHOUSE_URL`: `https://clickhouse.example.com`

The native protocol on port 9000 reaches ClickHouse through the `clickhouse`
TCPRoute. [gateway-api/10_deploy.yaml](../../core/infrastructure/gateway-api/10_deploy.yaml)
creates that route and the listener in `gateway-system`. The
`allow-gateway-tcp` ReferenceGrant lets that route reach the Service in the
`clickhouse` namespace.

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

The size and storage class are set in the Helm values in
[10_deploy.yaml](10_deploy.yaml) (`clickhouse.persistence`).

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

Connection configured via environment variables (see `optional/langfuse/11_deploy.yaml`):
- `CLICKHOUSE_URL=http://clickhouse-clickhouse.clickhouse.svc.cluster.local:8123`
- `CLICKHOUSE_MIGRATION_URL=clickhouse://default:<password>@clickhouse-clickhouse.clickhouse.svc.cluster.local:9000`
- `CLICKHOUSE_USER=default`
- `CLICKHOUSE_PASSWORD`: the admin password

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

### Verify the Native Protocol Route

Check the TCPRoute and the ReferenceGrant:
```bash
kubectl get tcproute clickhouse -n gateway-system -o yaml
kubectl get referencegrant allow-gateway-tcp -n clickhouse -o yaml
```

The TCPRoute should send to `clickhouse-clickhouse` port 9000 in the
`clickhouse` namespace.

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
- **Solution**: Verify the `clickhouse-route` HTTPRoute and the `clickhouse` TCPRoute
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
- The `clickhouse` namespace, StatefulSet, pod and service exist
- `clickhouse-client` inside the pod answers `SELECT 1`
- A test database and table can be created, a row inserted and queried
- The test database is dropped afterwards

It does not test external access or the code-server CLI config.

## Rollback

[19_rollback.yaml](19_rollback.yaml) runs when ClickHouse is removed from the
Optional Components page.

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
