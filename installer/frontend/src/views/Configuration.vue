/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold mb-6 text-base-content">Cluster Configuration</h1>
    
    
    <form @submit.prevent="saveAndContinue">
      <!-- Basic Settings -->
      <div class="card bg-base-100 shadow-xl mb-6">
        <div class="card-body">
          <h2 class="card-title mb-4">Basic Settings</h2>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="form-control">
              <label class="label">
                <span class="label-text">Cluster Name</span>
                <span class="label-text-alt">Name for your Thinkube cluster</span>
              </label>
              <input 
                v-model="config.clusterName" 
                type="text" 
                placeholder="thinkube" 
                class="input input-bordered w-full"
                :class="{ 'input-error': errors.clusterName }"
                required
              />
              <label v-if="errors.clusterName" class="label">
                <span class="label-text-alt text-error">{{ errors.clusterName }}</span>
              </label>
            </div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">Domain Name</span>
                <span class="label-text-alt">Your domain for the cluster</span>
              </label>
              <input 
                v-model="config.domainName" 
                type="text" 
                placeholder="thinkube.com" 
                class="input input-bordered w-full"
                :class="{ 'input-error': errors.domainName }"
                required
              />
              <label v-if="errors.domainName" class="label">
                <span class="label-text-alt text-error">{{ errors.domainName }}</span>
              </label>
            </div>

            <div class="form-control md:col-span-2">
              <label class="label">
                <span class="label-text">Cloudflare API Token</span>
                <span class="label-text-alt">For SSL certificate generation</span>
              </label>
              <div class="relative">
                <input 
                  v-model="config.cloudflareToken" 
                  :type="showCloudflareToken ? 'text' : 'password'" 
                  placeholder="Cloudflare API Token" 
                  class="input input-bordered w-full pr-24"
                  :class="{ 'input-error': errors.cloudflareToken, 'input-success': cloudflareVerified }"
                />
                <div class="absolute inset-y-0 right-0 flex items-center pr-3 gap-2">
                  <button 
                    v-if="config.cloudflareToken && config.domainName"
                    type="button"
                    class="btn btn-xs btn-ghost"
                    @click="verifyCloudflare"
                    :disabled="verifyingCloudflare"
                  >
                    <span v-if="verifyingCloudflare" class="loading loading-spinner loading-xs"></span>
                    <span v-else-if="cloudflareVerified" class="text-success">✓</span>
                    <span v-else>Verify</span>
                  </button>
                  <button 
                    type="button"
                    class="btn btn-ghost btn-xs btn-square"
                    @click="showCloudflareToken = !showCloudflareToken"
                  >
                    <svg v-if="showCloudflareToken" class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"></path>
                    </svg>
                    <svg v-else class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    </svg>
                  </button>
                </div>
              </div>
              <label v-if="errors.cloudflareToken" class="label">
                <span class="label-text-alt text-error">{{ errors.cloudflareToken }}</span>
              </label>
              <label v-else-if="cloudflareVerified" class="label">
                <span class="label-text-alt text-success">✓ Token has access to {{ config.domainName }}</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- ZeroTier Configuration (Only for Overlay Mode) -->
      <div v-if="config.networkMode === 'overlay'" class="card bg-base-100 shadow-xl mb-6">
        <div class="card-body">
          <h2 class="card-title mb-4">ZeroTier Configuration</h2>
          <p class="text-sm text-base-content text-opacity-70 mb-4">
            Configure ZeroTier overlay networking to connect distributed nodes securely over the internet.
          </p>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="form-control">
              <label class="label">
                <span class="label-text">ZeroTier Network ID</span>
                <span class="label-text-alt">16-character network ID from ZeroTier Central</span>
              </label>
              <input 
                v-model="config.zerotierNetworkId" 
                type="text" 
                placeholder="16-character network ID" 
                class="input input-bordered"
                :class="{ 'input-error': errors.zerotierNetworkId }"
              />
              <label v-if="errors.zerotierNetworkId" class="label">
                <span class="label-text-alt text-error">{{ errors.zerotierNetworkId }}</span>
              </label>
            </div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">ZeroTier API Token</span>
                <span class="label-text-alt">For automatic node authorization</span>
              </label>
              <div class="relative">
                <input 
                  v-model="config.zerotierApiToken" 
                  :type="showZerotierToken ? 'text' : 'password'" 
                  placeholder="ZeroTier Central API Token" 
                  class="input input-bordered w-full pr-24"
                  :class="{ 'input-error': errors.zerotierApiToken }"
                />
                <div class="absolute inset-y-0 right-0 flex items-center pr-3 gap-2">
                  <button 
                    v-if="config.zerotierApiToken && config.zerotierNetworkId"
                    type="button"
                    class="btn btn-xs btn-ghost"
                    @click="verifyZerotier"
                    :disabled="verifyingZerotier"
                  >
                    <span v-if="verifyingZerotier" class="loading loading-spinner loading-xs"></span>
                    <span v-else-if="zerotierVerified" class="text-success">✓</span>
                    <span v-else>Verify</span>
                  </button>
                  <button 
                    type="button"
                    class="btn btn-ghost btn-xs btn-square"
                    @click="showZerotierToken = !showZerotierToken"
                  >
                    <svg v-if="showZerotierToken" class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"></path>
                    </svg>
                    <svg v-else class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    </svg>
                  </button>
                </div>
              </div>
              <label v-if="errors.zerotierApiToken" class="label">
                <span class="label-text-alt text-error">{{ errors.zerotierApiToken }}</span>
              </label>
              <label v-else-if="zerotierVerified" class="label">
                <span class="label-text-alt text-success">✓ Token verified with network access</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- GitHub Integration (Required) -->
      <div class="card bg-base-100 shadow-xl mb-6">
        <div class="card-body">
          <h2 class="card-title mb-4">GitHub Integration (Required)</h2>
          <div class="alert alert-warning mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>GitHub access is required for Thinkube core components. Many services depend on Git repositories for configuration and deployment.</span>
          </div>
          <p class="text-sm mb-4">
            Provide a GitHub personal access token to enable repository operations, GitOps workflows, and CI/CD integration.
          </p>
          
          <div class="form-control">
            <label class="label">
              <span class="label-text">GitHub Personal Access Token</span>
              <a href="https://github.com/settings/tokens/new?scopes=repo,workflow,packages:write" target="_blank" class="label-text-alt link link-primary">
                Generate token →
              </a>
            </label>
            <div class="relative">
              <input 
                v-model="config.githubToken" 
                :type="showGithubToken ? 'text' : 'password'"
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
                class="input input-bordered pr-16 w-full font-mono"
                :class="{ 'input-error': errors.githubToken }"
              />
              <div class="absolute inset-y-0 right-0 flex items-center pr-3 gap-2">
                <button 
                  v-if="config.githubToken"
                  type="button"
                  class="btn btn-xs btn-ghost"
                  @click="verifyGithub"
                  :disabled="verifyingGithub"
                >
                  <span v-if="verifyingGithub" class="loading loading-spinner loading-xs"></span>
                  <span v-else-if="githubVerified" class="text-success">✓</span>
                  <span v-else>Verify</span>
                </button>
                <button 
                  type="button"
                  class="btn btn-ghost btn-xs btn-square"
                  @click="showGithubToken = !showGithubToken"
                >
                  <svg v-if="showGithubToken" class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"></path>
                  </svg>
                  <svg v-else class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                  </svg>
                </button>
              </div>
            </div>
            <label v-if="errors.githubToken" class="label">
              <span class="label-text-alt text-error">{{ errors.githubToken }}</span>
            </label>
            <label v-else-if="githubVerified" class="label">
              <span class="label-text-alt text-success">✓ Token verified with repository access</span>
            </label>
            <label class="label">
              <span class="label-text-alt">Required scopes: repo, workflow, packages:write</span>
            </label>
          </div>

          <!-- GitHub Organization -->
          <div class="form-control mt-4">
            <label class="label">
              <span class="label-text">GitHub Organization or Username</span>
            </label>
            <input 
              v-model="config.githubOrg" 
              type="text"
              placeholder="your-github-org-or-username" 
              class="input input-bordered w-full"
              :class="{ 'input-error': errors.githubOrg }"
            />
            <label v-if="errors.githubOrg" class="label">
              <span class="label-text-alt text-error">{{ errors.githubOrg }}</span>
            </label>
            <label class="label">
              <span class="label-text-alt">The GitHub organization or username where repositories will be created</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="flex justify-between">
        <button type="button" class="btn btn-ghost gap-2" @click="$router.push('/role-assignment')">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
          </svg>
          Back to Role Assignment
        </button>
        <button 
          type="submit"
          class="btn btn-primary gap-2"
          :disabled="!isValid"
        >
          Review Configuration
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
          </svg>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()


