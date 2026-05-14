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

async function requestWithStatus(path, options = {}) {
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
  let data = null
  try {
    data = await res.json()
  } catch (_) {
    data = null
  }
  return { ok: res.ok, status: res.status, data, statusText: res.statusText }
}

export default {
  // Extraction
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

  // Transcription (录音转文字)
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
    const url = `${BASE}/transcribe/${id}/export-docx`
    // Direct download via link click
    const a = document.createElement('a')
    a.href = url
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    return Promise.resolve()
  },

  pushTranscription(id) {
    return request(`/transcribe/${id}/push`, { method: 'POST' })
  },

  deleteTranscription(id) {
    return request(`/transcribe/${id}`, { method: 'DELETE' }).catch((err) => {
      // Fallback if DELETE is blocked
      return request(`/transcribe/${id}/delete`, { method: 'POST' })
    })
  },
}
