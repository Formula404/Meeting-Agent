<template>
  <div>
    <h1 class="page-title">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:8px">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      上传会议纪要
    </h1>

    <!-- 录音转文字入口 -->
    <div class="card transcription-entry">
      <div class="transcription-entry-content">
        <div class="transcription-entry-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        </div>
        <div>
          <div class="transcription-entry-title">会议录音转文字处理</div>
          <div class="transcription-entry-desc">上传录音转写文档，使用自定义提示词让 AI 提取结构化会议纪要</div>
        </div>
        <router-link to="/transcribe" class="btn btn-primary">开始处理</router-link>
      </div>
    </div>

    <!-- Step 1: File selection -->
    <div v-if="!selectedFile" class="upload-row">
      <div
        class="upload-zone upload-zone-docx"
        :class="{ dragover: draggingDocx }"
        @dragover.prevent="draggingDocx = true"
        @dragleave.prevent="draggingDocx = false"
        @drop.prevent="onDropDocx"
        @click="triggerDocxInput"
      >
        <div class="upload-zone-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </div>
        <div class="upload-zone-text">拖拽或点击选择 .docx 文件</div>
        <div class="upload-zone-hint">必选，仅支持 .docx 格式</div>
        <input
          ref="docxInput"
          type="file"
          accept=".docx"
          style="display:none"
          @change="onDocxChange"
        />
      </div>

      <div
        class="upload-zone upload-zone-pdf"
        :class="{ dragover: draggingPdf }"
        @dragover.prevent="draggingPdf = true"
        @dragleave.prevent="draggingPdf = false"
        @drop.prevent="onDropPdf"
        @click="triggerPdfInput"
      >
        <div class="upload-zone-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <path d="M9 15h6"/>
            <path d="M12 12v6"/>
          </svg>
        </div>
        <div class="upload-zone-text">拖拽或点击选择 PDF 文件</div>
        <div class="upload-zone-hint">可选，仅支持 .pdf 格式</div>
        <input
          ref="pdfInput"
          type="file"
          accept=".pdf"
          style="display:none"
          @change="onPdfChange"
        />
      </div>
    </div>

    <!-- Step 2: File selected, waiting for confirm -->
    <div v-else-if="!uploading && !resultId" class="card">
      <h2 class="card-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        已选择文件
      </h2>
      <div class="form-group">
        <label class="form-label">会议文件（.docx）</label>
        <div class="file-info-row">
          <div class="file-info">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <span>{{ selectedFile.name }}</span>
            <span class="file-size">（{{ formatSize(selectedFile.size) }}）</span>
          </div>
          <button class="btn btn-ghost btn-sm" @click.stop="cancelDocx">更换</button>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">附件（.pdf）<span class="text-muted text-xs">（可选）</span></label>
        <div v-if="pdfFile" class="file-info-row">
          <div class="file-info">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <path d="M9 15h6"/>
              <path d="M12 12v6"/>
            </svg>
            <span>{{ pdfFile.name }}</span>
            <span class="file-size">（{{ formatSize(pdfFile.size) }}）</span>
          </div>
          <div class="flex gap-1">
            <button class="btn btn-ghost btn-sm" @click.stop="triggerPdfInput">更换</button>
            <button class="btn btn-ghost btn-sm btn-danger-text" @click.stop="pdfFile = null">移除</button>
          </div>
        </div>
        <div v-else>
          <div
            class="upload-zone upload-zone-inline"
            :class="{ dragover: draggingPdf }"
            @dragover.prevent="draggingPdf = true"
            @dragleave.prevent="draggingPdf = false"
            @drop.prevent="onDropPdf"
            @click="triggerPdfInput"
          >
            <div class="upload-zone-text">点击或拖拽选择 PDF 附件</div>
          </div>
        </div>
      </div>
      <div class="flex gap-2 mt-5">
        <button class="btn btn-primary" @click="startExtract">开始解析</button>
        <button class="btn btn-outline" @click="cancelFile">重新选择</button>
      </div>
    </div>

    <!-- Step 3: Extracting -->
    <div v-if="uploading" class="card">
      <div class="extracting-state">
        <div class="spinner">
          <div class="spinner-dot"></div>
          <div class="spinner-dot"></div>
          <div class="spinner-dot"></div>
        </div>
        <div class="extracting-title">AI 正在解析中...</div>
        <div class="extracting-file">{{ selectedFile?.name }}</div>
      </div>
    </div>

    <div v-if="error" class="flash flash-error mt-4">{{ error }}</div>

    <!-- History -->
    <div v-if="recentList.length" class="card mt-6">
      <h2 class="card-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
        最近解析记录
      </h2>
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>状态</th>
              <th>附件</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in recentList" :key="r.id">
              <td class="truncate" style="max-width:140px">{{ r.original_filename }}</td>
              <td>
                <span class="badge" :class="r.status === 'pushed' ? 'badge-pushed' : 'badge-draft'">
                  <span v-if="r.status === 'pushed'">✓</span>
                  <span v-else>○</span>
                  {{ r.status === 'pushed' ? '已推送' : '草稿' }}
                </span>
              </td>
              <td class="text-sm text-muted">{{ r.pdf_filename ? '有' : '—' }}</td>
              <td class="text-sm text-muted">{{ formatTime(r.created_at) }}</td>
              <td>
                <div class="row-actions">
                  <router-link :to="{ name: 'review', params: { id: r.id } }" class="btn btn-outline btn-sm">查看</router-link>
                  <button
                    class="btn btn-ghost btn-sm btn-danger-text"
                    @click="handleDelete(r)"
                    :disabled="deletingId === r.id"
                  >
                    {{ deletingId === r.id ? '删除中...' : '删除' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/index.js'

const router = useRouter()

const docxInput = ref(null)
const pdfInput = ref(null)
const draggingDocx = ref(false)
const draggingPdf = ref(false)
const uploading = ref(false)
const error = ref('')
const resultId = ref(null)
const selectedFile = ref(null)
const pdfFile = ref(null)
const recentList = ref([])
const deletingId = ref(null)

onMounted(() => {
  api.listResults().then((list) => { recentList.value = list }).catch(() => {})
})

function triggerDocxInput() { docxInput.value?.click() }
function triggerPdfInput() { pdfInput.value?.click() }

function onDropDocx(e) {
  draggingDocx.value = false
  const file = e.dataTransfer.files[0]
  if (file) setDocxFile(file)
}

function onDropPdf(e) {
  draggingPdf.value = false
  const file = e.dataTransfer.files[0]
  if (file) setPdfFile(file)
}

function onDocxChange(e) {
  const file = e.target.files[0]
  if (file) setDocxFile(file)
  e.target.value = ''
}

function onPdfChange(e) {
  const file = e.target.files[0]
  if (file) setPdfFile(file)
  e.target.value = ''
}

function setDocxFile(file) {
  if (!file.name.endsWith('.docx')) {
    error.value = '仅支持 .docx 格式'
    return
  }
  error.value = ''
  resultId.value = null
  selectedFile.value = file
}

function setPdfFile(file) {
  if (!file.name.endsWith('.pdf')) {
    error.value = '仅支持 .pdf 格式'
    return
  }
  error.value = ''
  pdfFile.value = file
}

function cancelDocx() {
  selectedFile.value = null
  error.value = ''
}

function cancelFile() {
  selectedFile.value = null
  pdfFile.value = null
  error.value = ''
}

async function startExtract() {
  if (!selectedFile.value) return
  uploading.value = true
  error.value = ''
  resultId.value = null
  try {
    const data = await api.uploadFile(selectedFile.value, pdfFile.value)
    resultId.value = data.id
    selectedFile.value = null
    pdfFile.value = null
    recentList.value = await api.listResults()
    // Auto-navigate to review page
    router.push({ name: 'review', params: { id: data.id } })
  } catch (e) {
    error.value = e.message
  } finally {
    uploading.value = false
  }
}

async function handleDelete(record) {
  if (!confirm(`确认删除「${record.original_filename}」的解析记录？`)) return
  const targetId = record?.id ?? record?.result_id
  if (!targetId) {
    error.value = '删除失败: 缺少记录 ID'
    return
  }
  deletingId.value = targetId
  try {
    await api.deleteResult(targetId)
    recentList.value = recentList.value.filter((r) => (r.id ?? r.result_id) !== targetId)
  } catch (e) {
    error.value = `删除失败: ${e.message}`
  } finally {
    deletingId.value = null
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts + 'Z').toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.file-info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--gray-50);
  border: 1.5px solid var(--gray-200);
  border-radius: var(--radius-md);
  gap: 8px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-sm);
  color: var(--gray-700);
  min-width: 0;
  flex: 1;
}

.file-info svg {
  flex-shrink: 0;
  color: var(--primary-500);
}

.file-size {
  color: var(--gray-400);
  white-space: nowrap;
}

.extracting-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-8) 0;
}

.extracting-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--gray-700);
  margin-top: var(--space-4);
}

.extracting-file {
  font-size: var(--text-sm);
  color: var(--gray-400);
  margin-top: var(--space-2);
}

.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.transcription-entry {
  cursor: default;
}

.transcription-entry-content {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.transcription-entry-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-600);
  flex-shrink: 0;
}

.transcription-entry-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--gray-800);
}

.transcription-entry-desc {
  font-size: var(--text-sm);
  color: var(--gray-500);
  margin-top: 2px;
}

.transcription-entry-content .btn {
  margin-left: auto;
}

@media (max-width: 639px) {
  .transcription-entry-content {
    flex-direction: column;
    text-align: center;
  }
  .transcription-entry-content .btn {
    margin-left: 0;
    width: 100%;
  }
}
</style>
