// Toast notification mini — dipakai lewat <Toaster /> di App.vue
import { reactive } from 'vue'

export const toasts = reactive([])
let seq = 0

/**
 * Tampilkan toast.
 * @param {string} msg  pesan
 * @param {'info'|'success'|'error'} type
 * @param {number} ms   durasi tampil
 */
export function toast(msg, type = 'info', ms = 4500) {
  const id = ++seq
  toasts.push({ id, msg, type })
  setTimeout(() => {
    const i = toasts.findIndex(t => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, ms)
}
