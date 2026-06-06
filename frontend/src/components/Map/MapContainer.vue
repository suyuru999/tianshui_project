<template>
  <div id="map-container">
    <div ref="mapEl" id="map"></div>

    <div v-if="baseMapLoading" class="map-loading">
      <span class="loading-dot"></span>
      正在加载底图...
    </div>

    <div class="left-toolbar">
      <button
        v-for="tool in drawingTools"
        :key="tool.id"
        class="tool-btn"
        :class="{ active: activeTool === tool.id }"
        @click="selectTool(tool.id)"
        :title="tool.name"
      >
        <component :is="tool.icon" />
      </button>
    </div>

    <div class="right-dock">
      <div class="zoom-controls">
        <button class="zoom-btn" @click="zoomIn" title="放大"><Plus /></button>
        <button class="zoom-btn" @click="zoomOut" title="缩小"><Minus /></button>
        <button class="zoom-btn" @click="resetView" title="复位"><Aim /></button>
        <button class="zoom-btn" @click="rotateLeft" title="逆时针旋转"><RefreshLeft /></button>
        <button class="zoom-btn" @click="rotateRight" title="顺时针旋转"><RefreshRight /></button>
      </div>

      <div class="map-layer-panel">
        <div class="panel-head">
          <div class="panel-heading">
            <Operation class="panel-head-icon" />
            <span>地图控制</span>
          </div>
          <button class="panel-toggle" @click="rightPanelExpanded = !rightPanelExpanded" title="折叠面板">
            <ArrowDown :class="{ collapsed: !rightPanelExpanded }" />
          </button>
        </div>

        <div v-show="rightPanelExpanded" class="panel-body">
          <div class="control-section">
            <button class="section-title" @click="baseMapExpanded = !baseMapExpanded">
              <span>
                <MapLocation class="section-title-icon" />
                地图类型
              </span>
              <ArrowDown :class="{ collapsed: !baseMapExpanded }" />
            </button>

            <div v-show="baseMapExpanded" class="basemap-grid">
              <label v-for="type in mapTypes" :key="type.id" class="basemap-option">
                <input type="radio" name="baseMap" :value="type.id" v-model="currentMapType" />
                <span>{{ type.name }}</span>
              </label>
            </div>
          </div>

          <div class="control-section">
            <button class="section-title" @click="layerControlExpanded = !layerControlExpanded">
              <span>
                <Files class="section-title-icon" />
                图层控制
              </span>
              <ArrowDown :class="{ collapsed: !layerControlExpanded }" />
            </button>

            <div v-show="layerControlExpanded" class="layer-order-list">
              <div v-if="managedLayers.length === 0" class="layer-empty">暂无可控制图层</div>
              <div
                v-for="(layer, index) in managedLayers"
                :key="layer.id"
                class="managed-layer"
                draggable="true"
                @dragstart="startLayerDrag(index)"
                @dragover.prevent
                @drop="dropLayer(index)"
              >
                <label class="checkbox-label">
                  <input type="checkbox" v-model="layer.visible" @change="setManagedLayerVisible(layer)" />
                  <span>{{ layer.name }}</span>
                </label>
                <div class="layer-actions">
                  <button class="mini-btn" @click="moveLayer(index, -1)" :disabled="index === 0" title="上移">
                    <ArrowUp />
                  </button>
                  <button class="mini-btn" @click="moveLayer(index, 1)" :disabled="index === managedLayers.length - 1" title="下移">
                    <ArrowDown />
                  </button>
                  <button v-if="layer.temporary" class="mini-btn danger" @click="removeManagedLayer(layer)" title="移除">
                    <Close />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <button class="north-arrow" @click="resetRotation" title="指北针/恢复正北">
      <Compass class="north-icon" :style="{ transform: `rotate(${rotation}rad)` }" />
      <small>N</small>
    </button>

    <div class="coordinate-display">
      <div>经度: {{ coordinates.lng }}</div>
      <div>纬度: {{ coordinates.lat }}</div>
      <div>缩放: {{ viewState.zoom }}</div>
      <div>旋转: {{ viewState.rotation }}°</div>
    </div>

    <div class="drawing-hint" v-if="activeTool !== 'select' && activeTool !== 'pan' && activeTool !== 'delete'">
      {{ activeToolLabel }}
    </div>

    <div
      v-if="selectionToolbar.visible"
      class="feature-toolbar"
      :style="{ left: `${selectionToolbar.x}px`, top: `${selectionToolbar.y}px` }"
    >
      <button @click="deleteSelectedFeatures" title="删除选中图形">
        <Delete />
      </button>
    </div>

    <input
      v-if="textEditor.visible"
      ref="textEditorInput"
      class="text-editor"
      v-model="textEditor.value"
      :style="{ left: `${textEditor.x}px`, top: `${textEditor.y}px` }"
      @keydown.enter.prevent="commitTextEditor"
      @keydown.esc.prevent="cancelTextEditor"
      @blur="commitTextEditor"
    />

    <div class="attribution">天地图 / OpenStreetMap / ArcGIS</div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Aim,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  CirclePlus,
  Close,
  Compass,
  Crop,
  Delete,
  EditPen,
  Files,
  FullScreen,
  MapLocation,
  Minus,
  Operation,
  Plus,
  Pointer,
  Position,
  Rank,
  RefreshLeft,
  RefreshRight,
  SemiSelect
} from '@element-plus/icons-vue'
import 'ol/ol.css'
import Map from 'ol/Map'
import View from 'ol/View'
import { defaults as defaultControls, ScaleLine } from 'ol/control'
import { defaults as defaultInteractions, Draw, Modify, Select, Snap } from 'ol/interaction'
import { createBox } from 'ol/interaction/Draw'
import { click } from 'ol/events/condition'
import { fromLonLat, toLonLat } from 'ol/proj'
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import GeoJSON from 'ol/format/GeoJSON'
import KML from 'ol/format/KML'
import { Circle as CircleStyle, Fill, Icon, Stroke, Style, Text } from 'ol/style'
import { Circle as CircleGeom, LineString, Point, Polygon } from 'ol/geom'
import { fromCircle } from 'ol/geom/Polygon'
import { getArea as getGeodesicArea, getLength as getGeodesicLength } from 'ol/sphere'
import Feature from 'ol/Feature'
import shp from 'shpjs'
import { MapUtils } from '../../utils/mapUtils'

