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
        {{ isEditMode ? '编辑模板' : '创建模板' }}
      </h1>
      <router-link to="/templates" class="btn btn-ghost btn-sm" style="align-self:flex-start">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"/>
          <polyline points="12 19 5 12 12 5"/>
        </svg>
        返回
      </router-link>
    </div>

    <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>
    <div v-if="error" class="flash flash-error">{{ error }}</div>

    <div class="card">
      <!-- Name -->
      <div class="form-group">
        <label class="form-label">模板名称 <span class="text-danger">*</span></label>
        <input class="form-input" v-model="form.name" placeholder="例：工程部会议纪要模板" />
      </div>

      <!-- Description -->
      <div class="form-group">
        <label class="form-label">描述 <span class="text-xs text-muted">（可选）</span></label>
        <textarea class="form-textarea" v-model="form.description" placeholder="简述此模板的适用场景和特点" rows="2"></textarea>
      </div>

      <!-- Style prompt -->
      <div class="form-group">
        <label class="form-label">
          风格提示词
          <span class="text-xs text-muted">（追加到 AI 提示词末尾，控制会议纪要正文的写作风格）</span>
        </label>

        <div class="prompt-toolbar">
          <span class="prompt-toolbar-hint">直接编写，或上传示例会议纪要由 AI 自动分析</span>
        </div>

        <textarea
          class="form-textarea prompt-textarea"
          v-model="form.style_prompt"
          placeholder="例：&#10;1. 正文结构分「上周工作回顾」「本周工作计划」「需协调事项」三部分&#10;2. 每个部分使用 ## 二级标题&#10;3. 具体事项使用 - 项目符号列表&#10;4. 语言要求简洁正式"
          rows="8"
        ></textarea>
      </div>

      <!-- Upload docx for AI analysis -->
      <div class="docx-upload-area">
        <div class="upload-section-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="16 16 12 12 8 16"/>
            <line x1="12" y1="12" x2="12" y2="21"/>
            <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
            <polyline points="16 16 12 12 8 16"/>
          </svg>
          上传示例文档自动生成
        </div>
        <div class="upload-section-desc">
          上传一份已写好的会议纪要 .docx，AI 会自动分析其结构、语言风格、条目化程度和待办表述方式，生成风格提示词填入上方文本框。
        </div>
        <div
          class="upload-zone upload-zone-inline"
          :class="{ dragover: dragging }"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
          @click="triggerFileInput"
        >
          <div v-if="!analyzing" class="upload-zone-text">
            {{ selectedFile ? selectedFile.name : '点击或拖拽上传 .docx 示例文件' }}
          </div>
          <div v-else class="upload-zone-text">
            <span class="spinner-inline"></span>
            AI 分析中...
          </div>
          <input ref="fileInput" type="file" accept=".docx" style="display:none" @change="onFileChange" />
        </div>
        <div v-if="selectedFile && !analyzing" class="flex gap-2 mt-2">
          <button class="btn btn-primary btn-sm" @click="analyzeDocx">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            AI 分析
          </button>
          <button class="btn btn-ghost btn-sm" @click="clearFile">清除文件</button>
        </div>
        <div v-if="analyzeSuccess" class="flash flash-success mt-2" style="margin-bottom:0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          AI 分析完成！风格提示词已填入上方文本框，请审阅并优化。
        </div>
      </div>

      <!-- Sample output (auto-filled from uploaded docx) -->
      <div v-if="form.sample_output" class="form-group" style="margin-top:var(--space-4)">
        <label class="form-label">
          示例输出
          <span class="text-xs text-muted">（上传文档的内容，用于前端预览模板效果）</span>
        </label>
        <pre class="sample-preview">{{ form.sample_output }}</pre>
      </div>

      <!-- Submit -->
      <div class="action-bar">
        <button class="btn btn-primary" @click="handleSave" :disabled="saving || !form.name.trim()">
          {{ saving ? '保存中...' : '保存模板' }}
        </button>
        <router-link to="/templates" class="btn btn-outline">取消</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/index.js'

