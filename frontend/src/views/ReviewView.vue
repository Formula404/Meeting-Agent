<template>
  <div>
    <div class="review-header">
      <h1 class="page-title" style="margin-bottom:0">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:8px">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
        审查修改
      </h1>
      <router-link to="/" class="btn btn-ghost btn-sm" style="align-self:flex-start">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"/>
          <polyline points="12 19 5 12 12 5"/>
        </svg>
        返回上传
      </router-link>
    </div>

    <div v-if="loading" class="card">
      <div class="spinner">
        <div class="spinner-dot"></div>
        <div class="spinner-dot"></div>
        <div class="spinner-dot"></div>
      </div>
    </div>

    <div v-if="error" class="flash flash-error">{{ error }}</div>

    <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>

    <div v-if="errorDialog.visible" class="dialog-mask" @click.self="closeErrorDialog">
      <div class="dialog-card">
        <div class="dialog-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          推送失败
        </div>
        <div class="dialog-body">{{ errorDialog.message }}</div>
        <div class="dialog-actions">
          <button class="btn btn-primary btn-sm" @click="closeErrorDialog">我知道了</button>
        </div>
      </div>
    </div>

    <template v-if="!loading && result">
      <div class="card">
        <div class="flex-between mb-4">
          <span class="card-title" style="margin:0;border:none;padding:0">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            文件：{{ filename }}
            <span class="badge" :class="result.status === 'pushed' ? 'badge-pushed' : 'badge-draft'" style="margin-left:8px">
              {{ result.status === 'pushed' ? '✓ 已推送' : '○ 草稿' }}
            </span>
          </span>
        </div>

        <!-- pdf attachment -->
        <div class="form-group">
          <label class="form-label">PDF 附件</label>
          <div class="file-info-row">
            <div class="file-info">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <path d="M9 15h6"/>
                <path d="M12 12v6"/>
              </svg>
              <span v-if="pdfFilename" class="text-sm">{{ pdfFilename }}</span>
              <span v-else class="text-sm text-muted">未上传 PDF 附件</span>
            </div>
            <button class="btn btn-ghost btn-sm" @click="triggerPdfUpload">{{ pdfFilename ? '更换' : '上传' }}</button>
          </div>
          <input
            ref="pdfInput"
            type="file"
            accept=".pdf"
            style="display:none"
            @change="onPdfChange"
          />
          <div v-if="pdfUploading" class="text-xs text-muted" style="margin-top:4px">上传中...</div>
        </div>

        <!-- meeting_date -->
        <div class="form-group" ref="meetingDateRef">
          <label class="form-label">会议时间</label>
          <input
            class="form-input"
            type="datetime-local"
            step="1"
            :value="meetingDateInput"
            @input="onMeetingDateInput($event.target.value)"
          />
        </div>

        <!-- push_user -->
        <div class="form-group" ref="pushUserRef">
          <div class="form-label-row">
            <label class="form-label" style="margin:0">推送用户</label>
            <button v-if="local.push_user.length" class="btn btn-ghost btn-sm" @click="local.push_user = []">清除</button>
          </div>
          <TagInput
            v-model="local.push_user"
            :suggestions="userSuggestions"
            :invalidValues="invalidUsers"
            placeholder="输入用户姓名"
          />
        </div>

        <!-- push_dept -->
        <div class="form-group" ref="pushDeptRef">
          <div class="form-label-row">
            <label class="form-label" style="margin:0">推送部门</label>
            <button v-if="local.push_dept.length" class="btn btn-ghost btn-sm" @click="local.push_dept = []">清除</button>
          </div>
          <TagInput
            v-model="local.push_dept"
            :suggestions="deptSuggestions"
            :invalidValues="invalidDepts"
            placeholder="输入部门名称"
          />
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
            <button v-if="local.schedules.length" type="button" class="btn btn-ghost btn-sm btn-danger-text" @click="clearAllSchedules">清空全部</button>
            <button type="button" class="btn btn-outline btn-sm" @click="addSchedule">+ 添加日程</button>
          </div>
        </div>

        <div v-for="(item, idx) in local.schedules" :key="idx" :ref="(el) => setScheduleRef(el, idx)">
          <ScheduleEditor
            :item="item"
            :index="idx"
            :userSuggestions="userSuggestions"
            :invalidOwnerTags="invalidUsers"
            @update="updateSchedule(idx, $event)"
            @remove="removeSchedule(idx)"
          />
        </div>

        <div v-if="!local.schedules.length" class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <div>暂无日程安排，点击上方添加</div>
        </div>
      </div>

      <!-- Meeting content -->
      <div class="card" ref="meetingContentRef">
        <label class="form-label">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          会议纪要内容
        </label>
        <textarea
          class="form-textarea"
          v-model="local.meeting"
          rows="15"
        ></textarea>
      </div>

      <!-- Actions -->
      <div class="action-bar">
        <button class="btn btn-primary" @click="save" :disabled="saving">
          <svg v-if="!saving" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          {{ saving ? '保存中...' : '保存修改' }}
        </button>
        <button
          class="btn btn-success"
          @click="push"
          :disabled="pushing || !canPushBasic"
          v-if="result.status !== 'pushed'"
        >
          <svg v-if="!pushing" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
          {{ pushing ? '推送中...' : '推送到企业微信' }}
        </button>
        <button
          class="btn btn-warning"
          @click="push"
          :disabled="pushing || !canPushBasic"
          v-else
        >
          <svg v-if="!pushing" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          {{ pushing ? '推送中...' : '再次推送' }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/index.js'
import TagInput from '../components/TagInput.vue'
import ScheduleEditor from '../components/ScheduleEditor.vue'

const route = useRoute()

const loading = ref(true)
const error = ref('')
const flash = ref('')
const flashType = ref('flash-info')
const saving = ref(false)
const pushing = ref(false)
const invalidUsers = ref([])
const invalidDepts = ref([])
const meetingDateRef = ref(null)
const pushUserRef = ref(null)
const pushDeptRef = ref(null)
const meetingContentRef = ref(null)
const scheduleRefs = ref({})
const errorDialog = reactive({
  visible: false,
  message: '',
})

const pdfInput = ref(null)
const pdfFilename = ref('')
const pdfUploading = ref(false)

function triggerPdfUpload() { pdfInput.value?.click() }

async function onPdfChange(e) {
  const file = e.target.files[0]
  if (!file) return
  if (!file.name.endsWith('.pdf')) {
    flash.value = '仅支持 .pdf 格式'
    flashType.value = 'flash-error'
    return
  }
  pdfUploading.value = true
  flash.value = ''
  try {
    const data = await api.uploadPdf(route.params.id, file)
    pdfFilename.value = data.pdf_filename
    flash.value = 'PDF 附件上传成功'
    flashType.value = 'flash-success'
  } catch (err) {
    flash.value = `PDF 上传失败: ${err.message}`
    flashType.value = 'flash-error'
  } finally {
    pdfUploading.value = false
    e.target.value = ''
  }
}

const result = ref(null)
const local = reactive({
  meeting_date: '',
  push_user: [],
  push_dept: [],
  schedules: [],
  meeting: '',
})

const userSuggestions = ref([])
const deptSuggestions = ref([])
const filename = ref('')

const ERROR_MESSAGES = {
  81013: '推送目标无效或无权限：UserID、部门ID、标签ID全部非法或不可用。',
  40003: '无效的 UserID：至少有一个接收人不存在或无权限。',
  40066: '部门列表不合法：部门列表为空，或至少有一个部门ID不存在于通讯录中。',
  60003: '部门ID不存在：请检查部门是否已同步到系统。',
  60123: '无效的部门ID：请检查部门ID格式和实际可见权限。',
  60267: '时间参数不合法：请使用日期时间选择器选择开始/结束时间（精确到秒）。',
}

const meetingDateInput = computed(() => timestampToDateTimeLocal(local.meeting_date))

const canPushBasic = computed(() => {
  const hasTarget = local.push_user.length > 0 || local.push_dept.length > 0
  const hasMeeting = String(local.meeting || '').trim().length > 0
  return hasTarget && hasMeeting
})

onMounted(async () => {
  const id = route.params.id
  try {
    const [res, users, depts] = await Promise.all([
      api.getResult(id),
      api.listUsers().catch(() => []),
      api.listDepartments().catch(() => []),
    ])
    result.value = res
    filename.value = res.original_filename
    pdfFilename.value = res.pdf_filename || ''

    const data = res.result_json

    // Normalise owner from string → array if needed
    const schedules = (data.schedules || []).map((s) => ({
      ...s,
      owner: Array.isArray(s.owner ?? []) ? s.owner : [s.owner].filter(Boolean),
      start_time: normalizeTimestampValue(s.start_time),
      end_time: normalizeTimestampValue(s.end_time),
    }))

    Object.assign(local, {
      meeting_date: normalizeTimestampValue(data.meeting_date) || nowTimestamp(),
      push_user: Array.isArray(data.push_user) ? data.push_user : [],
      push_dept: Array.isArray(data.push_dept) ? data.push_dept : [],
      schedules,
      meeting: data.meeting || '',
    })

    userSuggestions.value = users.map((u) => ({ label: u.name, value: u.name }))
    deptSuggestions.value = depts.map((d) => ({ label: d.name, value: d.name }))
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

function updateSchedule(idx, { field, value }) {
  local.schedules[idx][field] = value
}

function removeSchedule(idx) {
  local.schedules.splice(idx, 1)
}

function addSchedule() {
  local.schedules.push({
    title: '',
    owner: [],
    start_time: '',
    end_time: '',
    description: '',
  })
}

function clearAllSchedules() {
  if (!confirm('确认清空全部日程？')) return
  local.schedules.splice(0)
}

async function save() {
  saving.value = true
  flash.value = ''
  try {
    await api.updateResult(route.params.id, { ...local })
    flash.value = '保存成功'
    flashType.value = 'flash-success'
  } catch (e) {
    flash.value = `保存失败: ${e.message}`
    flashType.value = 'flash-error'
  } finally {
    saving.value = false
  }
}

function buildSavePayload() {
  return {
    meeting_date: local.meeting_date || nowTimestamp(),
    push_user: local.push_user,
    push_dept: local.push_dept,
    schedules: local.schedules,
    meeting: local.meeting,
  }
}

function timestampToDateTimeLocal(value) {
  if (value === null || value === undefined || value === '') return ''
  const ts = Number(value)
  if (!Number.isFinite(ts)) return ''
  const d = new Date(ts * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function onMeetingDateInput(value) {
  if (!value) {
    local.meeting_date = ''
    return
  }
  const ts = Math.floor(new Date(value).getTime() / 1000)
  local.meeting_date = Number.isFinite(ts) ? ts : ''
}

function normalizeTimestampValue(value) {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'number' && Number.isFinite(value)) return Math.floor(value)
  const n = Number(value)
  if (Number.isFinite(n) && String(value).trim() !== '') return Math.floor(n)
  const parsed = new Date(String(value).replace(' ', 'T'))
  const ts = Math.floor(parsed.getTime() / 1000)
  return Number.isFinite(ts) ? ts : ''
}

function nowTimestamp() {
  return Math.floor(Date.now() / 1000)
}

function setScheduleRef(el, idx) {
  if (el) {
    scheduleRefs.value[idx] = el
    return
  }
  delete scheduleRefs.value[idx]
}

function scrollToField(target) {
  const el = target?.$el || target
  if (el && typeof el.scrollIntoView === 'function') {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function openErrorDialog(message, scrollTarget) {
  errorDialog.message = message
  errorDialog.visible = true
  if (scrollTarget) {
    setTimeout(() => scrollToField(scrollTarget), 0)
  }
}

function closeErrorDialog() {
  errorDialog.visible = false
}

function validateBeforePush() {
  if (!(local.push_user.length > 0 || local.push_dept.length > 0)) {
    return { ok: false, message: '推送用户和推送部门至少填写一项。', target: pushUserRef.value || pushDeptRef.value }
  }
  if (!String(local.meeting || '').trim()) {
    return { ok: false, message: '会议纪要内容不能为空。', target: meetingContentRef.value }
  }

  const meetingTs = Number(local.meeting_date || nowTimestamp())
  for (let i = 0; i < local.schedules.length; i += 1) {
    const item = local.schedules[i]
    const startTs = Number(item.start_time)
    const endTs = Number(item.end_time)
    if (!Number.isFinite(startTs) || !Number.isFinite(endTs)) {
      return { ok: false, message: `日程 #${i + 1} 时间不完整，请选择开始和结束时间。`, target: scheduleRefs.value[i] }
    }
    if (startTs >= endTs) {
      return { ok: false, message: `日程 #${i + 1} 开始时间必须早于结束时间。`, target: scheduleRefs.value[i] }
    }
    if (startTs <= meetingTs || endTs <= meetingTs) {
      return { ok: false, message: `日程 #${i + 1} 时间必须晚于会议时间。`, target: scheduleRefs.value[i] }
    }
  }
  return { ok: true }
}

function parseWecomError(raw) {
  const text = String(raw || '')
  const codeMatch = text.match(/errcode=(\d+)/)
  const code = codeMatch ? Number(codeMatch[1]) : null
  const reason = code && ERROR_MESSAGES[code] ? ERROR_MESSAGES[code] : ''
  const invalidUserMatch = text.match(/invaliduser['"]?\s*[:=]\s*['"]([^'"]+)['"]/i)
  const invalidPartyMatch = text.match(/invalidparty['"]?\s*[:=]\s*['"]([^'"]+)['"]/i)

  invalidUsers.value = invalidUserMatch ? invalidUserMatch[1].split('|').map((x) => x.trim()).filter(Boolean) : []
  invalidDepts.value = invalidPartyMatch ? invalidPartyMatch[1].split('|').map((x) => x.trim()).filter(Boolean) : []

  if (code && reason) return `推送失败（${code}）：${reason}`
  return `推送失败: ${text}`
}

async function push() {
  const check = validateBeforePush()
  if (!check.ok) {
    openErrorDialog(check.message, check.target)
    return
  }
  pushing.value = true
  flash.value = ''
  invalidUsers.value = []
  invalidDepts.value = []
  try {
    // Save first, then push
    await api.updateResult(route.params.id, buildSavePayload())
    const resp = await api.pushResult(route.params.id)
    flash.value = '推送成功！消息和日程已发送到企业微信'
    flashType.value = 'flash-success'
    // Refresh to update status badge
    const refreshed = await api.getResult(route.params.id)
    result.value = refreshed
  } catch (e) {
    const message = parseWecomError(e.message)
    openErrorDialog(message, invalidUsers.value.length ? pushUserRef.value : (invalidDepts.value.length ? pushDeptRef.value : null))
  } finally {
    pushing.value = false
  }
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

.form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  gap: 8px;
  flex-wrap: wrap;
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
</style>
