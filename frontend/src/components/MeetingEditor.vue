<template>
  <div class="meeting-editor">
    <div class="editor-toolbar" v-if="editor">
      <div class="toolbar-group">
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive('bold') }" @click="editor.chain().focus().toggleBold().run()" title="加粗">
          <strong>B</strong>
        </button>
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive('italic') }" @click="editor.chain().focus().toggleItalic().run()" title="斜体">
          <em>I</em>
        </button>
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive('underline') }" @click="editor.chain().focus().toggleUnderline().run()" title="下划线">
          <u>U</u>
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <div class="toolbar-group">
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive({ textAlign: 'left' }) }" @click="editor.chain().focus().setTextAlign('left').run()" title="左对齐">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="10" x2="17" y2="10"/><line x1="3" y1="14" x2="19" y2="14"/><line x1="3" y1="18" x2="13" y2="18"/></svg>
        </button>
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive({ textAlign: 'center' }) }" @click="editor.chain().focus().setTextAlign('center').run()" title="居中">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="5" y1="10" x2="19" y2="10"/><line x1="4" y1="14" x2="20" y2="14"/><line x1="7" y1="18" x2="17" y2="18"/></svg>
        </button>
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive({ textAlign: 'right' }) }" @click="editor.chain().focus().setTextAlign('right').run()" title="右对齐">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="7" y1="10" x2="21" y2="10"/><line x1="5" y1="14" x2="21" y2="14"/><line x1="11" y1="18" x2="21" y2="18"/></svg>
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <div class="toolbar-group">
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive('heading', { level: 1 }) }" @click="editor.chain().focus().toggleHeading({ level: 1 }).run()" title="标题1">H1</button>
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive('heading', { level: 2 }) }" @click="editor.chain().focus().toggleHeading({ level: 2 }).run()" title="标题2">H2</button>
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive('heading', { level: 3 }) }" @click="editor.chain().focus().toggleHeading({ level: 3 }).run()" title="标题3">H3</button>
      </div>

      <div class="toolbar-divider"></div>

      <div class="toolbar-group">
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive('bulletList') }" @click="editor.chain().focus().toggleBulletList().run()" title="无序列表">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1.5" fill="currentColor" stroke="none"/><circle cx="4" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="4" cy="18" r="1.5" fill="currentColor" stroke="none"/></svg>
        </button>
        <button type="button" class="toolbar-btn" :class="{ active: editor.isActive('orderedList') }" @click="editor.chain().focus().toggleOrderedList().run()" title="有序列表">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="10" y1="6" x2="21" y2="6"/><line x1="10" y1="12" x2="21" y2="12"/><line x1="10" y1="18" x2="21" y2="18"/><text x="2" y="10" font-size="10" font-weight="bold" fill="currentColor">1</text><text x="2" y="16" font-size="10" font-weight="bold" fill="currentColor">2</text><text x="2" y="22" font-size="10" font-weight="bold" fill="currentColor">3</text></svg>
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <div class="toolbar-group">
        <button type="button" class="toolbar-btn" @click="editor.chain().focus().setHorizontalRule().run()" title="分割线">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/></svg>
        </button>
      </div>
    </div>
    <editor-content :editor="editor" class="editor-content" />
  </div>
</template>

<script setup>
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import TextAlign from '@tiptap/extension-text-align'
import { watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  html: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'update:html'])

function plainTextToHtml(text) {
  return text
    .split('\n')
    .map(line => {
      const trimmed = line.trim()
      if (!trimmed) return '<p></p>'
      return `<p>${trimmed}</p>`
    })
    .join('')
}

function htmlToPlainText(html) {
  const div = document.createElement('div')
  div.innerHTML = html
  div.querySelectorAll('br').forEach(el => el.replaceWith('\n'))
  div.querySelectorAll('p, h1, h2, h3, li, div, hr, ul, ol').forEach(el => {
    const suffix = el.tagName === 'HR' ? '\n---\n' : '\n'
    el.after(suffix)
  })
  let text = div.textContent || ''
  text = text.replace(/\n{3,}/g, '\n\n')
  return text.trim()
}

let suppressUpdate = false