const mapEl = ref(null)
const currentMapType = ref('tdt_vec')
const activeTool = ref('select')
const rotation = ref(0)
const baseMapLoading = ref(true)
const coordinates = reactive({ lng: '-', lat: '-' })
const viewState = reactive({ zoom: 8, rotation: 0 })
const managedLayers = reactive([])
const rightPanelExpanded = ref(true)
const baseMapExpanded = ref(true)
const layerControlExpanded = ref(true)
const selectionToolbar = reactive({ visible: false, x: 0, y: 0 })
const textEditor = reactive({ visible: false, x: 0, y: 0, value: '', feature: null })
const textEditorInput = ref(null)

const defaultCenter = [114.3162, 30.5810]
const defaultZoom = 8
const mapTypes = [
  { id: 'tdt_vec', name: '天地图-标准' },
  { id: 'tdt_img', name: '天地图-影像' },
  { id: 'tdt_ter', name: '天地图-地形' },
  { id: 'tdt_gray', name: '天地图-灰色' },
  { id: 'osm', name: 'OSM' },
  { id: 'satellite', name: 'ArcGIS影像' },
  { id: 'terrain', name: 'ArcGIS地形' }
]
const drawingTools = [
  { id: 'select', name: '选择/编辑', icon: Pointer, type: null },
  { id: 'pan', name: '平移', icon: Rank, type: null },
  { id: 'point', name: '点', icon: Position, type: 'Point' },
  { id: 'line', name: '线', icon: SemiSelect, type: 'LineString' },
  { id: 'polygon', name: '多边形', icon: Crop, type: 'Polygon' },
  { id: 'rectangle', name: '矩形', icon: FullScreen, type: 'Circle' },
  { id: 'circle', name: '圆形', icon: CirclePlus, type: 'Circle' },
  { id: 'arrow', name: '箭头', icon: ArrowRight, type: 'LineString' },
  { id: 'text', name: '文字', icon: EditPen, type: 'Point' },
  { id: 'delete', name: '删除图形', icon: Delete, type: null }
]
const activeToolLabel = computed(() => {
  const tool = drawingTools.find(item => item.id === activeTool.value)
  return tool ? `${tool.name}: 在地图上点击或拖拽绘制` : ''
})

let map
let baseLayer
let fallbackBaseLayer
let blankBaseLayer
let baseLayerLoadingTimer
let baseLayerErrorCount = 0
let drawInteraction
let modifyInteraction
let selectInteraction
let snapInteraction
let draggedLayerIndex = null
let resizeObserver
const drawSource = new VectorSource()
const drawLayer = new VectorLayer({
  source: drawSource,
  style: feature => getDrawingStyle(feature, isFeatureSelected(feature))
})
drawLayer.setZIndex(1000)

const demoOverlayDefinitions = [
  { id: 'water', name: '水系分布 (示例)', geometry: new LineString([fromLonLat([113.6, 30.2]), fromLonLat([114.2, 30.55]), fromLonLat([115.0, 30.7])]), styleType: 'water' },
  { id: 'eco', name: '生态保护红线 (示例)', geometry: new Polygon([[fromLonLat([113.95, 30.1]), fromLonLat([114.65, 30.15]), fromLonLat([114.75, 30.75]), fromLonLat([114.05, 30.85]), fromLonLat([113.95, 30.1])]]), styleType: 'eco' },
  { id: 'station', name: '监测点位 (示例)', geometry: new Point(fromLonLat([114.3162, 30.5810])), styleType: 'station' }
]

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  resizeObserver?.disconnect()
  if (map) {
    map.setTarget(undefined)
  }
})

