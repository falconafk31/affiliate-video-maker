import { createRouter, createWebHashHistory } from 'vue-router'
import VideoEditor from '../components/VideoEditor.vue'
import LogViewer from '../components/LogViewer.vue'
import NotFound from '../components/NotFound.vue'

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
