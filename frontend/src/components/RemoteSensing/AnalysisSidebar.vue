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
            v-for="option in indexOptions"
            :key="option.key"
            class="index-btn"
            :class="{ active: localIndex === option.key }"
            :disabled="disabledIndices.includes(option.key)"
            @click="onIndexChange(option.key)"
          >
            <span class="btn-text">{{ option.label }}</span>
            <el-tag v-if="cachedIndices.includes(option.key)" size="small" type="success" class="cache-tag">已缓存</el-tag>
          </button>
        </div>
        <div v-if="capabilitiesKnown" class="supported-hint">
          {{ supportedIndexLabels.length > 0 ? `当前影像支持：${supportedIndexLabels.join('、')}` : '当前影像暂不支持多波段生态指数计算，请确认上传的是原始多波段遥感影像。' }}
        </div>
      </div>
    </div>

    <!-- 缓存管理 -->
    <div class="section">
      <div class="history-card">
        <div class="history-card__title-row">
          <FolderOpened class="history-card__icon" />
          <div class="history-card__title">最近结果</div>
        </div>
        <div class="history-card__summary-row">
          <span class="history-card__count">{{ historyItems.length }} 条</span>
          <div class="history-card__actions">
            <button
              v-if="historyExpanded && historyItems.length > 0"
              type="button"
              class="history-text-btn"
              @click="$emit('clear-history')"
            >
              清空
            </button>
            <button
              type="button"
              class="history-toggle-btn"
              @click="$emit('toggle-history')"
            >
              {{ historyExpanded ? '收起' : '展开' }}
            </button>
          </div>
        </div>
        <div class="history-card__description">
          这里会保留最近几次可直接回看的结果
        </div>

        <div v-if="historyExpanded && historyItems.length > 0" class="history-list">
          <div
            v-for="item in historyItems"
            :key="`${item.imageId}_${item.indexType}_${item.timestamp}`"
            class="history-item"
          >
            <button
              type="button"
              class="history-item__main"
              @click="$emit('restore-history', item)"
            >
              <div class="history-item__title">{{ item.fileName || '未命名影像' }}</div>
              <div class="history-item__meta">
                <span>{{ getIndexLabel(item.indexType) }}</span>
                <span>{{ formatHistoryTime(item.timestamp) }}</span>
              </div>
            </button>
            <button
              type="button"
              class="history-delete-btn"
              @click="$emit('delete-history', item)"
            >
              删除
            </button>
          </div>
        </div>
        <div v-else-if="historyExpanded" class="history-empty">
          当前还没有可恢复的分析结果
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { ArrowLeft, FolderOpened, Files, Search, TrendCharts } from '@element-plus/icons-vue';
import { formatHistoryTime } from '../../utils/resultHistory.js';

const props = defineProps({
  selectedIndex: String,
  fileName: String,
  uploading: Boolean,
  indexOptions: {
    type: Array,
    default: () => []
  },
  cachedIndices: {
    type: Array,
    default: () => []
  },
  disabledIndices: {
    type: Array,
    default: () => []
  },
  supportedIndexLabels: {
    type: Array,
    default: () => []
  },
  capabilitiesKnown: {
    type: Boolean,
    default: false
  },
  historyItems: {
    type: Array,
    default: () => []
  },
  historyExpanded: {
    type: Boolean,
    default: false
  }
});
const emit = defineEmits([
  'file-change',
  'start-analysis',
  'index-change',
  'clear-cache',
  'toggle-history',
  'clear-history',
  'delete-history',
  'restore-history'
]);

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

function getIndexLabel(indexType) {
  const map = {
    rsei: '遥感生态指数 (RSEI)',
    ndvi: '绿化指数 (NDVI)',
    ndwi: '湿度指数 (NDWI)',
    dryness: '干度指数 (NDBSI)',
    heat: '热度指数 (LST)'
  };
  return map[String(indexType || '').toLowerCase()] || indexType || '未知指数';
}
</script>

<style scoped>
.analysis-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-bottom: 16px;
  background: #0b2340;
  color: #c4d4eb;
}

/* 自定义滚动条样式 */
.analysis-sidebar::-webkit-scrollbar {
  width: 6px;
}

.analysis-sidebar::-webkit-scrollbar-track {
  background: #06182d;
  border-radius: 3px;
}

.analysis-sidebar::-webkit-scrollbar-thumb {
  background: rgba(130, 153, 188, 0.45);
  border-radius: 3px;
  transition: background 0.2s ease;
}

.analysis-sidebar::-webkit-scrollbar-thumb:hover {
  background: rgba(196, 212, 235, 0.55);
}

.panel-header {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 10px 12px;
  min-height: 110px;
  background: #06182d;
  color: #fff;
  padding: 22px 18px 18px;
  text-align: left;
  box-shadow: none;
  border-bottom: 1px solid #18385d;
  flex: 0 0 auto;
}

.back-home-link {
  grid-column: 2;
  grid-row: 1;
  min-width: 72px;
  min-height: 32px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid #1c4265;
  border-radius: 6px;
  background: #102d4d;
  color: #c4d4eb;
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}

.back-home-link:hover {
  background: #183b61;
  border-color: #285a82;
  color: #ffffff;
}

.back-home-icon {
  width: 14px;
  height: 14px;
  flex: 0 0 14px;
}

.panel-header h1 {
  grid-column: 1;
  grid-row: 1;
  margin: 2px 0 0;
  font-size: 22px;
  line-height: 1.22;
  font-weight: 700;
  color: #ffffff;
  white-space: nowrap;
  overflow: visible;
  text-overflow: clip;
}