const editor = useEditor({
  content: props.html || plainTextToHtml(props.modelValue),
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      horizontalRule: true,
    }),
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
  ],
  editorProps: {
    attributes: { class: 'editor-input' },
  },
  onCreate: ({ editor: ed }) => {
    // Emit initial HTML so parent has it without requiring user edit
    const html = ed.getHTML()
    emit('update:html', html)
    emit('update:modelValue', htmlToPlainText(html))
  },
  onUpdate: ({ editor: ed }) => {
    if (suppressUpdate) return
    const html = ed.getHTML()
    emit('update:html', html)
    emit('update:modelValue', htmlToPlainText(html))
  },
})

watch([() => props.html, () => props.modelValue], ([newHtml, newPlain]) => {
  if (!editor.value) return
  const currentHtml = editor.value.getHTML()
  const targetHtml = newHtml || plainTextToHtml(newPlain)
  if (targetHtml && targetHtml !== currentHtml) {
    suppressUpdate = true
    editor.value.commands.setContent(targetHtml)
    suppressUpdate = false
  }
})

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<style scoped>
.meeting-editor {
  border: 1.5px solid var(--gray-200);
  border-radius: var(--radius-md);
  overflow: visible;
  background: #fff;
}

.editor-toolbar {
  position: sticky;
  top: var(--nav-height);
  z-index: calc(var(--z-sticky) - 1);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1px;
  padding: 4px 6px;
  border-bottom: 1px solid var(--gray-200);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  background: var(--gray-50);
  box-shadow: 0 1px 0 rgba(226, 232, 240, 0.9);
  user-select: none;
}

@media (min-width: 640px) {
  .editor-toolbar {
    gap: 2px;
    padding: 6px 8px;
  }
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 1px;
}

.toolbar-divider {
  width: 1px;
  height: 18px;
  background: var(--gray-200);
  margin: 0 3px;
  flex-shrink: 0;
}

@media (min-width: 640px) {
  .toolbar-divider {
    height: 22px;
    margin: 0 4px;
  }
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 26px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: var(--gray-600);
  padding: 0;
  transition: background 0.15s, color 0.15s;
}

@media (min-width: 640px) {
  .toolbar-btn {
    width: 30px;
    height: 28px;
    font-size: 13px;
  }
}

.toolbar-btn:hover {
  background: var(--gray-200);
  color: var(--gray-800);
}

.toolbar-btn.active {
  background: var(--primary-100);
  color: var(--primary-700);
}

.toolbar-btn em { font-style: italic; }
.toolbar-btn strong { font-weight: 700; }
.toolbar-btn u { text-decoration: underline; }

.editor-content {
  padding: 0;
  min-height: 200px;
}

@media (min-width: 640px) {
  .editor-content {
    min-height: 280px;
  }
}

.editor-content :deep(.editor-input) {
  padding: 10px 12px;
  min-height: 200px;
  outline: none;
  line-height: 1.6;
  font-size: 14px;
  color: var(--gray-800);
}

@media (min-width: 640px) {
  .editor-content :deep(.editor-input) {
    padding: 12px 14px;
    min-height: 280px;
    line-height: 1.7;
  }
}

.editor-content :deep(.editor-input p) {
  margin: 0 0 4px;
}

.editor-content :deep(.editor-input h1) {
  font-size: 20px;
  font-weight: 700;
  margin: 12px 0 6px;
}

.editor-content :deep(.editor-input h2) {
  font-size: 17px;
  font-weight: 600;
  margin: 10px 0 4px;
}

.editor-content :deep(.editor-input h3) {
  font-size: 15px;
  font-weight: 600;
  margin: 8px 0 4px;
}

.editor-content :deep(.editor-input ul),
.editor-content :deep(.editor-input ol) {
  padding-left: 22px;
  margin: 4px 0;
}

.editor-content :deep(.editor-input li) {
  margin-bottom: 2px;
}

.editor-content :deep(.editor-input hr) {
  margin: 12px 0;
  border: none;
  border-top: 1px solid var(--gray-300);
}

.editor-content :deep(.editor-input p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  color: var(--gray-400);
  pointer-events: none;
  float: left;
  height: 0;
}
</style>