watch(currentMapType, type => {
  if (!map) return
  const nextBaseLayer = MapUtils.createBaseMap(type)
  nextBaseLayer.setZIndex(2)
  map.getLayers().insertAt(1, nextBaseLayer)
  if (baseLayer) {
    map.removeLayer(baseLayer)
  }
  baseLayer = nextBaseLayer
  updateFallbackBaseLayer()
  bindBaseLayerLoading(baseLayer)
})

function initMap() {
  blankBaseLayer = MapUtils.createBaseMap('blank')
  blankBaseLayer.setZIndex(0)
  fallbackBaseLayer = MapUtils.createBaseMap('osm')
  fallbackBaseLayer.setZIndex(1)
  baseLayer = MapUtils.createBaseMap(currentMapType.value)
  baseLayer.setZIndex(2)
  updateFallbackBaseLayer()
  bindBaseLayerLoading(baseLayer)
  map = new Map({
    target: mapEl.value,
    layers: [blankBaseLayer, fallbackBaseLayer, baseLayer, drawLayer],
    view: new View({
      center: fromLonLat(defaultCenter),
      zoom: defaultZoom
    }),
    controls: defaultControls({ zoom: false, rotate: false, attribution: false }).extend([
      new ScaleLine({ units: 'metric', bar: true, text: true, minWidth: 120 })
    ]),
    interactions: defaultInteractions({ altShiftDragRotate: true, pinchRotate: true })
  })
  requestAnimationFrame(() => {
    map.updateSize()
  })
  resizeObserver = new ResizeObserver(() => {
    map?.updateSize()
  })
  resizeObserver.observe(mapEl.value)

  modifyInteraction = new Modify({ source: drawSource })
  selectInteraction = new Select({ condition: click, layers: [drawLayer] })
  snapInteraction = new Snap({ source: drawSource })
  map.addInteraction(modifyInteraction)
  map.addInteraction(selectInteraction)
  map.addInteraction(snapInteraction)
  selectInteraction.on('select', updateSelectionToolbar)
  modifyInteraction.on('modifyend', event => {
    event.features.forEach(feature => refreshMeasurementFeature(feature))
    updateSelectionToolbar()
  })
  window.addEventListener('keydown', handleKeydown)

  demoOverlayDefinitions.forEach(item => addDemoLayer(item))
  syncLayerZIndexes()
  bindMapEvents()
}

function updateFallbackBaseLayer(forceVisible = false) {
  if (!fallbackBaseLayer) return
  fallbackBaseLayer.setVisible(forceVisible || currentMapType.value !== 'osm')
}

function bindMapEvents() {
  map.on('pointermove', event => {
    const [lng, lat] = toLonLat(event.coordinate)
    coordinates.lng = Number.isFinite(lng) ? lng.toFixed(4) : '-'
    coordinates.lat = Number.isFinite(lat) ? lat.toFixed(4) : '-'
  })

  map.on('singleclick', event => {
    if (activeTool.value !== 'text') return
    const feature = new Feature({ geometry: new Point(event.coordinate), drawType: 'text', label: '文字标注' })
    drawSource.addFeature(feature)
    openTextEditor(feature, event.coordinate)
  })

  map.on('click', event => {
    if (activeTool.value !== 'delete') return
    map.forEachFeatureAtPixel(event.pixel, feature => {
      removeFeatureWithMeasurement(feature)
      return true
    })
  })

  map.on('dblclick', event => {
    const feature = map.forEachFeatureAtPixel(event.pixel, item => item)
    if (!feature || feature.get('drawType') !== 'text') return
    event.preventDefault()
    openTextEditor(feature, feature.getGeometry().getCoordinates())
  })

  map.on('moveend', updateSelectionToolbar)

  const view = map.getView()
  view.on('change:resolution', updateViewState)
  view.on('change:rotation', updateViewState)
  updateViewState()
}

function bindBaseLayerLoading(layer) {
  baseMapLoading.value = true
  baseLayerErrorCount = 0
  clearTimeout(baseLayerLoadingTimer)
  baseLayerLoadingTimer = setTimeout(() => {
    baseMapLoading.value = false
  }, 3500)

  const source = layer.getSource?.()
  if (!source?.on) return
  let loadingTiles = 0
  source.on('tileloadstart', () => {
    loadingTiles += 1
    baseMapLoading.value = true
  })
  const finish = () => {
    loadingTiles = Math.max(0, loadingTiles - 1)
    if (loadingTiles === 0) {
      clearTimeout(baseLayerLoadingTimer)
      baseLayerLoadingTimer = setTimeout(() => {
        baseMapLoading.value = false
        if (baseLayerErrorCount === 0) {
          updateFallbackBaseLayer(false)
        }
      }, 180)
    }
  }
  source.on('tileloadend', finish)
  source.on('tileloaderror', () => {
    baseLayerErrorCount += 1
    updateFallbackBaseLayer(true)
    baseMapLoading.value = false
    finish()
    if (currentMapType.value.startsWith('tdt') && baseLayerErrorCount >= 6) {
      ElMessage.warning('天地图底图加载失败，已自动切换到 OSM')
      currentMapType.value = 'osm'
    }
  })
}

