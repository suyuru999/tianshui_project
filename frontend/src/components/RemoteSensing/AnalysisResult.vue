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
          <h2 class="result-title-apple">{{ resultTitle }}分析结果</h2>
          <div class="result-download-actions">
            <el-button type="primary" @click="downloadResults" class="result-download-btn">
              <el-icon><Download /></el-icon>
              下载计算结果
            </el-button>
          </div>
        </div>

        <div v-if="resultData?.preview_mode || resultData?.preview_message" class="result-notice is-preview">
          <div class="notice-title">当前为大文件预览分析</div>
          <div class="notice-text">{{ resultData?.preview_message || '系统已自动切换为预览模式。' }}</div>
        </div>

        <div v-if="primaryVisualizationUrl" class="visualization-section">
          <div class="visualization-header">
            <div class="visualization-title-block">
              <h3>{{ resultTitle }}分布图</h3>
              <span>{{ sourceFileName }}</span>
            </div>
          </div>
          <div class="visualization-map-body">
            <div class="visualization-image-frame">
              <img
                :src="primaryVisualizationUrl"
                alt="指数可视化结果"
                class="visualization-image"
                @error="handleVisualizationError"
              />
            </div>
            <div class="map-side-controls">
              <div class="map-legend-panel" aria-label="生态质量图例">
                <div class="legend-title">图例</div>
                <div v-for="item in qualityLegendItems" :key="item.name" class="legend-row">
                  <span class="legend-swatch" :style="{ backgroundColor: item.color }"></span>
                  <span class="legend-name">{{ item.name }}</span>
                </div>
              </div>
              <div class="result-image-actions map-edge-actions">
                <el-button type="primary" @click="addCurrentResultToMainMap" class="result-download-btn image-download-btn map-add-btn">
                  添加图层
                </el-button>
                <el-button v-if="primaryVisualizationUrl" type="primary" @click="downloadVisualization" class="result-download-btn image-download-btn image-secondary-btn">
                  <el-icon><Download /></el-icon>
                  图片
                </el-button>
                <el-button v-if="primaryResultFileUrl" type="primary" @click="downloadResultRaster" class="result-download-btn image-download-btn image-secondary-btn">
                  <el-icon><Download /></el-icon>
                  TIF
                </el-button>
              </div>
            </div>
          </div>
        </div>
        <div v-if="visualizationLoadError" class="result-notice is-warning">
          <div class="notice-title">可视化图片加载失败</div>
          <div class="notice-text">{{ visualizationLoadError }}</div>
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

          <!-- 统计值数值解读 -->
          <div class="chart-container">
            <h3 class="chart-title">统计值数值解读</h3>
            <div class="interpretation-content">
              <div v-if="indicesData.length > 0" class="interpretation-text">
                <div v-for="index in indicesData" :key="index.id" class="index-interpretation">
                  <h4 class="index-name">{{ getIndexDisplayName(index.index_type) }}</h4>
                  <div class="interpretation-items">
                    <div class="interpretation-item">
                      <span class="item-label">平均值解读：</span>
                      <span class="item-content">{{ getMeanInterpretation(index) }}</span>
                    </div>
                    <div class="interpretation-item">
                      <span class="item-label">数值范围：</span>
                      <span class="item-content">{{ getRangeInterpretation(index) }}</span>
                    </div>
                    <div class="interpretation-item">
                      <span class="item-label">变化程度：</span>
                      <span class="item-content">{{ getVariationInterpretation(index) }}</span>
                    </div>
                    <div class="interpretation-item">
                      <span class="item-label">生态意义：</span>
                      <span class="item-content">{{ getEcologicalMeaning(index) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="no-data-text">
                <p>暂无分析结果数据</p>
                <p class="hint-text">请等待计算完成或重新开始分析</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 无数据提示 -->
        <div v-if="indicesData.length === 0 && !loading" class="no-data-apple">
          <p>暂无分析结果数据</p>
          <p class="hint-text">请等待计算完成或重新开始分析</p>
        </div>

        <ResultCompareMap
          title="遥感结果叠加对比"
          description="打开遥感影像底图后，可直接把当前彩色分析结果叠加在上面做对比。"
          :compare-overlay="primaryCompareOverlay"
          empty-text="当前指数结果暂未生成叠加图，请重新分析该指数后再查看。"
        />
      </div>
    </template>
    <template v-else-if="status === 'error'">
      <div class="error-state-card">
        <h3 class="error-title">分析未完成</h3>
        <p class="error-message">{{ resultData?.error || '发生未知错误' }}</p>
        <p v-if="resultData?.details" class="error-details">{{ resultData.details }}</p>
        <div v-if="resultData?.supported_index_labels?.length" class="error-supported">
          建议改用：{{ resultData.supported_index_labels.join('、') }}
        </div>
        <div v-if="resultData?.bands_count" class="error-meta">
          当前识别波段数：{{ resultData.bands_count }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { ElIcon, ElButton, ElTag, ElMessage } from 'element-plus';
import { Loading, Download } from '@element-plus/icons-vue';
import { useRouter } from 'vue-router';
import * as echarts from 'echarts';
import { remoteSensingService } from '../../services/api.js';
import ResultCompareMap from '../Map/ResultCompareMap.vue';
import { saveMainMapAnalysisLayer } from '../../utils/mainMapAnalysisLayers.js';
import { saveBlobAsFile, saveUrlAsFile } from '../../utils/fileSave.js';

const props = defineProps({
  status: String, // waiting | analyzing | done
  resultData: Object,
  selectedIndex: String,
  taskId: String
});

const loading = ref(false);
const router = useRouter();
const indicesData = ref([]);
const pieChartRef = ref(null);
const visualizationLoadError = ref('');
let pieChart = null;
let removeResizeListener = null;

const indexLabelMap = computed(() => ({
  ndvi: '绿化指数 (NDVI)',
  heat: '热度指数 (LST)',
  ndwi: '湿度指数 (NDWI)',
  ndbi: '建筑指数 (NDBI)',
  dryness: '干度指数 (NDBSI)',
  wetness: '湿度指数',
  greenness: '绿度指数',
  rsei: 'RSEI',
  uploaded_raster: '上传成果栅格'
}));

const qualityLegendItems = [
  { name: '优秀', color: '#5cc53a' },
  { name: '良好', color: '#91d36c' },
  { name: '中等', color: '#f0ab2f' },
  { name: '较差', color: '#ff6868' },
  { name: '差', color: '#c93422' }
];

const selectedIndexKey = computed(() => String(props.selectedIndex || '').toLowerCase());

const selectedResultKey = computed(() => {
  const aliasMap = {
    lst: 'heat',
    ndbsi: 'dryness'
  };
  return aliasMap[selectedIndexKey.value] || selectedIndexKey.value;
});

const primaryIndex = computed(() => {
  if (!indicesData.value.length) return null;
  return indicesData.value.find((item) => String(item.index_type || '').toLowerCase() === selectedResultKey.value)
    || indicesData.value[0];
});

const resultTitle = computed(() => {
  const primaryType = primaryIndex.value?.index_type;
  return indexLabelMap.value[primaryType] || indexLabelMap.value[props.selectedIndex] || '遥感生态指数';
});

const primaryVisualizationUrl = computed(() => {
  const primary = primaryIndex.value;
  return normalizeVisualizationUrl(
    primary?.visualization_file_url
    || primary?.visualization_file
    || props.resultData?.visualization_file_url
    || props.resultData?.result?.visualization_file_url
    || props.resultData?.visualization_file
    || null
  );
});

const primaryResultFileUrl = computed(() => {
  const primary = primaryIndex.value;
  return normalizeVisualizationUrl(
    primary?.result_file_url
    || primary?.result_file
    || primary?.compare_overlay?.result_file_url
    || props.resultData?.result_file_url
    || props.resultData?.result?.result_file_url
    || props.resultData?.compare_overlay?.result_file_url
    || props.resultData?.result?.compare_overlay?.result_file_url
    || props.resultData?.result_file
    || null
  );
});

const primaryCompareOverlay = computed(() => {
  const primary = primaryIndex.value;
  return primary?.compare_overlay || props.resultData?.compare_overlay || props.resultData?.result?.compare_overlay || null;
});

const sourceFileName = computed(() => (
  props.resultData?.filename
  || props.resultData?.remote_sensing_image_name
  || props.resultData?.source_filename
  || primaryCompareOverlay.value?.source_filename
  || '遥感生态指数结果'
));

function isUuidLike(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || '').trim());
}

function normalizeVisualizationUrl(url) {
  if (!url || typeof url !== 'string') return null;

  if (url.startsWith('/media/')) {
    return url;
  }

  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.pathname.startsWith('/media/')) {
      return `${parsed.pathname}${parsed.search}${parsed.hash}`;
    }
    return parsed.toString();
  } catch (error) {
    console.warn('解析可视化图片地址失败:', url, error);
    return url;
  }
}

