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
                <input
                  type="radio"
                  name="baseMap"
                  :value="type.id"
                  v-model="currentMapType"
                />
                <span>{{ type.name }}</span>
              </label>

              <label class="basemap-option basemap-action-btn" :class="{ disabled: highResImageryLoading || highResImageryPublishing }">
                <input
                  type="checkbox"
                  name="referenceImageryToggle"
                  :checked="isReferenceImageryActive"
                  :disabled="highResImageryLoading || highResImageryPublishing"
                  @change="togglePreferredHighResImagery"
                />
                <span>{{ highResImageryPublishing ? '影像加载中...' : '遥感影像底图' }}</span>
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
              <div v-if="layerControlItems.length === 0" class="layer-empty">暂无可控制图层</div>
              <div
                v-for="(item, index) in layerControlItems"
                :key="item.layer.id"
                class="managed-layer"
                draggable="true"
                @dragstart="startLayerDrag(index)"
                @dragover.prevent
                @drop="dropLayer(index)"
              >
                <label class="checkbox-label">
                  <input type="checkbox" v-model="item.layer.visible" @change="setManagedLayerVisible(item.layer)" />
                  <span class="managed-layer-text">
                    <strong>{{ item.layer.name }}</strong>
                    <small v-if="item.layer.subtitle">{{ item.layer.subtitle }}</small>
                  </span>
                </label>
                <div class="layer-actions">
                  <button type="button" class="mini-btn" @mousedown.stop @dragstart.stop.prevent @click.stop="moveLayer(index, -1)" :disabled="index === 0" title="上移">
                    <ArrowUp />
                  </button>
                  <button type="button" class="mini-btn" @mousedown.stop @dragstart.stop.prevent @click.stop="moveLayer(index, 1)" :disabled="index === layerControlItems.length - 1" title="下移">
                    <ArrowDown />
                  </button>
                  <button
                    v-if="item.layer.temporary"
                    type="button"
                    draggable="false"
                    class="mini-btn danger"
                    @pointerdown.stop.prevent
                    @mousedown.stop.prevent
                    @dragstart.stop.prevent
                    @click.stop.prevent="removeManagedLayer(item.layer)"
                    title="移除"
                  >
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

    <div class="scale-ratio" aria-label="地图比例尺">
      <div class="scale-ratio-text">1：{{ scaleRatio }}</div>
      <div class="scale-ratio-bar" aria-hidden="true">
        <span class="scale-ratio-tick start"></span>
        <span class="scale-ratio-tick middle"></span>
        <span class="scale-ratio-tick end"></span>
      </div>
    </div>

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
import { defaults as defaultControls } from 'ol/control'
import { defaults as defaultInteractions, Draw, Modify, Select, Snap } from 'ol/interaction'
import { createBox } from 'ol/interaction/Draw'
import { click } from 'ol/events/condition'
import { fromLonLat, toLonLat, transformExtent } from 'ol/proj'
import VectorLayer from 'ol/layer/Vector'
import ImageLayer from 'ol/layer/Image'
import VectorSource from 'ol/source/Vector'
import ImageStatic from 'ol/source/ImageStatic'
import GeoJSON from 'ol/format/GeoJSON'
import KML from 'ol/format/KML'
import { bbox as bboxStrategy } from 'ol/loadingstrategy'
import { Circle as CircleStyle, Fill, Icon, Stroke, Style, Text } from 'ol/style'
import { Circle as CircleGeom, LineString, Point, Polygon } from 'ol/geom'
import { fromCircle } from 'ol/geom/Polygon'
import { getArea as getGeodesicArea, getLength as getGeodesicLength } from 'ol/sphere'
import Feature from 'ol/Feature'
import { MapUtils } from '../../utils/mapUtils'
import {
  fetchPreferredHighResImageryRecord,
  ensurePreferredHighResImageryRecord,
  getHighResImageryQualifiedLayerName,
  PREFERRED_HIGHRES_IMAGERY_FILE
} from '../../utils/highResImagery.js'
import { API_CONFIG } from '../../config/api.js'
import { spatialService } from '../../services/api.js'
import { removeMainMapAnalysisLayer } from '../../utils/mainMapAnalysisLayers.js'
import { prepareFileSave } from '../../utils/fileSave.js'

const REAL_LAYER_DEFINITIONS = [
  {
    id: 'watershed-boundary',
    name: '藉河流域范围',
    url: '/real-layers/watershed_boundary.geojson',
    styleType: 'watershed',
    visible: false
  },
  {
    id: 'watershed-points',
    name: '藉河流域点数据',
    url: '/real-layers/watershed_points.geojson',
    styleType: 'station',
    visible: false
  },
  {
    id: 'townships',
    name: '乡镇行政区划',
    url: '/real-layers/townships.geojson',
    styleType: 'admin',
    visible: false
  }
]

const geoserverProxyUrl = `${API_CONFIG.BASE_URL}/${API_CONFIG.VERSION}/environment/geoserver/ows/`

