# 会议纪要模板系统 — 可行性研究报告

> 编写日期：2026-06-09（v2，需求确认后更新）
> 范围：仅定制**会议纪要正文**格式，不影响结构化提取/推送流程

---

## 1. 需求确认

| # | 需求 | 状态 |
|---|------|------|
| 1 | 上传录音时提供模板选择选项 | ✅ 确认 |
| 2 | 未选择模板时使用默认提示词（向后兼容） | ✅ 确认 |
| 3 | 每个用户可创建模板，所有人可见，仅创建者与 admin 可修改 | ✅ 确认 |
| 4 | 首页提供查看现有模板的入口 | ✅ 确认 |
| 5 | 用户可预览每个模板生成的结构（示例 JSON） | ✅ 确认 |
| 6 | **模板仅定制会议纪要正文格式**，标题/日期等保持现有样式 | ✅ 确认 |
| 7 | 模板提示词作为**补充风格说明**追加到默认 prompt 后 | ✅ 确认 |
| 8 | 支持上传 .docx 示例 → AI 分析结构/语言风格/条目化/待办表述 → 生成自然语言版写作要求 | ✅ 确认 |
| 9 | 内置模板仅一个：「景枫周列会」 | ✅ 确认 |
| 10 | 删除模板时不检查引用 | ✅ 确认 |

---

## 2. 架构分析

### 2.1 本功能涉及的管线环节

模板只影响两条管线中**生成 meeting 正文**的环节：

```
管线 A（.docx / 文本输入）：
  workflow.py → LLM( SYSTEM_PROMPT + USER_PROMPT_TEMPLATE ) → JSON
                                         ↑ 模板 style_prompt 追加到这里

管线 B（录音转写 — 阶段 1：生成草稿）：
  transcription/workflow.py → run_transcription_extraction()
    → LLM( GENERATE_SYSTEM_PROMPT + GENERATE_USER_PROMPT_TEMPLATE ) → 纯文本
                                         ↑ 模板 style_prompt 追加到这里

管线 B（阶段 2：解析任务）→ 不受影响 ⛔
推送流程 → 不受影响 ⛔
```

**不涉及**的结构化字段：`meeting_date`, `push_dept`, `push_user`, `schedules` 全部保持现有逻辑。

### 2.2 当前 prompts 分析

两处 prompt 都需要追加 style_prompt：

- `meeting_agent/prompts.py` 的 `SYSTEM_PROMPT`（管线 A）
- `meeting_agent/transcription/prompts.py` 的 `GENERATE_SYSTEM_PROMPT`（管线 B 阶段 1）

注入方式：在原有 system prompt 末尾追加 `\n\n【模板风格要求】\n{style_prompt}`

---

## 3. 技术方案

### 3.1 模板定义模型（精简版）

```json
{
  "id": "uuid",
  "name": "景枫周列会",
  "description": "适用于景枫周例会，包含上周回顾、本周计划、需协调事项",
  "style_prompt": "请按以下风格书写会议纪要正文：\n1. 正文结构分「上周工作回顾」「本周工作计划」「需协调事项」三部分\n2. 每个部分使用 ## 二级标题\n3. 具体事项使用 - 项目符号列表\n4. 语言要求简洁正式……",
  "sample_output": {
    "meeting_date": "2026-06-09 14:00",
    "push_dept": [],
    "push_user": [],
    "schedules": [],
    "meeting": "## 上周工作回顾\n- ...\n\n## 本周工作计划\n- ...\n\n## 需协调事项\n- ..."
  },
  "created_by": 1,
  "is_builtin": false,
  "created_at": "2026-06-09T10:00:00",
  "updated_at": "2026-06-09T10:00:00"
}
```

### 3.2 关键设计决策

#### 决策 1：style_prompt 注入方式

```
原 SYSTEM_PROMPT + "\n\n【模板风格要求】\n" + style_prompt + "\n【模板风格要求结束】"
```

无需修改 `USER_PROMPT_TEMPLATE`。将风格要求放在 system prompt 尾部，LLM 在生成正文时自然会遵循。

#### 决策 2：".docx 示例 → AI 分析" 流程

```
用户上传 .docx
    → 后端读取示例文档全文
    → 调用 LLM（用专门的分析 prompt）：
       【分析指令】
       分析以下会议纪要示例，从以下维度提取写作风格要求：
       1. 整体结构（分几个部分？各部分标题是什么？）
       2. 语言风格（正式程度、用词特点、句式）
       3. 条目化程度（项目符号、编号、段落）
       4. 待办事项/决议的表述方式
       请输出一段自然语言描述，告诉 AI 助手如何写出同样风格的会议纪要。
    → 返回自然语言版的 "写作风格要求" 文本
    → 用户可在编辑器中修改/优化
    → 确认后保存为模板的 style_prompt
```