// 监听状态变化，当完成时加载数据
watch(() => props.status, async (newStatus) => {
  if (newStatus === 'done' && props.resultData) {
    await loadIndicesData();
  }
});

watch(() => props.resultData, async (newResultData) => {
  if (props.status === 'done' && newResultData) {
    await loadIndicesData();
  }
});

// 加载生态指数数据
async function loadIndicesData() {
  if (!props.resultData) {
    return;
  }

  loading.value = true;
  visualizationLoadError.value = '';

  try {
    if (Array.isArray(props.resultData.indices) && props.resultData.indices.length > 0) {
      indicesData.value = props.resultData.indices;
      await nextTick();
      initCharts();
      return;
    }

    // 尝试多种方式获取影像ID
    let imageId = null;

    if (props.resultData.remote_sensing_image_id) {
      imageId = props.resultData.remote_sensing_image_id;
    } else if (props.resultData.remote_sensing_image) {
      imageId = props.resultData.remote_sensing_image.id || props.resultData.remote_sensing_image;
    }

    if (!isUuidLike(imageId)) {
      indicesData.value = [];
      return;
    }

    const response = await remoteSensingService.getIndices(imageId, { silentError: true });

    if (response && response.indices) {
      indicesData.value = response.indices;

      // 等待DOM更新后初始化图表
      await nextTick();
      initCharts();
    } else {
      indicesData.value = Array.isArray(props.resultData.indices) ? props.resultData.indices : [];
    }
  } catch (error) {
    if (Array.isArray(props.resultData.indices)) {
      indicesData.value = props.resultData.indices;
      await nextTick();
      initCharts();
    } else {
      ElMessage.error('加载分析结果失败: ' + (error.message || '未知错误'));
    }
  } finally {
    loading.value = false;
  }
}

