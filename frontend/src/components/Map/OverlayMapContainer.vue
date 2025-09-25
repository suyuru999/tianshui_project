<template>
  <div id="overlay-map-container">
    <!-- 地图主体 -->
    <div id="overlay-map"></div>

    <!-- 缩放控制 -->
    <div class="zoom-controls">
      <button class="zoom-btn" @click="zoomIn" title="放大">+</button>
      <button class="zoom-btn" @click="zoomOut" title="缩小">-</button>
    </div>

    <!-- 比例尺 -->
    <div class="scale-bar">
      <div class="scale-text">50 km</div>
      <div class="scale-line"></div>
    </div>

    <!-- 坐标显示 -->
    <div class="coordinate-display">
      <div>经度: {{ coordinates.lng }}</div>
      <div>纬度: {{ coordinates.lat }}</div>
    </div>

    <!-- 地图类型选择 -->
    <div class="map-type-selector">
      <div class="selector-title">底图类型</div>
      <div class="selector-options">
        <label v-for="type in mapTypes" :key="type.id" class="map-type-option">
          <input
            type="radio"
            :name="'baseMap'"
            :value="type.id"
            v-model="currentMapType"
          />
          <span>{{ type.name }}</span>
        </label>
      </div>
    </div>
    
    <!-- 版权信息 -->
    <div class="attribution">
      天地图 © 国家基础地理信息中心
    </div>

    <!-- 项目信息弹窗 -->
    <div v-if="selectedProjectInfo" class="project-popup">
      <div class="popup-header">
        <h3>{{ selectedProjectInfo.name }}</h3>
        <button class="close-btn" @click="closeProjectPopup">×</button>
      </div>
      <div class="popup-content">
        <div class="info-item">
          <span class="label">项目类型:</span>
          <span class="value">{{ selectedProjectInfo.type }}</span>
        </div>
        <div class="info-item">
          <span class="label">项目面积:</span>
          <span class="value">{{ selectedProjectInfo.area }}</span>
        </div>
        <div class="info-item">
          <span class="label">项目状态:</span>
          <span class="value status" :class="selectedProjectInfo.status">{{ selectedProjectInfo.status }}</span>
        </div>
        <div class="info-item">
          <span class="label">开始时间:</span>
          <span class="value">{{ selectedProjectInfo.startDate }}</span>
        </div>
        <div class="info-item">
          <span class="label">结束时间:</span>
          <span class="value">{{ selectedProjectInfo.endDate }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import 'ol/ol.css'
import Map from 'ol/Map'
import View from 'ol/View'
import { defaults as defaultControls } from 'ol/control'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import XYZ from 'ol/source/XYZ'
import { Style, Fill, Stroke, Circle } from 'ol/style'
import { GeoJSON } from 'ol/format'
import { fromLonLat } from 'ol/proj'
import { MapUtils } from '../../utils/mapUtils'

// Props
const props = defineProps({
  overlayLayers: {
    type: Array,
    default: () => []
  },
  selectedProject: {
    type: [String, Number],
    default: null
  }
})

// 图层引用
let projectLayer = null
let environmentalLayer = null
let economicLayer = null
let customLayers = new Map() // 存储自定义图层

// Emits
const emit = defineEmits(['project-click'])

// 地图相关
let map
const coordinates = reactive({ lng: '-', lat: '-' })
const selectedProjectInfo = ref(null)

// 项目数据
const projects = [
  {
    id: 1,
    name: '天水市生态修复工程',
    type: '生态修复',
    area: '15.6 km²',
    status: '进行中',
    startDate: '2023-01-01',
    endDate: '2025-12-31',
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [105.7, 34.6],
        [105.8, 34.6],
        [105.8, 34.7],
        [105.7, 34.7],
        [105.7, 34.6]
      ]]
    }
  },
  {
    id: 2,
    name: '麦积区环境治理项目',
    type: '环境治理',
    area: '8.2 km²',
    status: '已完成',
    startDate: '2022-06-01',
    endDate: '2023-12-31',
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [105.6, 34.5],
        [105.7, 34.5],
        [105.7, 34.6],
        [105.6, 34.6],
        [105.6, 34.5]
      ]]
    }
  },
  {
    id: 3,
    name: '渭河流域生态保护',
    type: '生态保护',
    area: '25.3 km²',
    status: '规划中',
    startDate: '2024-03-01',
    endDate: '2026-12-31',
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [105.5, 34.4],
        [105.6, 34.4],
        [105.6, 34.5],
        [105.5, 34.5],
        [105.5, 34.4]
      ]]
    }
  }
]

