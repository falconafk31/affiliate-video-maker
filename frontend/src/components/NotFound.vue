<template>
  <div class="min-h-[70vh] flex flex-col items-center justify-center text-center px-4">
    <!-- Animated Icon -->
    <div class="relative mb-8">
      <div class="absolute inset-0 bg-retro-cyan text-black/20 blur-3xl rounded-none"></div>
      <div class="relative w-32 h-32 md:w-48 md:h-48 flex items-center justify-center bg-slate-900 border border-white/10 rounded-none shadow-2xl animate-pulse-slow">
        <h1 class="text-6xl md:text-8xl font-black text-transparent bg-clip-text bg-gradient-to-br from-brand-400 to-brand-700">
          404
        </h1>
      </div>
    </div>

    <!-- Text Content -->
    <h2 class="text-2xl md:text-3xl font-bold text-slate-100 mb-4">Waduh! Halaman Hilang</h2>
    <p class="text-slate-400 max-w-md mx-auto mb-10 leading-relaxed">
      Sepertinya halaman yang Anda cari telah dipindahkan atau tidak pernah ada. Coba cek kembali URL Anda atau kembali ke halaman utama.
    </p>

    <!-- Actions -->
    <div class="flex flex-col sm:flex-row gap-4">
      <router-link
        to="/"
        class="flex items-center justify-center gap-2 px-8 py-3 bg-retro-magenta text-black hover:bg-retro-cyan text-black text-slate-100 font-semibold rounded-none transition-all shadow-lg hover:shadow-brand-500/25 group"
      >
        <svg class="w-5 h-5 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Kembali ke Beranda
      </router-link>
      
      <button
        @click="$router.go(-1)"
        class="px-8 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-none transition-all"
      >
        Kembali ke Sebelumnya
      </button>
    </div>
  </div>
</template>

<script setup>
// No extra logic needed for simple 404
</script>

<style scoped>
.animate-pulse-slow {
  animation: pulse-slow 4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse-slow {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.9;
    transform: scale(1.02);
  }
}
</style>
