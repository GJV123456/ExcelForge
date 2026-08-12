import assert from 'node:assert/strict'
import test from 'node:test'

import { changeLocationType, changeStation, validateFormalLocation } from '../src/utils/formalLocation.js'

test('station input synchronizes start and end station', () => {
  const selected = changeLocationType({ type: '区间', direction: '上行', startStation: '角江路站', endStation: '下一站' }, '站点')
  const changed = changeStation(selected, '角江路站')

  assert.deepEqual(changed, { type: '站点', direction: '', startStation: '角江路站', endStation: '角江路站' })
  assert.equal(validateFormalLocation(changed), '')
})

test('station validation rejects missing or mismatched end station', () => {
  assert.match(validateFormalLocation({ type: '站点', direction: '', startStation: '', endStation: '' }), /请输入站点/)
  assert.match(validateFormalLocation({ type: '站点', direction: '', startStation: '甲站', endStation: '乙站' }), /必须相同/)
})