// 地图类型
const mapTypes = [
  { id: 'tdt_vec', name: '天地图-标准' },
  { id: 'tdt_img', name: '天地图-影像' },
  { id: 'tdt_ter', name: '天地图-地形' },
  { id: 'tdt_gray', name: '天地图-灰色' }
]
const currentMapType = ref('tdt_vec')
let baseLayer = null

// 创建底图 - 直接使用与MapContainer.vue相同的方式
const createBaseMap = () => {
  // 直接使用MapUtils创建底图，与主界面保持一致
  const baseLayer = MapUtils.createBaseMap(currentMapType.value)
  
  // 添加调试信息
  console.log('创建底图类型:', currentMapType.value)
  
  // 获取底图URL
  const source = baseLayer.getSource()
  if (source && source.getUrls) {
    const urls = source.getUrls()
    console.log('底图URLs:', urls)
  } else if (source && source.getUrl) {
    const url = source.getUrl()
    console.log('底图URL:', url)
  }
  
  // 创建标注图层
  const labelLayer = new TileLayer({
    source: new XYZ({
      url: `https://t{0-7}.tianditu.gov.cn/cva_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cva&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=69874af7f35c741d7132c50f80acad29`,
      crossOrigin: 'anonymous'
    }),
    zIndex: 1 // 确保标注图层在上面
  })
  
  console.log('创建标注图层')
  
  // 返回图层组
  return [baseLayer, labelLayer]
}

// 创建项目图层
const createProjectLayer = () => {
  const features = projects.map(project => {
    const feature = new GeoJSON().readFeature(project.geometry)
    feature.setId(project.id)
    // 只设置需要的属性，避免设置整个对象
    feature.setProperties({
      id: project.id,
      name: project.name,
      type: project.type,
      area: project.area,
      status: project.status,
      startDate: project.startDate,
      endDate: project.endDate
    })
    return feature
  })

  const source = new VectorSource({
    features: features
  })

  const layer = new VectorLayer({
    source: source,
    style: (feature) => {
      const project = feature.getProperties()
      const status = project.status
      
      let fillColor = '#52c41a' // 默认绿色
      if (status === '已完成') fillColor = '#1890ff'
      else if (status === '规划中') fillColor = '#faad14'
      
      return new Style({
        fill: new Fill({
          color: fillColor + '40' // 添加透明度
        }),
        stroke: new Stroke({
          color: fillColor,
          width: 2
        })
      })
    }
  })

  layer.set('layerId', 'restoration_projects')
  return layer
}

// 创建环境质量图层
const createEnvironmentalQualityLayer = () => {
  // 模拟环境质量数据
  const qualityData = {
    type: 'Polygon',
    coordinates: [[
      [105.65, 34.55],
      [105.75, 34.55],
      [105.75, 34.65],
      [105.65, 34.65],
      [105.65, 34.55]
    ]]
  }

  const feature = new GeoJSON().readFeature(qualityData)
  const source = new VectorSource({
    features: [feature]
  })

  const layer = new VectorLayer({
    source: source,
    style: new Style({
      fill: new Fill({
        color: '#1890ff40'
      }),
      stroke: new Stroke({
        color: '#1890ff',
        width: 2
      })
    })
  })

  layer.set('layerId', 'environmental_quality')
  return layer
}

// 创建社会经济数据图层
const createSocioEconomicLayer = () => {
  // 模拟社会经济数据
  const economicData = {
    type: 'Polygon',
    coordinates: [[
      [105.6, 34.5],
      [105.7, 34.5],
      [105.7, 34.6],
      [105.6, 34.6],
      [105.6, 34.5]
    ]]
  }

  const feature = new GeoJSON().readFeature(economicData)
  const source = new VectorSource({
    features: [feature]
  })

  const layer = new VectorLayer({
    source: source,
    style: new Style({
      fill: new Fill({
        color: '#faad1440'
      }),
      stroke: new Stroke({
        color: '#faad14',
        width: 2
      })
    })
  })

  layer.set('layerId', 'socio_economic')
  return layer
}

