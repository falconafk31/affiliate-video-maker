<template>
  <div class="min-h-screen bg-slate-950 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(14,165,233,0.15),rgba(255,255,255,0))]">
    <header class="border-b border-white/10 bg-slate-950/80 backdrop-blur-md sticky top-0 z-10">
      <div class="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <!-- Logo icon -->
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-400 to-brand-700 flex items-center justify-center shadow-lg">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h1 class="text-lg font-bold text-white leading-none">Affiliate Video Maker</h1>
            <p class="text-xs text-slate-400">Powered by Pollinations AI</p>
          </div>
        </div>

        <!-- Nav Tabs -->
        <nav class="flex gap-1 bg-slate-800/60 rounded-xl p-1">
          <router-link
            to="/"
            active-class="bg-brand-600 text-white shadow"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-all text-slate-400 hover:text-white">
            🎬 Editor
          </router-link>
          <router-link
            to="/logs"
            active-class="bg-brand-600 text-white shadow"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-all text-slate-400 hover:text-white">
            📋 Log Prompt
          </router-link>
        </nav>
      </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 py-10 text-slate-100">
      <router-view />
    </main>

    <footer class="border-t border-white/10 py-6 text-center text-slate-500 text-sm">
      &copy; {{ new Date().getFullYear() }} Affiliate Video Maker. All rights reserved.
    </footer>
  </div>
</template>

<script setup>
</script>
