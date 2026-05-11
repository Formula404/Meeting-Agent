<template>
  <div>
    <div class="flex-between mb-12">
      <h1 class="page-title" style="margin-bottom:0">审查修改</h1>
      <router-link to="/" class="btn btn-outline btn-sm">返回上传</router-link>
    </div>

    <div v-if="loading" class="card text-center text-muted">加载中...</div>

    <div v-if="error" class="flash flash-error">{{ error }}</div>

    <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>

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
        <div class="form-group">
          <label class="form-label">会议时间</label>
          <input class="form-input" v-model="local.meeting_date" placeholder="YYYY-MM-DD HH:mm" />
        </div>

        <!-- push_user -->
        <div class="form-group">
          <label class="form-label">推送用户</label>
          <TagInput v-model="local.push_user" :suggestions="userSuggestions" placeholder="输入用户姓名" />
        </div>

        <!-- push_dept -->
        <div class="form-group">
          <label class="form-label">推送部门</label>
          <TagInput v-model="local.push_dept" :suggestions="deptSuggestions" placeholder="输入部门名称" />
        </div>
      </div>

      <!-- Schedules -->
      <div class="card">
        <div class="flex-between mb-12">
          <span class="card-title" style="margin:0;border:none;padding:0">日程安排</span>
          <button type="button" class="btn btn-outline btn-sm" @click="addSchedule">+ 添加日程</button>
        </div>

        <ScheduleEditor
          v-for="(item, idx) in local.schedules"
          :key="idx"
          :item="item"
          :index="idx"
          :userSuggestions="userSuggestions"
          @update="updateSchedule(idx, $event)"
          @remove="removeSchedule(idx)"
        />

        <div v-if="!local.schedules.length" class="text-center text-muted text-sm" style="padding:16px 0">
          暂无日程安排
        </div>
      </div>

      <!-- Meeting content -->
      <div class="card">
        <label class="form-label">会议纪要内容</label>
        <textarea class="form-textarea" v-model="local.meeting" rows="15" style="font-size:14px;line-height:1.7"></textarea>
      </div>

      <!-- Actions -->
      <div class="flex gap-12 mt-20">
        <button class="btn btn-primary" @click="save" :disabled="saving">
          {{ saving ? '保存中...' : '保存修改' }}
        </button>
        <button
          class="btn btn-success"
          @click="push"
          :disabled="pushing"
          v-if="result.status !== 'pushed'"
        >
          {{ pushing ? '推送中...' : '推送到企业微信' }}
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
    }))

    Object.assign(local, {
      meeting_date: data.meeting_date || '',
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
    meeting_date: local.meeting_date,
    push_user: local.push_user,
    push_dept: local.push_dept,
    schedules: local.schedules,
    meeting: local.meeting,
  }
}

async function push() {
  pushing.value = true
  flash.value = ''
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
    flash.value = `推送失败: ${e.message}`
    flashType.value = 'flash-error'
  } finally {
    pushing.value = false
  }
}
</script>
