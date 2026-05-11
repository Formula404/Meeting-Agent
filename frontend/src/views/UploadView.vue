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
    <div v-if="uploading" class="card">
      <h2 class="card-title">正在解析</h2>
      <p>正在调用 AI 进行结构化提取，请稍候...</p>
      <div class="upload-progress">
        <p class="text-sm text-muted mt-16">文件名：{{ selectedFile?.name }}</p>
      </div>
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
              <th></th>
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
              <td>
                <router-link :to="{ name: 'review', params: { id: r.id } }" class="btn btn-outline btn-sm">查看</router-link>
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
