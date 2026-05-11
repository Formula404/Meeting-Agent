<template>
  <div class="tag-input-wrapper" @click="focusInput">
    <span
      v-for="(item, idx) in modelValue"
      :key="idx"
      class="tag-item"
      :class="{ 'tag-item-invalid': invalidSet.has(String(item)) }"
    >
      {{ item }}
      <button type="button" class="tag-remove" @click.stop="remove(idx)">&times;</button>
    </span>
    <input
      ref="inputRef"
      class="tag-input-field"
      :placeholder="modelValue.length ? '' : placeholder"
      v-model="query"
      @input="onInput"
      @keydown="onKeydown"
      @blur="onBlur"
    />
    <div v-if="showSuggestions && filtered.length" class="tag-suggestions">
      <div
        v-for="(s, i) in filtered"
        :key="s.value ?? s"
        class="tag-suggestion"
        :class="{ active: highlightIndex === i }"
        @mousedown.prevent="select(s)"
      >
        {{ s.label ?? s }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  suggestions: { type: Array, default: () => [] },
  placeholder: { type: String, default: '输入或选择...' },
  invalidValues: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const inputRef = ref(null)
const query = ref('')
const highlightIndex = ref(-1)
const showSuggestions = ref(false)
const invalidSet = computed(() => new Set(props.invalidValues.map((x) => String(x))))

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return []
  const selected = new Set(props.modelValue)
  return props.suggestions
    .filter((s) => {
      const label = (s.label ?? s).toLowerCase()
      return label.includes(q) && !selected.has(s.label ?? s)
    })
    .slice(0, 20)
})

function focusInput() { inputRef.value?.focus() }

function onInput() {
  showSuggestions.value = true
  highlightIndex.value = -1
}

function select(item) {
  const val = item.value ?? item
  const label = item.label ?? item
  if (props.modelValue.includes(label)) return
  emit('update:modelValue', [...props.modelValue, label])
  query.value = ''
  showSuggestions.value = false
  nextTick(() => inputRef.value?.focus())
}

function remove(idx) {
  const next = [...props.modelValue]
  next.splice(idx, 1)
  emit('update:modelValue', next)
}

function onKeydown(e) {
  if (e.key === 'Enter' && query.value.trim()) {
    e.preventDefault()
    if (highlightIndex.value >= 0 && filtered.value[highlightIndex.value]) {
      select(filtered.value[highlightIndex.value])
    } else {
      // Add as custom value
      emit('update:modelValue', [...props.modelValue, query.value.trim()])
      query.value = ''
      showSuggestions.value = false
    }
    return
  }
  if (e.key === 'Backspace' && !query.value && props.modelValue.length) {
    remove(props.modelValue.length - 1)
    return
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    highlightIndex.value = Math.min(highlightIndex.value + 1, filtered.value.length - 1)
    return
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    highlightIndex.value = Math.max(highlightIndex.value - 1, -1)
    return
  }
  if (e.key === 'Escape') {
    showSuggestions.value = false
    highlightIndex.value = -1
  }
}

function onBlur() {
  // Delay to allow mousedown on suggestion to fire
  setTimeout(() => {
    showSuggestions.value = false
    highlightIndex.value = -1
  }, 150)
}
</script>
