<template>
  <div class="fixed top-4 right-4 z-[100] space-y-2 w-[min(22rem,90vw)] pointer-events-none">
    <transition-group name="toast">
      <div v-for="t in toasts" :key="t.id"
           class="pointer-events-auto border-2 px-3 py-2 text-sm shadow-lg flex items-start gap-2"
           :class="{
             'border-emerald-500 bg-emerald-950/95 text-emerald-200': t.type === 'success',
             'border-red-500 bg-red-950/95 text-red-200': t.type === 'error',
             'border-retro-cyan bg-slate-950/95 text-slate-100': t.type === 'info',
           }">
        <span>{{ t.type === 'success' ? '✅' : t.type === 'error' ? '❌' : 'ℹ️' }}</span>
        <span class="flex-1 leading-snug">{{ t.msg }}</span>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { toasts } from '../toast.js'
</script>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all .25s ease; }
.toast-enter-from { opacity: 0; transform: translateX(20px); }
.toast-leave-to { opacity: 0; transform: translateX(20px); }
</style>