// 初始化图表
function initCharts() {
  // 初始化饼图
  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value);
    updatePieChart();

    // 监听窗口尺寸变化，带防抖，动态调整图例布局，避免与右侧面板遮挡
    const debounce = (fn, delay = 200) => {
      let timer = null;
      return (...args) => {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
      };
    };

    const onResize = debounce(() => {
      if (!pieChart || pieChart.isDisposed()) return;
      pieChart.resize();
      updatePieChart();
    }, 150);

    window.addEventListener('resize', onResize);
    removeResizeListener = () => window.removeEventListener('resize', onResize);
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
  const firstIndex = primaryIndex.value;
  if (!firstIndex) {
    pieChart.setOption({ series: [] });
    return;
  }

  const pieData = [
    { value: firstIndex.excellent_area || 0, name: '优秀', itemStyle: { color: '#67C23A' } },
    { value: firstIndex.good_area || 0, name: '良好', itemStyle: { color: '#95D475' } },
    { value: firstIndex.moderate_area || 0, name: '中等', itemStyle: { color: '#E6A23C' } },
    { value: firstIndex.poor_area || 0, name: '较差', itemStyle: { color: '#F56C6C' } },
    { value: firstIndex.bad_area || 0, name: '差', itemStyle: { color: '#C0392B' } }
  ].filter(item => item.value > 0);

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

  const chartWidth = pieChart.getWidth();
  const isWide = chartWidth >= 520; // 两栏卡片内也优先把图例放右侧，减少底部留白

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} km² ({d}%)'
    },
    legend: isWide
      ? {
          orient: 'vertical',
          right: '4%',
          top: 'middle',
          itemWidth: 12,
          itemHeight: 8,
          itemGap: 10,
          textStyle: { color: '#395875', fontSize: 12 }
        }
      : {
          type: 'scroll',
          orient: 'horizontal',
          bottom: 0,
          left: 'center',
          itemWidth: 12,
          itemHeight: 8,
          itemGap: 10,
          textStyle: { color: '#395875', fontSize: 12 },
          pageIconColor: '#409EFF'
        },
    series: [
      {
        name: '面积分布',
        type: 'pie',
        radius: isWide ? ['36%', '60%'] : ['36%', '58%'],
        center: isWide ? ['39%', '50%'] : ['50%', '46%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          color: '#395875',
          fontSize: 11
        },
        labelLine: {
          length: 12,
          length2: 10,
          smooth: true
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 13,
            fontWeight: 'bold'
          }
        },
        data: pieData
      }
    ]
  };

  pieChart.setOption(option);
}


