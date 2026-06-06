<template>
  <div class="climate-monitoring">
    <div class="main-container">
      <!-- 左侧控制面板 -->
      <div class="left-panel">
        <!-- 标题栏 -->
        <div class="panel-header">
          <RouterLink to="/" class="back-home-link" title="返回主界面">
            <ArrowLeft class="back-home-icon" />
            <span>主界面</span>
          </RouterLink>
          <h1>气候环境监测统计</h1>
          <p>上传CSV或Excel格式的气候监测数据，系统将自动生成统计图表。</p>
        </div>
        
        <!-- 数据文件管理 -->
        <div class="section">
          <div class="section-header">
            <Files class="section-icon" />
            <span>数据文件管理</span>
          </div>
          <div class="section-content">
            <div class="file-upload-area">
              <input
                ref="fileInput"
                type="file"
                accept=".csv,.xlsx,.xls"
                @change="handleFileSelect"
                style="display: none"
              />
              <div class="upload-zone" @click="fileInput?.click()">
                <div class="upload-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="#1890ff" stroke-width="2" fill="none"/>
                    <path d="M14 2V8H20" stroke="#1890ff" stroke-width="2" fill="none"/>
                    <path d="M12 18V12" stroke="#1890ff" stroke-width="2" stroke-linecap="round"/>
                    <path d="M9 15L12 12L15 15" stroke="#1890ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <div class="upload-text">上传气候数据文件</div>
                <div class="upload-hint">拖放文件到此处或点击选择文件</div>
                <div class="upload-types">支持的文件类型: .csv, .xlsx, .xls</div>
              </div>
              <div class="file-status">
                {{ selectedFile ? selectedFile.name : '未选择文件' }}
              </div>
            </div>
          </div>
        </div>

        <!-- 分析控制 -->
        <div class="section">
          <div class="section-header">
            <Search class="section-icon" />
            <span>数据分析控制</span>
          </div>
          <div class="section-content">
            <button
              @click="startAnalysis"
              class="analysis-btn"
              :class="{ 'disabled': !selectedFile || isAnalyzing }"
            >
              {{ isAnalyzing ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </div>

        <!-- 进度指示器 -->
        <div v-if="isAnalyzing" class="progress-section">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
          <div class="progress-text">
            {{ analysisStatus === 'uploading' ? '上传中...' : '分析中...' }} {{ Math.round(uploadProgress) }}%
          </div>
        </div>

        <!-- 成功信息 -->
        <div v-if="successMessage" class="success-message">
          <CircleCheck class="success-icon" />
          <div class="success-content">
            <div class="success-title">操作成功</div>
            <div class="success-details">{{ successMessage }}</div>
            <div class="success-actions">
              <button @click="clearSuccess" class="dismiss-btn">关闭</button>
            </div>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="errorMessage" class="error-message">
          <CircleClose class="error-icon" />
          <div class="error-content">
            <div class="error-title">操作失败</div>
            <div class="error-details">{{ errorMessage }}</div>
            <div class="error-actions">
              <button @click="clearError" class="retry-btn">重试</button>
              <button @click="clearError" class="dismiss-btn">关闭</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧内容区域 -->
      <div class="right-panel">
        <!-- 无数据时的占位符 -->
        <div v-if="!hasData" class="placeholder">
          <CirclePlus class="placeholder-icon" />
          <p>请先上传气候数据并开始分析</p>
        </div>

        <!-- 有数据时显示分析结果 -->
        <div v-else class="analysis-results">
          <!-- 统计概览 -->
          <div class="stats-overview">
            <h3>统计概览</h3>
            <div class="stats-grid">
              <div v-for="stat in statistics" :key="stat.indicator" class="stat-item">
                <div class="stat-label">{{ stat.indicator }}</div>
                <div class="stat-values">
                  <div class="stat-value">
                    <span class="label">平均:</span>
                    <span class="value">{{ stat.average }}</span>
                  </div>
                  <div class="stat-value">
                    <span class="label">最大:</span>
                    <span class="value">{{ stat.max }}</span>
                  </div>
                  <div class="stat-value">
                    <span class="label">最小:</span>
                    <span class="value">{{ stat.min }}</span>
                  </div>
                  <div class="stat-value">
                    <span class="label">标准差:</span>
                    <span class="value">{{ stat.stdDev }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 图表区域 -->
          <div class="charts-section">
            <h3>数据可视化</h3>
            <div class="charts-grid">
              <div class="chart-container">
                <h4>温度趋势图</h4>
                <canvas ref="temperatureChart" width="400" height="200"></canvas>
              </div>
              <div class="chart-container">
                <h4>降水量柱状图</h4>
                <canvas ref="precipitationChart" width="400" height="200"></canvas>
              </div>
              <div class="chart-container">
                <h4>湿度面积图</h4>
                <canvas ref="humidityChart" width="400" height="200"></canvas>
              </div>
              <div class="chart-container">
                <h4>风速雷达图</h4>
                <canvas ref="windSpeedChart" width="400" height="200"></canvas>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ArrowLeft, CircleCheck, CircleClose, CirclePlus, Files, Search } from '@element-plus/icons-vue'
import { climateMonitoringService } from '../services/api.js'

// 响应式数据
const fileInput = ref(null)
const selectedFile = ref(null)
const isAnalyzing = ref(false)
const uploadProgress = ref(0)
const analysisStatus = ref('')
const analysisTaskId = ref(null)
const errorMessage = ref('')
const successMessage = ref('')
const hasData = ref(false)
const statistics = ref([])
const chartData = ref({
  temperature: [],
  precipitation: [],
  humidity: [],
  windSpeed: []
})

// 图表ref
const temperatureChart = ref(null)
const precipitationChart = ref(null)
const humidityChart = ref(null)
const windSpeedChart = ref(null)

// 状态轮询间隔
let statusCheckInterval = null

// 文件选择处理
const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    // 验证文件
    const validationResult = validateClimateDataFile(file)
    if (validationResult.isValid) {
      selectedFile.value = file
      errorMessage.value = ''
      successMessage.value = `文件 "${file.name}" 选择成功，可以开始分析`
      // 3秒后自动清除成功消息
      setTimeout(() => {
        successMessage.value = ''
      }, 3000)
    } else {
      errorMessage.value = validationResult.errorMessage
      selectedFile.value = null
      // 清空文件输入
      if (fileInput.value) {
        fileInput.value.value = ''
      }
    }
  }
}

