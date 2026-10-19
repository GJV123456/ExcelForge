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
  // A formal workbook has several sheets and the input table is usually the
  // second sheet. Search every sheet (and the first few rows) instead of
  // assuming that sheet 1 contains the business headers.
  const candidates = []
  for (const sheetName of workbook.SheetNames) {
    const sheet = workbook.Sheets[sheetName]
    const matrix = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })
    for (let headerRow = 0; headerRow < Math.min(matrix.length, 12); headerRow += 1) {
      const headerEntries = (matrix[headerRow] || [])
        .map((value, index) => ({ name: normalize(value), index }))
        .filter(({ name }) => name)
      const exactHeaders = headerEntries.map(({ name }) => name)
      const excelType = detectExcelType(exactHeaders)
      const formalTypeA = !excelType && headerEntries.some(({ name }) => /^测试内容(?:（必填）|\(必填\))?$/.test(name))
      if (excelType || formalTypeA) candidates.push({ sheetName, matrix, headerRow, headerEntries, excelType: excelType || 'A' })
    }
  }
  if (!candidates.length) throw createHeaderError([])
  // Prefer a real Type B/A header over a descriptive/template row.
  const selected = candidates.find((item) => item.excelType === 'B') || candidates[0]
  const { matrix, headerRow, headerEntries, excelType } = selected
  const aliases = excelType === 'A'
    ? headerEntries.filter(({ name }) => name === '测试内容' || name.startsWith('测试内容'))
    : headerEntries
  const contentName = aliases.find(({ name }) => name === '测试内容')?.name ?? aliases[0]?.name
  const inferredType = /设备信息监视|监视模块/i.test(String(file.name || '')) ? '监视模块' : ''
  // Type B rows need meaningful test content. Device code is optional, and a
  // trailing template row can still contain an equipment type; neither should
  // make that blank row a submitted record.
  const businessNames = excelType === 'A'
    ? [contentName]
    : ['设备中文', '测试内容', '信号描述']
  const rows = matrix.slice(headerRow + 1)
    .map((row, index) => ({
      sortIndex: index + 1,
      ...Object.fromEntries(headerEntries.map(({ name, index: column }) => [name, normalize(row[column])]))
    }))
    .filter((row) => {
      const value = businessNames.map((name) => normalize(row[name])).find(Boolean) || ''
      return value && value.toLowerCase() !== 'end'
    })
    .map((row) => {
      if (excelType === 'A' && contentName !== '测试内容') row['测试内容'] = row[contentName] || ''
      if (excelType === 'A' && !row['类型'] && inferredType) row['类型'] = inferredType
      return row
    })
  const headers = headerEntries.map(({ name }) => name)
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
