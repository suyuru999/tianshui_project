<template>
  <div class="sidebar-panel-apple">
    <h3 class="sidebar-title-apple">
      <el-icon class="sidebar-title-icon"><Upload /></el-icon>
      <span>遥感影像分析</span>
    </h3>
    <div class="desc-apple">上传遥感影像数据，系统将自动提取多种生态指数并进行可视化。</div>
    <div class="upload-card-apple">
      <input 
        ref="fileInput" 
        type="file" 
        accept=".tif,.tiff,.jpg,.jpeg,.png" 
        style="display: none"
        @change="handleFileChange"
      >
      <el-button class="apple-btn" type="primary" @click="triggerFileUpload">
        上传影像数据
      </el-button>
      <div v-if="fileName" class="file-name-apple">{{ fileName }}</div>
      <div v-else class="file-tip-apple">未选择文件</div>
    </div>
    <el-button
      class="apple-btn main-btn"
      type="primary"
      :disabled="!fileName || uploading"
      @click="$emit('start-analysis')"
    >
      开始分析
    </el-button>
    <div class="group-title-apple">图层选择</div>
    <el-radio-group v-model="localIndex" @change="onIndexChange" class="radio-group-apple">
      <el-radio class="apple-radio" value="ndvi">绿化指数 (NDVI)</el-radio>
      <el-radio class="apple-radio" value="heat">热度指数 (LST)</el-radio>
      <el-radio class="apple-radio" value="ndwi">湿度指数 (NDWI)</el-radio>
      <el-radio class="apple-radio" value="dryness">干度指数 (NDBSI)</el-radio>
    </el-radio-group>
  
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { ElIcon, ElButton, ElRadioGroup, ElRadio } from 'element-plus';
import { Upload } from '@element-plus/icons-vue';

const props = defineProps({
  selectedIndex: String,
  fileName: String,
  uploading: Boolean
});
const emit = defineEmits(['file-change', 'start-analysis', 'index-change']);

const localIndex = ref(props.selectedIndex || 'NDVI');
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
  emit('index-change', val);
}
</script>

<style scoped>
.sidebar-panel-apple {
  display: flex;
  flex-direction: column;
  gap: 32px;
  background: transparent;
  height: 100%;
  overflow-y: auto;
}

/* 自定义滚动条样式 */
.sidebar-panel-apple::-webkit-scrollbar {
  width: 6px;
}

.sidebar-panel-apple::-webkit-scrollbar-track {
  background: rgba(241, 245, 249, 0.3);
  border-radius: 3px;
}

.sidebar-panel-apple::-webkit-scrollbar-thumb {
  background: rgba(203, 213, 225, 0.6);
  border-radius: 3px;
  transition: background 0.2s ease;
}

.sidebar-panel-apple::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.8);
}

.sidebar-title-apple {
  display: flex;
  align-items: center;
  font-size: 1.5rem;
  font-weight: 600;
  color: #222;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
  gap: 10px;
}
.sidebar-title-icon {
  font-size: 1.6rem;
  color: #5e9cff;
  background: linear-gradient(135deg, #e0eaff 0%, #f8fafc 100%);
  border-radius: 50%;
  padding: 6px;
}
.desc-apple {
  color: #6b7280;
  font-size: 1.05rem;
  margin-bottom: 8px;
  line-height: 1.6;
}
.upload-card-apple {
  background: rgba(255,255,255,0.95);
  border-radius: 18px;
  box-shadow: 0 2px 8px 0 rgba(60,60,60,0.06);
  padding: 24px 18px 12px 18px;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  align-items: center; /* 居中内容 */
  justify-content: center;
}
.upload-demo {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.el-upload {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.file-name-apple {
  color: #222;
  font-size: 1rem;
  margin-top: 8px;
  text-align: center;
}
.file-tip-apple {
  color: #b0b8c9;
  font-size: 0.98rem;
  margin-top: 8px;
  text-align: center;
}
.apple-btn {
  width: 80%;
  min-width: 160px;
  max-width: 260px;
  margin: 0 auto 12px auto;
  display: block;
  border-radius: 16px !important;
  font-size: 1.08rem;
  font-weight: 500;
  background: linear-gradient(90deg, #e0eaff 0%, #f8fafc 100%);
  color: #2563eb;
  border: none;
  box-shadow: 0 2px 8px 0 rgba(60,60,60,0.04);
  transition: background 0.2s, color 0.2s;
}
.apple-btn.main-btn {
  background: linear-gradient(90deg, #5e9cff 0%, #aee2ff 100%);
  color: #fff;
  font-weight: 600;
  margin-bottom: 18px;
}
.apple-btn:active {
  background: #e0eaff;
}
.group-title-apple {
  font-size: 1.1rem;
  font-weight: 500;
  color: #222;
  margin-bottom: 8px;
  margin-top: 8px;
  letter-spacing: 0.2px;
}
.radio-group-apple {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.apple-radio {
  border-radius: 12px;
  padding: 8px 16px;
  font-size: 1.05rem;
  color: #2563eb;
  background: rgba(94,156,255,0.07);
  margin-bottom: 4px;
  transition: background 0.2s, color 0.2s;
}
 

.apple-radio.is-checked {
  background: linear-gradient(90deg, #5e9cff 0%, #aee2ff 100%);
  color: #fff;
}
</style> 