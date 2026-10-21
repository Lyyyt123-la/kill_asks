const BASE = '/api'

async function request(path, options = {}) {
  const resp = await fetch(BASE + path, options)
  let data = null
  try {
    data = await resp.json()
  } catch (e) {
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

export const api = {
  health: () => request('/health'),
  listDatasets: () => request('/datasets'),
  getDataset: (id) => request(`/datasets/${id}`),
  preview: (id, limit = 50) => request(`/datasets/${id}/preview?limit=${limit}`),
  loadDemo: () => request('/datasets/demo', { method: 'POST' }),
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/datasets/upload', { method: 'POST', body: form })
  },
  chat: (payload) => jsonPost('/chat', payload),
  runSql: (payload) => jsonPost('/query', payload)
}