const mapEl = ref(null)
const currentMapType = ref('tdt_vec')
const activeTool = ref('select')
const rotation = ref(0)
const scaleRatio = ref('-')
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
const highResImageryList = ref([])
const highResImageryLoading = ref(false)
const highResImageryPublishing = ref(false)
const highResImageryError = ref('')
const selectedHighResImageryId = ref('')
const loadedHighResImageryId = ref('')
const defaultCenter = [114.3162, 30.5810]
const defaultZoom = 8
const referenceImageryLayerId = 'system-remote-imagery'
const mapTypes = [
  { id: 'blank', name: '无底图' },
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
const layerControlItems = computed(() => (
  managedLayers
    .map((layer, managedIndex) => ({ layer, managedIndex }))
    .filter(item => !item.layer.referenceImagery)
))
const referenceImageryLayerItem = computed(() => (
  managedLayers.find(item => item.id === referenceImageryLayerId) || null
))
const isReferenceImageryActive = computed(() => Boolean(referenceImageryLayerItem.value?.visible))
const selectedHighResImagery = computed(() => (
  highResImageryList.value.find(item => item.id === selectedHighResImageryId.value) || null
))

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

onMounted(() => {
  initMap()
  fetchHighResImageryList()
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
    controls: defaultControls({ zoom: false, rotate: false, attribution: false }),
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

  loadRealBusinessLayers()
  syncLayerZIndexes()
  bindMapEvents()
}

function mergeHighResImageryRecord(nextRecord) {
  if (!nextRecord?.id) return
  const nextList = [...highResImageryList.value]
  const index = nextList.findIndex(item => item.id === nextRecord.id)
  if (index >= 0) {
    nextList[index] = { ...nextList[index], ...nextRecord }
  } else {
    nextList.push(nextRecord)
  }
  highResImageryList.value = nextList
}

async function fetchHighResImageryList() {
  highResImageryLoading.value = true
  highResImageryError.value = ''
  try {
    const preferredImagery = await fetchPreferredHighResImageryRecord()
    highResImageryList.value = preferredImagery ? [preferredImagery] : []
    if (!selectedHighResImageryId.value && preferredImagery?.id) {
      selectedHighResImageryId.value = preferredImagery.id
    }
  } catch (error) {
    console.error('获取系统遥感影像列表失败:', error)
    highResImageryError.value = '系统遥感影像目录读取失败'
  } finally {
    highResImageryLoading.value = false
  }
}

async function togglePreferredHighResImagery() {
  if (highResImageryLoading.value || highResImageryPublishing.value) {
    return
  }

  if (!selectedHighResImageryId.value) {
    await fetchHighResImageryList()
  }

  if (!selectedHighResImageryId.value) {
    ElMessage.warning('未找到指定的遥感影像底图')
    return
  }

  if (isReferenceImageryActive.value) {
    setReferenceImageryVisible(false)
    return
  }

  if (setReferenceImageryVisible(true)) {
    return
  }

  await loadSelectedHighResImagery({ silentSuccess: true })
}

function buildReferenceImageryLayerRecord(imageryRecord, visible = true) {
  const layerName = getHighResImageryQualifiedLayerName(imageryRecord)
  const layer = imageryRecord.source_kind === 'business_layer'
    ? MapUtils.loadWMS(geoserverProxyUrl, layerName, {
      visible,
      opacity: 1,
      serverType: 'geoserver',
      metadata: imageryRecord.metadata
    })
    : MapUtils.loadStaticWMSImage(geoserverProxyUrl, layerName, {
      visible,
      opacity: 1,
      serverType: 'geoserver',
      metadata: imageryRecord.metadata,
      imageUrl: imageryRecord.preview_image_url || undefined
    })

  return {
    id: referenceImageryLayerId,
    name: imageryRecord.file_name || imageryRecord.name || '遥感影像底图',
    group: '参考影像',
    visible,
    layer,
    serviceLayer: imageryRecord,
    referenceImagery: true
  }
}

function upsertReferenceImageryLayer(imageryRecord, visible = true) {
  const existingIndex = managedLayers.findIndex(item => item.id === referenceImageryLayerId)
  if (existingIndex >= 0) {
    const existing = managedLayers[existingIndex]
    map.removeLayer(existing.layer)
    managedLayers.splice(existingIndex, 1)
  }

  const nextItem = buildReferenceImageryLayerRecord(imageryRecord, visible)
  map.addLayer(nextItem.layer)
  managedLayers.splice(0, 0, nextItem)
  loadedHighResImageryId.value = imageryRecord.id
  syncLayerZIndexes()
  if (visible) {
    fitServiceLayer(nextItem)
  }
}

async function loadSelectedHighResImagery(options = {}) {
  if (!selectedHighResImageryId.value) {
    ElMessage.warning('请先选择一景系统遥感影像')
    return
  }

  highResImageryPublishing.value = true
  try {
    let imageryRecord = selectedHighResImagery.value
    if (!imageryRecord || imageryRecord.file_name === PREFERRED_HIGHRES_IMAGERY_FILE || imageryRecord.source_kind === 'business_layer') {
      imageryRecord = await ensurePreferredHighResImageryRecord()
    } else if (!imageryRecord.geoserver_layer_name || imageryRecord.status !== 'published') {
      const response = await spatialService.publishHighResImagery({
        imagery_id: selectedHighResImageryId.value
      })
      imageryRecord = response?.result || imageryRecord
    }
    mergeHighResImageryRecord(imageryRecord)

    upsertReferenceImageryLayer(imageryRecord, true)
    if (!options.silentSuccess) {
      ElMessage.success('遥感影像底图已加载，可在图层控制中开关对比')
    }
  } catch (error) {
    console.error('加载系统遥感影像失败:', error)
    ElMessage.error('系统遥感影像加载失败')
  } finally {
    highResImageryPublishing.value = false
  }
}

function clearReferenceImagery() {
  const existing = managedLayers.find(item => item.id === referenceImageryLayerId)
  if (!existing) return
  removeManagedLayer(existing)
}

function setReferenceImageryVisible(visible) {
  const existing = referenceImageryLayerItem.value
  if (!existing) return false
  existing.visible = visible
  existing.layer.setVisible(visible)
  if (visible) {
    fitServiceLayer(existing)
  }
  return true
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
  view.on('change:center', updateViewState)
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

async function loadRealBusinessLayers() {
  for (const definition of REAL_LAYER_DEFINITIONS) {
    try {
      const response = await fetch(definition.url)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      let geojson
      if (definition.url.toLowerCase().endsWith('.zip')) {
        const blob = await response.blob()
        geojson = await parseShapefileZipOnServer(new File([blob], `${definition.id}.zip`, { type: 'application/zip' }))
      } else {
        geojson = await response.json()
      }
      const source = createVectorSourceFromGeoJson(geojson)
      if (source.getFeatures().length === 0) {
        throw new Error('未解析到有效要素')
      }

      const layer = new VectorLayer({
        source,
        visible: definition.visible,
        style: getBusinessStyle(definition.styleType)
      })
      map.addLayer(layer)
      managedLayers.push({
        id: definition.id,
        name: definition.name,
        group: '业务图层',
        visible: definition.visible,
        layer
      })
    } catch (error) {
      console.error(`真实图层加载失败: ${definition.name}`, error)
      ElMessage.warning(`${definition.name} 加载失败，请检查真实图层文件`)
    }
  }
  syncLayerZIndexes()
}

async function parseShapefileZipOnServer(file) {
  const response = await spatialService.parseLocalVectorLayer(file)
  const geojson = response?.geojson || response
  if (!geojson || geojson.type !== 'FeatureCollection') {
    throw new Error(response?.error || 'Shapefile ZIP 解析结果无效')
  }
  return geojson
}

function createVectorSourceFromGeoJson(geojson) {
  const source = new VectorSource()
  const collections = Array.isArray(geojson) ? geojson : [geojson]
  collections.forEach(collection => {
    source.addFeatures(new GeoJSON().readFeatures(collection, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857'
    }))
  })
  return source
}

function addVectorLayerFromSource({ id, name, source, styleType = 'eco', visible = true, temporary = false }) {
  const layer = new VectorLayer({
    source,
    visible,
    style: getBusinessStyle(styleType)
  })
  map.addLayer(layer)
  managedLayers.push({
    id,
    name,
    group: temporary ? '临时图层' : '业务图层',
    visible,
    temporary,
    layer
  })
  syncLayerZIndexes()
  return layer
}

function parseWmsEndpoint(wmsUrl) {
  const url = new URL(wmsUrl)
  const layers = url.searchParams.get('layers') || url.searchParams.get('LAYERS')
  return {
    baseUrl: `${url.origin}${url.pathname}`,
    layers
  }
}

function parseWfsEndpoint(wfsUrl) {
  const url = new URL(wfsUrl)
  const typeName = url.searchParams.get('typeName')
    || url.searchParams.get('typename')
    || url.searchParams.get('TYPENAME')
    || url.searchParams.get('TYPENAMES')
  return {
    baseUrl: `${url.origin}${url.pathname}`,
    typeName
  }
}

function addBusinessServiceLayer(serviceLayer, visible = false) {
  if (!serviceLayer?.id) return false
  const serviceLayerId = String(serviceLayer.id)
  const existing = managedLayers.find(item => String(item.id) === serviceLayerId)
  if (existing) {
    existing.visible = visible
    existing.serviceLayer = serviceLayer
    tagBusinessServiceLayer(existing.layer, serviceLayer)
    if (serviceLayer.layer_type === 'vector' && typeof existing.layer.setStyle === 'function') {
      existing.layer.setStyle(getBusinessServiceStyle(serviceLayer))
    }
    existing.layer.setVisible(visible)
    if (visible) fitServiceLayer(existing)
    return true
  }

  let layer = null
  const isExternalService = Boolean(serviceLayer?.metadata?.is_external_service)
  if (serviceLayer.layer_type === 'vector' && serviceLayer.wfs_url && serviceLayer.geoserver_layer_name) {
    const internalTypeName = serviceLayer.geoserver_workspace
      ? `${serviceLayer.geoserver_workspace}:${serviceLayer.geoserver_layer_name}`
      : serviceLayer.geoserver_layer_name
    const { baseUrl, typeName: externalTypeName } = parseWfsEndpoint(serviceLayer.wfs_url)
    const wfsUrl = isExternalService ? baseUrl : geoserverProxyUrl
    const typeName = isExternalService ? (externalTypeName || serviceLayer.geoserver_layer_name) : internalTypeName
    layer = MapUtils.loadWFS(wfsUrl, typeName, {
      visible,
      strategy: bboxStrategy,
      style: getBusinessServiceStyle(serviceLayer),
      dataProjection: 'EPSG:3857',
      featureProjection: 'EPSG:3857'
    })
  } else if (serviceLayer.wms_url) {
    const { baseUrl, layers } = parseWmsEndpoint(serviceLayer.wms_url)
    if (!layers) return false
    layer = MapUtils.loadWMS(isExternalService ? baseUrl : geoserverProxyUrl, layers, {
      visible,
      opacity: serviceLayer.layer_type === 'raster' ? 0.72 : 0.85
    })
  }

  if (!layer) return false
  tagBusinessServiceLayer(layer, serviceLayer)
  map.addLayer(layer)
  managedLayers.push({
    id: serviceLayerId,
    name: serviceLayer.name,
    group: '业务图层',
    visible,
    layer,
    serviceLayer
  })
  syncLayerZIndexes()
  if (visible) {
    fitServiceLayer({ layer, serviceLayer })
  }
  return true
}

function getServiceLayerExtent(serviceLayer) {
  const bounds = serviceLayer?.metadata?.bounds
  if (!Array.isArray(bounds) || bounds.length !== 4) return null
  const extent = bounds.map(Number)
  if (extent.some(value => !Number.isFinite(value))) return null
  const crs = serviceLayer.metadata?.crs || 'EPSG:4326'
  try {
    return crs === 'EPSG:3857' ? extent : transformExtent(extent, crs, 'EPSG:3857')
  } catch (error) {
    console.warn('图层范围坐标转换失败，按经纬度处理:', error)
    return transformExtent(extent, 'EPSG:4326', 'EPSG:3857')
  }
}

function fitServiceLayer(item) {
  const extent = getServiceLayerExtent(item.serviceLayer)
  if (extent) {
    map.getView().fit(extent, { padding: [70, 70, 70, 70], duration: 350, maxZoom: 14 })
    return
  }
  fitLayer(item.layer)
}

function resolveOverlayExtent(compareOverlay) {
  const bounds3857 = compareOverlay?.bounds_3857
  if (Array.isArray(bounds3857) && bounds3857.length === 4) {
    const extent = bounds3857.map(Number)
    if (extent.every(value => Number.isFinite(value))) return extent
  }

  const rawBounds = compareOverlay?.bounds
  const rawCrs = compareOverlay?.crs || 'EPSG:4326'
  if (!Array.isArray(rawBounds) || rawBounds.length !== 4) return null

  const extent = rawBounds.map(Number)
  if (extent.some(value => !Number.isFinite(value))) return null

  try {
    return rawCrs === 'EPSG:3857' ? extent : transformExtent(extent, rawCrs, 'EPSG:3857')
  } catch (error) {
    console.warn('分析结果图层范围转换失败，按 EPSG:4326 处理:', error)
    return transformExtent(extent, 'EPSG:4326', 'EPSG:3857')
  }
}

function addResultOverlayLayer(compareOverlay, options = {}) {
  if (!map || !compareOverlay?.overlay_image_url) {
    ElMessage.warning('当前结果缺少可叠加的 PNG 图层')
    return false
  }

  const extent = resolveOverlayExtent(compareOverlay)
  if (!extent) {
    ElMessage.warning('当前结果缺少空间范围，无法叠加到主地图')
    return false
  }

  const id = String(options.id || `result-overlay-${Date.now()}`)
  removeAnalysisLayerFromMap({ id, overlayUrl: compareOverlay.overlay_image_url, removePersisted: false })

  const layer = new ImageLayer({
    source: new ImageStatic({
      url: compareOverlay.overlay_image_url,
      imageExtent: extent,
      projection: 'EPSG:3857'
    }),
    visible: true,
    opacity: Number(options.opacity || 0.68)
  })
  layer.set('analysisResultLayer', true)
  layer.set('analysisResultLayerId', id)
  layer.set('analysisOverlayUrl', compareOverlay.overlay_image_url)
  layer.analysisResultLayer = true
  layer.analysisResultLayerId = id
  layer.analysisOverlayUrl = compareOverlay.overlay_image_url

  map.addLayer(layer)
  managedLayers.push({
    id,
    name: options.name || '分析结果图层',
    subtitle: options.subtitle || compareOverlay.source_filename || '',
    group: '临时图层',
    visible: true,
    temporary: true,
    analysisResultLayer: true,
    layer,
    compareOverlay
  })
  syncLayerZIndexes()
  map.getView().fit(extent, { padding: [70, 70, 70, 70], duration: 350, maxZoom: 14 })
  return true
}

function tagBusinessServiceLayer(layer, serviceLayer) {
  if (!layer || !serviceLayer?.id) return
  layer.set('businessServiceLayer', true)
  layer.set('businessServiceLayerId', String(serviceLayer.id))
  layer.set('businessServiceLayerName', serviceLayer.geoserver_layer_name || '')
}

function getOpenLayersLayerId(layer) {
  return String(layer?.analysisResultLayerId || layer?.get?.('analysisResultLayerId') || layer?.id || '')
}

function getOpenLayersLayerOverlayUrl(layer) {
  const taggedUrl = layer?.analysisOverlayUrl || layer?.get?.('analysisOverlayUrl')
  if (taggedUrl) return taggedUrl
  return layer?.getSource?.()?.getUrl?.() || ''
}

function isOpenLayersAnalysisLayer(layer) {
  return Boolean(layer?.analysisResultLayer || layer?.get?.('analysisResultLayer'))
}

function removeAnalysisLayerFromMap({ id = '', overlayUrl = '', removePersisted = true } = {}) {
  const layerId = String(id || '')
  const imageUrl = String(overlayUrl || '')

  const matchesManagedAnalysisLayer = (managedLayer) => {
    if (!managedLayer?.analysisResultLayer) return false
    const managedLayerId = String(managedLayer.id || getOpenLayersLayerId(managedLayer.layer) || '')
    const managedLayerUrl = managedLayer.compareOverlay?.overlay_image_url || getOpenLayersLayerOverlayUrl(managedLayer.layer)
    return (
      (layerId && managedLayerId === layerId)
      || (imageUrl && managedLayerUrl === imageUrl)
      || (!layerId && !imageUrl)
    )
  }
  const matchedManagedLayers = managedLayers.filter(matchesManagedAnalysisLayer)
  const matchedLayerObjects = new Set(matchedManagedLayers.map(item => item.layer).filter(Boolean))

  const matchesMapLayer = (layer) => {
    const mapLayerId = getOpenLayersLayerId(layer)
    const mapLayerUrl = getOpenLayersLayerOverlayUrl(layer)
    return (
      matchedLayerObjects.has(layer)
      || (layerId && mapLayerId === layerId)
      || (imageUrl && mapLayerUrl === imageUrl)
      || (!layerId && !imageUrl && isOpenLayersAnalysisLayer(layer))
    )
  }

  if (map) {
    map.getLayers().getArray().slice().forEach((layer) => {
      if (matchesMapLayer(layer)) {
        map.removeLayer(layer)
      }
    })
    map.renderSync()
  }

  const remainingItems = managedLayers.filter((managedLayer) => !matchesManagedAnalysisLayer(managedLayer))
  managedLayers.splice(0, managedLayers.length, ...remainingItems)

  if (removePersisted && (layerId || imageUrl)) {
    removeMainMapAnalysisLayer(layerId, { overlayImageUrl: imageUrl })
  }
}

function getBusinessStyle(type) {
  const styles = {
    water: new Style({ stroke: new Stroke({ color: '#1677ff', width: 4 }) }),
    watershed: new Style({
      stroke: new Stroke({ color: '#0f766e', width: 3 }),
      fill: new Fill({ color: 'rgba(15, 118, 110, 0.12)' })
    }),
    admin: new Style({
      stroke: new Stroke({ color: '#8b5cf6', width: 1.4 }),
      fill: new Fill({ color: 'rgba(139, 92, 246, 0.06)' })
    }),
    eco: new Style({
      stroke: new Stroke({ color: '#1f8f4d', width: 2 }),
      fill: new Fill({ color: 'rgba(64, 169, 91, 0.18)' }),
      image: new CircleStyle({
        radius: 7,
        fill: new Fill({ color: '#22c55e' }),
        stroke: new Stroke({ color: '#ffffff', width: 2 })
      })
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

function colorWithOpacity(color, opacity) {
  const match = String(color || '').match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i)
  if (!match) return color || 'rgba(64, 169, 91, 0.18)'
  const alpha = Math.min(1, Math.max(0, Number(opacity)))
  return `rgba(${parseInt(match[1], 16)}, ${parseInt(match[2], 16)}, ${parseInt(match[3], 16)}, ${alpha})`
}

function getBusinessServiceStyle(serviceLayer) {
  const config = serviceLayer?.style_config || {}
  const fillColor = config.fill_color || '#1f8f4d'
  const strokeColor = config.stroke_color || '#1f8f4d'
  const parsedStrokeWidth = Number(config.stroke_width ?? 2)
  const strokeWidth = Number.isFinite(parsedStrokeWidth) ? parsedStrokeWidth : 2
  const parsedFillOpacity = Number(config.fill_opacity ?? 0.18)
  const fillOpacity = Number.isFinite(parsedFillOpacity) ? parsedFillOpacity : 0.18

  return new Style({
    stroke: new Stroke({ color: strokeColor, width: strokeWidth }),
    fill: new Fill({ color: colorWithOpacity(fillColor, fillOpacity) }),
    image: new CircleStyle({
      radius: 7,
      fill: new Fill({ color: fillColor }),
      stroke: new Stroke({ color: strokeColor, width: strokeWidth })
    })
  })
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
  const target = event.target
  if (
    target instanceof HTMLInputElement
    || target instanceof HTMLTextAreaElement
    || target instanceof HTMLSelectElement
    || target?.isContentEditable
  ) return
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
  scaleRatio.value = formatScaleRatio(view)
  viewState.zoom = Number.isFinite(zoom) ? zoom.toFixed(1) : '-'
  viewState.rotation = Number.isFinite(viewRotation) ? Math.round((viewRotation * 180) / Math.PI) : 0
}

function formatScaleRatio(view) {
  const resolution = Number(view.getResolution())
  if (!Number.isFinite(resolution) || resolution <= 0) return '-'
  const center = view.getCenter()
  const [, lat = 0] = center ? toLonLat(center) : []
  const latitudeFactor = Math.cos((Number(lat) || 0) * Math.PI / 180)
  const metersPerPixel = resolution * Math.max(latitudeFactor, 0.01)
  const denominator = metersPerPixel * 96 / 0.0254
  if (!Number.isFinite(denominator) || denominator <= 0) return '-'
  let rounded
  if (denominator >= 10000000) {
    rounded = Math.round(denominator / 1000000) * 1000000
  } else if (denominator >= 1000000) {
    rounded = Math.round(denominator / 100000) * 100000
  } else if (denominator >= 100000) {
    rounded = Math.round(denominator / 10000) * 10000
  } else if (denominator >= 10000) {
    rounded = Math.round(denominator / 1000) * 1000
  } else if (denominator >= 1000) {
    rounded = Math.round(denominator / 100) * 100
  } else {
    rounded = Math.round(denominator)
  }
  return rounded.toLocaleString('zh-CN')
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
      const geojson = await parseShapefileZipOnServer(file)
      const source = createVectorSourceFromGeoJson(geojson)
      if (source.getFeatures().length === 0) {
        ElMessage.warning('Shapefile ZIP 中未解析到有效要素')
        return false
      }
      const layer = addVectorLayerFromSource({
        id: `temp-${Date.now()}`,
        name: file.name,
        source,
        styleType: 'eco',
        temporary: true
      })
      fitLayer(layer)
      return true
    } catch (error) {
      console.error(error)
      const message = error?.response?.data?.error || error?.response?.data?.details || error?.message
      ElMessage.error(message || 'Shapefile ZIP 加载失败，请确认包含 .shp/.shx/.dbf/.prj 文件')
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

    const layer = addVectorLayerFromSource({
      id: `temp-${Date.now()}`,
      name: file.name,
      source,
      styleType: 'eco',
      temporary: true
    })
    fitLayer(layer)
    return true
  } catch (error) {
    console.error(error)
    ElMessage.error('文件加载失败，请检查文件格式或坐标系')
    return false
  }
}

function fitLayer(layer) {
  const source = layer.getSource?.()
  const extent = source?.getExtent?.() || source?.getImageExtent?.()
  if (!extent || extent.some(value => !Number.isFinite(value))) return
  map.getView().fit(extent, { padding: [60, 60, 60, 60], duration: 350, maxZoom: 14 })
}

async function exportMap(format = 'png') {
  selectionToolbar.visible = false
  commitTextEditor()
  await nextTick()
  const normalizedFormat = format === 'jpg' || format === 'jpeg' ? 'jpg' : 'png'
  const mimeType = normalizedFormat === 'jpg' ? 'image/jpeg' : 'image/png'
  const timestamp = new Date()
    .toISOString()
    .replace(/[-:]/g, '')
    .replace(/\..+$/, '')
    .replace('T', '_')
  let saveTarget
  try {
    saveTarget = await prepareFileSave(`藉河流域地图_${timestamp}.${normalizedFormat}`, mimeType)
  } catch (error) {
    if (error?.name === 'AbortError') return
    console.error('准备导出地图失败:', error)
    ElMessage.error('导出地图失败，请稍后重试')
    return
  }

  map.once('rendercomplete', async () => {
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
    try {
      const blob = await new Promise((resolve, reject) => {
        mapCanvas.toBlob((result) => {
          if (!result) {
            reject(new Error('地图图片生成失败'))
            return
          }
          resolve(result)
        }, mimeType)
      })
      await saveTarget.write(blob)
      ElMessage.success('地图图片已导出')
    } catch (error) {
      if (error?.name === 'AbortError') return
      console.error('导出地图失败:', error)
      ElMessage.error('导出地图失败，请稍后重试')
    }
  })
  map.renderSync()
}

function setManagedLayerVisible(item) {
  item.layer.setVisible(item.visible)
  if (item.visible) {
    fitServiceLayer(item)
  }
}

function setLayerVisibleById(layerId, visible) {
  const normalizedLayerId = String(layerId)
  const item = managedLayers.find(layer => String(layer.id) === normalizedLayerId)
  if (!item) return false
  item.visible = visible
  item.layer.setVisible(visible)
  if (visible) {
    fitLayer(item.layer)
  }
  return true
}

function moveLayer(index, direction) {
  const visibleItems = layerControlItems.value
  const targetIndex = index + direction
  if (targetIndex < 0 || targetIndex >= visibleItems.length) return
  const fromManagedIndex = visibleItems[index]?.managedIndex
  const toManagedIndex = visibleItems[targetIndex]?.managedIndex
  if (fromManagedIndex === undefined || toManagedIndex === undefined) return
  const [item] = managedLayers.splice(fromManagedIndex, 1)
  managedLayers.splice(toManagedIndex, 0, item)
  syncLayerZIndexes()
}

function startLayerDrag(index) {
  draggedLayerIndex = index
}

function dropLayer(index) {
  if (draggedLayerIndex === null || draggedLayerIndex === index) return
  const visibleItems = layerControlItems.value
  const fromManagedIndex = visibleItems[draggedLayerIndex]?.managedIndex
  const toManagedIndex = visibleItems[index]?.managedIndex
  if (fromManagedIndex === undefined || toManagedIndex === undefined) {
    draggedLayerIndex = null
    return
  }
  const [item] = managedLayers.splice(fromManagedIndex, 1)
  managedLayers.splice(toManagedIndex, 0, item)
  draggedLayerIndex = null
  syncLayerZIndexes()
}

function removeManagedLayer(item, options = {}) {
  const candidateLayer = item?.layer || item
  const candidateId = String(
    item?.id
    || item?.layer?.id
    || candidateLayer?.analysisResultLayerId
    || candidateLayer?.get?.('analysisResultLayerId')
    || ''
  )
  const candidateOverlayUrl = candidateLayer?.analysisOverlayUrl || candidateLayer?.get?.('analysisOverlayUrl') || item?.compareOverlay?.overlay_image_url || ''

  if (item?.analysisResultLayer || candidateLayer?.analysisResultLayer || candidateLayer?.get?.('analysisResultLayer')) {
    removeAnalysisLayerFromMap({
      id: candidateId || item?.id || '',
      overlayUrl: candidateOverlayUrl,
      removePersisted: options.removePersisted !== false
    })
    return
  }

  const matchesManagedItem = (managedLayer) => {
    if (!managedLayer) return false
    const layerObject = managedLayer.layer
    const layerId = String(managedLayer.id || layerObject?.analysisResultLayerId || layerObject?.get?.('analysisResultLayerId') || layerObject?.id || '')
    const overlayUrl = layerObject?.analysisOverlayUrl || layerObject?.get?.('analysisOverlayUrl') || managedLayer.compareOverlay?.overlay_image_url || ''
    return (
      managedLayer === item
      || layerObject === item
      || layerObject === candidateLayer
      || (candidateId && layerId === candidateId)
      || (candidateOverlayUrl && overlayUrl === candidateOverlayUrl)
    )
  }

  const matchedItems = managedLayers.filter(matchesManagedItem)
  matchedItems.forEach((managedItem) => {
    if (map && managedItem.layer) {
      map.removeLayer(managedItem.layer)
    }
  })
  if (map) {
    map.renderSync()
  }

  const remainingItems = managedLayers.filter(layerItem => !matchesManagedItem(layerItem))
  managedLayers.splice(0, managedLayers.length, ...remainingItems)

  const persistedId = matchedItems.find(Boolean)?.id || candidateId
  if (persistedId && options.removePersisted !== false) {
    removeMainMapAnalysisLayer(persistedId)
  }

  const hasReferenceImagery = matchedItems.some(layerItem => layerItem.referenceImagery)
  if (hasReferenceImagery) {
    loadedHighResImageryId.value = ''
  }
}

function removeAnalysisResultLayers(options = {}) {
  if (options.removePersisted === false) {
    removeAnalysisLayerFromMap({ removePersisted: false })
    return
  }
  const layers = managedLayers.filter(item => item.analysisResultLayer)
  layers.forEach(item => removeManagedLayer(item, options))
}

function removeLayerById(layerId) {
  const normalizedLayerId = String(layerId)
  const item = managedLayers.find(layer => String(layer.id) === normalizedLayerId)
  if (!item) {
    removeAnalysisLayerFromMap({ id: normalizedLayerId })
    return false
  }
  removeManagedLayer(item)
  return true
}

function removeBusinessServiceLayer(serviceLayer) {
  const serviceLayerId = String(serviceLayer?.id || serviceLayer || '')
  const geoserverLayerName = String(serviceLayer?.geoserver_layer_name || '')
  const qualifiedLayerName = serviceLayer?.geoserver_workspace && geoserverLayerName
    ? `${serviceLayer.geoserver_workspace}:${geoserverLayerName}`
    : geoserverLayerName

  const matchesMapLayer = (layer) => {
    if (!layer || layer === drawLayer) return false
    if (serviceLayerId && String(layer.get?.('businessServiceLayerId') || '') === serviceLayerId) return true
    if (geoserverLayerName && String(layer.get?.('businessServiceLayerName') || '') === geoserverLayerName) return true

    const source = layer.getSource?.()
    const sourceLayers = String(source?.getParams?.()?.LAYERS || '')
    if (qualifiedLayerName && sourceLayers.split(',').includes(qualifiedLayerName)) return true

    if (!geoserverLayerName || typeof source?.getFeatures !== 'function') return false
    return source.getFeatures().some((feature) => {
      const featureId = String(feature.getId?.() || '')
      return featureId === geoserverLayerName || featureId.startsWith(`${geoserverLayerName}.`)
    })
  }

  const managedMatches = (item) => (
    (serviceLayerId && String(item?.id || '') === serviceLayerId)
    || (geoserverLayerName && String(item?.serviceLayer?.geoserver_layer_name || '') === geoserverLayerName)
    || matchesMapLayer(item?.layer)
  )

  const layersToRemove = new Set(managedLayers.filter(managedMatches).map(item => item.layer).filter(Boolean))
  map?.getLayers().getArray().slice().forEach((layer) => {
    if (matchesMapLayer(layer)) layersToRemove.add(layer)
  })
  layersToRemove.forEach(layer => map?.removeLayer(layer))

  const remainingItems = managedLayers.filter(item => !managedMatches(item))
  managedLayers.splice(0, managedLayers.length, ...remainingItems)
  map?.renderSync()
  return layersToRemove.size > 0
}

function pruneBusinessServiceLayers(serviceLayers = []) {
  const validIds = new Set(serviceLayers.map(layer => String(layer?.id || '')).filter(Boolean))
  const validNames = new Set(serviceLayers.map(layer => String(layer?.geoserver_layer_name || '')).filter(Boolean))

  const getGeneratedLayerName = (layer) => {
    const taggedName = String(layer?.get?.('businessServiceLayerName') || '')
    if (taggedName) return taggedName

    const source = layer?.getSource?.()
    const sourceLayers = String(source?.getParams?.()?.LAYERS || '').split(',').filter(Boolean)
    const wmsLayerName = sourceLayers[0]?.split(':').pop() || ''
    if (/_[0-9a-f]{8}$/i.test(wmsLayerName)) return wmsLayerName

    if (typeof source?.getFeatures !== 'function') return ''
    const featureId = String(source.getFeatures().find(feature => feature.getId?.())?.getId?.() || '')
    const featureLayerName = featureId.includes('.') ? featureId.slice(0, featureId.lastIndexOf('.')) : ''
    return /_[0-9a-f]{8}$/i.test(featureLayerName) ? featureLayerName : ''
  }

  const isOrphaned = (layer) => {
    if (!layer || layer === drawLayer) return false
    const taggedId = String(layer.get?.('businessServiceLayerId') || '')
    if (taggedId) return !validIds.has(taggedId)
    const generatedLayerName = getGeneratedLayerName(layer)
    return Boolean(generatedLayerName && !validNames.has(generatedLayerName))
  }

  const layersToRemove = new Set()
  managedLayers.forEach((item) => {
    const itemId = String(item?.id || '')
    if (item?.serviceLayer && itemId && !validIds.has(itemId)) layersToRemove.add(item.layer)
    if (isOrphaned(item?.layer)) layersToRemove.add(item.layer)
  })
  map?.getLayers().getArray().slice().forEach((layer) => {
    if (isOrphaned(layer)) layersToRemove.add(layer)
  })
  layersToRemove.forEach(layer => map?.removeLayer(layer))

  const remainingItems = managedLayers.filter(item => !layersToRemove.has(item.layer))
  managedLayers.splice(0, managedLayers.length, ...remainingItems)
  map?.renderSync()
  return layersToRemove.size
}

function refreshAnalysisResultLayersFromStore() {
  removeAnalysisResultLayers({ removePersisted: false })
  window.dispatchEvent(new CustomEvent('tianshui-main-map-analysis-layers-updated'))
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
  addResultOverlayLayer,
  addBusinessServiceLayer,
  exportMap,
  resetView,
  removeAnalysisResultLayers,
  removeBusinessServiceLayer,
  removeLayerById,
  pruneBusinessServiceLayers,
  refreshAnalysisResultLayersFromStore,
  setLayerVisibleById
})
</script>

<style scoped>
#map-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: #ffffff;
}

#map-container,
#map-container * {
  box-sizing: border-box;
}

#map {
  width: 100%;
  height: 100%;
}