// 验证气候数据文件
const validateClimateDataFile = (file) => {
  // 1. 检查文件是否存在
  if (!file) {
    return {
      isValid: false,
      errorMessage: '请选择一个文件'
    }
  }

  // 2. 检查文件大小（限制为50MB）
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    return {
      isValid: false,
      errorMessage: '文件大小不能超过50MB'
    }
  }

  // 3. 检查文件类型
  const allowedTypes = ['.csv', '.xlsx', '.xls']
  const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
  if (!allowedTypes.includes(fileExtension)) {
    return {
      isValid: false,
      errorMessage: '只支持CSV和Excel格式文件(.csv, .xlsx, .xls)'
    }
  }

  // 4. 检查文件名
  if (!file.name || file.name.trim() === '') {
    return {
      isValid: false,
      errorMessage: '文件名不能为空'
    }
  }

  // 5. 检查文件是否为空
  if (file.size === 0) {
    return {
      isValid: false,
      errorMessage: '文件不能为空'
    }
  }

  return {
    isValid: true,
    errorMessage: ''
  }
}

const removeFile = () => {
  selectedFile.value = null
  fileInput.value.value = ''
}

// 清除错误信息
const clearError = () => {
  errorMessage.value = ''
}

// 清除成功信息
const clearSuccess = () => {
  successMessage.value = ''
}

const startAnalysis = async () => {
  // 1. 检查是否选择了文件
  if (!selectedFile.value) {
    errorMessage.value = '请先选择一个气候数据文件'
    return
  }

  // 2. 再次验证文件（双重检查）
  const validationResult = validateClimateDataFile(selectedFile.value)
  if (!validationResult.isValid) {
    errorMessage.value = validationResult.errorMessage
    return
  }

  // 3. 检查是否正在分析中
  if (isAnalyzing.value) {
    errorMessage.value = '正在分析中，请等待完成'
    return
  }
  
  try {
    isAnalyzing.value = true
    errorMessage.value = ''
    uploadProgress.value = 0
    analysisStatus.value = 'uploading'
    
    // 调用真实的后端API
    try {
      // 1. 上传文件
      console.log('开始上传文件:', selectedFile.value.name)
      
      // 模拟上传进度
      const uploadProgressInterval = setInterval(() => {
        if (uploadProgress.value < 90) {
          uploadProgress.value += Math.random() * 10
        }
      }, 200)
      
      const uploadResponse = await climateMonitoringService.uploadClimateData(selectedFile.value, {
        name: selectedFile.value.name,
        description: '气候监测数据分析'
      })
      
      clearInterval(uploadProgressInterval)
      uploadProgress.value = 100
      
      console.log('上传响应:', uploadResponse)
      
      // 验证上传响应
      if (!uploadResponse) {
        throw new Error('上传响应为空，请检查网络连接')
      }
      
      if (uploadResponse.success) {
        const fileId = uploadResponse.file_id
        
        // 验证文件ID
        if (!fileId) {
          throw new Error('上传成功但未返回文件ID')
        }
        
        analysisStatus.value = 'processing'
        uploadProgress.value = 0
        
        // 2. 开始分析
        console.log('开始分析，文件ID:', fileId)
        
        // 模拟分析进度
        const analysisProgressInterval = setInterval(() => {
          if (uploadProgress.value < 95) {
            uploadProgress.value += Math.random() * 5
          }
        }, 300)
        
        const analysisResponse = await climateMonitoringService.analyzeClimateData(fileId, 'comprehensive')
        
        clearInterval(analysisProgressInterval)
        
        console.log('分析响应:', analysisResponse)
        
        // 验证分析响应
        if (!analysisResponse) {
          throw new Error('分析响应为空，请检查后端服务')
        }
        
        if (analysisResponse.success) {
          const taskId = analysisResponse.task_id
          
          // 验证任务ID
          if (!taskId) {
            throw new Error('分析启动成功但未返回任务ID')
          }
          
          analysisTaskId.value = taskId
          
          // 3. 开始轮询分析状态
          startStatusPolling()
        } else {
          throw new Error(analysisResponse.message || '分析启动失败')
        }
      } else {
        throw new Error(uploadResponse.message || '文件上传失败')
      }
    } catch (apiError) {
      console.error('API调用失败:', apiError)
      uploadProgress.value = 0
      
      // 根据错误类型提供更具体的错误信息
      let errorMsg = 'API调用失败'
      if (apiError.message) {
        errorMsg = apiError.message
      } else if (apiError.response) {
        errorMsg = `服务器错误: ${apiError.response.status}`
      } else if (apiError.request) {
        errorMsg = '网络连接失败，请检查后端服务是否正常运行'
      }
      
      errorMessage.value = errorMsg
      isAnalyzing.value = false
    }
  } catch (error) {
    console.error('分析过程中出错:', error)
    errorMessage.value = error.message || '分析过程中出现错误'
    isAnalyzing.value = false
    uploadProgress.value = 0
  }
}

