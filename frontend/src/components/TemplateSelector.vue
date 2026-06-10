<template>
  <div class="template-selector">
    <div class="template-selector-header">
      <label class="form-label" style="margin-bottom:0">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
        纪要模板
        <span class="text-xs text-muted" style="font-weight:400;text-transform:none">（可选，不选则使用默认格式）</span>
      </label>
      <router-link to="/templates" class="btn btn-ghost btn-sm" style="flex-shrink:0">管理模板</router-link>
    </div>
    <div class="template-select-row">
      <div class="template-select-wrapper">
        <select class="form-select" v-model="selectedId" @change="onChange">
          <option value="">— 默认模板 —</option>
          <option v-for="t in templates" :key="t.id" :value="t.id">
            {{ t.name }}{{ t.is_builtin ? ' ⭐' : '' }}
          </option>
        </select>
      </div>
      <button
        v-if="selectedTemplate"
        class="btn btn-outline btn-sm"
        @click="showPreview = true"
        title="预览模板"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
        预览
      </button>
    </div>

    <!-- Preview dialog -->
    <div v-if="showPreview && selectedTemplate" class="dialog-mask" @click.self="showPreview = false">
      <div class="dialog-card preview-card">
        <div class="dialog-title" style="color:var(--gray-800)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          {{ selectedTemplate.name }}
        </div>
        <div class="preview-body">
          <div class="preview-section">
            <div class="preview-label">描述</div>
            <div class="preview-value">{{ selectedTemplate.description || '无描述' }}</div>
          </div>
          <div class="preview-section">
            <div class="preview-label">风格要求</div>
            <pre class="preview-prompt">{{ selectedTemplate.style_prompt || '无' }}</pre>
          </div>
          <div class="preview-section">
            <div class="preview-label">示例输出</div>
            <pre class="preview-sample">{{ formatSample(selectedTemplate.sample_output) }}</pre>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="btn btn-outline btn-sm" @click="showPreview = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../api/index.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const templates = ref([])
const showPreview = ref(false)
const selectedId = ref(props.modelValue)

const selectedTemplate = computed(() =>
  templates.value.find((t) => t.id === selectedId.value)
)

onMounted(async () => {
  try {
    templates.value = await api.listTemplates()
  } catch (_) {}
})

watch(() => props.modelValue, (v) => {
  selectedId.value = v
})

function onChange() {
  emit('update:modelValue', selectedId.value)
}

function formatSample(sample) {
  if (!sample || sample === '{}') return '无示例输出'
  return String(sample).substring(0, 500) + (String(sample).length > 500 ? '...' : '')
}
</script>

<style scoped>
.template-selector {
  margin-bottom: var(--space-4);
}

.template-selector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.template-select-row {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.template-select-wrapper {
  flex: 1;
}

.template-select-wrapper .form-select {
  width: 100%;
}

.preview-card {
  width: min(560px, 100%);
  max-height: 80vh;
  overflow-y: auto;
}

.preview-body {
  margin-top: var(--space-3);
}

.preview-section {
  margin-bottom: var(--space-3);
}

.preview-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--gray-500);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: var(--space-1);
}

.preview-value {
  font-size: var(--text-sm);
  color: var(--gray-700);
  line-height: var(--leading-relaxed);
}

.preview-prompt {
  font-size: var(--text-xs);
  color: var(--gray-600);
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  white-space: pre-wrap;
  line-height: var(--leading-relaxed);
  max-height: 200px;
  overflow-y: auto;
  font-family: inherit;
}

.preview-sample {
  font-size: var(--text-sm);
  color: var(--gray-700);
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  white-space: pre-wrap;
  line-height: var(--leading-relaxed);
  max-height: 240px;
  overflow-y: auto;
  font-family: inherit;
}
</style>
