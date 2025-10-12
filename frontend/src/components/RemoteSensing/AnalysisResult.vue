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
        <div class="result-header-apple">
          <h2 class="result-title-apple">{{ indexLabelMap[selectedIndex] }}分析结果</h2>
          <el-button type="primary" @click="downloadResults" class="download-btn-apple">
            <el-icon><Download /></el-icon>
            下载数据
          </el-button>
        </div>

        <!-- 加载中 -->
        <div v-if="loading" class="loading-data-apple">
          <el-icon class="loading-icon-small"><Loading /></el-icon>
          <span>正在加载结果数据...</span>
        </div>

        <!-- 统计数据卡片 -->
        <div v-if="indicesData.length > 0" class="statistics-section">
          <div class="stats-cards">
            <div v-for="index in indicesData" :key="index.id" class="stat-card">
              <div class="stat-card-header">
                <span class="stat-card-title">{{ getIndexDisplayName(index.index_type) }}</span>
                <el-tag :type="getIndexTagType(index.mean_value)" size="small">
                  {{ getIndexLevel(index.mean_value) }}
                </el-tag>
              </div>
              <div class="stat-card-body">
                <div class="stat-item">
                  <span class="stat-label">平均值</span>
                  <span class="stat-value">{{ formatValue(index.mean_value) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">最小值</span>
                  <span class="stat-value">{{ formatValue(index.min_value) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">最大值</span>
                  <span class="stat-value">{{ formatValue(index.max_value) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">标准差</span>
                  <span class="stat-value">{{ formatValue(index.std_value) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 图表区域 - 始终显示 -->
        <div class="charts-section">
          <!-- 面积分布饼图 -->
          <div class="chart-container">
            <h3 class="chart-title">生态质量等级面积分布</h3>
            <div ref="pieChartRef" class="chart-canvas"></div>
          </div>

          <!-- 指数对比柱状图 -->
          <div class="chart-container">
            <h3 class="chart-title">各指数平均值对比</h3>
            <div ref="barChartRef" class="chart-canvas"></div>
          </div>
        </div>

        <!-- 无数据提示 -->
        <div v-if="indicesData.length === 0 && !loading" class="no-data-apple">
          <p>暂无分析结果数据</p>
          <p class="hint-text">请等待计算完成或重新开始分析</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue';
import { ElIcon, ElButton, ElTag, ElMessage } from 'element-plus';
import { Loading, Download } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import { remoteSensingService } from '../../services/api.js';

const props = defineProps({
  status: String, // waiting | analyzing | done
  resultData: Object,
  selectedIndex: String,
  taskId: String
});

const loading = ref(false);
const indicesData = ref([]);
const pieChartRef = ref(null);
const barChartRef = ref(null);
let pieChart = null;
let barChart = null;

const indexLabelMap = computed(() => ({
  ndvi: '绿化指数 (NDVI)',
  heat: '热度指数 (LST)',
  ndwi: '湿度指数 (NDWI)',
  dryness: '干度指数 (NDBSI)',
  wetness: '湿度指数',
  greenness: '绿度指数'
}));

// 监听状态变化，当完成时加载数据
watch(() => props.status, async (newStatus) => {
  if (newStatus === 'done' && props.resultData) {
    await loadIndicesData();
  }
});

// 加载生态指数数据
async function loadIndicesData() {
  if (!props.resultData) {
    console.log('没有结果数据，无法加载指数');
    return;
  }

  loading.value = true;

  try {
    // 尝试多种方式获取影像ID
    let imageId = null;

    if (props.resultData.remote_sensing_image_id) {
      imageId = props.resultData.remote_sensing_image_id;
    } else if (props.resultData.remote_sensing_image) {
      imageId = props.resultData.remote_sensing_image.id || props.resultData.remote_sensing_image;
    }

    if (!imageId) {
      console.error('无法获取影像ID，resultData:', props.resultData);
      ElMessage.warning('无法获取影像ID');
      return;
    }

    console.log('加载影像指数数据，影像ID:', imageId);

    const response = await remoteSensingService.getIndices(imageId);
    console.log('获取到的指数数据:', response);
    console.log('响应结构:', {
      hasIndices: !!response.indices,
      indicesLength: response.indices?.length,
      indicesData: response.indices
    });

    if (response && response.indices) {
      indicesData.value = response.indices;
      console.log('设置indicesData:', indicesData.value);
      console.log('indicesData长度:', indicesData.value.length);

      // 等待DOM更新后初始化图表
      await nextTick();
      initCharts();
    } else {
      console.log('暂无指数数据，响应:', response);
      indicesData.value = [];
    }
  } catch (error) {
    console.error('加载指数数据失败:', error);
    ElMessage.error('加载分析结果失败: ' + (error.message || '未知错误'));
  } finally {
    loading.value = false;
  }
}

// 初始化图表
function initCharts() {
  console.log('开始初始化图表，数据长度:', indicesData.value.length);
  console.log('图表数据:', indicesData.value);

  // 初始化饼图
  if (pieChartRef.value) {
    console.log('初始化饼图，DOM元素:', pieChartRef.value);
    pieChart = echarts.init(pieChartRef.value);
    updatePieChart();
  } else {
    console.log('饼图DOM元素不存在');
  }

  // 初始化柱状图
  if (barChartRef.value) {
    console.log('初始化柱状图，DOM元素:', barChartRef.value);
    barChart = echarts.init(barChartRef.value);
    updateBarChart();
  } else {
    console.log('柱状图DOM元素不存在');
  }
}

// 更新饼图
function updatePieChart() {
  if (!pieChart) return;
  
  if (indicesData.value.length === 0) {
    const option = {
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 16
        }
      },
      series: []
    };
    pieChart.setOption(option);
    return;
  }

  // 使用第一个指数的面积数据（通常是主要指数）
  const firstIndex = indicesData.value[0];
  
  console.log('饼图数据 - 第一个指数:', firstIndex);
  console.log('面积字段:', {
    excellent_area: firstIndex.excellent_area,
    good_area: firstIndex.good_area,
    moderate_area: firstIndex.moderate_area,
    poor_area: firstIndex.poor_area,
    bad_area: firstIndex.bad_area
  });

  const pieData = [
    { value: firstIndex.excellent_area || 0, name: '优秀', itemStyle: { color: '#67C23A' } },
    { value: firstIndex.good_area || 0, name: '良好', itemStyle: { color: '#95D475' } },
    { value: firstIndex.moderate_area || 0, name: '中等', itemStyle: { color: '#E6A23C' } },
    { value: firstIndex.poor_area || 0, name: '较差', itemStyle: { color: '#F56C6C' } },
    { value: firstIndex.bad_area || 0, name: '差', itemStyle: { color: '#C0392B' } }
  ].filter(item => item.value > 0);
  
  console.log('过滤后的饼图数据:', pieData);

  // 如果没有面积数据，显示提示信息
  if (pieData.length === 0) {
    const option = {
      title: {
        text: '暂无面积分布数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 16
        }
      },
      series: []
    };
    pieChart.setOption(option);
    return;
  }

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} km² ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '10%',
      top: 'center',
      textStyle: {
        fontSize: 14
      }
    },
    series: [
      {
        name: '面积分布',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          fontSize: 12
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        data: pieData
      }
    ]
  };

  pieChart.setOption(option);
  console.log('饼图配置已设置，数据项数:', pieData.length);
  
  // 检查图表是否正确渲染
  setTimeout(() => {
    if (pieChart && !pieChart.isDisposed()) {
      console.log('饼图渲染状态检查:', {
        isDisposed: pieChart.isDisposed(),
        width: pieChart.getWidth(),
        height: pieChart.getHeight(),
        containerVisible: pieChartRef.value?.offsetWidth > 0 && pieChartRef.value?.offsetHeight > 0
      });
      
      // 强制重新渲染
      pieChart.resize();
    }
  }, 100);
}

// 更新柱状图
function updateBarChart() {
  if (!barChart) return;
  
  if (indicesData.value.length === 0) {
    const option = {
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 16
        }
      },
      series: []
    };
    barChart.setOption(option);
    return;
  }

  console.log('柱状图数据 - 所有指数:', indicesData.value);
  
  const categories = indicesData.value.map(item => getIndexDisplayName(item.index_type));
  const values = indicesData.value.map(item => item.mean_value || 0);
  
  console.log('柱状图分类:', categories);
  console.log('柱状图数值:', values);

  // 如果没有数据，显示提示信息
  if (values.every(v => v === 0)) {
    const option = {
      title: {
        text: '暂无指数对比数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 16
        }
      },
      series: []
    };
    barChart.setOption(option);
    return;
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const data = params[0];
        return `${data.name}<br/>平均值: ${data.value.toFixed(4)}`;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: {
        rotate: 30,
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      name: '指数值',
      axisLabel: {
        formatter: '{value}'
      }
    },
    series: [
      {
        name: '平均值',
        type: 'bar',
        data: values.map((value) => ({
          value: value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#5e9cff' },
              { offset: 1, color: '#aee2ff' }
            ])
          }
        })),
        barWidth: '60%',
        label: {
          show: true,
          position: 'top',
          formatter: '{c}',
          fontSize: 11
        }
      }
    ]
  };

  barChart.setOption(option);
  console.log('柱状图配置已设置，数据项数:', values.length);
  
  // 检查图表是否正确渲染
  setTimeout(() => {
    if (barChart && !barChart.isDisposed()) {
      console.log('柱状图渲染状态检查:', {
        isDisposed: barChart.isDisposed(),
        width: barChart.getWidth(),
        height: barChart.getHeight(),
        containerVisible: barChartRef.value?.offsetWidth > 0 && barChartRef.value?.offsetHeight > 0
      });
      
      // 强制重新渲染
      barChart.resize();
    }
  }, 100);
}

