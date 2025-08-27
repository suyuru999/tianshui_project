<template>
  <div class="layer-manager">
    <h3>图层管理</h3>
    
    <!-- 底图图层 -->
    <div class="layer-section">
      <h4>底图图层</h4>
      <ul class="layer-list">
        <li v-for="layer in baseMaps" :key="layer.id" class="layer-item">
          <label class="layer-label">
            <input 
              type="checkbox" 
              :checked="layer.visible"
              @change="toggleBaseMapVisibility(layer.id)"
            />
            <span class="layer-name">{{ layer.name }}</span>
          </label>
        </li>
      </ul>
    </div>

    <!-- 业务图层 -->
    <div class="layer-section">
      <h4>业务图层 ({{ businessLayers.length }})</h4>
      <ul class="layer-list">
        <li v-for="layer in businessLayers" :key="layer.id" class="layer-item">
          <label class="layer-label">
            <input 
              type="checkbox" 
              :checked="layer.visible"
              @change="toggleBusinessLayerVisibility(layer.id)"
            />
            <span class="layer-name">{{ layer.name }}</span>
            <span class="layer-type">[{{ layer.type }}]</span>
          </label>
          <button 
            class="remove-btn"
            @click="removeBusinessLayer(layer.id)"
            title="删除图层"
          >
            ×
          </button>
        </li>
      </ul>
      
      <div v-if="businessLayers.length === 0" class="empty-tip">
        暂无业务图层
      </div>
    </div>
  </div>
</template>

<script setup>
import { useMapStore } from '../../store/map'

const mapStore = useMapStore()
const { 
  baseMaps, 
  businessLayers, 
  toggleLayerVisibility, 
  removeBusinessLayer: storeRemoveBusinessLayer 
} = mapStore

// 切换底图可见性
const toggleBaseMapVisibility = (layerId) => {
  toggleLayerVisibility(layerId, false)
}

// 切换业务图层可见性
const toggleBusinessLayerVisibility = (layerId) => {
  toggleLayerVisibility(layerId, true)
}

// 删除业务图层
const removeBusinessLayer = (layerId) => {
  if (confirm('确定要删除这个图层吗？')) {
    storeRemoveBusinessLayer(layerId)
  }
}
</script>

<style scoped>
.layer-manager {
  position: absolute;
  top: 20px;
  right: 20px;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  padding: 16px;
  min-width: 250px;
  max-width: 300px;
  z-index: 10;
  max-height: 80vh;
  overflow-y: auto;
}

.layer-manager h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}

.layer-section {
  margin-bottom: 16px;
}

.layer-section h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #666;
  font-weight: normal;
}

.layer-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.layer-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
  border-bottom: 1px solid #f5f5f5;
}

.layer-item:last-child {
  border-bottom: none;
}

.layer-label {
  display: flex;
  align-items: center;
  flex: 1;
  cursor: pointer;
}

.layer-label input[type="checkbox"] {
  margin-right: 8px;
}

.layer-name {
  font-size: 13px;
  color: #333;
  flex: 1;
}

.layer-type {
  font-size: 11px;
  color: #999;
  margin-left: 4px;
}

.remove-btn {
  background: #ff4d4f;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  margin-left: 8px;
  transition: background 0.2s;
}

.remove-btn:hover {
  background: #ff7875;
}

.empty-tip {
  text-align: center;
  color: #999;
  font-size: 12px;
  padding: 16px 0;
}
</style> 