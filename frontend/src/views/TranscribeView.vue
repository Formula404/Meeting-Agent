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
         Step 1: Upload (only when not editing)
         ══════════════════════════════════════════════════════════════ -->
    <template v-if="!isEditMode && !processing && !resultId">
      <div class="card">
        <h2 class="card-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
          上传录音文件
        </h2>

        <!-- Mode toggle: file upload vs URL input -->
        <div class="mode-toggle">
          <button
            class="mode-toggle-btn"
            :class="{ active: inputMode === 'file' }"
            @click="inputMode = 'file'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            文件上传
          </button>
          <button
            class="mode-toggle-btn"
            :class="{ active: inputMode === 'url' }"
            @click="inputMode = 'url'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
            URL 输入
          </button>
        </div>

        <!-- File upload mode -->
        <template v-if="inputMode === 'file'">
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
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="23"/>
                <line x1="8" y1="23" x2="16" y2="23"/>
              </svg>
            </div>
            <div class="upload-zone-text">拖拽或点击选择录音文件</div>
            <div class="upload-zone-hint">支持 wav/mp3/m4a/flac 等常见音频格式，≤100MB</div>
            <input
              ref="fileInput"
              type="file"
              accept=".wav,.mp3,.m4a,.flv,.mp4,.wma,.3gp,.amr,.aac,.ogg,.flac"
              style="display:none"
              @change="onFileChange"
            />
          </div>
          <div v-if="selectedFile" class="file-info-row mt-4">
            <div class="file-info">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="23"/>
                <line x1="8" y1="23" x2="16" y2="23"/>
              </svg>
              <span>{{ selectedFile.name }}</span>
              <span class="file-size">（{{ formatSize(selectedFile.size) }}）</span>
            </div>
            <button class="btn btn-ghost btn-sm" @click.stop="selectedFile = null">更换</button>
          </div>
        </template>

        <!-- URL input mode -->
        <template v-else>
          <div class="url-input-area">
            <div class="form-group">
              <label class="form-label">音频文件 URL</label>
              <input
                class="form-input"
                v-model="audioUrl"
                placeholder="https://oss.aliyuncs.com/meeting-audio.wav"
              />
              <span class="form-hint">输入公网可访问的音频文件直链，无大小限制</span>
            </div>
            <div class="form-group">
              <label class="form-label">文件名 <span class="text-xs text-muted">（可选）</span></label>
              <input
                class="form-input"
                v-model="audioFilename"
                placeholder="根据 URL 自动推断，也可手动指定"
              />
            </div>
          </div>
        </template>

        <div class="flex gap-2 mt-4">
          <button class="btn btn-primary" @click="startTranscribe" :disabled="!canTranscribe">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            开始识别
          </button>
          <button class="btn btn-outline" @click="clearAll">清除</button>
        </div>
      </div>

      <!-- Meeting info card (shown when file selected or URL entered) -->
      <div v-if="showMeetingInfo" class="card mt-4">
        <h2 class="card-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          会议基本信息
          <span class="text-xs text-muted">（可选，辅助 AI 生成更准确的纪要）</span>
        </h2>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">会议名称</label>
            <input class="form-input" v-model="meetingForm.name" placeholder="例：周例会" />
          </div>
          <div class="form-group">
            <label class="form-label">会议时间</label>
            <input class="form-input" v-model="meetingForm.time" type="datetime-local" />
          </div>
          <div class="form-group">
            <label class="form-label">会议地点 <span class="text-xs text-muted">（可选）</span></label>
            <input class="form-input" v-model="meetingForm.location" placeholder="例：3楼会议室" />
          </div>
          <div class="form-group">
            <label class="form-label">会议主持 <span class="text-xs text-muted">（可选）</span></label>
            <TagInput
              v-model="meetingForm.chair"
              :suggestions="userSuggestions"
              :invalidValues="[]"
              placeholder="输入主持人姓名"
            />
          </div>
          <div class="form-group">
            <label class="form-label">与会人员</label>
            <TagInput
              v-model="meetingForm.attendees"
              :suggestions="userSuggestions"
              :invalidValues="[]"
              placeholder="输入与会人员姓名"
            />
          </div>
          <div class="form-group">
            <label class="form-label">参会部门 <span class="text-xs text-muted">（可选）</span></label>
            <TagInput
              v-model="meetingForm.departments"
              :suggestions="deptSuggestions"
              :invalidValues="[]"
              placeholder="输入部门名称"
            />
          </div>
          <div class="form-group">
            <label class="form-label">记录人 <span class="text-xs text-muted">（可选）</span></label>
            <TagInput
              v-model="meetingForm.recorder"
              :suggestions="userSuggestions"
              :invalidValues="[]"
              placeholder="输入记录人姓名"
            />
          </div>
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
        <div class="extracting-title">腾讯云 ASR 语音识别中...</div>
        <div class="extracting-file">{{ displayFileName }}</div>
        <div class="extracting-desc">音频时长越长等待越久，请耐心等候</div>
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
          <div class="flex gap-2 pdf-actions">
            <button class="btn btn-outline btn-sm" @click="generatePdf" :disabled="generatingPdf">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
              {{ generatingPdf ? '生成中...' : pdfFilename ? '重新生成 PDF' : '生成 PDF' }}
            </button>
            <button
              v-if="pdfFilename"
              class="btn btn-success btn-sm"
              @click="downloadPdf"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              下载 PDF
            </button>
            <span class="pdf-hint">生成后推送至企业微信时将作为附件发送</span>
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
          <span v-if="!parsed" class="badge badge-draft" style="margin-left:8px;font-size:11px">草稿</span>
          <span v-if="parsed" class="badge badge-pushed" style="margin-left:8px;font-size:11px">已解析</span>
        </label>

        <!-- Status hint -->
        <div v-if="!parsed" class="parse-hint">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
          当前为会议纪要草稿，编辑确认后点击下方「会议纪要解析」按钮，自动提取工作任务
        </div>
        <div v-if="parsed" class="parse-hint parsed">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          已按部门/中心分解为结构化任务清单，可直接用于内部下发与执行跟踪
        </div>

        <MeetingEditor v-model="resultData.meeting" v-model:html="resultData.meeting_html" />

        <!-- Parse button (only show when not parsed yet) -->
        <div v-if="!parsed" class="flex gap-2 mt-4">
          <button
            class="btn btn-accent"
            @click="parseResult"
            :disabled="parsing || !resultData.meeting?.trim()"
          >
            <svg v-if="!parsing" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            <span v-if="parsing" class="spinner-inline"></span>
            {{ parsing ? '解析中...' : '会议纪要解析' }}
          </button>
          <span v-if="!resultData.meeting?.trim()" class="text-sm text-muted" style="align-self:center">
            请先填写会议纪要内容
          </span>
        </div>
        <!-- Re-parse button (when already parsed, smaller ghost style) -->
        <div v-if="parsed" class="flex gap-2 mt-4">
          <button
            class="btn btn-ghost btn-sm"
            @click="parsed = false"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px">
              <polyline points="1 4 1 10 7 10"/>
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
            </svg>
            重新编辑后再次解析
          </button>
        </div>
      </div>

      <!-- Meeting info fields (only after parsing) -->
      <template v-if="parsed">
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

        <!-- Schedules (only after parsing) -->
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
      </template>

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
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/index.js'
import TagInput from '../components/TagInput.vue'
import ScheduleEditor from '../components/ScheduleEditor.vue'
import MeetingEditor from '../components/MeetingEditor.vue'

