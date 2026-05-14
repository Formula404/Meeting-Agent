<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
        </div>
        <h1 class="auth-title">登录</h1>
        <p class="auth-desc">会议纪要自动推送系统</p>
      </div>

      <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>

      <form @submit.prevent="handleLogin" class="auth-form">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input
            class="form-input"
            v-model="form.username"
            placeholder="输入用户名"
            autocomplete="username"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <input
            class="form-input"
            type="password"
            v-model="form.password"
            placeholder="输入密码"
            autocomplete="current-password"
            required
          />
        </div>

        <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
          <span v-if="loading" class="btn-loading-dots">
            <span class="btn-dot"></span><span class="btn-dot"></span><span class="btn-dot"></span>
          </span>
          <span v-else>登 录</span>
        </button>
      </form>

      <div class="auth-footer">
        还没有账号？
        <router-link to="/register" class="auth-link">注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/index.js'
import { authStore } from '../store/auth.js'

const router = useRouter()
const loading = ref(false)
const flash = ref('')
const flashType = ref('flash-error')

const form = reactive({
  username: '',
  password: '',
})

async function handleLogin() {
  if (!form.username.trim() || !form.password) {
    flash.value = '请输入用户名和密码'
    flashType.value = 'flash-error'
    return
  }
  loading.value = true
  flash.value = ''
  try {
    const data = await api.login(form.username, form.password)
    authStore.setToken(data.token)
    authStore.setUser(data.user)
    router.push('/')
  } catch (e) {
    flash.value = e.message
    flashType.value = 'flash-error'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - var(--nav-height) - var(--space-10) * 2);
  padding: var(--space-4);
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: var(--surface-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  padding: var(--space-8) var(--space-6);
  border: 1px solid rgba(226, 232, 240, 0.6);
}

@media (min-width: 640px) {
  .auth-card {
    padding: var(--space-10) var(--space-8);
  }
}

.auth-header {
  text-align: center;
  margin-bottom: var(--space-6);
}

.auth-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto var(--space-4);
  background: linear-gradient(135deg, var(--primary-50), var(--primary-100));
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-600);
}

.auth-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--gray-900);
  margin-bottom: var(--space-1);
}

.auth-desc {
  font-size: var(--text-sm);
  color: var(--gray-400);
}

.auth-form {
  margin-bottom: var(--space-5);
}

.auth-form .form-group {
  margin-bottom: var(--space-4);
}

.btn-block {
  width: 100%;
  padding: 11px 20px;
  font-size: var(--text-base);
  margin-top: var(--space-2);
}

.auth-footer {
  text-align: center;
  font-size: var(--text-sm);
  color: var(--gray-400);
}

.auth-link {
  color: var(--primary-600);
  text-decoration: none;
  font-weight: 600;
}

.auth-link:hover {
  text-decoration: underline;
}

.btn-loading-dots {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.btn-dot {
  width: 6px;
  height: 6px;
  background: #fff;
  border-radius: 50%;
  animation: dotBounce 1.2s infinite ease-in-out both;
}

.btn-dot:nth-child(1) { animation-delay: -0.32s; }
.btn-dot:nth-child(2) { animation-delay: -0.16s; }
.btn-dot:nth-child(3) { animation-delay: 0s; }

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
</style>