const config = ref({
  networkMode: 'overlay', // Default to overlay mode (ZeroTier)
  clusterName: 'thinkube',
  domainName: 'my-homelab.com',
  cloudflareToken: '',
  zerotierNetworkId: '',
  zerotierApiToken: '',
  githubToken: '',
  githubOrg: ''
})

const errors = ref({
  clusterName: '',
  domainName: '',
  cloudflareToken: '',
  zerotierNetworkId: '',
  zerotierApiToken: '',
  githubToken: '',
  githubOrg: ''
})

const showCloudflareToken = ref(false)
const showZerotierToken = ref(false)
const showGithubToken = ref(false)
const verifyingCloudflare = ref(false)
const cloudflareVerified = ref(false)
const verifyingGithub = ref(false)
const githubVerified = ref(false)

// Load saved configuration on mount
onMounted(() => {
  // Load network mode from localStorage (set during Server Discovery)
  const savedConfig = localStorage.getItem('thinkube-config')
  if (savedConfig) {
    try {
      const parsed = JSON.parse(savedConfig)
      // Network mode was already selected in Server Discovery
      if (parsed.networkMode) {
        config.value.networkMode = parsed.networkMode
      }
      // Restore API tokens and other sensitive data
      if (parsed.cloudflareToken) {
        config.value.cloudflareToken = parsed.cloudflareToken
      }
      if (parsed.zerotierNetworkId) {
        config.value.zerotierNetworkId = parsed.zerotierNetworkId
      }
      if (parsed.zerotierApiToken) {
        config.value.zerotierApiToken = parsed.zerotierApiToken
      }
      if (parsed.domainName) {
        config.value.domainName = parsed.domainName
      }
      if (parsed.clusterName) {
        config.value.clusterName = parsed.clusterName
      }
      if (parsed.githubOrg) {
        config.value.githubOrg = parsed.githubOrg
      }
    } catch (e) {
      console.error('Failed to parse saved config:', e)
    }
  }
  
  // Also check sessionStorage for network mode
  const networkMode = sessionStorage.getItem('networkMode')
  if (networkMode) {
    config.value.networkMode = networkMode
  }
})