function addDemoLayer(definition) {
  const source = new VectorSource({
    features: [new Feature({ geometry: definition.geometry, layerType: definition.styleType })]
  })
  const layer = new VectorLayer({
    source,
    visible: false,
    style: getBusinessStyle(definition.styleType)
  })
  map.addLayer(layer)
  managedLayers.push({
    id: definition.id,
    name: definition.name,
    group: '业务图层',
    visible: false,
    layer
  })
}

function getBusinessStyle(type) {
  const styles = {
    water: new Style({ stroke: new Stroke({ color: '#1677ff', width: 4 }) }),
    eco: new Style({
      stroke: new Stroke({ color: '#1f8f4d', width: 2 }),
      fill: new Fill({ color: 'rgba(64, 169, 91, 0.18)' })
    }),
    station: new Style({
      image: new CircleStyle({
        radius: 7,
        fill: new Fill({ color: '#f5222d' }),
        stroke: new Stroke({ color: '#fff', width: 2 })
      })
    })
  }
  return styles[type] || styles.station
}

function getDrawingStyle(feature, selected = false) {
  const type = feature.get('drawType')
  const label = feature.get('label')
  const measurement = feature.get('measurementLabel')
  const baseStroke = selected ? 3 : 2
  const accentColor = '#5f7f9d'
  const selectedColor = '#315f8c'
  const fillColor = 'rgba(95, 127, 157, 0.14)'

  if (type === 'text') {
    return new Style({
      text: new Text({
        text: label,
        font: selected ? '600 14px sans-serif' : '500 14px sans-serif',
        fill: new Fill({ color: selected ? selectedColor : '#2f465c' }),
        stroke: new Stroke({ color: '#ffffff', width: 4 }),
        offsetY: -12
      })
    })
  }
  if (type === 'arrow') {
    const geometry = feature.getGeometry()
    const styles = [
      new Style({ stroke: new Stroke({ color: selected ? selectedColor : accentColor, width: baseStroke }) })
    ]
    const coordinates = geometry.getCoordinates()
    if (coordinates.length >= 2) {
      const start = coordinates[coordinates.length - 2]
      const end = coordinates[coordinates.length - 1]
      const dx = end[0] - start[0]
      const dy = end[1] - start[1]
      styles.push(new Style({
        geometry: new Point(end),
        image: new Icon({
          src: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 26 26"><path d="M4 13h15M13 7l6 6-6 6" fill="none" stroke="%235f7f9d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>',
          rotation: -Math.atan2(dy, dx),
          rotateWithView: true
        })
      }))
    }
    return styles
  }

  const styles = [
    new Style({
      stroke: new Stroke({ color: accentColor, width: baseStroke }),
      fill: new Fill({ color: fillColor }),
      image: new CircleStyle({
        radius: selected ? 7 : 6,
        fill: new Fill({ color: selected ? selectedColor : accentColor }),
        stroke: new Stroke({ color: '#fff', width: 2 })
      })
    })
  ]

  if (measurement) {
    styles.push(new Style({
      geometry: new Point(feature.get('measurementCoordinate')),
      text: new Text({
        text: measurement,
        font: '600 12px sans-serif',
        padding: [4, 0, 4, 0],
        fill: new Fill({ color: '#315f8c' }),
        stroke: new Stroke({ color: 'rgba(255, 255, 255, 0.95)', width: 4 }),
        offsetY: -10
      })
    }))
  }

  return styles
}

function selectTool(toolId) {
  activeTool.value = toolId
  clearDrawInteraction()
  selectInteraction.setActive(toolId === 'select')
  modifyInteraction.setActive(toolId === 'select')
  if (toolId === 'text' || toolId === 'delete' || toolId === 'select' || toolId === 'pan') return

  const tool = drawingTools.find(item => item.id === toolId)
  if (!tool?.type) return
  drawInteraction = new Draw({
    source: drawSource,
    type: tool.type,
    geometryFunction: toolId === 'rectangle' ? createBox() : undefined
  })
  drawInteraction.on('drawend', event => {
    event.feature.set('drawType', toolId)
    refreshMeasurementFeature(event.feature)
    event.feature.changed()
    drawLayer.changed()
    syncLayerZIndexes()
    requestAnimationFrame(() => {
      activeTool.value = 'select'
      clearDrawInteraction()
      selectInteraction.setActive(true)
      modifyInteraction.setActive(true)
      drawLayer.changed()
    })
  })
  map.addInteraction(drawInteraction)
}