// 获取指数显示名称
function getIndexDisplayName(indexType) {
  return indexLabelMap.value[indexType] || indexType.toUpperCase();
}

// 获取指数等级
function getIndexLevel(value) {
  if (value >= 0.8) return '优秀';
  if (value >= 0.6) return '良好';
  if (value >= 0.4) return '中等';
  if (value >= 0.2) return '较差';
  return '差';
}

// 获取标签类型
function getIndexTagType(value) {
  if (value >= 0.8) return 'success';
  if (value >= 0.6) return '';
  if (value >= 0.4) return 'warning';
  return 'danger';
}

// 格式化数值
function formatValue(value) {
  if (value === null || value === undefined) return 'N/A';
  return typeof value === 'number' ? value.toFixed(4) : value;
}

// 下载结果
function downloadResults() {
  if (indicesData.value.length === 0) {
    ElMessage.warning('暂无数据可下载');
    return;
  }

  // 生成CSV数据
  const headers = ['指数类型', '平均值', '最小值', '最大值', '标准差', '优秀面积(km²)', '良好面积(km²)', '中等面积(km²)', '较差面积(km²)', '差面积(km²)'];
  const rows = indicesData.value.map(item => [
    getIndexDisplayName(item.index_type),
    formatValue(item.mean_value),
    formatValue(item.min_value),
    formatValue(item.max_value),
    formatValue(item.std_value),
    formatValue(item.excellent_area),
    formatValue(item.good_area),
    formatValue(item.moderate_area),
    formatValue(item.poor_area),
    formatValue(item.bad_area)
  ]);

  const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', `遥感生态指数分析结果_${new Date().getTime()}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  ElMessage.success('数据下载成功');
}

