import assert from 'node:assert/strict'
import test from 'node:test'
import * as XLSX from 'xlsx'

import { buildContent, parseExcel } from '../src/utils/excelParser.js'

test('ignores rows that only contain values outside business columns', async () => {
  const workbook = XLSX.utils.book_new()
  const sheet = XLSX.utils.aoa_to_sheet([
    ['设备编码', '设备类型', '设备中文', '附加编号', '', '', '', '', '残留列'],
    ['P111-10', '监视模块', '切非反馈', '_N1L09-M01_MK-1', '', '', '', '', '_N1L09-M07'],
    ['', '', '', '', '', '', '', '', '_N1L09-M08']
  ])
  XLSX.utils.book_append_sheet(workbook, sheet, 'Sheet1')
  const bytes = XLSX.write(workbook, { type: 'array', bookType: 'xlsx' })

  const parsed = await parseExcel(new Blob([bytes]))

  assert.equal(parsed.excelType, 'B')
  assert.equal(parsed.rows.length, 1)
  assert.equal(parsed.rows[0]['设备编码'], 'P111-10')
  assert.equal(parsed.rows[0]['附加编号'], '_N1L09-M01_MK-1')
})

test('keeps rows without equipment codes and skips equipment-type-only placeholders', async () => {
  const workbook = XLSX.utils.book_new()
  const sheet = XLSX.utils.aoa_to_sheet([
    ['设备编码', '设备类型', '设备中文'],
    ['', '特殊模块', '站厅B端弱电综合设备室气灭测试（含远程控制盒）'],
    ['', '特殊模块', '']
  ])
  XLSX.utils.book_append_sheet(workbook, sheet, 'Sheet1')
  const bytes = XLSX.write(workbook, { type: 'array', bookType: 'xlsx' })

  const parsed = await parseExcel(new Blob([bytes]))

  assert.equal(parsed.rows.length, 1)
  assert.equal(parsed.rows[0]['设备编码'], '')
  assert.equal(parsed.rows[0]['设备中文'], '站厅B端弱电综合设备室气灭测试（含远程控制盒）')
})

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
