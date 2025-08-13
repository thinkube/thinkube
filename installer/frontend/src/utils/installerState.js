/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Installer state management utilities
 * Provides persistent state tracking for the linear installation flow
 */

const STORAGE_KEY = 'thinkubeInstaller'

/**
 * Save a checkpoint for a completed step
 * @param {string} step - The step identifier
 * @param {object} data - Data to store for this step
 */
export const saveCheckpoint = (step, data) => {
  const state = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  state[step] = {
    completed: true,
    timestamp: new Date().toISOString(),
    data: data
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

/**
 * Get checkpoint data for a specific step
 * @param {string} step - The step identifier
 * @returns {object|null} The checkpoint data or null if not found
 */
export const getCheckpoint = (step) => {
  const state = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  return state[step] || null
}

/**
 * Check if a step has been completed
 * @param {string} step - The step identifier
 * @returns {boolean} True if the step has been completed
 */
export const isStepCompleted = (step) => {
  const checkpoint = getCheckpoint(step)
  return checkpoint?.completed === true
}

/**
 * Get all checkpoints
 * @returns {object} All stored checkpoints
 */
export const getAllCheckpoints = () => {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
}

/**
 * Clear all installer state and session data
 */
export const clearAllCheckpoints = () => {
  // Clear all installer-related localStorage items
  localStorage.removeItem(STORAGE_KEY)
  localStorage.removeItem('thinkube-config')
  localStorage.removeItem('thinkube-last-inventory')
  localStorage.removeItem('thinkube-session-backup')
  localStorage.removeItem('thinkubeDeployment')
  
  // Clear any other keys that might have been created
  const keysToRemove = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith('thinkube')) {
      keysToRemove.push(key)
    }
  }
  keysToRemove.forEach(key => localStorage.removeItem(key))
  
  // Clear all sessionStorage
  sessionStorage.clear()
  
  console.log('All installer state cleared')
}

/**
 * Get the last completed step
 * @returns {string|null} The name of the last completed step
 */
export const getLastCompletedStep = () => {
  const state = getAllCheckpoints()
  let lastStep = null
  let lastTime = null
  
  for (const [step, data] of Object.entries(state)) {
    if (data.completed && (!lastTime || new Date(data.timestamp) > new Date(lastTime))) {
      lastStep = step
      lastTime = data.timestamp
    }
  }
  
  return lastStep
}

/**
 * Check if installer has any saved state
 * @returns {boolean} True if there's saved state
 */
export const hasInstallerState = () => {
  const state = localStorage.getItem(STORAGE_KEY)
  return state && state !== '{}'
}

// Step identifiers for consistency
export const STEPS = {
  REQUIREMENTS: 'requirements',
  SUDO_PASSWORD: 'sudoPassword',
  INSTALLATION: 'installation',
  SERVER_DISCOVERY: 'serverDiscovery',
  SSH_SETUP: 'sshSetup',
  HARDWARE_DETECTION: 'hardwareDetection',
  VM_PLANNING: 'vmPlanning',
  ROLE_ASSIGNMENT: 'roleAssignment',
  CONFIGURATION: 'configuration',
  REVIEW: 'review',
  DEPLOY: 'deploy'
}