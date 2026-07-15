<template>
  <div>
    <h1 class="page-title">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:8px">
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
        <circle cx="12" cy="12" r="3"/>
      </svg>
      用户与部门管理
    </h1>

    <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>

    <!-- ── Users ── -->
    <div class="card">
      <div class="card-header flex-between" @click="toggleSection('users')">
        <h2 class="card-title" style="margin:0;border:none;padding:0">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          用户列表
          <span class="card-count">{{ filteredUsers.length }}</span>
        </h2>
        <span class="card-actions">
          <button class="btn btn-primary btn-sm" @click.stop="openUserModal()">+ 添加用户</button>
          <span class="chevron" :class="{ open: !collapsed.users }">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </span>
      </div>

      <div v-show="!collapsed.users">
        <div class="search-bar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input class="form-input search-input" v-model="userSearch" placeholder="搜索姓名、UserID 或部门..." />
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>姓名</th>
                <th>UserID</th>
                <th>部门</th>
                <th style="width:80px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in filteredUsers" :key="u.id">
                <td><span style="font-weight:500">{{ u.name }}</span></td>
                <td><code>{{ u.userid }}</code></td>
                <td class="text-sm text-muted">{{ u.department_name || '-' }}</td>
                <td>
                  <button class="btn btn-ghost btn-sm btn-danger-text" @click="deleteUser(u.id)">删除</button>
                </td>
              </tr>
              <tr v-if="!filteredUsers.length">
                <td colspan="4" class="text-center text-muted text-sm" style="padding:32px 0">
                  {{ userSearch ? '无匹配结果' : '暂无用户数据' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Web Users ── -->
    <div class="card">
      <div class="card-header flex-between" @click="toggleSection('webUsers')">
        <h2 class="card-title" style="margin:0;border:none;padding:0">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          注册账号管理
          <span class="card-count">{{ filteredWebUsers.length }}</span>
        </h2>
        <span class="card-actions">
          <button class="btn btn-primary btn-sm" @click.stop="openWebUserModal()">+ 添加账号</button>
          <span class="chevron" :class="{ open: !collapsed.webUsers }">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </span>
      </div>

      <div v-show="!collapsed.webUsers">
        <div class="search-bar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input class="form-input search-input" v-model="webUserSearch" placeholder="搜索用户名、角色或部门..." />
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>用户名</th>
                <th>角色</th>
                <th>部门</th>
                <th>创建时间</th>
                <th style="width:80px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in filteredWebUsers" :key="u.id">
                <td><span style="font-weight:500">{{ u.username }}</span></td>
                <td>
                  <span class="badge" :class="u.role === 'admin' ? 'badge-admin' : 'badge-user'">
                    {{ u.role === 'admin' ? '管理员' : '用户' }}
                  </span>
                </td>
                <td class="text-sm text-muted">{{ u.department_name || '-' }}</td>
                <td class="text-sm text-muted">{{ u.created_at?.slice(0, 10) || '-' }}</td>
                <td>
                  <button class="btn btn-ghost btn-sm btn-danger-text" @click="deleteWebUser(u.id)">删除</button>
                </td>
              </tr>
              <tr v-if="!filteredWebUsers.length">
                <td colspan="5" class="text-center text-muted text-sm" style="padding:32px 0">
                  {{ webUserSearch ? '无匹配结果' : '暂无注册账号' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Departments ── -->
    <div class="card">
      <div class="card-header flex-between" @click="toggleSection('departments')">
        <h2 class="card-title" style="margin:0;border:none;padding:0">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
          部门列表
          <span class="card-count">{{ filteredDepts.length }}</span>
        </h2>
        <span class="card-actions">
          <button class="btn btn-primary btn-sm" @click.stop="openDeptModal()">+ 添加部门</button>
          <span class="chevron" :class="{ open: !collapsed.departments }">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </span>
      </div>

      <div v-show="!collapsed.departments">
        <div class="search-bar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input class="form-input search-input" v-model="deptSearch" placeholder="搜索部门名称或 ID..." />
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>部门名称</th>
                <th>部门 ID</th>
                <th style="width:80px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in filteredDepts" :key="d.id">
                <td><span style="font-weight:500">{{ d.name }}</span></td>
                <td><code>{{ d.dept_id }}</code></td>
                <td>
                  <button class="btn btn-ghost btn-sm btn-danger-text" @click="deleteDept(d.id)">删除</button>
                </td>
              </tr>
              <tr v-if="!filteredDepts.length">
                <td colspan="3" class="text-center text-muted text-sm" style="padding:32px 0">
                  {{ deptSearch ? '无匹配结果' : '暂无部门数据' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── User Modal ── -->
    <Modal :visible="showUserModal" :title="'添加用户'" size="md" @close="closeUserModal">
      <!-- Single add -->
      <div class="modal-section">
        <h4 class="modal-section-title">单个添加</h4>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">姓名</label>
            <input class="form-input" v-model="userForm.name" placeholder="中文姓名" @keyup.enter="addUser" />
          </div>
          <div class="form-group">
            <label class="form-label">UserID</label>
            <input class="form-input" v-model="userForm.userid" placeholder="企业微信 userid" @keyup.enter="addUser" />
          </div>
          <div class="form-group">
            <label class="form-label">部门</label>
            <input class="form-input" v-model="userForm.department_name" placeholder="所属部门" @keyup.enter="addUser" />
          </div>
        </div>
        <button class="btn btn-primary btn-sm" @click="addUser" :disabled="userAdding">
          {{ userAdding ? '添加中...' : '保存' }}
        </button>
      </div>

      <div class="modal-divider">
        <span>或</span>
      </div>

      <!-- Batch add -->
      <div class="modal-section">
        <h4 class="modal-section-title">批量导入</h4>
        <p class="modal-hint">每行一条，字段用 Tab 或逗号分隔：<code>姓名, UserID, 部门</code></p>
        <textarea
          class="form-input batch-textarea"
          v-model="userBatchText"
          placeholder="张三, zhangsan, 技术部&#10;李四, lisi, 产品部&#10;王五, wangwu, 运营部"
          rows="5"
        ></textarea>
        <button class="btn btn-outline btn-sm" @click="batchAddUsers" :disabled="userAdding">
          {{ userAdding ? `添加中 (${userBatchProgress})...` : '批量导入' }}
        </button>
      </div>
    </Modal>

    <!-- ── Web User Modal ── -->
    <Modal :visible="showWebUserModal" :title="'添加账号'" size="md" @close="closeWebUserModal">
      <div class="modal-section">
        <h4 class="modal-section-title">单个添加</h4>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <input class="form-input" v-model="webUserForm.username" placeholder="登录用户名" @keyup.enter="addWebUser" />
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <input class="form-input" type="password" v-model="webUserForm.password" placeholder="至少 6 位" @keyup.enter="addWebUser" />
          </div>
          <div class="form-group">
            <label class="form-label">部门</label>
            <input class="form-input" v-model="webUserForm.department_name" placeholder="所属部门" @keyup.enter="addWebUser" />
          </div>
          <div class="form-group">
            <label class="form-label">角色</label>
            <select class="form-input" v-model="webUserForm.role">
              <option value="user">用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
        </div>
        <button class="btn btn-primary btn-sm" @click="addWebUser" :disabled="webUserAdding">
          {{ webUserAdding ? '添加中...' : '保存' }}
        </button>
      </div>

      <div class="modal-divider">
        <span>或</span>
      </div>

      <div class="modal-section">
        <h4 class="modal-section-title">批量导入</h4>
        <p class="modal-hint">每行一条，字段用 Tab 或逗号分隔：<code>用户名, 密码, 部门, 角色</code>（角色默认 user，可选 admin）</p>
        <textarea
          class="form-input batch-textarea"
          v-model="webUserBatchText"
          placeholder="alice, pass1234, 技术部, user&#10;bob, pass5678, 产品部, admin"
          rows="5"
        ></textarea>
        <button class="btn btn-outline btn-sm" @click="batchAddWebUsers" :disabled="webUserAdding">
          {{ webUserAdding ? `添加中 (${webUserBatchProgress})...` : '批量导入' }}
        </button>
      </div>
    </Modal>

    <!-- ── Department Modal ── -->
    <Modal :visible="showDeptModal" :title="'添加部门'" size="md" @close="closeDeptModal">
      <div class="modal-section">
        <h4 class="modal-section-title">单个添加</h4>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">部门名称</label>
            <input class="form-input" v-model="deptForm.name" placeholder="部门中文名称" @keyup.enter="addDept" />
          </div>
          <div class="form-group">
            <label class="form-label">部门 ID</label>
            <input class="form-input" v-model.number="deptForm.dept_id" placeholder="企业微信部门 ID" type="number" @keyup.enter="addDept" />
          </div>
        </div>
        <button class="btn btn-primary btn-sm" @click="addDept" :disabled="deptAdding">
          {{ deptAdding ? '添加中...' : '保存' }}
        </button>
      </div>

      <div class="modal-divider">
        <span>或</span>
      </div>

      <div class="modal-section">
        <h4 class="modal-section-title">批量导入</h4>
        <p class="modal-hint">每行一条，字段用 Tab 或逗号分隔：<code>部门名称, 部门ID</code></p>
        <textarea
          class="form-input batch-textarea"
          v-model="deptBatchText"
          placeholder="技术部, 1001&#10;产品部, 1002&#10;运营部, 1003"
          rows="5"
        ></textarea>
        <button class="btn btn-outline btn-sm" @click="batchAddDepts" :disabled="deptAdding">
          {{ deptAdding ? `添加中 (${deptBatchProgress})...` : '批量导入' }}
        </button>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api/index.js'
import Modal from '../components/Modal.vue'

const flash = ref('')
const flashType = ref('flash-info')
const users = ref([])
const webUsers = ref([])
const departments = ref([])

const collapsed = ref({ users: false, webUsers: false, departments: false })
function toggleSection(name) {
  collapsed.value[name] = !collapsed.value[name]
}

// ── Search ──
const userSearch = ref('')
const webUserSearch = ref('')
const deptSearch = ref('')

const filteredUsers = computed(() => {
  const q = userSearch.value.toLowerCase()
  if (!q) return users.value
  return users.value.filter(u =>
    u.name.toLowerCase().includes(q) ||
    u.userid.toLowerCase().includes(q) ||
    (u.department_name || '').toLowerCase().includes(q)
  )
})

const filteredWebUsers = computed(() => {
  const q = webUserSearch.value.toLowerCase()
  if (!q) return webUsers.value
  return webUsers.value.filter(u =>
    u.username.toLowerCase().includes(q) ||
    u.role.toLowerCase().includes(q) ||
    (u.department_name || '').toLowerCase().includes(q)
  )
})

const filteredDepts = computed(() => {
  const q = deptSearch.value.toLowerCase()
  if (!q) return departments.value
  return departments.value.filter(d =>
    d.name.toLowerCase().includes(q) ||
    String(d.dept_id).includes(q)
  )
})

// ── User Modal ──
const showUserModal = ref(false)
const userForm = ref({ name: '', userid: '', department_name: '' })
const userAdding = ref(false)
const userBatchText = ref('')
const userBatchProgress = ref('')

function openUserModal() {
  userForm.value = { name: '', userid: '', department_name: '' }
  userBatchText.value = ''
  showUserModal.value = true
}

function closeUserModal() {
  showUserModal.value = false
}

async function addUser() {
  if (!userForm.value.name || !userForm.value.userid) {
    setFlash('姓名和 UserID 不能为空', 'flash-error')
    return
  }
  userAdding.value = true
  try {
    await api.createUser(userForm.value)
    userForm.value = { name: '', userid: '', department_name: '' }
    await refresh()
    setFlash('用户添加成功', 'flash-success')
  } catch (e) {
    setFlash(e.message, 'flash-error')
  } finally {
    userAdding.value = false
  }
}

function parseBatchLines(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean)
  return lines.map(line => {
    const sep = line.includes('\t') ? '\t' : ','
    return line.split(sep).map(s => s.trim())
  })
}

async function batchAddUsers() {
  if (!userBatchText.value.trim()) {
    setFlash('请输入批量导入内容', 'flash-error')
    return
  }
  const rows = parseBatchLines(userBatchText.value)
  if (!rows.length) {
    setFlash('未解析到有效数据', 'flash-error')
    return
  }
  userAdding.value = true
  let ok = 0
  const errors = []
  for (let i = 0; i < rows.length; i++) {
    const [name, userid, dept = ''] = rows[i]
    if (!name || !userid) {
      errors.push(`第 ${i + 1} 行: 姓名或 UserID 为空`)
      continue
    }
    userBatchProgress.value = `${i + 1}/${rows.length}`
    try {
      await api.createUser({ name, userid, department_name: dept })
      ok++
    } catch (e) {
      errors.push(`第 ${i + 1} 行 (${name}): ${e.message}`)
    }
  }
  userAdding.value = false
  userBatchText.value = ''
  userBatchProgress.value = ''
  await refresh()
  if (errors.length) {
    setFlash(`成功导入 ${ok} 条，${errors.length} 条失败: ${errors.join('; ')}`, 'flash-error')
  } else {
    setFlash(`成功导入 ${ok} 条`, 'flash-success')
  }
}

async function deleteUser(id) {
  if (!confirm('确定删除该用户？')) return
  try {
    await api.deleteUser(id)
    await refresh()
    setFlash('用户已删除', 'flash-success')
  } catch (e) {
    setFlash(e.message, 'flash-error')
  }
}

// ── Web User Modal ──
const showWebUserModal = ref(false)
const webUserForm = ref({ username: '', password: '', department_name: '', role: 'user' })
const webUserAdding = ref(false)
const webUserBatchText = ref('')
const webUserBatchProgress = ref('')

function openWebUserModal() {
  webUserForm.value = { username: '', password: '', department_name: '', role: 'user' }
  webUserBatchText.value = ''
  showWebUserModal.value = true
}

function closeWebUserModal() {
  showWebUserModal.value = false
}

async function addWebUser() {
  if (!webUserForm.value.username || !webUserForm.value.password) {
    setFlash('用户名和密码不能为空', 'flash-error')
    return
  }
  if (webUserForm.value.password.length < 6) {
    setFlash('密码长度不能少于 6 位', 'flash-error')
    return
  }
  webUserAdding.value = true
  try {
    await api.createWebUser(webUserForm.value)
    webUserForm.value = { username: '', password: '', department_name: '', role: 'user' }
    await refresh()
    setFlash('注册账号添加成功', 'flash-success')
  } catch (e) {
    setFlash(e.message, 'flash-error')
  } finally {
    webUserAdding.value = false
  }
}

async function batchAddWebUsers() {
  if (!webUserBatchText.value.trim()) {
    setFlash('请输入批量导入内容', 'flash-error')
    return
  }
  const rows = parseBatchLines(webUserBatchText.value)
  if (!rows.length) {
    setFlash('未解析到有效数据', 'flash-error')
    return
  }
  webUserAdding.value = true
  let ok = 0
  const errors = []
  for (let i = 0; i < rows.length; i++) {
    const [username, password, dept = '', role = 'user'] = rows[i]
    if (!username || !password) {
      errors.push(`第 ${i + 1} 行: 用户名或密码为空`)
      continue
    }
    webUserBatchProgress.value = `${i + 1}/${rows.length}`
    try {
      await api.createWebUser({ username, password, department_name: dept, role })
      ok++
    } catch (e) {
      errors.push(`第 ${i + 1} 行 (${username}): ${e.message}`)
    }
  }
  webUserAdding.value = false
  webUserBatchText.value = ''
  webUserBatchProgress.value = ''
  await refresh()
  if (errors.length) {
    setFlash(`成功导入 ${ok} 条，${errors.length} 条失败: ${errors.join('; ')}`, 'flash-error')
  } else {
    setFlash(`成功导入 ${ok} 条`, 'flash-success')
  }
}

async function deleteWebUser(id) {
  if (!confirm('确定删除该注册账号？')) return
  try {
    await api.deleteWebUser(id)
    await refresh()
    setFlash('注册账号已删除', 'flash-success')
  } catch (e) {
    setFlash(e.message, 'flash-error')
  }
}

// ── Department Modal ──
const showDeptModal = ref(false)
const deptForm = ref({ name: '', dept_id: '' })
const deptAdding = ref(false)
const deptBatchText = ref('')
const deptBatchProgress = ref('')

function openDeptModal() {
  deptForm.value = { name: '', dept_id: '' }
  deptBatchText.value = ''
  showDeptModal.value = true
}

function closeDeptModal() {
  showDeptModal.value = false
}

async function addDept() {
  if (!deptForm.value.name || !deptForm.value.dept_id) {
    setFlash('部门名称和部门 ID 不能为空', 'flash-error')
    return
  }
  deptAdding.value = true
  try {
    await api.createDepartment({
      name: deptForm.value.name,
      dept_id: Number(deptForm.value.dept_id),
    })
    deptForm.value = { name: '', dept_id: '' }
    await refresh()
    setFlash('部门添加成功', 'flash-success')
  } catch (e) {
    setFlash(e.message, 'flash-error')
  } finally {
    deptAdding.value = false
  }
}

async function batchAddDepts() {
  if (!deptBatchText.value.trim()) {
    setFlash('请输入批量导入内容', 'flash-error')
    return
  }
  const rows = parseBatchLines(deptBatchText.value)
  if (!rows.length) {
    setFlash('未解析到有效数据', 'flash-error')
    return
  }
  deptAdding.value = true
  let ok = 0
  const errors = []
  for (let i = 0; i < rows.length; i++) {
    const [name, deptIdStr] = rows[i]
    const dept_id = Number(deptIdStr)
    if (!name || !deptIdStr || isNaN(dept_id)) {
      errors.push(`第 ${i + 1} 行: 部门名称或 ID 无效`)
      continue
    }
    deptBatchProgress.value = `${i + 1}/${rows.length}`
    try {
      await api.createDepartment({ name, dept_id })
      ok++
    } catch (e) {
      errors.push(`第 ${i + 1} 行 (${name}): ${e.message}`)
    }
  }
  deptAdding.value = false
  deptBatchText.value = ''
  deptBatchProgress.value = ''
  await refresh()
  if (errors.length) {
    setFlash(`成功导入 ${ok} 条，${errors.length} 条失败: ${errors.join('; ')}`, 'flash-error')
  } else {
    setFlash(`成功导入 ${ok} 条`, 'flash-success')
  }
}

async function deleteDept(id) {
  if (!confirm('确定删除该部门？')) return
  try {
    await api.deleteDepartment(id)
    await refresh()
    setFlash('部门已删除', 'flash-success')
  } catch (e) {
    setFlash(e.message, 'flash-error')
  }
}

// ── Common ──
onMounted(() => {
  refresh()
})

async function refresh() {
  try {
    const [u, wu, d] = await Promise.all([
      api.listUsers(),
      api.listWebUsers(),
      api.listDepartments(),
    ])
    users.value = u
    webUsers.value = wu
    departments.value = d
  } catch (e) {
    setFlash(e.message, 'flash-error')
  }
}

function setFlash(msg, type) {
  flash.value = msg
  flashType.value = type
  setTimeout(() => { flash.value = '' }, 4000)
}
</script>

<style scoped>
/* ── Search ── */
.search-bar {
  position: relative;
  margin-bottom: var(--space-3);
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--gray-400);
  pointer-events: none;
}

.search-input {
  padding-left: 36px !important;
}

/* ── Modal content ── */
.modal-section {
  margin-bottom: var(--space-4);
}

.modal-section-title {
  margin: 0 0 var(--space-3) 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-700);
}

.modal-hint {
  margin: 0 0 var(--space-2) 0;
  font-size: 12px;
  color: var(--gray-500);
}

.modal-hint code {
  font-size: 11px;
  background: var(--gray-100);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
}

.modal-divider {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: var(--space-4) 0;
  color: var(--gray-400);
  font-size: 12px;
}

.modal-divider::before,
.modal-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--gray-200);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.form-grid .form-group {
  margin-bottom: 0;
}

.batch-textarea {
  width: 100%;
  resize: vertical;
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: var(--space-3);
}

@media (max-width: 480px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

/* ── Badge ── */
.badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
}

.badge-admin {
  background: #fef3c7;
  color: #92400e;
}

.badge-user {
  background: #dbeafe;
  color: #1e40af;
}

/* ── Card ── */
.card-header {
  cursor: pointer;
  user-select: none;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.card-header:hover .chevron {
  opacity: 0.7;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

@media (max-width: 480px) {
  .card-actions .btn {
    font-size: 11px;
    padding: 5px 8px;
  }
}

.chevron {
  display: flex;
  align-items: center;
  color: var(--gray-400);
  transition: transform 0.2s ease;
}

.chevron.open {
  transform: rotate(180deg);
}

.card-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-full);
  background: var(--gray-100);
  color: var(--gray-500);
  vertical-align: middle;
  margin-left: 6px;
}
</style>
