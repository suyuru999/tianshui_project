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
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import 'ol/ol.css'
import { Map as OLMap } from 'ol'
import View from 'ol/View'
import { defaults as defaultControls } from 'ol/control'
import TileLayer from 'ol/layer/Tile'
import XYZ from 'ol/source/XYZ'
import TileWMS from 'ol/source/TileWMS'
// 不再需要坐标转换，直接使用 EPSG:4326
import { MapUtils } from '../../utils/mapUtils'
import { API_CONFIG } from '../../config/api.js'
import OverlayAnalysisPopup from './OverlayAnalysisPopup.vue'

// Props
const props = defineProps({
  layerVisibility: {
    type: Object,
    default: () => ({
      ecology: true,
      economy: true,
      engineering: true
    })
  }
})

// 地图配置
const TDT_TOKEN = '69874af7f35c741d7132c50f80acad29'
const GEOSERVER_WORKSPACE = 'tianshuipy'
const GEOSERVER_OWS_PROXY = `${API_CONFIG.BASE_URL}/${API_CONFIG.VERSION}/environment/geoserver/ows/`
const TIANSHUI_CENTER = [105.7, 34.6] // 天水市中心坐标

// 地图实例
let map = null
let ecologyRasterLayer = null
let economyVectorLayer = null
let engineeringVectorLayer = null

// 坐标显示
const coordinates = reactive({ lng: '105.7000', lat: '34.6000' })

// 弹窗数据
const popup = reactive({
  visible: false,
  coordinate: { lng: 0, lat: 0 },
  ecologyData: null,
  economyData: null,
  engineeringData: []
})

// 监听图层可见性变化
watch(() => props.layerVisibility, (newVal) => {
  if (ecologyRasterLayer) {
    ecologyRasterLayer.setVisible(newVal.ecology)
  }
  if (economyVectorLayer) {
    economyVectorLayer.setVisible(newVal.economy)
  }
  if (engineeringVectorLayer) {
    engineeringVectorLayer.setVisible(newVal.engineering)
  }
}, { deep: true })

// 创建高德底图（稳定可靠）
const createBaseMap = () => {
  return new TileLayer({
    source: new XYZ({
      url: 'https://webrd0{1-4}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
          crossOrigin: 'anonymous'
    }),
    visible: true,
    zIndex: 0
  })
}

// 创建三个WMS图层
const createWMSLayers = () => {
  const wmsBaseUrl = GEOSERVER_OWS_PROXY
  
  // WMS 通用参数（使用 1.1.0 版本，更兼容）
  const wmsCommonParams = {
    'VERSION': '1.1.0',
    'TILED': true,
    'TRANSPARENT': true,
    'FORMAT': 'image/png',
    'SRS': 'EPSG:4326'  // 使用 SRS 对应 WMS 1.1.0，与 View 投影一致
  }
  
  // 1. 生态栅格图层
  ecologyRasterLayer = new TileLayer({
    source: new TileWMS({
    url: wmsBaseUrl,
    params: {
        ...wmsCommonParams,
        'LAYERS': `${GEOSERVER_WORKSPACE}:ecology_raster`
    },
    serverType: 'geoserver',
    crossOrigin: 'anonymous'
    }),
    visible: props.layerVisibility.ecology,
    opacity: 0.7,
    zIndex: 2
  })
  
  // 2. 经济矢量图层
  economyVectorLayer = new TileLayer({
    source: new TileWMS({
    url: wmsBaseUrl,
    params: {
        ...wmsCommonParams,
        'LAYERS': `${GEOSERVER_WORKSPACE}:economy_vector`
    },
    serverType: 'geoserver',
    crossOrigin: 'anonymous'
    }),
    visible: props.layerVisibility.economy,
    opacity: 0.6,
    zIndex: 3
  })
  
  // 3. 工程矢量图层
  engineeringVectorLayer = new TileLayer({
    source: new TileWMS({
    url: wmsBaseUrl,
    params: {
        ...wmsCommonParams,
        'LAYERS': `${GEOSERVER_WORKSPACE}:engineering_vector`
    },
    serverType: 'geoserver',
    crossOrigin: 'anonymous'
    }),
    visible: props.layerVisibility.engineering,
    opacity: 0.8,
    zIndex: 4
  })
  
  return [ecologyRasterLayer, economyVectorLayer, engineeringVectorLayer]
}