// 获取指数显示名称
function getIndexDisplayName(indexType) {
  return indexLabelMap.value[indexType] || indexType.toUpperCase();
}

// 获取平均值解读
function getMeanInterpretation(index) {
  const mean = index.mean_value || 0;
  const indexType = index.index_type;
  
  switch (indexType) {
    case 'dryness':
      if (mean < -5000) return '区域整体偏向湿润，植被覆盖良好，生态质量较高';
      else if (mean < 0) return '区域整体湿润，植被覆盖较好，生态质量中等偏上';
      else if (mean < 2000) return '区域干湿适中，植被与建筑用地并存';
      else return '区域整体偏向干燥，建筑用地较多，生态质量需要改善';
    
    case 'heat':
      if (mean < -5000) return '区域温度较低，植被覆盖良好，热岛效应不明显';
      else if (mean < 0) return '区域温度适中，植被覆盖较好，热环境良好';
      else if (mean < 2000) return '区域温度偏高，存在一定热岛效应';
      else return '区域温度较高，热岛效应明显，需要增加绿化';
    
    case 'ndvi':
      if (mean > 0.6) return '区域植被覆盖极好，生态质量优秀';
      else if (mean > 0.3) return '区域植被覆盖良好，生态质量较好';
      else if (mean > 0.1) return '区域植被覆盖一般，生态质量中等';
      else return '区域植被覆盖较差，生态质量需要改善';
    
    case 'ndwi':
      if (mean > 0.3) return '区域水体丰富，湿度较高，生态环境良好';
      else if (mean > 0.1) return '区域湿度适中，水体分布合理';
      else if (mean > -0.1) return '区域湿度一般，水体分布较少';
      else return '区域湿度较低，水体缺乏，需要增加水体';
    
    case 'wetness':
      if (mean > 1000) return '区域湿度很高，植被和水体丰富，生态质量优秀';
      else if (mean > 0) return '区域湿度较高，植被覆盖良好，生态质量较好';
      else if (mean > -1000) return '区域湿度适中，生态质量中等';
      else return '区域湿度较低，生态质量需要改善';
    
    default:
      return '数值分析需要结合具体指数类型进行解读';
  }
}

// 获取数值范围解读
function getRangeInterpretation(index) {
  const min = index.min_value || 0;
  const max = index.max_value || 0;
  const range = max - min;
  
  if (range > 30000) return '数值变化极大，区域内部差异显著，空间异质性很强';
  else if (range > 10000) return '数值变化较大，区域内部存在明显差异，空间异质性较强';
  else if (range > 5000) return '数值变化适中，区域内部有一定差异，空间异质性中等';
  else return '数值变化较小，区域内部相对均匀，空间异质性较弱';
}

