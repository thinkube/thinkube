# Node Configuration UI Design

## Overview

The installer needs to support three deployment scenarios for baremetal servers:

1. **Container-Only Mode** (like bcn2): Baremetal hosts only LXD containers, not directly used in cluster
2. **Hybrid Mode** (like bcn1): Baremetal is both a Kubernetes worker AND hosts LXD containers
3. **Direct Mode** (theoretical): Baremetal is used directly without hosting containers

## UI Design Approach

### Step 1: Baremetal Server Definition

```
=== Add Baremetal Server ===

Hostname: [bcn1]
IP Address: [10.0.1.101]
SSH Username: [thinkube]
SSH Password: [••••••••]

Hardware Detection: 
[ ] Detect hardware after adding (CPU, RAM, Disk, GPU)

[Add Server]
```

### Step 2: Server Role Selection (Per Server)

After adding a server and detecting hardware, present role options:

```
=== Configure Server: bcn1 ===
Detected: 32 cores, 128GB RAM, 2TB disk, 2× RTX 3090

How will this server be used?

○ Container Host Only
  Server will only host LXD containers for the cluster
  
◉ Hybrid Mode (Recommended for powerful servers)
  Server will join Kubernetes cluster AND host LXD containers
  
○ Direct Kubernetes Node
  Server will join Kubernetes cluster directly (no containers)

[Continue]
```

### Step 3: Container Definition (If Container Host or Hybrid)

```
=== Define Containers for bcn1 ===

This server will host LXD containers. Define what containers to create:

[✓] Kubernetes Worker (tkw1)
    Memory: [48GB] CPU: [12] Disk: [700GB]
    [✓] GPU Passthrough (1× RTX 3090)
    
[ ] DNS Server
    Memory: [2GB] CPU: [1] Disk: [20GB]
    
[ ] Custom Container
    Name: [____] Memory: [__GB] CPU: [_] Disk: [__GB]
    
[Add Container Type]
[Continue]
```

### Step 4: Cluster Role Assignment

```
=== Kubernetes Cluster Roles ===

Assign roles to your nodes:

Control Plane:
  ◉ tkc (Container on bcn2)
  ○ bcn1 (Direct)
  ○ Other...

Workers:
  [✓] tkw1 (Container on bcn1)
  [✓] bcn1 (Direct - Hybrid mode)
  [ ] bcn2 (Direct)
  
DNS Server:
  ◉ dns1 (Container on bcn2)
  ○ External DNS
  
[Continue]
```

### Step 5: Summary View

```
=== Deployment Summary ===

Baremetal Servers:
├── bcn1 (10.0.1.101) - HYBRID MODE
│   ├── Direct: Kubernetes Worker
│   └── Containers:
│       └── tkw1: Kubernetes Worker (48GB/12CPU/700GB + GPU)
│
└── bcn2 (10.0.1.102) - CONTAINER HOST
    └── Containers:
        ├── tkc: Kubernetes Control Plane (48GB/12CPU/700GB + GPU)
        └── dns1: DNS Server (2GB/1CPU/20GB)

Kubernetes Cluster:
├── Control Plane: tkc
└── Workers: tkw1, bcn1

[Review Configuration] [Back] [Deploy]
```

## Implementation Details

### Backend Data Model

```python
class ServerRole(Enum):
    CONTAINER_HOST = "container_host"  # Only hosts containers
    HYBRID = "hybrid"                  # Direct k8s node + hosts containers  
    DIRECT = "direct"                  # Direct k8s node only

class ContainerType(Enum):
    K8S_CONTROL = "k8s_control"
    K8S_WORKER = "k8s_worker"
    DNS = "dns"
    CUSTOM = "custom"

class BaremetalServer(BaseModel):
    hostname: str
    ip_address: str
    role: ServerRole
    hardware: Optional[HardwareInfo]
    containers: List[Container] = []
    k8s_role: Optional[str] = None  # "control_plane" or "worker" if direct/hybrid

class Container(BaseModel):
    name: str
    type: ContainerType
    parent_host: str
    memory: str
    cpu_cores: int
    disk_size: str
    gpu_passthrough: bool = False
    gpu_type: Optional[str] = None
    k8s_role: Optional[str] = None  # For k8s containers
```

### UI Components Needed

1. **Server List Component**
   - Add/Edit/Delete servers
   - Show role badges (Container Host, Hybrid, Direct)
   - Hardware summary

2. **Role Selector Component**
   - Radio buttons with descriptions
   - Hardware-based recommendations

3. **Container Builder Component**
   - Predefined templates (K8s Control, K8s Worker, DNS)
   - Resource sliders with server limits
   - GPU assignment for capable servers

4. **Cluster Visualizer Component**
   - Tree view of servers and containers
   - Role assignments clearly marked
   - Network topology hints

### Validation Rules

1. **Hardware Constraints**
   - Container resources cannot exceed host capacity
   - GPU passthrough only if host has GPU
   - Reserved resources for host OS (10% CPU, 4GB RAM)

2. **Cluster Requirements**
   - Exactly one control plane node
   - At least one worker node
   - DNS server recommended

3. **Network Validation**
   - All IPs in same subnet
   - No IP conflicts
   - Valid IP ranges

### Auto-Detection Features

1. **Hardware Detection** (via SSH after adding server)
   - CPU cores, architecture
   - Total RAM
   - Disk space
   - GPU presence and type

2. **Smart Defaults**
   - Powerful servers (>32GB RAM) → Suggest Hybrid mode
   - Servers with GPU → Suggest container with GPU passthrough
   - First server → Suggest as control plane host

3. **Template Suggestions**
   - 2-server setup → One for control plane, one hybrid worker
   - 3+ servers → Dedicated control plane, multiple workers

This design provides flexibility while guiding users toward sensible configurations based on their hardware.