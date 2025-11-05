<template>
  <div id="overlay-map-container">
    <!-- 地图主体 -->
    <div id="overlay-map"></div>

    <!-- 缩放控制 -->
    <div class="zoom-controls">
      <button class="zoom-btn" @click="zoomIn" title="放大">+</button>
      <button class="zoom-btn" @click="zoomOut" title="缩小">-</button>
    </div>

    <!-- 坐标显示 -->
    <div class="coordinate-display">
      <div>经度: {{ coordinates.lng }}</div>
      <div>纬度: {{ coordinates.lat }}</div>
    </div>

    <!-- 图层控制面板 -->
    <div class="layer-control-panel">
      <div class="panel-title">图层控制</div>
      <div class="layer-item">
        <label>
          <input type="checkbox" v-model="layerVisibility.ecology" @change="toggleLayer('ecology')" />
          <span>生态指数栅格</span>
        </label>
      </div>
      <div class="layer-item">
        <label>
          <input type="checkbox" v-model="layerVisibility.economy" @change="toggleLayer('economy')" />
          <span>经济数据矢量</span>
        </label>
      </div>
      <div class="layer-item">
        <label>
          <input type="checkbox" v-model="layerVisibility.engineering" @change="toggleLayer('engineering')" />
          <span>工程项目矢量</span>
        </label>
      </div>
    </div>

    <!-- 底图说明 -->
    <div class="map-info">
      <small>底图：高德地图（备用方案）</small>
    </div>

    <!-- 叠加分析信息弹窗 -->
    <OverlayAnalysisPopup
      :visible="popup.visible"
      :coordinate="popup.coordinate"
      :ecology-data="popup.ecologyData"
      :economy-data="popup.economyData"
      :engineering-data="popup.engineeringData"
      @close="closePopup"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import 'ol/ol.css'
import { Map as OLMap } from 'ol'
import View from 'ol/View'
import { defaults as defaultControls } from 'ol/control'
import TileLayer from 'ol/layer/Tile'
import XYZ from 'ol/source/XYZ'
import OSM from 'ol/source/OSM'
import TileWMS from 'ol/source/TileWMS'
import { fromLonLat, toLonLat } from 'ol/proj'
import { MapUtils } from '../../utils/mapUtils'
import OverlayAnalysisPopup from './OverlayAnalysisPopup.vue'

// 地图配置
const GEOSERVER_URL = 'http://localhost:8080/geoserver'
const GEOSERVER_WORKSPACE = 'tianshuipy'
const TIANSHUI_CENTER = [105.7, 34.6] // 天水市中心坐标

// 地图实例
let map = null
let ecologyRasterLayer = null
let economyVectorLayer = null
let engineeringVectorLayer = null

// 坐标显示
const coordinates = reactive({ lng: '105.7000', lat: '34.6000' })

// 图层可见性控制
const layerVisibility = reactive({
  ecology: true,
  economy: true,
  engineering: true
})

// 弹窗数据
const popup = reactive({
  visible: false,
  coordinate: { lng: 0, lat: 0 },
  ecologyData: null,
  economyData: null,
  engineeringData: []
})

// 创建底图 - 使用高德地图（国内访问更稳定）
const createBaseMap = () => {
  console.log('📍 使用高德地图作为底图（备用方案）')
  return new TileLayer({
    source: new XYZ({
      url: 'https://webrd0{1-4}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
      crossOrigin: 'anonymous'
    }),
    visible: true,
    zIndex: 0
  })
  
  // 备选方案：使用OSM
  // return new TileLayer({
  //   source: new OSM(),
  //   visible: true,
  //   zIndex: 0
  // })
}

