<template>
  <div class="animate-fade-in space-y-8">

    <!-- Hero -->
    <div class="text-center space-y-2">
      <h2 class="text-3xl sm:text-4xl font-bold text-slate-100">
        📂 Video <span class="text-retro-cyan">Library</span>
      </h2>
      <p class="text-slate-400 max-w-xl mx-auto text-sm sm:text-base">
        Simpan video raw sekali, pakai berkali-kali. Tidak perlu upload ulang setiap sesi.
      </p>
    </div>

    <!-- Upload Card -->
    <div class="retro-box p-6 sm:p-8 space-y-5">
      <div class="flex items-center gap-2">
        <span class="w-7 h-7 rounded-none bg-retro-magenta text-black text-slate-100 text-sm font-bold flex items-center justify-center flex-shrink-0">+</span>
        <h3 class="text-base font-semibold text-slate-100">Upload Video ke Library</h3>
      </div>

      <div
        id="library-drop-zone"
        class="relative border-2 border-dashed rounded-none transition-all duration-200 cursor-pointer"
        :class="isDragging
          ? 'border-brand-400 bg-brand-900/20'
          : 'border-slate-600 hover:border-brand-500 bg-slate-800/30'"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
        @click="$refs.libFileInput.click()"
      >
        <input
          ref="libFileInput"
          type="file"
          accept=".mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo"
          class="hidden"
          @change="onFileChange"
        />
        <div class="py-8 px-6 flex flex-col items-center gap-3 text-center">
          <template v-if="!uploadFile">
            <div class="w-14 h-14 rounded-none bg-slate-700 flex items-center justify-center">
              <svg class="w-7 h-7 text-retro-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p class="text-slate-300 font-medium">Drag & drop video (.mp4, .mov, .avi)</p>
              <p class="text-slate-500 text-sm">atau klik untuk pilih file</p>
            </div>
          </template>
          <template v-else>
            <div class="w-14 h-14 rounded-none bg-green-900/40 flex items-center justify-center">
              <svg class="w-7 h-7 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <p class="text-slate-200 font-semibold truncate max-w-xs">{{ uploadFile.name }}</p>
              <p class="text-slate-500 text-sm">{{ formatSize(uploadFile.size) }}</p>
            </div>
            <button type="button" class="text-xs text-red-400 hover:text-red-300 transition-colors"
              @click.stop="clearUpload">Hapus</button>
          </template>
        </div>
      </div>

      <!-- Display Name input -->
      <div v-if="uploadFile">
        <label class="block text-sm font-medium text-slate-300 mb-2">Nama Tampilan (opsional)</label>
        <input
          v-model="displayName"
          type="text"
          class="input-retro"
          :placeholder="uploadFile.name"
        />
      </div>

      <!-- Upload Button -->
      <button
        type="button"
        id="library-upload-btn"
        class="btn-retro w-full"
        :disabled="!uploadFile || isUploading"
        @click="uploadToLibrary"
      >
        <svg v-if="isUploading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        {{ isUploading ? `Mengupload... ${uploadPercent}%` : '📤 Simpan ke Library' }}
      </button>

      <!-- Upload error -->
      <div v-if="uploadError" class="flex items-start gap-2 bg-red-900/30 border border-red-700/50 rounded-none p-3">
        <p class="text-red-300 text-xs">{{ uploadError }}</p>
      </div>
    </div>

    <!-- Library Grid -->
    <div class="retro-box p-6 sm:p-8 space-y-5">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <h3 class="text-base font-semibold text-slate-100">Video Tersimpan</h3>
          <span class="text-xs bg-slate-700 text-slate-300 rounded-none px-2 py-0.5">{{ videos.length }}</span>
        </div>
        <button @click="fetchLibrary" :disabled="isLoading"
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 rounded-none transition-all">
          <svg class="w-3.5 h-3.5" :class="{ 'animate-spin': isLoading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          Refresh
        </button>
      </div>

      <!-- Error -->
      <div v-if="fetchError" class="text-red-300 text-sm bg-red-900/20 border border-red-700/40 rounded-none p-3">
        ⚠️ {{ fetchError }}
      </div>

      <!-- Empty State -->
      <div v-if="!isLoading && videos.length === 0 && !fetchError" class="py-16 text-center">
        <p class="text-5xl mb-4">🎬</p>
        <p class="text-slate-400 font-medium">Library masih kosong</p>
        <p class="text-slate-500 text-sm mt-1">Upload video raw pertamamu di atas!</p>
      </div>

      <!-- Grid -->
      <div v-if="videos.length > 0" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <div
          v-for="vid in videos"
          :key="vid.id"
          class="group relative bg-slate-800/60 rounded-none border border-slate-700 overflow-hidden hover:border-brand-500/60 transition-all duration-200"
        >
          <!-- Video thumbnail / preview -->
          <div class="aspect-[9/16] bg-slate-900 flex items-center justify-center relative overflow-hidden">
            <video
              :src="API_BASE + vid.video_url"
              class="w-full h-full object-cover cursor-pointer"
              muted
              playsinline
              preload="metadata"
              @mouseenter="e => { if(window.innerWidth > 768) e.target.play() }"
              @mouseleave="e => { if(window.innerWidth > 768) { e.target.pause(); e.target.currentTime = 0; } }"
              @click="e => e.target.paused ? e.target.play() : e.target.pause()"
            ></video>
            <div class="absolute inset-0 bg-black/30 group-hover:bg-black/10 transition-all flex items-center justify-center pointer-events-none">
              <svg class="w-10 h-10 text-slate-100/70 group-hover:text-slate-100/0 transition-all drop-shadow-md" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </div>
          </div>

          <!-- Info -->
          <div class="p-3 space-y-2">
            <p class="text-slate-100 text-xs font-semibold leading-tight line-clamp-2">{{ vid.original_name }}</p>
            <div class="flex items-center justify-between text-[10px] text-slate-500">
              <span>{{ formatSize(vid.size) }}</span>
              <span>{{ formatAge(vid.uploaded_at) }}</span>
            </div>

            <!-- Actions -->
            <div class="flex gap-1.5">
              <button
                id="library-use-btn"
                @click="useVideo(vid)"
                class="flex-1 text-[10px] font-bold py-1.5 rounded-none bg-retro-magenta text-black hover:bg-retro-cyan text-black text-slate-100 transition-all text-center"
              >
                ✅ Pakai
              </button>
              <button
                @click="confirmDelete(vid)"
                class="p-1.5 rounded-none bg-slate-700 hover:bg-red-800 text-slate-300 hover:text-slate-100 transition-all"
                title="Hapus"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Retention notice -->
      <p v-if="videos.length > 0" class="text-xs text-slate-600 text-center">
        📅 Video library disimpan selama {{ retentionDays }} hari sejak tanggal upload.
      </p>
    </div>

    <!-- Toast -->
    <div v-if="toast.show"
      class="fixed bottom-6 right-6 px-4 py-2.5 rounded-none shadow-xl text-sm font-medium z-50 animate-fade-in"
      :class="toast.type === 'success' ? 'bg-green-700 text-slate-100' : 'bg-red-700 text-slate-100'">
      {{ toast.msg }}
    </div>

    <!-- Delete Modal -->
    <Teleport to="body">
      <div v-if="deleteModal.show"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80"
        @click.self="deleteModal.show = false">
        <div class="retro-box w-full max-w-sm p-6 space-y-4 animate-fade-in shadow-2xl">
          <h3 class="text-retro-cyan font-bold font-retro text-2xl uppercase">⚠️ Konfirmasi</h3>
          <p class="text-slate-300 text-sm">Hapus <span class="font-bold text-retro-magenta">{{ deleteModal.vid?.original_name }}</span> dari library? Aksi ini tidak bisa dibatalkan.</p>
          <div class="flex gap-3 pt-2">
            <button @click="executeDelete" class="flex-1 btn-retro-secondary">
              Ya, Hapus
            </button>
            <button @click="deleteModal.show = false" class="flex-1 btn-retro">
              Batal
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const API_BASE  = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:9000`
const router    = useRouter()

// Upload state
const libFileInput  = ref(null)
const uploadFile    = ref(null)
const displayName   = ref('')
const isDragging    = ref(false)
const isUploading   = ref(false)
const uploadPercent = ref(0)
const uploadError   = ref('')

// Library state
const videos     = ref([])
const isLoading  = ref(false)
const fetchError = ref('')
const retentionDays = ref(30)

const toast = reactive({ show: false, msg: '', type: 'success' })

// ── File Handling ─────────────────────────────────────────────────────────────
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
  uploadFile.value = file
  displayName.value = ''
  uploadError.value = ''
}
function clearUpload() {
  uploadFile.value = null
  displayName.value = ''
  uploadError.value = ''
  if (libFileInput.value) libFileInput.value.value = ''
}

// ── Upload ────────────────────────────────────────────────────────────────────
async function uploadToLibrary() {
  if (!uploadFile.value) return
  isUploading.value = true
  uploadPercent.value = 0
  uploadError.value = ''
  try {
    const form = new FormData()
    form.append('video', uploadFile.value)
    if (displayName.value.trim()) form.append('display_name', displayName.value.trim())

    const res = await axios.post(`${API_BASE}/api/library/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: p => {
        uploadPercent.value = Math.round((p.loaded * 100) / p.total)
      },
      timeout: 300000,
    })
    videos.value.unshift(res.data.video)
    clearUpload()
    showToast('✅ Video berhasil disimpan ke library!', 'success')
  } catch (err) {
    uploadError.value = err.response?.data?.detail || 'Gagal upload. Coba lagi.'
  } finally {
    isUploading.value = false
  }
}

