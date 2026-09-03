<template>
  <div class="loading-spinner" :class="[`loading-${type}`, { 'loading-overlay': overlay }]">
    <!-- 默认加载动画 -->
    <div v-if="type === 'default'" class="spinner-default">
      <div class="spinner-circle"></div>
      <div class="spinner-text">{{ text }}</div>
    </div>
    
    <!-- 脉冲加载动画 -->
    <div v-else-if="type === 'pulse'" class="spinner-pulse">
      <div class="pulse-dot"></div>
      <div class="pulse-dot"></div>
      <div class="pulse-dot"></div>
      <div class="spinner-text">{{ text }}</div>
    </div>
    
    <!-- 旋转加载动画 -->
    <div v-else-if="type === 'rotate'" class="spinner-rotate">
      <div class="rotate-circle"></div>
      <div class="spinner-text">{{ text }}</div>
    </div>
    
    <!-- 进度条加载 -->
    <div v-else-if="type === 'progress'" class="spinner-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
      </div>
      <div class="spinner-text">{{ text }} {{ progress }}%</div>
    </div>
    
    <!-- 骨架屏加载 -->
    <div v-else-if="type === 'skeleton'" class="spinner-skeleton">
      <div class="skeleton-item" v-for="i in skeletonCount" :key="i"></div>
      <div class="spinner-text">{{ text }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // 加载类型：default, pulse, rotate, progress, skeleton
  type: {
    type: String,
    default: 'default'
  },
  // 加载文本
  text: {
    type: String,
    default: '加载中...'
  },
  // 是否为遮罩层
  overlay: {
    type: Boolean,
    default: false
  },
  // 进度值（0-100）
  progress: {
    type: Number,
    default: 0
  },
  // 骨架屏项目数量
  skeletonCount: {
    type: Number,
    default: 3
  }
})

// 计算进度值
const computedProgress = computed(() => {
  return Math.max(0, Math.min(100, props.progress))
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(8, 23, 43, 0.82);
  z-index: 9999;
}

/* 默认加载动画 */
.spinner-default {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner-circle {
  width: 40px;
  height: 40px;
  border: 4px solid #203b60;
  border-top: 4px solid #1677ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 脉冲加载动画 */
.spinner-pulse {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.pulse-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #1677ff;
  animation: pulse 1.4s ease-in-out infinite both;
}

.pulse-dot:nth-child(1) { animation-delay: -0.32s; }
.pulse-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes pulse {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* 旋转加载动画 */
.spinner-rotate {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.rotate-circle {
  width: 50px;
  height: 50px;
  border: 3px solid transparent;
  border-top: 3px solid #1677ff;
  border-right: 3px solid #1677ff;
  border-radius: 50%;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 进度条加载 */
.spinner-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  width: 200px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #0f223d;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #1677ff;
  border-radius: 4px;
  transition: width 0.3s ease;
}

/* 骨架屏加载 */
.spinner-skeleton {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  width: 200px;
}

.skeleton-item {
  width: 100%;
  height: 20px;
  background: #183358;
  border-radius: 4px;
  animation: skeleton-loading 1.5s infinite;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 加载文本 */
.spinner-text {
  color: #c4d4eb;
  font-size: 14px;
  text-align: center;
  user-select: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .loading-spinner {
    padding: 16px;
  }
  
  .spinner-progress,
  .spinner-skeleton {
    width: 150px;
  }
  
  .spinner-circle,
  .rotate-circle {
    width: 32px;
    height: 32px;
  }
  
  .pulse-dot {
    width: 10px;
    height: 10px;
  }
}
</style>