// 验证状态响应数据
const validateStatusResponse = (response) => {
  if (!response || typeof response !== 'object') {
    throw new Error('状态响应格式无效')
  }
  
  if (!response.status) {
    throw new Error('状态响应缺少status字段')
  }
  
  const validStatuses = ['pending', 'processing', 'completed', 'failed']
  if (!validStatuses.includes(response.status)) {
    throw new Error(`无效的状态值: ${response.status}`)
  }
  
  // 验证进度值
  if (response.progress !== undefined && response.progress !== null) {
    const progress = Number(response.progress)
    if (isNaN(progress) || progress < 0 || progress > 100) {
      console.warn('进度值无效，使用默认值0')
      response.progress = 0
    }
  }
  
  return true
}

// 开始轮询分析状态
const startStatusPolling = () => {
  // 验证任务ID
  if (!analysisTaskId.value) {
    console.error('任务ID不存在，无法开始状态轮询')
    errorMessage.value = '任务ID不存在'
    isAnalyzing.value = false
    return
  }
  
  let pollCount = 0
  const maxPolls = 150 // 最多轮询5分钟 (150 * 2秒)
  
  statusCheckInterval = setInterval(async () => {
    try {
      pollCount++
      
      // 防止无限轮询
      if (pollCount > maxPolls) {
        console.warn('状态轮询超时，停止轮询')
        clearInterval(statusCheckInterval)
        errorMessage.value = '分析超时，请重试'
        isAnalyzing.value = false
        uploadProgress.value = 0
        return
      }
      
      const statusResponse = await climateMonitoringService.getAnalysisStatus(analysisTaskId.value)
      
      if (!statusResponse) {
        throw new Error('无法获取状态响应')
      }
      
      // 验证状态响应
      validateStatusResponse(statusResponse)
      
      analysisStatus.value = statusResponse.status
      
              if (statusResponse.status === 'completed') {
          // 分析完成，获取结果
          uploadProgress.value = 100
          await loadAnalysisResults()
          clearInterval(statusCheckInterval)
          isAnalyzing.value = false
          hasData.value = true
          successMessage.value = '气候数据分析完成！'
          // 5秒后自动清除成功消息
          setTimeout(() => {
            successMessage.value = ''
          }, 5000)
      } else if (statusResponse.status === 'failed') {
        // 分析失败
        errorMessage.value = statusResponse.error_message || '分析失败'
        clearInterval(statusCheckInterval)
        isAnalyzing.value = false
        uploadProgress.value = 0
      } else if (statusResponse.status === 'processing') {
        // 更新进度
        const progress = Number(statusResponse.progress) || 0
        if (progress > 0) {
          uploadProgress.value = Math.max(0, Math.min(100, progress)) // 确保进度在0-100之间
        } else {
          // 如果后端没有返回进度，使用模拟进度
          if (uploadProgress.value < 95) {
            uploadProgress.value += Math.random() * 3
          }
        }
      } else if (statusResponse.status === 'pending') {
        // 任务等待中，缓慢增加进度
        if (uploadProgress.value < 20) {
          uploadProgress.value += Math.random() * 2
        }
      }
      
    } catch (error) {
      console.error('状态检查失败:', error)
      clearInterval(statusCheckInterval)
      isAnalyzing.value = false
      uploadProgress.value = 0
      errorMessage.value = `状态检查失败: ${error.message}`
    }
  }, 2000) // 每2秒检查一次
}

