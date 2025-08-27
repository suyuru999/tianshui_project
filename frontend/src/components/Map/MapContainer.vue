<template>
  <div id="map-container">
    <!-- 地图主体 -->
    <div id="map"></div>

    <!-- 左侧工具栏 -->
    <div class="left-toolbar">
      <div class="tool-item" v-for="tool in drawingTools" :key="tool.id">
        <button 
          class="tool-btn"
          :class="{ active: activeTool === tool.id }"
          @click="selectTool(tool.id)"
          :title="tool.name"
        >
          {{ tool.icon }}
        </button>
      </div>
    </div>

    <!-- 地图类型+叠加图层纵向合并面板 -->
    <div class="map-layer-panel">
      <div class="panel-section">
        <div class="panel-title">地图类型</div>
        <div class="panel-group">
          <label v-for="type in mapTypes" :key="type.id" class="radio-label">
            <input
              type="radio"
              :name="'baseMap'"
              :value="type.id"
              v-model="currentMapType"
            />
            {{ type.name }}
          </label>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-title">图层控制</div>
        <div class="panel-group">
          <label v-for="layer in overlayLayers" :key="layer.id" class="checkbox-label">
            <input
              type="checkbox"
              v-model="layer.visible"
              @change="toggleOverlayLayer(layer.id)"
            />
            {{ layer.name }}
          </label>
        </div>
      </div>
    </div>

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

    <!-- 版权信息 -->
    <div class="attribution">
      天地图  
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import 'ol/ol.css'
import Map from 'ol/Map'
import View from 'ol/View'
import { defaults as defaultControls } from 'ol/control'
import { MapUtils } from '../../utils/mapUtils'

// 地图类型
const mapTypes = [
  { id: 'tdt_vec', name: '天地图-标准' },
  { id: 'tdt_img', name: '天地图-影像' },
  { id: 'tdt_ter', name: '天地图-地形' },
  { id: 'tdt_gray', name: '天地图-灰色' },
  { id: 'osm', name: 'OSM' },
  { id: 'satellite', name: 'ArcGIS影像' },
  { id: 'terrain', name: 'ArcGIS地形' }
]
const currentMapType = ref('tdt_vec')
let baseLayer = null

let map
const activeTool = ref('select')
const coordinates = reactive({ lng: '-', lat: '-' })

// 绘图工具
const drawingTools = reactive([
  { id: 'select', name: '选择', icon: '👆' },
  { id: 'pan', name: '平移', icon: '✋' },
  { id: 'rectangle', name: '矩形', icon: '⬜' },
  { id: 'circle', name: '圆形', icon: '⭕' },
  { id: 'marker', name: '标记', icon: '📍' },
  { id: 'draw', name: '绘制', icon: '✏️' },
  { id: 'delete', name: '删除', icon: '🗑️' },
  { id: 'collapse', name: '收起', icon: '◀️' }
])

// 叠加图层
const overlayLayers = reactive([
  { id: 1, name: '水系分布 (WMS)', visible: false },
  { id: 2, name: '高程渲染 (DEM)', visible: false }, 
  { id: 3, name: '生态保护红线', visible: false }
])

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (map) {
    map.setTarget(undefined)
  }
})

// 监听底图类型变化，切换底图
watch(currentMapType, (newType) => {
  if (!map) return
  map.removeLayer(baseLayer)
  baseLayer = MapUtils.createBaseMap(newType)
  map.getLayers().insertAt(0, baseLayer)
})

// 初始化地图
const initMap = () => {
  baseLayer = MapUtils.createBaseMap(currentMapType.value)
  map = new Map({
    target: 'map',
    layers: [baseLayer],
    view: new View({
      center: [114.3162, 30.5810], // 武汉坐标
      zoom: 8
    }),
    controls: defaultControls({ zoom: false }) // 关闭默认缩放控件
  })

  // 监听鼠标移动，更新坐标显示
  map.on('pointermove', (event) => {
    const coordinate = event.coordinate
    coordinates.lng = coordinate[0].toFixed(4)
    coordinates.lat = coordinate[1].toFixed(4)
  })
}

// 选择工具
const selectTool = (toolId) => {
  activeTool.value = toolId
  console.log('选择工具:', toolId)
  // TODO: 实现工具切换逻辑
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

// 切换叠加图层
const toggleOverlayLayer = (layerId) => {
  const layer = overlayLayers.find(l => l.id === layerId)
  if (layer) {
    layer.visible = !layer.visible
    console.log('切换图层:', layer.name, layer.visible)
    // TODO: 实现图层显示/隐藏逻辑
  }
}
</script>

<style scoped>
#map-container {
  width: 100%;
  height: 100%;
  position: relative;
}

#map {
  width: 100%;
  height: 100%;
}

/* 左侧工具栏 */
.left-toolbar {
  position: absolute;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 1000;
}

.tool-item {
  display: flex;
  flex-direction: column;
}

.tool-btn {
  width: 40px;
  height: 40px;
  border: 1px solid #d9d9d9;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.tool-btn:hover {
  background: #f5f5f5;
  border-color: #1890ff;
}

.tool-btn.active {
  background: #1890ff;
  color: white;
  border-color: #1890ff;
}

/* 地图类型+叠加图层纵向合并面板 */
.map-layer-panel {
  position: absolute;
  top: 80px;
  right: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  padding: 16px 12px;
  min-width: 180px;
  z-index: 1001;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.panel-section {
  margin-bottom: 8px;
}
.panel-title {
  font-size: 13px;
  color: #333;
  font-weight: bold;
  margin-bottom: 6px;
}
.panel-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.radio-label, .checkbox-label {
  font-size: 13px;
  color: #333;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
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
</style> 