function clearDrawInteraction() {
  if (drawInteraction) {
    map.removeInteraction(drawInteraction)
    drawInteraction = null
  }
}

function isFeatureSelected(feature) {
  return Boolean(selectInteraction?.getFeatures().getArray().includes(feature))
}

function updateSelectionToolbar() {
  if (!map || !selectInteraction) return
  const selected = selectInteraction.getFeatures().getArray()
  drawLayer.changed()
  if (!selected.length) {
    selectionToolbar.visible = false
    return
  }

  const feature = selected[0]
  const coordinate = getFeatureInteriorCoordinate(feature)
  const pixel = map.getPixelFromCoordinate(coordinate)
  selectionToolbar.x = pixel[0] + 12
  selectionToolbar.y = pixel[1] - 42
  selectionToolbar.visible = true
}

function deleteSelectedFeatures() {
  const selected = selectInteraction.getFeatures()
  selected.getArray().slice().forEach(feature => removeFeatureWithMeasurement(feature))
  selected.clear()
  selectionToolbar.visible = false
}

function handleKeydown(event) {
  if (textEditor.visible) return
  if (event.key !== 'Delete' && event.key !== 'Backspace') return
  if (!selectInteraction?.getFeatures().getLength()) return
  event.preventDefault()
  deleteSelectedFeatures()
}

function removeFeatureWithMeasurement(feature) {
  const measurementFeature = feature.get('measurementFeature')
  if (measurementFeature) {
    drawSource.removeFeature(measurementFeature)
  }
  drawSource.removeFeature(feature)
}

function openTextEditor(feature, coordinate) {
  const pixel = map.getPixelFromCoordinate(coordinate)
  textEditor.visible = true
  textEditor.x = pixel[0] + 12
  textEditor.y = pixel[1] - 18
  textEditor.value = feature.get('label') || ''
  textEditor.feature = feature
  nextTick(() => {
    textEditorInput.value?.focus()
    textEditorInput.value?.select()
  })
}

function commitTextEditor() {
  if (!textEditor.visible) return
  const value = textEditor.value.trim()
  if (textEditor.feature) {
    if (value) {
      textEditor.feature.set('label', value)
    } else {
      removeFeatureWithMeasurement(textEditor.feature)
    }
  }
  closeTextEditor()
}

function cancelTextEditor() {
  closeTextEditor()
}

function closeTextEditor() {
  textEditor.visible = false
  textEditor.value = ''
  textEditor.feature = null
}

function refreshMeasurementFeature(feature) {
  if (!feature || feature.get('drawType') === 'text' || feature.get('isMeasurement')) return
  const label = getMeasurementLabel(feature)
  if (!label) return
  const coordinate = getFeatureInteriorCoordinate(feature)
  feature.set('measurementLabel', label)
  feature.set('measurementCoordinate', coordinate)
}

function getFeatureInteriorCoordinate(feature) {
  const geometry = feature.getGeometry()
  if (geometry instanceof Polygon) {
    return geometry.getInteriorPoint().getCoordinates()
  }
  if (geometry instanceof CircleGeom) {
    return geometry.getCenter()
  }
  if (geometry instanceof LineString) {
    return geometry.getCoordinateAt(0.5)
  }
  if (geometry instanceof Point) {
    return geometry.getCoordinates()
  }
  const extent = geometry.getExtent()
  return [(extent[0] + extent[2]) / 2, (extent[1] + extent[3]) / 2]
}

function getMeasurementLabel(feature) {
  const geometry = feature.getGeometry()
  const type = feature.get('drawType')
  if (geometry instanceof Point || type === 'marker' || type === 'point') {
    const [lng, lat] = toLonLat(geometry.getCoordinates())
    return `${lng.toFixed(5)}, ${lat.toFixed(5)}`
  }
  if (geometry instanceof Polygon) {
    return formatArea(getGeodesicArea(geometry, { projection: 'EPSG:3857' }))
  }
  if (geometry instanceof CircleGeom) {
    const polygon = fromCircle(geometry, 96)
    return formatArea(getGeodesicArea(polygon, { projection: 'EPSG:3857' }))
  }
  if (geometry instanceof LineString || type === 'arrow') {
    return formatLength(getGeodesicLength(geometry, { projection: 'EPSG:3857' }))
  }
  return ''
}

function formatArea(area) {
  const absoluteArea = Math.abs(area)
  if (absoluteArea >= 1000000) {
    return `${(absoluteArea / 1000000).toFixed(2)} km²`
  }
  if (absoluteArea >= 666.67) {
    return `${(absoluteArea / 666.6667).toFixed(2)} 亩`
  }
  return `${absoluteArea.toFixed(1)} ㎡`
}

