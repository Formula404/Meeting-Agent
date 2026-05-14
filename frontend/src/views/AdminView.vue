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
          <span class="card-count">{{ users.length }}</span>
        </h2>
        <span class="card-actions">
          <button class="btn btn-primary btn-sm" @click.stop="showUserForm = true">+ 添加用户</button>
          <span class="chevron" :class="{ open: !collapsed.users }">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </span>
      </div>

      <div v-show="!collapsed.users">
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
              <tr v-for="u in users" :key="u.id">
                <td><span style="font-weight:500">{{ u.name }}</span></td>
                <td><code>{{ u.userid }}</code></td>
                <td class="text-sm text-muted">{{ u.department_name || '-' }}</td>
                <td>
                  <button class="btn btn-ghost btn-sm btn-danger-text" @click="deleteUser(u.id)">删除</button>
                </td>
              </tr>
              <tr v-if="!users.length">
                <td colspan="4" class="text-center text-muted text-sm" style="padding:32px 0">暂无用户数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Add user form -->
        <div v-if="showUserForm" class="inline-form">
          <div class="schedule-grid">
            <div class="form-group">
              <label class="form-label">姓名</label>
              <input class="form-input" v-model="userForm.name" placeholder="中文姓名" />
            </div>
            <div class="form-group">
              <label class="form-label">UserID</label>
              <input class="form-input" v-model="userForm.userid" placeholder="企业微信 userid" />
            </div>
            <div class="form-group">
              <label class="form-label">部门</label>
              <input class="form-input" v-model="userForm.department_name" placeholder="所属部门" />
            </div>
          </div>
          <div class="flex gap-2">
            <button class="btn btn-primary btn-sm" @click="addUser">保存</button>
            <button class="btn btn-outline btn-sm" @click="showUserForm = false">取消</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Web Users (login accounts) ── -->
    <div class="card">
      <div class="card-header flex-between" @click="toggleSection('webUsers')">
        <h2 class="card-title" style="margin:0;border:none;padding:0">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          注册账号管理
          <span class="card-count">{{ webUsers.length }}</span>
        </h2>
        <span class="card-actions">
          <button class="btn btn-primary btn-sm" @click.stop="showWebUserForm = true">+ 添加账号</button>
          <span class="chevron" :class="{ open: !collapsed.webUsers }">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </span>
      </div>

      <div v-show="!collapsed.webUsers">
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
              <tr v-for="u in webUsers" :key="u.id">
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
              <tr v-if="!webUsers.length">
                <td colspan="5" class="text-center text-muted text-sm" style="padding:32px 0">暂无注册账号</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Add web user form -->
        <div v-if="showWebUserForm" class="inline-form">
          <div class="schedule-grid">
            <div class="form-group">
              <label class="form-label">用户名</label>
              <input class="form-input" v-model="webUserForm.username" placeholder="登录用户名" />
            </div>
            <div class="form-group">
              <label class="form-label">密码</label>
              <input class="form-input" type="password" v-model="webUserForm.password" placeholder="至少 6 位" />
            </div>
            <div class="form-group">
              <label class="form-label">部门</label>
              <input class="form-input" v-model="webUserForm.department_name" placeholder="所属部门" />
            </div>
            <div class="form-group">
              <label class="form-label">角色</label>
              <select class="form-input" v-model="webUserForm.role">
                <option value="user">用户</option>
                <option value="admin">管理员</option>
              </select>
            </div>
          </div>
          <div class="flex gap-2">
            <button class="btn btn-primary btn-sm" @click="addWebUser">保存</button>
            <button class="btn btn-outline btn-sm" @click="showWebUserForm = false">取消</button>
          </div>
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
          <span class="card-count">{{ departments.length }}</span>
        </h2>
        <span class="card-actions">
          <button class="btn btn-primary btn-sm" @click.stop="showDeptForm = true">+ 添加部门</button>
          <span class="chevron" :class="{ open: !collapsed.departments }">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </span>
      </div>

      <div v-show="!collapsed.departments">
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
              <tr v-for="d in departments" :key="d.id">
                <td><span style="font-weight:500">{{ d.name }}</span></td>
                <td><code>{{ d.dept_id }}</code></td>
                <td>
                  <button class="btn btn-ghost btn-sm btn-danger-text" @click="deleteDept(d.id)">删除</button>
                </td>
              </tr>
              <tr v-if="!departments.length">
                <td colspan="3" class="text-center text-muted text-sm" style="padding:32px 0">暂无部门数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Add dept form -->
        <div v-if="showDeptForm" class="inline-form">
          <div class="schedule-grid">
            <div class="form-group">
              <label class="form-label">部门名称</label>
              <input class="form-input" v-model="deptForm.name" placeholder="部门中文名称" />
            </div>
            <div class="form-group">
              <label class="form-label">部门 ID</label>
              <input class="form-input" v-model.number="deptForm.dept_id" placeholder="企业微信部门 ID" type="number" />
            </div>
          </div>
          <div class="flex gap-2">
            <button class="btn btn-primary btn-sm" @click="addDept">保存</button>
            <button class="btn btn-outline btn-sm" @click="showDeptForm = false">取消</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/index.js'

const flash = ref('')
const flashType = ref('flash-info')
const users = ref([])
const webUsers = ref([])
const departments = ref([])

const collapsed = ref({ users: false, webUsers: false, departments: false })
function toggleSection(name) {
  collapsed.value[name] = !collapsed.value[name]
}

// WeCom User form
const showUserForm = ref(false)
const userForm = ref({ name: '', userid: '', department_name: '' })

// Web User form
const showWebUserForm = ref(false)
const webUserForm = ref({ username: '', password: '', department_name: '', role: 'user' })

// Dept form
const showDeptForm = ref(false)
const deptForm = ref({ name: '', dept_id: '' })

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

async function addWebUser() {
  try {
    await api.createWebUser(webUserForm.value)
    webUserForm.value = { username: '', password: '', department_name: '', role: 'user' }
    showWebUserForm.value = false
    await refresh()
    setFlash('注册账号添加成功', 'flash-success')
  } catch (e) {
    setFlash(e.message, 'flash-error')
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

async function addUser() {
  try {
    await api.createUser(userForm.value)
    userForm.value = { name: '', userid: '', department_name: '' }
    showUserForm.value = false
    await refresh()
    setFlash('用户添加成功', 'flash-success')
  } catch (e) {
    setFlash(e.message, 'flash-error')
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

async function addDept() {
  try {
    await api.createDepartment({
      name: deptForm.value.name,
      dept_id: Number(deptForm.value.dept_id),
    })
    deptForm.value = { name: '', dept_id: '' }
    showDeptForm.value = false
    await refresh()
    setFlash('部门添加成功', 'flash-success')
  } catch (e) {
    setFlash(e.message, 'flash-error')
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

function setFlash(msg, type) {
  flash.value = msg
  flashType.value = type
  setTimeout(() => { flash.value = '' }, 4000)
}
</script>

<style scoped>
.inline-form {
  margin-top: var(--space-4);
  padding: var(--space-5);
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
}

.inline-form .form-group {
  margin-bottom: 0;
}

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

.card-header {
  cursor: pointer;
  user-select: none;
}

.card-header:hover .chevron {
  opacity: 0.7;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
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