// 获取变化程度解读
function getVariationInterpretation(index) {
  const std = index.std_value || 0;
  const min = index.min_value || 0;
  const max = index.max_value || 0;
  const range = max - min;
  
  // 基于标准差和数值范围的变化程度评估
  if (std > 10000) return '标准差极大，数据变化剧烈，空间分布极不均匀，存在显著的空间差异';
  else if (std > 5000) return '标准差较大，数据变化明显，空间分布不均匀，存在较大的空间差异';
  else if (std > 2000) return '标准差中等，数据变化适中，空间分布相对均匀，存在一定的空间差异';
  else if (std > 500) return '标准差较小，数据变化平缓，空间分布较为均匀，空间差异较小';
  else return '标准差很小，数据变化微弱，空间分布非常均匀，空间差异很小';
}

// 获取生态意义解读
function getEcologicalMeaning(index) {
  const indexType = index.index_type;
  const mean = index.mean_value || 0;
  
  switch (indexType) {
    case 'dryness':
      if (mean < -5000) return '建议加强植被保护，维持现有生态优势，可适当发展生态旅游';
      else if (mean < 0) return '建议适度增加绿化，平衡发展与生态保护，提升生态质量';
      else return '建议大力增加绿化覆盖，减少建筑密度，改善生态环境';
    
    case 'heat':
      if (mean < -5000) return '建议保持现有植被覆盖，避免过度开发，维持良好的热环境';
      else if (mean < 0) return '建议适度增加绿化，减少热岛效应，改善城市热环境';
      else return '建议增加绿化面积，建设生态廊道，缓解热岛效应';
    
    case 'ndvi':
      if (mean > 0.6) return '建议保护现有植被，建立生态保护区，维持生态优势';
      else if (mean > 0.3) return '建议适度增加植被覆盖，提升生态质量，建设生态城市';
      else return '建议大力植树造林，增加绿化面积，改善生态环境';
    
    case 'ndwi':
      if (mean > 0.3) return '建议保护现有水体，维持湿地生态，发展生态旅游';
      else if (mean > 0.1) return '建议适度增加水体面积，提升生态多样性';
      else return '建议建设人工水体，增加湿地面积，改善生态环境';
    
    case 'wetness':
      if (mean > 1000) return '建议保护现有湿地和植被，维持生态优势，发展生态产业';
      else if (mean > 0) return '建议适度增加湿地面积，提升生态质量';
      else return '建议增加水体面积，改善土壤湿度，提升生态质量';
    
    default:
      return '建议根据具体指数类型制定相应的生态保护和管理策略';
  }
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
  if (value >= 0.6) return 'info';
  if (value >= 0.4) return 'warning';
  return 'danger';
}

// 格式化数值
function formatValue(value) {
  if (value === null || value === undefined) return 'N/A';
  return typeof value === 'number' ? value.toFixed(4) : value;
}

function handleVisualizationError(event) {
  const failedUrl = event?.target?.currentSrc || event?.target?.src || primaryVisualizationUrl.value || '';
  console.error('可视化图片加载失败:', failedUrl);
  if (failedUrl && failedUrl.includes('/media/')) {
    visualizationLoadError.value = '结果图片文件已不存在，通常是旧缓存或后台结果文件已被清理。请重新分析，或删除这条历史记录后再生成。';
    return;
  }

  visualizationLoadError.value = failedUrl
    ? `图片地址无法访问：${failedUrl}`
    : '图片地址为空或服务未返回有效文件。';
}

