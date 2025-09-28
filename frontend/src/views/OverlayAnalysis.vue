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

          <!-- 已加载的自定义图层（可勾选显示/隐藏） -->
          <div class="custom-layers-section" v-if="customUploadedLayers.length">
            <div class="custom-layers-title">已加载的自定义图层</div>
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
        </div>
      </div>

      <!-- 重大工程叠加分析 -->
      <div class="section">
        <div class="section-title">
          <i class="section-icon">🔍</i>
          <span>重大工程叠加分析</span>
        </div>

        <!-- 文件上传区域 -->
        <div class="overlay-analysis-section">
          <div class="upload-grid">
            <!-- 生态指数文件上传 -->
            <div class="upload-item">
              <div class="upload-label">生态指数文件 (JSON)</div>
              <input
                type="file"
                ref="ecologicalIndexFileInput"
                accept=".json"
                @change="handleEcologicalIndexFileUpload"
                style="display: none"
              />
              <button
                class="upload-btn"
                @click="$refs.ecologicalIndexFileInput.click()"
              >
                选择文件
              </button>
              <div class="file-status" v-if="uploadedIndexFile">
                {{ uploadedIndexFile.name }}
              </div>
            </div>

            <!-- 生态修复工程文件上传 -->
            <div class="upload-item">
              <div class="upload-label">生态修复工程文件 (GeoJSON)</div>
              <input
                type="file"
                ref="ecologicalProjectFileInput"
                accept=".json"
                @change="handleEcologicalProjectFileUpload"
                style="display: none"
              />
              <button
                class="upload-btn"
                @click="$refs.ecologicalProjectFileInput.click()"
              >
                选择文件
              </button>
              <div class="file-status" v-if="uploadedProjectFile">
                {{ uploadedProjectFile.name }}
              </div>
            </div>
          </div>

          <!-- 分析控制 -->
          <div class="analysis-controls">
            <div class="file-selectors">
              <select v-model="selectedIndexFileId" class="file-selector">
                <option value="">选择生态指数文件</option>
                <option
                  v-for="file in indexFiles"
                  :key="file.id"
                  :value="file.id"
                >
                  {{ file.filename }}
                </option>
              </select>

              <select v-model="selectedProjectFileId" class="file-selector">
                <option value="">选择工程文件</option>
                <option
                  v-for="file in projectFiles"
                  :key="file.id"
                  :value="file.id"
                >
                  {{ file.filename }}
                </option>
              </select>
            </div>

            <button
              class="analyze-btn"
              @click="startOverlayAnalysis"
              :disabled="!selectedIndexFileId || !selectedProjectFileId || analysisInProgress"
            >
              {{ analysisInProgress ? '分析中...' : '开始分析' }}
            </button>
          </div>

          <!-- 分析进度 -->
          <div v-if="analysisInProgress" class="analysis-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: analysisProgress + '%' }"></div>
            </div>
            <div class="progress-text">{{ analysisProgressText }}</div>
          </div>

          <!-- 分析结果 -->
          <div v-if="analysisResults" class="analysis-results">
            <div class="results-header">
              <h4>分析结果</h4>
              <span class="risk-badge" :class="analysisResults.overall_risk_level">
                {{ getRiskLevelText(analysisResults.overall_risk_level) }}
              </span>
            </div>

            <div class="results-content">
              <!-- 风险摘要 -->
              <div class="result-section">
                <h5>风险摘要</h5>
                <div class="risk-summary">
                  <div class="summary-item">
                    <span class="label">总体风险等级:</span>
                    <span class="value">{{ getRiskLevelText(analysisResults.overall_risk_level) }}</span>
                  </div>
                  <div class="summary-item">
                    <span class="label">风险分数:</span>
                    <span class="value">{{ analysisResults.analysis_summary?.overall_risk_score?.toFixed(2) || 'N/A' }}</span>
                  </div>
                  <div class="summary-item">
                    <span class="label">高风险因子:</span>
                    <span class="value">{{ analysisResults.analysis_summary?.high_risk_count || 0 }}</span>
                  </div>
                </div>
              </div>

              <!-- 详细风险分析 -->
              <div class="result-section" v-if="analysisResults.risk_analysis?.risk_levels">
                <h5>详细风险分析</h5>
                <div class="risk-details">
                  <div
                    v-for="(risk, riskType) in analysisResults.risk_analysis.risk_levels"
                    :key="riskType"
                    class="risk-detail-item"
                  >
                    <div class="risk-detail-header">
                      <span class="risk-name">{{ getRiskTypeName(riskType) }}</span>
                      <span class="risk-level-badge" :class="risk.level">{{ getRiskLevelText(risk.level) }}</span>
                    </div>
                    <div class="risk-description">{{ risk.description }}</div>
                    <div class="risk-score">风险分数: {{ risk.score?.toFixed(2) || 'N/A' }}</div>
                  </div>
                </div>
              </div>

              <!-- 监控建议 -->
              <div class="result-section" v-if="analysisResults.monitoring_recommendations">
                <h5>监控建议</h5>
                <div class="monitoring-recommendations">
                  <div class="recommendation-item">
                    <span class="label">监控频率:</span>
                    <span class="value">{{ analysisResults.monitoring_recommendations.monitoring_frequency }}</span>
                  </div>
                  <div class="recommendation-item" v-if="analysisResults.monitoring_recommendations.key_indicators">
                    <span class="label">关键指标:</span>
                    <span class="value">{{ analysisResults.monitoring_recommendations.key_indicators.join(', ') }}</span>
                  </div>
                </div>

                <!-- 推荐行动 -->
                <div v-if="analysisResults.monitoring_recommendations.recommended_actions" class="recommended-actions">
                  <h6>推荐行动:</h6>
                  <ul class="action-list">
                    <li
                      v-for="action in analysisResults.monitoring_recommendations.recommended_actions.slice(0, 3)"
                      :key="action.action"
                      class="action-item"
                    >
                      <span class="action-text">{{ action.action }}</span>
                      <span class="action-meta">
                        优先级: {{ action.priority }} | 时限: {{ action.timeline }}
                      </span>
                    </li>
                  </ul>
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
import { ref, reactive, computed } from 'vue'
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

