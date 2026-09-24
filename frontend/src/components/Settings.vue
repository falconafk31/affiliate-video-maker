<template>
  <div class="max-w-4xl mx-auto px-4 py-8 space-y-6 animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <h2 class="text-2xl font-bold text-slate-100">⚙️ Setting — Kelola AI Model</h2>
      <router-link to="/" class="text-retro-cyan text-sm underline hover:text-white transition-colors">
        ← Kembali ke Editor
      </router-link>
    </div>
    <p class="text-sm text-slate-400">
      Pisahkan <b class="text-slate-300">model teks</b> (untuk hook) dan <b class="text-slate-300">model suara</b> (untuk voiceover).
      Provider apa pun yang <b>OpenAI-compatible</b> bisa dipakai — isi <b>Base URL</b> (akhiran <code>/v1</code>), <b>API Key</b>, dan nama <b>model</b> sesuai provider (tidak hardcode).
      Konfigurasi disimpan di <b>database SQLite</b> server; API key selalu tampil <b>ter-mask</b>.
    </p>

    <!-- Endpoint yang digunakan -->
    <section class="retro-box p-4 space-y-2">
      <h3 class="text-sm font-bold text-brand-300">🔌 Endpoint yang digunakan</h3>
      <ul class="text-xs text-slate-400 space-y-1">
        <li>• <b class="text-slate-300">Model teks (hook)</b> — <code>POST {base_url}/chat/completions</code> (custom) atau <code>POST {{ pollinationsUrl }}/v1/chat/completions</code> (bawaan Pollinations)</li>
        <li>• <b class="text-slate-300">Model suara — standar</b> — <code>POST {base_url}/audio/speech</code> (OpenAI TTS, ElevenLabs, MiniMax, LocalAI, dll.)</li>
        <li>• <b class="text-slate-300">Model suara — chat audio</b> — <code>POST {base_url}/chat/completions</code> + <code>modalities: ["text","audio"]</code> (gpt-4o-audio style)</li>
        <li>• <b class="text-slate-300">Model suara — bawaan</b> — Edge-TTS (tanpa API key) / <code>POST {{ pollinationsUrl }}/v1/chat/completions</code> (GPT Audio Pollinations)</li>
        <li>• <b class="text-slate-300">🧪 Test Koneksi</b> — <code>POST /api/ai-config/test</code> → permintaan mini sungguhan ke endpoint provider di atas</li>
      </ul>
    </section>

    <!-- ── Model Teks (hook) ─────────────────────────────────────────────── -->
    <section class="retro-box p-4 space-y-3">
      <h3 class="text-sm font-bold text-brand-300">🧠 Model Teks (Generate Hook)</h3>
      <div class="space-y-1">
        <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input type="radio" :value="''" v-model="pendingActiveText" class="accent-brand-500" />
          Pollinations (bawaan) — <span class="text-slate-500">POST {{ pollinationsUrl }}/v1/chat/completions</span>
        </label>
        <div v-for="m in aiConfig.text_models" :key="m.id"
             class="flex items-center gap-2 text-xs text-slate-300 flex-wrap">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="radio" :value="m.id" v-model="pendingActiveText" class="accent-brand-500" />
            {{ m.label }} — <span class="text-slate-500">{{ m.model }}</span>
          </label>
          <span class="text-slate-500">POST {{ m.base_url }}/chat/completions</span>
          <span class="text-slate-500">{{ m.api_key || '(tanpa key)' }}</span>
          <button type="button" @click="deleteAiTextModel(m.id)" class="ml-auto text-red-400 hover:text-red-300">hapus</button>
        </div>
      </div>
      <button type="button" @click="activateAiTextModel"
              :disabled="pendingActiveText === aiConfig.active_text_model"
              class="btn-retro text-xs px-3 py-1.5 disabled:opacity-40">
        Aktifkan untuk Hook
      </button>

      <details class="border-2 border-slate-700 p-2">
        <summary class="text-xs text-slate-400 cursor-pointer">+ Tambah / edit model teks</summary>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
          <input v-model="textForm.label" placeholder="Label (mis. GPT-4o-mini)" class="input-retro text-xs" />
          <input v-model="textForm.model" placeholder="Model (mis. gpt-4o-mini)" class="input-retro text-xs" />
          <input v-model="textForm.base_url" placeholder="Base URL — https://api.openai.com/v1" class="input-retro text-xs sm:col-span-2" />
          <input v-model="textForm.api_key" type="password" placeholder="API Key (kosong = pertahankan lama)" class="input-retro text-xs sm:col-span-2" />
        </div>
        <p class="text-[11px] text-slate-500 mt-1">Endpoint: <code>POST {{ textForm.base_url || '{base_url}' }}/chat/completions</code></p>
        <div class="flex gap-2 mt-2">
          <button type="button" @click="testAiText" :disabled="testBusy === 'text'"
                  class="btn-retro text-xs px-3 py-1.5 disabled:opacity-40">
            {{ testBusy === 'text' ? 'Menguji…' : '🧪 Test Koneksi' }}
          </button>
          <button type="button" @click="saveAiTextModel" class="btn-retro text-xs px-3 py-1.5">Simpan Model Teks</button>
        </div>
      </details>
    </section>

    <!-- ── Model Suara (voiceover) ───────────────────────────────────────── -->
    <section class="retro-box p-4 space-y-3">
      <h3 class="text-sm font-bold text-brand-300">🎙️ Model Suara (Voiceover)</h3>
      <div class="space-y-1">
        <div v-for="m in aiConfig.voice_models" :key="m.id"
             class="flex items-center gap-2 text-xs text-slate-300 flex-wrap">
          <span>{{ m.label }} — <span class="text-slate-500">{{ m.model }} / {{ m.voice }}</span></span>
          <span class="text-slate-500">POST {{ m.base_url }}{{ m.endpoint_type === 'chat_audio' ? '/chat/completions' : '/audio/speech' }}</span>
          <span class="text-slate-500">{{ m.api_key || '(tanpa key)' }}</span>
          <button type="button" @click="deleteAiVoiceModel(m.id)" class="ml-auto text-red-400 hover:text-red-300">hapus</button>
        </div>
        <p v-if="!aiConfig.voice_models.length" class="text-xs text-slate-600">Belum ada model suara custom — tambah di bawah.</p>
      </div>

      <details class="border-2 border-slate-700 p-2">
        <summary class="text-xs text-slate-400 cursor-pointer">+ Tambah / edit model suara</summary>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
          <input v-model="voiceForm.label" placeholder="Label (mis. ElevenLabs Nova)" class="input-retro text-xs" />
          <input v-model="voiceForm.model" placeholder="Model (mis. tts-1)" class="input-retro text-xs" />
          <input v-model="voiceForm.base_url" placeholder="Base URL — https://api.openai.com/v1" class="input-retro text-xs" />
          <input v-model="voiceForm.voice" placeholder="Voice (mis. nova / alloy)" class="input-retro text-xs" />
          <select v-model="voiceForm.endpoint_type" class="input-retro text-xs">
            <option value="speech">Endpoint: /audio/speech (standar)</option>
            <option value="chat_audio">Endpoint: chat/completions + audio</option>
          </select>
          <input v-model="voiceForm.api_key" type="password" placeholder="API Key (kosong = pertahankan lama)" class="input-retro text-xs" />
          <input v-model.number="voiceForm.speed" type="number" min="0.25" max="4" step="0.05" placeholder="Speed (1.0)" class="input-retro text-xs" />
        </div>
        <p class="text-[11px] text-slate-500 mt-1">Endpoint: <code>POST {{ voiceForm.base_url || '{base_url}' }}{{ voiceForm.endpoint_type === 'chat_audio' ? '/chat/completions' : '/audio/speech' }}</code></p>
        <div class="flex gap-2 mt-2">
          <button type="button" @click="testAiVoice" :disabled="testBusy === 'voice'"
                  class="btn-retro text-xs px-3 py-1.5 disabled:opacity-40">
            {{ testBusy === 'voice' ? 'Menguji…' : '🧪 Test Koneksi' }}
          </button>
          <button type="button" @click="saveAiVoiceModel" class="btn-retro text-xs px-3 py-1.5">Simpan Model Suara</button>
        </div>
      </details>
    </section>

    <!-- ── Model bawaan (tidak hardcode) ─────────────────────────────────── -->
    <section class="retro-box p-4 space-y-3">
      <h3 class="text-sm font-bold text-brand-300">🔧 Model Bawaan — bisa diganti (tidak hardcode)</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div>
          <span class="block text-[11px] text-slate-400 mb-1">Model teks Pollinations (hook bawaan)</span>
          <div class="flex gap-1">
            <input v-model="defaultsForm.pollinations_text_model" placeholder="openai" class="input-retro text-xs flex-1" />
            <button type="button" @click="testAiDefault('pollinations_text')" :disabled="testBusy === 'pt'"
                    class="btn-retro text-[10px] px-2 disabled:opacity-40">{{ testBusy === 'pt' ? '…' : '🧪' }}</button>
          </div>
          <p class="text-[10px] text-slate-600 mt-0.5">POST {{ pollinationsUrl }}/v1/chat/completions</p>
        </div>
        <div>
          <span class="block text-[11px] text-slate-400 mb-1">Model suara Pollinations (GPT Audio)</span>
          <div class="flex gap-1">
            <input v-model="defaultsForm.pollinations_audio_model" placeholder="openai-audio" class="input-retro text-xs flex-1" />
            <button type="button" @click="testAiDefault('pollinations_audio')" :disabled="testBusy === 'pa'"
                    class="btn-retro text-[10px] px-2 disabled:opacity-40">{{ testBusy === 'pa' ? '…' : '🧪' }}</button>
          </div>
          <p class="text-[10px] text-slate-600 mt-0.5">POST {{ pollinationsUrl }}/v1/chat/completions (modalities audio)</p>
        </div>
        <div class="sm:col-span-2">
          <span class="block text-[11px] text-slate-400 mb-1">Voice Edge-TTS (mis. id-ID-ArdiNeural untuk laki-laki)</span>
          <input v-model="defaultsForm.edge_tts_voice" placeholder="id-ID-GadisNeural" class="input-retro text-xs" />
        </div>
      </div>
      <button type="button" @click="saveAiDefaults" class="btn-retro text-xs px-3 py-1.5">Simpan Model Bawaan</button>
    </section>

    <p v-if="aiStatus" class="text-sm" :class="aiStatusIsError ? 'text-red-400' : 'text-emerald-400'">{{ aiStatus }}</p>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const aiConfig = reactive({ text_models: [], voice_models: [], active_text_model: '', defaults: {} })
