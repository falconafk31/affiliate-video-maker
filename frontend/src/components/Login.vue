<template>
  <div class="flex flex-col items-center justify-center py-20 px-4 animate-fade-in">
    <div class="retro-box w-full max-w-md p-8 space-y-6">
      <div class="text-center">
        <div class="w-16 h-16 mx-auto bg-retro-magenta text-black border-4 border-retro-cyan flex items-center justify-center shadow-[4px_4px_0_0_#00FFFF] mb-4">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
          </svg>
        </div>
        <h2 class="text-3xl font-retro font-bold text-retro-cyan uppercase">System Login</h2>
        <p class="text-slate-400 text-sm mt-2 font-mono">Restricted Access Area</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">Access Code / Password</label>
          <input 
            type="password" 
            v-model="password" 
            class="input-retro w-full text-lg tracking-widest text-center" 
            placeholder="••••••••"
            required
            :disabled="isLoading"
            autocomplete="current-password"
          />
        </div>

        <div v-if="errorMsg" class="bg-red-900/40 border border-red-500 p-3 text-sm text-red-300 text-center animate-fade-in">
          {{ errorMsg }}
        </div>

        <button 
          type="submit" 
          class="btn-retro w-full text-lg py-3"
          :disabled="isLoading || !password"
        >
          {{ isLoading ? 'AUTHENTICATING...' : 'ENTER' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:9000`
const router = useRouter()

const password = ref('')
const isLoading = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  if (!password.value) return
  isLoading.value = true
  errorMsg.value = ''

  try {
    const res = await axios.post(`${API_BASE}/api/login`, {
      password: password.value
    })
    
    // Save token
    if (res.data && res.data.access_token) {
      localStorage.setItem('token', res.data.access_token)
      // Configure axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`
      router.push('/')
    }
  } catch (err) {
    if (err.response && err.response.data && err.response.data.detail) {
      errorMsg.value = err.response.data.detail
    } else {
      errorMsg.value = 'Failed to connect to server.'
    }
  } finally {
    isLoading.value = false
    password.value = ''
  }
}
</script>
