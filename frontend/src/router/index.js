import { createRouter, createWebHashHistory } from 'vue-router'
import VideoEditor from '../components/VideoEditor.vue'

// Lazy loaded components to reduce initial bundle size
const LogViewer = () => import('../components/LogViewer.vue')
const VideoLibrary = () => import('../components/VideoLibrary.vue')
const NotFound = () => import('../components/NotFound.vue')
const Login = () => import('../components/Login.vue')

const routes = [
  {
    path: '/',
    name: 'Home',
    component: VideoEditor,
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/logs',
    name: 'Logs',
    component: LogViewer,
    meta: { requiresAuth: true }
  },
  {
    path: '/library',
    name: 'Library',
    component: VideoLibrary,
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login' })
  } else if (to.name === 'Login' && token) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
