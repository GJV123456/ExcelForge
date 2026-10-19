import assert from 'node:assert/strict'
import test from 'node:test'

import { getDownloadFilename } from '../src/utils/download.js'

test('prefers the UTF-8 filename from Content-Disposition', () => {
  const filename = getDownloadFilename({
    'content-disposition': "attachment; filename=\"formal-output.xls\"; filename*=UTF-8''T19-%E8%A7%92%E6%B1%9F%E8%B7%AF%E7%AB%99-01-FAS%E8%AE%BE%E5%A4%87%E4%BF%A1%E6%81%AF%E7%9B%91%E8%A7%86-%E7%83%9F%E6%84%9F%E5%92%8C%E6%B8%A9%E6%84%9F_20261019_%E5%AF%BC%E5%85%A5%E7%89%88V1.xls"
  })

  assert.equal(filename, 'T19-角江路站-01-FAS设备信息监视-烟感和温感_20261019_导入版V1.xls')
})

test('falls back to a safe xls filename', () => {
  assert.equal(getDownloadFilename({}), '最终导入表.xls')
  assert.equal(
    getDownloadFilename({ 'content-disposition': 'attachment; filename="../unsafe.xlsx"' }),
    '最终导入表.xls'
  )
})
