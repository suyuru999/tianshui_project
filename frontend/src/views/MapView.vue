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
          <User class="inline-icon user-icon" />
          <span>{{ currentUser ? `${currentUser.username}（${currentUser.role_display || currentUser.role || '用户'}）` : '未登录' }}</span>
        </div>
        <button class="login-btn" @click="currentUser ? handleLogout() : (loginDialogVisible = true)">
          {{ currentUser ? '退出' : '登录' }}
        </button>
      </div>

      <div v-if="loginDialogVisible" class="login-mask" @click.self="loginDialogVisible = false">
        <div class="login-dialog">
          <div class="login-title">系统登录</div>
          <label class="login-field">
            <span>用户名</span>
            <input v-model="loginForm.username" type="text" autocomplete="username" />
          </label>
          <label class="login-field">
            <span>密码</span>
            <input v-model="loginForm.password" type="password" autocomplete="current-password" @keydown.enter="handleLogin" />
          </label>
          <div class="login-actions">
            <button class="dialog-cancel" @click="loginDialogVisible = false">取消</button>
            <button class="dialog-confirm" :disabled="loginLoading" @click="handleLogin">
              {{ loginLoading ? '登录中...' : '登录' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 图层管理 -->
      <div class="section">
        <div class="section-header" @click="toggleLayerManagement">
          <Files class="inline-icon section-icon" />
          <span>图层管理</span>
          <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !layerManagementExpanded }" />
        </div>
        
        <div class="section-content" v-show="layerManagementExpanded">
          <!-- 业务图层 -->
          <div class="layer-group">
            <div class="layer-group-header" @click="toggleBusinessLayers">
              <h4>业务图层</h4>
              <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !businessLayersExpanded }" />
            </div>
            <div class="layer-group-content" v-show="businessLayersExpanded">
              <div class="layer-item" v-for="layer in businessLayers" :key="layer.id">
                <div class="layer-info">
                  <component :is="layer.icon" class="inline-icon layer-icon" />
                  <span>{{ layer.name }}</span>
                </div>
                <div class="layer-controls">
                  <label class="toggle-switch" v-if="layer.type !== 'wfs'">
                    <input 
                      type="checkbox" 
                      :checked="layer.visible"
                      @change="handleBusinessLayerToggle(layer)"
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
              <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !tempLayersExpanded }" />
            </div>
            <div class="layer-group-content" v-show="tempLayersExpanded">
              <button class="upload-btn" @click="triggerFileUpload">
                <Upload class="button-icon" />
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
          <Setting class="inline-icon section-icon" />
          <span>工具箱</span>
          <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !toolboxExpanded }" />
        </div>
        <div class="section-content" v-show="toolboxExpanded">
          <p class="tool-tip">使用地图左侧的工具栏进行图形绘制。</p>
          
          <!-- 坐标定位 -->
          <div class="coordinate-section">
            <h4>坐标定位</h4>
            <div class="coordinate-inputs">
              <input type="text" placeholder="经度,纬度" v-model="coordinateInput" />
              <button class="locate-btn" @click="locateCoordinate">
                <Search class="button-icon" />
              </button>
            </div>
          </div>

          <!-- 导出地图 -->
          <button class="export-btn" @click="exportMap">
            <Camera class="button-icon" />
            导出地图为图片
          </button>
        </div>
      </div>

      <!-- 业务功能 -->
      <div class="section">
        <div class="section-header" @click="toggleBusinessFunctions">
          <DataAnalysis class="inline-icon section-icon" />
          <span>业务功能</span>
          <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !businessFunctionsExpanded }" />
        </div>
        <div class="section-content" v-show="businessFunctionsExpanded">
          <div class="business-functions">
            <div class="function-item" v-for="func in businessFunctions" :key="func.id" @click="handleBusinessFunctionClick(func)">
              <component :is="func.icon" class="inline-icon function-icon" />
              <span>{{ func.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主地图区域 -->
    <div class="main-content">
      <MapContainer ref="mapContainerRef" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  Camera,
  Connection,
  DataAnalysis,
  Files,
  Guide,
  Histogram,
  MapLocation,
  Message,
  Search,
  Setting,
  Ship,
  Sunrise,
  TrendCharts,
  Upload,
  User
} from '@element-plus/icons-vue'
import MapContainer from '../components/Map/MapContainer.vue'
import { useMapStore } from '../store/map'
import { useRouter } from 'vue-router'
import { authService, spatialService } from '../services/api.js'

const router = useRouter()
const mapStore = useMapStore()
const { toggleLayerVisibility } = mapStore

const fileInput = ref(null)
const mapContainerRef = ref(null)
const coordinateInput = ref('')
const currentUser = ref(null)
const loginDialogVisible = ref(false)
const loginLoading = ref(false)
const loginForm = reactive({
  username: 'admin',
  password: 'admin123456'
})

// 折叠状态控制
const layerManagementExpanded = ref(true)
const businessLayersExpanded = ref(true)
const tempLayersExpanded = ref(true)
const toolboxExpanded = ref(true)
const businessFunctionsExpanded = ref(true)

// 业务图层数据
const businessLayers = reactive([
  {
    id: 'water',
    name: '水系分布 (WMS)',
    type: 'wms',
    icon: Ship,
    visible: false
  },
  {
    id: 'dem',
    name: '高程渲染 (DEM)',
    type: 'dem',
    icon: Sunrise,
    visible: false
  },
  {
    id: 'eco',
    name: '生态保护红线',
    type: 'vector',
    icon: Guide,
    visible: false
  },
  {
    id: 'wfs-admin',
    name: '行政区划 (WFS)',
    type: 'wfs',
    icon: MapLocation,
    visible: false
  }
])

// 业务功能
const businessFunctions = reactive([
  {
    id: 1,
    name: '遥感生态指数分析',
    icon: DataAnalysis,
    status: 'available'
  },
  {
    id: 2,
    name: '生态环境指数计算',
    icon: Histogram,
    status: 'available'
  },
  {
    id: 3,
    name: '重大工程叠加分析',
    icon: Connection,
    status: 'planned'
  },
  {
    id: 4,
    name: '气候环境监测统计',
    icon: TrendCharts,
    status: 'available',
    route: '/climate-monitoring'
  },
  {
    id: 5,
    name: '民众意见反馈',
    icon: Message,
    status: 'available',
    route: '/feedback'
  }
])

businessFunctions[0].route = '/remote-sensing-analysis'
businessFunctions[1].route = '/ecological-index'
businessFunctions[2].status = 'available'
businessFunctions[2].route = '/overlay-analysis'

onMounted(() => {
  loadCurrentUser()
})

const loadCurrentUser = async () => {
  try {
    currentUser.value = await authService.getProfile()
  } catch {
    currentUser.value = null
  }
}

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loginLoading.value = true
  try {
    const result = await authService.login({
      username: loginForm.username,
      password: loginForm.password
    })
    currentUser.value = result.user
    loginDialogVisible.value = false
    ElMessage.success('登录成功')
  } catch (error) {
    console.error(error)
  } finally {
    loginLoading.value = false
  }
}

