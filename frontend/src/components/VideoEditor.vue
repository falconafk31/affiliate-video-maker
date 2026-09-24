<template>
  <div class="animate-fade-in space-y-8">

    <!-- Hero text -->
    <div class="text-center space-y-2">
      <h2 class="text-3xl sm:text-4xl font-bold text-slate-100">
        Generate AI-Powered <span class="text-retro-cyan">Affiliate Videos</span>
      </h2>
      <p class="text-slate-400 max-w-xl mx-auto text-sm sm:text-base">
        Ketik nama produk, pilih platform, generate hook otomatis, lalu buat videonya!
      </p>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════════
         STEP 1 — Auto Hook Generator
    ════════════════════════════════════════════════════════════════════════ -->
    <div class="retro-box p-6 sm:p-8 space-y-5">
      <div class="flex items-center gap-2 mb-1">
        <span class="w-7 h-7 rounded-none bg-retro-magenta text-black text-slate-100 text-sm font-bold flex items-center justify-center flex-shrink-0">1</span>
        <h3 class="text-base font-semibold text-slate-100">Generate Hook Otomatis</h3>
        <span class="ml-auto text-xs bg-brand-900/60 text-brand-300 border border-brand-700/50 rounded-none px-2 py-0.5">AI Generator</span>
      </div>

      <!-- Product name input -->
      <div>
        <label for="product-name" class="block text-sm font-medium text-slate-300 mb-2">
          Nama Produk <span class="text-retro-cyan">*</span>
        </label>
        <input
          id="product-name"
          v-model="productName"
          type="text"
          class="input-retro"
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
            @click="setHookType('tiktok')"
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
            @click="setHookType('shopee')"
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
        <div class="flex items-end justify-between gap-3 mb-2">
          <label class="block text-sm font-medium text-slate-300">Variasi Hook V3</label>
          <span class="text-[11px] text-slate-500">{{ selectedHookVariation?.profileLabel }} · {{ selectedHookVariation?.duration }}</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          <button
            v-for="v in hookVariations[hookType]"
            :key="v.key"
            type="button"
            class="text-xs py-2.5 px-3 rounded-none border transition-all duration-150 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            :class="selectedVariation === v.key
              ? 'border-brand-500 bg-brand-900/40 text-brand-300'
              : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
            :title="`${v.description} Target ${v.duration}.`"
            :aria-pressed="selectedVariation === v.key"
            @click="selectedVariation = v.key"
          >
            <span class="block font-semibold">{{ v.label }}</span>
            <span class="block mt-1 text-[10px] leading-relaxed text-slate-500">{{ v.description }}</span>
          </button>
        </div>
      </div>

      <!-- V3 grounding context: facts prevent fabricated claims -->
      <details class="border border-slate-700 bg-slate-900/40 rounded-none">
        <summary class="cursor-pointer px-4 py-3 text-sm font-medium text-slate-300 hover:text-retro-cyan">
          🎯 Fakta, Audiens &amp; Konteks (opsional)
        </summary>
        <div class="space-y-4 border-t border-slate-700 p-4">
          <div>
            <label for="product-facts" class="block text-xs font-medium text-slate-300 mb-1">Fakta produk / promo terverifikasi</label>
            <textarea id="product-facts" v-model="productFacts" rows="3" maxlength="2500" class="input-retro"
              placeholder="Contoh: Bahan aluminium, garansi satu tahun, voucher dua puluh persen berlaku sampai tanggal tertentu."></textarea>
            <p class="mt-1 text-[11px] text-slate-500">Hanya fakta ini boleh dipakai AI. Angka yang tidak tersedia tidak akan dikarang.</p>
          </div>
          <div>
            <label for="target-audience" class="block text-xs font-medium text-slate-300 mb-1">Audiens target</label>
            <input id="target-audience" v-model="targetAudience" type="text" maxlength="500" class="input-retro"
              placeholder="Contoh: ibu yang bekerja dari rumah, pemain pemula, atau pembaca." />
          </div>
          <div v-if="['story', 'review', 'v2_personal'].includes(selectedVariation)">
            <label for="experience-notes" class="block text-xs font-medium text-slate-300 mb-1">Pengalaman nyata (wajib untuk tone personal)</label>
            <textarea id="experience-notes" v-model="experienceNotes" rows="3" maxlength="2000" class="input-retro"
              placeholder="Ceritakan penggunaan nyata; jangan berisi klaim yang belum diuji."></textarea>
          </div>
          <div v-if="selectedVariation === 'v2_visual'">
            <label for="visual-context" class="block text-xs font-medium text-slate-300 mb-1">Visual frame / aksi video <span class="text-retro-cyan">*</span></label>
            <textarea id="visual-context" v-model="visualContext" rows="3" maxlength="1500" class="input-retro"
              placeholder="Contoh: Tangan membuka tutup kipas, lalu udara bergerak di dekat kepala."></textarea>
            <p class="mt-1 text-[11px] text-amber-400">Wajib diisi agar voiceover cocok dengan footage.</p>
          </div>
          <div>
            <label for="cta-preference" class="block text-xs font-medium text-slate-300 mb-1">Preferensi CTA (opsional)</label>
            <input id="cta-preference" v-model="ctaPreference" type="text" maxlength="300" class="input-retro"
              placeholder="Contoh: Cek keranjang kuning, lalu lihat detail produk." />
          </div>
        </div>
      </details>

      <!-- Generate button -->
      <div class="flex items-center justify-between text-xs text-slate-500">
        <span>Model teks: <span class="text-slate-300">{{ activeTextLabel }}</span></span>
        <router-link to="/setting"
                class="underline underline-offset-2 hover:text-brand-300 transition-colors">
          ⚙️ Ganti model
        </router-link>
      </div>
      <button
        type="button"
        id="generate-hook-btn"
        class="btn-retro w-full"
        :disabled="!hookCanGenerate || isGenerating"
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
      <div v-if="hookGenerated && !isGenerating" class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-green-900/20 border border-green-700/30 rounded-none p-4 animate-fade-in">
        <div class="flex items-center gap-2 text-xs text-green-400">
          <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
          Hook V3 berhasil digenerate! Silakan cek & edit di Step 2.
        </div>
         <div v-if="hookMetadata" class="text-[11px] text-green-300/80">
           {{ hookMetadata.word_count }} kata · ±{{ hookMetadata.estimated_duration }} detik
           <span v-if="hookMetadata.repair_count > 0">· {{ hookMetadata.repair_count }} repair</span>
         <div v-if="hookMetadata?.warnings?.length" class="text-[11px] text-amber-300/90">
           ⚠ {{ hookMetadata.warnings.join(' · ') }}
         </div>

         </div>

        <button
          type="button"
          class="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-green-600 hover:bg-green-500 text-slate-100 text-[11px] font-bold rounded-none transition-colors shadow-lg shadow-green-900/20"
          @click="generateHook"
        >
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Coba Lagi (Regenerate)
        </button>
      </div>

      <!-- Hook error -->
      <div v-if="hookError" class="flex items-start gap-2 bg-red-900/30 border border-red-700/50 rounded-none p-3">
        <svg class="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <p class="text-red-300 text-xs">{{ hookError }}</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════════
         STEP 2 — Video & Voiceover Form
    ════════════════════════════════════════════════════════════════════════ -->
    <form @submit.prevent="handleSubmit" class="retro-box p-6 sm:p-8 space-y-6">
      <div class="flex items-center justify-between gap-2 mb-1">
        <div class="flex items-center gap-2">
          <span class="w-7 h-7 rounded-none bg-retro-magenta text-black text-slate-100 text-sm font-bold flex items-center justify-center flex-shrink-0">2</span>
          <h3 class="text-base font-semibold text-slate-100">Pilih Mode &amp; Proses</h3>
        </div>
        
        <!-- Mode Switcher -->
        <div class="flex bg-slate-800/80 p-1 rounded-none border border-slate-700">
          <button 
            type="button" 
            class="px-3 py-1.5 rounded-none text-xs font-medium transition-all"
            :class="mode === 'video' ? 'bg-retro-magenta text-black text-slate-100 shadow-lg' : 'text-slate-400 hover:text-slate-200'"
            @click="mode = 'video'"
          >
            Video + Audio
          </button>
          <button 
            type="button" 
            class="px-3 py-1.5 rounded-none text-xs font-medium transition-all"
            :class="mode === 'audio' ? 'bg-retro-magenta text-black text-slate-100 shadow-lg' : 'text-slate-400 hover:text-slate-200'"
            @click="mode = 'audio'"
          >
            Hanya Audio (MP3)
          </button>
        </div>
      </div>

      <!-- Badge model AI aktif (C3) -->
      <div class="flex flex-wrap gap-2 text-[11px] -mt-2">
        <span class="px-2 py-1 border border-slate-700 text-slate-400">🧠 Teks: <b class="text-slate-200">{{ activeTextLabel }}</b></span>
        <span class="px-2 py-1 border border-slate-700 text-slate-400">🎙️ Suara: <b class="text-slate-200">{{ voiceModelLabel }}</b></span>
      </div>

      <!-- Drag & Drop Video Upload — Only if mode is 'video' -->
      <div v-if="mode === 'video'" class="animate-fade-in space-y-3">
        <label class="block text-sm font-medium text-slate-300 mb-2">
          Video File <span class="text-retro-cyan">*</span>
        </label>

        <!-- Library Video Selected Badge -->
        <div v-if="libraryVideo"
          class="flex items-center gap-3 bg-brand-900/30 border border-brand-700/50 rounded-none p-3">
          <div class="w-8 h-8 rounded-none bg-retro-magenta text-black/30 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-retro-cyan" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm text-slate-100 font-medium truncate">{{ libraryVideo.name }}</p>
            <p class="text-xs text-slate-400">{{ formatSize(libraryVideo.size) }} · Dari Library</p>
          </div>
          <button type="button" @click="clearLibraryVideo"
            class="text-xs text-red-400 hover:text-red-300 transition-colors px-2 py-1 rounded">
            Hapus
          </button>
        </div>

        <!-- Upload area (show when no library video) -->
        <div v-else>
          <div
            id="drop-zone"
            class="relative border-2 border-dashed rounded-none transition-all duration-200 cursor-pointer"
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
                <div class="w-14 h-14 rounded-none bg-slate-700 flex items-center justify-center">
                  <svg class="w-7 h-7 text-retro-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                <div class="w-14 h-14 rounded-none bg-green-900/40 flex items-center justify-center">
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

          <!-- Pick from Library link -->
          <div class="flex items-center gap-3 mt-3">
            <div class="flex-1 h-px bg-slate-700"></div>
            <span class="text-xs text-slate-500">atau</span>
            <div class="flex-1 h-px bg-slate-700"></div>
          </div>
          <button
            type="button"
            id="pick-library-btn"
            class="w-full mt-3 flex items-center justify-center gap-2 py-2.5 px-4 rounded-none border border-slate-600 hover:border-brand-500 text-slate-300 hover:text-slate-100 text-sm transition-all bg-slate-800/40 hover:bg-slate-800"
            @click="showLibraryPicker = true"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"/>
            </svg>
            📂 Pilih dari Video Library
          </button>
        </div>
        <p v-if="errors.video" class="mt-2 text-sm text-red-400">{{ errors.video }}</p>
      </div>

      <!-- Voiceover Script Editor -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex flex-col">
            <label for="prompt" class="text-sm font-semibold text-slate-200">
              Script Editor <span class="text-retro-cyan">*</span>
            </label>
            <span class="text-[11px] text-slate-500">Koreksi skrip AI sesuai kebutuhanmu sebelum TTS</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="flex items-center gap-1 px-2 py-1 bg-brand-900/30 border border-brand-700/50 rounded-none">
              <span class="text-[10px] font-bold text-retro-cyan uppercase tracking-wider">Estimasi</span>
              <span class="text-xs font-mono text-brand-200">± {{ estimatedDuration }} Detik</span>
            </div>
            <span class="text-xs font-mono text-slate-500 bg-slate-800 px-2 py-1 rounded-none">{{ prompt.length }} Chars</span>
          </div>
        </div>
        <textarea
          id="prompt"
          v-model="prompt"
          rows="5"
          class="input-retro resize-none border-brand-900/20 focus:border-brand-500/50 bg-slate-800/20"
          placeholder="Skrip akan otomatis terisi setelah generate hook di atas, atau tulis sendiri di sini..."
        ></textarea>
        <p v-if="errors.prompt" class="mt-2 text-sm text-red-400">{{ errors.prompt }}</p>
      </div>

      <!-- Voice Model -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label for="voice-model" class="block text-sm font-medium text-slate-300">Voice Model</label>
          <router-link to="/setting"
                  class="text-xs text-slate-400 hover:text-brand-300 underline underline-offset-2 transition-colors">
            ⚙️ Kelola AI Model
          </router-link>
        </div>
        <select id="voice-model" v-model="voiceModel" class="input-retro">
          <option v-for="v in voiceOptions" :key="v.value" :value="v.value">{{ v.label }}</option>
        </select>
        <div class="flex items-center gap-2 mt-2">
          <button type="button" @click="previewVoice" :disabled="previewBusy"
                  class="px-3 py-1.5 border-2 border-retro-cyan text-retro-cyan text-xs hover:bg-retro-cyan hover:text-black transition-all disabled:opacity-50">
            {{ previewBusy ? '⏳ Membuat…' : '🔊 Contoh Suara' }}
          </button>
          <span v-if="previewErr" class="text-[11px] text-red-400">{{ previewErr }}</span>
        </div>
        <audio v-if="previewUrl" id="voice-preview-audio" :src="previewUrl" controls class="w-full mt-2"></audio>
        <p v-if="voiceModel.startsWith('custom:')" class="text-[11px] text-slate-500 mt-1">
          Model suara custom (OpenAI-compatible) — timing subtitle proporsional.
        </p>
      </div>

      <!-- Auto Subtitle Burn-in (hanya mode video) -->
      <div v-if="mode === 'video'" class="space-y-2 animate-fade-in">
        <label class="block text-sm font-medium text-slate-300 mb-2">
          Auto Subtitle Burn-in
          <span class="ml-2 text-xs text-slate-500">Opsional — dari skrip</span>
        </label>
        <div class="grid grid-cols-2 gap-2">
          <button
            type="button"
            id="subtitle-on-btn"
            class="flex flex-col items-center gap-1 py-3 px-2 rounded-none border-2 transition-all duration-150 text-center"
            :class="burnSubtitles
              ? 'border-brand-500 bg-brand-900/40 text-brand-300'
              : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
            @click="burnSubtitles = true"
          >
            <span class="text-lg">🔥</span>
            <span class="text-xs font-semibold leading-tight">AKTIF</span>
            <span class="text-xs opacity-60 leading-tight">Teks di tengah video</span>
          </button>
          <button
            type="button"
            id="subtitle-off-btn"
            class="flex flex-col items-center gap-1 py-3 px-2 rounded-none border-2 transition-all duration-150 text-center"
            :class="!burnSubtitles
              ? 'border-brand-500 bg-brand-900/40 text-brand-300'
              : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
            @click="burnSubtitles = false"
          >
            <span class="text-lg">⚫</span>
            <span class="text-xs font-semibold leading-tight">NONAKTIF</span>
            <span class="text-xs opacity-60 leading-tight">Video polos tanpa teks</span>
          </button>
        </div>
        <p v-if="burnSubtitles" class="text-[11px] text-slate-500">
          Caption otomatis dari skrip di-burn permanen ke video (gaya TikTok: putih tebal,
          outline hitam, di tengah layar). Timing mengikuti voiceover — paling akurat dengan
          voice Edge-TTS. File .srt juga disimpan dan bisa diunduh dari halaman Logs.
        </p>
      </div>

      <!-- 🎨 Custom Subtitle Style (hanya saat Auto Subtitle AKTIF) -->
      <div v-if="mode === 'video' && burnSubtitles" class="space-y-3 p-3 border-2 border-dashed border-slate-700 bg-slate-900/40 animate-fade-in">
        <label class="block text-sm font-medium text-slate-300">
          🎨 Gaya Caption
          <span class="ml-2 text-xs text-slate-500">Burn-in permanen</span>
        </label>

        <!-- Ukuran & posisi -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <span class="block text-xs text-slate-400 mb-1">Ukuran</span>
            <div class="grid grid-cols-3 gap-1">
              <button v-for="s in ['sm','md','lg']" :key="s" type="button"
                      @click="subtitleStyle.size = s"
                      :class="subtitleStyle.size === s ? 'border-brand-500 bg-brand-900/40 text-brand-300' : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
                      class="py-1.5 border-2 text-xs transition-all">
                {{ s === 'sm' ? 'Kecil' : s === 'md' ? 'Sedang' : 'Besar' }}
              </button>
            </div>
          </div>
          <div>
            <span class="block text-xs text-slate-400 mb-1">Posisi</span>
            <div class="grid grid-cols-3 gap-1">
              <button v-for="p in ['top','center','bottom']" :key="p" type="button"
                      @click="subtitleStyle.position = p"
                      :class="subtitleStyle.position === p ? 'border-brand-500 bg-brand-900/40 text-brand-300' : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
                      class="py-1.5 border-2 text-xs transition-all">
                {{ p === 'top' ? 'Atas' : p === 'center' ? 'Tengah' : 'Bawah' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Warna teks -->
        <div>
          <span class="block text-xs text-slate-400 mb-1">Warna Teks</span>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="(hex, cname) in SUBTITLE_COLORS" :key="cname" type="button"
                    @click="subtitleStyle.color = cname" :title="cname"
                    :class="subtitleStyle.color === cname ? 'border-brand-400 scale-110' : 'border-slate-700 hover:border-slate-500'"
                    class="w-7 h-7 border-2 transition-all" :style="{ backgroundColor: hex }"></button>
          </div>
        </div>

        <!-- Outline -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <span class="block text-xs text-slate-400 mb-1">Tebal Outline</span>
            <div class="grid grid-cols-3 gap-1">
              <button v-for="o in ['thin','md','thick']" :key="o" type="button"
                      @click="subtitleStyle.outline = o"
                      :class="subtitleStyle.outline === o ? 'border-brand-500 bg-brand-900/40 text-brand-300' : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
                      class="py-1.5 border-2 text-xs transition-all">
                {{ o === 'thin' ? 'Tipis' : o === 'md' ? 'Sedang' : 'Tebal' }}
              </button>
            </div>
          </div>
          <div>
            <span class="block text-xs text-slate-400 mb-1">Warna Outline</span>
            <div class="grid grid-cols-3 gap-1">
              <button v-for="oc in ['black','white','none']" :key="oc" type="button"
                      @click="subtitleStyle.outlineColor = oc"
                      :class="subtitleStyle.outlineColor === oc ? 'border-brand-500 bg-brand-900/40 text-brand-300' : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
                      class="py-1.5 border-2 text-xs transition-all">
                {{ oc === 'black' ? 'Hitam' : oc === 'white' ? 'Putih' : 'Tanpa' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Custom font + kapital -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <span class="block text-xs text-slate-400 mb-1">Font (TTF / OTF / TTC — maks 5 MB)</span>
            <select v-model="subtitleStyle.fontId" class="input-retro text-xs">
              <option value="">DejaVu Sans (bawaan)</option>
              <option v-for="f in subtitleFonts" :key="f.id" :value="f.id">{{ f.display_name }} — {{ f.family }}</option>
            </select>
            <div class="flex gap-1 mt-1">
              <label class="flex-1 cursor-pointer border-2 border-dashed border-slate-700 hover:border-brand-500 text-slate-400 text-xs py-1.5 text-center transition-all">
                📂 Impor Font…
                <input type="file" accept=".ttf,.otf,.ttc" class="hidden" @change="onFontFileChange" />
              </label>
              <button v-if="subtitleStyle.fontId" type="button" @click="deleteSubtitleFont(subtitleStyle.fontId)"
                      class="px-2 border-2 border-red-800 text-red-400 hover:bg-red-900/40 text-xs transition-all">
                Hapus
              </button>
            </div>
            <p v-if="fontStatus" class="text-[11px] mt-1" :class="fontStatusIsError ? 'text-red-400' : 'text-emerald-400'">{{ fontStatus }}</p>
          </div>
          <div class="flex items-end">
            <label class="flex items-center gap-2 cursor-pointer select-none w-full border-2 border-slate-700 py-2 px-2">
              <input type="checkbox" v-model="subtitleStyle.caps" class="accent-brand-500 w-4 h-4" />
              <span class="text-xs text-slate-300">HURUF KAPITAL semua</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Preview Caption (mock burn-in) — tanpa render FFmpeg -->
      <div v-if="mode === 'video'" class="space-y-2 animate-fade-in">
        <label class="block text-sm font-medium text-slate-300 mb-2">
          👀 Preview Caption
          <span class="ml-2 text-xs text-slate-500">Perkiraan tampilan subtitle di video</span>
        </label>
        <div class="mx-auto bg-slate-950 border-2 border-slate-700 relative overflow-hidden"
             :style="{ width: '170px', height: '302px' }">
          <div class="absolute inset-0 flex items-center justify-center text-[10px] text-slate-600">Area Video</div>
          <div class="absolute left-2 right-2" :style="captionPreviewStyle">
            <span :style="captionPreviewTextStyle">CONTOH TEKS SUBTITLE</span>
          </div>
        </div>
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
            class="flex flex-col items-center gap-1 py-3 px-2 rounded-none border-2 transition-all duration-150 text-center"
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

      <!-- Rasio Output & Kualitas (mode video) -->
      <div v-if="mode === 'video'" class="space-y-2 animate-fade-in">
        <label class="block text-sm font-medium text-slate-300 mb-2">
          Rasio Output
          <span class="ml-2 text-xs text-slate-500">Bentuk hasil video</span>
        </label>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="r in ratioOptions" :key="r.value"
            type="button"
            class="flex flex-col items-center gap-1 py-3 px-2 rounded-none border-2 transition-all duration-150 text-center"
            :class="outputRatio === r.value
              ? 'border-brand-500 bg-brand-900/40 text-brand-300'
              : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
            @click="outputRatio = r.value"
          >
            <span class="text-lg">{{ r.icon }}</span>
            <span class="text-xs font-semibold leading-tight">{{ r.label }}</span>
            <span class="text-xs opacity-60 leading-tight">{{ r.desc }}</span>
          </button>
        </div>
        <label class="block text-sm font-medium text-slate-300 mb-2 mt-3">
          Kualitas Render
        </label>
        <div class="grid grid-cols-2 gap-2">
          <button
            v-for="q in qualityOptions" :key="q.value"
            type="button"
            class="flex flex-col items-center gap-1 py-3 px-2 rounded-none border-2 transition-all duration-150 text-center"
            :class="quality === q.value
              ? 'border-brand-500 bg-brand-900/40 text-brand-300'
              : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:border-slate-500'"
            @click="quality = q.value"
          >
            <span class="text-lg">{{ q.icon }}</span>
            <span class="text-xs font-semibold leading-tight">{{ q.label }}</span>
            <span class="text-xs opacity-60 leading-tight">{{ q.desc }}</span>
          </button>
        </div>
      </div>

      <!-- Submit -->
      <button id="submit-btn" type="submit" class="btn-retro w-full text-base py-4" :disabled="isLoading">
        <svg v-if="isLoading" class="w-5 h-5 animate-spin-slow" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        {{ isLoading ? loadingMessage : (mode === 'video' ? '🎬 Buat Video Sekarang' : '🎙️ Generate Audio MP3') }}
      </button>

      <!-- SSE Progress Bar (only for video mode with SSE) -->
      <div v-if="isLoading && mode === 'video' && progressPercent > 0"
        class="space-y-2 animate-fade-in">
        <div class="flex items-center justify-between text-xs text-slate-400">
          <span>{{ loadingMessage }}</span>
          <span class="font-mono">{{ progressPercent }}%</span>
        </div>
        <div class="w-full bg-slate-700 rounded-none h-2 overflow-hidden">
          <div
            class="h-2 rounded-none bg-gradient-to-r from-brand-500 to-brand-400 transition-all duration-700"
            :style="{ width: progressPercent + '%' }"
          ></div>
        </div>
      </div>

      <!-- Error -->
      <div v-if="serverError" class="flex items-start gap-3 bg-red-900/30 border border-red-700/50 rounded-none p-4">
        <svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div class="flex-1 space-y-2">
          <p class="text-red-300 text-sm">{{ serverError }}</p>
          <button type="button" @click="handleSubmit"
                  class="text-xs text-retro-cyan underline hover:text-white transition-colors">
            ↻ Coba Lagi
          </button>
        </div>
      </div>
    </form>

    <!-- ═══════════════════════════════════════════════════════════════════════
         Result Card
    ════════════════════════════════════════════════════════════════════════ -->
    <div v-if="outputVideoUrl || outputAudioUrl" id="result-section" class="retro-box p-6 sm:p-8 space-y-5 animate-fade-in">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-none bg-green-500/20 flex items-center justify-center">
          <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-slate-100">
          {{ outputVideoUrl ? 'Video kamu sudah siap! 🎉' : 'Audio kamu sudah siap! 🎙️' }}
        </h3>
      </div>

      <!-- Video Result (Bandwidth Saver) -->
      <div v-if="outputVideoUrl" class="bg-slate-800/50 p-6 rounded-none border border-slate-700 flex flex-col items-center gap-4 text-center">
        <template v-if="!showPreview">
          <div class="w-16 h-16 rounded-none bg-green-900/30 text-green-400 flex items-center justify-center">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <p class="text-slate-200 font-semibold text-lg">Render Selesai!</p>
            <p class="text-slate-400 text-xs mt-1">Preview dinonaktifkan otomatis untuk menghemat bandwidth server.</p>
          </div>
          <button @click="showPreview = true" class="text-retro-cyan text-sm underline hover:text-white transition-colors">
            Muat Preview Video
          </button>
        </template>
        <template v-else>
          <video id="output-video" :src="outputVideoUrl" controls autoplay class="w-full rounded-none bg-black max-h-[480px]"></video>
        </template>
      </div>
      
      <!-- Audio Result -->
      <div v-if="outputAudioUrl && !outputVideoUrl" class="bg-slate-800/50 p-6 rounded-none border border-slate-700 flex flex-col items-center gap-4">
        <div class="w-16 h-16 rounded-none bg-retro-cyan text-black/20 flex items-center justify-center text-retro-cyan animate-pulse">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </div>
        <audio controls :src="outputAudioUrl" class="w-full"></audio>
        <p class="text-slate-400 text-xs">Voiceover generated successfully.</p>
      </div>

      <a id="download-btn" :href="outputVideoUrl || outputAudioUrl" :download="outputVideoUrl ? 'affiliate_video.mp4' : 'voiceover.mp3'" class="btn-retro w-full text-center">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Download {{ outputVideoUrl ? 'Video' : 'Audio' }}
      </a>

      <button id="reset-btn" type="button" class="btn-retro-secondary w-full" @click="reset">
        Buat {{ outputVideoUrl ? 'Video' : 'Audio' }} Lainnya
      </button>
    </div>

  </div>

  <!-- ═══════════════════════════════════════════════════════════════════════
       Library Picker Mini Modal
  ════════════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <div v-if="showLibraryPicker"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80"
      @click.self="showLibraryPicker = false">
      <div class="bg-slate-900 border border-slate-700 rounded-none w-full max-w-2xl p-6 space-y-4 animate-fade-in shadow-2xl max-h-[80vh] flex flex-col">
        <div class="flex items-center justify-between">
          <h3 class="text-slate-100 font-semibold">📂 Pilih Video dari Library</h3>
          <button @click="showLibraryPicker = false" class="text-slate-400 hover:text-slate-100 p-1">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div v-if="libraryPickerLoading" class="py-8 text-center text-slate-400">Memuat library...</div>
        <div v-else-if="libraryItems.length === 0" class="py-8 text-center">
          <p class="text-slate-400">Library kosong.</p>
          <router-link to="/library" @click="showLibraryPicker = false"
            class="text-retro-cyan text-sm hover:underline">Upload video dulu →</router-link>
        </div>
        <div v-else class="overflow-y-auto flex-1 grid grid-cols-2 sm:grid-cols-3 gap-3 pr-1">
          <div v-for="vid in libraryItems" :key="vid.id"
            class="cursor-pointer rounded-none border-2 border-slate-700 hover:border-brand-500 overflow-hidden transition-all group"
            @click="pickLibraryVideo(vid)">
            <div class="aspect-[9/16] bg-slate-800 relative overflow-hidden">
              <video :src="API_BASE_URL + vid.video_url" class="w-full h-full object-cover"
                muted preload="metadata"
                @mouseenter="e => e.target.play()"
                @mouseleave="e => { e.target.pause(); e.target.currentTime = 0 }"></video>
              <div class="absolute inset-0 bg-black/40 group-hover:bg-black/10 transition-all"></div>
            </div>
            <div class="p-2">
              <p class="text-xs text-slate-100 font-medium line-clamp-1">{{ vid.original_name }}</p>
              <p class="text-[10px] text-slate-500">{{ formatSize(vid.size) }}</p>
            </div>
          </div>
        </div>

        <p class="text-xs text-slate-500 text-center">Klik video untuk memilih</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import axios from 'axios'

// ── Config ────────────────────────────────────────────────────────────────────
// Base URL API: default kosong = same-origin "/api/..." (di-proxy Vite saat dev,
// Nginx saat production). Override dengan VITE_API_BASE_URL bila backend beda origin.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

// ── State ─────────────────────────────────────────────────────────────────────
const fileInput      = ref(null)
const selectedFile   = ref(null)
const prompt         = ref('')
const voiceModel     = ref('id-ID-GadisNeural')
const logId          = ref('')
const isDragging     = ref(false)
const isLoading      = ref(false)
const loadingMessage = ref('Memproses…')
const serverError    = ref('')
const outputVideoUrl = ref('')
const outputAudioUrl = ref('')
const durationMode   = ref('auto')
const burnSubtitles  = ref(true)   // Auto subtitle burn-in: AKTIF / NONAKTIF
const mode           = ref('video') // 'video' | 'audio'

// ── Custom Subtitle Style & Font ──────────────────────────────────────────────
const SUBTITLE_COLORS = {
  white:   '#ffffff',
  yellow:  '#ffd60a',
  cyan:    '#22d3ee',
  magenta: '#e879f9',
  green:   '#4ade80',
  red:     '#f87171',
  blue:    '#60a5fa',
  orange:  '#fb923c',
  black:   '#111827',
}
const subtitleStyle = reactive({
  size: 'md',            // sm | md | lg
  color: 'white',        // key SUBTITLE_COLORS
  outline: 'md',         // thin | md | thick
  outlineColor: 'black', // black | white | none
  position: 'center',    // top | center | bottom
  caps: false,
  fontId: '',            // '' = DejaVu Sans bawaan
})
const subtitleFonts    = ref([])   // daftar custom font dari server
const fontStatus       = ref('')
const fontStatusIsError = ref(false)

async function fetchSubtitleFonts() {
  try {
    const res = await axios.get(`${API_BASE_URL}/api/fonts`)
    subtitleFonts.value = res.data.fonts || []
  } catch { /* biarkan kosong bila gagal */ }
}

function flashFontStatus(msg, isError = false) {
  fontStatus.value = msg
  fontStatusIsError.value = isError
  setTimeout(() => { fontStatus.value = '' }, 5000)
}

async function onFontFileChange(e) {
  const file = e.target?.files?.[0]
  e.target.value = ''
  if (!file) return
  const okExt = /\.(ttf|otf|ttc)$/i.test(file.name)
  if (!okExt) {
    flashFontStatus('Format font tidak didukung. Gunakan .ttf, .otf, atau .ttc.', true)
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    flashFontStatus('Ukuran font maksimal 5 MB.', true)
    return
  }
  const fd = new FormData()
  fd.append('font', file)
  try {
    const res = await axios.post(`${API_BASE_URL}/api/fonts/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await fetchSubtitleFonts()
    subtitleStyle.fontId = res.data.font.id
    flashFontStatus(`✅ Font "${res.data.font.family}" siap dipakai.`)
  } catch (err) {
    flashFontStatus(err?.response?.data?.detail || 'Gagal upload font.', true)
  }
}

async function deleteSubtitleFont(fontId) {
  if (!fontId) return
  if (!confirm('Hapus font custom ini?')) return
  try {
    await axios.delete(`${API_BASE_URL}/api/fonts/${fontId}`)
    subtitleStyle.fontId = ''
    await fetchSubtitleFonts()
    flashFontStatus('Font dihapus.')
  } catch (err) {
    flashFontStatus(err?.response?.data?.detail || 'Gagal menghapus font.', true)
  }
}

const showPreview    = ref(false)

// SSE Progress
const progressPercent = ref(0)

// Library state
const libraryVideo       = ref(null)   // { id, name, size, url } picked from library
const showLibraryPicker  = ref(false)
const libraryItems       = ref([])
const libraryPickerLoading = ref(false)

// Hook generator state — V3 uses stable variation keys, not platform indexes.
const productName        = ref('')
const hookType           = ref('tiktok')     // 'tiktok' | 'shopee'
const selectedVariation  = ref('viral')
const productFacts       = ref('')
const targetAudience     = ref('')
const experienceNotes    = ref('')
const visualContext      = ref('')
const ctaPreference      = ref('')
const hookGenerated      = ref(false)
const isGenerating       = ref(false)
const hookError          = ref('')
const hookMetadata       = ref(null)


const errors = reactive({ video: '', prompt: '' })

// Check sessionStorage for library video on mount (set by VideoLibrary.vue)
onMounted(() => {
  fetchSubtitleFonts()
  fetchAiConfig()
  const stored = sessionStorage.getItem('library_video')
  if (stored) {
    try {
      libraryVideo.value = JSON.parse(stored)
      sessionStorage.removeItem('library_video')
    } catch {}
  }
})

// Clear output results when key inputs change to prevent playing stale/unsynced audio/video
watch([prompt, voiceModel, durationMode, burnSubtitles, selectedFile, mode, libraryVideo], () => {
  outputVideoUrl.value = ''
  outputAudioUrl.value = ''
  showPreview.value = false
})

// ── Computed ──────────────────────────────────────────────────────────────────
const estimatedDuration = computed(() => {
  const words = prompt.value.trim().split(/\s+/).filter(w => w.length > 0).length
  if (words === 0) return 0
  // Standard Indonesian narrations: ~140 words per minute
  return Math.ceil(words / 2.33)
})

// ── Output Ratio & Quality ────────────────────────────────────────────────────
const outputRatio = ref('9:16')   // '9:16' | '1:1' | '16:9'
const quality     = ref('hemat')  // 'hemat' (cepat) | 'hd'

const qualityOptions = [
  { value: 'hemat', icon: '⚡', label: 'Hemat & Cepat', desc: 'File kecil' },
  { value: 'hd',    icon: '✨', label: 'HD',            desc: 'Lebih tajam' },
]

const ratioOptions = [
  { value: '9:16', icon: '📱', label: '9:16 Vertikal', desc: 'TikTok / Reels' },
  { value: '1:1',  icon: '⬜', label: '1:1 Kotak',     desc: 'Feed IG / FB' },
  { value: '16:9', icon: '🖥️', label: '16:9 Lanskap',  desc: 'YouTube / Web' },
]

// ── Contoh Suara (voice preview) ──────────────────────────────────────────────
const previewBusy = ref(false)
const previewUrl  = ref('')
const previewErr  = ref('')
async function previewVoice() {
  if (previewBusy.value) return
  previewBusy.value = true
  previewErr.value = ''
  try {
    const r = await axios.post(`${API_BASE_URL}/api/voice-preview`,
      { voice_model: voiceModel.value }, { timeout: 30000 })
    previewUrl.value = API_BASE_URL + r.data.audio_url
    setTimeout(() => { document.getElementById('voice-preview-audio')?.load() }, 50)
  } catch (e) {
    previewErr.value = e?.response?.data?.detail || 'Gagal membuat contoh suara.'
  } finally { previewBusy.value = false }
}

// ── Preview Caption Style (C1) ───────────────────────────────────────────────
const SIZE_PX    = { sm: 11, md: 14, lg: 18 }
const OUTLINE_PX = { thin: 1, md: 2, thick: 3 }
const captionPreviewStyle = computed(() => {
  const pos = subtitleStyle.position
  return {
    top: pos === 'top' ? '12%' : pos === 'center' ? '50%' : 'auto',
    bottom: pos === 'bottom' ? '10%' : 'auto',
    transform: pos === 'center' ? 'translateY(50%)' : 'none',
    textAlign: 'center',
  }
})
const captionPreviewTextStyle = computed(() => {
  const size  = SIZE_PX[subtitleStyle.size] || 14
  const ow    = OUTLINE_PX[subtitleStyle.outline] || 2
  const color = SUBTITLE_COLORS[subtitleStyle.color] || '#ffffff'
  const oc    = subtitleStyle.outlineColor === 'white' ? '#ffffff'
              : subtitleStyle.outlineColor === 'none' ? 'transparent' : '#111827'
  return {
    fontSize: size + 'px',
    fontWeight: '700',
    color,
    textTransform: subtitleStyle.caps ? 'uppercase' : 'none',
    textShadow: subtitleStyle.outlineColor === 'none' ? 'none'
      : `${ow}px 0 0 ${oc}, -${ow}px 0 0 ${oc}, 0 ${ow}px 0 ${oc}, 0 -${ow}px 0 ${oc}`,
    lineHeight: '1.3',
  }
})

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
// ── Custom AI Provider (OpenAI-compatible) — dikelola di halaman /setting ─────
const aiConfig = reactive({ text_models: [], voice_models: [], active_text_model: '', defaults: {} })

async function fetchAiConfig() {
  try {
    const res = await axios.get(`${API_BASE_URL}/api/ai-config`)
    aiConfig.text_models       = res.data.text_models || []
    aiConfig.voice_models      = res.data.voice_models || []
    aiConfig.active_text_model = res.data.active_text_model || ''
    aiConfig.defaults          = res.data.defaults || {}
  } catch { /* biarkan kosong bila gagal */ }
}

const activeTextLabel = computed(() => {
  if (!aiConfig.active_text_model) return 'Pollinations (bawaan)'
  const m = aiConfig.text_models.find(x => x.id === aiConfig.active_text_model)
  return m ? `${m.label} (${m.model})` : 'Pollinations (bawaan)'
})

const voiceModelLabel = computed(() => {
  if (!voiceModel.value.startsWith('custom:')) {
    return `Edge-TTS — ${aiConfig.defaults.edge_tts_voice || 'id-ID-GadisNeural'}`
  }
  const id = voiceModel.value.slice('custom:'.length)
  const m = aiConfig.voice_models.find(x => x.id === id)
  return m ? `${m.label} (${m.model})` : 'Voice custom'
})

const voiceOptions = computed(() => {
  const base = [
    { value: 'id-ID-GadisNeural', label: `Edge-TTS — ${aiConfig.defaults.edge_tts_voice || 'id-ID-GadisNeural'}` },
    { value: 'openai-audio:shimmer', label: 'GPT Audio — Perempuan, Shimmer (Pollinations)' },
    { value: 'openai-audio:nova', label: 'GPT Audio — Perempuan, Nova (Pollinations)' },
    { value: 'openai-audio:alloy', label: 'GPT Audio — Netral, Alloy (Pollinations)' },
    { value: 'openai-audio:onyx', label: 'GPT Audio — Laki-laki, Onyx (Pollinations)' },
    { value: 'openai-audio:echo', label: 'GPT Audio — Laki-laki, Echo (Pollinations)' },
    { value: 'openai-audio:fable', label: 'GPT Audio — Laki-laki, Fable (Pollinations)' },
  ]
  const custom = aiConfig.voice_models.map(m => ({
    value: `custom:${m.id}`,
    label: `🎙️ ${m.label} — ${m.model} / ${m.voice} (custom)`,
  }))
  return [...custom, ...base]
})

// ── Hook Variations V3 — keys tetap kompatibel dengan API lama ───────────────
const hookProfileMeta = {
  short: { profileLabel: 'Pendek', duration: '30–37 detik' },
  standard: { profileLabel: 'Standar', duration: '30–45 detik' },
  long: { profileLabel: 'Panjang', duration: '37–50 detik' },
}
const v3Variation = (key, label, profile, description) => ({
  key, label, profile, description, ...hookProfileMeta[profile],
})
const universalVariations = [
  v3Variation('v2_problem', '🚀 Problem', 'standard', 'Masalah spesifik audiens, solusi, lalu CTA.'),
  v3Variation('v2_personal', '🚀 Personal', 'standard', 'Satu POV dari pengalaman yang diberikan.'),
  v3Variation('v2_education', '🚀 Edukasi', 'standard', 'Insight praktis tanpa statistik karangan.'),
  v3Variation('v2_contra', '🚀 Pro-Kontra', 'standard', 'Tantang satu asumsi aman dengan fakta input.'),
  v3Variation('v2_visual', '🚀 Visual Shock', 'standard', 'Reaksi spontan yang cocok dengan visual context.'),
]
const hookVariations = {
  tiktok: [
    v3Variation('viral', '🔥 Viral Impulsif', 'short', 'Hook tinggi energi dengan satu keunggulan relevan.'),
    v3Variation('shock', '😱 Shock & Reveal', 'standard', 'Aksi nyata diikuti reveal fitur tersembunyi.'),
    v3Variation('story', '💬 Cerita Personal', 'long', 'Cerita satu orang dari pengalaman input.'),
    v3Variation('fomo', '⚡ FOMO Healthy', 'short', 'Urgensi hanya dari fakta promo atau scarcity.'),
    ...universalVariations,
  ],
  shopee: [
    v3Variation('flash', '🛒 Flash Sale', 'short', 'Deal Shopee dari fakta harga dan promo.'),
    v3Variation('review', '⭐ Review Jujur', 'long', 'Review jujur atau buyer checklist yang jujur.'),
    v3Variation('bundle', '🎁 Bundle Deal', 'short', 'Nilai paket dari isi dan bonus terverifikasi.'),
    v3Variation('premium', '💎 Premium Value', 'long', 'Nilai premium dari kualitas terverifikasi.'),
    ...universalVariations,
  ],
}
const selectedHookVariation = computed(() =>
  hookVariations[hookType.value].find(v => v.key === selectedVariation.value)
  || hookVariations[hookType.value][0],
)
const hookCanGenerate = computed(() =>
  !!productName.value.trim()
  && (selectedVariation.value !== 'v2_visual' || !!visualContext.value.trim()),
)

function setHookType(platform) {
  hookType.value = platform
  if (!hookVariations[platform].some(v => v.key === selectedVariation.value)) {
    selectedVariation.value = hookVariations[platform][0].key
  }
}

// ── Generate Hook via AI ─────────────────────────────────────────────────────
async function generateHook() {
  const name = productName.value.trim()
  if (!name || !hookCanGenerate.value) {
    if (selectedVariation.value === 'v2_visual' && !visualContext.value.trim()) {
      hookError.value = 'Isi konteks visual terlebih dahulu untuk Visual Shock.'
    }
    return
  }

  isGenerating.value = true
  hookGenerated.value = false
  hookError.value = ''
  hookMetadata.value = null
  const varItem = selectedHookVariation.value

  try {
    const formData = new FormData()
    formData.append('product_name', name)
    formData.append('hook_type',    hookType.value)
    formData.append('variation',    varItem.key)
    formData.append('product_facts', productFacts.value.trim())
    formData.append('target_audience', targetAudience.value.trim())
    formData.append('experience_notes', experienceNotes.value.trim())
    formData.append('visual_context', visualContext.value.trim())
    formData.append('cta_preference', ctaPreference.value.trim())

    const response = await axios.post(`${API_BASE_URL}/api/generate-hook`, formData, { timeout: 60000 })
    prompt.value        = response.data.script
    logId.value         = response.data.log_id || ''
    hookMetadata.value  = response.data
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
  let valid = true
  if (mode.value === 'video') {
    if (!libraryVideo.value && !selectedFile.value) {
      errors.video = 'Pilih file video atau pilih dari Library.'
      valid = false
    } else if (selectedFile.value) {
      valid = validateFile(selectedFile.value)
    } else {
      errors.video = ''
    }
  }
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

// Library picker helpers
function clearLibraryVideo() {
  libraryVideo.value = null
}

async function openLibraryPicker() {
  showLibraryPicker.value = true
  libraryPickerLoading.value = true
  try {
    const res = await axios.get(`${API_BASE_URL}/api/library`)
    libraryItems.value = res.data.videos
  } catch {
    libraryItems.value = []
  } finally {
    libraryPickerLoading.value = false
  }
}

watch(showLibraryPicker, (val) => {
  if (val) openLibraryPicker()
})

function pickLibraryVideo(vid) {
  libraryVideo.value = { id: vid.id, name: vid.original_name, size: vid.size, url: API_BASE_URL + vid.video_url }
  showLibraryPicker.value = false
  errors.video = ''
}

// ── Submit ────────────────────────────────────────────────────────────────────
async function handleSubmit() {
  if (!validateForm()) return

  isLoading.value = true
  serverError.value = ''
  outputVideoUrl.value = ''
  outputAudioUrl.value = ''
  showPreview.value = false
  progressPercent.value = 0

  try {
    const formData = new FormData()

    if (mode.value === 'video') {
      // === SSE 2-Step Flow for video render ===
      formData.append('prompt_text', prompt.value.trim())
      formData.append('voice_model', voiceModel.value)
      formData.append('duration_mode', durationMode.value)
      formData.append('burn_subtitles', String(burnSubtitles.value))
      formData.append('subtitle_size', subtitleStyle.size)
      formData.append('subtitle_color', subtitleStyle.color)
      formData.append('subtitle_outline', subtitleStyle.outline)
      formData.append('subtitle_outline_color', subtitleStyle.outlineColor)
      formData.append('subtitle_position', subtitleStyle.position)
      formData.append('subtitle_caps', String(subtitleStyle.caps))
      formData.append('subtitle_font_id', subtitleStyle.fontId || '')
      formData.append('output_ratio', outputRatio.value)
      formData.append('quality', quality.value)
      if (logId.value) formData.append('log_id', logId.value)

      if (libraryVideo.value) {
        // Use library video — send a dummy empty file + library_video_id
        const emptyBlob = new Blob([''], { type: 'video/mp4' })
        formData.append('video', emptyBlob, 'placeholder.mp4')
        formData.append('library_video_id', libraryVideo.value.id)
      } else {
        formData.append('video', selectedFile.value)
      }

      loadingMessage.value = '⏳ Mengirim job...'

      // Step 1: Submit job
      const submitRes = await axios.post(`${API_BASE_URL}/api/jobs/submit`, formData, {
        timeout: 60000,
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const jobId = submitRes.data.job_id

      // Step 2: Subscribe SSE stream
      await new Promise((resolve, reject) => {
        const es = new EventSource(`${API_BASE_URL}/api/jobs/${jobId}/stream`)
        es.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            progressPercent.value = data.progress || 0
            loadingMessage.value  = data.message  || 'Memproses...'

            if (data.status === 'done') {
              es.close()
              const timestamp = '?t=' + Date.now()
              outputVideoUrl.value = API_BASE_URL + data.video_url + timestamp
              resolve()
            } else if (data.status === 'error') {
              es.close()
              reject(new Error(data.error || 'Server error'))
            }
          } catch (parseErr) {
            es.close()
            reject(parseErr)
          }
        }
        es.onerror = () => {
          es.close()
          reject(new Error('Koneksi SSE terputus. Coba lagi.'))
        }
      })

    } else {
      // === Audio-only (unchanged, direct axios) ===
      formData.append('prompt_text', prompt.value.trim())
      formData.append('voice_model', voiceModel.value)
      if (logId.value) formData.append('log_id', logId.value)
      loadingMessage.value = 'Sedang membuat AI voiceover…'

      const response = await axios.post(`${API_BASE_URL}/api/generate-audio`, formData, {
        timeout: 300000,
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const data = response.data
      const timestamp = '?t=' + Date.now()
      outputAudioUrl.value = API_BASE_URL + data.audio_url + timestamp
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
      serverError.value = err.message || 'Tidak bisa terhubung ke backend. Pastikan server berjalan di ' + API_BASE_URL
    }
  } finally {
    isLoading.value = false
    loadingMessage.value = 'Memproses…'
  }
}

// ── Reset ─────────────────────────────────────────────────────────────────────
function reset() {
  outputVideoUrl.value = ''
  outputAudioUrl.value = ''
  showPreview.value = false
  // do NOT clear promptText, selectedFile, libraryVideo so they can iterate faster
  errors.prompt        = ''
  errors.video         = ''
  progressPercent.value = 0
  serverError.value    = ''
}
</script>
