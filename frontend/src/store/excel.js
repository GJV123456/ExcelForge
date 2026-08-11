import { defineStore } from 'pinia'

export const useExcelStore = defineStore('excel', {
  state: () => ({ file: null, excelType: '', headers: [], rows: [], rules: [], preview: [] }),
  actions: {
    setExcel({ file, excelType, headers, rows }) { this.file = file; this.excelType = excelType; this.headers = headers; this.rows = rows },
    setRules(rules) { this.rules = rules },
    setPreview(preview) { this.preview = preview },
    reset() { this.file = null; this.excelType = ''; this.headers = []; this.rows = []; this.rules = []; this.preview = [] }
  }
})
