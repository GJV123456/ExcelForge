import request from '../utils/request'

export const processExcel = (data) => request.post('/api/excel/process', data, { responseType: 'blob' })
export const processExcelV2 = (data) => request.post('/api/v2/excel/process', data, { responseType: 'blob' })

export const getGenerations = (params = {}) => request.get('/api/generations', { params })
export const getGeneration = (id) => request.get(`/api/generations/${id}`)
export const downloadGeneration = (id) => request.get(`/api/generations/${id}/download`, { responseType: 'blob' })