// 初始化地图
const initMap = () => {
  try {
    console.log('🗺️ 初始化重大工程叠加分析地图...')
    
    const mapElement = document.getElementById('overlay-map')
    if (!mapElement) {
      console.error('❌ 地图容器未找到')
      return
    }
    
    console.log('📦 地图容器尺寸:', {
      width: mapElement.offsetWidth,
      height: mapElement.offsetHeight
    })
    
    // 创建高德底图
    const gaodeLayer = createBaseMap()
    
    // 创建三个WMS图层
    const wmsLayers = createWMSLayers()
    
    // 创建地图（直接使用经纬度坐标，不需要转换）
    map = new OLMap({
      target: 'overlay-map',
      layers: [gaodeLayer, ...wmsLayers],
      view: new View({
        projection: 'EPSG:4326',  // ✅ 关键：使用 EPSG:4326 投影
        center: [105.7, 34.6],     // ✅ 直接使用经纬度坐标
        zoom: 10
      }),
      controls: defaultControls({ zoom: false })
    })
    
    console.log('✅ 地图对象创建完成')
    console.log('📍 地图中心点:', map.getView().getCenter())
    console.log('📦 已加载图层数:', map.getLayers().getLength())
    console.log('🔍 地图尺寸:', map.getSize())
    
    // 设置地图点击事件
    map.on('click', handleMapClick)
    
    // 设置鼠标移动事件（更新坐标显示）
    map.on('pointermove', (event) => {
      // 坐标已经是 EPSG:4326 (经纬度)，无需转换
      const coord = event.coordinate
      if (coord && !isNaN(coord[0]) && !isNaN(coord[1])) {
        coordinates.lng = coord[0].toFixed(4)
        coordinates.lat = coord[1].toFixed(4)
      }
    })
    
    // 强制刷新地图
    setTimeout(() => {
      if (map) {
        map.updateSize()
        const newSize = map.getSize()
        console.log('🔄 地图尺寸更新:', newSize)
      map.render()
        console.log('✅ 地图渲染完成')
    }
  }, 200)
  
    // 再次刷新（确保底图显示）
  setTimeout(() => {
      if (map) {
    map.updateSize()
    map.render()
        console.log('🔄 地图二次刷新完成')
      }
  }, 500)
  
    } catch (error) {
    console.error('❌ 地图初始化失败:', error)
    console.error('错误堆栈:', error.stack)
  }
}

// 处理地图点击事件
const handleMapClick = async (event) => {
  try {
    console.log('🖱️ 地图点击事件触发')
    
    // 坐标已经是 EPSG:4326 (经纬度)，无需转换
    const coord = event.coordinate
    
    console.log('📍 点击坐标 (经纬度):', coord)
    
    // 重置弹窗数据
    popup.visible = false
    popup.coordinate = { lng: coord[0], lat: coord[1] }
    popup.ecologyData = null
    popup.economyData = null
    popup.engineeringData = []
        
        // 准备图层源映射
    const layerSources = {
      ecology: ecologyRasterLayer?.getSource(),
      economy: economyVectorLayer?.getSource(),
      engineering: engineeringVectorLayer?.getSource()
    }
    
    console.log('🔍 开始获取图层信息...')
        
        // 批量获取GetFeatureInfo
        const results = await MapUtils.getMultipleFeatureInfo(layerSources, coord, map)
    
    console.log('📊 GetFeatureInfo结果:', results)
        
        // 解析生态栅格数据
        if (results.ecology) {
      popup.ecologyData = parseEcologyData(results.ecology)
      console.log('🌿 生态数据:', popup.ecologyData)
        }
        
        // 解析经济矢量数据
        if (results.economy) {
      popup.economyData = parseEconomyData(results.economy)
      console.log('💰 经济数据:', popup.economyData)
        }
        
        // 解析工程矢量数据
        if (results.engineering) {
      popup.engineeringData = parseEngineeringData(results.engineering)
      console.log('🏗️ 工程数据:', popup.engineeringData)
        }
        
        // 显示弹窗
    popup.visible = true
    console.log('✅ 弹窗已打开')
        
      } catch (error) {
    console.error('❌ 处理地图点击失败:', error)
  }
}