#### 决策 3：核心字段不变，只定制 `meeting` 文本

- `meeting_date`, `push_dept`, `push_user`, `schedules` 仍然由现有 prompt 逻辑提取
- 只有 `meeting` 字段的生成受模板 style_prompt 影响
- ReviewView 和推送流程无需改动

### 3.3 数据库变更

```sql
CREATE TABLE templates (
    id              TEXT PRIMARY KEY,          -- UUID
    name            TEXT NOT NULL,             -- 模板名称
    description     TEXT DEFAULT '',           -- 描述
    style_prompt    TEXT NOT NULL DEFAULT '',  -- 风格提示词（自然语言）
    sample_output   TEXT DEFAULT '{}',         -- JSON: 示例输出（用于前端预览）
    created_by      INTEGER NOT NULL REFERENCES web_users(id),
    is_default      BOOLEAN DEFAULT FALSE,     -- 是否为默认模板
    is_builtin      BOOLEAN DEFAULT FALSE,     -- 是否为系统内置模板
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_templates_is_default ON templates(is_default) WHERE is_default = TRUE;
```

已有表变更：

```sql
ALTER TABLE extraction_results ADD COLUMN template_id TEXT REFERENCES templates(id);
ALTER TABLE transcription_results ADD COLUMN template_id TEXT REFERENCES templates(id);
ALTER TABLE background_tasks ADD COLUMN template_id TEXT;
```

### 3.4 后端 API

#### 新增路由

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/api/templates` | 列出所有模板 | 登录用户 |
| GET | `/api/templates/{id}` | 获取单个模板详情 | 登录用户 |
| POST | `/api/templates` | 创建模板 | 登录用户 |
| PUT | `/api/templates/{id}` | 修改模板 | 创建者或 admin |
| DELETE | `/api/templates/{id}` | 删除模板 | 创建者或 admin（不检查引用） |
| POST | `/api/templates/generate-prompt` | 上传 .docx → AI 分析 → 返回建议的 style_prompt | 登录用户 |

#### 现有路由变更

**POST /api/extract**（上传 .docx）：
- 表单新增可选字段 `template_id`

**POST /api/transcribe**（上传录音）：
- 表单新增可选字段 `template_id`

**POST /api/transcribe/url**：
- 表单新增可选字段 `template_id`

### 3.5 Worker 变更

以 `_run_extract_task` 为例：

```
1. 从 background_task 读取 template_id
2. 如果有 template_id：
   a. 从数据库查询 templates 表获取 style_prompt
   b. 在调用 get_llm() 后将 style_prompt 追加到 system prompt 末尾
   c. 正常调用 LLM
3. 如果没有 template_id → 使用默认 prompt（完全向后兼容）
4. 保存结果时，将 template_id 写入结果表
```

```python
# 伪代码
def _run_extract_task(task):
    template_id = task.get("template_id")
    style_prompt = ""
    if template_id:
        tmpl = get_template(template_id)
        style_prompt = tmpl["style_prompt"]
    
    # 原有的 workflow 调用改为可传入 style_prompt
    result = run_meeting_extraction_from_text(
        text, style_prompt=style_prompt
    )