// 验证数据完整性
const validateAnalysisData = (data) => {
  if (!data || typeof data !== 'object') {
    throw new Error('分析数据格式无效')
  }
  
  // 检查必需的统计字段
  const requiredFields = [
    'temperature_avg', 'temperature_max', 'temperature_min', 'temperature_std',
    'precipitation_avg', 'precipitation_max', 'precipitation_min', 'precipitation_std',
    'humidity_avg', 'humidity_max', 'humidity_min', 'humidity_std',
    'wind_speed_avg', 'wind_speed_max', 'wind_speed_min', 'wind_speed_std'
  ]
  
  const missingFields = requiredFields.filter(field => 
    data[field] === undefined || data[field] === null || isNaN(data[field])
  )
  
  if (missingFields.length > 0) {
    console.warn('缺少统计字段:', missingFields)
    // 不抛出错误，而是使用默认值
  }
  
  // 检查图表数据
  if (data.chart_data && typeof data.chart_data === 'object') {
    const chartFields = ['temperature', 'precipitation', 'humidity', 'wind_speed']
    chartFields.forEach(field => {
      if (!Array.isArray(data.chart_data[field])) {
        console.warn(`图表数据字段 ${field} 不是数组`)
        data.chart_data[field] = []
      }
    })
  }
  
  return true
}

// 安全获取数值，提供默认值
const safeGetValue = (value, defaultValue = 0, precision = 1) => {
  if (value === null || value === undefined || isNaN(value)) {
    return defaultValue
  }
  return Number(value).toFixed(precision)
}

// 加载分析结果
const loadAnalysisResults = async () => {
  try {
    // 验证任务ID
    if (!analysisTaskId.value) {
      throw new Error('任务ID不存在，无法加载分析结果')
    }
    
    const resultsResponse = await climateMonitoringService.getAnalysisResults(analysisTaskId.value)
    
    if (!resultsResponse) {
      throw new Error('无法获取分析结果响应')
    }
    
    if (!resultsResponse.success) {
      throw new Error(resultsResponse.message || '分析结果获取失败')
    }
    
    const data = resultsResponse.data
    if (!data) {
      throw new Error('分析结果数据为空')
    }
    
    // 验证数据完整性
    validateAnalysisData(data)
    
    // 更新统计数据 - 使用安全的数值获取
    statistics.value = [
      { 
        indicator: '温度(°C)', 
        average: safeGetValue(data.temperature_avg, 0), 
        max: safeGetValue(data.temperature_max, 0), 
        min: safeGetValue(data.temperature_min, 0), 
        stdDev: safeGetValue(data.temperature_std, 0) 
      },
      { 
        indicator: '降水量(mm)', 
        average: safeGetValue(data.precipitation_avg, 0), 
        max: safeGetValue(data.precipitation_max, 0), 
        min: safeGetValue(data.precipitation_min, 0), 
        stdDev: safeGetValue(data.precipitation_std, 0) 
      },
      { 
        indicator: '湿度(%)', 
        average: safeGetValue(data.humidity_avg, 0), 
        max: safeGetValue(data.humidity_max, 0), 
        min: safeGetValue(data.humidity_min, 0), 
        stdDev: safeGetValue(data.humidity_std, 0) 
      },
      { 
        indicator: '风速(m/s)', 
        average: safeGetValue(data.wind_speed_avg, 0), 
        max: safeGetValue(data.wind_speed_max, 0), 
        min: safeGetValue(data.wind_speed_min, 0), 
        stdDev: safeGetValue(data.wind_speed_std, 0) 
      }
    ]
    
    // 更新图表数据 - 添加验证
    if (data.chart_data && typeof data.chart_data === 'object') {
      chartData.value = {
        temperature: Array.isArray(data.chart_data.temperature) ? data.chart_data.temperature : [],
        precipitation: Array.isArray(data.chart_data.precipitation) ? data.chart_data.precipitation : [],
        humidity: Array.isArray(data.chart_data.humidity) ? data.chart_data.humidity : [],
        windSpeed: Array.isArray(data.chart_data.wind_speed) ? data.chart_data.wind_speed : []
      }
    } else {
      console.warn('图表数据不存在或格式无效，使用空数据')
      chartData.value = {
        temperature: [],
        precipitation: [],
        humidity: [],
        windSpeed: []
      }
    }
    
    // 生成图表
    setTimeout(() => {
      generateCharts()
    }, 100)
    
  } catch (error) {
    console.error('加载分析结果失败:', error)
    errorMessage.value = '加载分析结果失败'
  }
}

// 生成所有图表
const generateCharts = () => {
  console.log('开始生成图表')
  drawTemperatureChart()
  drawPrecipitationChart()
  drawHumidityChart()
  drawWindSpeedChart()
}


// 清理函数
const cleanup = () => {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval)
    statusCheckInterval = null
  }
}

// 组件挂载
onMounted(() => {
  console.log('气候监测组件已挂载')
})

// 组件卸载时清理
onUnmounted(() => {
  cleanup()
})

