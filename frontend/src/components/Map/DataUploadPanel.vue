<template>
  <div class="data-upload-panel" :class="{ 'embedded': embedded }">
    <div class="panel-header" v-if="!embedded">
      <h3>数据上传管理</h3>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>
    
    <div class="panel-content">
      <!-- 数据类型选择器 -->
      <div class="data-type-selector">
        <div 
          v-for="type in dataTypes" 
          :key="type.value"
          class="type-tab"
          :class="{ 'active': selectedType === type.value }"
          @click="selectDataType(type.value)"
        >
          <span class="type-icon">{{ type.icon }}</span>
          <span class="type-label">{{ type.label }}</span>
        </div>
      </div>

      <!-- 统一的上传区域 -->
      <div class="upload-section">
        <div class="upload-zone" @click="triggerFileInput(selectedType)">
          <input 
            ref="ecologyInput"
            v-if="selectedType === 'ecology'"
            type="file" 
            accept=".tif,.tiff"
            @change="handleFileSelect($event, 'ecology')"
            style="display: none"
          />
          <input 
            ref="economyInput"
            v-if="selectedType === 'economy'"
            type="file" 
            accept=".zip"
            @change="handleFileSelect($event, 'economy')"
            style="display: none"
          />
          <input 
            ref="engineeringInput"
            v-if="selectedType === 'engineering'"
            type="file" 
            accept=".zip"
            @change="handleFileSelect($event, 'engineering')"
            style="display: none"
          />
          <div v-if="!files[selectedType]">
            <div class="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="#1890ff" stroke-width="2" fill="none"/>
                <path d="M14 2V8H20" stroke="#1890ff" stroke-width="2" fill="none"/>
                <path d="M12 18V12" stroke="#1890ff" stroke-width="2" stroke-linecap="round"/>
                <path d="M9 15L12 12L15 15" stroke="#1890ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="upload-text">{{ currentDataType.uploadText }}</div>
            <div class="upload-hint">拖放文件到此处或点击选择文件</div>
            <div class="upload-types">{{ currentDataType.fileTypes }}</div>
          </div>
          <div v-else class="file-info">
            <div class="file-name">{{ files[selectedType].name }}</div>
            <div class="file-size">{{ formatFileSize(files[selectedType].size) }}</div>
            <button class="remove-btn" @click.stop="removeFile(selectedType)">移除</button>
          </div>
        </div>
        <button 
          class="upload-btn" 
          :disabled="!files[selectedType] || uploading[selectedType]"
          @click="uploadFile(selectedType)"
        >
          {{ uploading[selectedType] ? '上传中...' : currentDataType.buttonText }}
        </button>
        <div v-if="uploadProgress[selectedType] > 0" class="progress-bar">
          <div class="progress-fill" :style="{ width: uploadProgress[selectedType] + '%' }"></div>
          <span class="progress-text">{{ uploadProgress[selectedType] }}%</span>
        </div>
        <div v-if="uploadStatus[selectedType]" :class="['status-message', uploadStatus[selectedType].type]">
          {{ uploadStatus[selectedType].message }}
        </div>
        <div v-if="publishedLayers[selectedType]" class="published-row">
          <div>
            <strong>{{ currentDataType.label }}</strong>
            <span>已发布到地图</span>
          </div>
          <button
            class="delete-layer-btn"
            :disabled="deleting[selectedType]"
            @click="deleteUploadedLayer(selectedType)"
          >
            {{ deleting[selectedType] ? '删除中...' : '删除图层' }}
          </button>
        </div>
      </div>

      <!-- 数据说明 -->
      <div class="data-requirements">
        <h4>数据要求说明</h4>
        <ul>
          <li><strong>生态指数栅格：</strong>GeoTIFF格式，需包含地理坐标信息，推荐使用EPSG:4326或EPSG:3857投影</li>
          <li><strong>经济数据矢量：</strong>需包含字段：admin_name（区域名称）、GDP、POP（人口）、area_km2（面积）</li>
          <li><strong>工程项目矢量：</strong>需包含字段：proj_name（项目名称）、proj_type（类型）、status（状态）、start_date、end_date、area_km2</li>
          <li><strong>字符编码：</strong>所有矢量数据请使用UTF-8编码，确保中文正常显示</li>
          <li><strong>坐标系统：</strong>建议使用 EPSG:4326 (WGS84) 坐标系</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import request from '../../utils/http.js'
import { API_ENDPOINTS, buildApiUrl } from '../../config/api.js'

// Props
defineProps({
  embedded: {
    type: Boolean,
    default: false
  }
})

