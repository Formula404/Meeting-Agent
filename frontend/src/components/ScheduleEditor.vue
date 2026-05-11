<template>
  <div class="schedule-card">
    <div class="schedule-card-header">
      <span class="schedule-card-title">日程 #{{ index + 1 }}</span>
      <button type="button" class="btn btn-danger btn-sm" @click="$emit('remove')">删除</button>
    </div>
    <div class="form-group">
      <label class="form-label">标题</label>
      <input class="form-input" :value="item.title" @input="update('title', $event.target.value)" placeholder="日程标题" />
    </div>
    <div class="schedule-grid">
      <div class="form-group">
        <label class="form-label">负责人</label>
        <TagInput
          :modelValue="item.owner ?? []"
          @update:modelValue="update('owner', $event)"
          :suggestions="userSuggestions"
          :invalidValues="invalidOwnerTags"
          placeholder="输入负责人姓名"
        />
      </div>
      <div class="form-group">
        <label class="form-label">开始时间</label>
        <input
          class="form-input"
          type="datetime-local"
          step="1"
          :value="toDateTimeLocal(item.start_time)"
          @input="onTimeInput('start_time', $event.target.value)"
        />
      </div>
      <div class="form-group">
        <label class="form-label">结束时间</label>
        <input
          class="form-input"
          type="datetime-local"
          step="1"
          :value="toDateTimeLocal(item.end_time)"
          @input="onTimeInput('end_time', $event.target.value)"
        />
      </div>
      <div class="form-group">
        <label class="form-label">备注</label>
        <input class="form-input" :value="item.description" @input="update('description', $event.target.value)" placeholder="事项说明" />
      </div>
    </div>
  </div>
</template>

<script setup>
import TagInput from './TagInput.vue'

defineProps({
  item: { type: Object, required: true },
  index: { type: Number, required: true },
  userSuggestions: { type: Array, default: () => [] },
  invalidOwnerTags: { type: Array, default: () => [] },
})

const emit = defineEmits(['update', 'remove'])

function update(field, value) {
  emit('update', { field, value })
}

function toDateTimeLocal(value) {
  if (value === null || value === undefined || value === '') return ''
  const ts = Number(value)
  if (!Number.isFinite(ts)) return ''
  const d = new Date(ts * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function onTimeInput(field, value) {
  if (!value) {
    update(field, '')
    return
  }
  const ts = Math.floor(new Date(value).getTime() / 1000)
  update(field, Number.isFinite(ts) ? ts : '')
}
</script>