// 创建三个WMS图层
const createWMSLayers = () => {
  const wmsBaseUrl = `${GEOSERVER_URL}/${GEOSERVER_WORKSPACE}/wms`
  
  // 1. 生态栅格图层
  ecologyRasterLayer = new TileLayer({
    source: new TileWMS({
      url: wmsBaseUrl,
      params: {
        'LAYERS': `${GEOSERVER_WORKSPACE}:ecology_raster`,
        'TILED': true,
        'VERSION': '1.3.0',
        'FORMAT': 'image/png',
        'TRANSPARENT': true
      },
      serverType: 'geoserver',
      crossOrigin: 'anonymous'
    }),
    visible: true,
    opacity: 0.7,
    zIndex: 2
  })
  
  // 2. 经济矢量图层
  economyVectorLayer = new TileLayer({
    source: new TileWMS({
      url: wmsBaseUrl,
      params: {
        'LAYERS': `${GEOSERVER_WORKSPACE}:economy_vector`,
        'TILED': true,
        'VERSION': '1.3.0',
        'FORMAT': 'image/png',
        'TRANSPARENT': true
      },
      serverType: 'geoserver',
      crossOrigin: 'anonymous'
    }),
    visible: true,
    opacity: 0.6,
    zIndex: 3
  })
  
  // 3. 工程矢量图层
  engineeringVectorLayer = new TileLayer({
    source: new TileWMS({
      url: wmsBaseUrl,
      params: {
        'LAYERS': `${GEOSERVER_WORKSPACE}:engineering_vector`,
        'TILED': true,
        'VERSION': '1.3.0',
        'FORMAT': 'image/png',
        'TRANSPARENT': true
      },
      serverType: 'geoserver',
      crossOrigin: 'anonymous'
    }),
    visible: true,
    opacity: 0.8,
    zIndex: 4
  })
  
  return [ecologyRasterLayer, economyVectorLayer, engineeringVectorLayer]
}

// 初始化地图
const initMap = () => {
  try {
    console.log('🗺️ 初始化重大工程叠加分析地图（高德底图版本）...')
    
    // 创建底图
    const baseLayer = createBaseMap()
    
    // 监听底图加载
    baseLayer.getSource().on('tileloaderror', (event) => {
      console.error('❌ 高德地图底图加载失败:', event.tile?.src_)
    })
    
    baseLayer.getSource().on('tileloadend', () => {
      console.log('✅ 高德地图底图瓦片加载成功')
    })
    
    // 创建三个WMS图层
    const wmsLayers = createWMSLayers()
    
    // 转换中心点坐标
    const center = fromLonLat(TIANSHUI_CENTER)
    console.log('🌍 天水市坐标:', TIANSHUI_CENTER)
    console.log('🗺️ Web Mercator坐标:', center)
    
    // 创建地图
    map = new OLMap({
      target: 'overlay-map',
      layers: [baseLayer, ...wmsLayers],
      view: new View({
        center: center,
        zoom: 10,
        projection: 'EPSG:3857'
      }),
      controls: defaultControls({ zoom: false })
    })
    
    console.log('✅ 地图创建成功')
    console.log('📦 已加载图层数:', map.getLayers().getLength())
    
    // 设置地图点击事件
    map.on('click', handleMapClick)
    
    // 设置鼠标移动事件
    map.on('pointermove', (event) => {
      try {
        const lonLat = toLonLat(event.coordinate)
        if (lonLat && !isNaN(lonLat[0]) && !isNaN(lonLat[1])) {
          coordinates.lng = lonLat[0].toFixed(4)
          coordinates.lat = lonLat[1].toFixed(4)
        }
      } catch (error) {
        // 忽略坐标转换错误
      }
    })
    
    // 强制刷新地图
    setTimeout(() => {
      if (map) {
        map.updateSize()
        map.render()
        console.log('✅ 地图渲染完成')
      }
    }, 100)
    
  } catch (error) {
    console.error('❌ 地图初始化失败:', error)
  }
}

// 处理地图点击事件
const handleMapClick = async (event) => {
  try {
    console.log('🖱️ 地图点击')
    
    const coordinate = event.coordinate
    const lonLat = toLonLat(coordinate)
    
    popup.visible = false
    popup.coordinate = { lng: lonLat[0], lat: lonLat[1] }
    popup.ecologyData = null
    popup.economyData = null
    popup.engineeringData = []
    
    const layerSources = {
      ecology: ecologyRasterLayer?.getSource(),
      economy: economyVectorLayer?.getSource(),
      engineering: engineeringVectorLayer?.getSource()
    }
    
    const results = await MapUtils.getMultipleFeatureInfo(layerSources, coordinate, map)
    
    if (results.ecology) {
      popup.ecologyData = parseEcologyData(results.ecology)
    }
    
    if (results.economy) {
      popup.economyData = parseEconomyData(results.economy)
    }
    
    if (results.engineering) {
      popup.engineeringData = parseEngineeringData(results.engineering)
    }
    
    popup.visible = true
    
  } catch (error) {
    console.error('❌ 处理点击失败:', error)
  }
}

