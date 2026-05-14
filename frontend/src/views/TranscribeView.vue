<template>
  <div>
    <div class="review-header">
      <h1 class="page-title" style="margin-bottom:0">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:8px">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
        <template v-if="isEditMode">编辑转录结果</template>
        <template v-else>录音转文字</template>
      </h1>
      <router-link to="/" class="btn btn-ghost btn-sm" style="align-self:flex-start">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"/>
          <polyline points="12 19 5 12 12 5"/>
        </svg>
        返回首页
      </router-link>
    </div>

    <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>
    <div v-if="error" class="flash flash-error">{{ error }}</div>

    <!-- ══════════════════════════════════════════════════════════════
         Step 1: Upload + Custom Prompt (only when not editing)
         ══════════════════════════════════════════════════════════════ -->
    <template v-if="!isEditMode && !processing && !resultId">
      <div class="card">
        <h2 class="card-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          上传录音转文字文件
        </h2>
        <div
          class="upload-zone"
          :class="{ dragover: dragging }"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
          @click="triggerFileInput"
        >
          <div class="upload-zone-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="18" x2="12" y2="12"/>
              <line x1="9" y1="15" x2="12" y2="12"/>
              <line x1="15" y1="15" x2="12" y2="12"/>
            </svg>
          </div>
          <div class="upload-zone-text">拖拽或点击选择转录文件</div>
          <div class="upload-zone-hint">支持 .docx 或 .txt 格式</div>
          <input
            ref="fileInput"
            type="file"
            accept=".docx,.txt"
            style="display:none"
            @change="onFileChange"
          />
        </div>
        <div v-if="selectedFile" class="file-info-row mt-4">
          <div class="file-info">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <span>{{ selectedFile.name }}</span>
            <span class="file-size">（{{ formatSize(selectedFile.size) }}）</span>
          </div>
          <button class="btn btn-ghost btn-sm" @click.stop="selectedFile = null">更换</button>
        </div>
      </div>

      <div class="card">
        <h2 class="card-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          自定义提取要求
        </h2>
        <div class="form-group">
          <label class="form-label">请输入您希望 AI 如何提取会议纪要的提示词</label>
          <textarea
            class="form-textarea"
            v-model="customPrompt"
            rows="6"
            placeholder="例如：请提取本次会议的主要讨论内容、决策事项和待办任务，按以下格式组织：1. 会议概况 2. 讨论要点 3. 决策事项 4. 后续行动..."
          ></textarea>
        </div>
        <div class="flex gap-2 mt-4">
          <button class="btn btn-primary" @click="startTranscribe" :disabled="!selectedFile">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            开始提取
          </button>
          <button class="btn btn-outline" @click="clearAll">清除</button>
        </div>
      </div>
    </template>

    <!-- ══════════════════════════════════════════════════════════════
         Step 2: Processing
         ══════════════════════════════════════════════════════════════ -->
    <div v-if="processing" class="card">
      <div class="extracting-state">
        <div class="spinner">
          <div class="spinner-dot"></div>
          <div class="spinner-dot"></div>
          <div class="spinner-dot"></div>
        </div>
        <div class="extracting-title">AI 正在提取会议纪要...</div>
        <div class="extracting-file">{{ selectedFile?.name }}</div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════
         Step 3: Result Editor
         ══════════════════════════════════════════════════════════════ -->
    <template v-if="resultData">
      <!-- Result info bar -->
      <div class="card" style="padding:var(--space-4) var(--space-5)">
        <div class="flex-between">
          <div class="flex gap-2" style="align-items:center">
            <span class="badge" :class="resultStatus === 'pushed' ? 'badge-pushed' : 'badge-draft'">
              {{ resultStatus === 'pushed' ? '✓ 已推送' : '○ 草稿' }}
            </span>
            <span class="text-sm text-muted">文件：{{ resultFilename }}</span>
          </div>
          <div class="flex gap-2">
            <button class="btn btn-outline btn-sm" @click="exportDocx" :disabled="exporting">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              {{ exporting ? '导出中...' : '导出 Word' }}
            </button>
            <button
              class="btn btn-success btn-sm"
              @click="pushResult"
              :disabled="pushing"
            >
              {{ pushing ? '推送中...' : '推送到企业微信' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Meeting content -->
      <div class="card">
        <label class="form-label">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          会议纪要内容
        </label>
        <textarea
          class="form-textarea"
          v-model="resultData.meeting"
          rows="12"
        ></textarea>
      </div>

      <!-- Meeting info fields -->
      <div class="card">
        <div class="schedule-grid">
          <div class="form-group">
            <label class="form-label">会议时间</label>
            <input class="form-input" v-model="resultData.meeting_date" placeholder="YYYY-MM-DD HH:mm" />
          </div>
          <div class="form-group">
            <label class="form-label">推送用户</label>
            <TagInput
              v-model="resultData.push_user"
              :suggestions="userSuggestions"
              :invalidValues="[]"
              placeholder="输入用户姓名"
            />
          </div>
          <div class="form-group">
            <label class="form-label">推送部门</label>
            <TagInput
              v-model="resultData.push_dept"
              :suggestions="deptSuggestions"
              :invalidValues="[]"
              placeholder="输入部门名称"
            />
          </div>
        </div>
      </div>

      <!-- Schedules -->
      <div class="card">
        <div class="flex-between mb-4">
          <span class="card-title" style="margin:0;border:none;padding:0">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            日程安排
          </span>
          <div class="flex gap-2">
            <button v-if="resultData.schedules?.length" type="button" class="btn btn-ghost btn-sm btn-danger-text" @click="clearSchedules">清空全部</button>
            <button type="button" class="btn btn-outline btn-sm" @click="addSchedule">+ 添加日程</button>
          </div>
        </div>

        <div v-for="(item, idx) in resultData.schedules" :key="idx">
          <ScheduleEditor
            :item="item"
            :index="idx"
            :userSuggestions="userSuggestions"
            :invalidOwnerTags="[]"
            @update="updateSchedule(idx, $event)"
            @remove="removeSchedule(idx)"
          />
        </div>

        <div v-if="!resultData.schedules?.length" class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <div>暂无日程安排</div>
        </div>
      </div>

      <!-- Save button -->
      <div class="action-bar">
        <button class="btn btn-primary" @click="saveResult" :disabled="saving">
          <svg v-if="!saving" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          {{ saving ? '保存中...' : '保存修改' }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/index.js'
import TagInput from '../components/TagInput.vue'
import ScheduleEditor from '../components/ScheduleEditor.vue'

const route = useRoute()
const router = useRouter()

const isEditMode = computed(() => !!route.params.id)

// Upload state
const fileInput = ref(null)
const dragging = ref(false)
const selectedFile = ref(null)
const customPrompt = ref('')

// Processing state
const processing = ref(false)
const error = ref('')
const flash = ref('')
const flashType = ref('flash-info')

// Result state
const resultId = ref(null)
const resultData = ref(null)
const resultStatus = ref('draft')
const resultFilename = ref('')
const saving = ref(false)
const exporting = ref(false)
const pushing = ref(false)

const userSuggestions = ref([])
const deptSuggestions = ref([])

onMounted(async () => {
  // Load users/depts for tag input
  try {
    const [users, depts] = await Promise.all([
      api.listUsers().catch(() => []),
      api.listDepartments().catch(() => []),
    ])
    userSuggestions.value = users.map((u) => ({ label: u.name, value: u.name }))
    deptSuggestions.value = depts.map((d) => ({ label: d.name, value: d.name }))
  } catch (_) {}

  // If editing existing result
  if (isEditMode.value) {
    await loadExistingResult(route.params.id)
  }
})

async function loadExistingResult(id) {
  try {
    const record = await api.getTranscription(id)
    resultId.value = id
    resultFilename.value = record.original_filename
    resultStatus.value = record.status
    resultData.value = normalizeSchedules(record.result_json)
  } catch (e) {
    error.value = `加载失败: ${e.message}`
  }
}

function normalizeSchedules(data) {
  const schedules = (data.schedules || []).map((s) => ({
    ...s,
    owner: Array.isArray(s.owner ?? []) ? s.owner : [s.owner].filter(Boolean),
  }))
  return { ...data, schedules }
}

// File handling
function triggerFileInput() { fileInput.value?.click() }

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) setFile(file)
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) setFile(file)
  e.target.value = ''
}

