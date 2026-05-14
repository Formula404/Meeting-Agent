import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import api from './api/index.js'
import { authStore } from './store/auth.js'
import './style.css'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('./views/LoginView.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('./views/RegisterView.vue'),
    meta: { title: '注册', public: true },
  },
  {
    path: '/',
    name: 'upload',
    component: () => import('./views/UploadView.vue'),
    meta: { title: '上传会议记录' },
  },
  {
    path: '/review/:id',
    name: 'review',
    component: () => import('./views/ReviewView.vue'),
    meta: { title: '审查修改' },
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('./views/AdminView.vue'),
    meta: { title: '用户与部门管理', admin: true },
  },
  {
    path: '/transcribe',
    name: 'transcribe',
    component: () => import('./views/TranscribeView.vue'),
    meta: { title: '录音转文字' },
  },
  {
    path: '/transcribe/:id',
    name: 'transcribe-edit',
    component: () => import('./views/TranscribeView.vue'),
    meta: { title: '编辑转录结果' },
  },
]

const router = createRouter({ history: createWebHistory(), routes })

// ── Route guard ──
router.beforeEach(async (to, from, next) => {
  // Public routes (login, register) — always allowed
  if (to.meta.public) {
    // Already logged in → redirect to home
    if (authStore.token && authStore.user) {
      return next('/')
    }
    return next()
  }

  // Protected routes
  if (!authStore.token) {
    return next('/login')
  }

  // Verify token if we haven't loaded user yet
  if (!authStore.user) {
    try {
      const user = await api.getMe()
      authStore.setUser(user)
    } catch {
      authStore.logout()
      return next('/login')
    }
  }

  // Admin route check
  if (to.meta.admin && !authStore.isAdmin) {
    return next('/')
  }

  next()
})

// ── Dynamic document title ──
router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} — 会议纪要自动推送` : '会议纪要自动推送'
})

const app = createApp(App)
app.use(router)
app.mount('#app')
