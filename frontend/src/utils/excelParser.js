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
  const typeAMissing = getMissingHeaders(names, typeAHeaders)
  const typeBMissing = getMissingHeaders(names, typeBHeaders)
  return new Error([
    '未检测到有效表头，请检查 Excel 第一行。',
    `当前检测到：${formatHeaders(names)}。`,
    `类型A（人工处理版）必须包含：${typeAHeaders.join('、')}；缺少：${formatHeaders(typeAMissing)}。`,
    `类型B（原始设备版）必须包含：${typeBHeaders.join('、')}；缺少：${formatHeaders(typeBMissing)}。`
  ].join('\n'))
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
  return rules.map((rule) => rule.type === 'field' ? (normalize(row[rule.value]) || '[空]') : rule.value).join('')
}

export function extractEquipmentCode(content) {
  const text = normalize(content)
  const lineMatches = text.match(lineEquipmentCodePattern)
  if (lineMatches?.length) return lineMatches[0].toUpperCase()
  const hyphenMatches = text.match(hyphenEquipmentCodePattern)
  return hyphenMatches?.[0]?.toUpperCase() || ''
}
