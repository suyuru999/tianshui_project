<template>
  <div v-if="visible" class="overlay-analysis-popup">
    <div class="popup-header">
      <h3>叠加分析与监控</h3>
      <button class="close-btn" @click="close">×</button>
    </div>
    
    <div class="popup-content">
      <!-- 坐标信息 -->
      <div class="section">
        <div class="section-title">📍 位置信息</div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">经度:</span>
            <span class="value">{{ formatCoordinate(coordinate.lng) }}</span>
          </div>
          <div class="info-item">
            <span class="label">纬度:</span>
            <span class="value">{{ formatCoordinate(coordinate.lat) }}</span>
          </div>
        </div>
      </div>

      <!-- 生态栅格信息 -->
      <div class="section" v-if="ecologyData">
        <div class="section-title">🌿 生态指数</div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">生态指数值:</span>
            <span class="value" :class="getEcologyLevelClass(ecologyData.value)">
              {{ formatEcologyValue(ecologyData.value) }}
            </span>
          </div>
          <div class="info-item" v-if="ecologyData.level">
            <span class="label">生态等级:</span>
            <span class="value" :class="getEcologyLevelClass(ecologyData.value)">
              {{ ecologyData.level }}
            </span>
          </div>
        </div>
        <div class="risk-indicator" :class="getEcologyRiskClass(ecologyData.value)">
          <span class="indicator-icon">{{ getEcologyRiskIcon(ecologyData.value) }}</span>
          <span class="indicator-text">{{ getEcologyRiskText(ecologyData.value) }}</span>
        </div>
      </div>
      <div class="section" v-else>
        <div class="section-title">🌿 生态指数</div>
        <div class="no-data">该位置无生态指数数据</div>
      </div>

      <!-- 经济矢量信息 -->
      <div class="section" v-if="economyData">
        <div class="section-title">💰 经济数据</div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">区域名称:</span>
            <span class="value">{{ economyData.admin_name || '未知' }}</span>
          </div>
          <div class="info-item">
            <span class="label">GDP (亿元):</span>
            <span class="value" :class="getGDPLevelClass(economyData.GDP)">
              {{ formatGDP(economyData.GDP) }}
            </span>
          </div>
          <div class="info-item">
            <span class="label">人口:</span>
            <span class="value">{{ formatPopulation(economyData.POP) }}</span>
          </div>
          <div class="info-item" v-if="economyData.area_km2">
            <span class="label">面积:</span>
            <span class="value">{{ formatArea(economyData.area_km2) }}</span>
          </div>
        </div>
        <div class="risk-indicator" :class="getGDPLevelClass(economyData.GDP)">
          <span class="indicator-icon">💰</span>
          <span class="indicator-text">{{ getGDPLevelText(economyData.GDP) }}</span>
        </div>
      </div>
      <div class="section" v-else>
        <div class="section-title">💰 经济数据</div>
        <div class="no-data">该位置无经济数据</div>
      </div>

      <!-- 工程矢量信息 -->
      <div class="section" v-if="engineeringData && engineeringData.length > 0">
        <div class="section-title">🏗️ 工程项目</div>
        <div class="project-list">
          <div 
            v-for="(project, index) in engineeringData" 
            :key="index"
            class="project-item"
          >
            <div class="project-header">
              <span class="project-name">{{ project.proj_name || '未知工程' }}</span>
              <span class="project-status" :class="getStatusClass(project.status)">
                {{ project.status || '未知' }}
              </span>
            </div>
            <div class="project-details">
              <div class="detail-item">
                <span class="label">类型:</span>
                <span class="value">{{ project.proj_type || '未知' }}</span>
              </div>
              <div class="detail-item" v-if="project.area_km2">
                <span class="label">面积:</span>
                <span class="value">{{ formatArea(project.area_km2) }}</span>
              </div>
              <div class="detail-item" v-if="project.start_date">
                <span class="label">开始时间:</span>
                <span class="value">{{ project.start_date }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="section" v-else>
        <div class="section-title">🏗️ 工程项目</div>
        <div class="no-data">该位置无工程项目</div>
      </div>

      <!-- 风险分析 -->
      <div class="section risk-analysis" v-if="riskAnalysis">
        <div class="section-title">⚠️ 风险分析</div>
        <div class="risk-summary">
          <div class="risk-item" :class="riskAnalysis.level">
            <span class="risk-icon">{{ getRiskIcon(riskAnalysis.level) }}</span>
            <span class="risk-text">{{ riskAnalysis.text }}</span>
          </div>
          <div class="risk-details" v-if="riskAnalysis.details">
            <div class="detail-text">{{ riskAnalysis.details }}</div>
          </div>
        </div>
      </div>

      <!-- 决策建议 -->
      <div class="section decision-recommendation" v-if="riskAnalysis && riskAnalysis.recommendation">
        <div class="section-title">💡 决策建议</div>
        <div class="recommendation-content">
          <div class="recommendation-text">{{ riskAnalysis.recommendation }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  coordinate: {
    type: Object,
    default: () => ({ lng: 0, lat: 0 })
  },
  ecologyData: {
    type: Object,
    default: null
  },
  economyData: {
    type: Object,
    default: null
  },
  engineeringData: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close'])

const close = () => {
  emit('close')
}

// 格式化坐标
const formatCoordinate = (coord) => {
  if (coord === null || coord === undefined || isNaN(coord) || coord === 'NaN') {
    return 'N/A'
  }
  if (typeof coord === 'number') {
    return coord.toFixed(4)
  }
  if (typeof coord === 'string' && coord !== 'NaN') {
    return coord
  }
  return 'N/A'
}

// 格式化生态指数值
const formatEcologyValue = (value) => {
  if (value === null || value === undefined) return 'N/A'
  // 如果是DEM风格的值（50-1000），转换为生态指数风格（0-1）
  if (value >= 50 && value <= 1000) {
    return ((value - 50) / 950).toFixed(3)
  }
  return value.toFixed(3)
}

// 获取生态等级
const getEcologyLevelClass = (value) => {
  if (value === null || value === undefined) return 'unknown'
  
  // 处理DEM风格的值（50-1000）
  let normalizedValue = value
  if (value >= 50 && value <= 1000) {
    normalizedValue = (value - 50) / 950
  }
  
  if (normalizedValue >= 0.6) return 'excellent'
  if (normalizedValue >= 0.4) return 'good'
  if (normalizedValue >= 0.2) return 'moderate'
  return 'poor'
}

// 获取生态风险等级
const getEcologyRiskClass = (value) => {
  const level = getEcologyLevelClass(value)
  if (level === 'poor') return 'high-risk'
  if (level === 'moderate') return 'medium-risk'
  return 'low-risk'
}

const getEcologyRiskIcon = (value) => {
  const level = getEcologyLevelClass(value)
  if (level === 'poor') return '🔴'
  if (level === 'moderate') return '🟡'
  return '🟢'
}

const getEcologyRiskText = (value) => {
  const level = getEcologyLevelClass(value)
  if (level === 'poor') return '生态指数较差，需要关注'
  if (level === 'moderate') return '生态指数中等'
  return '生态指数良好'
}

// 格式化GDP
const formatGDP = (gdp) => {
  if (gdp === null || gdp === undefined) return 'N/A'
  return gdp.toFixed(1)
}

// 获取GDP等级
const getGDPLevelClass = (gdp) => {
  if (gdp === null || gdp === undefined) return 'unknown'
  if (gdp >= 500) return 'high'
  if (gdp >= 100) return 'medium'
  return 'low'
}

const getGDPLevelText = (gdp) => {
  const level = getGDPLevelClass(gdp)
  if (level === 'high') return '高GDP区域'
  if (level === 'medium') return '中GDP区域'
  return '低GDP区域'
}

// 格式化人口
const formatPopulation = (pop) => {
  if (pop === null || pop === undefined) return 'N/A'
  if (pop >= 10000) {
    return (pop / 10000).toFixed(1) + '万'
  }
  return pop.toString()
}

// 格式化面积
const formatArea = (area) => {
  if (area === null || area === undefined) return 'N/A'
  return area.toFixed(2) + ' km²'
}

// 获取状态样式类
const getStatusClass = (status) => {
  if (!status) return 'unknown'
  if (status === '已完工') return 'completed'
  if (status === '进行中') return 'ongoing'
  if (status === '规划中') return 'planned'
  return 'unknown'
}

// 计算风险分析
const riskAnalysis = computed(() => {
  const hasEcology = props.ecologyData && props.ecologyData.value !== null
  const hasEconomy = props.economyData && props.economyData.GDP !== null
  const hasEngineering = props.engineeringData && props.engineeringData.length > 0
  
  if (!hasEcology && !hasEconomy) return null
  
  let riskLevel = 'low'
  let riskText = '风险较低'
  let riskDetails = ''
  let recommendation = ''
  
  // 生态指数较差
  const ecologyPoor = hasEcology && getEcologyLevelClass(props.ecologyData.value) === 'poor'
  // 生态指数中等
  const ecologyModerate = hasEcology && getEcologyLevelClass(props.ecologyData.value) === 'moderate'
  // GDP高
  const economyHigh = hasEconomy && getGDPLevelClass(props.economyData.GDP) === 'high'
  // GDP中等
  const economyMedium = hasEconomy && getGDPLevelClass(props.economyData.GDP) === 'medium'
  // 人口多（假设>50万为多）
  const populationHigh = hasEconomy && props.economyData.POP && props.economyData.POP > 500000
  // 无治理工程
  const noEngineering = !hasEngineering || props.engineeringData.length === 0
  
  // 风险等级判断逻辑
  // 极高风险场景：生态差 + 高GDP + 无治理工程
  if (ecologyPoor && economyHigh && noEngineering) {
    riskLevel = 'critical'
    riskText = '⚠️ 极高风险'
    riskDetails = '该位置生态指数较差（红色），且位于高GDP区域（红色），但无工程项目。'
    recommendation = '建议尽快部署生态修复工程，优先考虑生态敏感区域保护。'
  } 
  // 高风险场景：生态差 + 中GDP + 无治理工程
  else if (ecologyPoor && economyMedium && noEngineering) {
    riskLevel = 'high'
    riskText = '⚠️ 高风险'
    riskDetails = '该位置生态指数较差（红色），且位于中GDP区域（橙色），但无工程项目。'
    recommendation = '建议部署生态修复工程，加强生态保护措施。'
  }
  // 中高风险场景：生态差 + 无治理工程
  else if (ecologyPoor && noEngineering) {
    riskLevel = 'high'
    riskText = '⚠️ 中高风险'
    riskDetails = '该位置生态指数较差（红色），但无工程项目。'
    recommendation = '建议考虑部署生态修复工程，改善生态环境质量。'
  }
  // 中等风险场景：生态中等 + 高GDP + 无治理工程
  else if (ecologyModerate && economyHigh && noEngineering) {
    riskLevel = 'medium'
    riskText = '⚠️ 中等风险'
    riskDetails = '该位置生态指数中等（黄色），且位于高GDP区域（红色），但无工程项目。'
    recommendation = '建议加强生态监测，必要时部署生态修复工程。'
  }
  // 中等风险场景：生态中等 + 无治理工程
  else if (ecologyModerate && noEngineering) {
    riskLevel = 'medium'
    riskText = '⚠️ 中等风险'
    riskDetails = '该位置生态指数中等（黄色），但无工程项目。'
    recommendation = '建议加强生态监测，预防生态恶化。'
  }
  // 低风险场景：已有治理工程
  else if (hasEngineering) {
    riskLevel = 'low'
    riskText = '✅ 已有治理工程'
    riskDetails = '该位置已有工程项目，生态风险相对可控。'
    recommendation = '建议持续监控工程效果，确保生态修复效果。'
  }
  // 低风险场景：生态良好
  else if (hasEcology && !ecologyPoor && !ecologyModerate) {
    riskLevel = 'low'
    riskText = '✅ 生态状况良好'
    riskDetails = '该位置生态指数良好（绿色），生态风险较低。'
    recommendation = '建议继续保持良好的生态环境，定期监测。'
  }
  
  return {
    level: riskLevel,
    text: riskText,
    details: riskDetails,
    recommendation: recommendation
  }
})

const getRiskIcon = (level) => {
  if (level === 'critical') return '🔴'
  if (level === 'high') return '🟠'
  if (level === 'medium') return '🟡'
  return '🟢'
}
</script>

<style scoped>
.overlay-analysis-popup {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  min-width: 450px;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  z-index: 2000;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 2px solid #f0f0f0;
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
  color: white;
  border-radius: 12px 12px 0 0;
}

.popup-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: white;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.popup-content {
  padding: 20px 24px;
}

.section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.info-item .value {
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

/* 生态等级颜色 */
.value.excellent {
  color: #52c41a;
}

.value.good {
  color: #73d13d;
}

.value.moderate {
  color: #faad14;
}

.value.poor {
  color: #ff4d4f;
}

/* GDP等级颜色 */
.value.high {
  color: #ff4d4f;
}

.value.medium {
  color: #faad14;
}

.value.low {
  color: #52c41a;
}

.risk-indicator {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
}

.risk-indicator.high-risk {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #cf1322;
}

.risk-indicator.medium-risk {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  color: #d48806;
}

.risk-indicator.low-risk {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #389e0d;
}

.indicator-icon {
  font-size: 16px;
}

.no-data {
  color: #999;
  font-size: 13px;
  font-style: italic;
  padding: 8px 0;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-item {
  background: #fafafa;
  border-radius: 6px;
  padding: 12px;
  border: 1px solid #e8e8e8;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.project-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.project-status {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.project-status.completed {
  background: #f6ffed;
  color: #52c41a;
}

.project-status.ongoing {
  background: #fffbe6;
  color: #faad14;
}

.project-status.planned {
  background: #e6f7ff;
  color: #1890ff;
}

.project-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.detail-item .label {
  color: #666;
}

.detail-item .value {
  color: #333;
  font-weight: 500;
}

.risk-analysis {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  border: 2px solid #e8e8e8;
}

.risk-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  padding: 10px;
  border-radius: 6px;
}

.risk-item.critical {
  background: #fff2f0;
  color: #cf1322;
}

.risk-item.high {
  background: #fff7e6;
  color: #d46b08;
}

.risk-item.medium {
  background: #fffbe6;
  color: #d48806;
}

.risk-item.low {
  background: #f6ffed;
  color: #389e0d;
}

.risk-icon {
  font-size: 18px;
}

.risk-details {
  padding: 8px 12px;
  background: white;
  border-radius: 4px;
  font-size: 13px;
  color: #666;
  line-height: 1.6;
}

.detail-text {
  margin: 0;
}

.decision-recommendation {
  background: #f0f9ff;
  border-radius: 8px;
  padding: 16px;
  border: 2px solid #91d5ff;
}

.recommendation-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recommendation-text {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
  padding: 12px;
  background: white;
  border-radius: 6px;
  border-left: 4px solid #1890ff;
}
</style>

