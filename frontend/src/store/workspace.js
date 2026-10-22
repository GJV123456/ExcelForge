import { defineStore } from 'pinia'
import { getWorkspaceContext } from '../api/workspace'

const sameId = (left, right) => left != null && right != null && String(left) === String(right)

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    lines: [],
    professions: [],
    projects: [],
    currentUser: {},
    selectedLineId: null,
    selectedProfessionId: null,
    selectedProjectId: null,
    selectedDebugSubitemId: null,
    selectedDebugDivisionId: null,
    loading: false,
    error: '',
    loaded: false
  }),
  getters: {
    selectedLine: (state) => state.lines.find((item) => item.id === state.selectedLineId),
    selectedProfession: (state) => state.professions.find((item) => item.id === state.selectedProfessionId),
    selectedProject: (state) => state.projects.find((item) => item.id === state.selectedProjectId),
    isSelected: (state) => Boolean(state.selectedLineId && state.selectedProfessionId && state.selectedProjectId)
  },
  actions: {
    async load() {
      if (this.loaded || this.loading) return
      this.loading = true
      this.error = ''
      try {
        const response = await getWorkspaceContext()
        const data = response.data?.data || {}
        this.lines = data.lines || []
        this.professions = data.professions || []
        this.projects = data.projects || []
        this.currentUser = data.currentUser || {}
        const saved = JSON.parse(localStorage.getItem('excelforge_scope') || '{}')
        // Open scoped accounts in their own workspace first so edit controls
        // are available immediately instead of starting on a read-only line.
        const assignedLineId = this.currentUser.role === 'super_admin' ? null : this.currentUser.lineId
        const assignedProfessionId = this.currentUser.role === 'professional_configurator'
          ? this.currentUser.professionId
          : null
        this.selectedLineId = this.lines.find((item) => sameId(item.id, assignedLineId))?.id
          ?? this.lines.find((item) => sameId(item.id, saved.lineId))?.id ?? this.lines[0]?.id ?? null
        this.selectedProfessionId = this.professions.find((item) => sameId(item.id, assignedProfessionId))?.id
          ?? this.professions.find((item) => sameId(item.id, saved.professionId))?.id ?? this.professions[0]?.id ?? null
        const projects = this.projects.filter((item) => !item.lineId || sameId(item.lineId, this.selectedLineId))
        this.selectedProjectId = projects.find((item) => sameId(item.id, saved.projectId))?.id ?? projects[0]?.id ?? null
        this.selectedDebugSubitemId = saved.debugSubitemId || null
        this.selectedDebugDivisionId = saved.debugDivisionId || null
        this.persist()
        this.loaded = true
      } catch (error) {
        this.error = error.response?.data?.detail || error.response?.data?.message || error.message || '工作区数据加载失败'
        throw error
      } finally { this.loading = false }
    },
    async reload() {
      this.loaded = false
      return this.load()
    },
    setLine(value) {
      this.selectedLineId = value || null
      const preferredProfessionId = this.currentUser.role === 'professional_configurator'
        ? this.currentUser.professionId
        : this.selectedProfessionId
      this.selectedProfessionId = this.professions.find((item) => sameId(item.id, preferredProfessionId))?.id
        ?? this.professions[0]?.id ?? null
      const projects = this.projects.filter((item) => !item.lineId || sameId(item.lineId, this.selectedLineId))
      this.selectedProjectId = projects[0]?.id ?? null
      this.selectedDebugSubitemId = null
      this.selectedDebugDivisionId = null
      this.persist()
    },
    setProfession(value) {
      this.selectedProfessionId = value || null
      const projects = this.projects.filter((item) => !item.lineId || sameId(item.lineId, this.selectedLineId))
      if (!projects.some((item) => sameId(item.id, this.selectedProjectId))) this.selectedProjectId = projects[0]?.id ?? null
      this.selectedDebugSubitemId = null
      this.selectedDebugDivisionId = null
      this.persist()
    },
    setProject(value) { this.selectedProjectId = value || null; this.selectedDebugSubitemId = null; this.selectedDebugDivisionId = null; this.persist() },
    setDebugSubitem(value) { this.selectedDebugSubitemId = value || null; this.selectedDebugDivisionId = null; this.persist() },
    setDebugDivision(value) { this.selectedDebugDivisionId = value || null; this.persist() },
    persist() { localStorage.setItem('excelforge_scope', JSON.stringify({ lineId: this.selectedLineId, professionId: this.selectedProfessionId, projectId: this.selectedProjectId, debugSubitemId: this.selectedDebugSubitemId, debugDivisionId: this.selectedDebugDivisionId })) }
  }
})
