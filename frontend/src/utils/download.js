const DEFAULT_FILENAME = '最终导入表.xls'

const getHeader = (headers, name) => {
  if (!headers) return ''
  if (typeof headers.get === 'function') return headers.get(name) || ''
  return headers[name] || headers[name.toLowerCase()] || ''
}

const safeDecodeURIComponent = (value) => {
  try { return decodeURIComponent(value) } catch { return value }
}

const sanitizeFilename = (value) => {
  if (/[\\/]/.test(value)) return DEFAULT_FILENAME
  const basename = value.replace(/[\u0000-\u001f<>:"|?*]/g, '').trim()
  return /\.(xls|xlsx|csv)$/i.test(basename) ? basename : DEFAULT_FILENAME
}

export const getDownloadFilename = (headers) => {
  const disposition = getHeader(headers, 'content-disposition')
  const encodedMatch = disposition.match(/filename\*\s*=\s*(?:UTF-8'')?([^;]+)/i)
  if (encodedMatch) return sanitizeFilename(safeDecodeURIComponent(encodedMatch[1].trim().replace(/^"|"$/g, '')))

  const filenameMatch = disposition.match(/filename\s*=\s*(?:"([^"]+)"|([^;]+))/i)
  if (filenameMatch) return sanitizeFilename((filenameMatch[1] || filenameMatch[2]).trim())
  return DEFAULT_FILENAME
}

export const downloadResponseBlob = (response) => {
  const url = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = getDownloadFilename(response.headers)
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