function setFile(file) {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (ext !== '.docx' && ext !== '.txt') {
    error.value = '仅支持 .docx 或 .txt 格式'
    return
  }
  error.value = ''
  selectedFile.value = file
}

function clearAll() {
  selectedFile.value = null
  customPrompt.value = ''
  error.value = ''
}

// Start transcription
async function startTranscribe() {
  if (!selectedFile.value) return
  processing.value = true
  error.value = ''
  try {
    const data = await api.transcribeFile(selectedFile.value, customPrompt.value)
    resultId.value = data.id
    resultFilename.value = data.original_filename
    resultStatus.value = 'draft'
    resultData.value = normalizeSchedules(data.result)
    // Update URL to edit mode without reload
    router.replace({ name: 'transcribe-edit', params: { id: data.id } })
  } catch (e) {
    error.value = `提取失败: ${e.message}`
  } finally {
    processing.value = false
  }
}

// Schedule management
function updateSchedule(idx, { field, value }) {
  resultData.value.schedules[idx][field] = value
}

function removeSchedule(idx) {
  resultData.value.schedules.splice(idx, 1)
}

function addSchedule() {
  if (!resultData.value.schedules) {
    resultData.value.schedules = []
  }
  resultData.value.schedules.push({
    title: '',
    owner: [],
    start_time: '',
    end_time: '',
    description: '',
  })
}