// 创建自定义图层
const createCustomLayer = (layerData) => {
  const features = new GeoJSON().readFeatures(layerData.data)
  const source = new VectorSource({
    features: features
  })

  const layer = new VectorLayer({
    source: source,
    style: new Style({
      fill: new Fill({
        color: layerData.color + '40'
      }),
      stroke: new Stroke({
        color: layerData.color,
        width: 2
      })
    })
  })

  layer.set('layerId', layerData.id)
  return layer
}

// 初始化地图
const initMap = () => {
  const mapElement = document.getElementById('overlay-map')
  if (!mapElement) {
    console.error('地图容器未找到')
    return
  }

  // 检查容器尺寸
  const rect = mapElement.getBoundingClientRect()
  console.log('地图容器尺寸:', rect.width, 'x', rect.height)
  
  if (rect.width === 0 || rect.height === 0) {
    console.warn('地图容器尺寸为0，延迟初始化')
    setTimeout(() => initMap(), 300)
    return
  }

  // 强制设置容器尺寸
  const parentElement = mapElement.parentElement
  if (parentElement) {
    const parentRect = parentElement.getBoundingClientRect()
    mapElement.style.width = parentRect.width + 'px'
    mapElement.style.height = parentRect.height + 'px'
  } else {
    mapElement.style.width = '100%'
    mapElement.style.height = '100%'
  }
  mapElement.style.minHeight = '400px'
  mapElement.style.flex = '1'
  mapElement.style.display = 'block'

  const baseLayers = createBaseMap()
  baseLayer = baseLayers[0] // 底图
  const labelLayer = baseLayers[1] // 标注图层
  
  // 添加瓦片加载事件监听
  const source = baseLayer.getSource()
  source.on('tileloadstart', (event) => {
    console.log('初始化时开始加载底图瓦片:', event.tile.src_)
  })
  
  source.on('tileloadend', (event) => {
    console.log('初始化时底图瓦片加载完成:', event.tile.src_)
  })
  
  
  source.on('tileloaderror', (event) => {
    console.error('初始化时底图瓦片加载失败:', event.tile.src_, event)
    
    // 如果天地图加载失败，切换到高德地图作为备用
    console.warn('天地图加载失败，切换到高德地图')
    baseLayer.setSource(new XYZ({
      url: 'https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
      crossOrigin: 'anonymous'
    }))
  })
  
  // 添加标注图层加载事件监听
  const labelSource = labelLayer.getSource()
  labelSource.on('tileloadstart', (event) => {
    console.log('初始化时开始加载标注瓦片:', event.tile.src_)
  })
  
  labelSource.on('tileloadend', (event) => {
    console.log('初始化时标注瓦片加载完成:', event.tile.src_)
  })
  
  labelSource.on('tileloaderror', (event) => {
    console.error('初始化时标注瓦片加载失败:', event.tile.src_, event)
  })
  
  projectLayer = createProjectLayer()
  environmentalLayer = createEnvironmentalQualityLayer()
  economicLayer = createSocioEconomicLayer()

  // 创建地图，添加底图和标注图层
  map = new Map({
    target: 'overlay-map',
    layers: [
      baseLayer,
      labelLayer
    ],
    view: new View({
      center: [105.7, 34.6], // 天水市坐标
      zoom: 8,
      // 确保使用正确的投影
      projection: 'EPSG:3857'
    }),
    controls: defaultControls({ zoom: false })
  })
  
  // 添加地图渲染开始和结束事件监听
  map.on('precompose', () => {
    console.log('地图开始渲染')
  })
  
  map.on('postcompose', () => {
    console.log('地图渲染后处理')
  })
  
  // 检查底图和标注图层是否可见
  console.log('底图可见性:', baseLayer.getVisible())
  console.log('标注图层可见性:', labelLayer.getVisible())
  
  // 确保图层可见
  baseLayer.setVisible(true)
  labelLayer.setVisible(true)
  console.log('设置底图和标注图层为可见')
  
  // 立即添加其他图层，不要延迟
  console.log('添加项目图层')
  map.addLayer(projectLayer)
  
  console.log('添加环境质量图层')
  map.addLayer(environmentalLayer)
  
  console.log('添加社会经济数据图层')
  map.addLayer(economicLayer)

  console.log('地图初始化完成', map)
  console.log('地图图层数量:', map.getLayers().getLength())
  
  // 检查地图是否正确渲染
  map.on('rendercomplete', () => {
    console.log('地图渲染完成')
  })
  
  // 强制刷新地图，确保地图正确渲染
  setTimeout(() => {
    map.updateSize()
    map.getView().setCenter([105.7, 34.6])
    console.log('地图已刷新 - 1秒后')
  }, 1000)
  
  // 再次刷新地图，解决底图消失问题
  setTimeout(() => {
    map.updateSize()
    // 强制重新渲染所有图层
    const layers = map.getLayers().getArray()
    layers.forEach(layer => {
      layer.setVisible(false)
      layer.setVisible(true)
    })
    console.log('地图已再次刷新 - 2秒后')
  }, 2000)

  // 监听鼠标移动，更新坐标显示
  map.on('pointermove', (event) => {
    const coordinate = event.coordinate
    // 直接使用坐标，不需要转换
    coordinates.lng = coordinate[0].toFixed(4)
    coordinates.lat = coordinate[1].toFixed(4)
  })

  // 监听项目点击
  map.on('click', (event) => {
    const features = map.getFeaturesAtPixel(event.pixel)
    if (features.length > 0) {
      const feature = features[0]
      const project = feature.getProperties()
      if (project.id) {
        selectedProjectInfo.value = project
        emit('project-click', project.id)
      }
    }
  })

  // 监听窗口大小变化
  window.addEventListener('resize', () => {
    if (map) {
      map.updateSize()
    }
  })
}

