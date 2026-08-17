const normalize = (value) => String(value ?? '').trim()

export function changeLocationType(location, type) {
  const next = { ...location, type }
  if (type === '站点') {
    const station = normalize(location.startStation || location.endStation)
    return { ...next, direction: '', startStation: station, endStation: station }
  }
  if (type === '全线') return { ...next, startStation: '', endStation: '' }
  return next
}

export function changeStation(location, station) {
  return { ...location, startStation: station, endStation: station }
}

export function validateFormalLocation(location) {
  if (!location.type) return '请选择地点类型'
  if (location.type === '站点') {
    if (!normalize(location.startStation)) return '请输入站点'
    if (normalize(location.startStation) !== normalize(location.endStation)) return '站点的开始站点和结束站点必须相同'
  }
  if (location.type === '区间' && (!normalize(location.startStation) || !normalize(location.endStation))) return '请完整填写区间起止站点'
  return ''
}
