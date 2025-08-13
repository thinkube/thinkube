# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
Pydantic models for server-related data structures
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class ServerRole(str, Enum):
    CONTAINER_HOST = "container_host"
    HYBRID = "hybrid"
    DIRECT = "direct"


class ContainerType(str, Enum):
    K8S_CONTROL = "k8s_control"
    K8S_WORKER = "k8s_worker" 
    DNS = "dns"
    CUSTOM = "custom"


class NodeRole(str, Enum):
    CONTROL_PLANE = "control_plane"
    WORKER = "worker"


class HardwareInfo(BaseModel):
    cpu_cores: int
    cpu_model: str
    memory_gb: float
    disk_gb: float
    gpu_detected: bool = False
    gpu_model: Optional[str] = None
    gpu_count: int = 0
    architecture: str  # x86_64 or arm64


class Container(BaseModel):
    name: str
    type: ContainerType
    parent_host: str
    memory: str  # e.g., "48GB"
    cpu_cores: int
    disk_size: str  # e.g., "700GB"
    gpu_passthrough: bool = False
    gpu_type: Optional[str] = None
    k8s_role: Optional[NodeRole] = None


class ServerInfo(BaseModel):
    hostname: str
    ip_address: str
    role: ServerRole
    hardware: HardwareInfo
    containers: List[Container] = []
    ssh_available: bool = False
    ssh_username: str = "thinkube"


class ClusterConfig(BaseModel):
    cluster_name: str = Field(default="thinkube-cluster")
    domain_name: str = Field(default="thinkube.com")
    primary_ingress_ip: str
    cloudflare_api_token: str
    zerotier_network_id: str
    zerotier_api_token: str
    servers: List[ServerInfo] = []


class NetworkDiscoveryRequest(BaseModel):
    network_cidr: str = "192.168.1.0/24"
    timeout: int = 10


class SSHVerificationRequest(BaseModel):
    ip_address: str
    username: str = "thinkube"


class TokenRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    success: bool
    message: str