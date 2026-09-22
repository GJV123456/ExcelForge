import assert from 'node:assert/strict'
import test from 'node:test'

import { deriveEquipmentClassification, deriveEquipmentSubtype, deriveEquipmentStatus } from '../src/utils/equipmentSubtype.js'

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
  assert.deepEqual(
    deriveEquipmentClassification({
      equipmentType: '控制模块',
      equipmentChinese: '电源(远程复位)控制模块N1L19M79'
    }),
    { equipmentSubtype: '电源', equipmentStatus: '远程复位' }
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
  assert.equal(
    deriveEquipmentClassification({ equipmentType: '防火阀', equipmentCode: 'FF2-B211', equipmentChinese: '防火阀' }).equipmentStatus,
    'FF2'
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