// Validation functions
const isValidClusterName = (name) => /^[a-z0-9-]+$/.test(name)
const isValidDomain = (domain) => /^[a-z0-9.-]+$/.test(domain)
const isValidIP = (ip) => /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(ip)

// Watch for changes and validate
watch(() => config.value.clusterName, (val) => {
  errors.value.clusterName = val && !isValidClusterName(val) 
    ? 'Only lowercase letters, numbers, and hyphens' 
    : ''
})

watch(() => config.value.domainName, (val) => {
  errors.value.domainName = val && !isValidDomain(val) 
    ? 'Invalid domain name' 
    : ''
})

// Clear ZeroTier verification when switching network modes
watch(() => config.value.networkMode, (newMode) => {
  if (newMode === 'local') {
    // Clear ZeroTier verification status when switching to local mode
    zerotierVerified.value = false
    errors.value.zerotierApiToken = ''
    errors.value.zerotierNetworkId = ''
  }
})


const isValid = computed(() => {
  const baseValid = config.value.clusterName &&
                   config.value.domainName &&
                   config.value.cloudflareToken &&
                   config.value.githubToken &&  // GitHub token is now required
                   config.value.githubOrg &&     // GitHub org is also required
                   !errors.value.clusterName &&
                   !errors.value.domainName &&
                   !errors.value.githubOrg

  // If overlay mode is selected, ZeroTier fields are required
  if (config.value.networkMode === 'overlay') {
    return baseValid &&
           config.value.zerotierNetworkId &&
           config.value.zerotierApiToken
  }
  
  // For local mode, ZeroTier fields are not required
  return baseValid
})

