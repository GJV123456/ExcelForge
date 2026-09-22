const text = (value) => typeof value === 'string' ? value : ''
const firstText = (...values) => values.find((value) => typeof value === 'string') || ''

const BUILTIN_STATUS_MAP = {
  '监视模块/吸气式主机': ['预警', '火警', '故障', '远程复位'],
  '监视模块/感温电缆': ['报警反馈', '故障反馈', '远程复位'],
  '监视模块/感温光纤': ['感温光纤综合故障', '区间上行感温光纤报警反馈', '区间下行感温光纤报警反馈'],
  '监视模块/AFC': ['AFC切非反馈', 'AFC切非', 'AFC状态反馈', 'AFC释放控制'],
  '监视模块/EPS': ['状态反馈', '启动控制'],
  '监视模块/垂直电梯': ['垂直电梯状态反馈', '垂直电梯归首控制'],
  '监视模块/防火卷帘': ['防火卷帘一次降落反馈', '防火卷帘一次降落控制', '防火卷帘二次降落反馈', '防火卷帘二次降落控制'],
  '监视模块/400V切非': ['切非反馈'],
  '监视模块/消防泵': ['消防泵手/自动反馈', '消防泵动作反馈', '消防泵故障反馈', '压力开关动作反馈', '流量开关动作反馈', '高水位报警反馈', '低水位报警反馈', '最低水位报警反馈', '稳压泵动作反馈', '稳压泵故障反馈', '消防泵启动控制', '巡检柜报警反馈', '信号阀动作反馈', '水流指示器动作反馈'],
  '监视模块/门禁释放': ['门禁释放反馈', '门禁释放'],
  '监视模块/电气火灾、消防电源、应急疏散': ['电气火灾监控报警', '电气火灾监控故障反馈', '消防电源监控系统报警', '消防电源监控系统故障反馈', '应急照明及疏散指示系统状态反馈', '应急照明及疏散指示系统模式控制'],
  '控制模块/吸气式主机': ['预警', '火警', '故障', '远程复位'],
  '控制模块/感温电缆': ['报警反馈', '故障反馈', '远程复位'],
  '控制模块/AFC': ['AFC切非反馈', 'AFC切非', 'AFC状态反馈', 'AFC释放控制'],
  '控制模块/EPS': ['状态反馈', '启动控制'],
  '控制模块/垂直电梯': ['垂直电梯状态反馈', '垂直电梯归首控制'],
  '控制模块/防火卷帘': ['防火卷帘一次降落反馈', '防火卷帘一次降落控制', '防火卷帘二次降落反馈', '防火卷帘二次降落控制'],
  '控制模块/400V切非': ['切非'],
  '控制模块/消防泵': ['消防泵手/自动反馈', '消防泵动作反馈', '消防泵故障反馈', '压力开关动作反馈', '流量开关动作反馈', '高水位报警反馈', '低水位报警反馈', '最低水位报警反馈', '稳压泵动作反馈', '稳压泵故障反馈', '消防泵启动控制', '巡检柜报警反馈', '信号阀动作反馈', '水流指示器动作反馈'],
  '控制模块/门禁释放': ['门禁释放反馈', '门禁释放'],
  '控制模块/电气火灾、消防电源、应急疏散': ['电气火灾监控报警', '电气火灾监控故障反馈', '消防电源监控系统报警', '消防电源监控系统故障反馈', '应急照明及疏散指示系统状态反馈', '应急照明及疏散指示系统模式控制'],
  '控制模块/主机手自动、人工确认': ['FAS主机人工确定按钮', 'FAS主机自动状态按钮', '气灭主机自动状态按钮', 'FAS主机综合火警'],
  // 兼容数据库种子脚本曾使用的“等”后缀命名。
  '控制模块/主机手自动、人工确认等': ['FAS主机人工确定按钮', 'FAS主机自动状态按钮', '气灭主机自动状态按钮', 'FAS主机综合火警'],
  '防火阀/电动防火阀': ['动作状态', '关控制命令'],
  '排烟机': ['运行状态', '手自动切换状态', '开启控制命令'],
  '加压送风机': ['运行状态', '手自动切换状态', '开启控制命令']
}

export const getBuiltinStatuses = (parentName = '', subtypeName = '') => (
  BUILTIN_STATUS_MAP[subtypeName ? `${parentName}/${subtypeName}` : parentName] || []
)

// API 返回的责任专业是对象数组，保存时后端只接受 ID 数组。
const disciplineIds = (result = {}) => {
  if (Array.isArray(result.responsibleDisciplineIds)) {
    const id = result.responsibleDisciplineIds.find(Number.isInteger)
    return id == null ? [] : [id]
  }
  const id = (result.responsibleDisciplines || []).map((item) => item.id).find(Number.isInteger)
  return id == null ? [] : [id]
}

