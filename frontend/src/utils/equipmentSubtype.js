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

const rules = [
  { equipmentTypes: ['监视模块'], subtype: '吸气式主机', keywords: ['ASD'], fields: ['预警', '火警', '故障', '远程复位'] },
  {
    equipmentTypes: ['监视模块'],
    subtype: '感温电缆',
    keywords: ['感温电缆'],
    fields: ['报警反馈', '故障反馈', '远程复位']
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '感温电缆',
    keywords: ['感温电缆'],
    fields: ['远程复位']
  },
  {
    equipmentTypes: ['监视模块'],
    subtype: '感温光纤',
    keywords: ['感温光纤'],
    fields: ['综合故障', '上行感温光纤报警反馈', '下行感温光纤报警反馈']
  },
  {
    equipmentTypes: ['监视模块'],
    subtype: 'AFC',
    keywords: ['AFC'],
    fields: ['AFC切非反馈', 'AFC切非', 'AFC状态反馈', 'AFC释放控制']
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: 'AFC',
    keywords: ['AFC'],
    fields: ['AFC切非反馈', 'AFC切非', 'AFC状态反馈', 'AFC释放控制']
  },
  {
    equipmentTypes: ['监视模块'],
    subtype: 'EPS', keywords: ['EPS'],
    fields: ['状态反馈', '启动控制']
  },
  {
    equipmentTypes: ['监视模块'],
    subtype: '垂直电梯',
    keywords: ['垂直电梯'],
    fields: ['垂直电梯状态反馈', '垂直电梯归首控制']
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '垂直电梯',
    keywords: ['垂直电梯'],
    fields: ['垂直电梯状态反馈', '垂直电梯归首控制']
  },

  {
    equipmentTypes: ['监视模块'],
    subtype: '防火卷帘',
    keywords: ['RS', '防火卷帘'],
    fields: ['防火卷帘一次降落反馈', '防火卷帘一次降落控制', '防火卷帘二次降落反馈', '防火卷帘二次降落控制']
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '防火卷帘',
    keywords: ['RS', '防火卷帘'],
    fields: ['防火卷帘一次降落反馈', '防火卷帘一次降落控制', '防火卷帘二次降落反馈', '防火卷帘二次降落控制']
  },
  {
    equipmentTypes: ['监视模块'],
    subtype: '400V切非',
    fields: ['切非反馈'],
    match: ({ text, upperText }) => !upperText.includes('AFC') && text.includes('切非反馈')
  },
  {
    equipmentTypes: ['监视模块'],
    subtype: '消防泵',
    keywords: ['消防泵', '压力开关', '水位报警', '稳压泵', '巡检柜', '信号阀', '水流指示器', '流量开关'],
    fields: [
      '消防泵手/自动反馈',
      '消防泵动作反馈',
      '消防泵故障反馈',
      '压力开关动作反馈',
      '流量开关动作反馈',
      '高水位报警反馈',
      '低水位报警反馈',
      '最低水位报警反馈',
      '稳压泵动作反馈',
      '稳压泵故障反馈',
      '消防泵启动控制',
      '巡检柜报警反馈',
      '信号阀动作反馈',
      '水流指示器动作反馈'
    ]
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '消防泵',
    keywords: ['消防泵'],
    fields: [
      '消防泵启动控制',
    ]
  },

  { equipmentTypes: ['监视模块'], subtype: '防火门', keywords: ['防火门', '联络通道DI'], fields: [] },
  {
    equipmentTypes: ['监视模块'],
    subtype: '门禁',
    keywords: ['门禁'],
    fields: ['门禁释放反馈', '门禁释放']
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '门禁',
    keywords: ['门禁'],
    fields: ['门禁释放反馈', '门禁释放']
  },
  {
    equipmentTypes: ['监视模块'],
    subtype: '电气火灾、消防电源、应急疏散',
    keywords: ['电气火灾', '消防电源', '应急照明及疏散'],
    fields: [
      '电气火灾监控报警',
      '电气火灾监控故障反馈',
      '消防电源监控系统报警',
      '消防电源监控系统故障反馈',
      '应急照明及疏散指示系统状态反馈',
      '应急照明及疏散指示系统模式控制'
    ]
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '电气火灾、消防电源、应急疏散',
    keywords: ['电气火灾', '消防电源', '应急照明及疏散'],
    fields: [
      '电气火灾监控报警',
      '电气火灾监控故障反馈',
      '消防电源监控系统报警',
      '消防电源监控系统故障反馈',
      '应急照明及疏散指示系统状态反馈',
      '应急照明及疏散指示系统模式控制'
    ]
  },

  {
    equipmentTypes: ['控制模块'],
    subtype: '吸气式主机',
    keywords: ['ASD'],
    fields: ['远程复位']
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '电源',
    keywords: ['电源'],
    fields: ['远程复位']
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: 'EPS',
    keywords: ['EPS'],
    fields: ['启动控制', '状态反馈']
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '400V切非',
    fields: ['切非'],
    match: ({ text, upperText }) => !upperText.includes('AFC') && text.includes('切非')
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '声光报警器',
    keywords: ['SG', '声光'],
    fields: ['声光报警控制', '声光控制', '声光交替模块']
  },
  { equipmentTypes: ['控制模块'], subtype: 'PA', keywords: ['PA', '广播交替模块'], fields: ['PA广播状态保持', 'PA广播', '广播交替模块'] },
  {
    equipmentTypes: ['控制模块'],
    subtype: '消火栓点灯',
    keywords: ['消火栓按钮点灯'],
    fields: []
  },
  {
    equipmentTypes: ['控制模块'],
    subtype: '主机手自动、人工确认',
    keywords: ['人工确定按钮', '自动状态按钮', 'FAS主机综合火警'],
    fields: ['FAS主机人工确定按钮', 'FAS主机自动状态按钮', '气灭主机自动状态按钮', 'FAS主机综合火警']
  },
  {
    equipmentTypes: ['特殊模块'],
    subtype: '气灭测试',
    match: ({ text, testContent }) => text.includes('气灭测试') || testContent.includes('气灭测试'),
    fields: []
  },
  {
    equipmentTypes: ['特殊模块'],
    subtype: '区间电话',
    match: ({ text }) => text.includes('区间插孔') && text.includes('消防电话插孔'),
    fields: []
  },
  {
    equipmentTypes: ['特殊模块'],
    subtype: '站内电话',
    keywords: ['消防电话插孔','消防电话分机'],
    fields: []
  },
  {
    equipmentTypes: ['排烟机', '加压送风机'],
    subtype: '',
    keywords: [],
    fields: ['运行状态', '手自动切换状态', '开启控制命令'],
    match: () => true
  },
  {
    equipmentTypes: ['风阀'],
    subtype: '',
    keywords: [],
    fields: ['动作状态', '监视模块故障状态', '开控制命令', '控制模块故障状态'],
    match: () => true
  },
  {
    equipmentTypes: ['防火阀'],
    subtype: '电动防火阀',
    fields: [
      '动作状态',
      '监视模块故障状态',
      '关控制命令',
      '控制模块故障状态'
    ],
    match: ({ code, text, upperText }) => code.includes('FF2') || includesKeyword(text, upperText, 'FF2')
  },
  {
    equipmentTypes: ['防火阀'],
    subtype: '手动防火阀',
    fields: [],
    match: ({ code, text, upperText }) => code.includes('FF1') || code.includes('FP1') || includesKeyword(text, upperText, 'FF1') || includesKeyword(text, upperText, 'FP1')
  }
]

const findMatchedField = (rule, text, upperText) => {
  const fieldConfigs = (rule.fields || [])
    .map((item) => typeof item === 'string' ? matchedField(item) : item)
    .sort((a, b) => Math.max(...b.aliases.map((alias) => normalize(alias).length)) - Math.max(...a.aliases.map((alias) => normalize(alias).length)))

  for (const config of fieldConfigs) {
    if (includesAny(text, upperText, config.aliases)) return config.value
  }
  return ''
}

const findRule = ({ equipmentType, equipmentChinese, equipmentCode = '', signalDescription = '', testContent = '' }) => {
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
  const matched = findRule(input)
  const statusFromEquipmentChinese = matched ? findMatchedField(matched, equipmentText, normalizeCase(equipmentText)) : ''
  const statusFromSignalDescription = matched && !statusFromEquipmentChinese ? findMatchedField(matched, signalText, normalizeCase(signalText)) : ''
  const equipmentStatus = statusFromEquipmentChinese || statusFromSignalDescription
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