function formatLength(length) {
  if (length >= 1000) {
    return `${(length / 1000).toFixed(2)} km`
  }
  return `${length.toFixed(1)} m`
}

function zoomIn() {
  const view = map.getView()
  view.animate({ zoom: view.getZoom() + 1, duration: 220 })
}

function zoomOut() {
  const view = map.getView()
  view.animate({ zoom: view.getZoom() - 1, duration: 220 })
}

function resetView() {
  map.getView().animate({ center: fromLonLat(defaultCenter), zoom: defaultZoom, rotation: 0, duration: 350 })
}

function rotateLeft() {
  const view = map.getView()
  view.animate({ rotation: view.getRotation() - Math.PI / 12, duration: 220 })
}

function rotateRight() {
  const view = map.getView()
  view.animate({ rotation: view.getRotation() + Math.PI / 12, duration: 220 })
}

function resetRotation() {
  map.getView().animate({ rotation: 0, duration: 220 })
}

function updateViewState() {
  const view = map.getView()
  rotation.value = view.getRotation()
  const zoom = Number(view.getZoom())
  const viewRotation = Number(view.getRotation())
  viewState.zoom = Number.isFinite(zoom) ? zoom.toFixed(1) : '-'
  viewState.rotation = Number.isFinite(viewRotation) ? Math.round((viewRotation * 180) / Math.PI) : 0
}

function locateCoordinate(input) {
  const parts = String(input || '').split(/[,，\s]+/).filter(Boolean).map(Number)
  if (parts.length < 2 || parts.some(Number.isNaN)) {
    ElMessage.warning('请输入有效坐标，例如：114.3162,30.5810')
    return false
  }
  const [lng, lat] = parts
  if (lng < -180 || lng > 180 || lat < -90 || lat > 90) {
    ElMessage.warning('经度范围为 -180 到 180，纬度范围为 -90 到 90')
    return false
  }
  map.getView().animate({ center: fromLonLat([lng, lat]), zoom: 13, duration: 400 })
  const marker = new Feature({ geometry: new Point(fromLonLat([lng, lat])), drawType: 'marker' })
  refreshMeasurementFeature(marker)
  drawSource.addFeature(marker)
  return true
}

async function loadLocalFile(file) {
  if (!file) return false
  const lowerName = file.name.toLowerCase()
  if (lowerName.endsWith('.zip')) {
    try {
      const arrayBuffer = await file.arrayBuffer()
      const geojson = await shp(arrayBuffer)
      const source = new VectorSource()
      const collections = Array.isArray(geojson) ? geojson : [geojson]
      collections.forEach(collection => {
        source.addFeatures(new GeoJSON().readFeatures(collection, {
          dataProjection: 'EPSG:4326',
          featureProjection: 'EPSG:3857'
        }))
      })
      if (source.getFeatures().length === 0) {
        ElMessage.warning('Shapefile ZIP 中未解析到有效要素')
        return false
      }
      const layer = new VectorLayer({
        source,
        visible: true,
        style: getBusinessStyle('eco')
      })
      map.addLayer(layer)
      managedLayers.push({
        id: `temp-${Date.now()}`,
        name: file.name,
        group: '临时图层',
        visible: true,
        temporary: true,
        layer
      })
      syncLayerZIndexes()
      fitLayer(layer)
      return true
    } catch (error) {
      console.error(error)
      ElMessage.error('Shapefile ZIP 加载失败，请确认包含 .shp/.shx/.dbf/.prj 文件')
      return false
    }
  }

  try {
    const text = await file.text()
    const source = new VectorSource()
    if (lowerName.endsWith('.kml')) {
      source.addFeatures(new KML().readFeatures(text, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857'
      }))
    } else if (lowerName.endsWith('.geojson') || lowerName.endsWith('.json')) {
      source.addFeatures(new GeoJSON().readFeatures(JSON.parse(text), {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857'
      }))
    } else {
      ElMessage.warning('暂支持 KML、GeoJSON；Shapefile ZIP 待接入解析服务')
      return false
    }

    const layer = new VectorLayer({
      source,
      visible: true,
      style: getBusinessStyle('eco')
    })
    map.addLayer(layer)
    managedLayers.push({
      id: `temp-${Date.now()}`,
      name: file.name,
      group: '临时图层',
      visible: true,
      temporary: true,
      layer
    })
    syncLayerZIndexes()
    fitLayer(layer)
    return true
  } catch (error) {
    console.error(error)
    ElMessage.error('文件加载失败，请检查文件格式或坐标系')
    return false
  }
}

function fitLayer(layer) {
  const extent = layer.getSource()?.getExtent()
  if (!extent || extent.some(value => !Number.isFinite(value))) return
  map.getView().fit(extent, { padding: [60, 60, 60, 60], duration: 350, maxZoom: 14 })
}

