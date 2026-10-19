// T19 联调项目专属关键字和分类规则。
const matchedField = (value, aliases = [value]) => ({ value, aliases })
const includesKeyword = (text, upperText, keyword) => {
  const target = String(keyword || '').trim()
  if (!target) return false
  return /[a-z0-9]/i.test(target)
    ? String(upperText || '').includes(target.toUpperCase())
    : String(text || '').includes(target)
}
const rules = [
  { equipmentTypes: ['监视模块'], subtype: '吸气式主机', keywords: ['ASD'], fields: ['预警', '火警', '故障'] },
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
    fields: [matchedField('远程复位', ['远程复位', '远方复归'])]
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
    // 轨行区的站台上/下行插孔属于区间电话，即使原始描述没有直接写“区间”。
    match: ({ text }) =>
      (text.includes('区间插孔') || text.includes('轨行区插孔')) &&
      text.includes('消防电话插孔'),
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
    // 手动防火阀的不同资料版本分别使用“动作状态”和“动作反馈”。
    // 两者都必须作为状态传给后端，不能再让所有手动防火阀共用一条无状态规则。
    fields: ['动作状态', '动作反馈'],
    match: ({ code, text, upperText }) => code.includes('FF1') || code.includes('FP1') || includesKeyword(text, upperText, 'FF1') || includesKeyword(text, upperText, 'FP1')
  }
]


export const classificationProfile = { rules }
