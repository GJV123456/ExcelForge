import request from '../utils/request'

export const processExcel = (data) => request.post('/api/excel/process', data, { responseType: 'blob' })
export const processExcelV2 = (data) => request.post('/api/v2/excel/process', data, { responseType: 'blob' })
