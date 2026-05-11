<template>
  <div>
    <h1 class="page-title">用户与部门管理</h1>

    <div v-if="flash" class="flash" :class="flashType">{{ flash }}</div>

    <!-- ── Users ── -->
    <div class="card">
      <div class="flex-between mb-12">
        <h2 class="card-title" style="margin:0;border:none;padding:0">用户列表</h2>
        <button class="btn btn-primary btn-sm" @click="showUserForm = true">+ 添加用户</button>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>姓名</th>
            <th>UserID</th>
            <th>部门</th>
            <th style="width:100px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.name }}</td>
            <td><code>{{ u.userid }}</code></td>
            <td class="text-sm text-muted">{{ u.department_name || '-' }}</td>
            <td>
              <button class="btn btn-danger btn-sm" @click="deleteUser(u.id)">删除</button>
            </td>
          </tr>
          <tr v-if="!users.length">
            <td colspan="4" class="text-center text-muted text-sm">暂无用户数据</td>
          </tr>
        </tbody>
      </table>

      <!-- Add user form -->
      <div v-if="showUserForm" class="card" style="margin-top:16px;padding:16px;background:#f8fafc">
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
        <div class="flex gap-8">
          <button class="btn btn-primary btn-sm" @click="addUser">保存</button>
          <button class="btn btn-outline btn-sm" @click="showUserForm = false">取消</button>
        </div>
      </div>
    </div>

    <!-- ── Departments ── -->
    <div class="card">
      <div class="flex-between mb-12">
        <h2 class="card-title" style="margin:0;border:none;padding:0">部门列表</h2>
        <button class="btn btn-primary btn-sm" @click="showDeptForm = true">+ 添加部门</button>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>部门名称</th>
            <th>部门 ID</th>
            <th style="width:100px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in departments" :key="d.id">
            <td>{{ d.name }}</td>
            <td><code>{{ d.dept_id }}</code></td>
            <td>
              <button class="btn btn-danger btn-sm" @click="deleteDept(d.id)">删除</button>
            </td>
          </tr>
          <tr v-if="!departments.length">
            <td colspan="3" class="text-center text-muted text-sm">暂无部门数据</td>
          </tr>
        </tbody>
      </table>

      <!-- Add dept form -->
      <div v-if="showDeptForm" class="card" style="margin-top:16px;padding:16px;background:#f8fafc">
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
        <div class="flex gap-8">
          <button class="btn btn-primary btn-sm" @click="addDept">保存</button>
          <button class="btn btn-outline btn-sm" @click="showDeptForm = false">取消</button>
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
const departments = ref([])

// User form
const showUserForm = ref(false)
const userForm = ref({ name: '', userid: '', department_name: '' })

// Dept form
const showDeptForm = ref(false)
const deptForm = ref({ name: '', dept_id: '' })

onMounted(() => {
  refresh()
})

async function refresh() {
  try {
    const [u, d] = await Promise.all([
      api.listUsers(),
      api.listDepartments(),
    ])
    users.value = u
    departments.value = d
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
