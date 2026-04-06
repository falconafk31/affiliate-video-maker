<template>
  <div class="animate-fade-in space-y-8">

    <!-- Hero text -->
    <div class="text-center space-y-2">
      <h2 class="text-3xl sm:text-4xl font-bold text-white">
        Generate AI-Powered <span class="text-brand-400">Affiliate Videos</span>
      </h2>
      <p class="text-slate-400 max-w-xl mx-auto text-sm sm:text-base">
        Ketik nama produk, pilih platform, generate hook otomatis, lalu buat videonya!
      </p>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════════
         STEP 1 — Auto Hook Generator
    ════════════════════════════════════════════════════════════════════════ -->
    <div class="glass-card p-6 sm:p-8 space-y-5">
      <div class="flex items-center gap-2 mb-1">
        <span class="w-7 h-7 rounded-full bg-brand-600 text-white text-sm font-bold flex items-center justify-center flex-shrink-0">1</span>
        <h3 class="text-base font-semibold text-white">Generate Hook Otomatis</h3>
        <span class="ml-auto text-xs bg-brand-900/60 text-brand-300 border border-brand-700/50 rounded-full px-2 py-0.5">AI Generator</span>
      </div>

      <!-- Product name input -->
      <div>
        <label for="product-name" class="block text-sm font-medium text-slate-300 mb-2">
          Nama Produk <span class="text-brand-400">*</span>
        </label>
        <input
          id="product-name"
          v-model="productName"
          type="text"
          class="input-field"
          placeholder="Contoh: Serum Vitamin C Somethinc, Masker Wajah Aloe Vera, Celana Jogger Pria..."
          @keydown.enter.prevent="generateHook"
        />
      </div>

      <!-- Hook type selector (tabs) -->
      <div>
        <label class="block text-sm font-medium text-slate-300 mb-2">Platform Hook</label>
        <div class="grid grid-cols-2 gap-3">
          <!-- TikTok -->
          <button
            type="button"
            id="hook-tiktok"
            class="hook-tab"
            :class="hookType === 'tiktok' ? 'hook-tab-active' : 'hook-tab-inactive'"
            @click="hookType = 'tiktok'"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.16 8.16 0 004.77 1.52V6.76a4.85 4.85 0 01-1-.07z"/>
            </svg>
            <span class="font-semibold">TikTok Hook</span>
            <span class="text-xs opacity-70">Viral &amp; Impulsif</span>
          </button>
          <!-- Shopee -->
          <button
            type="button"
            id="hook-shopee"
            class="hook-tab"
            :class="hookType === 'shopee' ? 'hook-tab-active' : 'hook-tab-inactive'"
            @click="hookType = 'shopee'"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
            </svg>
            <span class="font-semibold">Shopee Hook</span>
            <span class="text-xs opacity-70">Promo &amp; Diskon</span>
          </button>
        </div>
      </div>

      <!-- Hook variation selector -->
      <div>
        <label class="block text-sm font-medium text-slate-300 mb-2">Variasi Hook</label>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="(v, i) in hookVariations[hookType]"
            :key="i"
            type="button"
            class="text-xs py-2 px-3 rounded-lg border transition-all duration-150 text-left"
            :class="selectedVariation === i
              ? 'border-brand-500 bg-brand-900/40 text-brand-300'
              : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
            @click="selectedVariation = i"
          >
            {{ v.label }}
          </button>
        </div>
      </div>

      <!-- Generate button -->
      <button
        type="button"
        id="generate-hook-btn"
        class="btn-primary w-full"
        :disabled="!productName.trim() || isGenerating"
        @click="generateHook"
      >
        <svg v-if="isGenerating" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
        </svg>
        {{ isGenerating ? '🤖 AI sedang menulis hook...' : `✨ Generate Hook ${hookType === 'tiktok' ? 'TikTok' : 'Shopee'} dengan AI` }}
      </button>

      <!-- Success badge -->
      <div v-if="hookGenerated && !isGenerating" class="flex items-center gap-2 text-xs text-green-400 animate-fade-in">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
        </svg>
        Hook AI berhasil digenerate! Skrip sudah terisi di bawah — edit sesukamu.
      </div>

      <!-- Hook error -->
      <div v-if="hookError" class="flex items-start gap-2 bg-red-900/30 border border-red-700/50 rounded-xl p-3">
        <svg class="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <p class="text-red-300 text-xs">{{ hookError }}</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════════
         STEP 2 — Video & Voiceover Form
    ════════════════════════════════════════════════════════════════════════ -->
    <form @submit.prevent="handleSubmit" class="glass-card p-6 sm:p-8 space-y-6">
      <div class="flex items-center justify-between gap-2 mb-1">
        <div class="flex items-center gap-2">
          <span class="w-7 h-7 rounded-full bg-brand-600 text-white text-sm font-bold flex items-center justify-center flex-shrink-0">2</span>
          <h3 class="text-base font-semibold text-white">Pilih Mode &amp; Proses</h3>
        </div>
        
        <!-- Mode Switcher -->
        <div class="flex bg-slate-800/80 p-1 rounded-lg border border-slate-700">
          <button 
            type="button" 
            class="px-3 py-1.5 rounded-md text-xs font-medium transition-all"
            :class="mode === 'video' ? 'bg-brand-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'"
            @click="mode = 'video'"
          >
            Video + Audio
          </button>
          <button 
            type="button" 
            class="px-3 py-1.5 rounded-md text-xs font-medium transition-all"
            :class="mode === 'audio' ? 'bg-brand-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'"
            @click="mode = 'audio'"
          >
            Hanya Audio (MP3)
          </button>
        </div>
      </div>

      <!-- Drag & Drop Video Upload — Only if mode is 'video' -->
      <div v-if="mode === 'video'" class="animate-fade-in">
        <label class="block text-sm font-medium text-slate-300 mb-2">
          Video File <span class="text-brand-400">*</span>
        </label>
        <div
          id="drop-zone"
          class="relative border-2 border-dashed rounded-xl transition-all duration-200 cursor-pointer"
          :class="[
            isDragging
              ? 'border-brand-400 bg-brand-900/20'
              : 'border-slate-600 hover:border-brand-500 bg-slate-800/30',
          ]"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
          @click="$refs.fileInput.click()"
        >
          <input
            ref="fileInput"
            id="file-input"
            type="file"
            accept=".mp4,video/mp4"
            class="hidden"
            @change="onFileChange"
          />
          <div class="py-10 px-6 flex flex-col items-center gap-3 text-center">
            <template v-if="!selectedFile">
              <div class="w-14 h-14 rounded-2xl bg-slate-700 flex items-center justify-center">
                <svg class="w-7 h-7 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <div>
                <p class="text-slate-300 font-medium">Drag &amp; drop file .mp4 kamu di sini</p>
                <p class="text-slate-500 text-sm">atau klik untuk pilih file</p>
              </div>
            </template>
            <template v-else>
              <div class="w-14 h-14 rounded-2xl bg-green-900/40 flex items-center justify-center">
                <svg class="w-7 h-7 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p class="text-slate-200 font-semibold truncate max-w-xs">{{ selectedFile.name }}</p>
                <p class="text-slate-500 text-sm">{{ formatSize(selectedFile.size) }}</p>
              </div>
              <button type="button" class="text-xs text-red-400 hover:text-red-300 transition-colors" @click.stop="clearFile">
                Hapus
              </button>
            </template>
          </div>
        </div>
        <p v-if="errors.video" class="mt-2 text-sm text-red-400">{{ errors.video }}</p>
      </div>

      <!-- Voiceover Script -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label for="prompt" class="block text-sm font-medium text-slate-300">
            Skrip Voiceover <span class="text-brand-400">*</span>
          </label>
          <span class="text-xs text-slate-500">{{ prompt.length }} karakter</span>
        </div>
        <textarea
          id="prompt"
          v-model="prompt"
          rows="5"
          class="input-field resize-none"
          placeholder="Skrip akan otomatis terisi setelah generate hook di atas, atau tulis sendiri di sini..."
        ></textarea>
        <p v-if="errors.prompt" class="mt-2 text-sm text-red-400">{{ errors.prompt }}</p>
      </div>

      <!-- Voice Model -->
      <div>
        <label for="voice-model" class="block text-sm font-medium text-slate-300 mb-2">Voice Model</label>
        <select id="voice-model" v-model="voiceModel" class="input-field">
          <option v-for="v in voiceOptions" :key="v.value" :value="v.value">{{ v.label }}</option>
        </select>
      </div>

      <!-- Duration Match Mode -->
      <div>
        <label class="block text-sm font-medium text-slate-300 mb-2">
          Sinkronisasi Durasi
          <span class="ml-2 text-xs text-slate-500">Video &amp; Audio</span>
        </label>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="m in durationModes"
            :key="m.value"
            type="button"
            class="flex flex-col items-center gap-1 py-3 px-2 rounded-xl border-2 transition-all duration-150 text-center"
            :class="durationMode === m.value
              ? 'border-brand-500 bg-brand-900/40 text-brand-300'
              : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
            @click="durationMode = m.value"
          >
            <span class="text-lg">{{ m.icon }}</span>
            <span class="text-xs font-semibold leading-tight">{{ m.label }}</span>
            <span class="text-xs opacity-60 leading-tight">{{ m.desc }}</span>
          </button>
        </div>
      </div>

      <!-- Submit -->
      <button id="submit-btn" type="submit" class="btn-primary w-full text-base py-4" :disabled="isLoading">
        <svg v-if="isLoading" class="w-5 h-5 animate-spin-slow" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        {{ isLoading ? loadingMessage : (mode === 'video' ? '🎬 Buat Video Sekarang' : '🎙️ Generate Audio MP3') }}
      </button>

      <!-- Error -->
      <div v-if="serverError" class="flex items-start gap-3 bg-red-900/30 border border-red-700/50 rounded-xl p-4">
        <svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="text-red-300 text-sm">{{ serverError }}</p>
      </div>
    </form>

    <!-- ═══════════════════════════════════════════════════════════════════════
         Result Card
    ════════════════════════════════════════════════════════════════════════ -->
    <div v-if="outputVideoUrl || outputAudioUrl" id="result-section" class="glass-card p-6 sm:p-8 space-y-5 animate-fade-in">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
          <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-white">
          {{ outputVideoUrl ? 'Video kamu sudah siap! 🎉' : 'Audio kamu sudah siap! 🎙️' }}
        </h3>
      </div>

      <!-- Video Result -->
      <video v-if="outputVideoUrl" id="output-video" :src="outputVideoUrl" controls class="w-full rounded-xl bg-black max-h-[480px]"></video>
      
      <!-- Audio Result -->
      <div v-if="outputAudioUrl && !outputVideoUrl" class="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 flex flex-col items-center gap-4">
        <div class="w-16 h-16 rounded-full bg-brand-500/20 flex items-center justify-center text-brand-400 animate-pulse">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </div>
        <audio controls :src="outputAudioUrl" class="w-full"></audio>
        <p class="text-slate-400 text-xs">Voiceover generated successfully.</p>
      </div>

      <a id="download-btn" :href="outputVideoUrl || outputAudioUrl" :download="outputVideoUrl ? 'affiliate_video.mp4' : 'voiceover.mp3'" class="btn-primary w-full text-center">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Download {{ outputVideoUrl ? 'Video' : 'Audio' }}
      </a>

      <button id="reset-btn" type="button" class="btn-secondary w-full" @click="reset">
        Buat {{ outputVideoUrl ? 'Video' : 'Audio' }} Lainnya
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import axios from 'axios'

