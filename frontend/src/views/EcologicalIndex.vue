<template>
  <div class="page-wrapper" v-loading="globalLoading" 
       element-loading-text="正在分析数据，请稍候..."
       element-loading-background="rgba(255, 255, 255, 0.8)">
    <div class="ecological-container">
      <!-- 左侧控制面板 -->
      <div class="left-panel">
        <!-- 主标题 -->
        <div class="main-title">生态环境评估</div>
        
        <!-- 描述文字 -->
        <div class="description">
          上传土地利用数据，系统将自动计算多种生态指数并进行可视化。
        </div>
        
        <!-- 文件上传区域 -->
        <div class="upload-section">
          <!-- 主要上传按钮 -->
          <el-button 
            class="upload-btn" 
            @click="triggerFileUpload"
            type="primary"
            size="large"
            :loading="uploadLoading"
          >
            <el-icon v-if="!uploadLoading"><Upload /></el-icon>
            {{ uploadLoading ? '正在处理...' : '上传影像数据' }}
          </el-button>
          
          <!-- 调试按钮 -->
          <!-- <el-button 
            class="test-btn" 
            @click="testButtonClick"
            size="small"
            type="warning"
          >
            测试按钮
          </el-button> -->
          
          <!-- 调试信息 -->
          <!-- <div class="debug-info">
            <small>globalLoading: {{ globalLoading }}</small>
          </div> -->
          
          <!-- 备用上传方式 -->
          <!-- 移除不必要的el-upload组件，使用自定义上传逻辑 -->
          
          <div class="file-status">
            {{ fileList.length === 0 ? '未选择文件' : `已选择: ${fileList[0].name}` }}
          </div>
          <!-- 如果已选择文件，显示重新选择按钮 -->
          <el-button 
            v-if="fileList.length > 0"
            class="re-upload-btn" 
            @click="clearFile"
            size="small"
            type="info"
          >
            重新选择
          </el-button>
        </div>
        
        <!-- 开始分析按钮 -->
        <el-button 
          class="start-analysis-btn" 
          @click="startAnalysis"
          :disabled="fileList.length === 0"
          :loading="globalLoading"
        >
          开始分析
        </el-button>
        
        <!-- 指数选择区域 -->
        <div class="index-selection">
          <div class="section-title">指数选择</div>
          
          <!-- 生态环境结构指数 -->
          <div class="index-group">
            <div class="group-title">生态环境结构指数</div>
            <div class="index-buttons">
              <el-button 
                v-for="index in structureIndices" 
                :key="index.key"
                :type="index.calculated ? 'success' : 'default'"
                :loading="index.loading"
                @click="calculateIndex(index.key)"
                class="index-btn"
                :disabled="fileList.length === 0"
              >
                {{ index.name }}
                <el-tag v-if="index.calculated" size="small" type="success">已计算</el-tag>
              </el-button>
            </div>
          </div>
          
          <!-- 生态环境胁迫指数 -->
          <div class="index-group">
            <div class="group-title">生态环境胁迫指数</div>
            <div class="index-buttons">
              <el-button 
                v-for="index in stressIndices" 
                :key="index.key"
                :type="index.calculated ? 'success' : 'default'"
                :loading="index.loading"
                @click="calculateIndex(index.key)"
                class="index-btn"
                :disabled="fileList.length === 0"
              >
                {{ index.name }}
                <el-tag v-if="index.calculated" size="small" type="success">已计算</el-tag>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧结果展示区域 -->
      <div class="right-panel">
        <div class="results-area">
          <!-- 有结果时显示 -->
          <div v-if="hasResults" class="results-content">
            <!-- 指数值展示 -->
            <div class="index-values">
              <div class="values-title">计算结果</div>
              <div class="values-grid">
                <div 
                  v-for="(value, key) in indexResults" 
                  :key="key"
                  class="value-item"
                >
                  <div class="value-name">{{ getIndexName(key) }}</div>
                  <div class="value-number">{{ value.toFixed(4) }}</div>
                  <div class="value-status" :class="getStatusClass(key, value)">
                    {{ getStatusText(key, value) }}
                  </div>
                  <div class="value-unit">{{ getIndexUnit(key) }}</div>
                </div>
              </div>
            </div>
            
            <!-- 图表展示 -->
            <div class="charts-section">
              <div class="chart-container">
                <div class="chart-title">指数分布雷达图</div>
                <div ref="radarChart" class="chart"></div>
              </div>
              
              <div class="chart-container">
                <div class="chart-title">指数对比柱状图</div>
                <div ref="barChart" class="chart"></div>
              </div>
            </div>
            
            <!-- 下载按钮 -->
            <div class="download-section">
              <el-button 
                type="success" 
                @click="downloadResults"
                class="download-btn"
              >
                <el-icon><Download /></el-icon>
                下载计算结果
              </el-button>
            </div>
          </div>
          
          <!-- 无结果时显示占位符 -->
          <div v-else class="placeholder">
            <div class="placeholder-text">
              请先上传数据并开始分析
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 移除自定义loading容器，使用Element Plus的内置loading -->
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { API_ENDPOINTS, buildApiUrl } from '../config/api.js'
import http from '../utils/http.js'

