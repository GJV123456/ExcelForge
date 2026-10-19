import assert from 'node:assert/strict'
import test from 'node:test'
import { deriveEquipmentClassification, inferElectricDamperStatus } from '../src/utils/equipmentSubtype.js'

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

test('electric fire damper duplicate rows alternate feedback and close command', () => {
  const classification = deriveEquipmentClassification({
    equipmentType: '防火阀',
    equipmentCode: 'FF2-B211',
    equipmentChinese: '站厅B端公安通信设备室'
  })

  assert.equal(inferElectricDamperStatus(classification, 0), '动作状态')
  assert.equal(inferElectricDamperStatus(classification, 1), '关控制命令')
})

test('explicit electric fire damper status is preserved', () => {
  const classification = deriveEquipmentClassification({
    equipmentType: '防火阀',
    equipmentCode: 'FF2-B211',
    equipmentChinese: '站厅B端公安通信设备室',
    signalDescription: '关控制命令'
  })

  assert.equal(inferElectricDamperStatus(classification, 0), '关控制命令')
})

test('manual fire damper keeps each source action/status', () => {
  for (const status of ['动作状态', '动作反馈']) {
    const classification = deriveEquipmentClassification({
      equipmentType: '防火阀',
      equipmentCode: 'FP1-A4',
      equipmentChinese: '站厅A端防火阀',
      signalDescription: status
    })

    assert.equal(classification.equipmentSubtype, '手动防火阀')
    assert.equal(classification.equipmentStatus, status)
  }
})

test('door access stays under the source monitoring or control module type', () => {
  for (const equipmentType of ['监视模块', '控制模块']) {
    for (const [source, expectedStatus] of [
      ['门禁释放反馈', '门禁释放反馈'],
      ['门禁释放', '门禁释放']
    ]) {
      const classification = deriveEquipmentClassification({
        equipmentType,
        equipmentChinese: '门禁',
        signalDescription: source
      })

      assert.equal(classification.equipmentType, undefined)
      assert.equal(classification.equipmentSubtype, '门禁')
      assert.equal(classification.equipmentStatus, expectedStatus)
    }
  }
})

test('platform up and down track-area fire telephone jacks classify as interval telephone', () => {
  for (const equipmentChinese of [
    '站台下行轨行区插孔54号消防电话插孔',
    '站台上行轨行区插孔55号消防电话插孔'
  ]) {
    const classification = deriveEquipmentClassification({
      equipmentType: '特殊模块',
      equipmentChinese
    })

    assert.equal(classification.equipmentSubtype, '区间电话')
  }
})