const pendingActiveText = ref('')
const textForm  = reactive({ id: null, label: '', model: '', base_url: '', api_key: '' })
const voiceForm = reactive({ id: null, label: '', model: '', base_url: '', api_key: '', voice: '', speed: 1.0, endpoint_type: 'speech' })
const defaultsForm = reactive({ pollinations_text_model: '', pollinations_audio_model: '', edge_tts_voice: '' })
const pollinationsUrl = ref('https://gen.pollinations.ai')
const testBusy        = ref('')
const aiStatus        = ref('')
const aiStatusIsError = ref(false)

function flashAiStatus(msg, isError = false) {
  aiStatus.value = msg
  aiStatusIsError.value = isError
  setTimeout(() => { aiStatus.value = '' }, 6000)
}

function flashTestResult(r) {
  flashAiStatus(r.data.ok
    ? `✅ Koneksi OK (${r.data.latency_ms} ms) — ${r.data.message}`
    : `❌ ${r.data.message}`, !r.data.ok)
}

async function fetchAiConfig() {
  try {
    const res = await axios.get(`${API_BASE_URL}/api/ai-config`)
    aiConfig.text_models       = res.data.text_models || []
    aiConfig.voice_models      = res.data.voice_models || []
    aiConfig.active_text_model = res.data.active_text_model || ''
    aiConfig.defaults          = res.data.defaults || {}
    pendingActiveText.value    = aiConfig.active_text_model
    pollinationsUrl.value      = res.data.pollinations_url || pollinationsUrl.value
    const d = aiConfig.defaults
    defaultsForm.pollinations_text_model  = d.pollinations_text_model  || 'openai'
    defaultsForm.pollinations_audio_model = d.pollinations_audio_model || 'openai-audio'
    defaultsForm.edge_tts_voice           = d.edge_tts_voice           || 'id-ID-GadisNeural'
  } catch { /* biarkan kosong bila gagal */ }
}

