<template>
  <div class="analysis-sidebar">
    <!-- 页面标题 -->
    <div class="panel-header">
      <RouterLink to="/" class="back-home-link" title="返回主界面">
        <ArrowLeft class="back-home-icon" />
        <span>主界面</span>
      </RouterLink>
      <h1>遥感生态指数分析</h1>
      <p class="panel-subtitle">上传遥感影像数据，系统将自动提取多种生态指数并进行可视化。</p>
    </div>

    <!-- 数据文件管理 -->
    <div class="section">
      <div class="section-title">
        <Files class="section-icon" />
        <span>数据文件管理</span>
      </div>

      <!-- 文件上传区域 -->
      <div class="file-upload-area">
        <div class="upload-zone" @click="triggerFileUpload">
          <div class="upload-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="#1890ff" stroke-width="2" fill="none"/>
              <path d="M14 2V8H20" stroke="#1890ff" stroke-width="2" fill="none"/>
              <path d="M12 18V12" stroke="#1890ff" stroke-width="2" stroke-linecap="round"/>
              <path d="M9 15L12 12L15 15" stroke="#1890ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="upload-text">上传遥感影像文件</div>
          <div class="upload-hint">拖放文件到此处或点击选择文件</div>
          <div class="upload-types">支持 .tif/.tiff 多波段影像或成果栅格；ADF请上传完整文件夹ZIP</div>
        </div>
        <input 
          ref="fileInput" 
          type="file" 
          accept=".tif,.tiff,.jpg,.jpeg,.png,.zip" 
          style="display: none"
          @change="handleFileChange"
        >
        <div v-if="fileName" class="file-status">{{ fileName }}</div>
      </div>
    </div>

    <!-- 数据分析控制 -->
    <div class="section">
      <div class="section-title">
        <Search class="section-icon" />
        <span>数据分析控制</span>
      </div>

      <button
        class="analysis-btn"
        :disabled="!fileName || uploading"
        @click="$emit('start-analysis')"
      >
        {{ uploading ? '分析中...' : '开始分析' }}
      </button>
    </div>

    <!-- 指数选择 -->
    <div class="section">
      <div class="section-title">
        <TrendCharts class="section-icon" />
        <span>指数选择</span>
      </div>

      <div class="index-group">
        <div class="group-title">生态指数类型</div>
        <div class="index-buttons">
          <button 
            class="index-btn"
            :class="{ active: localIndex === 'heat' }"
            :disabled="disabledIndices.includes('heat')"
            @click="onIndexChange('heat')"
          >
            <span class="btn-text">热度指数 (LST)</span>
            <el-tag v-if="hasCachedResult && localIndex === 'heat'" size="small" type="success" class="cache-tag">已缓存</el-tag>
          </button>
          <button 
            class="index-btn"
            :class="{ active: localIndex === 'ndvi' }"
            :disabled="disabledIndices.includes('ndvi')"
            @click="onIndexChange('ndvi')"
          >
            <span class="btn-text">绿化指数 (NDVI)</span>
            <el-tag v-if="hasCachedResult && localIndex === 'ndvi'" size="small" type="success" class="cache-tag">已缓存</el-tag>
          </button>
          <button 
            class="index-btn"
            :class="{ active: localIndex === 'ndwi' }"
            :disabled="disabledIndices.includes('ndwi')"
            @click="onIndexChange('ndwi')"
          >
            <span class="btn-text">湿度指数 (NDWI)</span>
            <el-tag v-if="hasCachedResult && localIndex === 'ndwi'" size="small" type="success" class="cache-tag">已缓存</el-tag>
          </button>
          <button 
            class="index-btn"
            :class="{ active: localIndex === 'dryness' }"
            :disabled="disabledIndices.includes('dryness')"
            @click="onIndexChange('dryness')"
          >
            <span class="btn-text">干度指数 (NDBSI)</span>
            <el-tag v-if="hasCachedResult && localIndex === 'dryness'" size="small" type="success" class="cache-tag">已缓存</el-tag>
          </button>
          <button
            class="index-btn"
            :class="{ active: localIndex === 'rsei' }"
            :disabled="disabledIndices.includes('rsei')"
            @click="onIndexChange('rsei')"
          >
            <span class="btn-text">遥感生态指数 (RSEI)</span>
            <el-tag v-if="hasCachedResult && localIndex === 'rsei'" size="small" type="success" class="cache-tag">已缓存</el-tag>
          </button>
        </div>
      </div>
    </div>

    <!-- 缓存管理 -->
    <div class="section">
      <div class="section-title">
        <FolderOpened class="section-icon" />
        <span>缓存管理</span>
      </div>

      <button 
        class="cache-btn" 
        @click="$emit('clear-cache')"
      >
        清空缓存
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { ArrowLeft, FolderOpened, Files, Search, TrendCharts } from '@element-plus/icons-vue';