function clearSchedules() {
  if (!confirm('确认清空全部日程？')) return
  resultData.value.schedules = []
}

// Save
async function saveResult() {
  if (!resultId.value) return
  saving.value = true
  flash.value = ''
  try {
    await api.updateTranscription(resultId.value, { ...resultData.value })
    flash.value = '保存成功'
    flashType.value = 'flash-success'
  } catch (e) {
    flash.value = `保存失败: ${e.message}`
    flashType.value = 'flash-error'
  } finally {
    saving.value = false
  }
}

// Export docx
async function exportDocx() {
  if (!resultId.value) return
  exporting.value = true
  flash.value = ''
  try {
    // Save first, then export
    await api.updateTranscription(resultId.value, { ...resultData.value })
    await api.exportTranscriptionDocx(resultId.value)
    flash.value = 'Word 文件已开始下载'
    flashType.value = 'flash-success'
  } catch (e) {
    flash.value = `导出失败: ${e.message}`
    flashType.value = 'flash-error'
  } finally {
    exporting.value = false
  }
}

// Push to WeCom
async function pushResult() {
  if (!resultId.value) return
  // Validate
  const meetingText = (resultData.value.meeting || '').trim()
  const hasTarget = (resultData.value.push_user?.length || 0) > 0 ||
                    (resultData.value.push_dept?.length || 0) > 0
  if (!hasTarget) {
    error.value = '请至少填写推送用户或推送部门'
    return
  }
  if (!meetingText) {
    error.value = '会议纪要内容不能为空'
    return
  }

  pushing.value = true
  flash.value = ''
  error.value = ''
  try {
    // Save first, then push
    await api.updateTranscription(resultId.value, { ...resultData.value })
    await api.pushTranscription(resultId.value)
    flash.value = '推送成功！消息和日程已发送到企业微信'
    flashType.value = 'flash-success'
    resultStatus.value = 'pushed'
  } catch (e) {
    flash.value = `推送失败: ${e.message}`
    flashType.value = 'flash-error'
  } finally {
    pushing.value = false
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8) 0;
  color: var(--gray-400);
  font-size: var(--text-sm);
}

.empty-state svg {
  opacity: 0.5;
}
</style>
