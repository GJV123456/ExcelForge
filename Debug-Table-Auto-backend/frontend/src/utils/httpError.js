const fallbackByStatus = (status) => {
  if (status === 400) return '请求内容不符合业务要求'
  if (status === 422) return '提交参数校验失败'
  if (status >= 500) return '文件生成失败'
  return '请求处理失败'
}

const parseData = async (data) => {
  if (typeof Blob !== 'undefined' && data instanceof Blob) {
    const text = await data.text()
    if (!text) return null
    try { return JSON.parse(text) } catch { return { detail: text } }
  }
  if (typeof data === 'string') {
    try { return JSON.parse(data) } catch { return { detail: data } }
  }
  return data && typeof data === 'object' ? data : null
}

export const getApiErrorMessage = async (error) => {
  if (typeof error?.publicMessage === 'string') return error.publicMessage
  if (!error?.response) return '服务器连接失败'
  try {
    const data = await parseData(error.response.data)
    if (typeof data?.detail === 'string' && data.detail.trim()) return data.detail
  } catch {
    // Fall through to the status-specific public message.
  }
  return fallbackByStatus(error.response.status)
}