.left-toolbar {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 46px;
  background: #102d4d;
  border: 1px solid #285276;
  border-radius: 8px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.22);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  z-index: 1000;
}

.tool-btn,
.mini-btn,
.north-arrow {
  appearance: none;
  border: 1px solid transparent;
  background: transparent;
  color: #dcebfa;
}

.tool-btn {
  width: 34px;
  height: 34px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.tool-btn svg,
.zoom-btn svg,
.mini-btn svg {
  width: 17px;
  height: 17px;
}

.tool-btn:hover,
.tool-btn.active {
  background: #1677ff;
  color: white;
  border-color: #1677ff;
  transform: none;
}

.right-dock {
  position: absolute;
  top: 14px;
  right: 14px;
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
  width: 312px;
  max-height: min(640px, calc(100vh - 76px));
  background: #102d4d;
  border: 1px solid #285276;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}

.panel-head {
  min-height: 46px;
  padding: 8px 10px 8px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid rgba(153, 177, 202, 0.14);
  background: #102d4d;
}

.panel-heading,
.section-title span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-heading {
  min-width: 0;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.35;
  word-break: break-word;
}

.panel-head-icon,
.section-title-icon {
  width: 15px;
  height: 15px;
  color: #26b6e8;
}

.panel-toggle {
  border: 1px solid #24527d;
  background: #0d2745;
  color: #ffffff;
}

.panel-toggle {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  flex-shrink: 0;
}

.panel-toggle:hover {
  background: #183b61;
}

.section-title {
  border: none;
  background: transparent;
  color: #c4d4eb;
}

.section-title:hover {
  background: #183b61;
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
  max-height: min(584px, calc(100vh - 124px));
  overflow: auto;
}

.control-section + .control-section {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #1c4265;
}

.section-title {
  width: 100%;
  min-height: 32px;
  border-radius: 6px;
  padding: 6px 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  font-weight: 700;
  color: #c4d4eb;
  cursor: pointer;
}

.basemap-grid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.basemap-option {
  position: relative;
  min-height: 32px;
  padding: 7px 8px;
  border: 1px solid #1d4264;
  border-radius: 7px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #c4d4eb;
  font-size: 12px;
  line-height: 1.35;
  background: #0b2340;
  cursor: pointer;
  min-width: 0;
}

.basemap-option span {
  min-width: 0;
  word-break: break-word;
}

.basemap-option input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.basemap-option:hover {
  border-color: #285a82;
  background: #183b61;
}

.basemap-option:has(input:checked) {
  border-color: #1677ff;
  background: #1677ff;
  color: #ffffff;
}

.basemap-action-btn {
  justify-content: flex-start;
  text-align: left;
}

.basemap-action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.basemap-action-btn.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  color: #c4d4eb;
  font-size: 12px;
  cursor: pointer;
  min-width: 0;
}

.checkbox-label input {
  margin-top: 2px;
  flex-shrink: 0;
}

.managed-layer-text {
  min-width: 0;
}

.managed-layer-text strong,
.managed-layer-text small {
  display: block;
  overflow: visible;
  text-overflow: clip;
  white-space: normal;
  word-break: break-word;
}

.managed-layer-text strong {
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
}

.managed-layer-text small {
  margin-top: 2px;
  color: #8299bc;
  font-size: 11px;
  font-weight: 500;
}

.layer-order-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.layer-empty {
  padding: 12px 10px;
  border: 1px dashed #1d4264;
  border-radius: 7px;
  color: #8299bc;
  background: #0b2340;
  font-size: 12px;
  text-align: center;
}

.managed-layer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  min-height: 36px;
  padding: 8px;
  border: 1px solid #1d4264;
  border-radius: 7px;
  background: #0b2340;
  cursor: grab;
}