export default {
  name: 'EcologicalIndex',
  setup() {
    // 响应式数据
    const fileList = ref([])
    const globalLoading = ref(false)
    const uploadLoading = ref(false)
    
    // 监听 globalLoading 的变化
    watch(globalLoading, (newVal, oldVal) => {
      // globalLoading 状态变化监听
    })
    
    // 指数定义
    const structureIndices = reactive([
      { key: 'fragmentation', name: '破碎度指数', calculated: false, loading: false, apiKey: 'fragmentation_index' },
      { key: 'cohesion', name: '内聚力指数', calculated: false, loading: false, apiKey: 'cohesion_index' },
      { key: 'diversity', name: '多样性指数', calculated: false, loading: false, apiKey: 'shannon_diversity' },
      { key: 'fragility', name: '脆弱度指数', calculated: false, loading: false, apiKey: 'fragility_index' }
    ])
    
    const stressIndices = reactive([
      { key: 'soil_erosion', name: '土壤侵蚀指数', calculated: false, loading: false, apiKey: 'soil_erosion_index' },
      { key: 'unused_land', name: '未利用地面积比例', calculated: false, loading: false, apiKey: 'unused_land_proportion' },
      { key: 'cultivated_construction', name: '耕地建设用地面积比例', calculated: false, loading: false, apiKey: 'cultivated_construction_proportion' },
      { key: 'land_degradation', name: '土地退化指数', calculated: false, loading: false, apiKey: 'land_degradation_index' }
    ])
    
    // 计算结果
    const indexResults = reactive({})
    
    // 图表引用
    const radarChart = ref(null)
    const barChart = ref(null)
    // 移除 uploadRef，因为我们使用自定义的文件上传逻辑
    
    // 计算属性
    const hasResults = computed(() => Object.keys(indexResults).length > 0)
    
    // 方法
    const triggerFileUpload = () => {
      uploadLoading.value = true
      ElMessage.info('正在打开文件选择器...') // 用户反馈
      
      try {
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = '.tif,.tiff,.zip'
        input.multiple = false
        input.style.display = 'none' // 隐藏input元素
        
        input.onchange = (e) => {
          const file = e.target.files[0]
          if (file) {
            if (beforeUpload(file)) {
              handleUploadSuccess({}, file)
            }
          }
        }
        
        // 添加到DOM中
        document.body.appendChild(input)
        input.click()
        
        // 清理DOM
        setTimeout(() => {
          if (document.body.contains(input)) {
            document.body.removeChild(input)
          }
        }, 1000)
      } catch (error) {
        console.error('文件上传错误:', error)
        ElMessage.error('文件上传失败，请重试')
      } finally {
        uploadLoading.value = false
      }
    }
    
    const beforeUpload = (file) => {
      const isValidFormat = /\.(tif|tiff|zip)$/i.test(file.name)
      if (!isValidFormat) {
        ElMessage.error('只支持 GeoTIFF(.tif/.tiff) 或 Shapefile 压缩包(.zip)')
        return false
      }
      
      // 检查ZIP文件
      if (file.name.toLowerCase().endsWith('.zip')) {
        // 基本大小检查 (避免空文件)
        if (file.size < 100) {
          ElMessage.error('ZIP文件过小，请确保包含完整的Shapefile组件(.shp/.shx/.dbf/.prj)')
          return false
        }
        ElMessage.info('检测到Shapefile压缩包，请确保：1) 是真正的ZIP格式（不是RAR）2) 包含.shp/.shx/.dbf/.prj四个文件')
      }
      
      return true
    }
    
    const handleUploadSuccess = (response, file) => {
      ElMessage.success(`${file.name} 上传成功`)
      fileList.value = [file]
    }
    
    // 移除 handleFileChange 函数，因为不再需要
    
    const testButtonClick = () => {
      ElMessage.success('测试按钮工作正常！')
      
      // 强制重置 globalLoading
      if (globalLoading.value) {
        globalLoading.value = false
        ElMessage.info('已重置加载状态')
      }
    }
    
    const clearFile = () => {
      fileList.value = []
      // 清除计算结果
      Object.keys(indexResults).forEach(key => {
        delete indexResults[key]
      })
      // 重置指数状态
      structureIndices.forEach(index => {
        index.calculated = false
        index.loading = false
      })
      stressIndices.forEach(index => {
        index.calculated = false
        index.loading = false
      })
      // 清除图表
      if (radarChart.value) {
        const radar = echarts.getInstanceByDom(radarChart.value)
        if (radar) radar.dispose()
      }
      if (barChart.value) {
        const bar = echarts.getInstanceByDom(barChart.value)
        if (bar) bar.dispose()
      }
      ElMessage.info('已清除文件，请重新选择')
    }
    
    const startAnalysis = async () => {
      if (fileList.value.length === 0) {
        ElMessage.warning('请先选择文件')
        return
      }
      
      globalLoading.value = true
      try {
        const file = fileList.value[0]
        const formData = new FormData()
        formData.append('landuse_file', file)
        
        // 计算生态环境结构指数
        ElMessage.info('正在计算生态环境结构指数...')
        const structureResponse = await http.post(buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.STRUCTURE_INDICES), formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        
        // 计算生态环境胁迫指数
        ElMessage.info('正在计算生态环境胁迫指数...')
        const stressResponse = await http.post(buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.STRESS_INDICES), formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        
        // 处理结果
        if (structureResponse.summary && stressResponse.summary) {
          // 合并所有指数结果
          Object.assign(indexResults, structureResponse.summary, stressResponse.summary)
          
          // 更新指数状态
          const allIndices = [...structureIndices, ...stressIndices]
          allIndices.forEach(index => {
            if (indexResults[index.apiKey] !== undefined) {
              index.calculated = true
            }
          })
          
          ElMessage.success('分析完成！')
          
          // 更新图表
          nextTick(() => {
            updateCharts()
          })
        } else {
          throw new Error('API返回结果格式错误')
        }
      } catch (error) {
        console.error('分析失败:', error)
        
        // 详细的错误信息处理
        let errorMessage = '分析失败'
        if (error.response) {
          // 服务器响应了错误状态码
          const { status, data } = error.response
          errorMessage = `分析失败 (${status}): ${data?.error || data?.message || '服务器错误'}`
        } else if (error.request) {
          // 请求已发出但没有收到响应
          errorMessage = '分析失败: 无法连接到服务器，请检查网络连接'
        } else if (error.message) {
          // 其他错误
          errorMessage = `分析失败: ${error.message}`
        }
        
        ElMessage.error(errorMessage)
      } finally {
        globalLoading.value = false
      }
    }
    
    const calculateIndex = async (indexKey) => {
      const index = [...structureIndices, ...stressIndices].find(i => i.key === indexKey)
      if (!index) return
      
      if (fileList.value.length === 0) {
        ElMessage.warning('请先选择文件')
        return
      }
      
      index.loading = true
      try {
        const file = fileList.value[0]
        const formData = new FormData()
        formData.append('landuse_file', file)
        
        let response
        let apiEndpoint
        
        // 根据指数类型选择对应的API端点
        if (structureIndices.find(i => i.key === indexKey)) {
          apiEndpoint = buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.STRUCTURE_INDICES)
        } else {
          apiEndpoint = buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.STRESS_INDICES)
        }
        
        // 调用API
        response = await http.post(apiEndpoint, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        
        // 处理结果
        if (response.summary && response.summary[index.apiKey] !== undefined) {
          indexResults[index.apiKey] = response.summary[index.apiKey]
          index.calculated = true
          
          ElMessage.success(`${index.name} 计算完成`)
          
          // 更新图表
          nextTick(() => {
            updateCharts()
          })
        } else {
          throw new Error('API返回结果中未找到对应指数')
        }
      } catch (error) {
        console.error(`${index.name} 计算失败:`, error)
        
        // 详细的错误信息处理
        let errorMessage = `${index.name} 计算失败`
        if (error.response) {
          // 服务器响应了错误状态码
          const { status, data } = error.response
          errorMessage = `${index.name} 计算失败 (${status}): ${data?.error || data?.message || '服务器错误'}`
        } else if (error.request) {
          // 请求已发出但没有收到响应
          errorMessage = `${index.name} 计算失败: 无法连接到服务器，请检查网络连接`
        } else if (error.message) {
          // 其他错误
          errorMessage = `${index.name} 计算失败: ${error.message}`
        }
        
        ElMessage.error(errorMessage)
      } finally {
        index.loading = false
      }
    }
    
    const getIndexName = (key) => {
      const allIndices = [...structureIndices, ...stressIndices]
      const index = allIndices.find(i => i.apiKey === key)
      return index ? index.name : key
    }
    
    const getStatusClass = (key, value) => {
      // 根据不同指数类型和值返回对应的状态类
      switch (key) {
        case 'fragmentation_index':
          // 破碎化指数：0表示完全未破碎，1表示极度破碎
          if (value === 0) return 'status-excellent' // 优：完全未破碎
          if (value < 0.3) return 'status-good'      // 良：轻微破碎
          if (value < 0.5) return 'status-moderate'  // 中：中度破碎
          if (value < 0.7) return 'status-poor'      // 差：严重破碎
          return 'status-bad'                        // 劣：极度破碎
        
        case 'shannon_diversity':
          // 多样性指数：值越高表示多样性越丰富
          if (value > 2.0) return 'status-excellent' // 优：非常丰富的多样性
          if (value > 1.5) return 'status-good'      // 良：较好的多样性
          if (value > 1.0) return 'status-moderate'  // 中：中等多样性
          if (value > 0.5) return 'status-poor'      // 差：较低多样性
          return 'status-bad'                        // 劣：极低多样性
          
        case 'cohesion_index':
          // 内聚力指数：值越高表示连接性越好
          if (value === 0) return 'status-bad'       // 劣：无连接性
          if (value < 0.3) return 'status-poor'      // 差：低连接性
          if (value < 0.5) return 'status-moderate'  // 中：中等连接性
          if (value < 0.8) return 'status-good'      // 良：良好连接性
          return 'status-excellent'                  // 优：极佳连接性
          
        case 'fragility_index':
          // 脆弱性指数：值越低表示抵抗力越强
          if (value < 0.2) return 'status-excellent' // 优：极低脆弱性
          if (value < 0.3) return 'status-good'      // 良：低脆弱性
          if (value < 0.5) return 'status-moderate'  // 中：中等脆弱性
          if (value < 0.7) return 'status-poor'      // 差：高脆弱性
          return 'status-bad'                        // 劣：极高脆弱性
          
        case 'soil_erosion_index':
          // 土壤侵蚀指数：值越低表示侵蚀程度越轻
          if (value < 0.2) return 'status-excellent' // 优：微度侵蚀
          if (value < 0.3) return 'status-good'      // 良：轻度侵蚀
          if (value < 0.5) return 'status-moderate'  // 中：中度侵蚀
          if (value < 0.7) return 'status-poor'      // 差：重度侵蚀
          return 'status-bad'                        // 劣：极重度侵蚀
          
        case 'land_degradation_index':
          // 土地退化指数：值越低表示退化程度越轻
          if (value < 0.2) return 'status-excellent' // 优：微度退化
          if (value < 0.3) return 'status-good'      // 良：轻度退化
          if (value < 0.5) return 'status-moderate'  // 中：中度退化
          if (value < 0.7) return 'status-poor'      // 差：重度退化
          return 'status-bad'                        // 劣：极重度退化
          
        case 'unused_land_proportion':
          // 未利用土地比例：按照生态环境评估界面标准
          if (value < 5) return 'status-excellent'   // 优：极低比例
          if (value < 10) return 'status-good'       // 良：低比例
          if (value < 15) return 'status-moderate'   // 中：中等比例
          if (value < 20) return 'status-poor'       // 差：高比例
          return 'status-bad'                        // 劣：极高比例
          
        case 'cultivated_construction_proportion':
          // 耕地与建设用地比例：按照生态环境评估界面标准
          if (value >= 35 && value <= 45) return 'status-excellent' // 优：最佳平衡
          if (value >= 30 && value < 35 || value > 45 && value <= 50) return 'status-good' // 良：良好平衡
          if (value >= 25 && value < 30 || value > 50 && value <= 55) return 'status-moderate' // 中：一般平衡
          if (value >= 20 && value < 25 || value > 55 && value <= 60) return 'status-poor' // 差：较差平衡
          return 'status-bad' // 劣：严重失衡
          
        default:
          // 默认情况
          return 'status-unknown'
      }
    }
    
    const getStatusText = (key, value) => {
      // 根据不同指数类型和值返回对应的状态文本
      switch (key) {
        case 'fragmentation_index':
          if (value === 0) return '优' 
          if (value < 0.3) return '良'
          if (value < 0.5) return '中'
          if (value < 0.7) return '差'
          return '劣'
        
        case 'shannon_diversity':
          if (value > 2.0) return '优'
          if (value > 1.5) return '良'
          if (value > 1.0) return '中'
          if (value > 0.5) return '差'
          return '劣'
          
        case 'cohesion_index':
          if (value === 0) return '劣'
          if (value < 0.3) return '差'
          if (value < 0.5) return '中'
          if (value < 0.8) return '良'
          return '优'
          
        case 'fragility_index':
          if (value < 0.2) return '优'
          if (value < 0.3) return '良'
          if (value < 0.5) return '中'
          if (value < 0.7) return '差'
          return '劣'
          
        case 'soil_erosion_index':
          if (value < 0.2) return '优'
          if (value < 0.3) return '良'
          if (value < 0.5) return '中'
          if (value < 0.7) return '差'
          return '劣'
          
        case 'land_degradation_index':
          if (value < 0.2) return '优'
          if (value < 0.3) return '良'
          if (value < 0.5) return '中'
          if (value < 0.7) return '差'
          return '劣'
          
        case 'unused_land_proportion':
          if (value < 5) return '优'
          if (value < 10) return '良'
          if (value < 15) return '中'
          if (value < 20) return '差'
          return '劣'
          
        case 'cultivated_construction_proportion':
          if (value >= 35 && value <= 45) return '优'
          if (value >= 30 && value < 35 || value > 45 && value <= 50) return '良'
          if (value >= 25 && value < 30 || value > 50 && value <= 55) return '中'
          if (value >= 20 && value < 25 || value > 55 && value <= 60) return '差'
          return '劣'
          
        default:
          return '未知'
      }
    }
    
    const getIndexUnit = (key) => {
      // 根据指数类型返回对应的单位
      const unitMap = {
        'fragmentation_index': '无单位',
        'cohesion_index': '%',
        'shannon_diversity': '无单位',
        'fragility_index': '无单位',
        'soil_erosion_index': '无单位',
        'unused_land_proportion': '%',
        'cultivated_construction_proportion': '%',
        'land_degradation_index': '无单位'
      }
      return unitMap[key] || '无单位'
    }
    
    const downloadResults = () => {
      try {
        // 准备下载数据
        const downloadData = {
          timestamp: new Date().toISOString(),
          filename: fileList.value[0]?.name || 'unknown',
          results: indexResults,
          summary: {
            total_indices: Object.keys(indexResults).length,
            calculated_time: new Date().toLocaleString('zh-CN')
          }
        }
        
        // 创建Blob对象
        const blob = new Blob([JSON.stringify(downloadData, null, 2)], {
          type: 'application/json'
        })
        
        // 创建下载链接
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `ecological_indices_${new Date().getTime()}.json`
        document.body.appendChild(a)
        a.click()
        
        // 清理
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        ElMessage.success('计算结果已下载')
      } catch (error) {
        console.error('下载失败:', error)
        ElMessage.error('下载失败')
      }
    }
    
    const updateCharts = () => {
      if (Object.keys(indexResults).length === 0) return
      
      // 更新雷达图
      if (radarChart.value) {
        const radar = echarts.init(radarChart.value)
        
        // 计算合适的最大值
        const maxValue = Math.max(...Object.values(indexResults))
        const chartMax = Math.ceil(maxValue * 1.2) // 留出20%的边距
        
        const radarOption = {
          title: { 
            text: '生态环境指数雷达图',
            textStyle: { fontSize: 16, fontWeight: 'bold' }
          },
          radar: {
            indicator: Object.keys(indexResults).map(key => ({
              name: getIndexName(key),
              max: chartMax
            })),
            radius: '60%',
            center: ['50%', '55%']
          },
          series: [{
            type: 'radar',
            data: [{
              value: Object.values(indexResults),
              name: '指数值',
              areaStyle: { 
                opacity: 0.3,
                color: '#3b82f6'
              },
              lineStyle: {
                color: '#3b82f6',
                width: 2
              },
              itemStyle: {
                color: '#3b82f6'
              }
            }]
          }]
        }
        radar.setOption(radarOption)
      }
      
      // 更新柱状图
      if (barChart.value) {
        const bar = echarts.init(barChart.value)
        
        // 为不同类型的指数设置不同的颜色
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316']
        
        const barOption = {
          title: { 
            text: '生态环境指数对比',
            textStyle: { fontSize: 16, fontWeight: 'bold' }
          },
          tooltip: {
            trigger: 'axis',
            formatter: function(params) {
              const data = params[0]
              return `${data.name}<br/>${data.value.toFixed(4)}`
            }
          },
          xAxis: {
            type: 'category',
            data: Object.keys(indexResults).map(key => getIndexName(key)),
            axisLabel: { 
              rotate: 45,
              fontSize: 12
            }
          },
          yAxis: { 
            type: 'value',
            name: '指数值'
          },
          series: [{
            type: 'bar',
            data: Object.values(indexResults).map((value, index) => ({
              value: value,
              itemStyle: { 
                color: colors[index % colors.length]
              }
            })),
            barWidth: '60%'
          }]
        }
        bar.setOption(barOption)
      }
    }
    

    
    // 生命周期
    onMounted(() => {
      // 初始化图表
      nextTick(() => {
        updateCharts()
      })
    })
    
    return {
      fileList,
      globalLoading,
      uploadLoading,
      structureIndices,
      stressIndices,
      indexResults,
      hasResults,
      radarChart,
      barChart,
      triggerFileUpload,
      beforeUpload,
      testButtonClick,
      clearFile,
      startAnalysis,
      calculateIndex,
      getIndexName,
      getStatusClass,
      getStatusText,
      getIndexUnit,
      downloadResults
    }
  }
}
</script>

