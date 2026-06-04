<template>
  <div class="min-h-screen bg-retro-bg font-mono">
    <header class="border-b-4 border-retro-cyan bg-retro-black sticky top-0 z-10 shadow-[0_4px_0_0_#FF00FF]">
      <div class="max-w-6xl mx-auto px-4 py-4 flex flex-col sm:flex-row items-center justify-between gap-4 sm:gap-3 text-center sm:text-left">
        <div class="flex items-center justify-center sm:justify-start gap-3 w-full sm:w-auto">
          <!-- Logo icon -->
          <div class="w-8 h-8 sm:w-10 sm:h-10 border-2 border-retro-cyan bg-retro-magenta flex items-center justify-center shadow-[2px_2px_0_0_#00FFFF] flex-shrink-0">
            <span class="font-retro font-bold text-xl sm:text-2xl text-black">V</span>
          </div>
          <div>
            <h1 class="text-2xl sm:text-3xl font-bold text-retro-cyan font-retro uppercase leading-none tracking-wider shadow-black drop-shadow-md">Affiliate Video Maker</h1>
            <p class="text-[9px] sm:text-[10px] text-retro-magenta font-bold uppercase mt-1">Powered by Pollinations AI</p>
          </div>
        </div>

        <!-- Nav Tabs -->
        <nav class="flex flex-wrap justify-center gap-2 sm:gap-2 w-full sm:w-auto">
          <router-link
            to="/"
            active-class="bg-retro-cyan !text-black shadow-[2px_2px_0_0_#FF00FF]"
            class="px-2 py-1 sm:px-4 sm:py-2 border-2 border-retro-cyan font-retro text-base sm:text-lg uppercase transition-all text-retro-cyan hover:bg-retro-cyan hover:text-black">
            [ Editor ]
          </router-link>
          <router-link
            to="/library"
            active-class="bg-retro-cyan !text-black shadow-[2px_2px_0_0_#FF00FF]"
            class="px-2 py-1 sm:px-4 sm:py-2 border-2 border-retro-cyan font-retro text-base sm:text-lg uppercase transition-all text-retro-cyan hover:bg-retro-cyan hover:text-black">
            [ Library ]
          </router-link>
          <router-link
            to="/logs"
            active-class="bg-retro-cyan !text-black shadow-[2px_2px_0_0_#FF00FF]"
            class="px-2 py-1 sm:px-4 sm:py-2 border-2 border-retro-cyan font-retro text-base sm:text-lg uppercase transition-all text-retro-cyan hover:bg-retro-cyan hover:text-black">
            [ Logs ]
          </router-link>
        </nav>
      </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 py-10 text-slate-100">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>

    <footer class="border-t border-white/10 py-6 text-center text-slate-500 text-sm">
      &copy; {{ new Date().getFullYear() }} Affiliate Video Maker. All rights reserved.
    </footer>
  </div>
</template>

<script setup>
</script>
