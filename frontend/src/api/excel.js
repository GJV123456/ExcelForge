import request from '../utils/request'
import * as XLSX from 'xlsx'

const useMockProcess = import.meta.env.DEV && import.meta.env.VITE_ENABLE_MOCK_PROCESS !== 'false'
const mockDelay = (value) => new Promise((resolve) => setTimeout(() => resolve(value), 1000))

export const processExcel = (data) => {
  if (useMockProcess) {
    const rows = data.testContents.map((item) => ({
      '序号': item.sortIndex,
      '测试内容': item.generatedContent,
      '设备编码': item.equipmentCode,
      '设备类型': item.equipmentType,
      '地点类型': data.testLocation.type,
      '行车方向': data.testLocation.direction,
      '开始站点': data.testLocation.startStation,
      '结束站点': data.testLocation.endStation
    }))
    const sheet = XLSX.utils.json_to_sheet(rows)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, sheet, '测试内容')
    const output = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })
    return mockDelay({ data: new Blob([output], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }) })
  }
  return request.post('/api/excel/process', data, { responseType: 'blob' })
}