async function testAiText() {
  if (!textForm.base_url.trim() || !textForm.model.trim()) {
    flashAiStatus('Isi Base URL dan Model dulu sebelum test.', true); return
  }
  testBusy.value = 'text'
  try {
    flashTestResult(await axios.post(`${API_BASE_URL}/api/ai-config/test`, {
      kind: 'text', id: textForm.id, base_url: textForm.base_url,
      api_key: textForm.api_key, model: textForm.model,
    }))
  } catch (err) {
    flashAiStatus(err?.response?.data?.detail || 'Test koneksi gagal.', true)
  } finally { testBusy.value = '' }
}

async function testAiVoice() {
  if (!voiceForm.base_url.trim() || !voiceForm.model.trim() || !voiceForm.voice.trim()) {
    flashAiStatus('Isi Base URL, Model, dan Voice dulu sebelum test.', true); return
  }
  testBusy.value = 'voice'
  try {
    flashTestResult(await axios.post(`${API_BASE_URL}/api/ai-config/test`, {
      kind: voiceForm.endpoint_type === 'chat_audio' ? 'voice_chat_audio' : 'voice_speech',
      id: voiceForm.id, base_url: voiceForm.base_url,
      api_key: voiceForm.api_key, model: voiceForm.model,
      voice: voiceForm.voice,
    }))
  } catch (err) {
    flashAiStatus(err?.response?.data?.detail || 'Test koneksi gagal.', true)
  } finally { testBusy.value = '' }
}

