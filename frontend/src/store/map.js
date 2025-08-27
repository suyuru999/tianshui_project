import { ref, reactive } from 'vue'

// 地图状态管理
export const useMapStore = () => {
  // 底图配置
  const baseMaps = reactive([
    {
      id: 'osm',
      name: 'OpenStreetMap',
      type: 'osm',
      visible: true
    },
    {
      id: 'satellite',
      name: '卫星影像',
      type: 'satellite',
      visible: false
    },
    {
      id: 'terrain',
      name: '地形图',
      type: 'terrain',
      visible: false
    }
  ])

  // 业务图层
  const businessLayers = ref([])

  // 当前选中的底图
  const currentBaseMap = ref('osm')

  // 添加业务图层
  const addBusinessLayer = (layer) => {
    businessLayers.value.push({
      id: Date.now(),
      name: layer.name,
      type: layer.type,
      visible: true,
      source: layer.source,
      ...layer
    })
  }

  // 移除业务图层
  const removeBusinessLayer = (layerId) => {
    const index = businessLayers.value.findIndex(layer => layer.id === layerId)
    if (index > -1) {
      businessLayers.value.splice(index, 1)
    }
  }

  // 切换图层可见性
  const toggleLayerVisibility = (layerId, isBusiness = false) => {
    if (isBusiness) {
      const layer = businessLayers.value.find(l => l.id === layerId)
      if (layer) {
        layer.visible = !layer.visible
      }
    } else {
      const layer = baseMaps.find(l => l.id === layerId)
      if (layer) {
        layer.visible = !layer.visible
      }
    }
  }

  // 切换底图
  const switchBaseMap = (baseMapId) => {
    currentBaseMap.value = baseMapId
    // 更新底图可见性
    baseMaps.forEach(map => {
      map.visible = map.id === baseMapId
    })
  }

  return {
    baseMaps,
    businessLayers,
    currentBaseMap,
    addBusinessLayer,
    removeBusinessLayer,
    toggleLayerVisibility,
    switchBaseMap
  }
} 