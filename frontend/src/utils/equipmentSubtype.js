const normalize = (value) => String(value ?? '').trim()
const normalizeCase = (value) => normalize(value).toUpperCase()
const hasAscii = (value) => /[a-z0-9]/i.test(value)

const includesKeyword = (text, upperText, keyword) => {
  const target = normalize(keyword)
  if (!target) return false
  return hasAscii(target) ? upperText.includes(target.toUpperCase()) : text.includes(target)
}

const includesAny = (text, upperText, keywords = []) => keywords.some((keyword) => includesKeyword(text, upperText, keyword))

const matchedField = (value, aliases = [value]) => ({ value, aliases })
const intervalNamePattern = /([\u4e00-\u9fa5A-Za-z0-9]+)区间(?:上行|下行)/

import { getClassificationProfile } from '../data/integrations/classificationProfiles.js'

const findMatchedField = (rule, text, upperText) => {
  const fieldConfigs = (rule.fields || [])
    .map((item) => typeof item === 'string' ? matchedField(item) : item)
    .sort((a, b) => Math.max(...b.aliases.map((alias) => normalize(alias).length)) - Math.max(...a.aliases.map((alias) => normalize(alias).length)))

  for (const config of fieldConfigs) {
    if (includesAny(text, upperText, config.aliases)) return config.value
  }
  return ''
}

const findRule = ({ rules, equipmentType, equipmentChinese, equipmentCode = '', signalDescription = '', testContent = '' }) => {
  const type = normalize(equipmentType)
  const text = normalize(equipmentChinese)
  const upperText = normalizeCase(equipmentChinese)
  const signalText = normalize(signalDescription)
  const signalUpperText = normalizeCase(signalDescription)
  const normalizedTestContent = normalize(testContent)
  const code = normalizeCase(equipmentCode)
  const matchesRule = (rule, sourceText, sourceUpperText) => {
    if (!rule.equipmentTypes.includes(type)) return false
    if (rule.match) return rule.match({ text: sourceText, upperText: sourceUpperText, code, testContent: normalizedTestContent })
    return includesAny(sourceText, sourceUpperText, rule.keywords)
  }

  return rules.find((rule) => matchesRule(rule, text, upperText)) || rules.find((rule) => matchesRule(rule, signalText, signalUpperText))
}

export function deriveEquipmentClassification(input) {
  const type = normalize(input.equipmentType)
  const code = normalizeCase(input.equipmentCode)
  const equipmentText = normalize([input.equipmentChinese, input.equipmentCode].filter(Boolean).join(' '))
  const signalText = normalize(input.signalDescription)
  const allSourceText = normalize([equipmentText, signalText, input.testContent].filter(Boolean).join(' '))
  const isAsdRemoteReset = /ASD/i.test(allSourceText) && /远程复位|远方复归/.test(allSourceText)
  const effectiveType = isAsdRemoteReset ? '控制模块' : type
  const profile = input.classificationProfile || getClassificationProfile(input.integrationCode)
  const rules = profile.rules || []
  const matched = findRule({ rules, ...input, equipmentType: effectiveType })
  const statusFromEquipmentChinese = matched ? findMatchedField(matched, equipmentText, normalizeCase(equipmentText)) : ''
  const statusFromSignalDescription = matched && !statusFromEquipmentChinese ? findMatchedField(matched, signalText, normalizeCase(signalText)) : ''
  const testContent = normalize(input.testContent)
  const statusFromTestContent = matched && !statusFromEquipmentChinese && !statusFromSignalDescription
    ? findMatchedField(matched, testContent, normalizeCase(testContent))
    : ''
  const equipmentStatus = statusFromEquipmentChinese || statusFromSignalDescription || statusFromTestContent
  // 老数据中的防火阀规则有时只在设备编码里带 FF2，中文内容没有明确的
  // “动作状态/关控制命令”字段。此时仍保留编码对应的状态，供左侧规则列表展示。
  const fallbackStatus = !equipmentStatus
    && type === '防火阀'
    && matched?.subtype === '电动防火阀'
    && code.includes('FF2')
    ? 'FF2'
    : ''
  const intervalName = matched?.subtype === '感温光纤' ? extractIntervalName(input.equipmentChinese) : ''

  const result = {
    equipmentSubtype: matched?.subtype || '',
    equipmentStatus: equipmentStatus || fallbackStatus
  }
  if (effectiveType !== type) result.equipmentType = effectiveType
  if (matched?.subtype === '感温光纤') result.intervalName = intervalName
  return result
}

export function extractIntervalName(content) {
  return normalize(content).match(intervalNamePattern)?.[1] || ''
}

export function deriveEquipmentSubtype(input) {
  return deriveEquipmentClassification(input).equipmentSubtype
}

export function deriveEquipmentStatus(input) {
  return deriveEquipmentClassification(input).equipmentStatus
}