const verifyCloudflare = async () => {
  verifyingCloudflare.value = true
  cloudflareVerified.value = false
  errors.value.cloudflareToken = ''
  
  try {
    const response = await axios.post('/api/verify-cloudflare', {
      token: config.value.cloudflareToken,
      domain: config.value.domainName
    })
    
    if (response.data.valid) {
      cloudflareVerified.value = true
      errors.value.cloudflareToken = ''
    } else {
      errors.value.cloudflareToken = response.data.message || 'Token does not have access to this domain'
      cloudflareVerified.value = false
    }
  } catch (error) {
    errors.value.cloudflareToken = error.response?.data?.detail || 'Failed to verify Cloudflare token'
    cloudflareVerified.value = false
  } finally {
    verifyingCloudflare.value = false
  }
}

// Reset verification when token or domain changes
watch([() => config.value.cloudflareToken, () => config.value.domainName], () => {
  cloudflareVerified.value = false
  errors.value.cloudflareToken = ''
})

// Store Cloudflare token securely
const storeCloudflareToken = async () => {
  try {
    const response = await axios.post('/api/store-cloudflare-token', {
      token: config.value.cloudflareToken
    })
    
    if (response.data.success) {
      console.log('Cloudflare token stored securely')
      return true
    }
    return false
  } catch (error) {
    console.error('Failed to store Cloudflare token:', error)
    return false
  }
}

const zerotierVerified = ref(false)
const verifyingZerotier = ref(false)

const verifyZerotier = async () => {
  if (!config.value.zerotierApiToken || !config.value.zerotierNetworkId) {
    errors.value.zerotierApiToken = 'Both API token and Network ID are required'
    zerotierVerified.value = false
    return false
  }
  
  verifyingZerotier.value = true
  errors.value.zerotierApiToken = ''
  
  try {
    const response = await axios.post('/api/verify-zerotier', {
      api_token: config.value.zerotierApiToken,
      network_id: config.value.zerotierNetworkId
    })
    
    if (response.data.valid) {
      zerotierVerified.value = true
      errors.value.zerotierApiToken = ''
      return true
    } else {
      errors.value.zerotierApiToken = response.data.message || 'Invalid credentials'
      zerotierVerified.value = false
      return false
    }
  } catch (error) {
    errors.value.zerotierApiToken = error.response?.data?.detail || 'Failed to verify ZeroTier credentials'
    zerotierVerified.value = false
    return false
  } finally {
    verifyingZerotier.value = false
  }
}

// Reset ZeroTier verification when credentials change
watch([() => config.value.zerotierApiToken, () => config.value.zerotierNetworkId], () => {
  zerotierVerified.value = false
  errors.value.zerotierApiToken = ''
})

// GitHub token verification
const verifyGithub = async () => {
  if (!config.value.githubToken) {
    errors.value.githubToken = 'GitHub token is required'
    githubVerified.value = false
    return false
  }
  
  verifyingGithub.value = true
  errors.value.githubToken = ''
  
  try {
    const response = await axios.post('/api/verify-github', {
      token: config.value.githubToken
    })
    
    if (response.data.valid) {
      githubVerified.value = true
      errors.value.githubToken = ''
      return true
    } else {
      errors.value.githubToken = response.data.message || 'Invalid GitHub token'
      githubVerified.value = false
      return false
    }
  } catch (error) {
    errors.value.githubToken = error.response?.data?.detail || 'Failed to verify GitHub token'
    githubVerified.value = false
    return false
  } finally {
    verifyingGithub.value = false
  }
}

// Reset GitHub verification when token changes
watch(() => config.value.githubToken, () => {
  githubVerified.value = false
  errors.value.githubToken = ''
})

// Store GitHub token securely
const storeGithubToken = async () => {
  if (!config.value.githubToken) {
    return true  // Optional, so return true if not provided
  }
  
  try {
    const response = await axios.post('/api/store-github-token', {
      token: config.value.githubToken
    })
    
    if (response.data.success) {
      console.log('GitHub token stored securely')
      return true
    }
    return false
  } catch (error) {
    console.error('Failed to store GitHub token:', error)
    return false
  }
}

