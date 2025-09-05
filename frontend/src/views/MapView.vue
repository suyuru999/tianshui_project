<template>
  <div class="map-view">
    <!-- 左侧边栏 -->
    <div class="sidebar">
      <!-- 系统标题 -->
      <div class="sidebar-header">
        <h1>流域生态环境监管系统</h1>
      </div>

      <!-- 用户信息 -->
      <div class="user-section">
        <div class="user-info">
          <i class="user-icon">👤</i>
          <span>未登录</span>
        </div>
        <button class="login-btn">登录</button>
      </div>

      <!-- 图层管理 -->
      <div class="section">
        <div class="section-header" @click="toggleLayerManagement">
          <i class="section-icon">📄</i>
          <span>图层管理</span>
          <i class="collapse-icon" :class="{ 'collapsed': !layerManagementExpanded }">▼</i>
        </div>
        
        <div class="section-content" v-show="layerManagementExpanded">
          <!-- 业务图层 -->
          <div class="layer-group">
            <div class="layer-group-header" @click="toggleBusinessLayers">
              <h4>业务图层</h4>
              <i class="collapse-icon" :class="{ 'collapsed': !businessLayersExpanded }">▼</i>
            </div>
            <div class="layer-group-content" v-show="businessLayersExpanded">
              <div class="layer-item" v-for="layer in businessLayers" :key="layer.id">
                <div class="layer-info">
                  <i :class="layer.icon"></i>
                  <span>{{ layer.name }}</span>
                </div>
                <div class="layer-controls">
                  <label class="toggle-switch" v-if="layer.type !== 'wfs'">
                    <input 
                      type="checkbox" 
                      :checked="layer.visible"
                      @change="toggleLayerVisibility(layer.id, true)"
                    />
                    <span class="slider"></span>
                  </label>
                  <button v-else class="load-btn" @click="loadWFSLayer(layer)">加载</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 临时图层 -->
          <div class="layer-group">
            <div class="layer-group-header" @click="toggleTempLayers">
              <h4>临时图层</h4>
              <i class="collapse-icon" :class="{ 'collapsed': !tempLayersExpanded }">▼</i>
            </div>
            <div class="layer-group-content" v-show="tempLayersExpanded">
              <button class="upload-btn" @click="triggerFileUpload">
                <i>📤</i>
                上传本地文件 (KML/SHP.zip)
              </button>
              <input 
                ref="fileInput" 
                type="file" 
                accept=".kml,.zip,.geojson,.json" 
                style="display: none"
                @change="handleFileUpload"
              >
            </div>
          </div>
        </div>
      </div>

      <!-- 工具箱 -->
      <div class="section">
        <div class="section-header" @click="toggleToolbox">
          <i class="section-icon">🔧</i>
          <span>工具箱</span>
          <i class="collapse-icon" :class="{ 'collapsed': !toolboxExpanded }">▼</i>
        </div>
        <div class="section-content" v-show="toolboxExpanded">
          <p class="tool-tip">使用地图左侧的工具栏进行图形绘制。</p>
          
          <!-- 坐标定位 -->
          <div class="coordinate-section">
            <h4>坐标定位</h4>
            <div class="coordinate-inputs">
              <input type="text" placeholder="经度,纬度" v-model="coordinateInput" />
              <button class="locate-btn" @click="locateCoordinate">
                <i>🔍</i>
              </button>
            </div>
          </div>

          <!-- 导出地图 -->
          <button class="export-btn" @click="exportMap">
            <i>📷</i>
            导出地图为图片
          </button>
        </div>
      </div>

      <!-- 业务功能 -->
      <div class="section">
        <div class="section-header" @click="toggleBusinessFunctions">
          <i class="section-icon">📊</i>
          <span>业务功能</span>
          <i class="collapse-icon" :class="{ 'collapsed': !businessFunctionsExpanded }">▼</i>
        </div>
        <div class="section-content" v-show="businessFunctionsExpanded">
          <div class="business-functions">
            <div class="function-item" v-for="func in businessFunctions" :key="func.id" @click="handleBusinessFunctionClick(func)">
              <i :class="func.icon"></i>
              <span>{{ func.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主地图区域 -->
    <div class="main-content">
      <MapContainer />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import MapContainer from '../components/Map/MapContainer.vue'
import { useMapStore } from '../store/map'
import { useRouter } from 'vue-router'

const router = useRouter()
const mapStore = useMapStore()
const { toggleLayerVisibility } = mapStore

const fileInput = ref(null)
const coordinateInput = ref('')

// 折叠状态控制
const layerManagementExpanded = ref(true)
const businessLayersExpanded = ref(true)
const tempLayersExpanded = ref(true)
const toolboxExpanded = ref(true)
const businessFunctionsExpanded = ref(true)

// 业务图层数据
const businessLayers = reactive([
  {
    id: 1,
    name: '水系分布 (WMS)',
    type: 'wms',
    icon: '💧',
    visible: false
  },
  {
    id: 2,
    name: '高程渲染 (DEM)',
    type: 'dem',
    icon: '🏔️',
    visible: false
  },
  {
    id: 3,
    name: '生态保护红线',
    type: 'vector',
    icon: '🛡️',
    visible: false
  },
  {
    id: 4,
    name: '行政区划 (WFS)',
    type: 'wfs',
    icon: '🏛️',
    visible: false
  }
])

// 业务功能
const businessFunctions = reactive([
  {
    id: 1,
    name: '遥感生态指数分析',
    icon: '🌿'
  },
  {
    id: 2,
    name: '生态环境指数计算',
    icon: '📊'
  },
  {
    id: 3,
    name: '重大工程叠加分析',
    icon: '🏗️'
  },
  {
    id: 4,
    name: '气候环境监测统计',
    icon: '📈'
  },
  {
    id: 5,
    name: '民众意见反馈',
    icon: '💬'
  }
])

// 跳转到遥感生态指数分析
const handleBusinessFunctionClick = (func) => {
  if (func.name === '遥感生态指数分析') {
    router.push('/remote-sensing-analysis')
    console.log('func')
  }
  if (func.name === '生态环境指数计算') {
    router.push('/ecological-index')
  }
  if (func.name === '气候环境监测统计') {
    router.push('/climate-monitoring')
  }
  if (func.name === '民众意见反馈') {
    router.push('/feedback')
  }
  // 可扩展其他功能跳转
}

// 触发文件上传
const triggerFileUpload = () => {
  fileInput.value.click()
}

// 处理文件上传
const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    console.log('上传文件:', file.name)
    // TODO: 实现文件上传逻辑
  }
  event.target.value = ''
}

