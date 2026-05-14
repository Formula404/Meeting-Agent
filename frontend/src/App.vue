<template>
  <div class="app-shell">
    <nav class="nav-bar">
      <div class="nav-inner">
        <router-link to="/" class="nav-brand">
          <svg class="nav-brand-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          会议纪要自动推送
        </router-link>
        <div class="nav-links">
          <router-link to="/" class="nav-link">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>上传</span>
          </router-link>
          <router-link v-if="authStore.isAdmin" to="/admin" class="nav-link">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            <span>管理</span>
          </router-link>
        </div>
        <div v-if="authStore.isLoggedIn" class="nav-right">
          <span class="nav-user">
            <span class="nav-user-avatar">{{ authStore.user?.username?.[0]?.toUpperCase() }}</span>
            <span class="nav-user-name">{{ authStore.user?.username }}</span>
            <span v-if="authStore.isAdmin" class="nav-user-badge">管理员</span>
          </span>
          <button class="btn btn-ghost btn-sm nav-logout" @click="handleLogout">退出</button>
        </div>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { authStore } from './store/auth.js'
import { useRouter } from 'vue-router'
import api from './api/index.js'

const router = useRouter()

async function handleLogout() {
  try {
    await api.logout()
  } catch (_) {
    // Logout even if API call fails
  }
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.nav-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--gray-500);
}

.nav-user-avatar {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--primary-500), var(--primary-400));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.nav-user-name {
  color: var(--gray-700);
  font-weight: 500;
}

.nav-user-badge {
  font-size: 10px;
  font-weight: 600;
  background: var(--primary-50);
  color: var(--primary-600);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.nav-logout {
  color: var(--gray-400);
  font-size: var(--text-xs);
}
.nav-logout:hover {
  color: var(--danger);
}
</style>