// 组件挂载时检查是否需要加载数据
onMounted(() => {
  if (props.status === 'done' && props.resultData) {
    loadIndicesData();
  }
});
</script>

<style scoped>
.result-panel-apple {
  width: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  background: transparent;
  padding: 0;
}

.placeholder-apple {
  color: #b0b8c9;
  font-size: 1.18rem;
  letter-spacing: 0.2px;
  text-align: center;
  padding: 80px 32px;
}

.loading-apple {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 80px 32px;
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
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.result-header-apple {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 2px solid #e9eff5;
}

.result-title-apple {
  font-size: 1.5rem;
  font-weight: 600;
  color: #222;
  margin: 0;
  letter-spacing: 0.3px;
}

.download-btn-apple {
  border-radius: 12px;
  padding: 10px 20px;
  font-weight: 500;
}

.loading-data-apple {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #606266;
  font-size: 1rem;
}

.loading-icon-small {
  font-size: 24px;
  color: #5e9cff;
  animation: apple-spin 1.2s linear infinite;
}

/* 统计卡片 */
.statistics-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(60, 60, 60, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(60, 60, 60, 0.12);
}

.stat-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e9eff5;
}

.stat-card-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #303133;
}

.stat-card-body {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.85rem;
  color: #909399;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #303133;
}

/* 图表区域 */
.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
  margin-top: 8px;
}

.chart-container {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(60, 60, 60, 0.08);
}

.chart-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px 0;
  text-align: center;
}

.chart-canvas {
  width: 100%;
  height: 350px;
}

/* 无数据提示 */
.no-data-apple {
  text-align: center;
  padding: 60px 32px;
  color: #909399;
}

.no-data-apple p {
  margin: 8px 0;
  font-size: 1.1rem;
}

.hint-text {
  font-size: 0.95rem;
  color: #b0b8c9;
}

/* 响应式设计 */
@media (max-width: 900px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }

  .charts-section {
    grid-template-columns: 1fr;
  }

  .chart-canvas {
    height: 300px;
  }
}
</style>