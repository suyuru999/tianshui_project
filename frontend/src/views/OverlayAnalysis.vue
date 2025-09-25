<template>
  <div class="overlay-analysis">
    <!-- 左侧控制面板 -->
    <div class="control-panel">
      <!-- 页面标题 -->
      <div class="panel-header">
        <h1>重大工程叠加分析</h1>
        <p class="panel-subtitle">叠加展示与分析修复工程、环境质量与社会经济数据。</p>
      </div>

      <!-- 数据图层管理 -->
      <div class="section">
        <div class="section-title">
          <i class="section-icon">📊</i>
          <span>数据图层管理</span>
        </div>

        <!-- 默认图层 -->
        <div class="layer-group">
          <div class="layer-group-title">默认图层</div>
          <div class="layer-list">
            <div class="layer-item" v-for="layer in baseLayers" :key="layer.id">
              <label class="layer-checkbox">
                <input
                  type="checkbox"
                  v-model="layer.visible"
                />
                <span class="checkmark"></span>
                <span class="layer-name">{{ layer.name }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- 上传自定义图层 -->
        <div class="layer-group">
          <div class="layer-group-title">上传自定义图层</div>

          <!-- 文件类型选择 -->
          <div class="file-type-selector">
            <div
              class="file-type-option"
              :class="{ active: selectedFileType === 'geojson' }"
              @click="selectedFileType = 'geojson'"
            >
              GeoJSON
            </div>
            <div
              class="file-type-option"
              :class="{ active: selectedFileType === 'shapefile' }"
              @click="selectedFileType = 'shapefile'"
            >
              Shapefile
            </div>
            <div
              class="file-type-option"
              :class="{ active: selectedFileType === 'ecological' }"
              @click="selectedFileType = 'ecological'"
            >
              生态指数
            </div>
          </div>

          <div class="upload-section">
            <!-- GeoJSON上传组件 -->
            <GeoJSONUploader
              v-if="selectedFileType === 'geojson'"
              @file-loaded="handleGeoJSONLoaded"
              @file-cleared="handleGeoJSONClear"
              @load-to-map="addGeoJSONToMap"
              @generate-sample="handleSampleData"
            />

            <!-- Shapefile上传组件 -->
            <ShapefileUploader
              v-if="selectedFileType === 'shapefile'"
              @file-loaded="handleShapefileLoaded"
              @file-cleared="handleShapefileClear"
              @load-to-map="addShapefileToMap"
            />

            <!-- 生态指数上传组件 -->
            <EcologicalIndicesUploader
              v-if="selectedFileType === 'ecological'"
              @file-loaded="handleEcologicalIndicesLoaded"
              @file-cleared="handleEcologicalIndicesClear"
              @visualize-on-map="visualizeEcologicalIndices"
              @analyze-with-layers="analyzeEcologicalIndices"
            />
          </div>

            <!-- 已加载的自定义图层（可勾选显示/隐藏） -->
            <div class="layer-group" v-if="customUploadedLayers.length">
              <div class="layer-group-title">已加载自定义图层</div>
              <div class="layer-list">
                <div class="layer-item" v-for="layer in customUploadedLayers" :key="layer.id">
                  <label class="layer-checkbox">
                    <input
                      type="checkbox"
                      v-model="layer.visible"
                      @change="onLayerVisibilityChange(layer)"
                    />
                    <span class="checkmark"></span>
                    <span class="layer-name">{{ layer.name }}</span>
                  </label>
                  <button class="remove-layer-btn" @click="removeCustomLayer(layer.id)" title="移除图层">×</button>
                </div>
              </div>
            </div>

        </div>
      </div>

      <!-- 风险分析与监控 -->
      <div class="section">
        <div class="section-title">
          <i class="section-icon">⚠️</i>
          <span>风险分析与监控</span>
        </div>
        <div class="analysis-section">
          <p class="analysis-tip">
            请在下方选择或在地图上点击一个项目以查看其分析报告。
          </p>
          <div class="project-selector">
            <select v-model="selectedProject" class="project-dropdown">
              <option value="">请选择一个项目进行分析</option>
              <option v-for="project in projects" :key="project.id" :value="project.id">
                {{ project.name }}
              </option>
            </select>
          </div>

          <!-- 项目分析报告 -->
          <div v-if="selectedProject && projectAnalysis" class="analysis-report">
            <div class="report-header">
              <h4>{{ projectAnalysis.name }} - 分析报告</h4>
            </div>
            <div class="report-content">
              <!-- 项目基本信息 -->
              <div class="report-section">
                <h5>项目基本信息</h5>
                <div class="info-grid">
                  <div class="info-item">
                    <span class="label">项目类型:</span>
                    <span class="value">{{ projectAnalysis.type }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">项目面积:</span>
                    <span class="value">{{ projectAnalysis.area }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">项目状态:</span>
                    <span class="value status" :class="projectAnalysis.status">{{ projectAnalysis.status }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">开始时间:</span>
                    <span class="value">{{ projectAnalysis.startDate }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">结束时间:</span>
                    <span class="value">{{ projectAnalysis.endDate }}</span>
                  </div>
                </div>
              </div>

              <!-- 环境风险评估 -->
              <div class="report-section">
                <h5>环境风险评估</h5>
                <div class="risk-indicators">
                  <div class="risk-item" v-for="risk in projectAnalysis.risks" :key="risk.type">
                    <div class="risk-header">
                      <span class="risk-type">{{ risk.type }}</span>
                      <span class="risk-level" :class="risk.level">{{ risk.level }}</span>
                    </div>
                    <div class="risk-description">{{ risk.description }}</div>
                  </div>
                </div>
              </div>

              <!-- 社会经济影响 -->
              <div class="report-section">
                <h5>社会经济影响</h5>
                <div class="impact-metrics">
                  <div class="metric-item">
                    <span class="metric-label">预计投资:</span>
                    <span class="metric-value">{{ projectAnalysis.investment }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">就业岗位:</span>
                    <span class="metric-value">{{ projectAnalysis.jobs }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">受益人口:</span>
                    <span class="metric-value">{{ projectAnalysis.beneficiaries }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧地图区域 -->
    <div class="map-area">
      <OverlayMapContainer
        ref="mapContainer"
        :overlay-layers="overlayLayers"
        :selected-project="selectedProject"
        @project-click="handleProjectClick"
      />

      <!-- 生态指数图层 -->
      <EcologicalIndicesLayer
        v-if="showEcologicalIndicesLayer && ecologicalIndicesData"
        :indices-data="ecologicalIndicesData"
        @close="showEcologicalIndicesLayer = false"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import OverlayMapContainer from '../components/Map/OverlayMapContainer.vue'
import GeoJSONUploader from '../components/Common/GeoJSONUploader.vue'
import ShapefileUploader from '../components/Common/ShapefileUploader.vue'
import EcologicalIndicesUploader from '../components/Common/EcologicalIndicesUploader.vue'
import EcologicalIndicesLayer from '../components/Map/EcologicalIndicesLayer.vue'

// Emits
const emit = defineEmits(['layer-uploaded'])

// 地图容器引用
const mapContainer = ref(null)

// 文件类型选择
const selectedFileType = ref('geojson') // 默认选择GeoJSON

// 生态指数数据
const ecologicalIndicesData = ref(null)
const showEcologicalIndicesLayer = ref(false)

// 默认图层数据
const defaultLayers = reactive([
  {
    id: 'restoration_projects',
    name: '生态修复工程 (SHP)',
    visible: true,


    type: 'vector',
    color: '#52c41a'
  },
  {
    id: 'environmental_quality',
    name: '生态环境质量',
    visible: true,
    type: 'raster',
    color: '#1890ff'
  },
  {
    id: 'socio_economic',
    name: '社会经济数据',
    visible: true,
    type: 'vector',
    color: '#faad14'
  }
])

// 基础图层与自定义图层分组（用于左侧勾选列表）
const baseLayerIds = ['restoration_projects', 'environmental_quality', 'socio_economic']
const baseLayers = computed(() => defaultLayers.filter(l => baseLayerIds.includes(l.id)))
const customUploadedLayers = computed(() => defaultLayers.filter(l => !baseLayerIds.includes(l.id)))


// 项目数据
const projects = reactive([
  {


    id: 1,
    name: '天水市生态修复工程',
    type: '生态修复',
    area: '15.6 km²',
    status: '进行中',
    startDate: '2023-01-01',
    endDate: '2025-12-31'
  },
  {
    id: 2,
    name: '麦积区环境治理项目',
    type: '环境治理',
    area: '8.2 km²',
    status: '已完成',
    startDate: '2022-06-01',
    endDate: '2023-12-31'
  },
  {
    id: 3,
    name: '渭河流域生态保护',
    type: '生态保护',
    area: '25.3 km²',
    status: '规划中',
    startDate: '2024-03-01',
    endDate: '2026-12-31'
  }
])

const selectedProject = ref('')
const projectAnalysis = ref(null)

// 项目分析数据
const projectAnalysisData = {
  1: {
    name: '天水市生态修复工程',
    type: '生态修复',
    area: '15.6 km²',
    status: '进行中',
    startDate: '2023-01-01',
    endDate: '2025-12-31',
    investment: '2.5亿元',
    jobs: '120个',
    beneficiaries: '5.2万人',
    risks: [
      {
        type: '生态风险',
        level: '中等',
        description: '项目区域内存在部分敏感生态区域，需要加强保护措施'
      },
      {
        type: '技术风险',
        level: '低',
        description: '采用成熟技术方案，技术风险较低'
      },
      {
        type: '资金风险',
        level: '低',
        description: '资金已到位，风险可控'
      }
    ]
  },
  2: {
    name: '麦积区环境治理项目',
    type: '环境治理',
    area: '8.2 km²',
    status: '已完成',
    startDate: '2022-06-01',
    endDate: '2023-12-31',
    investment: '1.8亿元',
    jobs: '80个',
    beneficiaries: '3.1万人',
    risks: [
      {
        type: '生态风险',
        level: '低',
        description: '项目已完成，生态效果良好'
      },
      {
        type: '技术风险',
        level: '无',
        description: '项目已成功完成，技术方案有效'
      },
      {
        type: '资金风险',
        level: '无',
        description: '项目资金使用合理，无超支'
      }
    ]
  },
  3: {
    name: '渭河流域生态保护',
    type: '生态保护',
    area: '25.3 km²',
    status: '规划中',
    startDate: '2024-03-01',
    endDate: '2026-12-31',
    investment: '3.2亿元',
    jobs: '150个',
    beneficiaries: '8.5万人',
    risks: [
      {
        type: '生态风险',
        level: '高',
        description: '流域生态敏感，需要谨慎规划'
      },
      {
        type: '技术风险',
        level: '中等',
        description: '涉及复杂流域治理技术，需要专业团队'
      },
      {
        type: '资金风险',
        level: '中等',
        description: '投资规模较大，需要分期实施'
      }
    ]
  }
}

// 计算叠加图层（传递所有图层及其可见状态，而不是只传递可见的）
const overlayLayers = computed(() => {
  const layers = defaultLayers.map(layer => ({
    id: layer.id,
    name: layer.name,
    visible: layer.visible,
    type: layer.type,
    color: layer.color,
    data: layer.data
  }))
  console.log('overlayLayers 计算结果:', layers)
  return layers
})


// 处理GeoJSON文件加载
const handleGeoJSONLoaded = ({ file, data }) => {
  console.log('GeoJSON文件已加载:', file.name)
  console.log('GeoJSON数据:', data)
}

// 处理GeoJSON文件清除
const handleGeoJSONClear = () => {
  console.log('GeoJSON文件已清除')
}

// 将GeoJSON添加到地图
const addGeoJSONToMap = ({ data, fileName }) => {
  // 将上传的图层添加到默认图层列表中
  const newLayer = {
    id: `custom_${Date.now()}`,
    name: `自定义图层 (${fileName})`,
    visible: true,
    type: 'vector',
    color: '#722ed1',
    data: data
  }

  defaultLayers.push(newLayer)

  // 通知地图组件加载新图层
  if (mapContainer.value) {
    mapContainer.value.addCustomLayer(newLayer)
  }

  console.log('GeoJSON已添加到地图')
}

// 处理示例数据
const handleSampleData = (sampleData) => {
  console.log('生成示例数据:', sampleData)

  // 将示例数据添加到地图
  const newLayer = {
    id: `sample_${Date.now()}`,
    name: '示例数据图层',
    visible: true,
    type: 'vector',
    color: '#eb2f96',
    data: sampleData
  }

  defaultLayers.push(newLayer)

  // 通知地图组件加载新图层
  if (mapContainer.value) {
    mapContainer.value.addCustomLayer(newLayer)
  }
}

// Shapefile相关处理方法
// 处理Shapefile文件加载
const handleShapefileLoaded = ({ file, data }) => {
  console.log('Shapefile文件已加载:', file.name)
  console.log('转换后的GeoJSON数据:', data)
}

// 处理Shapefile文件清除
const handleShapefileClear = () => {
  console.log('Shapefile文件已清除')
}

// 将Shapefile添加到地图
const addShapefileToMap = ({ data, fileName }) => {
  // 将上传的图层添加到默认图层列表中
  const newLayer = {
    id: `shapefile_${Date.now()}`,
    name: `Shapefile图层 (${fileName})`,
    visible: true,
    type: 'vector',
    color: '#13c2c2',
    data: data
  }

  defaultLayers.push(newLayer)

  // 通知地图组件加载新图层
  if (mapContainer.value) {
    mapContainer.value.addCustomLayer(newLayer)
  }

  console.log('Shapefile已添加到地图')
}

// 生态指数相关处理方法
// 处理生态指数文件加载
const handleEcologicalIndicesLoaded = ({ file, data }) => {
  console.log('生态指数文件已加载:', file.name)
  console.log('生态指数数据:', data)

  // 保存生态指数数据
  ecologicalIndicesData.value = data
}

// 处理生态指数文件清除
const handleEcologicalIndicesClear = () => {
  console.log('生态指数文件已清除')
  ecologicalIndicesData.value = null
  showEcologicalIndicesLayer.value = false
}

// 在地图上可视化生态指数
const visualizeEcologicalIndices = ({ data, fileName }) => {
  console.log('在地图上可视化生态指数:', fileName)

  // 显示生态指数图层
  ecologicalIndicesData.value = data
  showEcologicalIndicesLayer.value = true

  // 在地图上高亮显示对应区域
  // 这里可以根据实际需求添加高亮逻辑
}

// 与其他图层叠加分析生态指数
const analyzeEcologicalIndices = ({ data, fileName }) => {
  console.log('生态指数与其他图层叠加分析:', fileName)

  // 保存生态指数数据
  ecologicalIndicesData.value = data
  showEcologicalIndicesLayer.value = true

  // 添加叠加分析图层
  const newLayer = {
    id: `ecological_${Date.now()}`,
    name: `生态指数图层 (${fileName})`,
    visible: true,
    type: 'ecological',
    data: data
  }

  defaultLayers.push(newLayer)

  // 通知地图组件加载新图层
  if (mapContainer.value) {
    // 这里可以添加特殊的生态指数图层处理逻辑
    // 目前简单添加为自定义图层
    mapContainer.value.addCustomLayer({
      id: newLayer.id,
      name: newLayer.name,
      visible: true,
      type: 'vector',
      color: '#722ed1',
      data: {
        type: 'Feature',
        properties: data.results,
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [105.65, 34.55],
            [105.75, 34.55],
            [105.75, 34.65],
            [105.65, 34.65],
            [105.65, 34.55]
          ]]
        }
      }
    })
  }
}

// 处理项目点击
const handleProjectClick = (projectId) => {
  selectedProject.value = projectId
  projectAnalysis.value = projectAnalysisData[projectId] || null
  console.log('选择项目:', projectId)
}
// 图层可见性变化处理
const onLayerVisibilityChange = (layer) => {
  console.log(`图层 ${layer.name} (${layer.id}) 可见性变更为: ${layer.visible}`)
}

// 移除自定义图层
const removeCustomLayer = (layerId) => {
  console.log('移除图层:', layerId)

  // 从defaultLayers中移除
  const index = defaultLayers.findIndex(layer => layer.id === layerId)
  if (index > -1) {
    defaultLayers.splice(index, 1)
  }

  // 通知地图组件移除图层
  if (mapContainer.value && mapContainer.value.removeCustomLayer) {
    mapContainer.value.removeCustomLayer(layerId)
  }
}

// 监听项目选择变化
watch(selectedProject, (newProjectId) => {
  if (newProjectId) {
    projectAnalysis.value = projectAnalysisData[newProjectId] || null
  } else {
    projectAnalysis.value = null
  }
})
</script>

<style scoped>
.overlay-analysis {
  display: flex;

  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* 左侧控制面板 */
.control-panel {
  width: 350px;
  background: #fafafa;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.panel-header {
  background: #1890ff;
  color: white;
  padding: 20px;
  text-align: center;
}

.panel-header h1 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
}

.panel-subtitle {
  margin: 0;
  font-size: 12px;
  opacity: 0.9;
  line-height: 1.4;
}

/* 功能区块 */
.section {
  padding: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.section-icon {
  font-size: 16px;
}

/* 图层组 */
.layer-group {
  margin-bottom: 20px;
}

.layer-group-title {
  font-size: 13px;
  color: #666;
  margin-bottom: 12px;
  font-weight: 500;
}

.layer-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.layer-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}

/* 图层复选框样式 */
.layer-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #333;
  user-select: none;
  flex: 1;
}

.layer-checkbox input[type="checkbox"] {
  display: none;
}

/* 移除图层按钮样式 */
.remove-layer-btn {
  background: #ff4d4f;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 8px;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.remove-layer-btn:hover {
  opacity: 1;
}

.checkmark {
  width: 16px;
  height: 16px;
  border: 2px solid #d9d9d9;
  border-radius: 3px;
  position: relative;
  transition: all 0.2s;
}

.layer-checkbox input[type="checkbox"]:checked + .checkmark {
  background: #1890ff;
  border-color: #1890ff;
}

.layer-checkbox input[type="checkbox"]:checked + .checkmark::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1px;
  width: 4px;
  height: 8px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.layer-name {
  flex: 1;
}

/* 上传区域 */
.upload-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-type-selector {
  display: flex;
  margin-bottom: 12px;
  background: #f5f5f5;
  border-radius: 4px;
  padding: 2px;
}

.file-type-option {
  flex: 1;
  padding: 8px 12px;
  text-align: center;
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.file-type-option.active {
  background: #1890ff;
  color: white;
  font-weight: 500;
}

.file-type-option:not(.active):hover {
  background: #e6f7ff;
  color: #1890ff;
}

.upload-option {
  display: flex;
  align-items: center;
  gap: 12px;
}

.upload-label {
  font-size: 13px;
  color: #333;
  flex: 1;
}

.file-select-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s;
}

.file-select-btn:hover {
  background: #40a9ff;
}

.file-status {
  font-size: 12px;
  color: #999;
  padding-left: 4px;
}

/* 风险分析区域 */
.analysis-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-tip {
  font-size: 12px;
  color: #666;
  margin: 0;
  line-height: 1.4;
}

.project-selector {
  width: 100%;
}

.project-dropdown {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 13px;
  background: white;
  cursor: pointer;
}

.project-dropdown:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

/* 分析报告样式 */
.analysis-report {
  margin-top: 16px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e8e8e8;
  overflow: hidden;
}

.report-header {
  background: #fafafa;
  padding: 12px 16px;
  border-bottom: 1px solid #e8e8e8;
}

.report-header h4 {
  margin: 0;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.report-content {
  padding: 16px;
}

.report-section {
  margin-bottom: 20px;
}

.report-section:last-child {
  margin-bottom: 0;
}

.report-section h5 {
  margin: 0 0 12px 0;
  font-size: 13px;
  color: #333;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 6px;
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #f5f5f5;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.info-item .value {
  font-size: 12px;
  color: #333;
}

.info-item .value.status {
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.info-item .value.status.进行中 {
  background: #e6f7ff;
  color: #1890ff;
}

.info-item .value.status.已完成 {
  background: #f6ffed;
  color: #52c41a;
}

.info-item .value.status.规划中 {
  background: #fffbe6;
  color: #faad14;
}

/* 风险评估样式 */
.risk-indicators {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-item {
  background: #fafafa;
  border-radius: 4px;
  padding: 12px;
  border-left: 3px solid #d9d9d9;
}

.risk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.risk-type {
  font-size: 12px;
  color: #333;
  font-weight: 500;
}

.risk-level {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 8px;
  font-weight: 500;
}

.risk-level.高 {
  background: #fff2f0;
  color: #ff4d4f;
}

.risk-level.中等 {
  background: #fffbe6;
  color: #faad14;
}

.risk-level.低 {
  background: #f6ffed;
  color: #52c41a;
}

.risk-level.无 {
  background: #f0f0f0;
  color: #999;
}

.risk-description {
  font-size: 11px;
  color: #666;
  line-height: 1.4;
}

/* 社会经济影响样式 */
.impact-metrics {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f9f9f9;
  border-radius: 4px;
}

.metric-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.metric-value {
  font-size: 12px;
  color: #333;
  font-weight: 600;
}

/* 右侧地图区域 */
.map-area {
  flex: 1;
  position: relative;
  background: #f5f5f5;
  min-height: 500px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  min-width: 0; /* 确保flex子元素可以收缩 */
}
</style>
