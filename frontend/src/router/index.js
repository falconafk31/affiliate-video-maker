import { createRouter, createWebHashHistory } from 'vue-router'
import VideoEditor from '../components/VideoEditor.vue'

// Lazy loaded components to reduce initial bundle size
const LogViewer = () => import('../components/LogViewer.vue')
const VideoLibrary = () => import('../components/VideoLibrary.vue')
const NotFound = () => import('../components/NotFound.vue')

const routes = [
  {
    path: '/',
    name: 'Home',
    component: VideoEditor
  },
  {
    path: '/logs',
    name: 'Logs',
    component: LogViewer
  },
  {
    path: '/library',
    name: 'Library',
    component: VideoLibrary
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

export default router