```

`workflow.py` 和 `transcription/workflow.py` 分别增加 `style_prompt` 参数，在构造 system prompt 时追加。

### 3.6 前端变更

#### 新增页面

| 文件 | 说明 |
|------|------|
| `TemplateListView.vue` | 模板列表页（卡片网格），每条显示名称、描述、预览按钮 |
| `TemplateDetailView.vue` | 模板详情页，展示完整信息 + sample_output 渲染 |
| `TemplateEditorView.vue` | 创建/编辑模板 |
| `TemplateCreateFromDocx.vue` | 基于 .docx 示例创建模板的子页面（嵌入 TemplateEditorView） |

#### 新增组件

| 文件 | 说明 |
|------|------|
| `TemplateSelector.vue` | 下拉选择器 + 预览按钮，嵌入 UploadView / TranscribeView |
| `StylePromptEditor.vue` | 风格提示词编辑器，嵌入 TemplateEditorView |

#### 现有页面变更

- **UploadView.vue**：文件选择区下方增加模板选择器
- **TranscribeView.vue**：会议信息表单下方增加模板选择器
- **导航栏**：增加「会议模板」入口

#### TemplateEditorView 交互流程

```
┌─ 页面布局 ──────────────────────────────────────┐
│  模板名称: [________________]                      │
│  描述:    [________________]                      │
│                                                   │
│  ┌─ 风格提示词 ────────────────────────────────┐  │
│  │ [多行文本框，用户可编辑]                       │  │
│  │                                               │  │
│  │ 上传示例会议纪要自动生成 ↗                    │  │
│  └──────────────────────────────────────────────┘  │
│                                                   │
│  ┌─ 上传示例文档 ──────────────────────────────┐  │
│  │ 拖拽 .docx 到这里                              │  │
│  │ 或点击选择文件                                  │  │
│  │ [AI 分析] 按钮 → 自动填充上方文本框            │  │
│  └──────────────────────────────────────────────┘  │
│                                                   │
│  ┌─ 示例输出（预览用） ────────────────────────┐  │
│  │ [格式化 JSON 编辑器]                           │  │
│  └──────────────────────────────────────────────┘  │
│                                                   │
│  [保存]                                           │
└───────────────────────────────────────────────────┘
```

### 3.7 权限模型

```
全员可见  → GET /api/templates
创建      → POST /api/templates（所有登录用户）
修改      → PUT /api/templates/{id}（仅创建者或 admin）
删除      → DELETE /api/templates/{id}（仅创建者或 admin，不检查引用）
内置模板  → is_builtin = true 时不可修改/删除
```

---

## 4. TODOLIST

### 第一阶段：数据库与后端基础设施

- [ ] 新建 `templates` 表，包含字段：id, name, description, style_prompt, sample_output, created_by, is_default, is_builtin, created_at, updated_at
- [ ] `init_db()` 自动创建 templates 表
- [ ] 为 `extraction_results` 加 `template_id` 列
- [ ] 为 `transcription_results` 加 `template_id` 列
- [ ] 为 `background_tasks` 加 `template_id` 列
- [ ] `web/models.py` 新增模板 CRUD：create_template, get_template, list_templates, update_template, delete_template

### 第二阶段：模板管理 API

- [ ] `GET /api/templates` — 列出所有模板
- [ ] `GET /api/templates/{id}` — 模板详情
- [ ] `POST /api/templates` — 创建模板
- [ ] `PUT /api/templates/{id}` — 更新模板（权限校验）
- [ ] `DELETE /api/templates/{id}` — 删除模板（权限校验，不检查引用）
- [ ] `POST /api/templates/generate-prompt` — 上传 .docx → 读取全文 → 调用 LLM 分析 → 返回建议的 style_prompt

### 第三阶段：模板注入

- [ ] `workflow.py` 中的 `_extract_from_meeting_text()` 增加 `style_prompt` 参数，追加到 SYSTEM_PROMPT
- [ ] `transcription/workflow.py` 中的 `run_transcription_extraction()` 增加 `style_prompt` 参数追加到 GENERATE_SYSTEM_PROMPT
- [ ] 修改 `POST /api/extract` 接受可选 `template_id`
- [ ] 修改 `POST /api/transcribe` 接受可选 `template_id`
- [ ] 修改 `POST /api/transcribe/url` 接受可选 `template_id`
- [ ] Worker: `_run_extract_task` 读取 template_id → 加载 style_prompt → 传入 workflow
- [ ] Worker: `_run_transcribe_task` 读取 template_id → 加载 style_prompt → 传入 workflow
- [ ] 保存结果时将 `template_id` 写入结果表

### 第四阶段：前端 — 模板管理

- [ ] `TemplateListView.vue` — 模板卡片网格列表页
- [ ] `TemplateDetailView.vue` — 模板详情 + 示例输出预览
- [ ] `TemplateEditorView.vue` — 创建/编辑模板
  - 名称/描述 表单
  - style_prompt 文本框
  - .docx 上传区域 → "AI 分析" 按钮 → 自动填充文本框
  - sample_output JSON 编辑器
- [ ] 导航栏增加「会议模板」入口

### 第五阶段：前端 — 模板选择

- [ ] `TemplateSelector.vue` 组件（下拉选择 + 预览按钮）
- [ ] `UploadView.vue` 集成模板选择器
- [ ] `TranscribeView.vue` 集成模板选择器

### 第六阶段：内置模板

- [ ] 预置「景枫周列会」模板（is_builtin = true），编写默认 style_prompt
- [ ] 系统启动时自动 seed 内置模板

### 第七阶段：收尾

- [ ] 端到端测试：创建模板 → 上传录音选模板 → 生成 → 查看正文风格是否符合
- [ ] 端到端测试：不选模板 → 走默认逻辑 → 不受影响
- [ ] 端到端测试：上传 .docx 示例 → AI 分析 → 生成 style_prompt

---

## 5. 工作量预估

| 阶段 | 内容 | 预估 |
|------|------|------|
| 一 | 数据库 + models CRUD | 0.5 天 |
| 二 | 模板管理 API + generate-prompt | 1 天 |
| 三 | 模板注入 + worker 改造 | 1 天 |
| 四 | 前端模板管理页面 | 2 天 |
| 五 | 前端模板选择器 + 集成 | 0.5 天 |
| 六 | 内置模板 seed | 0.25 天 |
| 七 | 测试 + 收尾 | 0.75 天 |
| **总计** | | **~6 天** |