const route = useRoute()
const router = useRouter()

const isEditMode = computed(() => !!route.params.id)

// Upload state
const fileInput = ref(null)
const dragging = ref(false)
const selectedFile = ref(null)

// URL input mode state
const inputMode = ref('file')
const audioUrl = ref('')
const audioFilename = ref('')

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
const generatingPdf = ref(false)
const parsing = ref(false)
const parsed = ref(false)
const pdfFilename = ref('')

const userSuggestions = ref([])
const deptSuggestions = ref([])

const meetingForm = reactive({
  name: '',
  time: '',
  location: '',
  chair: [],
  attendees: [],
  departments: [],
  recorder: [],
})

const canTranscribe = computed(() => {
  if (inputMode.value === 'file') return !!selectedFile.value
  return audioUrl.value.trim().length > 0
})

const showMeetingInfo = computed(() => {
  if (inputMode.value === 'file') return !!selectedFile.value
  return audioUrl.value.trim().length > 0
})

const displayFileName = computed(() => {
  if (inputMode.value === 'file' && selectedFile.value) return selectedFile.value.name
  if (inputMode.value === 'url' && audioUrl.value.trim()) {
    return audioFilename.value.trim() || audioUrl.value.trim().split('/').pop() || audioUrl.value.trim()
  }
  return ''
})

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
    parsed.value = record.result_json._parsed === true
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
  const audioExts = ['.wav', '.mp3', '.m4a', '.flv', '.mp4', '.wma', '.3gp', '.amr', '.aac', '.ogg', '.flac']
  if (!audioExts.includes(ext)) {
    error.value = '仅支持音频格式：wav/mp3/m4a/flac 等'
    return
  }
  error.value = ''
  selectedFile.value = file
}