async function exportMap(format = 'png') {
  selectionToolbar.visible = false
  commitTextEditor()
  await nextTick()
  map.once('rendercomplete', () => {
    const mapCanvas = document.createElement('canvas')
    const size = map.getSize()
    mapCanvas.width = size[0]
    mapCanvas.height = size[1]
    const mapContext = mapCanvas.getContext('2d')
    Array.from(document.querySelectorAll('#map .ol-layer canvas, #map canvas')).forEach(canvas => {
      if (canvas.width <= 0) return
      const layerElement = canvas.closest('.ol-layer') || canvas.parentNode
      if (layerElement && getComputedStyle(layerElement).display === 'none') return
      const opacity = layerElement?.style.opacity || canvas.style.opacity
      mapContext.globalAlpha = opacity === '' ? 1 : Number(opacity)
      const transform = canvas.style.transform
      const matrix = transform?.match(/^matrix\(([^(]*)\)$/)?.[1]?.split(',').map(Number)
      if (matrix) {
        CanvasRenderingContext2D.prototype.setTransform.apply(mapContext, matrix)
      } else {
        mapContext.setTransform(1, 0, 0, 1, 0, 0)
      }
      mapContext.drawImage(canvas, 0, 0)
    })
    mapContext.setTransform(1, 0, 0, 1, 0, 0)
    const link = document.createElement('a')
    link.download = `watershed-map.${format}`
    link.href = mapCanvas.toDataURL(`image/${format === 'jpg' ? 'jpeg' : 'png'}`)
    link.click()
  })
  map.renderSync()
}

function setManagedLayerVisible(item) {
  item.layer.setVisible(item.visible)
}

function setLayerVisibleById(layerId, visible) {
  const item = managedLayers.find(layer => layer.id === layerId)
  if (!item) return false
  item.visible = visible
  item.layer.setVisible(visible)
  return true
}

function moveLayer(index, direction) {
  const targetIndex = index + direction
  if (targetIndex < 0 || targetIndex >= managedLayers.length) return
  const [item] = managedLayers.splice(index, 1)
  managedLayers.splice(targetIndex, 0, item)
  syncLayerZIndexes()
}

function startLayerDrag(index) {
  draggedLayerIndex = index
}

function dropLayer(index) {
  if (draggedLayerIndex === null || draggedLayerIndex === index) return
  const [item] = managedLayers.splice(draggedLayerIndex, 1)
  managedLayers.splice(index, 0, item)
  draggedLayerIndex = null
  syncLayerZIndexes()
}

function removeManagedLayer(item) {
  map.removeLayer(item.layer)
  const index = managedLayers.findIndex(layer => layer.id === item.id)
  if (index > -1) managedLayers.splice(index, 1)
}

function syncLayerZIndexes() {
  managedLayers.forEach((item, index) => {
    item.layer.setZIndex(index + 10)
  })
  drawLayer.setZIndex(1000)
}

defineExpose({
  locateCoordinate,
  loadLocalFile,
  exportMap,
  resetView,
  setLayerVisibleById
})
</script>

<style scoped>
#map-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: #e5edf5;
}

#map {
  width: 100%;
  height: 100%;
}

.left-toolbar {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #dbe3ec;
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(30, 50, 70, 0.14);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 1000;
}

.tool-btn,
.mini-btn,
.north-arrow {
  appearance: none;
  border: 1px solid #d9d9d9;
  background: white;
  color: #26384a;
}

