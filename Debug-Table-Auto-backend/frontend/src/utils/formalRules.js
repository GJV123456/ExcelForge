const normalize = (value) => String(value ?? '').trim()

let nextRuleId = 1
const id = (prefix) => `${prefix}-${nextRuleId++}`

export function createEmptyResult() {
  return { id: id('result'), description: '', responsibleDisciplines: '' }
}

export function createEmptyStep() {
  return {
    id: id('step'),
    description: '',
    ratioChange: '否',
    results: [createEmptyResult()]
  }
}

export function ensureRuleTypes(rules, equipmentTypes) {
  return Object.fromEntries(
    equipmentTypes.map((equipmentType) => [
      equipmentType,
      rules[equipmentType]?.length ? rules[equipmentType] : [createEmptyStep()]
    ])
  )
}

export function parseResponsibleDisciplines(value) {
  return normalize(value).split(/[,，]/).map(normalize).filter(Boolean)
}

export function validateFormalRules(equipmentTypes, rules) {
  for (const equipmentType of equipmentTypes) {
    const typeLabel = equipmentType || '未提供设备类型'
    const steps = rules[equipmentType]
    if (!steps?.length) return `请为“${typeLabel}”至少添加一个操作步骤`
    for (const [stepIndex, step] of steps.entries()) {
      if (!normalize(step.description)) return `请填写“${typeLabel}”的第 ${stepIndex + 1} 个操作步骤`
      if (!['是', '否'].includes(step.ratioChange)) return `请选择“${typeLabel}”第 ${stepIndex + 1} 步是否变比`
      if (!step.results?.length) return `请为“${typeLabel}”第 ${stepIndex + 1} 步至少添加一个结果输出`
      for (const [resultIndex, result] of step.results.entries()) {
        if (!normalize(result.description)) return `请填写“${typeLabel}”第 ${stepIndex + 1} 步的第 ${resultIndex + 1} 个结果输出`
        if (!parseResponsibleDisciplines(result.responsibleDisciplines).length) return `请填写“${typeLabel}”第 ${stepIndex + 1} 步的第 ${resultIndex + 1} 个责任专业`
      }
    }
  }
  return ''
}

export function attachFormalRules(testContents, rules) {
  return testContents.map((content) => ({
    ...content,
    operationSteps: rules[content.equipmentType].map((step) => ({
      description: normalize(step.description),
      ratioChange: step.ratioChange,
      results: step.results.map((result) => ({
        description: normalize(result.description),
        responsibleDisciplines: parseResponsibleDisciplines(result.responsibleDisciplines)
      }))
    }))
  }))
}