function clearAll() {
  selectedFile.value = null
  audioUrl.value = ''
  audioFilename.value = ''
  error.value = ''
  Object.assign(meetingForm, {
    name: '', time: '', location: '',
    chair: [], attendees: [], departments: [], recorder: [],
  })
}

// Start transcription
async function startTranscribe() {
  if (!canTranscribe.value) return
  processing.value = true
  error.value = ''

  const metadata = {
    meeting_name: meetingForm.name,
    meeting_time: meetingForm.time,
    meeting_location: meetingForm.location,
    meeting_chair: meetingForm.chair.join(','),
    meeting_attendees: meetingForm.attendees.join(','),
    meeting_departments: meetingForm.departments.join(','),
    meeting_recorder: meetingForm.recorder.join(','),
  }

  try {
    let data
    if (inputMode.value === 'url') {
      data = await api.transcribeUrl(audioUrl.value.trim(), {
        ...metadata,
        audio_filename: audioFilename.value.trim(),
      })
    } else {
      if (!selectedFile.value) return
      data = await api.transcribeFile(selectedFile.value, metadata)
    }
    resultId.value = data.id
    resultFilename.value = data.original_filename
    resultStatus.value = 'draft'
    resultData.value = normalizeSchedules(data.result)
    parsed.value = data.result._parsed === true
    // Auto navigate to edit mode
    router.replace({ name: 'transcribe-edit', params: { id: data.id } })
  } catch (e) {
    error.value = `识别失败: ${e.message}`
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

// Parse meeting minutes → merge into shared extraction pipeline → ReviewView
async function parseResult() {
  if (!resultId.value) return
  const meetingText = (resultData.value.meeting || '').trim()
  if (!meetingText) {
    error.value = '会议纪要内容为空，请先填写内容再解析'
    return
  }

  parsing.value = true
  flash.value = ''
  error.value = ''
  try {
    // Save current transcription state first
    await api.updateTranscription(resultId.value, { ...resultData.value })
    // Call shared extraction pipeline with optional pdf_filename
    const data = await api.extractFromText(meetingText, resultFilename.value, pdfFilename.value)
    // Navigate to ReviewView for editing/saving/pushing (shared with docx flow)
    router.push({ name: 'review', params: { id: data.id } })
  } catch (e) {
    flash.value = `解析失败: ${e.message}`
    flashType.value = 'flash-error'
  } finally {
    parsing.value = false
  }
}

// Generate PDF
async function generatePdf() {
  if (!resultId.value) return
  generatingPdf.value = true
  flash.value = ''
  error.value = ''
  try {
    // Save meeting text first, then generate PDF
    await api.updateTranscription(resultId.value, { ...resultData.value })
    const data = await api.generatePdf(resultId.value)
    pdfFilename.value = data.pdf_filename
    flash.value = 'PDF 生成成功'
    flashType.value = 'flash-success'
  } catch (e) {
    flash.value = `PDF 生成失败: ${e.message}`
    flashType.value = 'flash-error'
  } finally {
    generatingPdf.value = false
  }
}

// Download PDF
function downloadPdf() {
  if (!resultId.value || !pdfFilename.value) return
  api.downloadPdf(resultId.value, pdfFilename.value)
  flash.value = 'PDF 文件已开始下载'
  flashType.value = 'flash-success'
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
  padding: var(--space-6) 0;
}

@media (min-width: 640px) {
  .extracting-state {
    padding: var(--space-8) 0;
  }
}

.extracting-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--gray-700);
  margin-top: var(--space-3);
}

