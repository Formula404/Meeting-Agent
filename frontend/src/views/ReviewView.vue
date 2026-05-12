<template>
  <div>
    <div class="review-header">
      <h1 class="page-title" style="margin-bottom:0">审查修改</h1>
      <router-link to="/" class="btn btn-outline btn-sm" style="align-self:flex-start">返回上传</router-link>
    </div>

    <div v-if="loading" class="card text-center text-muted">加载中...</div>

    <div v-if="error" class="flash flash-error">{{ error }}</div>

    <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>
    <div v-if="errorDialog.visible" class="dialog-mask" @click.self="closeErrorDialog">
      <div class="dialog-card">
        <div class="dialog-title">推送失败</div>
        <div class="dialog-body">{{ errorDialog.message }}</div>
        <div class="dialog-actions">
          <button class="btn btn-primary btn-sm" @click="closeErrorDialog">我知道了</button>
        </div>
      </div>
    </div>

    <template v-if="!loading && result">
      <div class="card">
        <div class="flex-between mb-12">
          <span class="card-title" style="margin:0;border:none;padding:0">
            文件：{{ filename }}
            <span class="badge" :class="result.status === 'pushed' ? 'badge-pushed' : 'badge-draft'">
              {{ result.status === 'pushed' ? '已推送' : '草稿' }}
            </span>
          </span>
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
          <label class="form-label">推送用户</label>
          <TagInput
            v-model="local.push_user"
            :suggestions="userSuggestions"
            :invalidValues="invalidUsers"
            placeholder="输入用户姓名"
          />
        </div>

        <!-- push_dept -->
        <div class="form-group" ref="pushDeptRef">
          <label class="form-label">推送部门</label>
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
        <div class="flex-between mb-12">
          <span class="card-title" style="margin:0;border:none;padding:0">日程安排</span>
          <button type="button" class="btn btn-outline btn-sm" @click="addSchedule">+ 添加日程</button>
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

        <div v-if="!local.schedules.length" class="text-center text-muted text-sm" style="padding:16px 0">
          暂无日程安排
        </div>
      </div>

      <!-- Meeting content -->
      <div class="card" ref="meetingContentRef">
        <label class="form-label">会议纪要内容</label>
        <textarea class="form-textarea" v-model="local.meeting" rows="15" style="font-size:14px;line-height:1.7"></textarea>
      </div>

      <!-- Actions -->
      <div class="action-bar">
        <button class="btn btn-primary" @click="save" :disabled="saving">
          {{ saving ? '保存中...' : '保存修改' }}
        </button>
        <button
          class="btn btn-success"
          @click="push"
          :disabled="pushing || !canPushBasic"
          v-if="result.status !== 'pushed'"
        >
          {{ pushing ? '推送中...' : '推送到企业微信' }}
        </button>
        <button
          class="btn btn-warning"
          @click="push"
          :disabled="pushing || !canPushBasic"
          v-else
        >
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
.dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 16px;
}
.dialog-card {
  width: min(520px, 100%);
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
  padding: 16px;
}
.dialog-title {
  font-size: 16px;
  font-weight: 700;
  color: #991b1b;
  margin-bottom: 8px;
}
.dialog-body {
  font-size: 14px;
  color: #334155;
  line-height: 1.6;
  white-space: pre-wrap;
}
.dialog-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