// 解析生态数据
const parseEcologyData = (data) => {
  try {
    if (!data.features || data.features.length === 0) return null
    
    const feature = data.features[0]
    const properties = feature.properties || {}
    
    let value = null
    const possibleFields = ['GRAY_INDEX', 'Band1', 'value', 'pixel_value']
    
    for (const field of possibleFields) {
      if (properties[field] !== undefined && properties[field] !== null) {
        value = parseFloat(properties[field])
        break
      }
    }
    
    if (value === null) return null
    
    let normalizedValue = value
    if (value >= 50 && value <= 1000) {
      normalizedValue = (value - 50) / 950
    }
    
    let level = '较差'
    if (normalizedValue >= 0.6) level = '优秀'
    else if (normalizedValue >= 0.4) level = '良好'
    else if (normalizedValue >= 0.2) level = '中等'
    
    return { value, normalizedValue, level }
  } catch (error) {
    return null
  }
}

// 解析经济数据
const parseEconomyData = (data) => {
  try {
    if (!data.features || data.features.length === 0) return null
    
    const feature = data.features[0]
    const properties = feature.properties || {}
    
    return {
      admin_name: properties.admin_name || properties.ADMIN_NAME || '未知',
      GDP: parseFloat(properties.GDP || properties.gdp || 0),
      POP: parseInt(properties.POP || properties.pop || 0),
      area_km2: parseFloat(properties.area_km2 || properties.AREA_KM2 || 0)
    }
  } catch (error) {
    return null
  }
}

// 解析工程数据
const parseEngineeringData = (data) => {
  try {
    if (!data.features || data.features.length === 0) return []
    
    return data.features.map(feature => {
      const properties = feature.properties || {}
      return {
        proj_name: properties.proj_name || properties.PROJ_NAME || '未知工程',
        proj_type: properties.proj_type || properties.PROJ_TYPE || '未知',
        status: properties.status || properties.STATUS || '未知',
        start_date: properties.start_date || properties.START_DATE || '',
        end_date: properties.end_date || properties.END_DATE || '',
        area_km2: parseFloat(properties.area_km2 || properties.AREA_KM2 || 0)
      }
    })
  } catch (error) {
    return []
  }
}

// 切换图层
const toggleLayer = (layerType) => {
  try {
    if (layerType === 'ecology' && ecologyRasterLayer) {
      ecologyRasterLayer.setVisible(layerVisibility.ecology)
    } else if (layerType === 'economy' && economyVectorLayer) {
      economyVectorLayer.setVisible(layerVisibility.economy)
    } else if (layerType === 'engineering' && engineeringVectorLayer) {
      engineeringVectorLayer.setVisible(layerVisibility.engineering)
    }
    map?.render()
  } catch (error) {
    console.error('切换图层失败:', error)
  }
}

// 关闭弹窗
const closePopup = () => {
  popup.visible = false
}

// 缩放控制
const zoomIn = () => {
  const view = map?.getView()
  if (view) {
    view.animate({ zoom: view.getZoom() + 1, duration: 250 })
  }
}

const zoomOut = () => {
  const view = map?.getView()
  if (view) {
    view.animate({ zoom: view.getZoom() - 1, duration: 250 })
  }
}

// 生命周期
onMounted(() => {
  console.log('🚀 OverlayMapContainer（高德底图版本）已挂载')
  setTimeout(() => {
    initMap()
  }, 100)
})

onUnmounted(() => {
  if (map) {
    map.setTarget(undefined)
    map = null
  }
})
</script>

<style scoped>
#overlay-map-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: #f0f0f0;
}

#overlay-map {
  width: 100%;
  height: 100%;
  min-height: 400px;
  position: absolute;
  top: 0;
  left: 0;
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
  z-index: 1000;
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

/* 坐标显示 */
.coordinate-display {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 12px;
  color: #333;
  line-height: 1.6;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 1000;
  font-family: 'Courier New', monospace;
}

/* 图层控制面板 */
.layer-control-panel {
  position: absolute;
  top: 20px;
  left: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  padding: 16px;
  min-width: 200px;
  z-index: 1000;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #f0f0f0;
}

.layer-item {
  margin-bottom: 10px;
}

.layer-item:last-child {
  margin-bottom: 0;
}

.layer-item label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 13px;
  color: #555;
  transition: color 0.2s;
}

.layer-item label:hover {
  color: #1890ff;
}

.layer-item input[type="checkbox"] {
  margin-right: 8px;
  cursor: pointer;
  width: 16px;
  height: 16px;
}

/* 底图说明 */
.map-info {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.9);
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 11px;
  color: #666;
  z-index: 1000;
}
</style>



