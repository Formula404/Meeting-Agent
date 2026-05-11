const BASE = '/api'

async function request(path, options = {}) {
  const url = `${BASE}${path}`
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  }
  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body)
  }
  if (config.body instanceof FormData) {
    delete config.headers['Content-Type']
  }

  const res = await fetch(url, config)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export default {
  // Extraction
  uploadFile(file) {
    const form = new FormData()
    form.append('file', file)
    return request('/extract', { method: 'POST', body: form })
  },

  listResults() {
    return request('/results')
  },

  getResult(id) {
    return request(`/results/${id}`)
  },

  updateResult(id, result) {
    return request(`/results/${id}`, { method: 'PUT', body: { result } })
  },

  pushResult(id) {
    return request(`/results/${id}/push`, { method: 'POST' })
  },

  // Users
  listUsers() {
    return request('/users')
  },

  createUser(body) {
    return request('/users', { method: 'POST', body })
  },

  updateUser(id, body) {
    return request(`/users/${id}`, { method: 'PUT', body })
  },

  deleteUser(id) {
    return request(`/users/${id}`, { method: 'DELETE' })
  },

  // Departments
  listDepartments() {
    return request('/departments')
  },

  createDepartment(body) {
    return request('/departments', { method: 'POST', body })
  },

  updateDepartment(id, body) {
    return request(`/departments/${id}`, { method: 'PUT', body })
  },

  deleteDepartment(id) {
    return request(`/departments/${id}`, { method: 'DELETE' })
  },
}
