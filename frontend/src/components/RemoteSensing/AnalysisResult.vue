<template>
  <div class="result-panel-apple">
    <template v-if="status === 'waiting'">
      <div class="placeholder-apple">请先上传数据并开始分析</div>
    </template>
    <template v-else-if="status === 'analyzing'">
      <div class="loading-apple">
        <el-icon class="loading-icon-apple"><Loading /></el-icon>
        <span class="loading-text-apple">正在分析，请稍候...</span>
      </div>
    </template>
    <template v-else-if="status === 'done'">
      <div class="result-content-apple">
        <div class="result-title-apple">{{ indexLabelMap[selectedIndex] }}分析结果</div>
        <!-- 这里可插入ECharts或图片等可视化内容 -->
        <div class="result-msg-apple">{{ resultData?.msg || '（此处展示分析结果）' }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { ElIcon } from 'element-plus';
import { Loading } from '@element-plus/icons-vue';

const props = defineProps({
  status: String, // waiting | analyzing | done
  resultData: Object,
  selectedIndex: String
});

const indexLabelMap = computed(() => ({
  NDVI: '绿化指数 (NDVI)',
  LST: '热度指数 (LST)',
  NDWI: '湿度指数',
  NDBSI: '干度指数'
}));
</script>

<style scoped>
.result-panel-apple {
  width: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f8fafc 0%, #e9eff5 100%);
  border-radius: 28px;
  box-shadow: 0 4px 24px 0 rgba(60,60,60,0.07);
  padding: 36px 32px;
  transition: box-shadow 0.2s;
}
.placeholder-apple {
  color: #b0b8c9;
  font-size: 1.18rem;
  letter-spacing: 0.2px;
  text-align: center;
  padding: 32px 0;
}
.loading-apple {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px 0;
}
.loading-icon-apple {
  font-size: 48px;
  color: #5e9cff;
  animation: apple-spin 1.2s linear infinite;
}
@keyframes apple-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
.loading-text-apple {
  color: #2563eb;
  font-size: 1.15rem;
  font-weight: 500;
  letter-spacing: 0.2px;
}
.result-content-apple {
  background: rgba(255,255,255,0.98);
  border-radius: 20px;
  box-shadow: 0 2px 8px 0 rgba(60,60,60,0.06);
  padding: 32px 24px;
  min-width: 320px;
  max-width: 520px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}
.result-title-apple {
  font-size: 1.25rem;
  font-weight: 600;
  color: #222;
  margin-bottom: 8px;
  letter-spacing: 0.2px;
}
.result-msg-apple {
  color: #2563eb;
  font-size: 1.08rem;
  text-align: center;
  word-break: break-all;
}
</style> 