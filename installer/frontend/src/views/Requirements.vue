/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-6 text-base-content">System Requirements</h1>
    
    <div v-if="error" class="alert alert-error mb-6">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{{ error }}</span>
    </div>
    
    <div v-if="isLoading" class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <div class="flex flex-col items-center justify-center py-8">
          <div class="loading loading-spinner loading-lg text-primary mb-4"></div>
          <p class="text-lg">Checking system requirements...</p>
        </div>
      </div>
    </div>
    
    <div v-else class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Control Node Requirements</h2>
        
        <!-- System Requirements -->
        <div v-if="systemRequirements.length > 0" class="mb-6">
          <h3 class="font-semibold mb-3 text-base-content">System Requirements</h3>
          <div class="space-y-3">
            <div v-for="req in systemRequirements" :key="req.name" 
                 class="flex items-center gap-4 p-3 rounded-lg bg-base-200">
              <div class="flex-shrink-0">
                <svg v-if="req.status === 'pass'" class="w-6 h-6 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <svg v-else-if="req.status === 'fail'" class="w-6 h-6 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
              <div class="flex-1">
                <h3 class="font-semibold text-base-content">{{ req.name }}</h3>
                <p class="text-sm text-base-content text-opacity-60">
                  {{ req.details }}
                  <span v-if="req.required" class="badge badge-sm badge-neutral ml-2">Required</span>
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Tools to be Installed -->
        <div v-if="toolRequirements.length > 0">
          <h3 class="font-semibold mb-3 text-base-content">Tools to be Installed</h3>
          <div class="space-y-3">
            <div v-for="req in toolRequirements" :key="req.name" 
                 class="flex items-center gap-4 p-3 rounded-lg bg-base-200">
              <div class="flex-shrink-0">
                <svg v-if="req.status === 'pass'" class="w-6 h-6 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <svg v-else-if="req.status === 'missing'" class="w-6 h-6 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
              <div class="flex-1">
                <h3 class="font-semibold text-base-content">{{ req.name }}</h3>
                <p class="text-sm text-base-content text-opacity-60">
                  {{ req.details }}
                  <span v-if="req.action === 'install'" class="badge badge-sm badge-info ml-2">Will be installed</span>
                </p>
              </div>
            </div>
          </div>
        </div>

        <div v-if="!hardRequirementsMet && allChecked" class="alert alert-error mt-6">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>System requirements are not met. Please resolve them before continuing.</span>
        </div>

        <div v-if="hasToolsToInstall && hardRequirementsMet && allChecked" class="mt-6">
          <div class="alert alert-info">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <div class="prose prose-sm max-w-none">
              <p class="text-base-content">Some tools need to be installed to continue.</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="!isLoading" class="flex justify-between">
      <button class="btn btn-ghost gap-2" @click="$router.push('/')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
        Back
      </button>
      <button 
        v-if="allRequirementsMet"
        class="btn btn-primary gap-2" 
        @click="$router.push('/sudo-password')"
      >
        Continue
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </button>
      <button 
        v-else-if="canInstallTools"
        class="btn btn-primary gap-2"
        @click="$router.push('/sudo-password')"
      >
        Install Tools & Continue
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </button>
      <div v-else-if="!hardRequirementsMet" class="text-error">
        Please resolve the system requirements before continuing.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const requirements = ref([])
const isLoading = ref(true)
const error = ref('')

// Separate requirements by category
const systemRequirements = computed(() => {
  return requirements.value.filter(req => req.category === 'system')
})

const toolRequirements = computed(() => {
  return requirements.value.filter(req => req.category === 'tools')
})

// Check if hard requirements are met
const hardRequirementsMet = computed(() => {
  return systemRequirements.value.every(req => req.status === 'pass')
})

// Check if there are tools to install
const hasToolsToInstall = computed(() => {
  return toolRequirements.value.some(req => req.status === 'missing')
})

// Overall status
const allRequirementsMet = computed(() => {
  return hardRequirementsMet.value && !hasToolsToInstall.value
})

const allChecked = computed(() => {
  return !isLoading.value
})

const canInstallTools = computed(() => {
  // Can install tools if all hard requirements are met and there are tools to install
  return hardRequirementsMet.value && hasToolsToInstall.value
})

const runSetup = async () => {
  try {
    // Get sudo password from previous configuration step
    const config = JSON.parse(localStorage.getItem('thinkube-config') || '{}')
    
    const response = await axios.post('/api/run-setup', {
      sudo_password: config.sudoPassword || ''
    })
    
    if (response.data.status === 'exists') {
      alert('thinkube is already installed: ' + response.data.details.join(', '))
    } else {
      // Redirect to installation page to watch progress
      window.location.href = '/installation'
    }
  } catch (error) {
    console.error('Failed to start setup:', error)
    alert('Failed to start setup: ' + error.message)
  }
}

onMounted(async () => {
  // Keep loading state for at least 500ms to prevent flash
  const minLoadTime = new Promise(resolve => setTimeout(resolve, 500))
  
  try {
    error.value = ''
    const [response] = await Promise.all([
      axios.get('/api/check-requirements'),
      minLoadTime
    ])
    
    // Use the data as-is from the backend
    requirements.value = response.data.requirements
  } catch (err) {
    console.error('Failed to check requirements:', err)
    error.value = `Failed to check requirements: ${err.message}`
    
    // If it's a network error, show more details
    if (err.code === 'ERR_NETWORK' || err.message.includes('Network')) {
      error.value = 'Cannot connect to backend. Make sure the backend server is running on port 8000.'
    }
    
    requirements.value = []
    
    // Keep error visible for at least 3 seconds
    setTimeout(() => {
      isLoading.value = false
    }, 3000)
    return
  }
  
  isLoading.value = false
})
</script>