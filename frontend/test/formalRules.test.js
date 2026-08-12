import assert from 'node:assert/strict'
import test from 'node:test'

import {
  attachFormalRules,
  ensureRuleTypes,
  parseResponsibleDisciplines,
  validateFormalRules
} from '../src/utils/formalRules.js'

test('initializes one blank rule per equipment type without losing existing entries', () => {
  const existing = { 烟感: [{ id: 'kept', description: '测试', ratioChange: '否', results: [] }] }
  const rules = ensureRuleTypes(existing, ['烟感', '温感'])

  assert.equal(rules.烟感[0].id, 'kept')
  assert.equal(rules.温感.length, 1)
  assert.equal(rules.温感[0].results.length, 1)
})

test('validates explicit steps, results and disciplines', () => {
  const invalid = { 烟感: [{ description: '测试', ratioChange: '否', results: [{ description: '输出', responsibleDisciplines: '' }] }] }
  const valid = { 烟感: [{ description: '测试', ratioChange: '否', results: [{ description: '输出', responsibleDisciplines: 'FAS， 综合监控' }] }] }

  assert.match(validateFormalRules(['烟感'], invalid), /责任专业/)
  assert.equal(validateFormalRules(['烟感'], valid), '')
  assert.deepEqual(parseResponsibleDisciplines('FAS， 综合监控,现场'), ['FAS', '综合监控', '现场'])
})

test('attaches v2 operation steps without reordering contents', () => {
  const contents = [
    { sortIndex: 2, generatedContent: '乙', equipmentCode: 'B', equipmentType: '温感' },
    { sortIndex: 3, generatedContent: '甲', equipmentCode: 'A', equipmentType: '烟感' }
  ]
  const rules = {
    温感: [{ description: ' 步骤乙 ', ratioChange: '是', results: [{ description: ' 结果乙 ', responsibleDisciplines: 'FAS' }] }],
    烟感: [{ description: '步骤甲', ratioChange: '否', results: [{ description: '结果甲', responsibleDisciplines: 'FAS,综合监控' }] }]
  }

  const payload = attachFormalRules(contents, rules)

  assert.deepEqual(payload.map((item) => item.sortIndex), [2, 3])
  assert.deepEqual(payload[0].operationSteps[0], {
    description: '步骤乙',
    ratioChange: '是',
    results: [{ description: '结果乙', responsibleDisciplines: ['FAS'] }]
  })
  assert.deepEqual(payload[1].operationSteps[0].results[0].responsibleDisciplines, ['FAS', '综合监控'])
})