.tool-btn {
  width: 38px;
  height: 38px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.tool-btn svg,
.zoom-btn svg,
.mini-btn svg {
  width: 17px;
  height: 17px;
}

.tool-btn:hover,
.tool-btn.active {
  background: #5f7f9d;
  color: white;
  border-color: #5f7f9d;
}

.right-dock {
  position: absolute;
  top: 24px;
  right: 22px;
  z-index: 1002;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  pointer-events: none;
}

.right-dock > * {
  pointer-events: auto;
}

.map-layer-panel {
  width: 304px;
  max-height: calc(100vh - 92px);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #dbe3ec;
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(30, 50, 70, 0.15);
  overflow: hidden;
}

.panel-head {
  height: 48px;
  padding: 0 12px 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eef2f7;
  background: linear-gradient(180deg, #ffffff 0%, #f6f9fc 100%);
}

.panel-heading,
.section-title span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-heading {
  color: #111827;
  font-size: 14px;
  font-weight: 700;
}

.panel-head-icon,
.section-title-icon {
  width: 16px;
  height: 16px;
  color: #4f78a0;
}

.panel-toggle,
.section-title {
  border: none;
  background: transparent;
  color: #4b5563;
}

.panel-toggle {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.panel-toggle:hover,
.section-title:hover {
  background: #eef4f9;
}

.panel-toggle svg,
.section-title > svg {
  width: 15px;
  height: 15px;
  transition: transform 0.2s ease;
}

.panel-toggle svg.collapsed,
.section-title > svg.collapsed {
  transform: rotate(-90deg);
}

.panel-body {
  padding: 12px;
  max-height: calc(100vh - 140px);
  overflow: auto;
}

.control-section + .control-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5edf4;
}

.section-title {
  width: 100%;
  height: 32px;
  border-radius: 6px;
  padding: 0 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 700;
  color: #26384a;
  cursor: pointer;
}

.basemap-grid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.basemap-option {
  min-height: 34px;
  padding: 7px 8px;
  border: 1px solid #dbe3ec;
  border-radius: 7px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #33465a;
  font-size: 12px;
  background: #fff;
  cursor: pointer;
}

.basemap-option:hover {
  border-color: #9bb6cf;
  background: #f7fafc;
}

.basemap-option:has(input:checked) {
  border-color: #5f7f9d;
  background: #eef5fb;
  color: #315f8c;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #33465a;
  font-size: 13px;
  cursor: pointer;
  min-width: 0;
}

.checkbox-label span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.layer-order-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.layer-empty {
  padding: 14px 10px;
  border: 1px dashed #cbd8e4;
  border-radius: 7px;
  color: #789;
  background: #f8fbfd;
  font-size: 12px;
  text-align: center;
}

.managed-layer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 38px;
  padding: 6px 7px;
  border: 1px solid #dbe3ec;
  border-radius: 7px;
  background: #fff;
  cursor: grab;
}

.managed-layer:hover {
  border-color: #b7c8d8;
  background: #f8fbfd;
}

.managed-layer .checkbox-label {
  flex: 1;
}

.layer-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.mini-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  padding: 0;
  font-size: 12px;
}

.mini-btn:disabled {
  color: #bfbfbf;
  cursor: not-allowed;
}

.mini-btn.danger {
  color: #cf1322;
}

.zoom-controls {
  align-self: flex-end;
  display: flex;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #dbe3ec;
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(30, 50, 70, 0.15);
  overflow: hidden;
}

.zoom-btn {
  width: 38px;
  height: 38px;
  border: none;
  border-right: 1px solid #edf2f6;
  border-bottom: none;
  background: white;
  color: #26384a;
  cursor: pointer;
  font-size: 17px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.zoom-btn:last-child {
  border-right: none;
}

.zoom-btn:hover {
  background: #eef4f9;
}

.north-arrow {
  position: absolute;
  top: 18px;
  left: 18px;
  width: 44px;
  height: 50px;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.14);
  z-index: 1002;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.north-icon {
  width: 19px;
  height: 19px;
  color: #d4380d;
  line-height: 1;
}

.north-arrow small {
  font-size: 11px;
  color: #1f2937;
}

.coordinate-display {
  position: absolute;
  bottom: 18px;
  right: 18px;
  background: rgba(255, 255, 255, 0.94);
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 12px;
  color: #1f2937;
  line-height: 1.5;
  z-index: 1000;
}

.drawing-hint {
  position: absolute;
  left: 78px;
  top: 18px;
  background: rgba(38, 56, 74, 0.88);
  color: #fff;
  padding: 7px 12px;
  border-radius: 6px;
  font-size: 12px;
  z-index: 1000;
}

.map-loading {
  position: absolute;
  left: 50%;
  top: 18px;
  transform: translateX(-50%);
  z-index: 1001;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #dbe3ec;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  color: #315f8c;
  font-size: 13px;
  box-shadow: 0 8px 24px rgba(30, 50, 70, 0.12);
  pointer-events: none;
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #1677ff;
  animation: pulse 0.9s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(0.72);
    opacity: 0.55;
  }
  50% {
    transform: scale(1);
    opacity: 1;
  }
}

.feature-toolbar {
  position: absolute;
  z-index: 1004;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border: 1px solid #dbe3ec;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 20px rgba(30, 50, 70, 0.16);
}

.feature-toolbar button {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 5px;
  color: #8c2f39;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.feature-toolbar button:hover {
  background: #f7e8eb;
}

.feature-toolbar svg {
  width: 16px;
  height: 16px;
}

.text-editor {
  position: absolute;
  z-index: 1005;
  width: 150px;
  height: 30px;
  padding: 0 8px;
  border: 1px solid #5f7f9d;
  border-radius: 6px;
  color: #26384a;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 8px 20px rgba(30, 50, 70, 0.16);
  outline: none;
}

.attribution {
  position: absolute;
  bottom: 5px;
  right: 8px;
  font-size: 11px;
  color: #666;
  background: rgba(255, 255, 255, 0.82);
  padding: 2px 6px;
  border-radius: 2px;
  z-index: 1000;
}

:deep(.ol-scale-bar) {
  left: 18px;
  bottom: 18px;
}

@media (max-width: 1100px) {
  .right-dock {
    right: 14px;
    top: 14px;
  }

  .map-layer-panel {
    width: 276px;
  }

  .basemap-grid {
    grid-template-columns: 1fr;
  }
}
</style>
