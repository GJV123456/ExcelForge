import assert from 'node:assert/strict'
import test from 'node:test'

import { buildTestLocation, changeLocationType, changeStation, validateFormalLocation } from '../src/utils/formalLocation.js'

test('station input synchronizes start and end station', () => {
  const selected = changeLocationType({ type: '区间', direction: '上行', startStation: '角江路站', endStation: '下一站' }, '站点')
  const changed = changeStation(selected, '角江路站')

  assert.deepEqual(changed, { type: '站点', direction: '', startStation: '角江路站', endStation: '角江路站', stations: ['角江路站'] })
  assert.equal(validateFormalLocation(changed), '')
})

test('station validation rejects missing or mismatched end station', () => {
  assert.match(validateFormalLocation({ type: '站点', direction: '', startStation: '', endStation: '' }), /请输入站点/)
  assert.match(validateFormalLocation({ type: '站点', direction: '', startStation: '甲站', endStation: '乙站' }), /必须相同/)
})

test('full line payload does not keep stale station list', () => {
  const location = changeLocationType({
    type: '站点',
    direction: '',
    startStation: '智谷云谷站',
    endStation: '智谷云谷站',
    stations: ['智谷云谷站']
  }, '全线')

  assert.deepEqual(buildTestLocation(location), {
    type: '全线',
    direction: '',
    startStation: '',
    endStation: ''
  })
})

test('station payload keeps selected station list', () => {
  assert.deepEqual(
    buildTestLocation({ type: '站点', direction: '', startStation: '甲站', endStation: '甲站', stations: ['甲站', '乙站'] }),
    { type: '站点', direction: '', startStation: '甲站', endStation: '甲站', stations: ['甲站', '乙站'] }
  )
})
