import assert from 'node:assert/strict'
import test from 'node:test'

import { getApiErrorMessage } from '../src/utils/httpError.js'

test('restores JSON detail from an error Blob', async () => {
  const error = {
    response: {
      status: 400,
      data: new Blob([JSON.stringify({ detail: '正式业务规则尚未配置' })], { type: 'application/json' })
    }
  }

  assert.equal(await getApiErrorMessage(error), '正式业务规则尚未配置')
})

test('distinguishes network and validation errors', async () => {
  assert.equal(await getApiErrorMessage({ publicMessage: '文件生成失败' }), '文件生成失败')
  assert.equal(await getApiErrorMessage(new Error('offline')), '服务器连接失败')
  assert.equal(await getApiErrorMessage({ response: { status: 422, data: new Blob([]) } }), '提交参数校验失败')
})

test('shows field-level FastAPI validation details', async () => {
  const error = {
    response: {
      status: 422,
      data: { detail: [{ loc: ['body', 'steps', 0, 'results'], msg: 'Field required' }] }
    }
  }
  assert.equal(await getApiErrorMessage(error), 'steps.0.results：Field required')
})
