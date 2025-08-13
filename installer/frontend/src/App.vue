/*
 * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
 * SPDX-License-Identifier: Apache-2.0
 */

<template>
  <div data-theme="thinkube" class="min-h-screen bg-base-100 flex flex-col">
    <!-- Header -->
    <InstallerHeader />

    <!-- Main Content -->
    <main class="flex-1 container mx-auto px-4 py-8">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Footer -->
    <footer class="footer footer-center p-4 bg-base-300 text-base-content">
      <div>
        <p class="text-sm">© 2025 Alejandro Martínez Corriá and the Thinkube contributors | Apache-2.0 License</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import InstallerHeader from '@/components/InstallerHeader.vue'

// Set default theme
document.documentElement.setAttribute('data-theme', 'thinkube')
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<!-- 🤖 AI-generated -->