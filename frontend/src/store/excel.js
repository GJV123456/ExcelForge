import { defineStore } from 'pinia'

export const useExcelStore = defineStore('excel', {
  // 当前工作台只有 T19 联调项目，进入页面时直接使用该项目。
  state: () => ({ selectedIntegration: 'T19', file: null, excelType: '', headers: [], rows: [], rules: [], preview: [] }),
  actions: {
    setIntegration(code) { this.selectedIntegration = code || '' },
    setExcel({ file, excelType, headers, rows }) { this.file = file; this.excelType = excelType; this.headers = headers; this.rows = rows },
    setRules(rules) { this.rules = rules },
    setPreview(preview) { this.preview = preview },
    reset() { this.file = null; this.excelType = ''; this.headers = []; this.rows = []; this.rules = []; this.preview = [] }
  }
})