@media (min-width: 640px) {
  .extracting-title {
    font-size: var(--text-lg);
    margin-top: var(--space-4);
  }
}

.extracting-file {
  font-size: var(--text-sm);
  color: var(--gray-400);
  margin-top: var(--space-2);
}

.extracting-desc {
  font-size: var(--text-xs);
  color: var(--gray-400);
  margin-top: var(--space-1);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-6) 0;
  color: var(--gray-400);
  font-size: var(--text-sm);
}

@media (min-width: 640px) {
  .empty-state {
    padding: var(--space-8) 0;
    gap: var(--space-3);
  }
}

.empty-state svg {
  opacity: 0.5;
  width: 32px;
  height: 32px;
}

@media (min-width: 640px) {
  .empty-state svg {
    width: 40px;
    height: 40px;
  }
}

/* ── Mode Toggle ─────────────────────────────────────────────────── */
.mode-toggle {
  display: flex;
  gap: 0;
  margin-bottom: var(--space-4);
  background: var(--gray-100);
  border-radius: var(--radius-md);
  padding: 3px;
  width: fit-content;
}

.mode-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--gray-500);
  background: transparent;
  border: none;
  border-radius: calc(var(--radius-md) - 2px);
  cursor: pointer;
  transition: all 0.2s;
}

.mode-toggle-btn:hover {
  color: var(--gray-700);
}

.mode-toggle-btn.active {
  color: var(--primary-700);
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.mode-toggle-btn svg {
  flex-shrink: 0;
}

/* ── URL Input Area ─────────────────────────────────────────────── */
.url-input-area {
  padding: var(--space-4);
  background: var(--gray-50);
  border: 1.5px dashed var(--gray-300);
  border-radius: var(--radius-md);
}

.url-input-area .form-group + .form-group {
  margin-top: var(--space-3);
}

.form-hint {
  display: block;
  font-size: 11px;
  color: var(--gray-400);
  margin-top: 4px;
  line-height: 1.4;
}

@media (min-width: 640px) {
  .form-hint {
    font-size: var(--text-xs);
  }
}

.btn-accent {
  background: linear-gradient(135deg, var(--primary-600), var(--primary-400));
  color: #fff;
  border: none;
  font-weight: 600;
}
.btn-accent:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
  transform: translateY(-1px);
}
.btn-accent:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.parse-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11px;
  color: var(--gray-500);
  margin-bottom: var(--space-2);
  padding: 8px 10px;
  background: #fff8e6;
  border: 1px solid #f0db9e;
  border-radius: var(--radius-md);
  line-height: 1.5;
}

.parse-hint svg {
  flex-shrink: 0;
  margin-top: 1px;
}

.parse-hint.parsed {
  background: #e8f8ed;
  border-color: #9ed9b0;
  color: #2d7a4a;
}

@media (min-width: 640px) {
  .parse-hint {
    font-size: var(--text-xs);
    padding: 6px 10px;
    align-items: center;
  }
  .parse-hint svg {
    margin-top: 0;
  }
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
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── PDF Hint ──────────────────────────────────────────────────── */
.pdf-actions {
  flex-wrap: wrap;
  align-items: center;
}

.pdf-hint {
  font-size: 11px;
  color: var(--gray-400);
  line-height: 1.3;
}

@media (min-width: 640px) {
  .pdf-hint {
    font-size: var(--text-xs);
  }
}

@media (max-width: 639px) {
  .flex-between {
    flex-wrap: wrap;
    gap: var(--space-2);
  }
  .flex-between .flex.gap-2 {
    flex-wrap: wrap;
  }
  .flex-between .flex.gap-2 .btn {
    font-size: 11px;
    padding: 5px 10px;
  }
}
</style>