// Store ZeroTier token securely
const storeZerotierToken = async () => {
  try {
    const response = await axios.post('/api/store-zerotier-token', {
      token: config.value.zerotierApiToken
    })
    
    if (response.data.success) {
      console.log('ZeroTier token stored securely')
      return true
    }
    return false
  } catch (error) {
    console.error('Failed to store ZeroTier token:', error)
    return false
  }
}

const saveAndContinue = async () => {
  if (!isValid.value) {
    alert('Please fix all validation errors before continuing')
    return
  }
  
  // Verify Cloudflare token is required and verified
  if (!config.value.cloudflareToken) {
    alert('Cloudflare API token is required')
    return
  }
  
  if (!cloudflareVerified.value) {
    await verifyCloudflare()
    if (!cloudflareVerified.value) {
      alert('Please provide a valid Cloudflare API token with access to your domain')
      return
    }
  }
  
  // Verify ZeroTier credentials only if overlay mode is selected
  if (config.value.networkMode === 'overlay') {
    if (!config.value.zerotierApiToken || !config.value.zerotierNetworkId) {
      alert('ZeroTier API token and Network ID are both required for overlay mode')
      return
    }
    
    if (!zerotierVerified.value) {
      const zerotierValid = await verifyZerotier()
      if (!zerotierValid) {
        alert('Please provide valid ZeroTier credentials with network access')
        return
      }
    }
  }
  
  // Verify GitHub token if provided
  if (config.value.githubToken && !githubVerified.value) {
    const githubValid = await verifyGithub()
    if (!githubValid) {
      alert('Please provide a valid GitHub token or leave it empty')
      return
    }
  }
  
  // Store Cloudflare token securely in ~/.env
  const cloudflareStored = await storeCloudflareToken()
  if (!cloudflareStored) {
    alert('Failed to store Cloudflare token securely. Please try again.')
    return
  }
  
  // Store ZeroTier token securely in ~/.env (only if overlay mode)
  if (config.value.networkMode === 'overlay') {
    const zerotierStored = await storeZerotierToken()
    if (!zerotierStored) {
      alert('Failed to store ZeroTier token securely. Please try again.')
      return
    }
  }
  
  // Store GitHub token securely in ~/.env (if provided)
  const githubStored = await storeGithubToken()
  if (!githubStored) {
    alert('Failed to store GitHub token securely. Please try again.')
    return
  }
  
  // Get the already-verified sudo password from sessionStorage
  const sudoPassword = sessionStorage.getItem('sudoPassword')
  // Get the system username from sessionStorage
  const systemUsername = sessionStorage.getItem('systemUsername')
  
  // Save config WITHOUT the sensitive tokens (they're stored securely in ~/.env)
  const configToSave = {
    networkMode: config.value.networkMode,
    clusterName: config.value.clusterName,
    domainName: config.value.domainName,
    githubOrg: config.value.githubOrg,
    sudoPassword: sudoPassword,
    systemUsername: systemUsername
  }
  
  // Only include ZeroTier config if overlay mode is selected
  if (config.value.networkMode === 'overlay') {
    configToSave.zerotierNetworkId = config.value.zerotierNetworkId
    configToSave.zerotierApiToken = config.value.zerotierApiToken
  }
  localStorage.setItem('thinkube-config', JSON.stringify(configToSave))
  
  // Also save tokens to sessionStorage for immediate use in deployment
  sessionStorage.setItem('networkMode', config.value.networkMode)
  sessionStorage.setItem('cloudflareToken', config.value.cloudflareToken)
  
  // Only store ZeroTier tokens if overlay mode is selected
  if (config.value.networkMode === 'overlay') {
    sessionStorage.setItem('zerotierApiToken', config.value.zerotierApiToken)
    sessionStorage.setItem('zerotierNetworkId', config.value.zerotierNetworkId)
  }
  
  if (config.value.githubToken) {
    sessionStorage.setItem('githubToken', config.value.githubToken)
    sessionStorage.setItem('githubOrg', config.value.githubOrg)
  }
  
  router.push('/network-configuration')
}
</script>