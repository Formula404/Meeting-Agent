<template>
  <div class="schedule-card">
    <div class="schedule-card-header">
      <span class="schedule-card-title">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
          <line x1="16" y1="2" x2="16" y2="6"/>
          <line x1="8" y1="2" x2="8" y2="6"/>
          <line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
        日程 #{{ index + 1 }}
      </span>
      <button type="button" class="btn btn-ghost btn-sm btn-danger-text" @click="$emit('remove')">删除</button>
    </div>
    <div class="form-group">
      <label class="form-label">标题</label>
      <input
        class="form-input"
        :class="{ 'field-required': requiredErrors.title }"
        :value="item.title"
        @input="update('title', $event.target.value)"
        placeholder="日程标题"
      />
      <div v-if="requiredErrors.title" class="field-error">必填</div>
    </div>
    <div class="schedule-grid">
      <div class="form-group">
        <label class="form-label">负责人</label>
        <TagInput
          class="schedule-tag-input"
          :class="{ 'field-required': requiredErrors.owner }"
          :modelValue="item.owner ?? []"
          @update:modelValue="update('owner', $event)"
          :suggestions="userSuggestions"
          :invalidValues="invalidOwnerTags"
          placeholder="输入负责人姓名"
        />
        <div v-if="requiredErrors.owner" class="field-error">必填</div>
      </div>
      <div class="form-group">
        <label class="form-label">开始时间</label>
        <input
          class="form-input"
          :class="{ 'field-required': requiredErrors.start_time }"
          type="datetime-local"
          step="1"
          :value="toDateTimeLocal(item.start_time)"
          @input="onTimeInput('start_time', $event.target.value)"
        />
        <div v-if="requiredErrors.start_time" class="field-error">必填</div>
      </div>
      <div class="form-group">
        <label class="form-label">结束时间</label>
        <input
          class="form-input"
          :class="{ 'field-required': requiredErrors.end_time }"
          type="datetime-local"
          step="1"
          :value="toDateTimeLocal(item.end_time)"
          @input="onTimeInput('end_time', $event.target.value)"
        />
        <div v-if="requiredErrors.end_time" class="field-error">必填</div>
      </div>
      <div class="form-group">
        <label class="form-label">备注</label>
        <input class="form-input" :value="item.description" @input="update('description', $event.target.value)" placeholder="事项说明" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import TagInput from './TagInput.vue'

const props = defineProps({
  item: { type: Object, required: true },
  index: { type: Number, required: true },
  userSuggestions: { type: Array, default: () => [] },
  invalidOwnerTags: { type: Array, default: () => [] },
})

const emit = defineEmits(['update', 'remove'])

const requiredErrors = computed(() => ({
  title: !String(props.item?.title || '').trim(),
  owner: !Array.isArray(props.item?.owner) || props.item.owner.length === 0,
  start_time: !isValidTimestamp(props.item?.start_time),
  end_time: !isValidTimestamp(props.item?.end_time),
}))

function update(field, value) {
  emit('update', { field, value })
}

function isValidTimestamp(value) {
  const ts = Number(value)
  return Number.isFinite(ts)
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

<style scoped>
.field-required {
  border-color: var(--danger) !important;
}

.field-required:focus,
.schedule-tag-input.field-required:focus-within {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.12) !important;
}

.field-error {
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--danger);
}
</style>
