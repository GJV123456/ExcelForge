import assert from 'node:assert/strict'
import test from 'node:test'
import { deriveEquipmentClassification } from '../src/utils/equipmentSubtype.js'

test('ASD warning, fire, and fault remain monitoring module states', () => {
  for (const status of ['预警', '火警', '故障']) {
    const classification = deriveEquipmentClassification({
      equipmentType: '监视模块',
      equipmentChinese: `站厅ASD-1${status}`
    })

    assert.equal(classification.equipmentSubtype, '吸气式主机')
    assert.equal(classification.equipmentStatus, status)
    assert.equal(classification.equipmentType, undefined)
  }
})

test('ASD state is extracted from test content when the device name has no state', () => {
  for (const status of ['预警', '火警', '故障']) {
    const classification = deriveEquipmentClassification({
      equipmentType: '监视模块',
      equipmentChinese: '站厅B端ASD-1',
      testContent: `站厅B端ASD-1${status}N1L1M68监视模块`
    })

    assert.equal(classification.equipmentSubtype, '吸气式主机')
    assert.equal(classification.equipmentStatus, status)
  }
})

test('ASD remote reset is classified as a control module action', () => {
  const classification = deriveEquipmentClassification({
    equipmentType: '监视模块',
    equipmentChinese: '站厅ASD-1',
    signalDescription: '远程复位'
  })

  assert.equal(classification.equipmentType, '控制模块')
  assert.equal(classification.equipmentSubtype, '吸气式主机')
  assert.equal(classification.equipmentStatus, '远程复位')
})

test('ASD remote reset recognizes the source alias 远方复归', () => {
  const classification = deriveEquipmentClassification({
    equipmentType: '监视模块',
    equipmentChinese: '站厅ASD-1',
    signalDescription: '远方复归'
  })

  assert.equal(classification.equipmentType, '控制模块')
  assert.equal(classification.equipmentStatus, '远程复位')
})
