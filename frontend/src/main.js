import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import UploadView from './views/UploadView.vue'
import ReviewView from './views/ReviewView.vue'
import AdminView from './views/AdminView.vue'
import './style.css'

const routes = [
  { path: '/', name: 'upload', component: UploadView, meta: { title: '上传会议记录' } },
  { path: '/review/:id', name: 'review', component: ReviewView, meta: { title: '审查修改' } },
  { path: '/admin', name: 'admin', component: AdminView, meta: { title: '用户与部门管理' } },
]

const router = createRouter({ history: createWebHistory(), routes })

createApp(App).use(router).mount('#app')
