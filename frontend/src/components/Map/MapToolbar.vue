<template>
  <div class="map-toolbar">
    <div class="tool-group">
      <button 
        class="tool-btn"
        @click="zoomIn"
        title="放大"
      >
        +
      </button>
      <button 
        class="tool-btn"
        @click="zoomOut"
        title="缩小"
      >
        -
      </button>
    </div>
    
    <div class="tool-group">
      <button 
        class="tool-btn"
        @click="resetView"
        title="复位"
      >
        ⌂
      </button>
      <button 
        class="tool-btn"
        @click="toggleFullscreen"
        title="全屏"
      >
        ⛶
      </button>
    </div>
    
    <div class="tool-group">
      <button 
        class="tool-btn"
        @click="exportMap"
        title="导出地图"
      >
        📷
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['zoomIn', 'zoomOut', 'resetView', 'toggleFullscreen', 'exportMap'])

// 放大
const zoomIn = () => {
  emit('zoomIn')
}

// 缩小
const zoomOut = () => {
  emit('zoomOut')
}

// 复位视图
const resetView = () => {
  emit('resetView')
}

// 切换全屏
const toggleFullscreen = () => {
  emit('toggleFullscreen')
}

// 导出地图
const exportMap = () => {
  emit('exportMap')
}
</script>

<style scoped>
.map-toolbar {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.9);
  border-radius: 6px;
  padding: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 1000;
  display: flex;
  gap: 8px;
}

.tool-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tool-group:not(:last-child) {
  border-right: 1px solid #eee;
  padding-right: 8px;
}

.tool-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.tool-btn:hover {
  background: #f5f5f5;
  border-color: #1890ff;
}

.tool-btn:active {
  background: #e6f7ff;
}
</style> 