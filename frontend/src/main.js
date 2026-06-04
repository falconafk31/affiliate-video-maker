import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import axios from 'axios'

// ── Global Axios Configuration ──
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

const app = createApp(App)
app.use(router)
app.mount('#app')
