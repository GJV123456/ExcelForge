import assert from 'node:assert/strict'
import test from 'node:test'

import { deriveEquipmentClassification, deriveEquipmentSubtype, deriveEquipmentStatus, extractIntervalName } from '../src/utils/equipmentSubtype.js'

test('derives monitoring module subtypes from equipment chinese keywords', () => {
  assert.equal(deriveEquipmentSubtype({ equipmentType: '监视模块', equipmentChinese: 'ASD预警' }), '吸气式主机')
  assert.equal(deriveEquipmentSubtype({ equipmentType: '监视模块', equipmentChinese: '感温电缆报警反馈' }), '感温电缆')
  assert.equal(deriveEquipmentSubtype({ equipmentType: '监视模块', equipmentChinese: '垂直电梯状态反馈' }), '垂直电梯')
  assert.equal(deriveEquipmentSubtype({ equipmentType: '监视模块', equipmentChinese: '消防泵故障反馈' }), '消防泵')
})

test('distinguishes AFC from 400V switching rules', () => {
  for (const field of ['AFC切非反馈', 'AFC切非', 'AFC状态反馈', 'AFC释放控制']) {
    assert.deepEqual(
      deriveEquipmentClassification({ equipmentType: '监视模块', equipmentChinese: `设备${field}` }),
      { equipmentSubtype: 'AFC', equipmentStatus: field }
    )
  }
  assert.equal(deriveEquipmentSubtype({ equipmentType: '监视模块', equipmentChinese: '400V切非反馈' }), '400V切非')
  assert.equal(deriveEquipmentSubtype({ equipmentType: '控制模块', equipmentChinese: '400V切非控制' }), '400V切非')
})

test('derives control and special module subtypes', () => {
  assert.deepEqual(
    deriveEquipmentClassification({ equipmentType: '控制模块', equipmentChinese: 'ASD远程复位' }),
    { equipmentSubtype: '吸气式主机', equipmentStatus: '远程复位' }
  )
  assert.equal(deriveEquipmentSubtype({ equipmentType: '控制模块', equipmentChinese: 'SG声光控制' }), '声光报警器')
  assert.equal(deriveEquipmentSubtype({ equipmentType: '控制模块', equipmentChinese: 'PA广播状态保持' }), 'PA')
  assert.equal(deriveEquipmentSubtype({ equipmentType: '特殊模块', equipmentChinese: '区间插孔消防电话插孔' }), '区间电话')
  assert.equal(deriveEquipmentSubtype({ equipmentType: '特殊模块', equipmentChinese: '消防电话插孔' }), '站内电话')
})

test('derives fire damper subtypes from equipment code and chinese keywords', () => {
  assert.deepEqual(
    deriveEquipmentClassification({ equipmentType: '防火阀', equipmentCode: 'FF2-B905', equipmentChinese: '防火阀动作状态' }),
    { equipmentSubtype: '电动防火阀', equipmentStatus: '动作状态' }
  )
  assert.deepEqual(
    deriveEquipmentClassification({ equipmentType: '防火阀', equipmentCode: 'FP1-B7', equipmentChinese: '防火阀关控制命令' }),
    { equipmentSubtype: '手动防火阀', equipmentStatus: '' }
  )
  assert.deepEqual(
    deriveEquipmentClassification({ equipmentType: '防火阀', equipmentCode: 'FF2-B211', equipmentChinese: '防火阀' }),
    { equipmentSubtype: '电动防火阀', equipmentStatus: '' }
  )
  assert.deepEqual(
    deriveEquipmentClassification({ equipmentType: '防火阀', equipmentChinese: 'FF1动作状态' }),
    { equipmentSubtype: '手动防火阀', equipmentStatus: '' }
  )
})

test('returns empty subtype when no rule matches', () => {
  assert.equal(deriveEquipmentSubtype({ equipmentType: '防火阀', equipmentChinese: '普通风阀动作状态' }), '')
})