// 解析生态栅格数据
const parseEcologyData = (data) => {
  try {
    if (!data.features || data.features.length === 0) {
      return null
    }
    
      const feature = data.features[0]
      const properties = feature.properties || {}
      
      // 查找栅格值（可能在不同字段中）
      let value = null
    const possibleFields = ['GRAY_INDEX', 'Band1', 'value', 'pixel_value']
    
    for (const field of possibleFields) {
      if (properties[field] !== undefined && properties[field] !== null) {
        value = parseFloat(properties[field])
            break
          }
        }
    
    if (value === null) {
      return null
      }
      
    // 判断等级（假设栅格值范围是0-1，或者50-1000）
        let normalizedValue = value
        if (value >= 50 && value <= 1000) {
      normalizedValue = (value - 50) / 950 // 归一化到0-1
        }
        
    let level = '较差'
        if (normalizedValue >= 0.6) level = '优秀'
        else if (normalizedValue >= 0.4) level = '良好'
        else if (normalizedValue >= 0.2) level = '中等'
        
        return {
          value: value,
          normalizedValue: normalizedValue,
          level: level
        }
  } catch (error) {
    console.error('解析生态数据失败:', error)
    return null
  }
}

// 解析经济矢量数据
const parseEconomyData = (data) => {
  try {
    if (!data.features || data.features.length === 0) {
      return null
    }
    
    const feature = data.features[0]
    const properties = feature.properties || {}
    
    // 调试：打印所有属性
    console.log('💰 经济数据原始属性:', properties)
    console.log('💰 所有属性键:', Object.keys(properties))
    
    // 辅助函数：安全获取字符串值（处理空字符串、null、undefined、占位符）
    const getStringValue = (...keys) => {
      // 无效值列表（包括常见的占位符）
      const invalidValues = ['', 'null', 'undefined', 'N/A', 'NA', '-', 'none', 'None', 'NONE']
      
      for (const key of keys) {
        const value = properties[key]
        if (value !== null && value !== undefined) {
          const strValue = String(value).trim()
          // 检查是否为有效值
          if (strValue !== '') {
            // 检查是否只包含问号（任意数量）
            if (/^\?+$/.test(strValue)) {
              continue // 跳过，尝试下一个字段
            }
            // 检查是否在无效值列表中
            if (!invalidValues.includes(strValue)) {
              return strValue
            }
          }
        }
      }
      return null // 返回null，让前端组件处理
    }
    
    return {
      admin_name: getStringValue('admin_name', 'ADMIN_NAME', 'name', 'NAME', 'region_name', 'REGION_NAME'),
      GDP: parseFloat(properties.GDP || properties.gdp || properties.Gdp || 0),
      POP: parseInt(properties.POP || properties.pop || properties.Pop || 0),
      area_km2: parseFloat(properties.area_km2 || properties.AREA_KM2 || properties.area || properties.AREA || 0)
    }
  } catch (error) {
    console.error('解析经济数据失败:', error)
    return null
  }
}

// 解析工程矢量数据
const parseEngineeringData = (data) => {
  try {
    if (!data.features || data.features.length === 0) {
      return []
    }
    
    // 辅助函数：安全获取字符串值（处理空字符串、null、undefined、占位符）
    const getStringValue = (properties, ...keys) => {
      // 无效值列表（包括常见的占位符）
      const invalidValues = ['', 'null', 'undefined', 'N/A', 'NA', '-', 'none', 'None', 'NONE']
      
      for (const key of keys) {
        const value = properties[key]
        if (value !== null && value !== undefined) {
          const strValue = String(value).trim()
          // 检查是否为有效值
          if (strValue !== '') {
            // 检查是否只包含问号（任意数量）
            if (/^\?+$/.test(strValue)) {
              continue // 跳过，尝试下一个字段
            }
            // 检查是否在无效值列表中
            if (!invalidValues.includes(strValue)) {
              return strValue
            }
          }
        }
      }
      return null // 返回null，让前端组件处理
    }
    
    return data.features.map((feature, index) => {
      const properties = feature.properties || {}
      
      // 调试：打印第一个要素的属性
      if (index === 0) {
        console.log('🏗️ 工程数据原始属性:', properties)
        console.log('🏗️ 所有属性键:', Object.keys(properties))
      }
      
      return {
        proj_name: getStringValue(properties, 'proj_name', 'PROJ_NAME', 'name', 'NAME', 'project_name', 'PROJECT_NAME'),
        proj_type: getStringValue(properties, 'proj_type', 'PROJ_TYPE', 'type', 'TYPE', 'project_type', 'PROJECT_TYPE'),
        status: getStringValue(properties, 'status', 'STATUS', 'state', 'STATE'),
        start_date: getStringValue(properties, 'start_date', 'START_DATE', 'start_time', 'START_TIME', 'begin_date', 'BEGIN_DATE') || '',
        end_date: getStringValue(properties, 'end_date', 'END_DATE', 'end_time', 'END_TIME', 'finish_date', 'FINISH_DATE') || '',
        area_km2: parseFloat(properties.area_km2 || properties.AREA_KM2 || properties.area || properties.AREA || 0)
      }
    })
  } catch (error) {
    console.error('解析工程数据失败:', error)
    return []
  }
}

