<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="8.5" cy="7" r="4"/>
            <line x1="20" y1="8" x2="20" y2="14"/>
            <line x1="23" y1="11" x2="17" y2="11"/>
          </svg>
        </div>
        <h1 class="auth-title">注册</h1>
        <p class="auth-desc">创建账号使用会议纪要系统</p>
      </div>

      <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>

      <form @submit.prevent="handleRegister" class="auth-form">
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
          <label class="form-label">所属部门</label>
          <div class="custom-select" @click="toggleDropdown" v-click-outside="closeDropdown">
            <div class="custom-select-trigger" :class="{ active: dropdownOpen }">
              <span :class="form.department_name ? '' : 'placeholder'">{{ form.department_name || '请选择部门' }}</span>
              <svg class="cs-chevron" :class="{ open: dropdownOpen }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </div>
            <div v-show="dropdownOpen" class="custom-select-dropdown">
              <div class="cs-option" :class="{ selected: !form.department_name }" @click="selectOption('')">请选择部门</div>
              <div class="cs-option" v-for="d in departments" :key="d.id" :class="{ selected: form.department_name === d.name }" @click="selectOption(d.name)">
                {{ d.name }}
              </div>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <input
            class="form-input"
            type="password"
            v-model="form.password"
            placeholder="至少 6 位密码"
            autocomplete="new-password"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">确认密码</label>
          <input
            class="form-input"
            type="password"
            v-model="form.confirmPassword"
            placeholder="再次输入密码"
            autocomplete="new-password"
            required
          />
        </div>

        <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
          <span v-if="loading" class="btn-loading-dots">
            <span class="btn-dot"></span><span class="btn-dot"></span><span class="btn-dot"></span>
          </span>
          <span v-else>注 册</span>
        </button>
      </form>

      <div class="auth-footer">
        已有账号？
        <router-link to="/login" class="auth-link">登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/index.js'

const router = useRouter()
const loading = ref(false)
const flash = ref('')
const flashType = ref('flash-error')
const departments = ref([])
const dropdownOpen = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  department_name: '',
})

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
}

function closeDropdown() {
  dropdownOpen.value = false
}

function selectOption(name) {
  form.department_name = name
  dropdownOpen.value = false
}

// Click-outside directive
const vClickOutside = {
  mounted(el, binding) {
    el.__clickOutside = (e) => {
      if (!el.contains(e.target)) binding.value()
    }
    document.addEventListener('click', el.__clickOutside)
  },
  unmounted(el) {
    document.removeEventListener('click', el.__clickOutside)
  },
}

onMounted(async () => {
  // Register is public, but departments endpoint needs auth.
  // We'll try to fetch departments; if it fails (no token), show empty list.
  try {
    departments.value = await api.listDepartments()
  } catch (_) {
    // Departments endpoint is auth-protected now, so skip silently
  }
})

async function handleRegister() {
  const username = form.username.trim()
  if (!username) {
    flash.value = '请输入用户名'
    flashType.value = 'flash-error'
    return
  }
  if (!form.password || form.password.length < 6) {
    flash.value = '密码长度不能少于 6 位'
    flashType.value = 'flash-error'
    return
  }
  if (form.password !== form.confirmPassword) {
    flash.value = '两次输入的密码不一致'
    flashType.value = 'flash-error'
    return
  }

  loading.value = true
  flash.value = ''
  try {
    await api.register(username, form.password, form.department_name)
    flash.value = '注册成功，请登录'
    flashType.value = 'flash-success'
    setTimeout(() => router.push('/login'), 1200)
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
  box-sizing: border-box;
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: var(--surface-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  padding: var(--space-6) var(--space-5);
  border: 1px solid rgba(226, 232, 240, 0.6);
  box-sizing: border-box;
}

@media (min-width: 640px) {
  .auth-card {
    padding: var(--space-10) var(--space-8);
  }
}

.auth-header {
  text-align: center;
  margin-bottom: var(--space-5);
}

.auth-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto var(--space-3);
  background: linear-gradient(135deg, var(--primary-50), var(--primary-100));
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-600);
}

.auth-title {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--gray-900);
  margin-bottom: var(--space-1);
}

.auth-desc {
  font-size: var(--text-sm);
  color: var(--gray-400);
}

.auth-form {
  margin-bottom: var(--space-4);
}

.auth-form .form-group {
  margin-bottom: var(--space-3);
}

/* ── Custom Select ── */
.custom-select {
  position: relative;
}

.custom-select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid var(--gray-200);
  border-radius: var(--radius-md);
  background: var(--surface);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  box-sizing: border-box;
  user-select: none;
}

.custom-select-trigger:hover {
  border-color: var(--gray-300);
}

.custom-select-trigger.active {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.custom-select-trigger .placeholder {
  color: var(--gray-400);
}

.cs-chevron {
  flex-shrink: 0;
  color: var(--gray-400);
  transition: transform 0.2s ease;
}

.cs-chevron.open {
  transform: rotate(180deg);
}

.custom-select-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 50;
  background: #fff;
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  max-height: 220px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.cs-option {
  padding: 10px 14px;
  font-size: var(--text-sm);
  color: var(--gray-700);
  cursor: pointer;
  transition: background 0.15s;
}

.cs-option:first-child {
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.cs-option:last-child {
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.cs-option:hover {
  background: var(--primary-50);
}

.cs-option.selected {
  color: var(--primary-700);
  font-weight: 600;
  background: var(--primary-50);
}

/* ── Button ── */
.btn-block {
  width: 100%;
  padding: 10px 20px;
  font-size: var(--text-sm);
  margin-top: var(--space-2);
}

/* ── Footer ── */
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

/* ── Loading dots ── */
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