export const createRuleDraft = (rule, equipmentType) => {
  // 没有 rule 时表示新建，给表单准备一棵满足最小数量要求的空树。
  if (!rule) {
    return {
      equipmentTypeId: equipmentType?.id ?? null,
      code: '',
      content: '',
      equipmentSubtype: '',
      equipmentStatus: '',
      description: '',
      revision: 1,
      sortOrder: 1,
      isEnabled: true,
      operationSteps: [createOperationStep()]
    }
  }

  // 编辑已有规则时去掉子项 id，只保留前端可编辑字段。
  return {
    id: rule.id,
    equipmentTypeId: rule.equipmentType?.id ?? rule.equipmentTypeId ?? rule.equipment_type_id ?? equipmentType?.id ?? null,
    code: text(rule.code),
    content: text(rule.content),
    equipmentSubtype: firstText(rule.equipmentSubtype, rule.equipment_subtype, rule.subtype?.name, rule.equipmentSubtypeName),
    equipmentStatus: firstText(rule.equipmentStatus, rule.equipment_status, rule.status),
    description: text(rule.description),
    revision: Number.isInteger(rule.revision) ? rule.revision : 1,
    sortOrder: Number.isInteger(rule.sortOrder) ? rule.sortOrder : 1,
    isEnabled: rule.isEnabled !== false,
    operationSteps: (rule.operationSteps || []).map((step, stepIndex) => ({
      description: text(step.description),
      ratioChange: step.ratioChange === '是' ? '是' : '否',
      sortOrder: stepIndex + 1,
      isEnabled: step.isEnabled !== false,
      results: (step.results || []).map((result, resultIndex) => ({
        description: text(result.description),
        sortOrder: resultIndex + 1,
        isEnabled: result.isEnabled !== false,
        responsibleDisciplineIds: disciplineIds(result)
      }))
    }))
  }
}

export function createOperationStep() {
  // 后端要求至少一个结果，所以新步骤默认带一个空结果。
  return {
    description: '',
    ratioChange: '否',
    sortOrder: 1,
    isEnabled: true,
    results: [createResultOutput()]
  }
}

export function createResultOutput() {
  return {
    description: '',
    sortOrder: 1,
    isEnabled: true,
    responsibleDisciplineIds: []
  }
}

// 把页面草稿转换为 POST/PUT 请求体，并在这里统一重新编号 sortOrder。
// 注意：请求体不能携带步骤和结果的数据库 id。
export const buildTestContentPayload = (draft, { incrementRevision = false } = {}) => ({
  equipmentTypeId: draft.equipmentTypeId,
  ...(draft.code?.trim() ? { code: draft.code.trim() } : {}),
  content: draft.content.trim(),
  equipmentSubtype: draft.equipmentSubtype.trim(),
  equipmentStatus: draft.equipmentStatus.trim(),
  description: draft.description.trim(),
  revision: incrementRevision ? draft.revision + 1 : draft.revision,
  sortOrder: draft.sortOrder,
  isEnabled: draft.isEnabled,
  operationSteps: draft.operationSteps.map((step, stepIndex) => ({
    description: step.description.trim(),
    ratioChange: step.ratioChange,
    sortOrder: stepIndex + 1,
    isEnabled: step.isEnabled,
    results: step.results.map((result, resultIndex) => ({
      description: result.description.trim(),
      sortOrder: resultIndex + 1,
      isEnabled: result.isEnabled,
      responsibleDisciplineIds: result.responsibleDisciplineIds.length
        ? [result.responsibleDisciplineIds[0]]
        : []
    }))
  }))
})

// 提交前先做前端校验，减少无效请求；后端仍会再次校验。
export const validateRuleDraft = (draft) => {
  if (!draft.equipmentTypeId) return '请选择设备类型'
  if (!draft.content.trim()) return '请输入测试内容'
  if (!Number.isInteger(draft.sortOrder) || draft.sortOrder < 1) return '规则排序必须是大于 0 的整数'
  if (!draft.operationSteps.length) return '至少需要一个操作步骤'

  for (let stepIndex = 0; stepIndex < draft.operationSteps.length; stepIndex += 1) {
    const step = draft.operationSteps[stepIndex]
    if (!step.description.trim()) return `请输入第 ${stepIndex + 1} 个操作步骤的内容`
    if (!['是', '否'].includes(step.ratioChange)) return `第 ${stepIndex + 1} 个操作步骤的是否变比无效`
    if (!step.results.length) return `第 ${stepIndex + 1} 个操作步骤至少需要一个输出结果`

    for (let resultIndex = 0; resultIndex < step.results.length; resultIndex += 1) {
      const result = step.results[resultIndex]
      if (!result.description.trim()) return `请输入步骤 ${stepIndex + 1} 的第 ${resultIndex + 1} 个输出结果`
      if (!result.responsibleDisciplineIds.length) return `请为步骤 ${stepIndex + 1} 的第 ${resultIndex + 1} 个结果选择责任专业`
    }
  }
  return ''
}
