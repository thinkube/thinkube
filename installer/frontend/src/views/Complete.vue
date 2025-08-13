/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-4xl mx-auto">
    <!-- Error state if no data -->
    <div v-if="!dataLoaded" class="text-center mb-8">
      <div class="inline-flex items-center justify-center w-24 h-24 bg-error bg-opacity-20 rounded-full mb-6">
        <svg class="w-16 h-16 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
      </div>
      <h1 class="text-4xl font-bold mb-4">Configuration Not Found</h1>
      <p class="text-xl text-base-content text-opacity-70 mb-8">
        The deployment configuration could not be loaded. Please ensure you've completed all previous steps.
      </p>
      <button class="btn btn-primary" @click="$router.push('/')">
        Start Over
      </button>
    </div>
    
    <!-- Success state with data -->
    <div v-else>
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-24 h-24 bg-success bg-opacity-20 rounded-full mb-6">
          <svg class="w-16 h-16 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
        </div>
        <h1 class="text-4xl font-bold mb-4">Cluster Deployment Complete!</h1>
        <p class="text-xl text-base-content text-opacity-70">
          Your thinkube platform has been successfully deployed and is ready for AI workloads.
        </p>
      </div>

    <!-- Access Information -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Access Your Platform</h2>
        
        <div class="space-y-4">
          <div class="flex items-start gap-4">
            <div class="flex-shrink-0 w-12 h-12 bg-primary bg-opacity-20 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path>
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="font-semibold mb-1">Thinkube Control</h3>
              <a :href="`https://control.${domainName}`" target="_blank" class="link link-primary">
                https://control.{{ domainName }}
              </a>
              <p class="text-sm text-base-content text-opacity-70 mt-1">
                Central management dashboard for your Thinkube platform
              </p>
            </div>
          </div>
          
          <div class="flex items-start gap-4">
            <div class="flex-shrink-0 w-12 h-12 bg-primary bg-opacity-20 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path>
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="font-semibold mb-1">Argo Workflows</h3>
              <a :href="`https://argo.${domainName}`" target="_blank" class="link link-primary">
                https://argo.{{ domainName }}
              </a>
              <p class="text-sm text-base-content text-opacity-70 mt-1">
                Run and manage AI workflows and CI/CD pipelines
              </p>
            </div>
          </div>
          
          <div class="flex items-start gap-4">
            <div class="flex-shrink-0 w-12 h-12 bg-primary bg-opacity-20 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="font-semibold mb-1">Code Server</h3>
              <a :href="`https://code.${domainName}`" target="_blank" class="link link-primary">
                https://code.{{ domainName }}
              </a>
              <p class="text-sm text-base-content text-opacity-70 mt-1">
                VS Code in the browser with CI/CD integration
              </p>
            </div>
          </div>
          
          <div class="flex items-start gap-4">
            <div class="flex-shrink-0 w-12 h-12 bg-primary bg-opacity-20 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="font-semibold mb-1">SSH Access</h3>
              <code class="text-sm bg-base-200 px-2 py-1 rounded">
                ssh {{ systemUsername }}@{{ controlPlaneIP }}
              </code>
              <p class="text-sm text-base-content text-opacity-70 mt-1">
                Direct access to control plane node
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Admin Credentials -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Administrator Credentials</h2>
        
        <div class="alert alert-warning mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>Save these credentials securely. They will not be shown again.</span>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="label">
              <span class="label-text font-semibold">Admin Username</span>
            </label>
            <div class="input  flex items-center justify-between">
              <span>{{ adminUsername }}</span>
              <button class="btn btn-ghost btn-xs" @click="copyToClipboard(adminUsername)">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                </svg>
              </button>
            </div>
          </div>
          
          <div>
            <label class="label">
              <span class="label-text font-semibold">Admin Password</span>
            </label>
            <div class="input input-bordered flex items-center justify-between">
              <span class="font-mono">{{ showPassword ? adminPassword : '••••••••' }}</span>
              <div class="flex gap-1">
                <button class="btn btn-ghost btn-xs" @click="showPassword = !showPassword">
                  <svg v-if="showPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"></path>
                  </svg>
                  <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                  </svg>
                </button>
                <button class="btn btn-ghost btn-xs" @click="copyToClipboard(adminPassword)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Next Steps -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">Next Steps</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a href="https://docs.thinkube.org" target="_blank" class="btn btn-outline gap-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
            </svg>
            Read Documentation
          </a>
          
          <a href="https://github.com/thinkube/thinkube" target="_blank" class="btn btn-outline gap-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
            </svg>
            Explore Examples
          </a>
          
          <button class="btn btn-outline gap-2" @click="downloadLogs">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"></path>
            </svg>
            Download Logs
          </button>
        </div>
      </div>
    </div>

      <!-- Actions -->
      <div class="text-center">
        <button class="btn btn-ghost" @click="closeInstaller">
          Close Installer
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

// State
const domainName = ref('')
const adminUsername = ref('')
const adminPassword = ref('')
const systemUsername = ref('')
const controlPlaneIP = ref('')
const showPassword = ref(false)
const isElectron = computed(() => !!window.electronAPI)
const dataLoaded = ref(false)

// Load configuration
onMounted(() => {
  // Get configuration from sessionStorage first (current session data)
  const networkConfig = JSON.parse(sessionStorage.getItem('networkConfiguration') || '{}')
  const currentUser = sessionStorage.getItem('currentUser')
  const sudoPassword = sessionStorage.getItem('sudoPassword')
  
  // Get domain name from network configuration
  domainName.value = networkConfig.domainName || 'thinkube.local'
  
  // Admin username is always tkadmin
  adminUsername.value = 'tkadmin'
  
  // Admin password is the sudo password
  adminPassword.value = sudoPassword || 'ChangeMeNow123!'
  
  // System username
  systemUsername.value = currentUser || 'thinkube'
  
  // Get control plane IP from cluster nodes
  const clusterNodes = JSON.parse(sessionStorage.getItem('clusterNodes') || '[]')
  const controlNode = clusterNodes.find(n => n.role === 'control-plane')
  
  if (controlNode) {
    controlPlaneIP.value = controlNode.ip
  } else {
    // Fallback to first discovered server
    const servers = JSON.parse(sessionStorage.getItem('discoveredServers') || '[]')
    if (servers.length > 0) {
      controlPlaneIP.value = servers[0].ip_address || servers[0].ip
    }
  }
  
  // Check if we have the minimum required data
  if (domainName.value && adminUsername.value && controlPlaneIP.value) {
    dataLoaded.value = true
  }
})

// Methods
const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    // Could add a toast notification here
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

const downloadLogs = async () => {
  try {
    window.location.href = '/api/logs/download'
  } catch (error) {
    console.error('Failed to download logs:', error)
  }
}

const closeInstaller = () => {
  if (window.electronAPI) {
    window.electronAPI.close()
  } else {
    // For web version, just show a message
    alert('Installation complete! You can now close this browser tab.')
  }
}
</script>

<style scoped>
.link {
  @apply underline-offset-2;
}
</style>