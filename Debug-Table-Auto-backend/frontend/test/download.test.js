import assert from 'node:assert/strict'
import test from 'node:test'

import { getDownloadFilename } from '../src/utils/download.js'

test('prefers the UTF-8 filename from Content-Disposition', () => {
  const filename = getDownloadFilename({
    'content-disposition': "attachment; filename=\"mock-output.xls\"; filename*=UTF-8''%E8%81%94%E8%B0%83%E5%8D%A0%E4%BD%8D%E6%96%87%E4%BB%B6_%E4%B8%8D%E5%8F%AF%E5%AF%BC%E5%85%A5.xls"
  })

  assert.equal(filename, '联调占位文件_不可导入.xls')
})

test('falls back to a safe xls filename', () => {
  assert.equal(getDownloadFilename({}), '最终导入表.xls')
  assert.equal(
    getDownloadFilename({ 'content-disposition': 'attachment; filename="../unsafe.xlsx"' }),
    '最终导入表.xls'
  )
})
