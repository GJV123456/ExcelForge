<script setup>
import { Delete, Plus } from '@element-plus/icons-vue'
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

const getStationsList = () => {
  if (Array.isArray(props.modelValue.stations)) return props.modelValue.stations.slice()
  // fallback to single startStation if stations not present, otherwise provide one empty input by default
  return props.modelValue.startStation ? [props.modelValue.startStation] : ['']
}

const addStation = () => {
  const next = getStationsList()
  next.push('')
  emit('update:modelValue', { ...props.modelValue, stations: next, startStation: next[0] || '', endStation: next[0] || '' })
}

const updateStationAt = (index, value) => {
  const next = getStationsList()
  next[index] = value
  emit('update:modelValue', { ...props.modelValue, stations: next, startStation: next[0] || '', endStation: next[0] || '' })
}

const removeStationAt = (index) => {
  const next = getStationsList()
  next.splice(index, 1)
  emit('update:modelValue', { ...props.modelValue, stations: next, startStation: next[0] || '', endStation: next[0] || '' })
}
</script>

<template>
  <el-form :model="modelValue" label-position="top" class="location-form">
    <div class="form-grid">
      <el-form-item label="地点类型" required><el-select :model-value="modelValue.type" placeholder="请选择地点类型" @update:model-value="updateType"><el-option v-for="item in ['站点','区间','全线']" :key="item" :label="item" :value="item" /></el-select></el-form-item>
      <el-form-item v-if="modelValue.type === '区间' || modelValue.type === '全线'" label="行车方向"><el-select :model-value="modelValue.direction" clearable placeholder="请选择行车方向" @update:model-value="v => $emit('update:modelValue', { ...modelValue, direction: v })"><el-option v-for="item in ['上行','下行']" :key="item" :label="item" :value="item" /></el-select></el-form-item>
      <el-form-item v-if="modelValue.type === '站点'" label="站点（开始站点和结束站点）" required>
        <div class="stations-list">
          <div class="station-row" v-for="(s, idx) in getStationsList()" :key="idx">
            <el-autocomplete :model-value="s" :fetch-suggestions="queryStations" :debounce="0" :trigger-on-focus="true" fit-input-width clearable placeholder="请输入或选择站点" @update:model-value="v => updateStationAt(idx, v)" @select="item => updateStationAt(idx, item.value)" />
            <el-button class="station-remove" circle :icon="Delete" @click="removeStationAt(idx)" v-if="getStationsList().length > 1" />
          </div>
          <el-button class="station-add" type="primary" plain :icon="Plus" @click="addStation">添加站点</el-button>
        </div>
      </el-form-item>
      <el-form-item v-if="modelValue.type === '区间'" label="开始站点" required><el-autocomplete :model-value="modelValue.startStation" :fetch-suggestions="queryStations" :debounce="0" :trigger-on-focus="true" fit-input-width clearable placeholder="请输入或选择开始站点" @update:model-value="v => $emit('update:modelValue', { ...modelValue, startStation: v })" @select="item => $emit('update:modelValue', { ...modelValue, startStation: item.value })" /></el-form-item>
      <el-form-item v-if="modelValue.type === '区间'" label="结束站点" required><el-autocomplete :model-value="modelValue.endStation" :fetch-suggestions="queryStations" :debounce="0" :trigger-on-focus="true" fit-input-width clearable placeholder="请输入或选择结束站点" @update:model-value="v => $emit('update:modelValue', { ...modelValue, endStation: v })" @select="item => $emit('update:modelValue', { ...modelValue, endStation: item.value })" /></el-form-item>
    </div>
  </el-form>
</template>
