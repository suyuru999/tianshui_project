<template>
  <div class="overlay-analysis">
    <!-- 右侧地图区域 -->
    <div class="map-area">
      <OverlayMapContainer />
    </div>
  </div>
</template>

<script setup>
import OverlayMapContainer from '../components/Map/OverlayMapContainer.vue'
</script>

<style scoped>
.overlay-analysis {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.map-area {
  flex: 1;
  position: relative;
  background: #f5f5f5;
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

/* 自定义滚动条样式 */
.map-area::-webkit-scrollbar {
  width: 6px;
}

.map-area::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.map-area::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.map-area::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