// ── Fetch Library ─────────────────────────────────────────────────────────────
async function fetchLibrary() {
  isLoading.value = true
  fetchError.value = ''
  try {
    const res = await axios.get(`${API_BASE}/api/library`)
    videos.value = res.data.videos
  } catch {
    fetchError.value = 'Gagal memuat library. Pastikan backend berjalan.'
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchLibrary)

// ── Use Video ─────────────────────────────────────────────────────────────────
function useVideo(vid) {
  // Store in sessionStorage for VideoEditor to pick up
  sessionStorage.setItem('library_video', JSON.stringify({
    id: vid.id,
    name: vid.original_name,
    size: vid.size,
    url: API_BASE + vid.video_url,
  }))
  router.push('/')
  showToast('Video dipilih! Lanjutkan di halaman Editor.', 'success')
}

// ── Delete ────────────────────────────────────────────────────────────────────
const deleteModal = reactive({ show: false, vid: null })

function confirmDelete(vid) {
  deleteModal.vid = vid
  deleteModal.show = true
}

async function executeDelete() {
  const vid = deleteModal.vid
  if (!vid) return
  try {
    await axios.delete(`${API_BASE}/api/library/${vid.id}`)
    videos.value = videos.value.filter(v => v.id !== vid.id)
    showToast('🗑️ Video dihapus dari library.', 'success')
  } catch (err) {
    showToast(err.response?.data?.detail || 'Gagal menghapus video.', 'error')
  } finally {
    deleteModal.show = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatAge(ts) {
  const diff = Math.floor((Date.now() / 1000) - ts)
  if (diff < 60) return 'baru saja'
  if (diff < 3600) return Math.floor(diff / 60) + ' menit lalu'
  if (diff < 86400) return Math.floor(diff / 3600) + ' jam lalu'
  return Math.floor(diff / 86400) + ' hari lalu'
}

function showToast(msg, type = 'success') {
  toast.msg = msg
  toast.type = type
  toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}
</script>
