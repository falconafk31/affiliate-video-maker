<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-8">
    <div class="max-w-6xl mx-auto space-y-6">

      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-white">📋 Hook Generation Log</h1>
          <p class="text-slate-400 text-sm mt-1">Riwayat semua prompt yang di-generate oleh AI</p>
        </div>
        <div class="flex gap-2 flex-wrap">
          <button @click="refreshLogs" :disabled="loading"
            class="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-all">
            <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            Refresh
          </button>
          <a :href="`${apiBase}/api/logs/download`" target="_blank"
            class="flex items-center gap-2 px-4 py-2 rounded-xl bg-green-700 hover:bg-green-600 text-sm font-medium transition-all">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            Download CSV
          </a>
          <button @click="confirmClear"
            class="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-800 hover:bg-red-700 text-sm font-medium transition-all">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
            Reset Log
          </button>
        </div>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="glass-card p-4 text-center">
          <p class="text-3xl font-bold text-brand-400">{{ totalLogs }}</p>
          <p class="text-xs text-slate-400 mt-1">Total Log</p>
        </div>
        <div class="glass-card p-4 text-center">
          <p class="text-3xl font-bold text-purple-400">{{ tiktokCount }}</p>
          <p class="text-xs text-slate-400 mt-1">TikTok</p>
        </div>
        <div class="glass-card p-4 text-center">
          <p class="text-3xl font-bold text-orange-400">{{ shopeeCount }}</p>
          <p class="text-xs text-slate-400 mt-1">Shopee</p>
        </div>
        <div class="glass-card p-4 text-center">
          <p class="text-3xl font-bold text-green-400">{{ uniqueProducts }}</p>
          <p class="text-xs text-slate-400 mt-1">Produk Unik</p>
        </div>
      </div>

      <!-- Tab Switcher -->
      <div class="flex bg-slate-800/60 p-1 rounded-xl border border-slate-700 w-fit">
        <button
          @click="activeTab = 'table'"
          class="px-5 py-2 rounded-lg text-sm font-medium transition-all"
          :class="activeTab === 'table' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-white'"
        >
          📋 Tabel Log
        </button>
        <button
          @click="activeTab = 'analytics'; renderCharts()"
          class="px-5 py-2 rounded-lg text-sm font-medium transition-all"
          :class="activeTab === 'analytics' ? 'bg-brand-600 text-white shadow' : 'text-slate-400 hover:text-white'"
        >
          📈 Analytics
        </button>
      </div>

      <!-- Error -->
      <div v-if="error" class="glass-card p-4 border-red-700/60 text-red-300 text-sm">
        ⚠️ {{ error }}
      </div>

      <!-- ════════════════════ TAB: TABEL LOG ════════════════════ -->
      <template v-if="activeTab === 'table'">
        <!-- Filter + Search -->
        <div class="flex flex-col sm:flex-row gap-3">
          <input
            v-model="search"
            type="text"
            placeholder="Cari produk atau skrip..."
            class="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
          <select v-model="filterPlatform"
            class="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-brand-500">
            <option value="">Semua Platform</option>
            <option value="tiktok">TikTok</option>
            <option value="shopee">Shopee</option>
          </select>
        </div>

        <!-- Empty State -->
        <div v-if="!loading && filteredLogs.length === 0" class="glass-card p-12 text-center">
          <p class="text-4xl mb-3">📭</p>
          <p class="text-slate-400">Belum ada log yang tersimpan.</p>
          <p class="text-slate-500 text-sm mt-1">Generate hook pertama kamu di halaman utama!</p>
        </div>

        <!-- Table -->
        <div v-if="filteredLogs.length > 0" class="glass-card overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
                  <th class="px-4 py-3 text-left w-12">No</th>
                  <th class="px-4 py-3 text-left w-40">Waktu</th>
                  <th class="px-4 py-3 text-left w-24">Platform</th>
                  <th class="px-4 py-3 text-left w-28">Variasi</th>
                  <th class="px-4 py-3 text-left w-36">Produk</th>
                  <th class="px-4 py-3 text-left">Skrip Output</th>
                  <th class="px-4 py-3 text-center w-40">Media</th>
                  <th class="px-4 py-3 w-20"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-800">
                <tr v-for="log in paginatedLogs" :key="log.no"
                  class="hover:bg-slate-800/40 transition-colors group">
                  <td class="px-4 py-3 text-slate-500 font-mono">{{ log.no }}</td>
                  <td class="px-4 py-3 text-slate-400 whitespace-nowrap font-mono text-xs">{{ log.time }}</td>
                  <td class="px-4 py-3">
                    <span :class="log.platform === 'tiktok'
                      ? 'bg-purple-900/50 text-purple-300 border border-purple-700/40'
                      : 'bg-orange-900/50 text-orange-300 border border-orange-700/40'"
                      class="px-2 py-0.5 rounded-full text-xs font-medium">
                      {{ log.platform === 'tiktok' ? '🎵 TikTok' : '🛒 Shopee' }}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-slate-300 text-xs capitalize">{{ log.variation }}</td>
                  <td class="px-4 py-3 text-white font-medium">{{ log.input_product }}</td>
                  <td class="px-4 py-3 text-slate-300 text-xs leading-relaxed max-w-sm">
                    <p class="line-clamp-2 cursor-pointer hover:text-white transition-colors"
                       @click="openScriptModal(log.output_script, log.input_product)">
                      {{ log.output_script }}
                    </p>
                    <button class="mt-1 text-brand-400 hover:text-brand-300 text-[10px] font-medium"
                      @click="openScriptModal(log.output_script, log.input_product)">
                      Lihat selengkapnya →
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <div class="flex flex-col gap-1.5 items-center justify-center">
                      <a v-if="log.video_url" :href="apiBase + log.video_url" target="_blank"
                         class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-green-700 hover:bg-green-600 text-[10px] font-medium text-white transition-colors w-full justify-center"
                         title="Tonton / Download Video">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        Video
                      </a>
                      <a v-if="log.audio_url" :href="apiBase + log.audio_url" target="_blank"
                         class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-[10px] font-medium text-white transition-colors w-full justify-center"
                         title="Dengarkan / Download MP3">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                        </svg>
                        Audio
                      </a>
                      <span v-if="!log.video_url && !log.audio_url" class="text-slate-600 text-xs italic">-</span>
                    </div>
                  </td>
                  <td class="px-4 py-3">
                    <button @click="copyScript(log.output_script)"
                      class="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 transition-all"
                      title="Copy skrip">
                      <svg class="w-3.5 h-3.5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                      </svg>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          <div v-if="totalPages > 1" class="flex items-center justify-between px-4 py-3 border-t border-slate-800">
            <p class="text-xs text-slate-500">
              Menampilkan {{ (currentPage - 1) * perPage + 1 }}–{{ Math.min(currentPage * perPage, filteredLogs.length) }}
              dari {{ filteredLogs.length }} log
            </p>
            <div class="flex gap-1">
              <button @click="currentPage--" :disabled="currentPage === 1"
                class="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-xs disabled:opacity-40 transition-all">
                ← Prev
              </button>
              <span class="px-3 py-1.5 text-xs text-slate-400">{{ currentPage }} / {{ totalPages }}</span>
              <button @click="currentPage++" :disabled="currentPage === totalPages"
                class="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-xs disabled:opacity-40 transition-all">
                Next →
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- ════════════════════ TAB: ANALYTICS ════════════════════ -->
      <template v-if="activeTab === 'analytics'">
        <div v-if="logs.length === 0" class="glass-card p-12 text-center">
          <p class="text-4xl mb-3">📊</p>
          <p class="text-slate-400">Belum ada data untuk dianalisa.</p>
          <p class="text-slate-500 text-sm mt-1">Generate beberapa hook terlebih dahulu!</p>
        </div>

        <div v-else class="space-y-6">
          <!-- Row 1: Bar + Donut -->
          <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <!-- Bar Chart: Top Products -->
            <div class="glass-card p-5 lg:col-span-3">
              <h3 class="text-sm font-semibold text-white mb-4">🏆 Top 10 Produk Paling Sering Di-Generate</h3>
              <div class="relative h-64">
                <canvas id="chart-top-products"></canvas>
              </div>
            </div>
            <!-- Donut Chart: Variation Distribution -->
            <div class="glass-card p-5 lg:col-span-2">
              <h3 class="text-sm font-semibold text-white mb-4">🎯 Distribusi Variasi Hook</h3>
              <div class="relative h-64">
                <canvas id="chart-variations"></canvas>
              </div>
            </div>
          </div>

          <!-- Row 2: Line Chart -->
          <div class="glass-card p-5">
            <h3 class="text-sm font-semibold text-white mb-4">📅 Aktivitas Generate (30 Hari Terakhir)</h3>
            <div class="relative h-56">
              <canvas id="chart-daily-activity"></canvas>
            </div>
          </div>

          <!-- Row 3: Platform Breakdown -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="glass-card p-5">
              <h3 class="text-sm font-semibold text-white mb-3">🎵 TikTok — Variasi Terpopuler</h3>
              <div class="space-y-2">
                <div v-for="item in tiktokVariationRanking" :key="item.key"
                  class="flex items-center gap-3">
                  <span class="text-xs text-slate-400 w-24 truncate capitalize">{{ item.key }}</span>
                  <div class="flex-1 bg-slate-700 rounded-full h-2">
                    <div class="h-2 rounded-full bg-purple-500 transition-all duration-700"
                      :style="{ width: item.pct + '%' }"></div>
                  </div>
                  <span class="text-xs text-slate-300 w-8 text-right">{{ item.count }}</span>
                </div>
              </div>
            </div>
            <div class="glass-card p-5">
              <h3 class="text-sm font-semibold text-white mb-3">🛒 Shopee — Variasi Terpopuler</h3>
              <div class="space-y-2">
                <div v-for="item in shopeeVariationRanking" :key="item.key"
                  class="flex items-center gap-3">
                  <span class="text-xs text-slate-400 w-24 truncate capitalize">{{ item.key }}</span>
                  <div class="flex-1 bg-slate-700 rounded-full h-2">
                    <div class="h-2 rounded-full bg-orange-500 transition-all duration-700"
                      :style="{ width: item.pct + '%' }"></div>
                  </div>
                  <span class="text-xs text-slate-300 w-8 text-right">{{ item.count }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

    </div>
  </div>

  <!-- ════════ Script Modal ════════ -->
  <Teleport to="body">
    <div v-if="scriptModal.open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      @click.self="scriptModal.open = false">
      <div class="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 space-y-4 animate-fade-in shadow-2xl">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="text-white font-semibold">📝 Skrip Lengkap</h3>
            <p class="text-slate-400 text-xs mt-0.5">{{ scriptModal.product }}</p>
          </div>
          <button @click="scriptModal.open = false"
            class="text-slate-400 hover:text-white transition-colors p-1">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 leading-relaxed max-h-64 overflow-y-auto">
          {{ scriptModal.script }}
        </div>
        <div class="flex gap-2">
          <button @click="copyScript(scriptModal.script)"
            class="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-sm font-medium transition-all">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
            Copy Skrip
          </button>
          <button @click="scriptModal.open = false"
            class="px-4 py-2 rounded-xl bg-slate-700 hover:bg-slate-600 text-sm transition-all">
            Tutup
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Copy toast -->
  <div v-if="copied"
    class="fixed bottom-6 right-6 bg-green-700 text-white text-sm px-4 py-2 rounded-xl shadow-lg animate-fade-in z-50">
    ✅ Skrip disalin ke clipboard!
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, reactive } from 'vue'
import axios from 'axios'
import {
  Chart,
  BarElement, BarController,
  ArcElement, DoughnutController,
  LineElement, PointElement, LineController,
  CategoryScale, LinearScale,
  Tooltip, Legend
} from 'chart.js'