const drawTemperatureChart = () => {
  const canvas = temperatureChart.value
  console.log('绘制温度图表, canvas:', canvas)
  if (!canvas) {
    console.log('温度图表canvas未找到')
    return
  }
  
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // 使用实际数据
  const data = chartData.value.temperature
  if (!data || data.length === 0) {
    console.log('没有温度数据可绘制')
    return
  }
  
  const maxValue = Math.max(...data)
  const minValue = Math.min(...data)
  const range = maxValue - minValue || 1
  
  // 设置边距 - 增加左边距和底部边距
  const margin = { top: 20, right: 20, bottom: 60, left: 80 }
  const chartWidth = canvas.width - margin.left - margin.right
  const chartHeight = canvas.height - margin.top - margin.bottom
  
  // 绘制背景
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  // 绘制网格
  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 2])
  
  // 水平网格线
  for (let i = 0; i <= 10; i++) {
    const y = margin.top + (chartHeight / 10) * i
    ctx.beginPath()
    ctx.moveTo(margin.left, y)
    ctx.lineTo(canvas.width - margin.right, y)
    ctx.stroke()
  }
  
  // 垂直网格线
  for (let i = 0; i <= 10; i++) {
    const x = margin.left + (chartWidth / 10) * i
    ctx.beginPath()
    ctx.moveTo(x, margin.top)
    ctx.lineTo(x, canvas.height - margin.bottom)
    ctx.stroke()
  }
  
  ctx.setLineDash([])
  
  // 绘制坐标轴
  ctx.strokeStyle = '#333333'
  ctx.lineWidth = 2
  
  // X轴
  ctx.beginPath()
  ctx.moveTo(margin.left, canvas.height - margin.bottom)
  ctx.lineTo(canvas.width - margin.right, canvas.height - margin.bottom)
  ctx.stroke()
  
  // Y轴
  ctx.beginPath()
  ctx.moveTo(margin.left, margin.top)
  ctx.lineTo(margin.left, canvas.height - margin.bottom)
  ctx.stroke()
  
  // 绘制Y轴刻度标签
  ctx.fillStyle = '#666666'
  ctx.font = '11px Arial'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  
  for (let i = 0; i <= 10; i++) {
    const value = minValue + (range / 10) * (10 - i)
    const y = margin.top + (chartHeight / 10) * i
    ctx.fillText(value.toFixed(1), margin.left - 20, y)
  }
  
  // 绘制X轴刻度标签
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  
  const step = Math.max(1, Math.floor(data.length / 8))
  for (let i = 0; i < data.length; i += step) {
    const x = margin.left + (chartWidth / (data.length - 1)) * i
    ctx.fillText((i + 1).toString(), x, canvas.height - margin.bottom + 20)
  }
  
  // 绘制轴标签
  ctx.fillStyle = '#333333'
  ctx.font = 'bold 12px Arial'
  ctx.textAlign = 'center'
  
  // Y轴标签 - 垂直显示，放在刻度左侧
  ctx.save()
  ctx.translate(15, margin.top + chartHeight / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('温度(°C)', 0, 0)
  ctx.restore()
  
  // X轴标签 - 确保完全显示
  ctx.fillText('时间序列', canvas.width / 2, canvas.height - 15)
  
  // 绘制数据线
  ctx.strokeStyle = '#e74c3c'
  ctx.lineWidth = 3
  ctx.beginPath()
  
  data.forEach((value, index) => {
    const x = margin.left + (chartWidth / (data.length - 1)) * index
    const y = margin.top + chartHeight - ((value - minValue) / range) * chartHeight
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // 绘制数据点
  ctx.fillStyle = '#e74c3c'
  data.forEach((value, index) => {
    const x = margin.left + (chartWidth / (data.length - 1)) * index
    const y = margin.top + chartHeight - ((value - minValue) / range) * chartHeight
    
    ctx.beginPath()
    ctx.arc(x, y, 4, 0, 2 * Math.PI)
    ctx.fill()
  })
}

const drawPrecipitationChart = () => {
  const canvas = precipitationChart.value
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // 使用实际数据
  const data = chartData.value.precipitation
  if (!data || data.length === 0) {
    console.log('没有降水量数据可绘制')
    return
  }
  
  const maxValue = Math.max(...data)
  const minValue = Math.min(...data)
  const range = maxValue - minValue || 1
  
  // 设置边距 - 增加左边距和底部边距
  const margin = { top: 20, right: 20, bottom: 60, left: 80 }
  const chartWidth = canvas.width - margin.left - margin.right
  const chartHeight = canvas.height - margin.top - margin.bottom
  
  // 绘制背景
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  // 绘制网格
  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 2])
  
  // 水平网格线
  for (let i = 0; i <= 10; i++) {
    const y = margin.top + (chartHeight / 10) * i
    ctx.beginPath()
    ctx.moveTo(margin.left, y)
    ctx.lineTo(canvas.width - margin.right, y)
    ctx.stroke()
  }
  
  // 垂直网格线
  for (let i = 0; i <= 10; i++) {
    const x = margin.left + (chartWidth / 10) * i
    ctx.beginPath()
    ctx.moveTo(x, margin.top)
    ctx.lineTo(x, canvas.height - margin.bottom)
    ctx.stroke()
  }
  
  ctx.setLineDash([])
  
  // 绘制坐标轴
  ctx.strokeStyle = '#333333'
  ctx.lineWidth = 2
  
  // X轴
  ctx.beginPath()
  ctx.moveTo(margin.left, canvas.height - margin.bottom)
  ctx.lineTo(canvas.width - margin.right, canvas.height - margin.bottom)
  ctx.stroke()
  
  // Y轴
  ctx.beginPath()
  ctx.moveTo(margin.left, margin.top)
  ctx.lineTo(margin.left, canvas.height - margin.bottom)
  ctx.stroke()
  
  // 绘制Y轴刻度标签
  ctx.fillStyle = '#666666'
  ctx.font = '11px Arial'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  
  for (let i = 0; i <= 10; i++) {
    const value = minValue + (range / 10) * (10 - i)
    const y = margin.top + (chartHeight / 10) * i
    ctx.fillText(value.toFixed(1), margin.left - 20, y)
  }
  
  // 绘制X轴刻度标签
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  
  const step = Math.max(1, Math.floor(data.length / 8))
  for (let i = 0; i < data.length; i += step) {
    const x = margin.left + (chartWidth / data.length) * (i + 0.5)
    ctx.fillText((i + 1).toString(), x, canvas.height - margin.bottom + 20)
  }
  
  // 绘制轴标签
  ctx.fillStyle = '#333333'
  ctx.font = 'bold 12px Arial'
  ctx.textAlign = 'center'
  
  // Y轴标签 - 垂直显示，放在刻度左侧
  ctx.save()
  ctx.translate(15, margin.top + chartHeight / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('降水量(mm)', 0, 0)
  ctx.restore()
  
  // X轴标签 - 确保完全显示
  ctx.fillText('时间序列', canvas.width / 2, canvas.height - 15)
  
  // 绘制柱状图
  const barWidth = chartWidth / data.length
  ctx.fillStyle = '#2ecc71'
  
  data.forEach((value, index) => {
    const barHeight = ((value - minValue) / range) * chartHeight
    const x = margin.left + (chartWidth / data.length) * index
    const y = margin.top + chartHeight - barHeight
    
    ctx.fillRect(x, y, barWidth - 2, barHeight)
  })
}

const drawHumidityChart = () => {
  const canvas = humidityChart.value
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // 使用实际数据
  const data = chartData.value.humidity
  if (!data || data.length === 0) {
    console.log('没有湿度数据可绘制')
    return
  }
  
  const maxValue = Math.max(...data)
  const minValue = Math.min(...data)
  const range = maxValue - minValue || 1
  
  // 设置边距 - 增加左边距和底部边距
  const margin = { top: 20, right: 20, bottom: 60, left: 80 }
  const chartWidth = canvas.width - margin.left - margin.right
  const chartHeight = canvas.height - margin.top - margin.bottom
  
  // 绘制背景
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  // 绘制网格
  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 2])
  
  // 水平网格线
  for (let i = 0; i <= 10; i++) {
    const y = margin.top + (chartHeight / 10) * i
    ctx.beginPath()
    ctx.moveTo(margin.left, y)
    ctx.lineTo(canvas.width - margin.right, y)
    ctx.stroke()
  }
  
  // 垂直网格线
  for (let i = 0; i <= 10; i++) {
    const x = margin.left + (chartWidth / 10) * i
    ctx.beginPath()
    ctx.moveTo(x, margin.top)
    ctx.lineTo(x, canvas.height - margin.bottom)
    ctx.stroke()
  }
  
  ctx.setLineDash([])
  
  // 绘制坐标轴
  ctx.strokeStyle = '#333333'
  ctx.lineWidth = 2
  
  // X轴
  ctx.beginPath()
  ctx.moveTo(margin.left, canvas.height - margin.bottom)
  ctx.lineTo(canvas.width - margin.right, canvas.height - margin.bottom)
  ctx.stroke()
  
  // Y轴
  ctx.beginPath()
  ctx.moveTo(margin.left, margin.top)
  ctx.lineTo(margin.left, canvas.height - margin.bottom)
  ctx.stroke()
  
  // 绘制Y轴刻度标签
  ctx.fillStyle = '#666666'
  ctx.font = '11px Arial'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  
  for (let i = 0; i <= 10; i++) {
    const value = minValue + (range / 10) * (10 - i)
    const y = margin.top + (chartHeight / 10) * i
    ctx.fillText(value.toFixed(1), margin.left - 20, y)
  }
  
  // 绘制X轴刻度标签
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  
  const step = Math.max(1, Math.floor(data.length / 8))
  for (let i = 0; i < data.length; i += step) {
    const x = margin.left + (chartWidth / (data.length - 1)) * i
    ctx.fillText((i + 1).toString(), x, canvas.height - margin.bottom + 20)
  }
  
  // 绘制轴标签
  ctx.fillStyle = '#333333'
  ctx.font = 'bold 12px Arial'
  ctx.textAlign = 'center'
  
  // Y轴标签 - 垂直显示，放在刻度左侧
  ctx.save()
  ctx.translate(15, margin.top + chartHeight / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('湿度(%)', 0, 0)
  ctx.restore()
  
  // X轴标签 - 确保完全显示
  ctx.fillText('时间序列', canvas.width / 2, canvas.height - 15)
  
  // 绘制面积图
  ctx.fillStyle = 'rgba(52, 152, 219, 0.3)'
  ctx.strokeStyle = '#3498db'
  ctx.lineWidth = 2
  
  ctx.beginPath()
  ctx.moveTo(margin.left, canvas.height - margin.bottom)
  
  data.forEach((value, index) => {
    const x = margin.left + (chartWidth / (data.length - 1)) * index
    const y = margin.top + chartHeight - ((value - minValue) / range) * chartHeight
    ctx.lineTo(x, y)
  })
  
  ctx.lineTo(canvas.width - margin.right, canvas.height - margin.bottom)
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
}

