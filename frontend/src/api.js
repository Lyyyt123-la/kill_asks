const BASE = '/api'

function readAccessCode() {
  try {
    const url = new URL(window.location.href)
    const code = url.searchParams.get('code')
    if (code) {
      localStorage.setItem('askdata_access_code', code)
      return code
    }
    return localStorage.getItem('askdata_access_code') || ''
  } catch (error) {
    return ''
  }
}

const ACCESS_CODE = readAccessCode()

function buildHeaders(extra = {}) {
  const headers = { ...extra }
  if (ACCESS_CODE) headers['X-Access-Code'] = ACCESS_CODE
  return headers
}

async function request(path, options = {}) {
  const opts = { ...options, headers: buildHeaders(options.headers || {}) }
  const resp = await fetch(BASE + path, opts)
  let data = null
  try {
    data = await resp.json()
  } catch (error) {
    data = null
  }
  if (!resp.ok) {
    const detail = data && data.detail
    let message = `请求失败（HTTP ${resp.status}）`
    if (typeof detail === 'string') message = detail
    else if (Array.isArray(detail) && detail.length) message = detail[0].msg || message
    else if (detail) message = JSON.stringify(detail)
    throw new Error(message)
  }
  return data
}

function jsonPost(path, payload) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

function uploadFile(path, file) {
  const form = new FormData()
  form.append('file', file)
  return request(path, { method: 'POST', body: form })
}

export const api = {
  health: () => request('/health'),
  // 数据集
  listDatasets: () => request('/datasets'),
  getDataset: (id) => request(`/datasets/${id}`),
  preview: (id, limit = 50) => request(`/datasets/${id}/preview?limit=${limit}`),
  loadDemo: () => request('/datasets/demo', { method: 'POST' }),
  upload: (file) => uploadFile('/datasets/upload', file),
  // 对话
  chat: (payload) => jsonPost('/chat', payload),
  runSql: (payload) => jsonPost('/query', payload),
  // 文档 / 图片
  listDocuments: () => request('/documents'),
  getDocument: (id) => request(`/documents/${id}`),
  uploadDocument: (file) => uploadFile('/documents/upload', file),
  askDocument: (id, payload) => jsonPost(`/documents/${id}/ask`, payload),
  deleteDocument: (id) => request(`/documents/${id}`, { method: 'DELETE' })
}