// 数据类型配置
const dataTypes = [
  {
    value: 'ecology',
    label: '生态指数栅格',
    
    accept: '.tif,.tiff',
    uploadText: '上传生态指数栅格文件',
    fileTypes: '支持的文件类型: .tif, .tiff',
    buttonText: '上传生态栅格'
  },
  {
    value: 'economy',
    label: '经济数据矢量',
    
    accept: '.zip',
    uploadText: '上传经济数据矢量文件',
    fileTypes: '支持的文件类型: .zip (包含 .shp/.shx/.dbf/.prj)',
    buttonText: '上传经济矢量'
  },
  {
    value: 'engineering',
    label: '工程项目矢量',
    
    accept: '.zip',
    uploadText: '上传工程项目矢量文件',
    fileTypes: '支持的文件类型: .zip (包含 .shp/.shx/.dbf/.prj)',
    buttonText: '上传工程矢量'
  }
]

// 当前选择的数据类型
const selectedType = ref('ecology')

// 计算当前数据类型配置
const currentDataType = computed(() => {
  return dataTypes.find(type => type.value === selectedType.value) || dataTypes[0]
})

// 文件输入引用
const ecologyInput = ref(null)
const economyInput = ref(null)
const engineeringInput = ref(null)

// 选择数据类型
const selectDataType = (type) => {
  selectedType.value = type
}

// 文件选择
const files = reactive({
  ecology: null,
  economy: null,
  engineering: null
})

// 上传状态
const uploading = reactive({
  ecology: false,
  economy: false,
  engineering: false
})

// 上传进度
const uploadProgress = reactive({
  ecology: 0,
  economy: 0,
  engineering: 0
})

// 上传结果状态
const uploadStatus = reactive({
  ecology: null,
  economy: null,
  engineering: null
})

const publishedLayers = reactive({
  ecology: true,
  economy: true,
  engineering: true
})

const deleting = reactive({
  ecology: false,
  economy: false,
  engineering: false
})

// 触发文件选择
const triggerFileInput = (type) => {
  if (type === 'ecology' && ecologyInput.value) {
    ecologyInput.value.click()
  } else if (type === 'economy' && economyInput.value) {
    economyInput.value.click()
  } else if (type === 'engineering' && engineeringInput.value) {
    engineeringInput.value.click()
  }
}

// 处理文件选择
const handleFileSelect = (event, type) => {
  const file = event.target.files[0]
  if (file) {
    // 验证文件大小（最大100MB）
    const maxSize = 100 * 1024 * 1024
    if (file.size > maxSize) {
      uploadStatus[type] = {
        type: 'error',
        message: '文件大小超过100MB限制'
      }
      return
    }
    
    files[type] = file
    uploadStatus[type] = null
    uploadProgress[type] = 0
  }
}

// 移除文件
const removeFile = (type) => {
  files[type] = null
  uploadStatus[type] = null
  uploadProgress[type] = 0
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 上传文件
const uploadFile = async (type) => {
  if (!files[type]) return
  
  uploading[type] = true
  uploadStatus[type] = { type: 'info', message: '正在上传...' }
  uploadProgress[type] = 0
  
  try {
    const formData = new FormData()
    formData.append('file', files[type])
    formData.append('data_type', type)
    
    // 根据类型确定上传端点（注意：URL必须以斜杠结尾）
    let endpoint = ''
    if (type === 'ecology') {
      endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.UPLOAD_ECOLOGY_RASTER)
    } else if (type === 'economy') {
      endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.UPLOAD_ECONOMY_VECTOR)
    } else if (type === 'engineering') {
      endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.UPLOAD_ENGINEERING_VECTOR)
    }
    
    const response = await request.upload(endpoint, formData, {
      skipAuth: true,
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        uploadProgress[type] = percentCompleted
      }
    })
    
    if (response.success) {
      publishedLayers[type] = true
      uploadStatus[type] = {
        type: 'success',
        message: response.message || '上传成功！数据已发布到GeoServer'
      }
      
      // 3秒后清空文件选择
      setTimeout(() => {
        files[type] = null
        uploadProgress[type] = 0
      }, 3000)
      
      // 触发地图刷新事件
      emitRefreshMap(type, 'updated')
    } else {
      uploadStatus[type] = {
        type: 'error',
        message: response.message || '上传失败'
      }
    }
  } catch (error) {
    console.error('上传失败:', error)
    console.error('错误详情:', error.response?.data)
    
    // 提取错误信息
    let errorMessage = '上传失败'
    if (error.response) {
      // 服务器返回了错误响应
      if (error.response.data) {
        if (error.response.data.message) {
          errorMessage = error.response.data.message
        } else if (error.response.data.error) {
          errorMessage = error.response.data.error
        } else if (error.response.data.error_detail) {
          errorMessage = `上传失败: ${error.response.data.error_detail.substring(0, 200)}`
        }
      }
      errorMessage = `${errorMessage} (HTTP ${error.response.status})`
    } else if (error.message) {
      errorMessage = `上传失败: ${error.message}`
    }
    
    uploadStatus[type] = {
      type: 'error',
      message: errorMessage
    }
  } finally {
    uploading[type] = false
  }
}

