/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

import { createRouter, createWebHistory } from 'vue-router'
import Welcome from '../views/Welcome.vue'
import Requirements from '../views/Requirements.vue'
import SudoPassword from '../views/SudoPassword.vue'
import Installation from '../views/Installation.vue'
import ServerDiscovery from '../views/ServerDiscovery.vue'
import SSHSetup from '../views/SSHSetup.vue'
import HardwareDetection from '../views/HardwareDetection.vue'
import RoleAssignment from '../views/RoleAssignment.vue'
import Configuration from '../views/Configuration.vue'
import NetworkConfiguration from '../views/NetworkConfiguration.vue'
import Review from '../views/Review.vue'
import Deploy from '../views/Deploy.vue'
import Complete from '../views/Complete.vue'

const routes = [
  {
    path: '/',
    name: 'welcome',
    component: Welcome
  },
  {
    path: '/requirements',
    name: 'requirements',
    component: Requirements
  },
  {
    path: '/sudo-password',
    name: 'sudo-password',
    component: SudoPassword
  },
  {
    path: '/installation',
    name: 'installation',
    component: Installation
  },
  {
    path: '/server-discovery',
    name: 'server-discovery',
    component: ServerDiscovery
  },
  {
    path: '/ssh-setup',
    name: 'ssh-setup',
    component: SSHSetup
  },
  {
    path: '/hardware-detection',
    name: 'hardware-detection',
    component: HardwareDetection
  },
  {
    path: '/role-assignment',
    name: 'role-assignment',
    component: RoleAssignment
  },
  {
    path: '/configuration',
    name: 'configuration',
    component: Configuration
  },
  {
    path: '/network-configuration',
    name: 'network-configuration',
    component: NetworkConfiguration
  },
  {
    path: '/review',
    name: 'review',
    component: Review
  },
  {
    path: '/deploy',
    name: 'deploy',
    component: Deploy
  },
  {
    path: '/complete',
    name: 'complete',
    component: Complete
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Check for ongoing deployment on every navigation
router.beforeEach(async (to, from, next) => {
  console.log('Router guard checking navigation to:', to.name)
  
  // Check for both old and new deployment state formats
  const newStateKey = 'thinkube-deployment-state-v2'
  const oldStateKey = 'thinkube-deployment-state'
  
  let deploymentState = localStorage.getItem(newStateKey)
  let isNewFormat = true
  
  if (!deploymentState) {
    deploymentState = localStorage.getItem(oldStateKey)
    isNewFormat = false
  }
  
  if (deploymentState) {
    const state = JSON.parse(deploymentState)
    
    if (isNewFormat) {
      console.log('Found deployment state (v2):', {
        hasProgress: state.completedIds?.length > 0,
        totalPlaybooks: state.allPlaybooks?.length,
        completed: state.completedIds?.length
      })
      
      // If we have a session backup, we're in restart recovery mode
      const hasBackup = localStorage.getItem('thinkube-session-backup') !== null
      
      // If deployment is in progress and we're not already going to deploy
      if ((state.completedIds?.length > 0 || hasBackup) && to.name !== 'deploy' && to.name !== 'welcome') {
        console.log('Redirecting to deployment page - deployment in progress')
        next({ name: 'deploy' })
        return
      }
    } else {
      // Old format
      console.log('Found deployment state (old format):', {
        awaitingRestart: state.awaitingRestart,
        currentPhase: state.currentPhase,
        queueLength: state.queue?.length
      })
      
      if (state.awaitingRestart && to.name !== 'deploy') {
        console.log('Redirecting to deployment page due to awaitingRestart flag')
        next({ name: 'deploy' })
        return
      }
    }
  } else {
    console.log('No deployment state found')
  }
  
  // Otherwise, proceed normally
  next()
})

export default router

// 🤖 AI-generated