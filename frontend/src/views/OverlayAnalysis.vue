<template>
  <div class="overlay-analysis">
    <div class="main-container">
      <!-- 左侧控制面板 -->
      <div class="left-panel">
        <!-- 标题栏 -->
        <div class="panel-header">
          <RouterLink to="/" class="back-home-link" title="返回主界面">
            <ArrowLeft class="back-home-icon" />
            <span>主界面</span>
          </RouterLink>
          <h1>重大工程叠加分析</h1>
          <p>系统支持挂接最近一次或指定影像的 RSEI 结果，并叠加经济数据与工程项目数据进行风险分析。</p>
        </div>
        
        <!-- 图层控制 -->
        <div class="section">
          <div class="section-header">
            <MapLocation class="section-icon" />
            <span>图层控制</span>
          </div>
          <div class="section-content">
            <div class="layer-control">
              <div class="layer-item">
                <div class="layer-info">
                  
                  <span>生态指数栅格</span>
                </div>
                <div class="layer-controls">
                  <label class="toggle-switch">
                    <input 
                      type="checkbox" 
                      v-model="layerVisibility.ecology" 
                      @change="handleLayerToggle('ecology')" 
                    />
                    <span class="slider"></span>
                  </label>
                </div>
              </div>
              <div class="layer-item">
                <div class="layer-info">
                  
                  <span>经济数据矢量</span>
                </div>
                <div class="layer-controls">
                  <label class="toggle-switch">
                    <input 
                      type="checkbox" 
                      v-model="layerVisibility.economy" 
                      @change="handleLayerToggle('economy')" 
                    />
                    <span class="slider"></span>
                  </label>
                </div>
              </div>
              <div class="layer-item">
                <div class="layer-info">
                 
                  <span>工程项目矢量</span>
                </div>
                <div class="layer-controls">
                  <label class="toggle-switch">
                    <input 
                      type="checkbox" 
                      v-model="layerVisibility.engineering" 
                      @change="handleLayerToggle('engineering')" 
                    />
                    <span class="slider"></span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 数据上传管理 -->
        <div class="section">
          <div class="section-header">
            <Upload class="section-icon" />
            <span>数据上传管理</span>
          </div>
          <div class="section-content">
            <DataUploadPanel
              :embedded="true"
              @refresh-map="handleRefreshMap"
            />
          </div>
        </div>

        <!-- 使用说明 -->
        <div class="section">
          <div class="section-header">
            <InfoFilled class="section-icon" />
            <span>使用说明</span>
          </div>
          <div class="section-content">
            <div class="usage-info">
              <p>1. 先在遥感生态指数分析模块完成一次 RSEI 计算</p>
              <p>2. 进入本页后，可直接同步最近一次 RSEI，或选择指定影像对应的 RSEI</p>
              <p>3. 上传经济数据矢量和工程项目矢量后，系统自动叠加显示</p>
              <p>4. 点击地图任意位置获取叠加分析信息、风险判断和决策建议</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧地图区域 -->
      <div class="map-area">
        <OverlayMapContainer 
          ref="mapContainerRef"
          :layer-visibility="layerVisibility"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ArrowLeft, InfoFilled, MapLocation, Upload } from '@element-plus/icons-vue'
import OverlayMapContainer from '../components/Map/OverlayMapContainer.vue'
import DataUploadPanel from '../components/Map/DataUploadPanel.vue'

const mapContainerRef = ref(null)

// 图层可见性控制
const layerVisibility = reactive({
  ecology: true,
  economy: true,
  engineering: true
})

// 处理图层切换
const handleLayerToggle = (layerType) => {
  if (mapContainerRef.value) {
    mapContainerRef.value.toggleLayer(layerType)
  }
}

// 处理地图刷新
const handleRefreshMap = (payload = {}) => {
  if (payload.action === 'deleted' && payload.type && layerVisibility[payload.type] !== undefined) {
    layerVisibility[payload.type] = false
  }
  if (payload.action === 'updated' && payload.type && layerVisibility[payload.type] !== undefined) {
    layerVisibility[payload.type] = true
  }
  if (mapContainerRef.value) {
    mapContainerRef.value.refreshMap()
  }
}
</script>

<style scoped>
.overlay-analysis {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #f4f7fa;
}

.main-container {
  display: flex;
  width: 100%;
  height: 100%;
  min-width: 1200px;
}

/* 左侧控制面板 */
.left-panel {
  width: 360px;
  background: #ffffff;
  border-right: 1px solid #dbe6f0;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 12px rgba(15, 23, 42, 0.06);
  overflow-y: auto;
}

/* 自定义滚动条样式 */
.left-panel::-webkit-scrollbar {
  width: 6px;
}

.left-panel::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.left-panel::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.left-panel::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.panel-header {
  background: linear-gradient(135deg, #1f78d1 0%, #4a9ae6 100%);
  color: white;
  padding: 22px 18px;
  text-align: left;
  box-shadow: 0 2px 10px rgba(31, 120, 209, 0.18);
}

.back-home-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 14px;
  padding: 6px 10px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.92);
  background: rgba(255, 255, 255, 0.14);
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  transition: background 0.2s ease, transform 0.2s ease;
}

.back-home-link:hover {
  background: rgba(255, 255, 255, 0.22);
  transform: translateY(-1px);
}

.back-home-icon {
  width: 14px;
  height: 14px;
}

.panel-header h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
}

.panel-header p {
  margin: 10px 0 0 0;
  font-size: 12px;
  opacity: 0.92;
  line-height: 1.6;
}

/* 功能区块 */
.section {
  padding: 18px 16px;
  border-bottom: 1px solid #edf2f7;
}

.section:last-child {
  border-bottom: none;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  font-weight: 600;
  color: #2f455c;
  font-size: 15px;
}

.section-icon {
  font-size: 16px;
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

/* 图层控制 */
.layer-control {
  display: flex;
  flex-direction: column;
  border: 1px solid #dbe6f0;
  border-radius: 10px;
  background: #f8fbfd;
  padding: 0 12px;
}

.layer-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid #edf2f7;
  gap: 8px;
}

.layer-item:last-child {
  border-bottom: none;
}

.layer-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #44515f;
  flex: 1;
  min-width: 0;
}

.layer-icon {
  font-size: 15px;
  flex-shrink: 0;
}

.layer-controls {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* 切换开关样式 */
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
  background-color: #1f78d1;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

/* 使用说明 */
.usage-info {
  font-size: 13px;
  color: #667789;
  line-height: 1.75;
  padding: 14px 14px 14px 16px;
  border: 1px solid #dbe6f0;
  border-radius: 10px;
  background: #f8fbfd;
}

.usage-info p {
  margin: 8px 0;
  padding-left: 8px;
  position: relative;
}

.usage-info p::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #1890ff;
  font-weight: bold;
}

/* 右侧地图区域 */
.map-area {
  flex: 1;
  position: relative;
  background: #f4f7fa;
  min-width: 0;
  overflow: hidden;
}
</style>