.managed-layer:hover {
  border-color: #285a82;
  background: #183b61;
}

.managed-layer .checkbox-label {
  flex: 1;
}

.layer-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  padding-top: 1px;
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
  background: #102d4d;
  border: 1px solid #285276;
  border-radius: 8px;
  box-shadow: 0 14px 28px rgba(30, 50, 70, 0.14);
  overflow: hidden;
}

.zoom-btn {
  width: 34px;
  height: 34px;
  border: none;
  border-right: 1px solid #edf2f6;
  border-bottom: none;
  background: #102d4d;
  color: #ffffff;
  cursor: pointer;
  font-size: 16px;
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
  background: #183b61;
}

.north-arrow {
  position: absolute;
  top: 16px;
  left: 16px;
  width: 42px;
  height: 50px;
  border: 1px solid #285276;
  border-radius: 8px;
  background: #102d4d;
  color: #dcebfa;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
  z-index: 1002;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 0;
  cursor: pointer;
}

.north-arrow:hover {
  background: #183b61;
  border-color: #285a82;
}

.north-icon {
  width: 21px;
  height: 21px;
  color: #26b6e8;
  line-height: 1;
}

.north-arrow small {
  font-size: 11px;
  line-height: 1;
  color: #ffffff;
}

.coordinate-display {
  position: absolute;
  bottom: 42px;
  right: 16px;
  background: rgba(255, 255, 255, 0.94);
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 12px;
  color: #1f2937;
  line-height: 1.5;
  z-index: 1000;
  box-shadow: 0 8px 18px rgba(30, 50, 70, 0.10);
}