const deleteUploadedLayer = async (type) => {
  deleting[type] = true
  uploadStatus[type] = { type: 'info', message: '正在删除图层...' }
  try {
    const endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.DELETE_UPLOADED_LAYER)
    const response = await request.delete(endpoint, {
      skipAuth: true,
      params: { data_type: type }
    })

    publishedLayers[type] = false
    files[type] = null
    uploadProgress[type] = 0
    uploadStatus[type] = {
      type: response.success ? 'success' : 'error',
      message: response.message || '图层已删除'
    }
    emitRefreshMap(type, 'deleted')
  } catch (error) {
    console.error('删除图层失败:', error)
    uploadStatus[type] = {
      type: 'error',
      message: error.response?.data?.message || error.response?.data?.error || '删除图层失败'
    }
  } finally {
    deleting[type] = false
  }
}

// 定义事件
const emit = defineEmits(['close', 'refresh-map'])

// 触发地图刷新
const emitRefreshMap = (type = selectedType.value, action = 'updated') => {
  emit('refresh-map', { type, action })
}
</script>

<style scoped>
.data-upload-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  z-index: 2000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.data-upload-panel.embedded {
  position: relative;
  top: auto;
  left: auto;
  transform: none;
  width: 100%;
  max-width: 100%;
  max-height: none;
  box-shadow: none;
  border-radius: 0;
  z-index: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 2px solid #f0f0f0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.panel-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.upload-section {
  margin-bottom: 20px;
}

.icon {
  font-size: 20px;
}

/* 数据类型选择器 */
.data-type-selector {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 12px;
}

.type-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: #f5f5f5;
  color: #666;
  font-size: 13px;
  user-select: none;
  border: 1px solid transparent;
}

.type-tab:hover {
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.1) 0%, rgba(64, 169, 255, 0.1) 100%);
  color: #1890ff;
  border: 1px solid rgba(24, 144, 255, 0.2);
}

.type-tab.active {
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
  color: white;
  font-weight: 500;
  box-shadow: 0 2px 6px rgba(24, 144, 255, 0.3);
}

.type-icon {
  font-size: 16px;
}

.type-label {
  font-size: 13px;
}

.upload-zone {
  width: 100%;
  background: #f8f9fa;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.upload-zone:hover {
  border-color: #1890ff;
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.05) 0%, rgba(64, 169, 255, 0.05) 100%);
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
}

.upload-icon {
  color: #1890ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.upload-icon svg {
  width: 48px;
  height: 48px;
}

.upload-text {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.upload-hint {
  font-size: 12px;
  color: #666;
}

.upload-types {
  font-size: 11px;
  color: #999;
}

.file-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  text-align: left;
}

.file-name {
  font-weight: 500;
  color: #333;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: #999;
  font-size: 13px;
  margin-right: 12px;
}

.remove-btn {
  padding: 4px 12px;
  border: 1px solid #ff4d4f;
  background: white;
  color: #ff4d4f;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: #ff4d4f;
  color: white;
}

.upload-btn {
  width: 100%;
  padding: 12px;
  border: none;
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
  color: white;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
}

.upload-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
  opacity: 0.95;
}

.upload-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.progress-bar {
  position: relative;
  height: 24px;
  background: #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1890ff 0%, #40a9ff 100%);
  transition: width 0.3s;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.status-message {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.status-message.success {
  background: #f0f9ff;
  color: #0066cc;
  border: 1px solid #b3d9ff;
}

.status-message.error {
  background: #fff1f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

.status-message.info {
  background: #f0f5ff;
  color: #1890ff;
  border: 1px solid #adc6ff;
}

.published-row {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid #d6e8fa;
  border-radius: 7px;
  background: #f7fbff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #315f8c;
  font-size: 13px;
}

.published-row div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.published-row span {
  color: #6b7f93;
  font-size: 12px;
}

.delete-layer-btn {
  flex-shrink: 0;
  height: 30px;
  padding: 0 12px;
  border: 1px solid #ffccc7;
  border-radius: 5px;
  background: #fff;
  color: #cf1322;
  cursor: pointer;
  font-size: 12px;
}

.delete-layer-btn:hover:not(:disabled) {
  background: #fff1f0;
}

.delete-layer-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.data-requirements {
  margin-top: 32px;
  padding: 20px;
  background: #fff9e6;
  border-radius: 8px;
  border: 1px solid #ffe58f;
}

.data-requirements h4 {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: #fa8c16;
}

.data-requirements ul {
  margin: 0;
  padding-left: 20px;
}

.data-requirements li {
  margin-bottom: 8px;
  color: #666;
  font-size: 13px;
  line-height: 1.6;
}

.data-requirements strong {
  color: #333;
}
</style>