const drawWindSpeedChart = () => {
  const canvas = windSpeedChart.value
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // 使用实际数据
  const data = chartData.value.windSpeed
  if (!data || data.length === 0) {
    console.log('没有风速数据可绘制')
    return
  }
  
  const maxValue = Math.max(...data)
  const minValue = Math.min(...data)
  const range = maxValue - minValue || 1
  
  // 雷达图居中显示，使用较小的边距
  const margin = { top: 40, right: 40, bottom: 40, left: 40 }
  const chartWidth = canvas.width - margin.left - margin.right
  const chartHeight = canvas.height - margin.top - margin.bottom
  
  // 绘制背景
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  // 计算中心点和半径 - 完全居中
  const centerX = canvas.width / 2
  const centerY = canvas.height / 2
  const radius = Math.min(chartWidth, chartHeight) / 2 - 30
  
  // 绘制网格圆
  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 2])
  
  for (let i = 1; i <= 5; i++) {
    const r = (radius / 5) * i
    ctx.beginPath()
    ctx.arc(centerX, centerY, r, 0, 2 * Math.PI)
    ctx.stroke()
  }
  
  // 绘制径向线
  for (let i = 0; i < 8; i++) {
    const angle = (i / 8) * 2 * Math.PI
    const x = centerX + Math.cos(angle) * radius
    const y = centerY + Math.sin(angle) * radius
    
    ctx.beginPath()
    ctx.moveTo(centerX, centerY)
    ctx.lineTo(x, y)
    ctx.stroke()
  }
  
  ctx.setLineDash([])
  
  // 绘制坐标轴标签
  ctx.fillStyle = '#666666'
  ctx.font = '11px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  
  // 绘制刻度标签
  for (let i = 1; i <= 5; i++) {
    const value = minValue + (range / 5) * i
    const y = centerY - (radius / 5) * i
    ctx.fillText(value.toFixed(1), centerX + radius + 15, y)
  }
  
  // 绘制方向标签
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  for (let i = 0; i < 8; i++) {
    const angle = (i / 8) * 2 * Math.PI
    const x = centerX + Math.cos(angle) * (radius + 20)
    const y = centerY + Math.sin(angle) * (radius + 20)
    ctx.fillText(directions[i], x, y)
  }
  
  // 绘制标题
  ctx.fillStyle = '#333333'
  ctx.font = 'bold 12px Arial'
  ctx.fillText('风速分布(m/s)', centerX, 20)
  
  // 绘制雷达图
  ctx.fillStyle = 'rgba(231, 76, 60, 0.3)'
  ctx.strokeStyle = '#e74c3c'
  ctx.lineWidth = 2
  ctx.beginPath()
  
  data.forEach((value, index) => {
    const angle = (index / data.length) * 2 * Math.PI - Math.PI / 2
    const normalizedValue = (value - minValue) / range
    const r = normalizedValue * radius
    const x = centerX + Math.cos(angle) * r
    const y = centerY + Math.sin(angle) * r
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
  
  // 绘制数据点
  ctx.fillStyle = '#e74c3c'
  data.forEach((value, index) => {
    const angle = (index / data.length) * 2 * Math.PI - Math.PI / 2
    const normalizedValue = (value - minValue) / range
    const r = normalizedValue * radius
    const x = centerX + Math.cos(angle) * r
    const y = centerY + Math.sin(angle) * r
    
    ctx.beginPath()
    ctx.arc(x, y, 3, 0, 2 * Math.PI)
    ctx.fill()
  })
}
</script>

<style scoped>
.climate-monitoring {
  min-height: 100vh;
  background: white;
  padding: 0;
  margin: 0;
  overflow-x: auto;
  overflow-y: auto;
}

/* 自定义滚动条样式 */
.climate-monitoring::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.climate-monitoring::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.climate-monitoring::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.climate-monitoring::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.main-container {
  display: flex;
  min-height: 100vh;
  min-width: 1200px; /* 确保最小宽度，避免内容被压缩 */
}

.left-panel {
  width: 350px;
  background: white;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 12px rgba(0,0,0,0.08);
  overflow-y: auto;
}

/* 左侧面板滚动条样式 */
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

.panel-header {
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
  color: white;
  padding: 20px 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
}

.panel-header h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.panel-header p {
  margin: 8px 0 0 0;
  font-size: 12px;
  opacity: 0.9;
  line-height: 1.4;
}

/* 功能区块 */
.section {
  padding: 20px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.section:last-child {
  border-bottom: none;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  font-weight: 600;
  color: #333;
  font-size: 15px;
}

.section-icon {
  font-size: 16px;
}

.section-content {
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 文件上传区域 */
.file-upload-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upload-zone {
  width: 100%;
  background: #f8f9fa;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-zone:hover {
  border-color: #1890ff;
  background: #f0f8ff;
}

.upload-icon {
  font-size: 24px;
  color: #1890ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.upload-icon svg {
  width: 48px;
  height: 48px;
}

.upload-text {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.upload-hint {
  font-size: 12px;
  color: #666;
}

.upload-types {
  font-size: 11px;
  color: #999;
}

.file-status {
  font-size: 12px;
  color: #666;
  text-align: center;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #1890ff;
}

.analysis-btn {
  width: 100%;
  background: #1890ff;
  color: white;
  border: none;
  padding: 14px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.analysis-btn:hover:not(.disabled) {
  background: #40a9ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(24, 144, 255, 0.3);
}

.analysis-btn.disabled {
  cursor: not-allowed;
  background: #f5f5f5;
  color: #999;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

/* 进度指示器样式 */
.progress-section {
  margin-top: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 3px solid #1890ff;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1890ff 0%, #40a9ff 100%);
  transition: width 0.5s ease-in-out;
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-text {
  font-size: 13px;
  color: #666;
  text-align: center;
  font-weight: 500;
}

.error-message {
  background: #fff2f0;
  color: #ff4d4f;
  padding: 16px;
  border-radius: 8px;
  margin-top: 16px;
  border: 1px solid #ffccc7;
  font-size: 14px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(255, 77, 79, 0.1);
  border-left: 4px solid #ff4d4f;
}

.error-icon {
  font-size: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.error-content {
  flex: 1;
}

.error-title {
  font-weight: 600;
  margin-bottom: 5px;
  font-size: 15px;
}

.error-details {
  margin-bottom: 10px;
  line-height: 1.4;
}

.error-actions {
  display: flex;
  gap: 8px;
}

.retry-btn, .dismiss-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-btn {
  background: #1890ff;
  color: white;
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.2);
}

.retry-btn:hover {
  background: #40a9ff;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(24, 144, 255, 0.3);
}

.dismiss-btn {
  background: #f5f5f5;
  color: #666;
  border: 1px solid #d9d9d9;
}

.dismiss-btn:hover {
  background: #e6f7ff;
  border-color: #1890ff;
  color: #1890ff;
}

.success-message {
  background: #f6ffed;
  color: #52c41a;
  padding: 16px;
  border-radius: 8px;
  margin-top: 16px;
  border: 1px solid #b7eb8f;
  font-size: 14px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(82, 196, 26, 0.1);
  border-left: 4px solid #52c41a;
}

.success-icon {
  font-size: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.success-content {
  flex: 1;
}

.success-title {
  font-weight: 600;
  margin-bottom: 5px;
  font-size: 15px;
}

.success-details {
  margin-bottom: 10px;
  line-height: 1.4;
}

.success-actions {
  display: flex;
  gap: 8px;
}

.right-panel {
  flex: 1;
  background: white;
  display: flex;
  flex-direction: column;
  padding: 40px;
  overflow-y: auto;
  overflow-x: auto;
  max-height: 100vh;
}

/* 右侧面板滚动条样式 */
.right-panel::-webkit-scrollbar {
  width: 6px;
}

.right-panel::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.right-panel::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.right-panel::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.placeholder {
  text-align: center;
  color: #999;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.placeholder-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: #c3ccd6;
  opacity: 0.5;
}

.placeholder p {
  font-size: 14px;
  color: #999;
  margin: 0;
}

.analysis-results {
  animation: fadeIn 0.5s ease-in;
  width: 100%;
  height: 100%;
  display: block;
  padding: 20px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.stats-overview {
  margin-bottom: 30px;
}

.stats-overview h3 {
  color: #333;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.stat-item {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #007bff;
}

.stat-label {
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
  font-size: 14px;
}

.stat-values {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat-value {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e9ecef;
}

.stat-value:last-child {
  border-bottom: none;
}

.stat-value .label {
  color: #6c757d;
  font-size: 12px;
}

.stat-value .value {
  color: #333;
  font-weight: 600;
  font-size: 14px;
}

.charts-section h3 {
  color: #333;
  margin-bottom: 25px;
  font-size: 18px;
  font-weight: 600;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 25px;
  width: 100%;
  min-width: 800px; /* 确保图表网格最小宽度 */
}

.chart-container {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  min-width: 400px; /* 确保图表容器最小宽度 */
  overflow: hidden; /* 防止内容溢出 */
}

.chart-container h4 {
  color: #495057;
  margin-bottom: 15px;
  font-size: 14px;
  text-align: center;
  font-weight: 500;
}

.chart-container canvas {
  width: 100%;
  height: 200px;
  border-radius: 6px;
  background: white;
  max-width: 100%;
  display: block;
}


/* 响应式设计 */
@media (max-width: 1200px) {
  .main-container {
    flex-direction: column;
  }
  
  .left-panel {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e0e0e0;
    padding: 30px;
  }
  
  .right-panel {
    min-height: 400px;
  }
}

@media (max-width: 768px) {
  .main-container {
    flex-direction: column;
    min-width: 100%;
  }
  
  .left-panel {
    padding: 20px;
    width: 100%;
  }
  
  .right-panel {
    padding: 20px;
    min-height: 300px;
    max-height: none;
  }
  
  .charts-grid {
    grid-template-columns: 1fr;
    min-width: 100%;
  }
  
  .chart-container {
    min-width: 100%;
  }
  
  .chart-container canvas {
    height: 150px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
