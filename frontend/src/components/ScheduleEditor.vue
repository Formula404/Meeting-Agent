<template>
  <div class="schedule-card">
    <div class="schedule-card-header">
      <span class="schedule-card-title">日程 #{{ index + 1 }}</span>
      <button type="button" class="btn btn-danger btn-sm" @click="$emit('remove')">删除</button>
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
  border-color: #dc2626 !important;
}

.field-required:focus,
.schedule-tag-input.field-required:focus-within {
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.12);
}

.field-error {
  margin-top: 4px;
  font-size: 12px;
  color: #dc2626;
}
</style>