// 缩放控制
const zoomIn = () => {
  const view = map.getView()
  const zoom = view.getZoom()
  view.animate({
    zoom: zoom + 1,
    duration: 250
  })
}

const zoomOut = () => {
  const view = map.getView()
  const zoom = view.getZoom()
  view.animate({
    zoom: zoom - 1,
    duration: 250
  })
}

// 关闭项目弹窗
const closeProjectPopup = () => {
  selectedProjectInfo.value = null
}

// 监听选中项目变化
watch(() => props.selectedProject, (newProjectId) => {
  if (newProjectId) {
    const project = projects.find(p => p.id == newProjectId)
    if (project) {
      selectedProjectInfo.value = project
    }
  }
})

// 监听叠加图层变化
watch(() => props.overlayLayers, (newLayers) => {
  if (!map) return
  
  // 获取所有图层ID
  const visibleLayerIds = newLayers.map(layer => layer.id)
  
  // 控制项目图层显示
  if (projectLayer) {
    const shouldShow = visibleLayerIds.includes('restoration_projects')
    projectLayer.setVisible(shouldShow)
  }
  
  // 控制环境质量图层显示
  if (environmentalLayer) {
    const shouldShow = visibleLayerIds.includes('environmental_quality')
    environmentalLayer.setVisible(shouldShow)
  }
  
  // 控制社会经济图层显示
  if (economicLayer) {
    const shouldShow = visibleLayerIds.includes('socio_economic')
    economicLayer.setVisible(shouldShow)
  }
  
  // 控制自定义图层显示（容错处理）
  if (customLayers && typeof customLayers.forEach === 'function') {
    customLayers.forEach((layer, layerId) => {
      const shouldShow = visibleLayerIds.includes(layerId)
      layer.setVisible(shouldShow)
    })
  }
}, { deep: true })

// 添加自定义图层
const addCustomLayer = (layerData) => {
  if (!map) return
  
  const customLayer = createCustomLayer(layerData)
  customLayers.set(layerData.id, customLayer)
  map.addLayer(customLayer)
}

// 暴露方法给父组件
defineExpose({
  addCustomLayer
})

  // 监听底图类型变化，切换底图
