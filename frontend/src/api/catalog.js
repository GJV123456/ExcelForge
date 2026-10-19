import request from '../utils/request'
import { useExcelStore } from '../store/excel'

// 目录 API 按当前联调项目选择独立的后端目录数据库。
const integrationParams = (params = {}) => ({
  ...params,
  integrationCode: useExcelStore().selectedIntegration || 'T19'
})
const scoped = (data) => [data, { params: integrationParams() }]
const scopedConfig = () => ({ params: integrationParams() })

// 设备类型基础资料 CRUD。
export const getEquipmentTypes = (params = {}) => request.get('/api/catalog/equipment-types', { params: integrationParams(params) })
export const createEquipmentType = (data) => request.post('/api/catalog/equipment-types', ...scoped(data))
export const updateEquipmentType = (id, data) => request.put(`/api/catalog/equipment-types/${id}`, ...scoped(data))
export const deleteEquipmentType = (id) => request.delete(`/api/catalog/equipment-types/${id}`, scopedConfig())

// 一次返回设备类型及其子类型目录树。
export const getEquipmentHierarchy = (params = {}) => request.get('/api/catalog/equipment-hierarchy', { params: integrationParams(params) })

// 只查询某一个父设备类型下的子类型。
export const getEquipmentSubtypes = (equipmentTypeId, params = {}) => request.get(`/api/catalog/equipment-types/${equipmentTypeId}/subtypes`, { params: integrationParams(params) })
export const deleteEquipmentSubtype = (subtypeId) => request.delete(`/api/catalog/equipment-subtypes/${subtypeId}`, scopedConfig())
export const updateEquipmentSubtypeStatuses = (subtypeId, data) => request.put(`/api/catalog/equipment-subtypes/${subtypeId}/statuses`, ...scoped(data))

// 查询测试规则。返回数据包含 operationSteps/results 的嵌套结构。
export const getTestContents = (params = {}) => request.get('/api/catalog/test-contents', { params: integrationParams(params) })

export const getTestContent = (id) => request.get(`/api/catalog/test-contents/${id}`, scopedConfig())

// 规则采用“整棵树”写入：新增用 POST，修改用 PUT。
export const createTestContent = (data) => request.post('/api/catalog/test-contents', ...scoped(data))

export const updateTestContent = (id, data) => request.put(`/api/catalog/test-contents/${id}`, ...scoped(data))

export const deleteTestContent = (id) => request.delete(`/api/catalog/test-contents/${id}`, scopedConfig())

// 责任专业是输出结果的多选项，单独提供 CRUD 接口。
export const getDisciplines = (params = {}) => request.get('/api/catalog/disciplines', { params: integrationParams(params) })

export const createDiscipline = (data) => request.post('/api/catalog/disciplines', ...scoped(data))

export const updateDiscipline = (id, data) => request.put(`/api/catalog/disciplines/${id}`, ...scoped(data))

export const deleteDiscipline = (id) => request.delete(`/api/catalog/disciplines/${id}`, scopedConfig())

// 站点基础资料 CRUD。
export const getStations = (params = {}) => request.get('/api/catalog/stations', { params: integrationParams(params) })
export const createStation = (data) => request.post('/api/catalog/stations', ...scoped(data))
export const updateStation = (id, data) => request.put(`/api/catalog/stations/${id}`, ...scoped(data))
export const deleteStation = (id) => request.delete(`/api/catalog/stations/${id}`, scopedConfig())