// ── Config ────────────────────────────────────────────────────────────────────
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:9000`

// ── State ─────────────────────────────────────────────────────────────────────
const fileInput      = ref(null)
const selectedFile   = ref(null)
const prompt         = ref('')
const voiceModel     = ref('whisper')
const logId          = ref('')
const isDragging     = ref(false)
const isLoading      = ref(false)
const loadingMessage = ref('Memproses…')
const serverError    = ref('')
const outputVideoUrl = ref('')
const outputAudioUrl = ref('')
const durationMode   = ref('auto')
const mode           = ref('video') // 'video' | 'audio'

// Hook generator state
const productName      = ref('')
const hookType         = ref('tiktok')     // 'tiktok' | 'shopee'
const selectedVariation = ref(0)
const hookGenerated    = ref(false)
const isGenerating     = ref(false)
const hookError        = ref('')

const errors = reactive({ video: '', prompt: '' })

// ── Duration Modes ────────────────────────────────────────────────────────────
const durationModes = [
  {
    value: 'auto',
    icon: '🧠',
    label: 'Auto (Smart)',
    desc: 'Loop jika audio > video, trim jika video > audio',
  },
  {
    value: 'loop_video',
    icon: '🔁',
    label: 'Loop Video',
    desc: 'Video diulang agar sesuai panjang audio',
  },
  {
    value: 'trim_audio',
    icon: '✂️',
    label: 'Trim Audio',
    desc: 'Audio dipotong sesuai panjang video asli',
  },
]

// ── Voice Options ─────────────────────────────────────────────────────────────
const voiceOptions = [
  { value: 'whisper', label: 'Whisper — Laki-laki/Perempuan, Natural Berbisik' },
]

// ── Hook Variations (keys must match backend HOOK_STYLE_PROMPTS) ─────────────
const hookVariations = {
  tiktok: [
    { key: 'viral',  label: '🔥 Viral Impulsif' },
    { key: 'shock',  label: '😱 Shock & Reveal' },
    { key: 'story',  label: '💬 Cerita Personal' },
    { key: 'fomo',   label: '⚡ FOMO Urgency'   },
    { key: 'v2_problem',   label: '🚀 V2: Problem' },
    { key: 'v2_personal',  label: '🚀 V2: Personal' },
    { key: 'v2_education', label: '🚀 V2: Edukasi' },
    { key: 'v2_contra',    label: '🚀 V2: Pro-Kontra' },
    { key: 'v2_visual',    label: '🚀 V2: Visual Shock' },
  ],
  shopee: [
    { key: 'flash',   label: '🛒 Flash Sale'    },
    { key: 'review',  label: '⭐ Review Jujur'  },
    { key: 'bundle',  label: '🎁 Bundle Deal'   },
    { key: 'premium', label: '💎 Premium Value' },
    { key: 'v2_problem',   label: '🚀 V2: Problem' },
    { key: 'v2_personal',  label: '🚀 V2: Personal' },
    { key: 'v2_education', label: '🚀 V2: Edukasi' },
    { key: 'v2_contra',    label: '🚀 V2: Pro-Kontra' },
    { key: 'v2_visual',    label: '🚀 V2: Visual Shock' },
  ],
}

// ── Generate Hook via AI ─────────────────────────────────────────────────────
async function generateHook() {
  const name = productName.value.trim()
  if (!name) return

  isGenerating.value = true
  hookGenerated.value = false
  hookError.value = ''

  const variations = hookVariations[hookType.value]
  const varItem    = variations[selectedVariation.value] ?? variations[0]

  try {
    const formData = new FormData()
    formData.append('product_name', name)
    formData.append('hook_type',    hookType.value)
    formData.append('variation',    varItem.key)

    const response = await axios.post(`${API_BASE_URL}/api/generate-hook`, formData)
    prompt.value        = response.data.script
    logId.value         = response.data.log_id || ''
    hookGenerated.value = true

    setTimeout(() => {
      document.getElementById('prompt')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 100)

  } catch (err) {
    let msg = 'Gagal generate hook AI. Coba lagi.'
    if (err.response) {
      const status = err.response.status
      const detail = err.response.data?.detail
      const detailStr = typeof detail === 'string' ? detail : JSON.stringify(detail)
      msg = `Gagal (${status}): ${detailStr || err.message}`
    } else if (err.code === 'ECONNABORTED') {
      msg = 'Timeout. Server AI sedang sibuk, coba lagi.'
    } else {
      msg = `Koneksi gagal: ${err.message}`
    }
    hookError.value = msg
  } finally {
    isGenerating.value = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function validateFile(file) {
  if (!file) { errors.video = 'Pilih file video terlebih dahulu.'; return false }
  if (!file.name.toLowerCase().endsWith('.mp4')) {
    errors.video = 'Hanya file .mp4 yang diterima.'
    return false
  }
  if (file.size > 500 * 1024 * 1024) {
    errors.video = 'Ukuran video maksimal 500MB.'
    return false
  }
  errors.video = ''
  return true
}

function validateForm() {
  let valid = mode.value === 'video' ? validateFile(selectedFile.value) : true
  if (!prompt.value.trim()) {
    errors.prompt = 'Skrip voiceover tidak boleh kosong. Generate hook dulu atau tulis sendiri.'
    valid = false
  } else {
    errors.prompt = ''
  }
  return valid
}

// ── File events ───────────────────────────────────────────────────────────────
function onFileChange(e) {
  const file = e.target.files?.[0]
  if (file) applyFile(file)
}
function onDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer.files?.[0]
  if (file) applyFile(file)
}
function applyFile(file) {
  selectedFile.value = file
  validateFile(file)
  outputVideoUrl.value = ''
  serverError.value = ''
}
function clearFile() {
  selectedFile.value = null
  errors.video = ''
  if (fileInput.value) fileInput.value.value = ''
}

// ── Submit ────────────────────────────────────────────────────────────────────
async function handleSubmit() {
  if (!validateForm()) return

  isLoading.value = true
  serverError.value = ''
  outputVideoUrl.value = ''

  const messages = [
    'Sedang membuat AI voiceover…',
    'Menggabungkan audio dengan video…',
    'Hampir selesai, rendering video akhir…',
  ]
  let msgIdx = 0
  loadingMessage.value = 'Mempersiapakan upload...'
  let msgInterval = null

  const startMessages = () => {
    loadingMessage.value = messages[msgIdx]
    msgInterval = setInterval(() => {
      msgIdx = (msgIdx + 1) % messages.length
      loadingMessage.value = messages[msgIdx]
    }, 4000)
  }

  try {
    const formData = new FormData()
    if (mode.value === 'video') formData.append('video', selectedFile.value)
    formData.append('prompt_text', prompt.value.trim())
    formData.append('voice_model', voiceModel.value)
    if (mode.value === 'video') formData.append('duration_mode', durationMode.value)
    if (logId.value) formData.append('log_id', logId.value)

    const endpoint = mode.value === 'video' ? '/api/process-video' : '/api/generate-audio'
    const response = await axios.post(`${API_BASE_URL}${endpoint}`, formData, {
      timeout: 300_000,
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (mode.value === 'audio') {
          loadingMessage.value = 'Sedang membuat AI voiceover…'
          return
        }
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        if (percentCompleted < 100) {
          loadingMessage.value = `Mengunggah video: ${percentCompleted}%...`
        } else if (percentCompleted === 100 && !msgInterval) {
          startMessages()
        }
      }
    })

    const data = response.data
    
    if (mode.value === 'video') {
      outputVideoUrl.value = API_BASE_URL + data.video_url
    } else {
      outputAudioUrl.value = API_BASE_URL + data.audio_url
    }

    setTimeout(() => {
      document.getElementById('result-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 100)

  } catch (err) {
    if (err.response) {
      try {
        const text = await err.response.data.text()
        const json = JSON.parse(text)
        serverError.value = json.detail || 'Terjadi kesalahan pada server.'
      } catch {
        serverError.value = `Server error (${err.response.status}). Coba lagi.`
      }
    } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
      serverError.value = 'Request timeout. Video mungkin terlalu panjang atau server AI sedang sibuk.'
    } else {
      serverError.value = 'Tidak bisa terhubung ke backend. Pastikan server berjalan di ' + API_BASE_URL
    }
  } finally {
    clearInterval(msgInterval)
    isLoading.value = false
    loadingMessage.value = 'Memproses…'
  }
}

// ── Reset ─────────────────────────────────────────────────────────────────────
function reset() {
  clearFile()
  prompt.value        = ''
  productName.value   = ''
  voiceModel.value    = 'whisper'
  durationMode.value  = 'auto'
  hookGenerated.value = false
  outputVideoUrl.value = ''
  outputAudioUrl.value = ''
  serverError.value   = ''
  errors.video        = ''
  errors.prompt       = ''
}
</script>