.drawing-hint {
  position: absolute;
  left: 70px;
  top: 16px;
  background: rgba(13, 27, 42, 0.88);
  color: #fff;
  padding: 7px 12px;
  border-radius: 6px;
  font-size: 12px;
  z-index: 1000;
}

.map-loading {
  position: absolute;
  left: 50%;
  top: 16px;
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
  background: #2f97b9;
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
  bottom: 6px;
  right: 16px;
  font-size: 11px;
  color: #666;
  background: rgba(255, 255, 255, 0.82);
  padding: 2px 6px;
  border-radius: 2px;
  z-index: 1000;
}

.scale-ratio {
  position: absolute;
  left: 18px;
  bottom: 18px;
  width: 142px;
  min-height: 44px;
  padding: 7px 11px 9px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 7px;
  border: 1px solid #285276;
  border-radius: 6px;
  background: #102d4d;
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.24);
  z-index: 1000;
  pointer-events: none;
}

.scale-ratio-text {
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  text-align: center;
  letter-spacing: 0;
}

.scale-ratio-bar {
  position: relative;
  height: 10px;
  border-bottom: 2px solid #dcebfa;
}

.scale-ratio-tick {
  position: absolute;
  bottom: -2px;
  width: 2px;
  height: 10px;
  background: #dcebfa;
}

