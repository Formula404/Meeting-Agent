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
        {{ tmpl?.name || '模板详情' }}
      </h1>
      <div class="flex gap-2" style="align-self:flex-start">
        <router-link to="/templates" class="btn btn-ghost btn-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"/>
            <polyline points="12 19 5 12 12 5"/>
          </svg>
          返回
        </router-link>
        <router-link
          v-if="tmpl && !tmpl.is_builtin && (isAdmin || tmpl.created_by === currentUserId)"
          :to="{ name: 'template-edit', params: { id: tmpl.id } }"
          class="btn btn-outline btn-sm"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          编辑
        </router-link>
      </div>
    </div>

    <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>

    <div v-if="!tmpl && !loading" class="empty-state">
      <div>模板不存在</div>
      <router-link to="/templates" class="btn btn-outline">返回模板列表</router-link>
    </div>

    <template v-if="tmpl">
      <!-- Basic info -->
      <div class="card">
        <h2 class="card-title">基本信息</h2>
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">名称</div>
            <div class="info-value">{{ tmpl.name }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">类型</div>
            <div class="info-value">
              <span v-if="tmpl.is_builtin" class="badge badge-pushed">系统内置</span>
              <span v-else class="badge badge-draft">自定义</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-label">创建者</div>
            <div class="info-value">{{ tmpl.creator_name }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">创建时间</div>
            <div class="info-value">{{ formatTime(tmpl.created_at) }}</div>
          </div>
        </div>
        <div class="info-item" style="margin-top:var(--space-3)">
          <div class="info-label">描述</div>
          <div class="info-value">{{ tmpl.description || '无描述' }}</div>
        </div>
      </div>

      <!-- Style prompt -->
      <div class="card">
        <h2 class="card-title">风格要求</h2>
        <pre class="prompt-block">{{ tmpl.style_prompt || '无' }}</pre>
        <div class="prompt-hint">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          此提示词将作为额外风格要求追加到 AI 系统提示词末尾，仅影响会议纪要正文的格式
        </div>
      </div>

      <!-- Sample output -->
      <div class="card" v-if="tmpl.sample_output && tmpl.sample_output !== '{}'">
        <h2 class="card-title">示例输出</h2>
        <pre class="sample-text">{{ tmpl.sample_output }}</pre>
      </div>
      <div class="card" v-else>
        <h2 class="card-title">示例输出</h2>
        <div class="empty-hint">创建模板时未上传示例文档，无示例输出</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/index.js'

const route = useRoute()
const tmpl = ref(null)
const loading = ref(true)
const flash = ref('')
const flashType = ref('flash-info')
const isAdmin = ref(false)
const currentUserId = ref(null)

onMounted(async () => {
  try {
    const [data, me] = await Promise.all([
      api.getTemplate(route.params.id),
      api.getMe().catch(() => null),
    ])
    tmpl.value = data
    if (me) {
      currentUserId.value = me.id
      isAdmin.value = me.role === 'admin'
    }
  } catch (e) {
    flash.value = `加载失败: ${e.message}`
    flashType.value = 'flash-error'
  } finally {
    loading.value = false
  }
})

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts + 'Z').toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

@media (max-width: 480px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
}

.info-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--gray-500);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 2px;
}

.info-value {
  font-size: var(--text-sm);
  color: var(--gray-700);
}

.prompt-block {
  font-size: var(--text-sm);
  color: var(--gray-700);
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  white-space: pre-wrap;
  line-height: var(--leading-relaxed);
  font-family: inherit;
  max-height: 400px;
  overflow-y: auto;
}

.prompt-hint {
  font-size: var(--text-xs);
  color: var(--gray-400);
  margin-top: var(--space-2);
  line-height: var(--leading-relaxed);
}

.sample-text {
  font-size: var(--text-sm);
  color: var(--gray-700);
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  white-space: pre-wrap;
  line-height: var(--leading-relaxed);
  font-family: inherit;
  max-height: 400px;
  overflow-y: auto;
}

.empty-hint {
  font-size: var(--text-sm);
  color: var(--gray-400);
  font-style: italic;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-10) 0;
  color: var(--gray-400);
}
</style>