// 叠加分析相关数据
const indexFiles = ref([])
const projectFiles = ref([])
const selectedIndexFileId = ref('')
const selectedProjectFileId = ref('')
const uploadedIndexFile = ref(null)
const uploadedProjectFile = ref(null)
const analysisInProgress = ref(false)
const analysisProgress = ref(0)
const analysisProgressText = ref('')
const analysisResults = ref(null)

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



// 叠加分析相关方法
const API_BASE = '/api/v1/environment'

// 加载文件列表
const loadFileList = async () => {
  try {
    // 加载生态指数文件
    const indexResponse = await fetch(`${API_BASE}/ecological-index-files/`)
    const indexData = await indexResponse.json()
    indexFiles.value = Array.isArray(indexData) ? indexData : (indexData.results || [])

    // 加载生态修复工程文件
    const projectResponse = await fetch(`${API_BASE}/ecological-project-files/`)
    const projectData = await projectResponse.json()
    projectFiles.value = Array.isArray(projectData) ? projectData : (projectData.results || [])
  } catch (error) {
    console.error('加载文件列表失败:', error)
  }
}

// 处理生态指数文件上传
const handleEcologicalIndexFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)
  formData.append('filename', file.name)
  formData.append('description', '生态指数数据文件')

  try {
    const response = await fetch(`${API_BASE}/ecological-index-files/`, {
      method: 'POST',
      body: formData
    })

    if (response.ok) {
      uploadedIndexFile.value = file
      await loadFileList()
      console.log('生态指数文件上传成功')
    } else {
      console.error('上传失败:', response.statusText)
    }
  } catch (error) {
    console.error('上传错误:', error)
  }
}

