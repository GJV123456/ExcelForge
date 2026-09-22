<script setup>
import { changeLocationType, changeStation } from '../utils/formalLocation'

const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue'])

const updateType = (type) => emit('update:modelValue', changeLocationType(props.modelValue, type))
const updateStation = (station) => emit('update:modelValue', changeStation(props.modelValue, station))
</script>

<template>
  <el-form :model="modelValue" label-position="top" class="location-form">
    <div class="form-grid">
      <el-form-item label="地点类型" required><el-select :model-value="modelValue.type" placeholder="请选择地点类型" @update:model-value="updateType"><el-option v-for="item in ['站点','区间','全线']" :key="item" :label="item" :value="item" /></el-select></el-form-item>
      <el-form-item v-if="modelValue.type === '区间' || modelValue.type === '全线'" label="行车方向" required><el-select :model-value="modelValue.direction" placeholder="请选择行车方向" @update:model-value="v => $emit('update:modelValue', { ...modelValue, direction: v })"><el-option v-for="item in ['上行','下行']" :key="item" :label="item" :value="item" /></el-select></el-form-item>
      <el-form-item v-if="modelValue.type === '站点'" label="站点（同步填写开始站点和结束站点）" required><el-input :model-value="modelValue.startStation" placeholder="请输入站点" @update:model-value="updateStation" /></el-form-item>
      <el-form-item v-if="modelValue.type === '区间'" label="开始站点" required><el-input :model-value="modelValue.startStation" placeholder="请输入开始站点" @update:model-value="v => $emit('update:modelValue', { ...modelValue, startStation: v })" /></el-form-item>
      <el-form-item v-if="modelValue.type === '区间'" label="结束站点" required><el-input :model-value="modelValue.endStation" placeholder="请输入结束站点" @update:model-value="v => $emit('update:modelValue', { ...modelValue, endStation: v })" /></el-form-item>
    </div>
  </el-form>
</template>
