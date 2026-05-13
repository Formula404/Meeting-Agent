<template>
  <div>
    <h1 class="page-title">上传会议纪要</h1>

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
        <div class="upload-zone-icon">&#128196;</div>
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
        <div class="upload-zone-icon">&#128196;</div>
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
      <h2 class="card-title">已选择文件</h2>
      <div class="form-group">
        <label class="form-label">会议文件（.docx）</label>
        <p class="form-input" style="background:#f8fafc;cursor:default;display:flex;align-items:center;justify-content:space-between">
          <span>{{ selectedFile.name }}（{{ formatSize(selectedFile.size) }}）</span>
          <button class="btn btn-outline btn-sm" @click.stop="cancelDocx">更换</button>
        </p>
      </div>
      <div class="form-group">
        <label class="form-label">附件（.pdf）<span class="text-muted text-sm"> （可选）</span></label>
        <div v-if="pdfFile" class="form-input" style="background:#f8fafc;cursor:default;display:flex;align-items:center;justify-content:space-between">
          <span>{{ pdfFile.name }}（{{ formatSize(pdfFile.size) }}）</span>
          <div style="display:flex;gap:4px">
            <button class="btn btn-outline btn-sm" @click.stop="triggerPdfInput">更换</button>
            <button class="btn btn-outline btn-sm" style="color:#dc2626" @click.stop="pdfFile = null">移除</button>
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
      <div class="flex gap-8 mt-16">
        <button class="btn btn-primary" @click="startExtract">开始解析</button>
        <button class="btn btn-outline" @click="cancelFile">重新选择</button>
      </div>
    </div>

    <!-- Step 3: Extracting -->
    <div v-if="uploading" class="card" style="position:relative;min-height:140px">
      <div class="loader">
        <div class="justify-content-center jimu-primary-loading"></div>
      </div>
      <p class="text-sm text-muted extracting-hint">
        AI解析中，请稍后...<br />文件名：{{ selectedFile?.name }}
      </p>
    </div>

    <div v-if="error" class="flash flash-error mt-16">{{ error }}</div>

    <!-- History -->
    <div v-if="recentList.length" class="card mt-20">
      <h2 class="card-title">最近解析记录</h2>
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
                  {{ r.status === 'pushed' ? '已推送' : '草稿' }}
                </span>
              </td>
              <td class="text-sm text-muted">{{ r.pdf_filename ? '有' : '—' }}</td>
              <td class="text-sm text-muted">{{ formatTime(r.created_at) }}</td>
              <td style="white-space:nowrap">
                <div class="row-actions">
                  <router-link :to="{ name: 'review', params: { id: r.id } }" class="btn btn-outline btn-sm">查看</router-link>
                  <button class="btn btn-outline btn-sm" style="color:#dc2626" @click="handleDelete(r)" :disabled="deletingId === r.id">{{ deletingId === r.id ? '删除中...' : '删除' }}</button>
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
.loader {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
}

.jimu-primary-loading:before,
.jimu-primary-loading:after {
  position: absolute;
  top: 0;
  content: '';
}

.jimu-primary-loading:before {
  left: -19.992px;
}

.jimu-primary-loading:after {
  left: 19.992px;
  -webkit-animation-delay: 0.32s !important;
  animation-delay: 0.32s !important;
}

.jimu-primary-loading:before,
.jimu-primary-loading:after,
.jimu-primary-loading {
  background: #076fe5;
  -webkit-animation: loading-keys-app-loading 0.8s infinite ease-in-out;
  animation: loading-keys-app-loading 0.8s infinite ease-in-out;
  width: 13.6px;
  height: 32px;
}

.jimu-primary-loading {
  text-indent: -9999em;
  margin: auto;
  position: absolute;
  right: calc(50% - 6.8px);
  top: calc(50% - 16px);
  -webkit-animation-delay: 0.16s !important;
  animation-delay: 0.16s !important;
}

@-webkit-keyframes loading-keys-app-loading {
  0%, 80%, 100% { opacity: .75; box-shadow: 0 0 #076fe5; height: 32px; }
  40% { opacity: 1; box-shadow: 0 -8px #076fe5; height: 40px; }
}

@keyframes loading-keys-app-loading {
  0%, 80%, 100% { opacity: .75; box-shadow: 0 0 #076fe5; height: 32px; }
  40% { opacity: 1; box-shadow: 0 -8px #076fe5; height: 40px; }
}

.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.extracting-hint {
  position: absolute;
  bottom: 5px;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
}

/* Two-column upload zones on desktop */
.upload-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

@media (min-width: 640px) {
  .upload-row {
    grid-template-columns: 1fr 1fr;
  }
}

.upload-zone {
  border: 2px dashed #cbd5e1;
  border-radius: 10px;
  padding: 36px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafbfc;
}

@media (min-width: 640px) {
  .upload-zone { padding: 48px 24px; }
}

.upload-zone:hover,
.upload-zone.dragover {
  border-color: #2563eb;
  background: #eff6ff;
}

.upload-zone-pdf {
  border-color: #d1d5db;
}

.upload-zone-pdf:hover,
.upload-zone-pdf.dragover {
  border-color: #16a34a;
  background: #f0fdf4;
}

.upload-zone-icon {
  font-size: 36px;
  margin-bottom: 8px;
  opacity: 0.4;
}

@media (min-width: 640px) {
  .upload-zone-icon { font-size: 40px; margin-bottom: 12px; }
}

.upload-zone-text {
  font-size: 14px;
  color: #64748b;
}

@media (min-width: 640px) {
  .upload-zone-text { font-size: 15px; }
}

.upload-zone-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

/* Inline upload zone inside the "selected" card */
.upload-zone-inline {
  padding: 16px;
  border-style: dashed;
}
</style>
