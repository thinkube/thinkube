/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

import axios from 'axios'

// Configure axios defaults
const isTauri = window.__TAURI__ !== undefined
const baseURL = isTauri || (window.location.protocol === 'http:' && window.location.hostname === 'localhost') 
  ? 'http://localhost:8000' 
  : ''

// Create axios instance with default config
const axiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor to ensure /api prefix
axiosInstance.interceptors.request.use(
  (config) => {
    // Ensure all requests have /api prefix
    if (config.url && !config.url.startsWith('/api')) {
      config.url = `/api${config.url}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ERR_NETWORK' || error.message.includes('Network')) {
      console.error('Network error: Make sure the backend server is running on port 8000')
    }
    return Promise.reject(error)
  }
)

export default axiosInstance

// 🤖 AI-generated