.scale-ratio-tick.start {
  left: 0;
}

.scale-ratio-tick.middle {
  left: 50%;
  transform: translateX(-50%);
  height: 7px;
}

.scale-ratio-tick.end {
  right: 0;
}

@media (max-width: 1100px) {
  .right-dock {
    right: 14px;
    top: 14px;
  }

  .map-layer-panel {
    width: 292px;
  }

  .basemap-grid {
    grid-template-columns: 1fr;
  }
}

/* 深蓝 GIS 控件色，地图数据本身保持真实颜色。 */
#map-container {
  background: #ffffff;
  border-radius: 8px;
  overflow: hidden;
}

.left-toolbar {
  background: #102d4d;
  border-color: #285276;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24);
}

.tool-btn,
.mini-btn,
.north-arrow,
.zoom-btn {
  background: transparent;
  border-color: transparent;
  color: #dcebfa;
}

.north-arrow {
  background: #102d4d;
  border: 1px solid #285276;
  color: #dcebfa;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
}

.north-arrow:hover {
  background: #183b61;
  border-color: #285a82;
  color: #ffffff;
}

.tool-btn:hover,
.tool-btn.active,
.zoom-btn:hover,
.mini-btn:hover {
  background: #183b61;
  border-color: #1677ff;
  color: #ffffff;
  transform: none;
}

