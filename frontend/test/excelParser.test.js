import assert from 'node:assert/strict'
import test from 'node:test'

import { buildContent } from '../src/utils/excelParser.js'

test('builds type B content with signal description', () => {
  const row = {
    设备中文: '站厅B端应急照明',
    设备类型: '控制模块',
    设备编码: 'N1L19M79',
    信号描述: '远程复位',
    附加编号: 'A01'
  }
  const rules = [
    { type: 'field', value: '设备中文' },
    { type: 'field', value: '设备类型' },
    { type: 'field', value: '设备编码' },
    { type: 'field', value: '信号描述', optional: true },
    { type: 'field', value: '附加编号', optional: true },
    { type: 'text', value: '控制测试' }
  ]

  assert.equal(buildContent(row, rules), '站厅B端应急照明控制模块N1L19M79远程复位A01控制测试')
})

test('skips empty optional signal description and additional code fields', () => {
  const row = {
    设备中文: '风阀',
    设备类型: '防火阀',
    设备编码: 'FF1-B905'
  }
  const rules = [
    { type: 'field', value: '设备中文' },
    { type: 'field', value: '设备类型' },
    { type: 'field', value: '设备编码' },
    { type: 'field', value: '信号描述', optional: true },
    { type: 'field', value: '附加编号', optional: true },
    { type: 'text', value: '测试' }
  ]

  assert.equal(buildContent(row, rules), '风阀防火阀FF1-B905测试')
})

test('skips required empty fields in generated content', () => {
  const row = {
    设备中文: '风阀',
    设备类型: '',
    设备编码: 'FF1-B905'
  }
  const rules = [
    { type: 'field', value: '设备中文' },
    { type: 'field', value: '设备类型' },
    { type: 'field', value: '设备编码' }
  ]

  assert.equal(buildContent(row, rules), '风阀FF1-B905')
})

test('allows special module content to follow selected rules', () => {
  const row = {
    设备中文: '角江至石美下行区间插孔50号消防电话插孔特殊模块',
    设备类型: '特殊模块',
    设备编码: 'N1L2M50'
  }
  const rules = [
    { type: 'field', value: '设备中文' },
    { type: 'field', value: '设备类型' },
    { type: 'field', value: '设备编码' },
    { type: 'text', value: '测试' }
  ]

  assert.equal(buildContent(row, rules), '角江至石美下行区间插孔50号消防电话插孔特殊模块特殊模块N1L2M50测试')
})
