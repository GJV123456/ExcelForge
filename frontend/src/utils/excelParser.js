import * as XLSX from 'xlsx'

const normalize = (value) => String(value ?? '').trim()
const typeAHeaders = ['测试内容', '类型']
const typeBHeaders = ['设备编码', '设备类型', '设备中文']
const lineEquipmentCodePattern = /[A-Z]\d+[A-Z]\d+[A-Z]\d+/gi
const hyphenEquipmentCodePattern = /(?:[A-Z0-9]+-)+[A-Z0-9]+/gi
const getMissingHeaders = (headers, requiredHeaders) => requiredHeaders.filter((key) => !headers.includes(key))
const formatHeaders = (headers) => headers.length ? headers.join('、') : '无'
const createHeaderError = (headers) => {
  const names = headers.map(normalize).filter(Boolean)
  if (!names.length) return new Error('未检测到表头：请确认 Excel 第 1 行是表头，并且文件内容不为空。')

  const matchedA = typeAHeaders.filter((key) => names.includes(key))
  const matchedB = typeBHeaders.filter((key) => names.includes(key))
  const typeAMissing = getMissingHeaders(names, typeAHeaders)
  const typeBMissing = getMissingHeaders(names, typeBHeaders)

  if (matchedA.length > matchedB.length) {
    return new Error(`表头不匹配：人工处理版缺少「${formatHeaders(typeAMissing)}」。当前表头：${formatHeaders(names)}。`)
  }

  if (matchedB.length > matchedA.length) {
    return new Error(`表头不匹配：原始设备版缺少「${formatHeaders(typeBMissing)}」。当前表头：${formatHeaders(names)}。`)
  }

  return new Error(`表头不匹配：第 1 行需要包含「${typeAHeaders.join('、')}」或「${typeBHeaders.join('、')}」。当前表头：${formatHeaders(names)}。`)
}

export function detectExcelType(headers) {
  const names = headers.map(normalize)
  if (typeAHeaders.every((key) => names.includes(key))) return 'A'
  if (typeBHeaders.every((key) => names.includes(key))) return 'B'
  return ''
}

export async function parseExcel(file) {
  const data = await file.arrayBuffer()
  const workbook = XLSX.read(data, { type: 'array' })
  const sheet = workbook.Sheets[workbook.SheetNames[0]]
  if (!sheet) throw createHeaderError([])
  const matrix = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })
  const headers = (matrix[0] || []).map(normalize).filter(Boolean)
  const excelType = detectExcelType(headers)
  if (!excelType) throw createHeaderError(headers)
  const rows = matrix.slice(1).filter((row) => row.some((cell) => normalize(cell))).map((row, index) => ({
    sortIndex: index + 1,
    ...Object.fromEntries(headers.map((header, headerIndex) => [header, normalize(row[headerIndex])]))
  }))
  return { headers, rows, excelType }
}

export function buildContent(row, rules) {
  return rules.map((rule) => {
    if (rule.type !== 'field') return rule.value
    const value = normalize(row[rule.value])
    return value || ''
  }).join('')
}

export function extractEquipmentCode(content) {
  const text = normalize(content)
  const lineMatches = text.match(lineEquipmentCodePattern)
  if (lineMatches?.length) return lineMatches[0].toUpperCase()
  const hyphenMatches = text.match(hyphenEquipmentCodePattern)
  return hyphenMatches?.[0]?.toUpperCase() || ''
}
