<template>
  <div>
    <h1 class="page-title">上传会议记录</h1>

    <div
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

    <div v-if="uploading" class="upload-progress card">
      <p>正在上传并解析...</p>
      <p class="text-sm text-muted mt-16">正在调用 AI 进行结构化提取，请稍候</p>
    </div>

    <div v-if="error" class="flash flash-error mt-16">{{ error }}</div>

    <div v-if="resultId" class="flash flash-success mt-16 flex-between">
      <span>解析完成！</span>
      <router-link :to="{ name: 'review', params: { id: resultId } }" class="btn btn-primary btn-sm">
        前往审查修改
      </router-link>
    </div>

    <div v-if="recentList.length" class="card mt-20">
      <h2 class="card-title">最近解析记录</h2>
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
            <td>{{ r.original_filename }}</td>
            <td><span class="badge" :class="r.status === 'pushed' ? 'badge-pushed' : 'badge-draft'">{{ r.status === 'pushed' ? '已推送' : '草稿' }}</span></td>
            <td class="text-sm text-muted">{{ formatTime(r.created_at) }}</td>
            <td>
              <router-link :to="{ name: 'review', params: { id: r.id } }" class="btn btn-outline btn-sm">查看</router-link>
            </td>
          </tr>
        </tbody>
      </table>
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
const recentList = ref([])

onMounted(() => {
  api.listResults().then((list) => { recentList.value = list }).catch(() => {})
})

function triggerFileInput() { fileInput.value?.click() }

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) upload(file)
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) upload(file)
}

async function upload(file) {
  if (!file.name.endsWith('.docx')) {
    error.value = '仅支持 .docx 格式'
    return
  }
  uploading.value = true
  error.value = ''
  resultId.value = null
  try {
    const data = await api.uploadFile(file)
    resultId.value = data.id
    recentList.value = await api.listResults()
  } catch (e) {
    error.value = e.message
  } finally {
    uploading.value = false
  }
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts + 'Z').toLocaleString('zh-CN', { hour12: false })
}
</script>
