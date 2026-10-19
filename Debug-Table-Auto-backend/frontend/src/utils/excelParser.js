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
  const candidates = []
  for (const sheetName of workbook.SheetNames) {
    const matrix = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { header: 1, defval: '' })
    for (let headerRow = 0; headerRow < Math.min(matrix.length, 12); headerRow += 1) {
      const headerEntries = (matrix[headerRow] || []).map((value, index) => ({ name: normalize(value), index })).filter(({ name }) => name)
      const detected = detectExcelType(headerEntries.map(({ name }) => name))
      const formalTypeA = !detected && headerEntries.some(({ name }) => /^测试内容(?:（必填）|\(必填\))?$/.test(name))
      if (detected || formalTypeA) candidates.push({ matrix, headerRow, headerEntries, excelType: detected || 'A' })
    }
  }
  if (!candidates.length) throw createHeaderError([])
  const selected = candidates.find((item) => item.excelType === 'B') || candidates[0]
  const { matrix, headerRow, headerEntries, excelType } = selected
  const contentNames = headerEntries.filter(({ name }) => name === '测试内容' || name.startsWith('测试内容')).map(({ name }) => name)
  const contentName = contentNames.find((name) => name === '测试内容') || contentNames[0]
  const inferredType = /设备信息监视|监视模块/i.test(String(file.name || '')) ? '监视模块' : ''
  const businessNames = excelType === 'A' ? [contentName] : ['设备编码', '设备类型', '设备中文']
  const rows = matrix.slice(headerRow + 1).map((row, index) => ({ sortIndex: index + 1, ...Object.fromEntries(headerEntries.map(({ name, index: column }) => [name, normalize(row[column])])) }))
    .filter((row) => { const value = businessNames.map((name) => normalize(row[name])).find(Boolean) || ''; return value && value.toLowerCase() !== 'end' })
    .map((row) => { if (excelType === 'A' && contentName !== '测试内容') row['测试内容'] = row[contentName] || ''; if (excelType === 'A' && !row['类型'] && inferredType) row['类型'] = inferredType; return row })
  return { headers: headerEntries.map(({ name }) => name), rows, excelType }
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
