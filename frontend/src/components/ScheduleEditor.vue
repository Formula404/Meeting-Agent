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
          placeholder="输入负责人姓名"
        />
      </div>
      <div class="form-group">
        <label class="form-label">开始时间</label>
        <input class="form-input" :value="item.start_time" @input="update('start_time', $event.target.value)" placeholder="YYYY-MM-DD HH:mm" />
      </div>
      <div class="form-group">
        <label class="form-label">结束时间</label>
        <input class="form-input" :value="item.end_time" @input="update('end_time', $event.target.value)" placeholder="YYYY-MM-DD HH:mm" />
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
})

const emit = defineEmits(['update', 'remove'])

function update(field, value) {
  emit('update', { field, value })
}
</script>