<style scoped>
.page-wrapper {
  width: 100%;
  min-height: 100vh;
  background: #f8fafc;
  padding: 20px;
}

.ecological-container {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 24px;
  height: calc(100vh - 40px);
  overflow: hidden;
}

/* 左侧控制面板 */
.left-panel {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow-y: auto;
  max-height: 100%;
}

/* 自定义滚动条样式 */
.left-panel::-webkit-scrollbar {
  width: 6px;
}

.left-panel::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.left-panel::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.left-panel::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.main-title {
  font-size: 1.8rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.description {
  color: #6b7280;
  line-height: 1.6;
  font-size: 0.95rem;
}

.upload-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.re-upload-btn {
  width: 100%;
  height: 32px;
  background: #6b7280;
  border: none;
  color: white;
  font-weight: 500;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.re-upload-btn:hover {
  background: #4b5563;
  transform: translateY(-1px);
}

.upload-btn {
  width: 100%;
  height: 48px;
  background: #3b82f6 !important;
  border: none !important;
  color: white !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
  position: relative !important;
  z-index: 100 !important;
  cursor: pointer !important;
  font-size: 16px !important;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}

.upload-btn:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.test-btn {
  width: 100%;
  height: 32px;
  background: #f59e0b;
  border: none;
  color: white;
  font-weight: 500;
  border-radius: 6px;
  transition: all 0.2s ease;
  margin-top: 8px;
}

.test-btn:hover {
  background: #d97706;
  transform: translateY(-1px);
}

.debug-info {
  text-align: center;
  padding: 8px;
  background: #f3f4f6;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #6b7280;
}

.upload-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
}

.file-status {
  font-size: 0.9rem;
  color: #6b7280;
  text-align: center;
}

.start-analysis-btn {
  width: 100%;
  height: 52px;
  background: #10b981;
  border: none;
  color: white;
  font-size: 1.1rem;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.start-analysis-btn:hover {
  background: #059669;
  transform: translateY(-1px);
}

.start-analysis-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
}

/* 指数选择区域 */
.index-selection {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.index-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-title {
  font-size: 0.95rem;
  font-weight: 500;
  color: #6b7280;
  margin: 0;
}

.index-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.index-btn {
  width: 100%;
  height: 40px;
  text-align: left;
  padding: 0 16px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.index-btn:hover {
  transform: translateX(4px);
}

/* 右侧结果展示区域 */
.right-panel {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.results-area {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.results-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

/* 右侧结果区域滚动条样式 */
.results-content::-webkit-scrollbar {
  width: 6px;
}

.results-content::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.results-content::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.results-content::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.placeholder {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-text {
  color: #9ca3af;
  font-size: 1.1rem;
}

/* 结果展示样式 */
.index-values {
  margin-bottom: 32px;
}

.values-title {
  font-size: 1.3rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 20px;
}

.values-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.value-item {
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  text-align: center;
}

.value-name {
  font-size: 0.9rem;
  color: #6b7280;
  margin-bottom: 8px;
}

.value-number {
  font-size: 1.8rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 8px;
}

.value-status {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 500;
  display: inline-block;
  margin-bottom: 8px;
}

.value-unit {
  font-size: 0.75rem;
  color: #9ca3af;
  font-style: italic;
}

.status-excellent {
  background: #dcfce7;
  color: #166534;
}

.status-good {
  background: #e6f7ff;
  color: #1890ff;
}

.status-moderate {
  background: #fffbe6;
  color: #faad14;
}

.status-poor {
  background: #fff7e6;
  color: #fa8c16;
}

.status-bad {
  background: #fff1f0;
  color: #f5222d;
}

.status-unknown {
  background: #f5f5f5;
  color: #999;
}

/* 图表区域 */
.charts-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.chart-container {
  background: #f9fafb;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #e5e7eb;
}

.chart-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 16px;
  text-align: center;
}

.chart {
  height: 300px;
  width: 100%;
}

/* 下载区域 */
.download-section {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

/* 移除不再需要的loading-container样式 */

.download-btn {
  height: 44px;
  padding: 0 24px;
  background: #10b981;
  border: none;
  color: white;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.download-btn:hover {
  background: #059669;
  transform: translateY(-1px);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .ecological-container {
    grid-template-columns: 320px 1fr;
    gap: 20px;
  }
  
  .charts-section {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}

@media (max-width: 1000px) {
  .ecological-container {
    grid-template-columns: 1fr;
    gap: 20px;
    height: auto;
    overflow: visible;
  }
  
  .left-panel {
    order: 2;
    max-height: none;
    overflow-y: visible;
  }
  
  .right-panel {
    order: 1;
    min-height: 500px;
    overflow: visible;
  }
}

@media (max-width: 768px) {
  .page-wrapper {
    padding: 16px;
  }
  
  .left-panel {
    padding: 20px;
  }
  
  .values-grid {
    grid-template-columns: 1fr;
  }
  
  .chart {
    height: 250px;
  }
}
</style>

