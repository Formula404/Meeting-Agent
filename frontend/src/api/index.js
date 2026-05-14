const BASE = '/api'

function getToken() {
  return localStorage.getItem('token')
}

function authHeaders() {
  const token = getToken()
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

async function handleResponse(res) {
  if (res.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error(data?.detail || `HTTP ${res.status}`)
  }
  return data
}

async function request(path, options = {}) {
  const url = `${BASE}${path}`
  const config = {
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    ...options,
  }
  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body)
  }
  if (config.body instanceof FormData) {
    delete config.headers['Content-Type']
  }

  const res = await fetch(url, config)
  return handleResponse(res)
}

async function requestWithStatus(path, options = {}) {
  const url = `${BASE}${path}`
  const config = {
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    ...options,
  }
  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body)
  }
  if (config.body instanceof FormData) {
    delete config.headers['Content-Type']
  }

  const res = await fetch(url, config)
  let data = null
  try {
    data = await res.json()
  } catch (_) {
    data = null
  }
  if (res.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
  }
  return { ok: res.ok, status: res.status, data, statusText: res.statusText }
}

export default {
  // ── Auth ──
  login(username, password) {
    return request('/auth/login', { method: 'POST', body: { username, password } })
  },

  register(username, password, department_name) {
    return request('/auth/register', { method: 'POST', body: { username, password, department_name } })
  },

  getMe() {
    return request('/auth/me')
  },

  logout() {
    return request('/auth/logout', { method: 'POST' })
  },

  // ── Extraction ──
  uploadFile(file, pdfFile) {
    const form = new FormData()
    form.append('file', file)
    if (pdfFile) {
      form.append('pdf_file', pdfFile)
    }
    return request('/extract', { method: 'POST', body: form })
  },

  uploadPdf(resultId, pdfFile) {
    const form = new FormData()
    form.append('pdf_file', pdfFile)
    return request(`/results/${resultId}/upload-pdf`, { method: 'POST', body: form })
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

  deleteResult(id) {
    return requestWithStatus(`/results/${id}`, { method: 'DELETE' }).then(async (resp) => {
      if (resp.ok) return resp.data
      if (resp.status === 405) {
        return request(`/results/${id}/delete`, { method: 'POST' })
      }
      throw new Error((resp.data && resp.data.detail) || resp.statusText || `HTTP ${resp.status}`)
    })
  },

  // ── Users ──
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

  // ── Departments ──
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

  // ── Transcription ──
  transcribeFile(file, customPrompt) {
    const form = new FormData()
    form.append('file', file)
    form.append('custom_prompt', customPrompt)
    return request('/transcribe', { method: 'POST', body: form })
  },

  getTranscription(id) {
    return request(`/transcribe/${id}`)
  },

  updateTranscription(id, result) {
    return request(`/transcribe/${id}`, { method: 'PUT', body: { result } })
  },

  exportTranscriptionDocx(id) {
    const token = getToken()
    const url = `${BASE}/transcribe/${id}/export-docx`
    const a = document.createElement('a')
    a.href = url
    // Attach auth header via fetch + blob download
    fetch(url, { headers: { ...authHeaders() } }).then(res => {
      if (!res.ok) throw new Error('导出失败')
      return res.blob()
    }).then(blob => {
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = `${id}.docx`
      link.click()
      URL.revokeObjectURL(blobUrl)
    }).catch(err => {
      console.error('导出失败:', err)
      alert('导出失败')
    })
    return Promise.resolve()
  },

  pushTranscription(id) {
    return request(`/transcribe/${id}/push`, { method: 'POST' })
  },

  deleteTranscription(id) {
    return request(`/transcribe/${id}`, { method: 'DELETE' }).catch((err) => {
      return request(`/transcribe/${id}/delete`, { method: 'POST' })
    })
  },
}
