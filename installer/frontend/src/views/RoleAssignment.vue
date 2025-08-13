/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold mb-6">Kubernetes Role Assignment</h1>
    
    <!-- Role Requirements -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Role Requirements</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 class="font-semibold mb-2">Control Plane Node</h3>
            <ul class="text-sm space-y-1 text-base-content text-opacity-70">
              <li>• Manages Kubernetes API and cluster state</li>
              <li>• Requires at least 4 CPU cores and 8GB RAM</li>
              <li>• Can also run workloads (single-node cluster)</li>
              <li>• Must be baremetal (no VM support)</li>
            </ul>
          </div>
          
          <div>
            <h3 class="font-semibold mb-2">Worker Nodes (Optional)</h3>
            <ul class="text-sm space-y-1 text-base-content text-opacity-70">
              <li>• Additional nodes for workloads</li>
              <li>• Not required for single-node setups</li>
              <li>• GPU nodes for AI workloads</li>
              <li>• More nodes = more capacity</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Node List with Role Assignment -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Assign Roles to Nodes</h2>
        
        <div class="space-y-4">
          <!-- Baremetal Servers -->
          <div v-if="baremetalNodes.length > 0">
            <h3 class="font-semibold mb-2">Baremetal Servers</h3>
            <div class="space-y-2">
              <div 
                v-for="node in baremetalNodes" 
                :key="node.id"
                class="flex items-center justify-between p-3 rounded-lg bg-base-200"
              >
                <div class="flex items-center gap-3">
                  <div>
                    <p class="font-medium">{{ node.hostname }}</p>
                    <p class="text-sm text-base-content text-opacity-70">
                      {{ node.cpu }} CPU, {{ node.memory }} GB RAM
                      <span v-if="getNodeGPUStatus(node)" class="badge badge-success badge-sm ml-2">
                        {{ getNodeGPUStatus(node) }}
                      </span>
                    </p>
                  </div>
                </div>
                
                <select 
                  v-model="node.role" 
                  class="select select-sm"
                  @change="validateRoles"
                >
                  <option value="">No Role</option>
                  <option value="worker">Worker</option>
                  <option value="control_plane" :disabled="!canBeControlPlane(node) || (controlPlaneNodes.length > 0 && node.role !== 'control_plane')">Control Plane</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Validation Messages -->
    <div v-if="validationErrors.length > 0" class="alert alert-warning mb-6">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <div>
        <p v-for="error in validationErrors" :key="error">{{ error }}</p>
      </div>
    </div>
    
    <!-- Actions -->
    <div class="flex justify-between">
      <button class="btn btn-ghost gap-2" @click="$router.push('/hardware-detection')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
        Back
      </button>
      
      <button 
        class="btn btn-primary gap-2"
        @click="saveAndContinue"
        :disabled="!isValid"
      >
        Continue to Configuration
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// State
const allNodes = ref([])
const validationErrors = ref([])

// Computed
const baremetalNodes = computed(() => {
  return allNodes.value.filter(n => n.type === 'baremetal')
})


const controlPlaneNodes = computed(() => {
  return allNodes.value.filter(n => n.role === 'control_plane')
})

const workerNodes = computed(() => {
  return allNodes.value.filter(n => n.role === 'worker')
})


const isValid = computed(() => {
  return validationErrors.value.length === 0 &&
         controlPlaneNodes.value.length > 0
})

// Check if node can be control plane
const canBeControlPlane = (node) => {
  return node.cpu >= 4 && node.memory >= 8
}

// Get GPU status for baremetal nodes
const getNodeGPUStatus = (node) => {
  if (!node.hasGPU || !node.gpuInfo) return null
  
  // Get passthrough info for this node
  const passthroughInfo = node.gpuInfo.gpu_passthrough_info || []
  const totalGPUs = node.gpuInfo.gpu_count || 0
  const passthroughEligible = passthroughInfo.filter(g => g.passthrough_eligible).length
  
  return `${totalGPUs} GPU${totalGPUs > 1 ? 's' : ''}`
}


// Validate role assignment
const validateRoles = () => {
  validationErrors.value = []
  
  // Check control plane count (only allow ONE)
  const cpCount = controlPlaneNodes.value.length
  if (cpCount === 0) {
    validationErrors.value.push('Exactly one control plane node is required')
  } else if (cpCount > 1) {
    validationErrors.value.push('Only one control plane node is allowed for Thinkube')
  }
  
  // Check worker count - single node clusters are allowed
  // Control plane can also act as worker in single-node setups
  
  
  // Check unassigned nodes
  const unassignedCount = allNodes.value.filter(n => !n.role).length
  if (unassignedCount > 0) {
    validationErrors.value.push(`${unassignedCount} nodes have no role assigned`)
  }
}

// Save and continue
const saveAndContinue = () => {
  // Store the complete node configuration
  const clusterNodes = allNodes.value.filter(n => n.role).map(n => ({
    hostname: n.hostname,
    ip: n.ip,
    role: n.role,
    type: n.type,
    host: n.host,  // Important for VMs
    cpu: n.cpu,
    memory: n.memory,
    disk: n.disk,
    gpu: n.gpu,
    hasGPU: n.hasGPU,
    gpuInfo: n.gpuInfo
  }))
  
  sessionStorage.setItem('clusterNodes', JSON.stringify(clusterNodes))
  router.push('/configuration')
}

// Load all nodes
onMounted(() => {
  // Load baremetal servers
  const serverHardware = JSON.parse(sessionStorage.getItem('serverHardware') || '[]')
  const baremetalList = serverHardware.map(s => ({
    id: `bm-${s.hostname}`,
    hostname: s.hostname,
    ip: s.ip,
    type: 'baremetal',
    cpu: s.hardware?.cpu_cores || 0,
    memory: s.hardware?.memory_gb || 0,
    disk: s.hardware?.disk_gb || 0,
    hasGPU: s.hardware?.gpu_detected || false,
    gpuInfo: {
      gpu_count: s.hardware?.gpu_count || 0,
      gpu_model: s.hardware?.gpu_model || '',
      gpu_passthrough_info: s.hardware?.gpu_passthrough_info || [],
      iommu_enabled: s.hardware?.iommu_enabled || false
    },
    role: ''
  }))
  
  allNodes.value = baremetalList
  
  // Auto-assign recommended roles
  // Only ONE control plane allowed
  const eligibleForCP = allNodes.value.filter(n => canBeControlPlane(n))
  
  if (eligibleForCP.length > 0) {
    eligibleForCP[0].role = 'control_plane'
  }
  
  // Everything else as workers
  allNodes.value.forEach(node => {
    if (!node.role && node.hostname !== 'dns' && (node.type === 'baremetal' || node.cpu >= 2)) {
      node.role = 'worker'
    }
  })
  
  validateRoles()
})
</script>