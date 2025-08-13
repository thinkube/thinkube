/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-7xl mx-auto">
    <h1 class="text-3xl font-bold mb-6">Node Configuration</h1>
    
    <!-- Server List -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left: Server List -->
      <div class="lg:col-span-2 space-y-4">
        <div 
          v-for="(server, idx) in servers" 
          :key="server.ip_address"
          class="card bg-base-100 shadow-xl"
          :class="{ 'ring-2 ring-primary': selectedServerIndex === idx }"
        >
          <div class="card-body">
            <!-- Server Header -->
            <div class="flex items-center justify-between mb-4">
              <h2 class="card-title">
                {{ server.hostname || `Server ${idx + 1}` }}
                <div class="badge badge-ghost">{{ server.ip_address }}</div>
              </h2>
              <button 
                class="btn btn-sm btn-ghost"
                @click="removeServer(idx)"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
            
            <!-- Hardware Info -->
            <div v-if="server.hardware" class="stats stats-horizontal shadow mb-4">
              <div class="stat place-items-center py-2">
                <div class="stat-title text-xs">CPU</div>
                <div class="stat-value text-lg">{{ server.hardware.cpu_cores }}</div>
                <div class="stat-desc text-xs">cores</div>
              </div>
              <div class="stat place-items-center py-2">
                <div class="stat-title text-xs">RAM</div>
                <div class="stat-value text-lg">{{ server.hardware.memory_gb }}</div>
                <div class="stat-desc text-xs">GB</div>
              </div>
              <div class="stat place-items-center py-2">
                <div class="stat-title text-xs">Disk</div>
                <div class="stat-value text-lg">{{ Math.round(server.hardware.disk_gb / 1000) }}</div>
                <div class="stat-desc text-xs">TB</div>
              </div>
              <div v-if="server.hardware.gpu_detected" class="stat place-items-center py-2">
                <div class="stat-title text-xs">GPU</div>
                <div class="stat-value text-lg">{{ server.hardware.gpu_count }}</div>
                <div class="stat-desc text-xs">{{ server.hardware.gpu_model?.split(' ').slice(-2).join(' ') }}</div>
              </div>
            </div>
            
            <!-- SSH Credentials -->
            <div v-if="!server.ssh_verified" class="grid grid-cols-2 gap-2 mb-4">
              <input 
                v-model="server.ssh_username" 
                type="text" 
                placeholder="SSH Username" 
                class="input input-sm"
              />
              <div class="flex gap-2">
                <div class="relative flex-1">
                  <input 
                    v-model="server.ssh_password" 
                    :type="showPasswords[idx] ? 'text' : 'password'" 
                    placeholder="SSH Password" 
                    class="input input-bordered input-sm w-full pr-8"
                  />
                  <button 
                    type="button"
                    class="btn btn-ghost btn-xs btn-square absolute inset-y-0 right-0 flex items-center pr-2"
                    @click="togglePasswordVisibility(idx)"
                  >
                    <svg v-if="showPasswords[idx]" class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"></path>
                    </svg>
                    <svg v-else class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    </svg>
                  </button>
                </div>
                <button 
                  class="btn btn-sm btn-primary"
                  @click="verifyAndDetectHardware(server, idx)"
                  :disabled="!server.ssh_username || !server.ssh_password"
                >
                  Verify
                </button>
              </div>
            </div>
            
            <!-- Server Role Selection -->
            <div class="form-control mb-4">
              <label class="label">
                <span class="label-text font-semibold">Server Role</span>
              </label>
              <div class="space-y-2">
                <label class="flex items-start gap-3 p-3 rounded-lg hover:bg-base-200 cursor-pointer">
                  <input 
                    type="radio" 
                    :name="`role-${idx}`"
                    value="container_host"
                    v-model="server.role" 
                    class="radio radio-primary mt-1"
                  />
                  <div class="flex-1">
                    <div class="font-semibold">Container Host Only</div>
                    <div class="text-sm text-base-content text-opacity-70">Server will only host LXD containers for the cluster</div>
                  </div>
                </label>
                
                <label class="flex items-start gap-3 p-3 rounded-lg hover:bg-base-200 cursor-pointer">
                  <input 
                    type="radio" 
                    :name="`role-${idx}`"
                    value="hybrid"
                    v-model="server.role" 
                    class="radio radio-primary mt-1"
                  />
                  <div class="flex-1">
                    <div class="font-semibold">Hybrid Mode</div>
                    <div class="text-sm text-base-content text-opacity-70">Server will join Kubernetes cluster AND host LXD containers</div>
                    <div v-if="server.hardware && server.hardware.memory_gb >= 64" class="badge badge-success badge-sm mt-1">
                      Recommended
                    </div>
                  </div>
                </label>
                
                <label class="flex items-start gap-3 p-3 rounded-lg hover:bg-base-200 cursor-pointer">
                  <input 
                    type="radio" 
                    :name="`role-${idx}`"
                    value="direct"
                    v-model="server.role" 
                    class="radio radio-primary mt-1"
                  />
                  <div class="flex-1">
                    <div class="font-semibold">Direct Kubernetes Node</div>
                    <div class="text-sm text-base-content text-opacity-70">Server will join Kubernetes cluster directly (no containers)</div>
                  </div>
                </label>
              </div>
            </div>
            
            <!-- Kubernetes Role (if direct or hybrid) -->
            <div v-if="server.role === 'direct' || server.role === 'hybrid'" class="form-control mb-4">
              <label class="label">
                <span class="label-text font-semibold">Kubernetes Role</span>
              </label>
              <select v-model="server.k8s_role" class="select select-md">
                <option value="">Select role...</option>
                <option value="control_plane" :disabled="hasControlPlane && server.k8s_role !== 'control_plane'">
                  Control Plane {{ hasControlPlane && server.k8s_role !== 'control_plane' ? '(Already assigned)' : '' }}
                </option>
                <option value="worker">Worker Node</option>
              </select>
            </div>
            
            <!-- Container Configuration -->
            <div v-if="server.role === 'container_host' || server.role === 'hybrid'">
              <div class="divider">Containers</div>
              
              <!-- Container List -->
              <div class="space-y-2 mb-4">
                <div 
                  v-for="(container, cIdx) in server.containers" 
                  :key="cIdx"
                  class="card bg-base-200 shadow-sm"
                >
                  <div class="card-body p-3">
                    <div class="flex items-center justify-between">
                      <div>
                        <span class="font-semibold">{{ container.name }}</span>
                        <span class="badge badge-ghost badge-sm ml-2">{{ getContainerTypeLabel(container.type) }}</span>
                        <div class="text-sm text-base-content text-opacity-70">
                          {{ container.cpu_cores }} CPU • {{ container.memory }} RAM • {{ container.disk_size }} Disk
                          <span v-if="container.gpu_passthrough" class="badge badge-success badge-xs ml-2">GPU</span>
                        </div>
                      </div>
                      <button 
                        class="btn btn-ghost btn-xs"
                        @click="removeContainer(server, cIdx)"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Add Container Button -->
              <button 
                class="btn btn-sm btn-ghost gap-2"
                @click="showContainerModal(server, idx)"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                </svg>
                Add Container
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Right: Summary -->
      <div class="lg:col-span-1">
        <div class="card bg-base-100 shadow-xl sticky top-4">
          <div class="card-body">
            <h2 class="card-title mb-4">Cluster Summary</h2>
            
            <!-- Resource Totals -->
            <div class="space-y-2 mb-4">
              <div class="flex justify-between text-sm">
                <span>Total CPU Cores:</span>
                <span class="font-semibold">{{ totalResources.cpu }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span>Total Memory:</span>
                <span class="font-semibold">{{ totalResources.memory }} GB</span>
              </div>
              <div class="flex justify-between text-sm">
                <span>Total Storage:</span>
                <span class="font-semibold">{{ totalResources.storage }} TB</span>
              </div>
              <div v-if="totalResources.gpus > 0" class="flex justify-between text-sm">
                <span>Total GPUs:</span>
                <span class="font-semibold">{{ totalResources.gpus }}</span>
              </div>
            </div>
            
            <div class="divider">Kubernetes Nodes</div>
            
            <!-- Node Assignment -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-sm">Control Plane:</span>
                <span :class="controlPlaneCount === 1 ? 'badge badge-success' : 'badge badge-error'">
                  {{ controlPlaneCount }}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm">Worker Nodes:</span>
                <span :class="workerCount >= 1 ? 'badge badge-success' : 'badge badge-warning'">
                  {{ workerCount }}
                </span>
              </div>
            </div>
            
            <!-- Validation Messages -->
            <div v-if="validationErrors.length > 0" class="alert alert-error mt-4">
              <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <div v-for="error in validationErrors" :key="error" class="text-sm">
                  {{ error }}
                </div>
              </div>
            </div>
            
            <div v-else class="alert alert-success mt-4">
              <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Configuration is valid</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Container Modal -->
    <dialog ref="containerModal" class="modal">
      <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-lg mb-4">Add Container</h3>
        
        <form @submit.prevent="addContainer">
          <!-- Container Type -->
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">Container Type</span>
            </label>
            <select v-model="newContainer.type" class="select" @change="updateContainerDefaults">
              <option value="">Select type...</option>
              <option value="k8s_control">Kubernetes Control Plane</option>
              <option value="k8s_worker">Kubernetes Worker</option>
              <option value="dns">DNS Server</option>
              <option value="custom">Custom Container</option>
            </select>
          </div>
          
          <!-- Container Name -->
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">Container Name</span>
            </label>
            <input 
              v-model="newContainer.name" 
              type="text" 
              placeholder="e.g., tkw1" 
              class="input input-bordered"
              required
            />
          </div>
          
          <!-- Resources -->
          <div class="grid grid-cols-3 gap-4 mb-4">
            <div class="form-control">
              <label class="label">
                <span class="label-text">CPU Cores</span>
              </label>
              <input 
                v-model.number="newContainer.cpu_cores" 
                type="number" 
                min="1"
                :max="currentServerHardware?.cpu_cores || 32"
                class="input input-bordered"
                required
              />
            </div>
            
            <div class="form-control">
              <label class="label">
                <span class="label-text">Memory</span>
              </label>
              <input 
                v-model="newContainer.memory" 
                type="text" 
                placeholder="48GB" 
                class="input input-bordered"
                required
              />
            </div>
            
            <div class="form-control">
              <label class="label">
                <span class="label-text">Disk Size</span>
              </label>
              <input 
                v-model="newContainer.disk_size" 
                type="text" 
                placeholder="700GB" 
                class="input input-bordered"
                required
              />
            </div>
          </div>
          
          <!-- GPU Passthrough -->
          <div v-if="currentServerHardware?.gpu_detected" class="form-control mb-4">
            <label class="label cursor-pointer">
              <span class="label-text">Enable GPU Passthrough</span>
              <input type="checkbox" v-model="newContainer.gpu_passthrough" class="checkbox checkbox-primary" />
            </label>
          </div>
          
          <!-- K8s Role (for k8s containers) -->
          <div v-if="newContainer.type === 'k8s_control' || newContainer.type === 'k8s_worker'" class="form-control mb-4">
            <label class="label">
              <span class="label-text">Kubernetes Role</span>
            </label>
            <select v-model="newContainer.k8s_role" class="select">
              <option value="control_plane" :disabled="hasControlPlane">
                Control Plane {{ hasControlPlane ? '(Already assigned)' : '' }}
              </option>
              <option value="worker">Worker Node</option>
            </select>
          </div>
          
          <div class="modal-action">
            <button type="button" class="btn btn-ghost" @click="closeContainerModal">Cancel</button>
            <button type="submit" class="btn btn-primary">Add Container</button>
          </div>
        </form>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
    
    <!-- Navigation -->
    <div class="flex justify-between mt-6">
      <button class="btn btn-ghost gap-2" @click="$router.push('/network-discovery')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
        Back
      </button>
      <button 
        class="btn btn-primary gap-2"
        @click="saveAndContinue"
        :disabled="validationErrors.length > 0"
      >
        Review Configuration
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
import axios from 'axios'

const router = useRouter()

// State
const servers = ref([])
const selectedServerIndex = ref(0)
const testMode = ref(true)
const showPasswords = ref({})

// Container modal
const containerModal = ref(null)
const currentServerForContainer = ref(null)
const newContainer = ref({
  name: '',
  type: '',
  cpu_cores: 1,
  memory: '',
  disk_size: '',
  gpu_passthrough: false,
  k8s_role: null
})

// Computed
const currentServerHardware = computed(() => {
  if (currentServerForContainer.value !== null) {
    return servers.value[currentServerForContainer.value]?.hardware
  }
  return null
})

const totalResources = computed(() => {
  const totals = {
    cpu: 0,
    memory: 0,
    storage: 0,
    gpus: 0
  }
  
  for (const server of servers.value) {
    if (server.hardware) {
      totals.cpu += server.hardware.cpu_cores
      totals.memory += server.hardware.memory_gb
      totals.storage += server.hardware.disk_gb / 1000
      totals.gpus += server.hardware.gpu_count || 0
    }
  }
  
  return {
    cpu: Math.round(totals.cpu),
    memory: Math.round(totals.memory),
    storage: Math.round(totals.storage * 10) / 10,
    gpus: totals.gpus
  }
})

const controlPlaneCount = computed(() => {
  let count = 0
  
  for (const server of servers.value) {
    // Direct or hybrid server as control plane
    if ((server.role === 'direct' || server.role === 'hybrid') && server.k8s_role === 'control_plane') {
      count++
    }
    
    // Containers as control plane
    for (const container of server.containers || []) {
      if (container.k8s_role === 'control_plane') {
        count++
      }
    }
  }
  
  return count
})

const workerCount = computed(() => {
  let count = 0
  
  for (const server of servers.value) {
    // Direct or hybrid server as worker
    if ((server.role === 'direct' || server.role === 'hybrid') && server.k8s_role === 'worker') {
      count++
    }
    
    // Containers as workers
    for (const container of server.containers || []) {
      if (container.k8s_role === 'worker') {
        count++
      }
    }
  }
  
  return count
})

const hasControlPlane = computed(() => controlPlaneCount.value > 0)

const validationErrors = computed(() => {
  const errors = []
  
  if (servers.value.length === 0) {
    errors.push('At least one server is required')
  }
  
  if (controlPlaneCount.value !== 1) {
    errors.push(`Exactly one control plane required (found ${controlPlaneCount.value})`)
  }
  
  if (workerCount.value < 1) {
    errors.push('At least one worker node required')
  }
  
  // Check if all servers have SSH verified
  const unverifiedServers = servers.value.filter(s => !s.ssh_verified)
  if (unverifiedServers.length > 0) {
    errors.push(`${unverifiedServers.length} server(s) need SSH verification`)
  }
  
  // Check if all servers have roles assigned
  const noRoleServers = servers.value.filter(s => !s.role)
  if (noRoleServers.length > 0) {
    errors.push(`${noRoleServers.length} server(s) need role assignment`)
  }
  
  return errors
})

// Methods
const verifyAndDetectHardware = async (server, idx) => {
  try {
    // First verify SSH
    const sshResponse = await axios.post('/api/verify-server-ssh', {
      ip_address: server.ip_address,
      ssh_username: server.ssh_username,
      ssh_password: server.ssh_password,
      test_mode: testMode.value
    })
    
    if (!sshResponse.data.connected) {
      alert('SSH connection failed: ' + sshResponse.data.message)
      return
    }
    
    server.ssh_verified = true
    server.hostname = sshResponse.data.hostname || server.hostname
    
    // Then detect hardware
    const hwResponse = await axios.post('/api/detect-hardware', {
      ip_address: server.ip_address,
      test_mode: testMode.value
    })
    
    if (hwResponse.data.hardware) {
      server.hardware = hwResponse.data.hardware
      
      // Auto-suggest role based on hardware
      if (server.hardware.memory_gb >= 64) {
        server.role = 'hybrid'
      } else {
        server.role = 'container_host'
      }
    }
    
  } catch (error) {
    console.error('Verification failed:', error)
    alert('Failed to verify server: ' + error.message)
  }
}

const removeServer = (idx) => {
  servers.value.splice(idx, 1)
}

const togglePasswordVisibility = (idx) => {
  showPasswords.value[idx] = !showPasswords.value[idx]
}

const showContainerModal = (server, serverIdx) => {
  currentServerForContainer.value = serverIdx
  newContainer.value = {
    name: '',
    type: '',
    cpu_cores: 1,
    memory: '',
    disk_size: '',
    gpu_passthrough: false,
    k8s_role: null,
    parent_host: server.hostname
  }
  containerModal.value.showModal()
}

const closeContainerModal = () => {
  containerModal.value.close()
  currentServerForContainer.value = null
}

const updateContainerDefaults = () => {
  const defaults = {
    k8s_control: { name: 'tkc', cpu_cores: 12, memory: '48GB', disk_size: '700GB', k8s_role: 'control_plane' },
    k8s_worker: { name: 'tkw', cpu_cores: 12, memory: '48GB', disk_size: '700GB', k8s_role: 'worker' },
    dns: { name: 'dns1', cpu_cores: 1, memory: '2GB', disk_size: '20GB' },
    custom: { name: '', cpu_cores: 2, memory: '4GB', disk_size: '50GB' }
  }
  
  const type = newContainer.value.type
  if (defaults[type]) {
    Object.assign(newContainer.value, defaults[type])
  }
}

const addContainer = () => {
  const server = servers.value[currentServerForContainer.value]
  if (!server.containers) {
    server.containers = []
  }
  
  // Auto-number container names if needed
  if (newContainer.value.type === 'k8s_worker' && newContainer.value.name === 'tkw') {
    const workerCount = server.containers.filter(c => c.name.startsWith('tkw')).length
    newContainer.value.name = `tkw${workerCount + 1}`
  }
  
  server.containers.push({
    ...newContainer.value,
    parent_host: server.hostname
  })
  
  closeContainerModal()
}

const removeContainer = (server, idx) => {
  server.containers.splice(idx, 1)
}

const getContainerTypeLabel = (type) => {
  const labels = {
    k8s_control: 'K8s Control Plane',
    k8s_worker: 'K8s Worker',
    dns: 'DNS Server',
    custom: 'Custom'
  }
  return labels[type] || type
}

const saveAndContinue = async () => {
  try {
    // Save configuration to backend
    const response = await axios.post('/api/save-cluster-config', {
      servers: servers.value,
      test_mode: testMode.value
    })
    
    if (response.data.success) {
      // Store in session for review page
      sessionStorage.setItem('clusterConfig', JSON.stringify({
        servers: servers.value,
        summary: response.data.summary
      }))
      
      router.push('/review')
    } else {
      alert('Failed to save configuration: ' + response.data.message)
    }
  } catch (error) {
    console.error('Save failed:', error)
    alert('Failed to save configuration: ' + error.message)
  }
}

// Lifecycle
onMounted(() => {
  // Load selected servers from previous step
  const selectedServers = JSON.parse(sessionStorage.getItem('selectedServers') || '[]')
  testMode.value = sessionStorage.getItem('testMode') === 'true'
  
  // Convert to our server format
  servers.value = selectedServers.map(s => ({
    hostname: s.hostname || '',
    ip_address: s.ip,
    ssh_username: 'thinkube',
    ssh_password: '',
    role: '',
    hardware: null,
    containers: [],
    k8s_role: null,
    ssh_verified: false
  }))
})
</script>

<style scoped>
.stats {
  @apply bg-base-100;
}

.stat {
  @apply px-4;
}
</style>