watch(currentMapType, (newType) => {
  if (!map) return
  console.log('切换底图类型:', newType)
  
  // 获取当前所有图层
  const allLayers = map.getLayers().getArray();
  
  // 保存除底图和标注图层外的所有图层
  const otherLayers = allLayers.slice(2);
  
  // 清除所有图层
  map.setLayers([]);
  
  // 创建新底图和标注
  const baseLayers = createBaseMap();
  baseLayer = baseLayers[0];
  const labelLayer = baseLayers[1];
  
  // 添加事件监听
  const source = baseLayer.getSource();
  source.on('tileloadstart', (event) => {
    console.log('开始加载瓦片:', event.tile.src_);
  });
  
  source.on('tileloadend', (event) => {
    console.log('瓦片加载完成:', event.tile.src_);
  });
  
  source.on('tileloaderror', (event) => {
    console.error('瓦片加载失败:', event.tile.src_, event);
  });
  
  // 先添加底图和标注图层
  map.addLayer(baseLayer);
  map.addLayer(labelLayer);
  
  // 然后添加其他图层
  otherLayers.forEach(layer => {
    map.addLayer(layer);
  });
})

onMounted(() => {
  // 使用 nextTick 确保 DOM 完全渲染
  nextTick(() => {
    const mapElement = document.getElementById('overlay-map')
    if (mapElement) {
      // 使用 ResizeObserver 监听容器尺寸变化
      const resizeObserver = new ResizeObserver((entries) => {
        for (let entry of entries) {
          const { width, height } = entry.contentRect
          if (width > 0 && height > 0) {
            console.log('容器尺寸变化:', width, 'x', height)
            initMap()
            resizeObserver.disconnect()
            break
          }
        }
      })
      resizeObserver.observe(mapElement)
      
      // 备用方案：延迟初始化
      setTimeout(() => {
        if (!map) {
          initMap()
        }
      }, 1000)
    } else {
      // 如果找不到元素，延迟重试
      setTimeout(() => {
        initMap()
      }, 500)
    }
  })
})

onUnmounted(() => {
  if (map) {
    map.setTarget(undefined)
  }
})
</script>

<style scoped>
#overlay-map-container {
  width: 100%;
  height: 100%;
  position: relative;
  min-height: 500px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

#overlay-map {
  width: 100%;
  height: 100%;
  min-height: 500px;
  flex: 1;
  display: block;
  position: relative;
}

/* 缩放控制 */
.zoom-controls {
  position: absolute;
  top: 20px;
  right: 20px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  overflow: hidden;
}

.zoom-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: white;
  cursor: pointer;
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.zoom-btn:hover {
  background: #f5f5f5;
}

.zoom-btn:first-child {
  border-bottom: 1px solid #f0f0f0;
}

/* 比例尺 */
.scale-bar {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 12px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.scale-text {
  font-size: 12px;
  color: #333;
  font-weight: 500;
}

.scale-line {
  width: 60px;
  height: 2px;
  background: #333;
  position: relative;
}

.scale-line::before,
.scale-line::after {
  content: '';
  position: absolute;
  width: 2px;
  height: 8px;
  background: #333;
  top: -3px;
}

.scale-line::before {
  left: 0;
}

.scale-line::after {
  right: 0;
}

/* 坐标显示 */
.coordinate-display {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  color: #333;
  line-height: 1.4;
}

/* 地图类型选择器 */
.map-type-selector {
  position: absolute;
  top: 20px;
  right: 70px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  padding: 10px;
  z-index: 1000;
}

.selector-title {
  font-size: 13px;
  color: #333;
  font-weight: bold;
  margin-bottom: 6px;
}

.selector-options {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.map-type-option {
  font-size: 13px;
  color: #333;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

/* 版权信息 */
.attribution {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-size: 11px;
  color: #666;
  background: rgba(255, 255, 255, 0.8);
  padding: 2px 6px;
  border-radius: 2px;
}

/* 项目信息弹窗 */
.project-popup {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  min-width: 300px;
  max-width: 400px;
  z-index: 1000;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
  border-radius: 8px 8px 0 0;
}

.popup-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}

.popup-content {
  padding: 20px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.info-item:last-child {
  border-bottom: none;
}

.label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.value {
  font-size: 13px;
  color: #333;
}

.value.status {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.value.status.进行中 {
  background: #e6f7ff;
  color: #1890ff;
}

.value.status.已完成 {
  background: #f6ffed;
  color: #52c41a;
}

.value.status.规划中 {
  background: #fffbe6;
  color: #faad14;
}
</style>
