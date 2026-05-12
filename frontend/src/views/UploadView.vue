<template>
  <div>
    <h1 class="page-title">上传会议纪要</h1>

    <!-- Step 1: File selection -->
    <div
      v-if="!selectedFile"
      class="upload-zone"
      :class="{ dragover: dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
      @click="triggerFileInput"
    >
      <div class="upload-zone-icon">&#128196;</div>
      <div class="upload-zone-text">将 .docx 文件拖拽到此处，或点击选择文件</div>
      <div class="upload-zone-hint">仅支持 .docx 格式</div>
      <input
        ref="fileInput"
        type="file"
        accept=".docx"
        style="display:none"
        @change="onFileChange"
      />
    </div>

    <!-- Step 2: File selected, waiting for confirm -->
    <div v-else-if="!uploading && !resultId" class="card">
      <h2 class="card-title">已选择文件</h2>
      <div class="form-group">
        <label class="form-label">文件名</label>
        <p class="form-input" style="background:#f8fafc;cursor:default">{{ selectedFile.name }}</p>
      </div>
      <div class="form-group">
        <label class="form-label">文件大小</label>
        <p class="form-input" style="background:#f8fafc;cursor:default">{{ formatSize(selectedFile.size) }}</p>
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

    <!-- Step 4: Done -->
    <div v-if="resultId" class="flash flash-success mt-16 flex-between">
      <span>解析完成！</span>
      <router-link :to="{ name: 'review', params: { id: resultId } }" class="btn btn-primary btn-sm">
        前往审查修改
      </router-link>
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
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in recentList" :key="r.id">
              <td class="truncate" style="max-width:160px">{{ r.original_filename }}</td>
              <td>
                <span class="badge" :class="r.status === 'pushed' ? 'badge-pushed' : 'badge-draft'">
                  {{ r.status === 'pushed' ? '已推送' : '草稿' }}
                </span>
              </td>
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
import api from '../api/index.js'

const fileInput = ref(null)
const dragging = ref(false)
const uploading = ref(false)
const error = ref('')
const resultId = ref(null)
const selectedFile = ref(null)
const recentList = ref([])
const deletingId = ref(null)

onMounted(() => {
  api.listResults().then((list) => { recentList.value = list }).catch(() => {})
})

function triggerFileInput() { fileInput.value?.click() }

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) setFile(file)
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) setFile(file)
  // Reset so re-selecting the same file triggers change again
  e.target.value = ''
}

function setFile(file) {
  if (!file.name.endsWith('.docx')) {
    error.value = '仅支持 .docx 格式'
    return
  }
  error.value = ''
  resultId.value = null
  selectedFile.value = file
}

function cancelFile() {
  selectedFile.value = null
  error.value = ''
}

async function startExtract() {
  if (!selectedFile.value) return
  uploading.value = true
  error.value = ''
  resultId.value = null
  try {
    const data = await api.uploadFile(selectedFile.value)
    resultId.value = data.id
    selectedFile.value = null
    recentList.value = await api.listResults()
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
</style>