test('derives subtype and status together', () => {
  const result = deriveEquipmentClassification({ equipmentType: '监视模块', equipmentChinese: '站厅B端应急照明BH-EPS状态反馈' })

  assert.equal(result.equipmentSubtype, 'EPS')
  assert.equal(result.equipmentStatus, '状态反馈')
  assert.equal(deriveEquipmentStatus({ equipmentType: '监视模块', equipmentChinese: '站厅B端应急照明BH-EPS启动控制' }), '启动控制')
})

test('derives EPS subtype for control module rows', () => {
  const result = deriveEquipmentClassification({ equipmentType: '控制模块', equipmentChinese: '站厅B端应急照明BH-EPS启动控制' })

  assert.deepEqual(result, { equipmentSubtype: 'EPS', equipmentStatus: '启动控制' })
})

test('falls back to signal description when equipment chinese has no status field', () => {
  assert.deepEqual(
    deriveEquipmentClassification({
      equipmentType: '控制模块',
      equipmentChinese: '站厅B端应急照明BH-EPS',
      signalDescription: '启动控制'
    }),
    { equipmentSubtype: 'EPS', equipmentStatus: '启动控制' }
  )
})

test('prefers status from equipment chinese over signal description', () => {
  assert.deepEqual(
    deriveEquipmentClassification({
      equipmentType: '控制模块',
      equipmentChinese: '站厅B端应急照明BH-EPS状态反馈',
      signalDescription: '启动控制'
    }),
    { equipmentSubtype: 'EPS', equipmentStatus: '状态反馈' }
  )
})

test('derives air valve status fields', () => {
  for (const field of ['动作状态', '监视模块故障状态', '开控制命令', '控制模块故障状态']) {
    assert.deepEqual(
      deriveEquipmentClassification({ equipmentType: '风阀', equipmentChinese: `站厅风阀${field}` }),
      { equipmentSubtype: '', equipmentStatus: field }
    )
  }
})

test('derives air valve status from signal description fallback', () => {
  assert.deepEqual(
    deriveEquipmentClassification({
      equipmentType: '风阀',
      equipmentChinese: '站厅风阀',
      signalDescription: '控制模块故障状态'
    }),
    { equipmentSubtype: '', equipmentStatus: '控制模块故障状态' }
  )
})

test('derives electric fire damper status fields without using FF2 as status', () => {
  for (const field of ['动作状态', '监视模块故障状态', '关控制命令', '控制模块故障状态']) {
    assert.deepEqual(
      deriveEquipmentClassification({ equipmentType: '防火阀', equipmentCode: 'FF2-B905', equipmentChinese: `电动防火阀${field}` }),
      { equipmentSubtype: '电动防火阀', equipmentStatus: field }
    )
  }
})

test('prefers the longer fire pump water level status', () => {
  assert.deepEqual(
    deriveEquipmentClassification({ equipmentType: '监视模块', equipmentChinese: '站厅B端低水位报警反馈' }),
    { equipmentSubtype: '消防泵', equipmentStatus: '低水位报警反馈' }
  )
  assert.deepEqual(
    deriveEquipmentClassification({ equipmentType: '监视模块', equipmentChinese: '站厅B端最低水位报警反馈' }),
    { equipmentSubtype: '消防泵', equipmentStatus: '最低水位报警反馈' }
  )
})

test('extracts interval name for temperature optical fiber rows', () => {
  assert.equal(extractIntervalName('角石区间上行感温光纤报警反馈'), '角石')
  assert.equal(extractIntervalName('角石区间下行感温光纤报警反馈'), '角石')
  assert.equal(extractIntervalName('角石区间感温光纤报警反馈'), '')
  assert.deepEqual(
    deriveEquipmentClassification({ equipmentType: '监视模块', equipmentChinese: '角石区间上行感温光纤报警反馈' }),
    { equipmentSubtype: '感温光纤', equipmentStatus: '上行感温光纤报警反馈', intervalName: '角石' }
  )
})

test('keeps interval name empty for non optical fiber rows', () => {
  assert.deepEqual(
    deriveEquipmentClassification({ equipmentType: '监视模块', equipmentChinese: '站厅B端消防泵故障反馈' }),
    { equipmentSubtype: '消防泵', equipmentStatus: '消防泵故障反馈' }
  )
})
