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
    { type: 'field', value: '信号描述' },
    { type: 'field', value: '附加编号' },
    { type: 'text', value: '控制测试' }
  ]

  assert.equal(buildContent(row, rules), '站厅B端应急照明控制模块N1L19M79远程复位A01控制测试')
})