// 坐标定位
const locateCoordinate = () => {
  if (coordinateInput.value) {
    console.log('定位坐标:', coordinateInput.value)
    // TODO: 实现坐标定位逻辑
  }
}

// 导出地图
const exportMap = () => {
  console.log('导出地图')
  // TODO: 实现地图导出逻辑
}

// 加载WFS图层
const loadWFSLayer = (layer) => {
  console.log('加载WFS图层:', layer.name)
  // TODO: 实现WFS图层加载逻辑
}

// 折叠切换方法
const toggleLayerManagement = () => {
  layerManagementExpanded.value = !layerManagementExpanded.value
}

const toggleBusinessLayers = () => {
  businessLayersExpanded.value = !businessLayersExpanded.value
}

const toggleTempLayers = () => {
  tempLayersExpanded.value = !tempLayersExpanded.value
}

const toggleToolbox = () => {
  toolboxExpanded.value = !toolboxExpanded.value
}

const toggleBusinessFunctions = () => {
  businessFunctionsExpanded.value = !businessFunctionsExpanded.value
}
</script>

<style scoped>
.map-view {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* 左侧边栏 */
.sidebar {
  width: 320px;
  background: white;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0,0,0,0.1);
  overflow-y: auto;
}

.sidebar-header {
  background: #1890ff;
  color: white;
  padding: 16px;
  text-align: center;
}

.sidebar-header h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

/* 用户信息 */
.user-section {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
}

.user-icon {
  font-size: 16px;
}

.login-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.login-btn:hover {
  background: #40a9ff;
}

/* 功能区块 */
.section {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-weight: 500;
  color: #333;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
  padding: 4px;
  border-radius: 4px;
}

.section-header:hover {
  background: #f5f5f5;
}

.collapse-icon {
  margin-left: auto;
  font-size: 12px;
  transition: transform 0.3s;
  color: #999;
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.section-content {
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.section-icon {
  font-size: 16px;
}

/* 图层管理 */
.layer-group {
  margin-bottom: 16px;
}

.layer-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
  padding: 4px 0;
  margin-bottom: 8px;
  transition: background 0.2s;
  border-radius: 4px;
}

.layer-group-header:hover {
  background: #f9f9f9;
}

.layer-group-header h4 {
  margin: 0;
  font-size: 14px;
  color: #666;
  font-weight: normal;
}

.layer-group-content {
  padding-left: 12px;
  border-left: 2px solid #f0f0f0;
}

.layer-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.layer-item:last-child {
  border-bottom: none;
}

.layer-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.layer-controls {
  display: flex;
  align-items: center;
}

/* 开关样式 */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 20px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
  border-radius: 20px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #1890ff;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.load-btn {
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.load-btn:hover {
  background: #e6f7ff;
  border-color: #1890ff;
}

/* 上传按钮 */
.upload-btn {
  width: 100%;
  background: #52c41a;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
}

.upload-btn:hover {
  background: #73d13d;
}

/* 工具箱 */
.tool-tip {
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
  line-height: 1.4;
}

.coordinate-section h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #666;
  font-weight: normal;
}

.coordinate-inputs {
  display: flex;
  gap: 8px;
}

.coordinate-inputs input {
  flex: 1;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 12px;
}

.locate-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.locate-btn:hover {
  background: #40a9ff;
}

.export-btn {
  width: 100%;
  background: #722ed1;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  margin-top: 12px;
}

.export-btn:hover {
  background: #9254de;
}

/* 业务功能 */
.business-functions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.function-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 13px;
}

.function-item:hover {
  background: #f5f5f5;
}

/* 主地图区域 */
.main-content {
  flex: 1;
  position: relative;
}
</style> 