async function testAiDefault(which) {
  testBusy.value = which === 'pollinations_text' ? 'pt' : 'pa'
  try {
    flashTestResult(await axios.post(`${API_BASE_URL}/api/ai-config/test`, {
      kind: which,
      model: which === 'pollinations_text'
        ? defaultsForm.pollinations_text_model : defaultsForm.pollinations_audio_model,
    }))
  } catch (err) {
    flashAiStatus(err?.response?.data?.detail || 'Test koneksi gagal.', true)
  } finally { testBusy.value = '' }
}

async function saveAiTextModel() {
  if (!textForm.label.trim() || !textForm.model.trim() || !textForm.base_url.trim()) {
    flashAiStatus('Label, Base URL, dan Model wajib diisi.', true); return
  }
  try {
    const payload = { ...textForm }
    if (!payload.id) delete payload.id
    await axios.post(`${API_BASE_URL}/api/ai-config/text-models`, payload)
    Object.assign(textForm, { id: null, label: '', model: '', base_url: '', api_key: '' })
    await fetchAiConfig()
    flashAiStatus('✅ Model teks tersimpan di database.')
  } catch (err) {
    flashAiStatus(err?.response?.data?.detail || 'Gagal menyimpan model teks.', true)
  }
}

async function deleteAiTextModel(id) {
  if (!confirm('Hapus model teks ini?')) return
  try {
    await axios.delete(`${API_BASE_URL}/api/ai-config/text-models/${id}`)
    await fetchAiConfig()
    flashAiStatus('Model teks dihapus.')
  } catch (err) {
    flashAiStatus(err?.response?.data?.detail || 'Gagal menghapus.', true)
  }
}

async function activateAiTextModel() {
  try {
    await axios.post(`${API_BASE_URL}/api/ai-config/active-text-model`, { id: pendingActiveText.value })
    await fetchAiConfig()
    flashAiStatus(pendingActiveText.value ? '✅ Model teks aktif untuk hook.' : '✅ Kembali ke Pollinations (bawaan).')
  } catch (err) {
    flashAiStatus(err?.response?.data?.detail || 'Gagal mengaktifkan model.', true)
  }
}

async function saveAiVoiceModel() {
  if (!voiceForm.label.trim() || !voiceForm.model.trim() || !voiceForm.base_url.trim() || !voiceForm.voice.trim()) {
    flashAiStatus('Label, Base URL, Model, dan Voice wajib diisi.', true); return
  }
  try {
    const payload = { ...voiceForm }
    if (!payload.id) delete payload.id
    await axios.post(`${API_BASE_URL}/api/ai-config/voice-models`, payload)
    Object.assign(voiceForm, { id: null, label: '', model: '', base_url: '', api_key: '', voice: '', speed: 1.0, endpoint_type: 'speech' })
    await fetchAiConfig()
    flashAiStatus('✅ Model suara tersimpan di database — muncul di dropdown Voice Model.')
  } catch (err) {
    flashAiStatus(err?.response?.data?.detail || 'Gagal menyimpan model suara.', true)
  }
}

async function deleteAiVoiceModel(id) {
  if (!confirm('Hapus model suara ini?')) return
  try {
    await axios.delete(`${API_BASE_URL}/api/ai-config/voice-models/${id}`)
    await fetchAiConfig()
    flashAiStatus('Model suara dihapus.')
  } catch (err) {
    flashAiStatus(err?.response?.data?.detail || 'Gagal menghapus.', true)
  }
}

async function saveAiDefaults() {
  try {
    await axios.post(`${API_BASE_URL}/api/ai-config/defaults`, {
      pollinations_text_model: defaultsForm.pollinations_text_model,
      pollinations_audio_model: defaultsForm.pollinations_audio_model,
      edge_tts_voice: defaultsForm.edge_tts_voice,
    })
    await fetchAiConfig()
    flashAiStatus('✅ Model bawaan tersimpan di database.')
  } catch (err) {
    flashAiStatus(err?.response?.data?.detail || 'Gagal menyimpan model bawaan.', true)
  }
}

onMounted(fetchAiConfig)
</script>
