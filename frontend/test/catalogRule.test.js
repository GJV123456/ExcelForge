import assert from 'node:assert/strict'
import test from 'node:test'

import { buildTestContentPayload, createRuleDraft, validateRuleDraft } from '../src/utils/catalogRule.js'

test('turns API rule data into an editable draft', () => {
  const draft = createRuleDraft({
    id: 8,
    code: 'RULE_SMOKE',
    content: '烟感',
    revision: 3,
    equipmentType: { id: 1 },
    operationSteps: [{
      id: 10,
      description: '触发报警',
      ratioChange: '否',
      results: [{ id: 11, description: '收到火警', responsibleDisciplines: [{ id: 2, name: 'FAS' }] }]
    }]
  })

  assert.equal(draft.equipmentTypeId, 1)
  assert.deepEqual(draft.operationSteps[0].results[0].responsibleDisciplineIds, [2])
})

test('builds a full-tree write payload without child ids and with stable sort order', () => {
  const draft = createRuleDraft({
    id: 8,
    code: ' RULE_SMOKE ',
    content: ' 烟感 ',
    revision: 3,
    equipmentType: { id: 1 },
    operationSteps: [{
      id: 10,
      description: ' 触发报警 ',
      ratioChange: '否',
      sortOrder: 9,
      results: [{ id: 11, description: ' 收到火警 ', responsibleDisciplineIds: [2, 2] }]
    }]
  })
  const payload = buildTestContentPayload(draft, { incrementRevision: true })

  assert.equal(payload.revision, 4)
  assert.equal(payload.operationSteps[0].sortOrder, 1)
  assert.equal(payload.operationSteps[0].results[0].sortOrder, 1)
  assert.deepEqual(payload.operationSteps[0].results[0].responsibleDisciplineIds, [2])
  assert.equal('id' in payload.operationSteps[0], false)
})

test('validates the minimum rule tree constraints', () => {
  const draft = createRuleDraft(null, { id: 1, code: 'SMOKE' })
  assert.equal(draft.code, '')
  assert.equal('code' in buildTestContentPayload(draft), false)
  assert.match(validateRuleDraft(draft), /测试内容/)

  draft.content = '烟感'
  draft.operationSteps[0].description = '触发报警'
  draft.operationSteps[0].results[0].description = '收到火警'
  assert.match(validateRuleDraft(draft), /责任专业/)

  draft.operationSteps[0].results[0].responsibleDisciplineIds = [1]
  assert.equal(validateRuleDraft(draft), '')
})
