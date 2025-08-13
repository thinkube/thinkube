/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div class="flex items-center justify-center min-h-[60vh]">
    <div class="card w-full max-w-2xl bg-base-100 shadow-xl">
      <div class="card-body text-center">
        <div class="flex justify-center mb-6">
          <img src="/tk_full_logo.svg" alt="Thinkube" class="h-32" />
        </div>
        
        <h1 class="text-4xl font-bold mb-4 text-base-content">Welcome!</h1>
        <p class="text-lg text-base-content text-opacity-80 mb-8">
          Let's set up your AI-focused Kubernetes homelab platform
        </p>
        
        <div class="alert alert-info mb-8">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <span class="text-base-content">This installer will guide you through configuring and deploying Thinkube on your Ubuntu systems.</span>
        </div>

        <div class="prose prose-base max-w-none text-left mb-8">
          <ul class="space-y-3 list-none">
            <li class="flex items-center gap-3">
              <svg class="w-6 h-6 text-success flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span class="font-medium text-base-content">System requirements check</span>
            </li>
            <li class="flex items-center gap-3">
              <svg class="w-6 h-6 text-success flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span class="font-medium text-base-content">Cluster configuration</span>
            </li>
            <li class="flex items-center gap-3">
              <svg class="w-6 h-6 text-success flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span class="font-medium text-base-content">Automated deployment</span>
            </li>
          </ul>
        </div>

        <div class="card-actions justify-center">
          <button class="btn btn-primary btn-lg gap-2" @click="$router.push('/requirements')">
            Get Started
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { shouldSkipConfig, shouldCleanState } from '@/utils/configFlags'
import { deploymentState } from '@/utils/deploymentState'

const router = useRouter()

onMounted(async () => {
  // First check if we have a deployment in progress with a session backup
  const hasBackup = localStorage.getItem('thinkube-session-backup') !== null
  const deploymentStateData = await deploymentState.loadState()
  
  if (hasBackup && deploymentStateData && deploymentStateData.completedIds?.length > 0) {
    console.log('Found deployment in progress with session backup - redirecting to deploy page')
    router.push('/deploy')
    return
  }
  
  // Check if we should clean state
  if (await shouldCleanState()) {
    console.log('Cleaning installer state...')
    // Use the deployment state manager to clean properly
    await deploymentState.clearState()
    // Clear other localStorage items except inventory
    const keysToKeep = ['thinkube-last-inventory']
    const allKeys = Object.keys(localStorage)
    allKeys.forEach(key => {
      if (!keysToKeep.includes(key)) {
        localStorage.removeItem(key)
      }
    })
    // Clear all sessionStorage
    sessionStorage.clear()
  }
  
  // Check if we should skip configuration
  if (await shouldSkipConfig()) {
    console.log('Skip configuration mode detected')
    
    // Try to check if inventory.yaml exists via the backend
    // Retry a few times since backend might still be starting
    let retries = 5
    let inventoryFound = false
    
    while (retries > 0 && !inventoryFound) {
      try {
        const response = await fetch('http://localhost:8000/api/system/check-inventory')
        if (response.ok) {
          const data = await response.json()
          
          if (data.exists && data.content) {
            console.log('Found existing inventory.yaml, using it...')
            
            // Store the inventory for deployment
            sessionStorage.setItem('generatedInventory', data.content)
            
            // Set flag to indicate we're in skip-config mode
            sessionStorage.setItem('skipConfigMode', 'true')
            
            // Navigate directly to sudo password prompt
            router.push('/sudo-password')
            inventoryFound = true
          } else {
            console.error('No inventory.yaml found')
            alert('No previous inventory found. Please run through the configuration at least once.')
            break
          }
        } else {
          throw new Error(`Backend returned ${response.status}`)
        }
      } catch (error) {
        console.log(`Backend not ready yet (${retries} retries left)...`)
        retries--
        if (retries > 0) {
          // Wait 2 seconds before retry
          await new Promise(resolve => setTimeout(resolve, 2000))
        } else {
          console.error('Failed to check for existing inventory after retries:', error)
          alert('Failed to connect to backend. Please try again.')
        }
      }
    }
  }
})

// 🤖 AI-generated
</script>