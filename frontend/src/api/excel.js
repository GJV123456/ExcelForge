import request from '../utils/request'
import { useExcelStore } from '../store/excel'

const integrationParams = (params = {}) => ({ ...params, integrationCode: useExcelStore().selectedIntegration || 'T19' })

export const processExcel = (data) => request.post('/api/excel/process', data, { responseType: 'blob' })
export const processExcelV2 = (data) => request.post('/api/v2/excel/process', data, { responseType: 'blob' })

export const getGenerations = (params = {}) => request.get('/api/generations', { params: integrationParams(params) })
export const getGeneration = (id) => request.get(`/api/generations/${id}`, { params: integrationParams() })
export const downloadGeneration = (id) => request.get(`/api/generations/${id}/download`, { params: integrationParams(), responseType: 'blob' })
