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

    <!-- ══════════════════════════════════════════════════════════════
         方式一：会议录音识别
         ══════════════════════════════════════════════════════════════ -->
    <div class="method-section">
      <div class="method-header">
        <span class="method-badge method-badge-1">方式一</span>
        <span class="method-title">会议录音识别</span>
        <span class="method-desc">上传录音文件，AI 自动转写并提取结构化会议纪要</span>
      </div>
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
            <div class="transcription-entry-desc">上传录音文件，自动输出会议纪要并推送</div>
          </div>
          <router-link to="/transcribe" class="btn btn-primary">开始处理</router-link>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════
         方式二：会议纪要文件上传
         ══════════════════════════════════════════════════════════════ -->
    <div class="method-section">
      <div class="method-header">
        <span class="method-badge method-badge-2">方式二</span>
        <span class="method-title">会议纪要文件上传</span>
        <span class="method-desc">上传已整理好的会议纪要文档（.docx），可选 PDF 材料作为推送附件</span>
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
          <div class="upload-zone-label">
            <div class="upload-zone-text">会议纪要文件（.docx）</div>
            <div class="upload-zone-hint">必选 — 上传已整理好的会议纪要文档，AI 将提取关键信息</div>
          </div>
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
          <div class="upload-zone-label">
            <div class="upload-zone-text">推送附件（.pdf）</div>
            <div class="upload-zone-hint">可选 — 会议材料 PDF，推送至企业微信时随消息一并发送</div>
          </div>
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
          <label class="form-label">会议纪要文件（.docx）</label>
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
          <label class="form-label">推送附件（.pdf）<span class="text-muted text-xs">（可选，推送至企业微信时随消息发送）</span></label>
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

    <!-- History: Extraction records -->
    <div v-if="recentList.length" class="card mt-6">
      <h2 class="card-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
        最近解析记录
        <span class="card-count">{{ recentList.length }}</span>
      </h2>
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>状态</th>
              <th>附件</th>
              <th>操作人</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in paginatedResults" :key="r.id">
              <td class="truncate" style="max-width:140px">{{ r.original_filename }}</td>
              <td>
                <span class="badge" :class="r.status === 'pushed' ? 'badge-pushed' : 'badge-draft'">
                  <span v-if="r.status === 'pushed'">✓</span>
                  <span v-else>○</span>
                  {{ r.status === 'pushed' ? '已推送' : '草稿' }}
                </span>
              </td>
              <td class="text-sm text-muted">{{ r.pdf_filename ? '有' : '—' }}</td>
              <td class="text-sm text-muted">{{ r.operator_name || '—' }}</td>
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
      <!-- Pagination -->
      <div v-if="resultTotalPages > 1" class="pagination-bar">
        <span class="pagination-info">共 {{ recentList.length }} 条，第 {{ resultPage }}/{{ resultTotalPages }} 页</span>
        <div class="pagination-controls">
          <button class="pagination-btn" :disabled="resultPage <= 1" @click="resultPage = resultPage - 1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
          <button
            v-for="p in resultPageNumbers"
            :key="p"
            class="pagination-btn"
            :class="{ active: p === resultPage, ellipsis: p === 0 }"
            :disabled="p === 0"
            @click="resultPage = p"
          >{{ p === 0 ? '...' : p }}</button>
          <button class="pagination-btn" :disabled="resultPage >= resultTotalPages" @click="resultPage = resultPage + 1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- History: Transcription records -->
    <div v-if="transcriptionList.length" class="card mt-4">
      <h2 class="card-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
        最近识别记录
        <span class="card-count">{{ transcriptionList.length }}</span>
      </h2>
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>状态</th>
              <th>操作人</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in paginatedTranscriptions" :key="r.id">
              <td class="truncate" style="max-width:140px">{{ r.original_filename }}</td>
              <td>
                <span class="badge" :class="r.status === 'pushed' ? 'badge-pushed' : 'badge-draft'">
                  <span v-if="r.status === 'pushed'">✓</span>
                  <span v-else>○</span>
                  {{ r.status === 'pushed' ? '已推送' : '草稿' }}
                </span>
              </td>
              <td class="text-sm text-muted">{{ r.operator_name || '—' }}</td>
              <td class="text-sm text-muted">{{ formatTime(r.created_at) }}</td>
              <td>
                <div class="row-actions">
                  <router-link :to="{ name: 'transcribe-edit', params: { id: r.id } }" class="btn btn-outline btn-sm">查看</router-link>
                  <button
                    class="btn btn-ghost btn-sm btn-danger-text"
                    @click="handleDeleteTranscription(r)"
                    :disabled="deletingTransId === r.id"
                  >
                    {{ deletingTransId === r.id ? '删除中...' : '删除' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- Pagination -->
      <div v-if="transTotalPages > 1" class="pagination-bar">
        <span class="pagination-info">共 {{ transcriptionList.length }} 条，第 {{ transPage }}/{{ transTotalPages }} 页</span>
        <div class="pagination-controls">
          <button class="pagination-btn" :disabled="transPage <= 1" @click="transPage = transPage - 1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
          <button
            v-for="p in transPageNumbers"
            :key="p"
            class="pagination-btn"
            :class="{ active: p === transPage }"
            @click="transPage = p"
          >{{ p }}</button>
          <button class="pagination-btn" :disabled="transPage >= transTotalPages" @click="transPage = transPage + 1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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
const transcriptionList = ref([])
const deletingId = ref(null)
const deletingTransId = ref(null)

const PAGE_SIZE = 15

const resultPage = ref(1)
const transPage = ref(1)

const paginatedResults = computed(() => {
  const start = (resultPage.value - 1) * PAGE_SIZE
  return recentList.value.slice(start, start + PAGE_SIZE)
})

const resultTotalPages = computed(() => Math.max(1, Math.ceil(recentList.value.length / PAGE_SIZE)))

const resultPageNumbers = computed(() => {
  const total = resultTotalPages.value
  const current = resultPage.value
  return getPageRange(current, total)
})

const paginatedTranscriptions = computed(() => {
  const start = (transPage.value - 1) * PAGE_SIZE
  return transcriptionList.value.slice(start, start + PAGE_SIZE)
})

const transTotalPages = computed(() => Math.max(1, Math.ceil(transcriptionList.value.length / PAGE_SIZE)))

const transPageNumbers = computed(() => {
  const total = transTotalPages.value
  const current = transPage.value
  return getPageRange(current, total)
})

function getPageRange(current, total) {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  const pages = []
  if (current <= 4) {
    for (let i = 1; i <= 5; i++) pages.push(i)
    pages.push(0, total)
  } else if (current >= total - 3) {
    pages.push(1, 0)
    for (let i = total - 4; i <= total; i++) pages.push(i)
  } else {
    pages.push(1, 0, current - 1, current, current + 1, 0, total)
  }
  return pages
}

function onRecentUpdated() {
  if (resultPage.value > resultTotalPages.value) {
    resultPage.value = resultTotalPages.value
  }
}

function onTransUpdated() {
  if (transPage.value > transTotalPages.value) {
    transPage.value = transTotalPages.value
  }
}

onMounted(() => {
  api.listResults().then((list) => { recentList.value = list }).catch(() => {})
  api.listTranscriptions().then((list) => { transcriptionList.value = list }).catch(() => {})
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
    resultPage.value = 1
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
    onRecentUpdated()
  } catch (e) {
    error.value = `删除失败: ${e.message}`
  } finally {
    deletingId.value = null
  }
}

async function handleDeleteTranscription(record) {
  if (!confirm(`确认删除「${record.original_filename}」的识别记录？`)) return
  const targetId = record?.id ?? record?.result_id
  if (!targetId) {
    error.value = '删除失败: 缺少记录 ID'
    return
  }
  deletingTransId.value = targetId
  try {
    await api.deleteTranscription(targetId)
    transcriptionList.value = transcriptionList.value.filter((r) => (r.id ?? r.result_id) !== targetId)
    onTransUpdated()
  } catch (e) {
    error.value = `删除失败: ${e.message}`
  } finally {
    deletingTransId.value = null
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
/* ── Method Section ────────────────────────────────────────────── */
.method-section {
  margin-bottom: var(--space-5);
}

.method-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}

.method-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}

.method-badge-1 {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  color: var(--primary-700);
}

.method-badge-2 {
  background: linear-gradient(135deg, #d1fae5, #a7f3d0);
  color: #065f46;
}

.method-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--gray-800);
}

.method-desc {
  font-size: var(--text-xs);
  color: var(--gray-400);
  width: 100%;
}

@media (min-width: 640px) {
  .method-desc {
    width: auto;
    margin-left: auto;
    text-align: right;
    font-size: var(--text-xs);
  }
}

/* Upload zone with label layout */
.upload-zone-label {
  position: relative;
  z-index: 1;
}

.upload-zone-label .upload-zone-text {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--gray-700);
}