function buildDownloadName(extension) {
  const label = resultTitle.value || indexLabelMap.value[props.selectedIndex] || props.selectedIndex || '遥感生态指数';
  const safeLabel = String(label).replace(/[\\/:*?"<>|()\s]+/g, '_').replace(/^_+|_+$/g, '') || 'remote_sensing_result';
  return `${safeLabel}_${new Date().getTime()}.${extension}`;
}

async function downloadVisualization() {
  try {
    await saveUrlAsFile(primaryVisualizationUrl.value, buildDownloadName('png'), 'image/png');
    ElMessage.success('结果图片已下载');
  } catch (error) {
    if (error?.name === 'AbortError') return;
    console.error('下载结果图片失败:', error);
    ElMessage.error('下载结果图片失败，请确认结果图片仍然可访问');
  }
}

async function downloadResultRaster() {
  try {
    await saveUrlAsFile(primaryResultFileUrl.value, buildDownloadName('tif'), 'image/tiff');
    ElMessage.success('结果tif已下载');
  } catch (error) {
    if (error?.name === 'AbortError') return;
    console.error('下载结果tif失败:', error);
    ElMessage.error('下载结果tif失败，请确认结果文件仍然可访问');
  }
}

function addCurrentResultToMainMap() {
  const result = saveMainMapAnalysisLayer({
    id: `remote-${sourceFileName.value}-${selectedResultKey.value}-${primaryCompareOverlay.value?.overlay_image_url}`,
    title: `${sourceFileName.value} - ${resultTitle.value}`,
    subtitle: '遥感生态指数分析结果',
    feature: '遥感分析',
    compareOverlay: primaryCompareOverlay.value
  });
  if (!result.success) {
    ElMessage.warning(result.message);
    return;
  }
  ElMessage.success('已添加到主地图界面，可在图层控制中开关、排序或删除');
  router.push('/');
}

// 下载结果
async function downloadResults() {
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
  try {
    await saveBlobAsFile(blob, `遥感生态指数分析结果_${new Date().getTime()}.csv`, 'text/csv');
    ElMessage.success('数据下载成功');
  } catch (error) {
    if (error?.name === 'AbortError') return;
    console.error('数据下载失败:', error);
    ElMessage.error('数据下载失败');
  }
}

// 组件挂载时检查是否需要加载数据
onMounted(() => {
  if (props.status === 'done' && props.resultData) {
    loadIndicesData();
  }
});

// 卸载时清理监听
onUnmounted(() => {
  if (removeResizeListener) removeResizeListener();
  if (pieChart && !pieChart.isDisposed()) {
    pieChart.dispose();
  }
});
</script>

<style scoped>
.result-panel-apple {
  width: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  background: transparent;
  padding: 0;
}

.placeholder-apple {
  align-self: center;
  margin: auto;
  width: min(820px, 100%);
  min-height: 260px;
  padding: 32px;
  border: 1px dashed #1c4265;
  border-radius: 10px;
  background: #102d4d;
  color: #c4d4eb;
  font-size: 15px;
  box-shadow: none;
  letter-spacing: 0;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
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
  color: #2f97b9;
  animation: apple-spin 1.2s linear infinite;
}

@keyframes apple-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text-apple {
  color: #1f6f8f;
  font-size: 1.15rem;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.result-content-apple {
  width: 100%;
  max-width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 0;
}

.result-notice {
  border-radius: 8px;
  padding: 14px 16px;
  border: 1px solid #d9e3ed;
}

.result-notice.is-preview {
  background: #f8fbfd;
}

.result-notice.is-hint {
  background: #ffffff;
}

.result-notice.is-warning {
  background: #fffaf7;
}

.notice-title {
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 700;
  color: #223244;
}

.notice-text {
  font-size: 13px;
  line-height: 1.6;
  color: #66798a;
}

.result-header-apple {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  min-height: 54px;
  padding: 12px 16px;
  border: 1px solid #1c4265;
  background: #102d4d;
  border-radius: 8px;
}

.result-title-apple {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: 0;
}

.result-download-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
}

.result-download-btn {
  --el-button-bg-color: #1677e8;
  --el-button-border-color: #1677e8;
  --el-button-hover-bg-color: #2b8cff;
  --el-button-hover-border-color: #2b8cff;
  --el-button-active-bg-color: #1265c8;
  --el-button-active-border-color: #1265c8;
  min-width: 118px;
  height: 36px;
  padding: 0 14px;
  border-radius: 6px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
}

.result-download-btn + .result-download-btn {
  margin-left: 0;
}

.visualization-section {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #132a48;
  border: 1px solid #203b60;
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
}

.visualization-header {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.visualization-title-block {
  min-width: 0;
}

.visualization-title-block h3 {
  margin: 0;
  color: #ffffff;
  font-size: 18px;
  line-height: 1.25;
  font-weight: 700;
}

.visualization-title-block span {
  display: block;
  margin-top: 5px;
  color: #8299bc;
  font-size: 12px;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-image-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
  margin: 0;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
}

.map-edge-actions {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  gap: 8px;
  padding: 8px;
  background: rgba(19, 42, 72, 0.96);
  border: 1px solid #203b60;
  border-radius: 8px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
}

.map-edge-actions .image-download-btn {
  width: 100%;
  min-width: 0;
  height: 32px;
  padding: 0 8px;
  font-size: 12px;
}

.visualization-map-body {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 118px;
  gap: 12px;
  min-height: 340px;
  overflow: hidden;
  background: #0b223c;
  border: 1px solid #203b60;
  border-radius: 8px;
  padding: 10px;
}

.visualization-image-frame {
  min-width: 0;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #d6e2ec;
  border-radius: 6px;
}

.map-side-controls {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.map-legend-panel {
  width: 100%;
  padding: 10px;
  background: #132a48;
  border: 1px solid #203b60;
  border-radius: 8px;
  color: #c4d4eb;
  box-shadow: none;
}

.legend-title {
  margin-bottom: 8px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 22px;
  font-size: 12px;
  line-height: 1.2;
}

.legend-swatch {
  width: 14px;
  height: 8px;
  border-radius: 2px;
  flex: 0 0 auto;
}

.legend-name {
  white-space: nowrap;
}

.image-download-btn {
  min-width: 116px;
  height: 34px;
}

.image-secondary-btn {
  --el-button-bg-color: #0d2745;
  --el-button-border-color: #285a82;
  --el-button-hover-bg-color: #183b61;
  --el-button-hover-border-color: #2b8cff;
  --el-button-active-bg-color: #102d4d;
  --el-button-active-border-color: #1677ff;
  color: #c4d4eb;
}

.visualization-image {
  display: block;
  width: 100%;
  height: clamp(320px, 38vh, 430px);
  object-fit: contain;
  border-radius: 0;
  background: #ffffff;
}

.loading-data-apple {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #66798a;
  font-size: 1rem;
}

.loading-icon-small {
  font-size: 24px;
  color: #2f97b9;
  animation: apple-spin 1.2s linear infinite;
}

/* 统计卡片 */
.statistics-section {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  align-items: stretch;
}

.stat-card {
  min-width: 0;
  min-height: 208px;
  background: #102d4d;
  border-radius: 10px;
  padding: 16px;
  box-shadow: none;
  border: 1px solid #285a82;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: none;
  border-color: #3374a2;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.18);
}

.stat-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  min-height: 28px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #1c4265;
}

.stat-card-title {
  min-width: 0;
  font-size: 18px;
  line-height: 1.35;
  font-weight: 750;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-card-header :deep(.el-tag) {
  flex: 0 0 auto;
  height: 24px;
  padding: 0 9px;
  border-radius: 6px;
  border-color: #20649a;
  background: #123f67;
  color: #28aaff;
  font-size: 13px;
  font-weight: 600;
}

.stat-card-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  min-width: 0;
  min-height: 70px;
  padding: 11px 12px;
  border-radius: 7px;
  background: #12385c;
  border: 1px solid #245678;
}

.stat-label {
  font-size: 12px;
  color: #c4d4eb;
  line-height: 1.2;
  white-space: nowrap;
}

.stat-value {
  min-width: 0;
  display: block;
  font-size: 21px;
  line-height: 1.15;
  font-weight: 700;
  color: #ffffff;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0;
  white-space: nowrap;
  overflow: visible;
  text-overflow: clip;
}

/* 图表区域 */
.charts-section {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 0;
  align-items: stretch;
}

.chart-container {
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #132a48;
  min-height: 380px;
  border-radius: 10px;
  padding: 20px;
  box-shadow: none;
  border: 1px solid #203b60;
  align-self: stretch;
  overflow: hidden;
}

.chart-title {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 16px 0;
  min-height: 26px;
  text-align: center;
}

.chart-canvas {
  width: 100%;
  flex: 1 1 auto;
  height: 320px;
  background: #eef6ff;
  border: 1px solid #d3e3f1;
  border-radius: 8px;
  overflow: hidden;
}

/* 无数据提示 */
.no-data-apple {
  text-align: center;
  padding: 60px 32px;
  color: #66798a;
}

.error-state-card {
  background: #ffffff;
  border: 1px solid #d9e3ed;
  border-radius: 8px;
  padding: 24px;
  box-shadow: none;
}

.error-title {
  margin: 0 0 10px;
  font-size: 20px;
  color: #b42318;
}

.error-message {
  margin: 0;
  font-size: 15px;
  color: #7a3d3d;
  font-weight: 600;
}

.error-details,
.error-supported,
.error-meta {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: #7c6a6a;
}

.no-data-apple p {
  margin: 8px 0;
  font-size: 1.1rem;
}

.hint-text {
  font-size: 0.95rem;
  color: #8093a3;
}

/* 数值解读样式 */
.interpretation-content {
  flex: 1 1 auto;
  height: 320px;
  padding: 16px;
  background: #eaf4ff;
  border-radius: 8px;
  border: 1px solid #d3e3f1;
  overflow: hidden;
}

.interpretation-text {
  height: 100%;
  max-height: none;
  overflow-y: auto;
}

.index-interpretation {
  margin-bottom: 12px;
  padding: 16px;
  background: #f5faff;
  border-radius: 8px;
  box-shadow: none;
  border: 1px solid #d3e3f1;
  border-left: 4px solid #1677ff;
}

.index-interpretation:last-child {
  margin-bottom: 0;
}

.index-name {
  margin: 0 0 12px 0;
  font-size: 18px;
  font-weight: 600;
  color: #17314d;
  border-bottom: 1px solid #d3e3f1;
  padding-bottom: 10px;
}

.interpretation-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.interpretation-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  line-height: 1.6;
  font-size: 14px;
}

.item-label {
  font-weight: 600;
  color: #17314d;
  min-width: 88px;
  flex-shrink: 0;
}

.item-content {
  color: #5c7288;
  flex: 1;
  text-align: justify;
}

.no-data-text {
  text-align: center;
  padding: 40px 20px;
  color: #8093a3;
}

.no-data-text p {
  margin: 8px 0;
}

/* 响应式设计 */
@media (max-width: 900px) {
  .result-header-apple {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .result-download-actions {
    justify-content: flex-start;
  }

  .result-image-actions {
    justify-content: flex-start;
    max-width: none;
    align-self: stretch;
  }

  .map-edge-actions {
    width: auto;
    margin: 0 10px 10px;
    flex-direction: row;
    align-self: auto;
  }

  .visualization-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .visualization-map-body {
    grid-template-columns: 1fr;
  }

  .map-side-controls {
    display: grid;
    grid-template-columns: 1fr;
  }

  .map-legend-panel {
    width: auto;
    margin: 0;
  }

  .stats-cards {
    grid-template-columns: 1fr;
  }

  .charts-section {
    grid-template-columns: 1fr;
  }

  .chart-canvas {
    height: 280px;
  }
}

@media (max-width: 1680px) {
  .stats-cards {
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 16px;
  }

  .stat-card {
    min-height: 196px;
    padding: 14px;
  }

  .stat-card-title {
    font-size: 16px;
  }

  .stat-label {
    font-size: 12px;
  }

  .stat-item {
    min-height: 62px;
    padding: 9px 10px;
  }

  .stat-value {
    font-size: 18px;
  }
}

@media (max-width: 1280px) {
  .stats-cards {
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  }

  .charts-section {
    grid-template-columns: 1fr;
  }
}
</style>