const route = useRoute()
const router = useRouter()

const isEditMode = computed(() => !!route.params.id && route.name === 'template-edit')

const form = ref({
  name: '',
  description: '',
  style_prompt: '',
  sample_output: '{}',
})

const flash = ref('')
const flashType = ref('flash-info')
const error = ref('')
const saving = ref(false)

// File upload for AI analysis
const fileInput = ref(null)
const dragging = ref(false)
const selectedFile = ref(null)
const analyzing = ref(false)
const analyzeSuccess = ref(false)

onMounted(async () => {
  if (isEditMode.value) {
    try {
      const data = await api.getTemplate(route.params.id)
      form.value.name = data.name || ''
      form.value.description = data.description || ''
      form.value.style_prompt = data.style_prompt || ''
      form.value.sample_output = data.sample_output || '{}'
    } catch (e) {
      error.value = `加载模板失败: ${e.message}`
    }
  }
})

// File handling
function triggerFileInput() { fileInput.value?.click() }

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) setFile(file)
}

function onFileChange(e) {
  const f = e.target.files[0]
  if (f) setFile(f)
  e.target.value = ''
}

function setFile(file) {
  if (!file.name.endsWith('.docx')) {
    error.value = '仅支持 .docx 格式'
    return
  }
  error.value = ''
  selectedFile.value = file
  analyzeSuccess.value = false
}

function clearFile() {
  selectedFile.value = null
  analyzeSuccess.value = false
  error.value = ''
}

async function analyzeDocx() {
  if (!selectedFile.value) return
  analyzing.value = true
  error.value = ''
  analyzeSuccess.value = false
  try {
    const data = await api.generateStylePrompt(selectedFile.value)
    form.value.style_prompt = data.style_prompt
    form.value.sample_output = data.sample_output || ''
    analyzeSuccess.value = true
  } catch (e) {
    error.value = `AI 分析失败: ${e.message}`
  } finally {
    analyzing.value = false
  }
}

// Save
async function handleSave() {
  if (!form.value.name.trim()) return
  saving.value = true
  flash.value = ''
  error.value = ''

  const body = {
    name: form.value.name.trim(),
    description: form.value.description.trim(),
    style_prompt: form.value.style_prompt.trim(),
    sample_output: form.value.sample_output.trim() || '{}',
  }

  try {
    if (isEditMode.value) {
      await api.updateTemplate(route.params.id, body)
      flash.value = '模板已更新'
      flashType.value = 'flash-success'
    } else {
      const created = await api.createTemplate(body)
      router.push({ name: 'template-detail', params: { id: created.id } })
    }
  } catch (e) {
    error.value = `保存失败: ${e.message}`
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.text-danger {
  color: var(--danger);
}

.prompt-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.prompt-toolbar-hint {
  font-size: var(--text-xs);
  color: var(--gray-400);
}

.prompt-textarea {
  min-height: 180px;
  font-family: inherit;
  line-height: var(--leading-relaxed);
}

.sample-preview {
  font-size: var(--text-sm);
  color: var(--gray-700);
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  white-space: pre-wrap;
  line-height: var(--leading-relaxed);
  font-family: inherit;
  max-height: 300px;
  overflow-y: auto;
}

/* Upload area for docx analysis */
.docx-upload-area {
  margin-top: var(--space-3);
  padding: var(--space-4);
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
}

.upload-section-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--gray-700);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.upload-section-desc {
  font-size: var(--text-xs);
  color: var(--gray-400);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-3);
}

.upload-zone-inline {
  padding: var(--space-4);
  cursor: pointer;
}

.upload-zone-inline.dragover {
  border-color: var(--primary-400);
  background: var(--primary-50);
}

.form-hint {
  display: block;
  font-size: var(--text-xs);
  color: var(--gray-400);
  margin-top: 4px;
  line-height: var(--leading-relaxed);
}

.spinner-inline {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  vertical-align: middle;
  margin-right: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.flash-success {
  font-size: var(--text-xs);
  padding: var(--space-2) var(--space-3);
}
</style>