// 切换图层可见性
const toggleLayer = (layerType) => {
  try {
    if (layerType === 'ecology' && ecologyRasterLayer) {
      ecologyRasterLayer.setVisible(props.layerVisibility.ecology)
    } else if (layerType === 'economy' && economyVectorLayer) {
      economyVectorLayer.setVisible(props.layerVisibility.economy)
    } else if (layerType === 'engineering' && engineeringVectorLayer) {
      engineeringVectorLayer.setVisible(props.layerVisibility.engineering)
    }
    
    map?.render()
  } catch (error) {
    console.error('切换图层失败:', error)
  }
}

// 刷新地图
const refreshMap = () => {
  handleRefreshMap()
}

// 暴露方法给父组件
defineExpose({
  toggleLayer,
  refreshMap
})

// 关闭弹窗
const closePopup = () => {
  popup.visible = false
}

// 处理地图刷新（上传完成后）
const handleRefreshMap = () => {
  console.log('🔄 数据上传完成，刷新地图图层...')
  
  // 刷新所有WMS图层
  if (ecologyRasterLayer) {
    const source = ecologyRasterLayer.getSource()
    source.updateParams({ 'timestamp': Date.now() })
    source.refresh()
  }
  
  if (economyVectorLayer) {
    const source = economyVectorLayer.getSource()
    source.updateParams({ 'timestamp': Date.now() })
    source.refresh()
  }
  
  if (engineeringVectorLayer) {
    const source = engineeringVectorLayer.getSource()
    source.updateParams({ 'timestamp': Date.now() })
    source.refresh()
  }
  
  // 强制地图重新渲染
  if (map) {
    map.render()
  }
  
  console.log('✅ 地图图层已刷新')
}

// 缩放控制
const zoomIn = () => {
  const view = map?.getView()
  if (view) {
    const zoom = view.getZoom()
    view.animate({ zoom: zoom + 1, duration: 250 })
  }
}

const zoomOut = () => {
  const view = map?.getView()
  if (view) {
    const zoom = view.getZoom()
    view.animate({ zoom: zoom - 1, duration: 250 })
  }
}

// 生命周期
onMounted(() => {
  console.log('🚀 OverlayMapContainer 组件已挂载')
  
  // 等待DOM完全渲染
      setTimeout(() => {
    const mapElement = document.getElementById('overlay-map')
    if (mapElement) {
      console.log('✅ 地图容器已找到')
      console.log('📏 容器尺寸:', {
        offsetWidth: mapElement.offsetWidth,
        offsetHeight: mapElement.offsetHeight
      })
      
      // 如果容器尺寸为0，等待更长时间
      if (mapElement.offsetWidth === 0 || mapElement.offsetHeight === 0) {
        console.warn('⚠️ 容器尺寸为0，延迟初始化...')
    setTimeout(() => {
          initMap()
        }, 500)
  } else {
        initMap()
        }
      } else {
      console.error('❌ 地图容器未找到')
      }
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
  background: #e5e5e5;
}

#overlay-map {
  width: 100%;
  height: 100%;
  min-height: 400px;
  position: absolute;
  top: 0;
  left: 0;
  background: #e5e5e5;
}

/* 确保OpenLayers容器正确渲染 */
#overlay-map .ol-viewport {
  position: relative !important;
}

#overlay-map canvas {
  position: absolute;
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

</style>
