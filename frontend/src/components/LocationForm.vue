<script setup>
import { stationOptions } from '../data/stations'
import { changeLocationType, changeStation } from '../utils/formalLocation'

const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue'])

const queryStations = (query, callback) => {
  const keyword = String(query || '').trim().toLowerCase()
  const result = keyword ? stationOptions.filter((item) => item.value.toLowerCase().includes(keyword)) : stationOptions
  callback(result)
}
const updateType = (type) => emit('update:modelValue', changeLocationType(props.modelValue, type))
const updateStation = (station) => emit('update:modelValue', changeStation(props.modelValue, station))
</script>

<template>
  <el-form :model="modelValue" label-position="top" class="location-form">
    <div class="form-grid">
      <el-form-item label="地点类型" required><el-select :model-value="modelValue.type" placeholder="请选择地点类型" @update:model-value="updateType"><el-option v-for="item in ['站点','区间','全线']" :key="item" :label="item" :value="item" /></el-select></el-form-item>
      <el-form-item v-if="modelValue.type === '区间' || modelValue.type === '全线'" label="行车方向"><el-select :model-value="modelValue.direction" clearable placeholder="请选择行车方向" @update:model-value="v => $emit('update:modelValue', { ...modelValue, direction: v })"><el-option v-for="item in ['上行','下行']" :key="item" :label="item" :value="item" /></el-select></el-form-item>
      <el-form-item v-if="modelValue.type === '站点'" label="站点（同步填写开始站点和结束站点）" required><el-autocomplete :model-value="modelValue.startStation" :fetch-suggestions="queryStations" clearable placeholder="请输入或选择站点" @update:model-value="updateStation" @select="item => updateStation(item.value)" /></el-form-item>
      <el-form-item v-if="modelValue.type === '区间'" label="开始站点" required><el-autocomplete :model-value="modelValue.startStation" :fetch-suggestions="queryStations" clearable placeholder="请输入或选择开始站点" @update:model-value="v => $emit('update:modelValue', { ...modelValue, startStation: v })" @select="item => $emit('update:modelValue', { ...modelValue, startStation: item.value })" /></el-form-item>
      <el-form-item v-if="modelValue.type === '区间'" label="结束站点" required><el-autocomplete :model-value="modelValue.endStation" :fetch-suggestions="queryStations" clearable placeholder="请输入或选择结束站点" @update:model-value="v => $emit('update:modelValue', { ...modelValue, endStation: v })" @select="item => $emit('update:modelValue', { ...modelValue, endStation: item.value })" /></el-form-item>
    </div>
  </el-form>
</template>