Chart.register(
  BarElement, BarController,
  ArcElement, DoughnutController,
  LineElement, PointElement, LineController,
  CategoryScale, LinearScale,
  Tooltip, Legend
)

const API_BASE = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:9000`

const logs           = ref([])
const loading        = ref(false)
const error          = ref('')
const search         = ref('')
const filterPlatform = ref('')
const currentPage    = ref(1)
const perPage        = 15
const copied         = ref(false)
const apiBase        = API_BASE
const activeTab      = ref('table')

// Script Modal
const scriptModal = reactive({ open: false, script: '', product: '' })

// Chart instances (keep refs to destroy before re-render)
let chartTopProducts = null
let chartVariations  = null
let chartDaily       = null

// ── Fetch logs ─────────────────────────────────────────────────────────────────
async function refreshLogs() {
  loading.value = true
  error.value   = ''
  try {
    const res = await axios.get(`${API_BASE}/api/logs`)
    logs.value = [...res.data.logs].reverse()
    if (activeTab.value === 'analytics') {
      await nextTick()
      renderCharts()
    }
  } catch (err) {
    error.value = 'Gagal memuat log. Pastikan backend berjalan.'
  } finally {
    loading.value = false
  }
}

onMounted(refreshLogs)

// ── Stats ─────────────────────────────────────────────────────────────────────
const totalLogs      = computed(() => logs.value.length)
const tiktokCount    = computed(() => logs.value.filter(l => l.platform === 'tiktok').length)
const shopeeCount    = computed(() => logs.value.filter(l => l.platform === 'shopee').length)
const uniqueProducts = computed(() => new Set(logs.value.map(l => l.input_product)).size)

// ── Filter ────────────────────────────────────────────────────────────────────
const filteredLogs = computed(() => {
  let result = logs.value
  if (filterPlatform.value) result = result.filter(l => l.platform === filterPlatform.value)
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    result = result.filter(l =>
      l.input_product.toLowerCase().includes(q) ||
      l.output_script.toLowerCase().includes(q)
    )
  }
  currentPage.value = 1
  return result
})

// ── Pagination ────────────────────────────────────────────────────────────────
const totalPages    = computed(() => Math.ceil(filteredLogs.value.length / perPage))
const paginatedLogs = computed(() => {
  const start = (currentPage.value - 1) * perPage
  return filteredLogs.value.slice(start, start + perPage)
})

// ── Analytics Computed ─────────────────────────────────────────────────────────
const topProducts = computed(() => {
  const counts = {}
  logs.value.forEach(l => {
    counts[l.input_product] = (counts[l.input_product] || 0) + 1
  })
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
})

const variationDistribution = computed(() => {
  const counts = {}
  logs.value.forEach(l => {
    counts[l.variation] = (counts[l.variation] || 0) + 1
  })
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})

const dailyActivity = computed(() => {
  const today = new Date()
  const days = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    days.push(d.toISOString().slice(0, 10))
  }
  const counts = {}
  logs.value.forEach(l => {
    const day = (l.time || '').slice(0, 10)
    if (day) counts[day] = (counts[day] || 0) + 1
  })
  return { labels: days.map(d => d.slice(5)), data: days.map(d => counts[d] || 0) }
})

const tiktokVariationRanking = computed(() => {
  const counts = {}
  logs.value.filter(l => l.platform === 'tiktok').forEach(l => {
    counts[l.variation] = (counts[l.variation] || 0) + 1
  })
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([key, count]) => ({ key, count, pct: Math.round(count / total * 100) }))
})

const shopeeVariationRanking = computed(() => {
  const counts = {}
  logs.value.filter(l => l.platform === 'shopee').forEach(l => {
    counts[l.variation] = (counts[l.variation] || 0) + 1
  })
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([key, count]) => ({ key, count, pct: Math.round(count / total * 100) }))
})

// ── Chart Rendering ───────────────────────────────────────────────────────────
const CHART_COLORS = [
  '#38bdf8','#818cf8','#34d399','#fb923c','#f472b6',
  '#a78bfa','#facc15','#4ade80','#60a5fa','#f87171'
]

async function renderCharts() {
  if (logs.value.length === 0) return
  await nextTick()

  // ── Bar Chart: Top Products ─────────────────────────────────
  const ctxBar = document.getElementById('chart-top-products')
  if (ctxBar) {
    if (chartTopProducts) chartTopProducts.destroy()
    chartTopProducts = new Chart(ctxBar, {
      type: 'bar',
      data: {
        labels: topProducts.value.map(([k]) => k.length > 18 ? k.slice(0, 18) + '…' : k),
        datasets: [{
          label: 'Jumlah Generate',
          data: topProducts.value.map(([, v]) => v),
          backgroundColor: CHART_COLORS,
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => ` ${ctx.raw} generate` } }
        },
        scales: {
          x: { ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { display: false } },
          y: { ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { color: '#1e293b' } }
        }
      }
    })
  }

  // ── Donut Chart: Variations ─────────────────────────────────
  const ctxDoughnut = document.getElementById('chart-variations')
  if (ctxDoughnut) {
    if (chartVariations) chartVariations.destroy()
    chartVariations = new Chart(ctxDoughnut, {
      type: 'doughnut',
      data: {
        labels: variationDistribution.value.map(([k]) => k),
        datasets: [{
          data: variationDistribution.value.map(([, v]) => v),
          backgroundColor: CHART_COLORS,
          borderWidth: 2,
          borderColor: '#0f172a',
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#94a3b8', font: { size: 10 }, padding: 10, boxWidth: 12 }
          }
        },
        cutout: '65%',
      }
    })
  }

  // ── Line Chart: Daily Activity ──────────────────────────────
  const ctxLine = document.getElementById('chart-daily-activity')
  if (ctxLine) {
    if (chartDaily) chartDaily.destroy()
    const da = dailyActivity.value
    chartDaily = new Chart(ctxLine, {
      type: 'line',
      data: {
        labels: da.labels,
        datasets: [{
          label: 'Generate',
          data: da.data,
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56,189,248,0.08)',
          pointBackgroundColor: '#38bdf8',
          pointRadius: 3,
          tension: 0.4,
          fill: true,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => ` ${ctx.raw} generate` } }
        },
        scales: {
          x: {
            ticks: { color: '#94a3b8', font: { size: 10 }, maxTicksLimit: 10 },
            grid: { color: '#1e293b' }
          },
          y: {
            ticks: { color: '#94a3b8', font: { size: 11 }, stepSize: 1 },
            grid: { color: '#1e293b' },
            beginAtZero: true,
          }
        }
      }
    })
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────
function openScriptModal(script, product) {
  scriptModal.script = script
  scriptModal.product = product
  scriptModal.open = true
}

async function copyScript(script) {
  await navigator.clipboard.writeText(script)
  copied.value = true
  if (scriptModal.open) scriptModal.open = false
  setTimeout(() => { copied.value = false }, 2500)
}

async function confirmClear() {
  if (!confirm('Reset semua log? Aksi ini tidak bisa dibatalkan.')) return
  try {
    await axios.delete(`${API_BASE}/api/logs/clear`)
    logs.value = []
  } catch {
    error.value = 'Gagal reset log.'
  }
}
</script>