const props = defineProps({
  selectedIndex: String,
  fileName: String,
  uploading: Boolean,
  hasCachedResult: Boolean,
  disabledIndices: {
    type: Array,
    default: () => []
  }
});
const emit = defineEmits(['file-change', 'start-analysis', 'index-change', 'clear-cache']);

const localIndex = ref(props.selectedIndex || 'rsei');
watch(() => props.selectedIndex, (val) => {
  localIndex.value = val;
});

const fileInput = ref(null);

function triggerFileUpload() {
  fileInput.value.click();
}

function handleFileChange(event) {
  const file = event.target.files[0];
  if (file) {
    emit('file-change', file);
  }
}

function onIndexChange(val) {
  if (props.disabledIndices.includes(val)) {
    return;
  }
  emit('index-change', val);
}
</script>

<style scoped>
.analysis-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

/* 自定义滚动条样式 */
.analysis-sidebar::-webkit-scrollbar {
  width: 6px;
}

.analysis-sidebar::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.analysis-sidebar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.analysis-sidebar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.panel-header {
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
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

/* 文件上传区域 */
.file-upload-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upload-zone {
  width: 100%;
  background: #f8f9fa;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-zone:hover {
  border-color: #1890ff;
  background: #f0f8ff;
}

.upload-icon {
  font-size: 24px;
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

.file-status {
  font-size: 12px;
  color: #666;
  text-align: center;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #1890ff;
}

/* 分析按钮 */
.analysis-btn {
  width: 100%;
  background: #1890ff;
  color: white;
  border: none;
  padding: 14px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.analysis-btn:hover:not(.disabled) {
  background: #40a9ff;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(24, 144, 255, 0.3);
}

.analysis-btn.disabled {
  cursor: not-allowed;
  background: #d9d9d9;
  color: #999;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

/* 指数选择区域 */
.index-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.index-group:last-child {
  margin-bottom: 0;
}

.group-title {
  font-size: 14px;
  font-weight: 500;
  color: #555;
  margin: 0 0 8px 0;
}

.index-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.index-btn {
  width: 100% !important;
  min-width: 100% !important;
  max-width: 100% !important;
  height: 40px !important;
  padding: 0 16px !important;
  border-radius: 6px;
  transition: all 0.2s ease;
  background: #f8f9fa !important;
  border: 1px solid #e9ecef !important;
  color: #333 !important;
  margin: 0 !important;
  box-sizing: border-box !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  cursor: pointer;
  position: relative;
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
  font-variant-numeric: tabular-nums;
}

.index-btn .btn-text {
  flex: 1;
  text-align: center;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.cache-tag {
  margin-left: 8px;
  flex-shrink: 0;
}

.index-btn:hover:not(:disabled) {
  transform: translateX(4px);
  background: #e6f7ff !important;
  border-color: #1890ff !important;
  color: #1890ff !important;
}

.index-btn.active {
  background: #1890ff !important;
  border-color: #1890ff !important;
  color: white !important;
}

.index-btn:disabled {
  background: #f5f5f5 !important;
  color: #999 !important;
  cursor: not-allowed;
  transform: none;
}


/* 缓存管理 */
.cache-btn {
  width: 100%;
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  color: #666;
  font-weight: 500;
  border-radius: 6px;
  transition: all 0.2s ease;
  padding: 10px 16px;
  cursor: pointer;
}

.cache-btn:hover {
  background: #e6f7ff;
  border-color: #1890ff;
  color: #1890ff;
  transform: translateY(-1px);
}
</style> 
