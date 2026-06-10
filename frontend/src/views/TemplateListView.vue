<template>
  <div>
    <div class="review-header">
      <h1 class="page-title" style="margin-bottom:0">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:8px">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
        会议模板
      </h1>
      <router-link to="/templates/new" class="btn btn-primary btn-sm" style="align-self:flex-start">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        创建模板
      </router-link>
    </div>

    <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>

    <!-- Template grid -->
    <div v-if="templates.length" class="template-grid">
      <div
        v-for="t in templates"
        :key="t.id"
        class="template-card"
      >
        <div class="template-card-header">
          <div class="template-card-name">
            {{ t.name }}
            <span v-if="t.is_builtin" class="template-badge-builtin" title="系统内置模板">内置</span>
          </div>
          <div class="template-card-actions">
            <router-link :to="{ name: 'template-detail', params: { id: t.id } }" class="btn btn-ghost btn-sm">查看</router-link>
            <button
              v-if="t.is_builtin ? isAdmin : (isAdmin || t.created_by === currentUserId)"
              class="btn btn-ghost btn-sm btn-danger-text"
              @click="handleDelete(t)"
              :disabled="deletingId === t.id"
            >
              {{ deletingId === t.id ? '删除中...' : '删除' }}
            </button>
          </div>
        </div>
        <div class="template-card-desc">{{ t.description || '无描述' }}</div>
        <div class="template-card-meta">
          <span>创建者：{{ t.creator_name }}</span>
          <span>{{ formatTime(t.created_at) }}</span>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.3">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
      </svg>
      <div class="empty-title">暂无模板</div>
      <div class="empty-desc">创建模板后，上传录音时可选择模板来控制会议纪要的正文格式</div>
      <router-link to="/templates/new" class="btn btn-primary">创建第一个模板</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/index.js'

const templates = ref([])
const flash = ref('')
const flashType = ref('flash-info')
const deletingId = ref(null)
const currentUserId = ref(null)
const isAdmin = ref(false)

onMounted(async () => {
  try {
    const [tmpls, me] = await Promise.all([
      api.listTemplates(),
      api.getMe().catch(() => null),
    ])
    templates.value = tmpls
    if (me) {
      currentUserId.value = me.id
      isAdmin.value = me.role === 'admin'
    }
  } catch (_) {}
})

async function handleDelete(t) {
  if (!confirm(`确认删除模板「${t.name}」？此操作不可恢复。`)) return
  deletingId.value = t.id
  try {
    await api.deleteTemplate(t.id)
    templates.value = templates.value.filter((x) => x.id !== t.id)
    flash.value = `模板「${t.name}」已删除`
    flashType.value = 'flash-success'
  } catch (e) {
    flash.value = `删除失败: ${e.message}`
    flashType.value = 'flash-error'
  } finally {
    deletingId.value = null
  }
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts + 'Z').toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.template-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}

@media (min-width: 640px) {
  .template-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (min-width: 1024px) {
  .template-grid {
    grid-template-columns: 1fr 1fr 1fr;
  }
}

.template-card {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: var(--space-5) var(--space-4);
  border: 1px solid rgba(226, 232, 240, 0.6);
  transition: all var(--transition-base);
  display: flex;
  flex-direction: column;
}

.template-card:hover {
  box-shadow: var(--shadow-card-hover);
  border-color: var(--primary-200);
}

@media (min-width: 640px) {
  .template-card {
    padding: var(--space-6);
    border-radius: var(--radius-xl);
  }
}

.template-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2);
}

.template-card-name {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--gray-800);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.template-badge-builtin {
  font-size: 10px;
  font-weight: 600;
  background: var(--primary-50);
  color: var(--primary-600);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.template-card-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.template-card-desc {
  font-size: var(--text-sm);
  color: var(--gray-500);
  margin-top: var(--space-2);
  line-height: var(--leading-relaxed);
  flex: 1;
}

.template-card-meta {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-xs);
  color: var(--gray-400);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--gray-100);
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-10) 0;
  color: var(--gray-400);
  text-align: center;
}

.empty-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--gray-600);
}

.empty-desc {
  font-size: var(--text-sm);
  color: var(--gray-400);
  max-width: 360px;
  line-height: var(--leading-relaxed);
}
</style>