// 处理生态修复工程文件上传
const handleEcologicalProjectFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)
  formData.append('filename', file.name)
  formData.append('description', '生态修复工程项目数据文件')

  try {
    const response = await fetch(`${API_BASE}/ecological-project-files/`, {
      method: 'POST',
      body: formData
    })

    if (response.ok) {
      uploadedProjectFile.value = file
      await loadFileList()
      console.log('工程文件上传成功')
    } else {
      console.error('上传失败:', response.statusText)
    }
  } catch (error) {
    console.error('上传错误:', error)
  }
}

// 开始叠加分析
const startOverlayAnalysis = async () => {
  if (!selectedIndexFileId.value || !selectedProjectFileId.value) {
    return
  }

  analysisInProgress.value = true
  analysisProgress.value = 0
  analysisProgressText.value = '创建分析任务...'
  analysisResults.value = null

  const taskData = {
    name: `叠加分析任务_${new Date().toLocaleString()}`,
    description: '生态指数与修复工程项目的叠加影响分析',
    ecological_index_file: selectedIndexFileId.value,
    ecological_project_file: selectedProjectFileId.value
  }

  try {
    analysisProgress.value = 10

    const response = await fetch(`${API_BASE}/overlay-analysis-tasks/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(taskData)
    })

    if (response.ok) {
      const task = await response.json()
      console.log('创建任务响应:', task)
      console.log('任务ID:', task.id)

      analysisProgress.value = 50
      analysisProgressText.value = '分析任务已创建，正在执行...'

      // 检查任务ID是否存在
      if (task.id) {
        // 轮询任务状态
        await pollTaskStatus(task.id)
      } else {
        console.error('任务ID未定义:', task)
        analysisProgressText.value = '创建任务失败：任务ID未返回'
        analysisInProgress.value = false
      }
    } else {
      console.error('创建分析任务失败:', response.statusText)
      analysisInProgress.value = false
    }
  } catch (error) {
    console.error('创建任务错误:', error)
    analysisInProgress.value = false
  }
}

// 轮询任务状态
const pollTaskStatus = async (taskId) => {
  console.log('轮询任务状态，任务ID:', taskId)

  if (!taskId || taskId === 'undefined') {
    console.error('无效的任务ID:', taskId)
    analysisProgressText.value = '任务ID无效'
    analysisInProgress.value = false
    return
  }

  try {
    const response = await fetch(`${API_BASE}/overlay-analysis-tasks/${taskId}/`)

    if (!response.ok) {
      console.error('获取任务状态失败:', response.status, response.statusText)
      analysisProgressText.value = `获取任务状态失败: ${response.status}`
      analysisInProgress.value = false
      return
    }

    const task = await response.json()
    console.log('任务状态响应:', task)

    analysisProgress.value = task.progress || 50
    analysisProgressText.value = task.current_step || '处理中...'

    if (task.status === 'completed') {
      analysisProgress.value = 100
      analysisProgressText.value = '分析完成！'
      analysisResults.value = task.analysis_results

      setTimeout(() => {
        analysisInProgress.value = false
      }, 2000)
    } else if (task.status === 'failed') {
      analysisProgressText.value = '分析失败：' + (task.error_message || '未知错误')
      setTimeout(() => {
        analysisInProgress.value = false
      }, 3000)
    } else {
      // 继续轮询
      setTimeout(() => pollTaskStatus(taskId), 2000)
    }
  } catch (error) {
    console.error('轮询任务状态失败:', error)
    setTimeout(() => pollTaskStatus(taskId), 5000)
  }
}

// 获取风险等级文本
const getRiskLevelText = (level) => {
  const levelMap = {
    'low': '低风险',
    'medium': '中风险',
    'high': '高风险',
    'critical': '极高风险'
  }
  return levelMap[level] || level
}

// 获取风险类型名称
const getRiskTypeName = (type) => {
  const typeMap = {
    'fragility_risk': '生态脆弱性风险',
    'erosion_risk': '土壤侵蚀风险',
    'land_use_risk': '土地利用风险',
    'project_risk': '工程项目风险'
  }
  return typeMap[type] || type
}

// 组件挂载时加载文件列表
import { onMounted } from 'vue'
onMounted(() => {
  loadFileList()
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

/* 自定义图层区域样式 */
.custom-layers-section {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.custom-layers-title {
  font-size: 12px;
  font-weight: 500;
  color: #666;
  margin-bottom: 10px;
  padding-left: 4px;
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
  padding: 6px 10px;
  background: #f9f9f9;
  border-radius: 4px;
  border: 1px solid #e8e8e8;
  transition: all 0.2s;
}

.layer-item:hover {
  background: #f0f0f0;
  border-color: #d9d9d9;
}

/* 图层复选框样式 */
.layer-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 12px;
  color: #333;
  user-select: none;
  flex: 1;
}

.layer-checkbox input[type="checkbox"] {
  margin: 0;
  width: 14px;
  height: 14px;
}

.layer-name {
  font-size: 12px;
  color: #333;
  line-height: 1.4;
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
  margin-top: 4px;
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



/* 叠加分析样式 */
.overlay-analysis-section {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 4px;
}

.upload-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 4px;
}

.upload-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.upload-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.upload-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s;
}

.upload-btn:hover {
  background: #40a9ff;
}

.file-status {
  font-size: 11px;
  color: #52c41a;
  padding: 4px 8px;
  background: #f6ffed;
  border-radius: 4px;
  border: 1px solid #b7eb8f;
}

.analysis-controls {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;
  margin-top: 8px;
}

.file-selectors {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-selector {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 12px;
  background: white;
  cursor: pointer;
}

.file-selector:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.analyze-btn {
  background: #52c41a;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.2s;
}

.analyze-btn:hover:not(:disabled) {
  background: #73d13d;
}

.analyze-btn:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.analysis-progress {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 4px;
  border: 1px solid #e8e8e8;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #1890ff;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 12px;
  color: #666;
  text-align: center;
}

.analysis-results {
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  overflow: hidden;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
}

.results-header h4 {
  margin: 0;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.risk-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.risk-badge.low {
  background: #f6ffed;
  color: #52c41a;
}

.risk-badge.medium {
  background: #fffbe6;
  color: #faad14;
}

.risk-badge.high {
  background: #fff2f0;
  color: #ff4d4f;
}

.risk-badge.critical {
  background: #fff0f6;
  color: #eb2f96;
}

.results-content {
  padding: 16px;
}

.result-section {
  margin-bottom: 16px;
}

.result-section:last-child {
  margin-bottom: 0;
}

.result-section h5 {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #333;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 4px;
}

.risk-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 12px;
}

.summary-item .label {
  color: #666;
  font-weight: 500;
}

.summary-item .value {
  color: #333;
  font-weight: 600;
}

.risk-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.risk-detail-item {
  background: #fafafa;
  border-radius: 4px;
  padding: 8px;
  border-left: 3px solid #d9d9d9;
}

.risk-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.risk-name {
  font-size: 12px;
  color: #333;
  font-weight: 500;
}

.risk-level-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 8px;
  font-weight: 500;
}

.risk-level-badge.low {
  background: #f6ffed;
  color: #52c41a;
}

.risk-level-badge.medium {
  background: #fffbe6;
  color: #faad14;
}

.risk-level-badge.high {
  background: #fff2f0;
  color: #ff4d4f;
}

.risk-description {
  font-size: 11px;
  color: #666;
  line-height: 1.4;
  margin-bottom: 4px;
}

.risk-score {
  font-size: 10px;
  color: #999;
}

.monitoring-recommendations {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.recommendation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 12px;
}

.recommendation-item .label {
  color: #666;
  font-weight: 500;
}

.recommendation-item .value {
  color: #333;
}

.recommended-actions {
  margin-top: 12px;
}

.recommended-actions h6 {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #333;
  font-weight: 600;
}

.action-list {
  margin: 0;
  padding-left: 16px;
}

.action-item {
  margin-bottom: 6px;
  font-size: 11px;
  line-height: 1.4;
}

.action-text {
  color: #333;
  font-weight: 500;
}

.action-meta {
  color: #999;
  font-size: 10px;
  margin-left: 8px;
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