.panel-subtitle {
  grid-column: 1 / -1;
  margin: 0;
  padding-right: 4px;
  font-size: 13px;
  color: #91a9c4;
  line-height: 1.5;
  white-space: normal;
  word-break: normal;
}

/* 功能区块 */
.section {
  margin: 14px 16px 0;
  padding: 14px;
  border: 1px solid #1c4265;
  border-radius: 10px;
  background: #102d4d;
  box-shadow: none;
  flex: 0 0 auto;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  color: #ffffff;
}

.section-icon {
  font-size: 16px;
  color: #26b6e8;
}

/* 文件上传区域 */
.file-upload-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upload-zone {
  width: 100%;
  background: #0d2745;
  border: 1px dashed #285a82;
  border-radius: 8px;
  padding: 16px 14px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-zone:hover {
  border-color: #1677ff;
  background: #183b61;
}

.upload-icon {
  font-size: 24px;
  color: #26b6e8;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}

.upload-icon svg {
  width: 34px;
  height: 34px;
}

.upload-text {
  font-size: 14px;
  font-weight: 700;
  color: #ffffff;
}

.upload-hint {
  font-size: 12px;
  color: #91a9c4;
  line-height: 1.45;
}

.upload-types {
  font-size: 11px;
  color: #8299bc;
  line-height: 1.45;
  white-space: normal;
  overflow-wrap: anywhere;
}

.file-status {
  font-size: 12px;
  color: #c4d4eb;
  text-align: center;
  padding: 8px 12px;
  background: #0d2745;
  border-radius: 6px;
  border: 1px solid #1c4265;
  border-left: 3px solid #26b6e8;
  word-break: break-all;
}

/* 分析按钮 */
.analysis-btn {
  width: 100%;
  background: #1677ff;
  color: white;
  border: 1px solid rgba(47, 151, 185, 0.2);
  padding: 13px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.analysis-btn:hover:not(.disabled) {
  background: #0e62dd;
  transform: none;
  box-shadow: none;
}

.analysis-btn.disabled,
.analysis-btn:disabled {
  cursor: not-allowed;
  background: #14314f;
  border-color: #1c4265;
  color: #5d7494;
  opacity: 1;
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
  font-weight: 600;
  color: #c4d4eb;
  margin: 0 0 8px 0;
}

.index-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.supported-hint {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #0d2745;
  border: 1px solid #1c4265;
  color: #c4d4eb;
  font-size: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.index-btn {
  width: 100% !important;
  min-width: 100% !important;
  max-width: 100% !important;
  height: 40px !important;
  padding: 0 16px !important;
  border-radius: 7px;
  transition: all 0.2s ease;
  background: #102f50 !important;
  border: 1px solid rgba(95, 153, 205, 0.18) !important;
  color: #c2d3e5 !important;
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
  text-align: left;
  white-space: normal;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0;
  overflow: visible;
  text-overflow: clip;
  line-height: 1.35;
}

.cache-tag {
  margin-left: 8px;
  flex-shrink: 0;
}

.index-btn:hover:not(:disabled) {
  transform: none;
  background: #143b60 !important;
  border-color: rgba(22, 119, 232, 0.5) !important;
  color: #f4f8fc !important;
}

.index-btn.active {
  background: #183358 !important;
  border-color: rgba(22, 119, 232, 0.5) !important;
  color: #f4f8fc !important;
  box-shadow: inset 3px 0 0 #1677e8;
}

.index-btn:disabled {
  background: #14314f !important;
  color: #4d6680 !important;
  cursor: not-allowed;
  transform: none;
}


/* 缓存管理 */
.history-card {
  padding: 14px;
  border: 1px solid #1c4265;
  border-radius: 8px;
  background: #0d2745;
}

.history-card__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.history-card__icon {
  width: 18px;
  height: 18px;
  color: #26b6e8;
}

.history-card__summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
}

.history-card__title {
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
}

.history-card__count,
.history-card__actions {
  font-size: 12px;
  color: #8299bc;
}

.history-card__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.history-text-btn,
.history-toggle-btn,
.history-delete-btn,
.history-item__main {
  font: inherit;
}

.history-text-btn,
.history-toggle-btn {
  padding: 0;
  border: none;
  background: transparent;
  color: #26b6e8;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.history-toggle-btn {
  color: #c4d4eb;
}

.history-card__description {
  margin-top: 12px;
  font-size: 12px;
  line-height: 1.7;
  color: #8299bc;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 240px;
  margin-top: 16px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: stretch;
  gap: 10px;
  padding: 10px;
  border: 1px solid #1c4265;
  border-radius: 8px;
  background: #102d4d;
}

.history-item:hover {
  border-color: #285a82;
  background: #183b61;
}

.history-item__main {
  flex: 1;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.history-item__main:hover {
  transform: none;
}

.history-item__title {
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.5;
  word-break: break-all;
}

.history-item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 6px;
  font-size: 12px;
  color: #8299bc;
}

.history-delete-btn {
  align-self: center;
  min-width: 44px;
  padding: 6px 0;
  border: none;
  background: transparent;
  color: #ffb0a5;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.history-empty {
  margin-top: 16px;
  padding: 16px 12px;
  border: 1px dashed #1c4265;
  border-radius: 8px;
  background: #102d4d;
  color: #8299bc;
  font-size: 13px;
  text-align: center;
}
</style> 