const handleLogout = async () => {
  try {
    await authService.logout()
    currentUser.value = null
    ElMessage.success('已退出登录')
  } catch (error) {
    console.error(error)
  }
}

// 跳转到遥感生态指数分析
const handleBusinessFunctionClick = async (func) => {
  if (func.route) {
    router.push(func.route)
    return
  }
  ElMessage.info(`${func.name} 暂未接入后端接口，当前仅作为业务入口占位`)
}

// 触发文件上传
const triggerFileUpload = () => {
  fileInput.value.click()
}

// 处理文件上传
const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    mapContainerRef.value?.loadLocalFile(file).then((success) => {
      if (success) {
        ElMessage.success(`${file.name} 已加载为临时图层`)
      }
    })
  }
  event.target.value = ''
}

// 坐标定位
const locateCoordinate = () => {
  mapContainerRef.value?.locateCoordinate(coordinateInput.value)
}

// 导出地图
const exportMap = () => {
  mapContainerRef.value?.exportMap('png')
}

// 加载WFS图层
const loadWFSLayer = (layer) => {
  spatialService.getWFSCapabilities()
    .then((result) => {
      console.log('WFS capabilities:', result)
      ElMessage.info(`${layer.name} 的 WFS 服务入口已连通，但尚未配置具体 typeName 图层加载`)
    })
    .catch(() => {
      ElMessage.error('WFS 服务不可用，请检查 GeoServer 配置')
    })
}

const handleBusinessLayerToggle = async (layer) => {
  layer.visible = !layer.visible
  toggleLayerVisibility(layer.id, true)
  const applied = mapContainerRef.value?.setLayerVisibleById(layer.id, layer.visible)
  if (applied) {
    return
  }
  try {
    if (layer.type === 'wms' || layer.type === 'dem') {
      await spatialService.getWMSCapabilities()
      ElMessage.info(`${layer.name} 后端 WMS 入口已连通，但尚未配置可渲染图层名称`)
    } else {
      await spatialService.getSpatialLayers()
      ElMessage.info(`${layer.name} 正在等待后端返回可用业务图层数据`)
    }
  } catch {
    ElMessage.error(`${layer.name} 对应的空间服务不可用，请检查 GeoServer/后端配置`)
  }
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
  width: 350px;
  height: 100vh;
  background: white;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0,0,0,0.1);
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
}

.sidebar-header,
.user-section,
.section {
  flex-shrink: 0;
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

.inline-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: currentColor;
}

.button-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.user-icon {
  font-size: 16px;
  color: #1677ff;
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

.login-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(15, 23, 42, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-dialog {
  width: 320px;
  padding: 22px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
}

.login-title {
  margin-bottom: 18px;
  color: #1f2937;
  font-size: 18px;
  font-weight: 700;
}

.login-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 14px;
  color: #4b5563;
  font-size: 13px;
}

.login-field input {
  height: 36px;
  padding: 0 10px;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  color: #1f2937;
  background: #fff;
  outline: none;
}

.login-field input:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.12);
}

.login-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.dialog-cancel,
.dialog-confirm {
  height: 34px;
  padding: 0 16px;
  border-radius: 6px;
  cursor: pointer;
}

.dialog-cancel {
  border: 1px solid #d9e2ec;
  color: #4b5563;
  background: #fff;
}

.dialog-confirm {
  border: 1px solid #1890ff;
  color: #fff;
  background: #1890ff;
}

.dialog-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  padding: 0 12px;
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
  color: #1677ff;
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
  padding: 0 12px;
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

.layer-icon,
.function-icon {
  color: #4b5563;
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
  background: #1890ff;
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
  font-weight: 500;
  transition: all 0.2s;
  box-sizing: border-box;
  height: 43.2px;
}

.upload-btn:hover {
  background: #40a9ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.3);
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
  background: #1890ff;
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
  font-weight: 500;
  transition: all 0.2s;
  box-sizing: border-box;
  height: 43.2px;
  margin-top: 12px;
}

.export-btn:hover {
  background: #40a9ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.3);
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
  min-width: 0;
  height: 100vh;
}
</style> 