.right-dock .zoom-controls,
.map-layer-panel,
.coordinate-display,
.map-loading,
.feature-toolbar {
  background: #102d4d;
  border-color: #285276;
  color: #c4d4eb;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}

.panel-head {
  min-height: 46px;
  background: #102d4d;
  border-bottom-color: #1c4265;
}

.panel-heading {
  color: #ffffff;
}

.panel-head-icon,
.section-title-icon,
.north-icon {
  color: #26b6e8;
}

.panel-toggle {
  background: #0d2745;
  border-color: #24527d;
  color: #ffffff;
}

.panel-toggle:hover,
.section-title:hover {
  background: #183b61;
  color: #ffffff;
}

.panel-body,
.section-title {
  color: #c4d4eb;
}

.control-section + .control-section {
  border-top-color: #1c4265;
}

.basemap-option,
.managed-layer,
.layer-empty {
  background: #0b2340;
  border-color: #1d4264;
  color: #c4d4eb;
}

.basemap-option:hover,
.managed-layer:hover {
  background: #183b61;
  border-color: #285a82;
}

.basemap-option:has(input:checked) {
  background: #1677ff;
  border-color: #1677ff;
  color: #ffffff;
  box-shadow: none;
}

.managed-layer-text strong,
.north-arrow small {
  color: #ffffff;
}

.managed-layer-text small,
.layer-empty,
.coordinate-display,
.attribution {
  color: #8299bc;
}

.drawing-hint {
  background: #102d4d;
  border: 1px solid #285276;
  color: #ffffff;
}

.loading-dot {
  background: #1677ff;
}
</style>
