import { defineStore } from 'pinia'

const saved = JSON.parse(localStorage.getItem('excelforge_user') || '{}')
export const useUserStore = defineStore('user', {
  state: () => ({ token: saved.token || '', userInfo: saved.userInfo || {} }),
  actions: {
    setUser(token, userInfo = {}) { this.token = token; this.userInfo = userInfo; localStorage.setItem('excelforge_user', JSON.stringify({ token, userInfo })) },
    logout() { this.token = ''; this.userInfo = {}; localStorage.removeItem('excelforge_user') }
  }
})