.upload-zone-label .upload-zone-hint {
  font-size: 11px;
  color: var(--gray-400);
  margin-top: 2px;
}

.upload-zone:hover .upload-zone-label .upload-zone-text {
  color: var(--primary-600);
}

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

@media (max-width: 480px) {
  .file-info-row {
    flex-wrap: wrap;
    padding: 8px 10px;
  }
  .file-info {
    width: 100%;
  }
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
  .transcription-entry-icon {
    width: 44px;
    height: 44px;
  }
  .transcription-entry-title {
    font-size: var(--text-base);
  }
  .transcription-entry-desc {
    font-size: 12px;
  }
}

/* ── Pagination ────────────────────────────────────────────────── */
.card-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-full);
  background: var(--gray-100);
  color: var(--gray-500);
  vertical-align: middle;
  margin-left: 6px;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) 0 0;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.pagination-info {
  font-size: var(--text-xs);
  color: var(--gray-400);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 2px;
}

.pagination-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  padding: 0 6px;
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--gray-600);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
  touch-action: manipulation;
}

.pagination-btn:hover:not(:disabled):not(.active) {
  background: var(--gray-50);
  border-color: var(--gray-300);
}

.pagination-btn.active {
  background: var(--primary-600);
  border-color: var(--primary-600);
  color: #fff;
  font-weight: 600;
}

.pagination-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.pagination-btn.ellipsis {
  border: none;
  background: transparent;
  color: var(--gray-400);
  cursor: default;
  min-width: 24px;
}

.pagination-btn svg {
  display: block;
}

@media (max-width: 480px) {
  .pagination-bar {
    flex-direction: column;
    align-items: center;
  }
  .pagination-btn {
    min-width: 28px;
    height: 28px;
    font-size: 12px;
  }
}
</style>
