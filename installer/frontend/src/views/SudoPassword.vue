/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-3xl font-bold mb-6">Administrator Access</h1>
    
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title mb-4">Sudo Password Required</h2>
        
        <div class="alert alert-info mb-6">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <div>
            <p>The installer needs administrator access for SSH configuration and server setup.</p>
            <p class="text-sm mt-1">Your password will be used to run commands with sudo and will not be stored.</p>
          </div>
        </div>
        
        <form @submit.prevent="verifyAndContinue">
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">Current User</span>
            </label>
            <input 
              type="text" 
              :value="currentUser" 
              class="input input-md"
              disabled
            />
          </div>
          
          <div class="form-control mb-4">
            <label class="label">
              <span class="label-text">Sudo Password</span>
              <span class="label-text-alt">Your password for {{ currentUser }}</span>
            </label>
            <div class="relative">
              <input 
                v-model="sudoPassword" 
                :type="showSudoPassword ? 'text' : 'password'" 
                placeholder="Enter your password" 
                class="input input-bordered w-full pr-12"
                :class="{ 'input-error': error }"
                required
                autofocus
                @input="error = ''"
              />
              <button 
                type="button"
                class="absolute inset-y-0 right-0 flex items-center pr-3"
                @click="showSudoPassword = !showSudoPassword"
              >
                <svg v-if="showSudoPassword" class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"></path>
                </svg>
                <svg v-else class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                </svg>
              </button>
            </div>
            <label v-if="error" class="label">
              <span class="label-text-alt text-error">{{ error }}</span>
            </label>
          </div>
          
          <div class="form-control mb-6">
            <button 
              type="submit"
              class="btn btn-primary"
              :disabled="!sudoPassword || verifying"
            >
              <span v-if="verifying" class="loading loading-spinner"></span>
              <span v-else>Verify & Continue</span>
            </button>
          </div>
          
          <div class="text-sm text-base-content text-opacity-70">
            <p class="mb-2">The installer will use sudo to:</p>
            <ul class="list-disc list-inside space-y-1 ml-2">
              <li>Configure SSH access between servers</li>
              <li>Install missing tools (if needed)</li>
              <li>Configure your environment</li>
              <li>Set up system services</li>
            </ul>
          </div>
        </form>
      </div>
    </div>
    
    <div class="flex justify-between mt-6">
      <button class="btn btn-ghost gap-2" @click="$router.push('/requirements')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
        Back
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

const currentUser = ref('')
const sudoPassword = ref('')
const verifying = ref(false)
const error = ref('')
const showSudoPassword = ref(false)

const verifyAndContinue = async () => {
  verifying.value = true
  error.value = ''
  
  try {
    console.log('Verifying sudo password...')
    // Verify the sudo password
    const response = await axios.post('/api/verify-sudo', { 
      password: sudoPassword.value 
    })
    
    console.log('Verification response:', response.data)
    
    if (response.data.valid) {
      // Store the password temporarily for SSH setup and other operations
      sessionStorage.setItem('sudoPassword', sudoPassword.value)
      // Store the system username for inventory generation
      sessionStorage.setItem('systemUsername', currentUser.value)
      
      // Check if tools need installation
      console.log('Checking if tools need installation...')
      const requirementsResponse = await axios.get('/api/check-requirements')
      const toolRequirements = requirementsResponse.data.requirements.filter(req => req.category === 'tools')
      const hasToolsToInstall = toolRequirements.some(req => req.status === 'missing')
      
      // Check if we're in skip-config mode
      const skipConfigMode = sessionStorage.getItem('skipConfigMode') === 'true'
      
      if (hasToolsToInstall) {
        // Tools need installation - start the installation process
        console.log('Starting setup with password...')
        const setupResponse = await axios.post('/api/run-setup', {
          sudo_password: sudoPassword.value
        })
        console.log('Setup response:', setupResponse.data)
        
        if (setupResponse.data.status === 'exists' || skipConfigMode) {
          // If tools were already installed or we're in skip-config mode,
          // check where to go next
          if (skipConfigMode) {
            console.log('Skip-config mode: proceeding directly to deployment after tools')
            router.push('/deploy')
          } else {
            router.push('/server-discovery')
          }
        } else {
          // Redirect to installation progress page
          router.push('/installation')
        }
      } else if (skipConfigMode) {
        // All tools already installed and in skip-config mode
        console.log('Skip-config mode: tools already installed, proceeding directly to deployment')
        router.push('/deploy')
      } else {
        // All tools are already installed, proceed normally
        console.log('All tools already installed, proceeding to server discovery...')
        router.push('/server-discovery')
      }
    } else {
      error.value = 'Invalid password. Please try again.'
      sudoPassword.value = ''
    }
  } catch (err) {
    console.error('Failed to verify password:', err)
    
    // Handle specific sudo password errors
    if (err.response && err.response.status === 400 && err.response.data.detail?.includes('sudo password')) {
      error.value = 'Invalid sudo password. Please try again.'
      sudoPassword.value = ''
    } else {
      error.value = 'Failed to verify password: ' + (err.response?.data?.detail || err.message)
    }
  } finally {
    verifying.value = false
  }
}

onMounted(async () => {
  // Clear any stored passwords from previous sessions
  sessionStorage.removeItem('sudoPassword')
  
  // Get current user from backend
  try {
    const response = await axios.get('/api/current-user')
    currentUser.value = response.data.username
  } catch (error) {
    console.error('Failed to get current user:', error)
    currentUser.value = 'ubuntu'
  }
})
</script>

<style scoped>
.input:focus {
  outline-offset: 0;
}
</style>