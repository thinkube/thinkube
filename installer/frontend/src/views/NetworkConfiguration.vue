/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold mb-6 text-base-content">Network Configuration</h1>
    
    <!-- Network Validation Messages -->
    <div v-if="networkValidationErrors.length > 0" class="alert alert-warning mb-6">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <div>
        <h3 class="font-bold">Network Configuration Issues</h3>
        <ul class="text-sm mt-1">
          <li v-for="error in networkValidationErrors" :key="error">{{ error }}</li>
        </ul>
      </div>
    </div>
    
    <!-- Network Overview -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Network Overview</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-if="networkMode === 'local'" class="form-control">
            <label class="label">
              <span class="label-text">Local Network CIDR</span>
              <span class="label-text-alt text-xs">Auto-discovered</span>
            </label>
            <input 
              v-model="networkConfig.cidr" 
              type="text" 
              class="input input-disabled"
              readonly
            />
          </div>
          
          <div v-if="networkMode === 'local'" class="form-control">
            <label class="label">
              <span class="label-text">Gateway IP</span>
              <span class="label-text-alt text-xs">Last octet editable</span>
            </label>
            <div class="flex items-center gap-1">
              <span class="text-sm text-base-content text-opacity-70">{{ getNetworkBase(networkConfig.cidr) }}.</span>
              <input 
                :value="getLastOctet(networkConfig.gateway)"
                @input="networkConfig.gateway = setLastOctet(getNetworkBase(networkConfig.cidr), $event.target.value)"
                type="number" 
                min="1" 
                max="254"
                class="input input-bordered input-sm w-16"
                :class="{ 'input-error': !isValidIP(networkConfig.gateway) }"
              />
            </div>
          </div>
          
          <div v-if="networkMode === 'overlay'" class="form-control">
            <label class="label">
              <span class="label-text">ZeroTier Network CIDR</span>
              <span class="label-text-alt text-xs">Remote access network</span>
            </label>
            <input 
              v-model="networkConfig.zerotierCIDR" 
              type="text" 
              class="input input-bordered input-disabled"
              readonly
            />
          </div>
          
          <div v-if="networkMode === 'overlay'" class="form-control">
            <label class="label">
              <span class="label-text">Kubernetes Cluster CIDR</span>
              <span class="label-text-alt text-xs">Node network</span>
            </label>
            <input 
              v-model="networkConfig.cidr" 
              type="text" 
              placeholder="10.0.0.0/24"
              class="input input-bordered input-disabled"
              readonly
              title="Auto-detected from cluster nodes"
            />
          </div>
          
        </div>
        
        <div v-if="networkMode === 'overlay' && zerotierLoading" class="flex items-center gap-3 mt-4">
          <span class="loading loading-spinner loading-sm"></span>
          <span class="text-sm">Fetching ZeroTier network details...</span>
        </div>
        
        <div v-if="networkMode === 'overlay' && zerotierError" class="alert alert-error mt-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <div class="font-bold">Failed to fetch ZeroTier network</div>
            <div class="text-sm">{{ zerotierError }}</div>
          </div>
        </div>
        
        <div v-if="networkMode === 'overlay' && zerotierNetworkName" class="alert alert-info mt-4">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <div>
            <div class="font-bold text-base-content">Dual Network Configuration</div>
            <div class="text-sm text-base-content text-opacity-80">
              <strong>ZeroTier ({{ zerotierNetworkName }}):</strong> Remote management and distributed access<br>
              <strong>Local LAN ({{ networkConfig.cidr }}):</strong> High-speed cluster internal communication
            </div>
          </div>
        </div>
        
        <div v-if="networkMode === 'local'" class="alert alert-info mt-4">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <div>
            <div class="font-bold text-base-content">Local Network Mode</div>
            <div class="text-sm text-base-content text-opacity-80">Using existing network infrastructure • DNS and MetalLB will use local network IPs</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Ingress IP Configuration -->
    <div v-if="networkMode === 'overlay' || networkMode === 'local'" class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Ingress IP Configuration</h2>
        
        <div class="alert alert-info mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <div>
            <div class="font-bold text-base-content">MetalLB Load Balancer IPs</div>
            <div class="text-sm text-base-content text-opacity-80">
              <span v-if="networkMode === 'overlay'">These IPs will be reserved on the ZeroTier network for external access to services</span>
              <span v-else>These IPs will be reserved on your local network for Kubernetes ingress services</span>
            </div>
          </div>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">Primary Ingress IP</span>
              <span class="label-text-alt">For main services</span>
            </label>
            <div class="flex items-center gap-1">
              <span class="text-sm text-base-content text-opacity-70">{{ getNetworkBase(networkMode === 'overlay' ? networkConfig.zerotierCIDR : networkConfig.cidr) }}.</span>
              <input 
                v-model="networkConfig.primaryIngressOctet"
                type="number" 
                min="1" 
                max="254"
                placeholder="200"
                class="input input-bordered input-sm w-20"
                :class="{ 
                  'input-error': !isValidIngressOctet(networkConfig.primaryIngressOctet),
                  'input-warning': isIngressIPInUse(networkConfig.primaryIngressOctet)
                }"
              />
            </div>
            <div v-if="isIngressIPInUse(networkConfig.primaryIngressOctet)" class="text-xs text-warning mt-1">
              This IP is already assigned to another ZeroTier member
            </div>
          </div>
          
          <div class="form-control">
            <label class="label">
              <span class="label-text">Secondary Ingress IP</span>
              <span class="label-text-alt">For Knative services</span>
            </label>
            <div class="flex items-center gap-1">
              <span class="text-sm text-base-content text-opacity-70">{{ getNetworkBase(networkMode === 'overlay' ? networkConfig.zerotierCIDR : networkConfig.cidr) }}.</span>
              <input 
                v-model="networkConfig.secondaryIngressOctet"
                type="number" 
                min="1" 
                max="254"
                placeholder="201"
                class="input input-bordered input-sm w-20"
                :class="{ 
                  'input-error': !isValidIngressOctet(networkConfig.secondaryIngressOctet),
                  'input-warning': isIngressIPInUse(networkConfig.secondaryIngressOctet)
                }"
              />
            </div>
            <div v-if="isIngressIPInUse(networkConfig.secondaryIngressOctet)" class="text-xs text-warning mt-1">
              This IP is already assigned to another ZeroTier member
            </div>
          </div>
        </div>

        <!-- DNS External IP -->
        <div class="divider">DNS Configuration</div>
        
        <div class="form-control">
          <label class="label">
            <span class="label-text">CoreDNS External IP</span>
            <span class="label-text-alt">External IP for DNS resolution</span>
          </label>
          <div class="flex items-center gap-1">
            <span class="text-sm text-base-content text-opacity-70">{{ getNetworkBase(networkMode === 'overlay' ? networkConfig.zerotierCIDR : networkConfig.cidr) }}.</span>
            <input 
              v-model="networkConfig.dnsExternalOctet"
              type="number" 
              min="1" 
              max="254"
              placeholder="250"
              class="input input-bordered input-sm w-20"
              :class="{ 
                'input-error': !isValidIngressOctet(networkConfig.dnsExternalOctet) || isDNSIPConflict() || !isDNSInMetalLBRange()
              }"
            />
          </div>
          <label v-if="isDNSIPConflict()" class="label">
            <span class="label-text-alt text-error">DNS IP conflicts with other assignments</span>
          </label>
          <label v-else-if="!isDNSInMetalLBRange()" class="label">
            <span class="label-text-alt text-error">DNS IP should be within MetalLB range ({{ networkConfig.metallbStartOctet }}-{{ networkConfig.metallbEndOctet }})</span>
          </label>
        </div>

        <!-- MetalLB IP Range -->
        <div class="divider">MetalLB IP Range</div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">MetalLB Start IP</span>
              <span class="label-text-alt">First IP in range</span>
            </label>
            <div class="flex items-center gap-1">
              <span class="text-sm text-base-content text-opacity-70">{{ getNetworkBase(networkMode === 'overlay' ? networkConfig.zerotierCIDR : networkConfig.cidr) }}.</span>
              <input 
                v-model="networkConfig.metallbStartOctet"
                type="number" 
                min="1" 
                max="254"
                placeholder="200"
                class="input input-bordered input-sm w-20"
                :class="{ 
                  'input-error': !isValidIngressOctet(networkConfig.metallbStartOctet) || isMetalLBRangeInvalid()
                }"
              />
            </div>
          </div>
          
          <div class="form-control">
            <label class="label">
              <span class="label-text">MetalLB End IP</span>
              <span class="label-text-alt">Last IP in range</span>
            </label>
            <div class="flex items-center gap-1">
              <span class="text-sm text-base-content text-opacity-70">{{ getNetworkBase(networkMode === 'overlay' ? networkConfig.zerotierCIDR : networkConfig.cidr) }}.</span>
              <input 
                v-model="networkConfig.metallbEndOctet"
                type="number" 
                min="1" 
                max="254"
                placeholder="210"
                class="input input-bordered input-sm w-20"
                :class="{ 
                  'input-error': !isValidIngressOctet(networkConfig.metallbEndOctet) || isMetalLBRangeInvalid()
                }"
              />
            </div>
          </div>
        </div>

        <div v-if="isMetalLBRangeInvalid()" class="alert alert-error mt-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <div v-if="parseInt(networkConfig.metallbStartOctet) > parseInt(networkConfig.metallbEndOctet)">
              Start IP must be less than or equal to End IP
            </div>
            <div v-else-if="!isIngressIPInRange()">
              Primary ({{ networkConfig.primaryIngressOctet }}) and Secondary ({{ networkConfig.secondaryIngressOctet }}) ingress IPs must be within the MetalLB range
            </div>
          </div>
        </div>
        
        <div v-if="networkConfig.primaryIngressOctet && networkConfig.secondaryIngressOctet && networkConfig.metallbStartOctet && networkConfig.metallbEndOctet && !isMetalLBRangeInvalid()" class="mt-4">
          <div class="prose prose-sm max-w-none text-base-content text-opacity-80">
            <p class="font-medium mb-2">MetalLB Configuration:</p>
            <ul>
              <li>IP Range: <span class="font-mono">{{ getNetworkBase(networkMode === 'overlay' ? networkConfig.zerotierCIDR : networkConfig.cidr) }}.{{ networkConfig.metallbStartOctet }}-{{ getNetworkBase(networkMode === 'overlay' ? networkConfig.zerotierCIDR : networkConfig.cidr) }}.{{ networkConfig.metallbEndOctet }}</span></li>
              <li>Primary Ingress: <span class="font-mono">{{ getNetworkBase(networkMode === 'overlay' ? networkConfig.zerotierCIDR : networkConfig.cidr) }}.{{ networkConfig.primaryIngressOctet }}</span></li>
              <li>Secondary Ingress: <span class="font-mono">{{ getNetworkBase(networkMode === 'overlay' ? networkConfig.zerotierCIDR : networkConfig.cidr) }}.{{ networkConfig.secondaryIngressOctet }}</span></li>
            </ul>
          </div>
        </div>
      </div>
    </div>



    <!-- Baremetal Servers -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Baremetal Servers</h2>
        
        <div class="overflow-x-auto rounded-lg">
          <table class="table table-compact table-pin-rows hover">
            <thead>
              <tr>
                <th class="font-semibold text-base-content text-opacity-90">Hostname</th>
                <th v-if="networkMode === 'local'" class="font-semibold text-base-content text-opacity-90">LAN IP</th>
                <th v-if="networkMode === 'overlay'" class="font-semibold text-base-content text-opacity-90">ZeroTier IP</th>
                <th v-if="networkMode === 'overlay'" class="font-semibold text-base-content text-opacity-90">Local IP (Auto)</th>
                <th class="font-semibold text-base-content text-opacity-90">Role</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(server, idx) in physicalServers" :key="server.hostname">
                <td class="font-medium">{{ server.hostname }}</td>
                <td v-if="networkMode === 'local'">
                  <div class="flex items-center gap-1">
                    <span class="text-sm text-base-content text-opacity-70">{{ getNetworkBase(networkConfig.cidr) }}.</span>
                    <input 
                      :value="getLastOctet(server.ip)"
                      @input="server.ip = setLastOctet(getNetworkBase(networkConfig.cidr), $event.target.value)"
                      type="number" 
                      min="1" 
                      max="254"
                      class="input input-bordered input-sm w-16"
                      :class="{ 'input-error': !isValidIP(server.ip) }"
                    />
                  </div>
                </td>
                <td v-if="networkMode === 'overlay'">
                  <div class="flex items-center gap-1">
                    <span class="text-sm text-base-content text-opacity-70">{{ server.zerotierIP || server.ip }}</span>
                  </div>
                  <div v-if="server.zerotierIP && isZeroTierIPInUse(server.zerotierIP)" class="text-xs text-warning mt-1">
                    {{ getZeroTierIPStatus(server.zerotierIP) }}
                  </div>
                </td>
                <td v-if="networkMode === 'overlay'">
                  <div class="text-sm text-base-content text-opacity-70">
                    {{ server.localIP || 'Not detected' }}
                  </div>
                </td>
                <td>
                  <span class="badge badge-outline">{{ getServerRole(server.hostname) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>




    <!-- Existing ZeroTier Members Info -->
    <div v-if="ipConflicts.length > 0" class="alert alert-info mb-6">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <div>
        <h3 class="font-bold text-base-content">Existing ZeroTier Members Detected</h3>
        <div class="prose prose-sm max-w-none mt-2">
          <p class="text-sm mb-2">The following IPs are already assigned in your ZeroTier network:</p>
          <ul class="text-warning-content">
            <li v-for="conflict in ipConflicts" :key="conflict">{{ conflict }}</li>
          </ul>
          <p class="text-sm mt-2 text-info">These are expected if you're reinstalling on the same servers. The installer will reuse these assignments.</p>
        </div>
      </div>
    </div>

    <!-- Validation Summary -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Configuration Summary</h2>
        
        <div class="stats stats-vertical lg:stats-horizontal shadow">
          <div class="stat">
            <div class="stat-title font-medium">Baremetal Servers</div>
            <div class="stat-value text-primary">{{ physicalServers.length }}</div>
            <div class="stat-desc text-base-content text-opacity-60">{{ physicalServers.filter(s => isValidIP(s.ip)).length }} with valid IPs</div>
          </div>
          
          
          <div class="stat">
            <div class="stat-title font-medium">IP Conflicts</div>
            <div class="stat-value" :class="ipConflicts.length > 0 ? 'text-error' : 'text-success'">
              {{ ipConflicts.length }}
            </div>
            <div class="stat-desc text-base-content text-opacity-60">{{ ipConflicts.length === 0 ? 'No conflicts' : 'Need resolution' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex justify-between">
      <button class="btn btn-ghost gap-2" @click="$router.push('/configuration')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
        Back to Configuration
      </button>
      
      <button 
        class="btn btn-primary gap-2"
        @click="saveAndContinue"
        :disabled="!isConfigurationValid"
      >
        Continue to Review
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { generateDynamicInventory, inventoryToYAML } from '../utils/inventoryGenerator.js'
import axios from 'axios'

const router = useRouter()

// Get saved configuration
const config = JSON.parse(localStorage.getItem('thinkube-config') || '{}')
const networkMode = ref(config.networkMode || sessionStorage.getItem('networkMode') || 'overlay')

// State
const networkConfig = ref({
  cidr: '192.168.1.0/24',
  gateway: '192.168.1.1',
  zerotierCIDR: '',  // Will be fetched from ZeroTier API
  primaryIngressOctet: '200',  // Default primary ingress IP octet
  secondaryIngressOctet: '201',  // Default secondary ingress IP octet
  dnsExternalOctet: '205',  // CoreDNS external IP octet (within MetalLB range)
  metallbStartOctet: '200',  // MetalLB IP range start
  metallbEndOctet: '210',  // MetalLB IP range end
  controllerZerotierIP: ''  // External controller ZeroTier IP
})

const physicalServers = ref([])
const networkValidationErrors = ref([])

// ZeroTier API state
const zerotierLoading = ref(false)
const zerotierError = ref('')
const zerotierNetworkName = ref('')
const zerotierUsedIPs = ref([])
const zerotierMembers = ref([])

// External controller detection
const isExternalController = ref(false)
const discoveredServers = ref([])
const controllerOctet = ref('')

// Computed
const ipConflicts = computed(() => {
  const conflicts = []
  const ipToServers = {}
  
  // In overlay mode, servers have both ZeroTier and local IPs, so only check for ZeroTier duplicates
  if (networkMode.value === 'overlay') {
    physicalServers.value.forEach(server => {
      if (server.zerotierIP) {
        if (!ipToServers[server.zerotierIP]) {
          ipToServers[server.zerotierIP] = []
        }
        ipToServers[server.zerotierIP].push(server.hostname)
      }
    })
    
    // Include controller IP if external
    if (isExternalController.value && networkConfig.value.controllerZerotierIP) {
      if (!ipToServers[networkConfig.value.controllerZerotierIP]) {
        ipToServers[networkConfig.value.controllerZerotierIP] = []
      }
      ipToServers[networkConfig.value.controllerZerotierIP].push('Controller')
    }
  } else {
    // In local mode, check local IPs
    physicalServers.value.forEach(server => {
      if (server.ip) {
        if (!ipToServers[server.ip]) {
          ipToServers[server.ip] = []
        }
        ipToServers[server.ip].push(server.hostname)
      }
    })
  }
  
  // Check for duplicates
  Object.entries(ipToServers).forEach(([ip, servers]) => {
    if (servers.length > 1) {
      conflicts.push(`IP ${ip} is assigned to multiple servers: ${servers.join(', ')}`)
    }
  })
  
  return conflicts
})

const isConfigurationValid = computed(() => {
  if (networkMode.value === 'overlay') {
    // In overlay mode, check ZeroTier IPs
    const allServersValid = physicalServers.value.every(s => 
      s.zerotierIP && isValidIP(s.zerotierIP)
    )
    
    const networkValid = isValidIP(networkConfig.value.gateway) && 
                        networkConfig.value.cidr &&
                        networkConfig.value.zerotierCIDR
    
    // Remove external controller validation since that's handled in ZeroTier discovery
    
    return allServersValid && networkValid && ipConflicts.value.length === 0
  } else {
    // In local mode, check local IPs
    const allServersValid = physicalServers.value.every(s => 
      s.ip && isValidIP(s.ip)
    )
    
    const networkValid = isValidIP(networkConfig.value.gateway) && 
                        networkConfig.value.cidr
    
    return allServersValid && networkValid && ipConflicts.value.length === 0
  }
})

// Get control plane hostname
const controlPlaneHostname = computed(() => {
  const clusterNodes = JSON.parse(sessionStorage.getItem('clusterNodes') || '[]')
  const controlPlane = clusterNodes.find(n => n.role === 'control_plane')
  return controlPlane?.hostname || ''
})

// Generate list of MetalLB IPs for ZeroTier
const metallbIPsForZeroTier = computed(() => {
  if (!networkConfig.value.zerotierCIDR || !networkConfig.value.metallbStartOctet || !networkConfig.value.metallbEndOctet) {
    return ''
  }
  
  const base = getNetworkBase(networkConfig.value.zerotierCIDR)
  const start = parseInt(networkConfig.value.metallbStartOctet)
  const end = parseInt(networkConfig.value.metallbEndOctet)
  
  const ips = []
  for (let i = start; i <= end; i++) {
    ips.push(`${base}.${i}`)
  }
  
  return ips.join(', ')
})

// Methods
const isValidIP = (ip) => {
  if (!ip) return false
  const regex = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/
  if (!regex.test(ip)) return false
  
  const parts = ip.split('.')
  return parts.every(part => {
    const num = parseInt(part, 10)
    return num >= 0 && num <= 255
  })
}

const isValidCIDR = (cidr) => {
  if (!cidr) return false
  const parts = cidr.split('/')
  if (parts.length !== 2) return false
  
  const ip = parts[0]
  const mask = parseInt(parts[1], 10)
  
  return isValidIP(ip) && mask >= 0 && mask <= 32
}

const getNetworkBase = (cidr) => {
  if (!cidr) return ''
  return cidr.split('/')[0].split('.').slice(0, 3).join('.')
}

const getLastOctet = (ip) => {
  if (!ip) return ''
  return ip.split('.').pop()
}

const setLastOctet = (baseNetwork, octet) => {
  if (!baseNetwork || !octet) return ''
  return `${baseNetwork}.${octet}`
}

const isZeroTierIPInUse = (ip) => {
  return zerotierUsedIPs.value.includes(ip)
}

const getZeroTierIPStatus = (ip) => {
  if (!ip) return ''
  if (isZeroTierIPInUse(ip)) {
    const member = zerotierMembers.value.find(m => m.ipAssignments.includes(ip))
    if (member) {
      const memberName = member.name || member.nodeId.substring(0, 10)
      
      // Check if member is offline (likely stale)
      if (!member.online) {
        return `Previously assigned to ${memberName} (offline)`
      }
      
      return `Used by ${memberName}`
    }
    return 'Already in use'
  }
  return ''
}

const isValidIngressOctet = (octet) => {
  if (!octet) return false
  const num = parseInt(octet, 10)
  return num >= 1 && num <= 254
}

const isIngressIPInUse = (octet) => {
  if (!octet) return false
  
  // In overlay mode, check against ZeroTier network
  if (networkMode.value === 'overlay') {
    if (!networkConfig.value.zerotierCIDR) return false
    const fullIP = `${getNetworkBase(networkConfig.value.zerotierCIDR)}.${octet}`
    
    // Check if it's used by ZeroTier AND not already assigned to a VM/server in our config
    if (isZeroTierIPInUse(fullIP)) {
      // Check if this IP is already assigned to one of our servers
      const serverWithIP = physicalServers.value.find(s => s.zerotierIP === fullIP)
      
      // If it's assigned to our infrastructure, it's not a problem
      if (serverWithIP) {
        return false
      }
      
      // It's used by something else in ZeroTier
      return true
    }
  } else {
    // In local mode, check against local network IPs
    const fullIP = `${getNetworkBase(networkConfig.value.cidr)}.${octet}`
    
    // Check if any server is using this IP
    const serverWithIP = physicalServers.value.find(s => s.ip === fullIP)
    if (serverWithIP) {
      return true
    }
  }
  
  return false
}

const isMetalLBRangeInvalid = () => {
  const start = parseInt(networkConfig.value.metallbStartOctet)
  const end = parseInt(networkConfig.value.metallbEndOctet)
  
  // Check if range is valid
  if (!start || !end || start > end) return true
  
  // Check if ingress IPs are within range
  return !isIngressIPInRange()
}

const isIngressIPInRange = () => {
  const start = parseInt(networkConfig.value.metallbStartOctet)
  const end = parseInt(networkConfig.value.metallbEndOctet)
  const primary = parseInt(networkConfig.value.primaryIngressOctet)
  const secondary = parseInt(networkConfig.value.secondaryIngressOctet)
  
  if (!start || !end || !primary || !secondary) return false
  
  return primary >= start && primary <= end && secondary >= start && secondary <= end
}


const getServerRole = (hostname) => {
  const clusterNodes = JSON.parse(sessionStorage.getItem('clusterNodes') || '[]')
  const node = clusterNodes.find(n => n.hostname === hostname && n.type === 'baremetal')
  if (!node) return 'LXD Host'
  
  switch (node.role) {
    case 'control_plane':
      return 'Control Plane'
    case 'worker':
      return 'Worker'
    default:
      return node.role || 'Host'
  }
}

// Controller IP functions
const updateControllerIP = () => {
  if (!controllerOctet.value || !networkConfig.value.zerotierCIDR) {
    networkConfig.value.controllerZerotierIP = ''
    return
  }
  
  const base = getNetworkBase(networkConfig.value.zerotierCIDR)
  networkConfig.value.controllerZerotierIP = `${base}.${controllerOctet.value}`
}

const isValidControllerIP = () => {
  if (!controllerOctet.value) return false
  const octet = parseInt(controllerOctet.value)
  return octet >= 1 && octet <= 254
}

const isDNSIPConflict = () => {
  const dnsOctet = networkConfig.value.dnsExternalOctet
  if (!dnsOctet) return false
  
  // Check if DNS IP conflicts with ingress IPs
  if (dnsOctet === networkConfig.value.primaryIngressOctet || 
      dnsOctet === networkConfig.value.secondaryIngressOctet) {
    return true
  }
  
  // Check if DNS IP conflicts with server IPs
  const networkBase = getNetworkBase(networkMode.value === 'overlay' ? networkConfig.value.zerotierCIDR : networkConfig.value.cidr)
  const dnsIP = `${networkBase}.${dnsOctet}`
  
  return physicalServers.value.some(server => 
    server.ip === dnsIP || server.zerotierIP === dnsIP
  )
}

const isDNSInMetalLBRange = () => {
  const dnsOctet = parseInt(networkConfig.value.dnsExternalOctet)
  const start = parseInt(networkConfig.value.metallbStartOctet)
  const end = parseInt(networkConfig.value.metallbEndOctet)
  
  if (!dnsOctet || !start || !end) return true // Allow if not configured yet
  
  return dnsOctet >= start && dnsOctet <= end
}

const isControllerIPConflict = () => {
  if (!networkConfig.value.controllerZerotierIP) return false
  
  // Check against physical servers
  const serverConflict = physicalServers.value.some(s => s.zerotierIP === networkConfig.value.controllerZerotierIP)
  if (serverConflict) return true
  
  
  // Check against ingress IPs
  const base = getNetworkBase(networkConfig.value.zerotierCIDR)
  const primaryIngress = `${base}.${networkConfig.value.primaryIngressOctet}`
  const secondaryIngress = `${base}.${networkConfig.value.secondaryIngressOctet}`
  if (networkConfig.value.controllerZerotierIP === primaryIngress || 
      networkConfig.value.controllerZerotierIP === secondaryIngress) return true
  
  // Check against existing ZeroTier members
  return isZeroTierIPInUse(networkConfig.value.controllerZerotierIP)
}

const getIPConflictSource = (ip) => {
  if (!ip) return ''
  
  // Check physical servers
  const server = physicalServers.value.find(s => s.zerotierIP === ip)
  if (server) return server.hostname
  
  
  // Check ingress IPs
  const base = getNetworkBase(networkConfig.value.zerotierCIDR)
  if (ip === `${base}.${networkConfig.value.primaryIngressOctet}`) return 'Primary Ingress'
  if (ip === `${base}.${networkConfig.value.secondaryIngressOctet}`) return 'Secondary Ingress'
  
  // Check ZeroTier members
  const member = zerotierMembers.value.find(m => m.ipAssignments.includes(ip))
  if (member) {
    return member.name || member.nodeId.substring(0, 10)
  }
  
  return 'another node'
}

const assignZeroTierIPs = () => {
  if (!networkConfig.value.zerotierCIDR) return
  
  // Extract base from ZeroTier CIDR (e.g., "192.168.191.0/24" -> "192.168.191")
  const zerotierBase = networkConfig.value.zerotierCIDR.split('/')[0].split('.').slice(0, 3).join('.')
  
  // Create a set of used IPs for quick lookup
  const usedIPSet = new Set(zerotierUsedIPs.value)
  
  // Add controller IP to used set if external
  if (isExternalController.value && networkConfig.value.controllerZerotierIP) {
    usedIPSet.add(networkConfig.value.controllerZerotierIP)
  }
  
  // Function to find next available IP
  const findNextAvailableIP = (startFrom = 10) => {
    let counter = startFrom
    while (counter < 254) {
      const testIP = `${zerotierBase}.${counter}`
      if (!usedIPSet.has(testIP)) {
        usedIPSet.add(testIP) // Mark as used for next iteration
        return testIP
      }
      counter++
    }
    return null // No available IPs
  }
  
  // Assign to physical servers
  physicalServers.value.forEach(server => {
    if (!server.zerotierIP || usedIPSet.has(server.zerotierIP)) {
      const newIP = findNextAvailableIP()
      if (newIP) {
        server.zerotierIP = newIP
      } else {
        zerotierError.value = 'No available ZeroTier IPs'
      }
    }
  })
  
}

const fetchZeroTierMembers = async (config) => {
  try {
    const response = await axios.post('/api/fetch-zerotier-members', {
      network_id: config.zerotierNetworkId,
      api_token: config.zerotierApiToken
    })
    
    if (response.data.success) {
      zerotierMembers.value = response.data.members
      zerotierUsedIPs.value = response.data.used_ips
      console.log(`Found ${response.data.members.length} ZeroTier members with ${response.data.used_ips.length} used IPs`)
    }
  } catch (error) {
    console.error('Failed to fetch ZeroTier members:', error)
  }
}

const fetchZeroTierNetwork = async () => {
  const config = JSON.parse(localStorage.getItem('thinkube-config') || '{}')
  
  if (!config.zerotierNetworkId || !config.zerotierApiToken) {
    // In overlay mode, we should already have the CIDR from discovery
    if (networkConfig.value.zerotierCIDR) {
      // Just fetch members for IP assignment
      await fetchZeroTierMembers(config)
      assignZeroTierIPs()
    }
    return
  }
  
  zerotierLoading.value = true
  zerotierError.value = ''
  zerotierNetworkName.value = ''
  
  try {
    // Fetch network info and members in parallel
    const [networkResponse] = await Promise.all([
      axios.post('/api/fetch-zerotier-network', {
        network_id: config.zerotierNetworkId,
        api_token: config.zerotierApiToken
      }),
      fetchZeroTierMembers(config)
    ])
    
    if (networkResponse.data.success) {
      // Only update CIDR if we don't already have it from discovery
      if (!networkConfig.value.zerotierCIDR) {
        networkConfig.value.zerotierCIDR = networkResponse.data.cidr
      }
      zerotierNetworkName.value = networkResponse.data.network_name
      zerotierError.value = ''
      
      // Now assign ZeroTier IPs using the actual CIDR and avoiding used IPs
      assignZeroTierIPs()
    } else {
      zerotierError.value = networkResponse.data.message
      // Don't clear CIDR if we already have it from discovery
    }
  } catch (error) {
    zerotierError.value = error.response?.data?.message || 'Failed to connect to ZeroTier API'
    // Don't clear CIDR if we already have it from discovery
  } finally {
    zerotierLoading.value = false
  }
}

const generateDefaultIPs = () => {
  const networkBase = networkConfig.value.cidr.split('/')[0].split('.').slice(0, 3).join('.')
  
  // Find highest used IP in physical servers
  const usedIPs = physicalServers.value.map(s => parseInt(s.ip.split('.').pop())).filter(Boolean)
  let vmIPCounter = Math.max(...usedIPs, 50) + 10
  
  
  // Generate LXD internal network based on local network CIDR
  // This keeps them in the same address family while avoiding conflicts
  
  // Ingress IP will be configured later with MicroK8s
}


const saveAndContinue = () => {
  // Save network configuration
  sessionStorage.setItem('networkConfiguration', JSON.stringify({
    networkConfig: networkConfig.value,
    physicalServers: physicalServers.value,
  }))
  
  // Also generate and save the final inventory for later use
  try {
    const inventory = generateDynamicInventory()
    const inventoryYAML = inventoryToYAML(inventory)
    sessionStorage.setItem('generatedInventory', inventoryYAML)
  } catch (error) {
    console.error('Failed to generate inventory:', error)
  }
  
  router.push('/review')
}

// Watch for changes and validate (simplified)
watch([physicalServers, networkConfig], () => {
  // Any additional validation logic can go here
}, { deep: true })

// Function to get cluster network from node information
const getClusterNetwork = () => {
  // Get the network info from the nodes, not from the installer machine
  const serverNetworkInfo = JSON.parse(sessionStorage.getItem('serverNetworkInfo') || '[]')
  
  if (serverNetworkInfo.length > 0 && serverNetworkInfo[0].cidr) {
    // Use the network from the actual cluster nodes
    const clusterCIDR = serverNetworkInfo[0].cidr
    const gateway = serverNetworkInfo[0].gateway || clusterCIDR.split('/')[0].split('.').slice(0, 3).join('.') + '.1'
    
    console.log('Using cluster network from nodes:', clusterCIDR)
    return {
      cidr: clusterCIDR,
      gateway: gateway,
      detected: true
    }
  }
  
  // No network info available - return error state
  console.error('No network information available from cluster nodes')
  return {
    cidr: '',
    gateway: '',
    detected: false
  }
}

// Validate that all nodes are on the same network
const validateNetworkConsistency = (networkInfo) => {
  networkValidationErrors.value = []
  
  if (networkInfo.length === 0) {
    return
  }
  
  // Get unique CIDRs
  const cidrs = [...new Set(networkInfo.map(n => n.cidr).filter(Boolean))]
  
  if (cidrs.length > 1) {
    networkValidationErrors.value.push(`Nodes are on different networks: ${cidrs.join(', ')}`)
  }
  
  // Use the detected network if available
  if (cidrs.length > 0) {
    const detectedCIDR = cidrs[0]
    const detectedGateway = networkInfo.find(n => n.gateway)?.gateway || ''
    
    // Update local network config with detected values
    if (detectedCIDR) {
      // In overlay mode, this is the local network, not ZeroTier
      if (networkMode.value === 'overlay') {
        networkConfig.value.cidr = detectedCIDR
        console.log('Using detected local network for cluster internal:', detectedCIDR)
      } else {
        // In local mode, this is the primary network
        networkConfig.value.cidr = detectedCIDR
        console.log('Using detected network:', detectedCIDR)
      }
    }
    if (detectedGateway) {
      networkConfig.value.gateway = detectedGateway
      console.log('Using detected gateway:', detectedGateway)
    }
  }
}

// Lifecycle
onMounted(async () => {
  // Debug: Log what's in sessionStorage
  console.log('NetworkConfiguration - SessionStorage contents:')
  console.log('selectedServers:', sessionStorage.getItem('selectedServers'))
  console.log('discoveredServers:', sessionStorage.getItem('discoveredServers'))
  console.log('networkCIDR:', sessionStorage.getItem('networkCIDR'))
  console.log('networkMode:', sessionStorage.getItem('networkMode'))
  
  // Load data from previous steps
  const selectedServers = JSON.parse(sessionStorage.getItem('selectedServers') || '[]')
  const discoveredServersData = JSON.parse(sessionStorage.getItem('discoveredServers') || '[]')
  const networkCIDR = sessionStorage.getItem('networkCIDR') || '192.168.1.0/24'
  const serverNetworkInfo = JSON.parse(sessionStorage.getItem('serverNetworkInfo') || '[]')
  
  // Use selected servers or discovered servers
  const serversToUse = selectedServers.length > 0 ? selectedServers : discoveredServersData
  
  console.log('Servers to use:', serversToUse)
  console.log('Server network info:', serverNetworkInfo)
  
  if (serversToUse.length > 0) {
    // Use the servers we have
    // In overlay mode, the discovered IP IS the ZeroTier IP
    const networkMode = sessionStorage.getItem('networkMode') || 'overlay'
    physicalServers.value = serversToUse.map(server => {
      // Find network info for this server
      const netInfo = serverNetworkInfo.find(n => n.hostname === server.hostname)
      
      return {
        hostname: server.hostname || server.ip,
        ip: netInfo?.localIP || '',  // Local IP from hardware detection
        zerotierIP: networkMode === 'overlay' ? server.ip : '',  // In overlay, discovered IP is ZeroTier IP
        localIP: netInfo?.localIP || ''  // Store for display
      }
    })
    
    // Validate network consistency
    validateNetworkConsistency(serverNetworkInfo)
  } else {
    console.warn('No servers found in sessionStorage!')
  }
  
  // Set the discovered servers for other uses
  discoveredServers.value = serversToUse
  
  // Check if we're running from an external controller
  const hasLocalServer = discoveredServers.value.some(server => server.is_local)
  isExternalController.value = !hasLocalServer && discoveredServers.value.length > 0
  
  // Set network configuration
  console.log('Network Mode:', networkMode.value)
  console.log('Network CIDR from discovery:', networkCIDR)
  
  // In overlay mode, networkCIDR from discovery is the ZeroTier network
  if (networkMode.value === 'overlay') {
    // For overlay mode, store the ZeroTier CIDR from discovery
    networkConfig.value.zerotierCIDR = networkCIDR
    console.log('Setting ZeroTier CIDR from discovery:', networkCIDR)
    
    // Get the actual cluster network from node information
    const clusterNet = getClusterNetwork()
    if (clusterNet.detected) {
      networkConfig.value.cidr = clusterNet.cidr
      networkConfig.value.gateway = clusterNet.gateway
      console.log('Kubernetes cluster network from nodes:', clusterNet)
    } else {
      // Add error to validation errors
      networkValidationErrors.value.push('Unable to detect cluster network from nodes. Hardware detection may have failed.')
      console.error('Failed to detect cluster network')
    }
    console.log('After detection - ZeroTier CIDR:', networkConfig.value.zerotierCIDR)
    console.log('After detection - Local CIDR:', networkConfig.value.cidr)
  } else {
    // For local mode, networkCIDR is the actual LAN
    networkConfig.value.cidr = networkCIDR
    const networkBase = networkCIDR.split('/')[0].split('.').slice(0, 3).join('.')  
    networkConfig.value.gateway = `${networkBase}.1`
  }
  
  // Fetch ZeroTier network details automatically if in overlay mode
  // Note: We already have the CIDR from discovery, but this fetches additional details
  if (networkMode === 'overlay') {
    // Don't overwrite the CIDR we already have from discovery
    const existingCIDR = networkConfig.value.zerotierCIDR
    await fetchZeroTierNetwork()
    // Restore the CIDR if it was overwritten
    if (!networkConfig.value.zerotierCIDR && existingCIDR) {
      networkConfig.value.zerotierCIDR = existingCIDR
    }
  }
  
  // Generate default IP assignments (after ZeroTier CIDR is available)
  generateDefaultIPs()
  
  // Load saved configuration if exists
  const savedConfig = sessionStorage.getItem('networkConfiguration')
  if (savedConfig) {
    const parsed = JSON.parse(savedConfig)
    // Don't overwrite the CIDR values we just set from discovery
    const currentZeroTierCIDR = networkConfig.value.zerotierCIDR
    const currentLocalCIDR = networkConfig.value.cidr
    networkConfig.value = { ...networkConfig.value, ...parsed.networkConfig }
    // Restore the correct CIDR values if they were overwritten
    if (networkMode.value === 'overlay') {
      networkConfig.value.zerotierCIDR = currentZeroTierCIDR || parsed.networkConfig.zerotierCIDR
      networkConfig.value.cidr = currentLocalCIDR || parsed.networkConfig.cidr
    }
    if (parsed.physicalServers) physicalServers.value = parsed.physicalServers
  }
  
  // After loading/creating data, assign ZeroTier IPs if we have CIDR
  if (networkConfig.value.zerotierCIDR) {
    assignZeroTierIPs()
  }
})
</script>