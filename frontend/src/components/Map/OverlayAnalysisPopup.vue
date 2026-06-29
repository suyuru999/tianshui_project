<template>
  <div v-if="visible" class="overlay-analysis-popup">
    <div class="popup-header">
      <div class="header-copy">
        <span class="header-kicker">Overlay Insight</span>
        <h3>叠加分析与监控</h3>
      </div>
      <button class="close-btn" @click="close" aria-label="关闭弹窗">×</button>
    </div>
    
    <div class="popup-content">
      <!-- 坐标信息 -->
      <div class="section">
        <div class="section-title"><span class="section-icon">📍</span><span>位置信息</span></div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">经度</span>
            <span class="value">{{ formatCoordinate(coordinate.lng) }}</span>
          </div>
          <div class="info-item">
            <span class="label">纬度</span>
            <span class="value">{{ formatCoordinate(coordinate.lat) }}</span>
          </div>
        </div>
      </div>

      <!-- 生态栅格信息 -->
      <div class="section" v-if="ecologyData">
        <div class="section-title"><span class="section-icon">🌿</span><span>生态指数</span></div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">生态指数值</span>
            <span class="value" :class="getEcologyLevelClass(ecologyData.value)">
              {{ formatEcologyValue(ecologyData.value) }}
            </span>
          </div>
          <div class="info-item" v-if="ecologyData.level">
            <span class="label">生态等级</span>
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
        <div class="section-title"><span class="section-icon">🌿</span><span>生态指数</span></div>
        <div class="no-data">该位置无生态指数数据</div>
      </div>

      <!-- 经济矢量信息 -->
      <div class="section" v-if="economyData">
        <div class="section-title"><span class="section-icon">💰</span><span>经济数据</span></div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">区域名称</span>
            <span class="value">{{ economyData.admin_name || economyData.ADMIN_NAME || '未知' }}</span>
          </div>
          <div class="info-item">
            <span class="label">GDP（亿元）</span>
            <span class="value" :class="getGDPLevelClass(economyData.GDP)">
              {{ formatGDP(economyData.GDP) }}
            </span>
          </div>
          <div class="info-item">
            <span class="label">人口</span>
            <span class="value">{{ formatPopulation(economyData.POP) }}</span>
          </div>
          <div class="info-item" v-if="economyData.area_km2">
            <span class="label">面积</span>
            <span class="value">{{ formatArea(economyData.area_km2) }}</span>
          </div>
        </div>
        <div class="risk-indicator" :class="getGDPLevelClass(economyData.GDP)">
          <span class="indicator-icon">💰</span>
          <span class="indicator-text">{{ getGDPLevelText(economyData.GDP) }}</span>
        </div>
      </div>
      <div class="section" v-else>
        <div class="section-title"><span class="section-icon">💰</span><span>经济数据</span></div>
        <div class="no-data">该位置无经济数据</div>
      </div>

      <!-- 工程矢量信息 -->
      <div class="section" v-if="engineeringData && engineeringData.length > 0">
        <div class="section-title"><span class="section-icon">🏗️</span><span>工程项目</span></div>
        <div class="project-list">
          <div 
            v-for="(project, index) in engineeringData" 
            :key="index"
            class="project-item"
          >
            <div class="project-header">
              <span class="project-name">{{ project.proj_name || project.PROJ_NAME || '未知工程' }}</span>
              <span class="project-status" :class="getStatusClass(project.status)">
                {{ project.status || project.STATUS || '未知' }}
              </span>
            </div>
            <div class="project-details">
              <div class="detail-item">
                <span class="label">类型</span>
                <span class="value">{{ project.proj_type || project.PROJ_TYPE || '未知' }}</span>
              </div>
              <div class="detail-item" v-if="project.area_km2">
                <span class="label">面积</span>
                <span class="value">{{ formatArea(project.area_km2) }}</span>
              </div>
              <div class="detail-item" v-if="project.start_date">
                <span class="label">开始时间</span>
                <span class="value">{{ project.start_date }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="section" v-else>
        <div class="section-title"><span class="section-icon">🏗️</span><span>工程项目</span></div>
        <div class="no-data">该位置无工程项目</div>
      </div>

      <!-- 风险分析 -->
      <div class="section risk-analysis" v-if="riskAnalysis">
        <div class="section-title"><span class="section-icon">⚠️</span><span>风险分析</span></div>
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
        <div class="section-title"><span class="section-icon">💡</span><span>决策建议</span></div>
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
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(219, 227, 236, 0.92);
  border-radius: 24px;
  box-shadow: 0 24px 54px rgba(31, 53, 83, 0.18);
  backdrop-filter: blur(14px);
  min-width: 460px;
  max-width: 640px;
  max-height: 82vh;
  overflow-y: auto;
  z-index: 2000;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px 28px 22px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.18);
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.22), transparent 32%),
    linear-gradient(135deg, #1c7ed6 0%, #4ba3ea 100%);
  color: white;
  border-radius: 24px 24px 0 0;
}

.header-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.header-kicker {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.72);
}

.popup-header h3 {
  margin: 0;
  font-size: 30px;
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.close-btn {
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.22);
  font-size: 28px;
  cursor: pointer;
  color: white;
  padding: 0;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.24);
  border-color: rgba(255, 255, 255, 0.32);
  transform: rotate(90deg);
}

.popup-content {
  padding: 20px 28px 28px;
  background:
    linear-gradient(180deg, rgba(244, 247, 250, 0.42) 0%, rgba(255, 255, 255, 0.96) 20%),
    #ffffff;
}

.section {
  margin-bottom: 18px;
  padding: 18px 4px 20px;
  border-bottom: 1px solid #e8eff5;
}

.section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #24384d;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  letter-spacing: 0.01em;
}

.section-icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: linear-gradient(135deg, #eef5fb 0%, #f8fbfd 100%);
  box-shadow: inset 0 0 0 1px #dbe6f0;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 92px;
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f8fb 100%);
  border: 1px solid #e1e9f0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.info-item .label {
  font-size: 12px;
  color: #708398;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.info-item .value {
  font-size: 15px;
  color: #26384a;
  font-weight: 700;
  line-height: 1.5;
  word-break: break-word;
}

/* 生态等级颜色 */
.value.excellent {
  color: #1f8f4d;
}

.value.good {
  color: #4c9a2a;
}

.value.moderate {
  color: #cf8a18;
}

.value.poor {
  color: #d64545;
}

/* GDP等级颜色 */
.value.high {
  color: #d64545;
}

.value.medium {
  color: #cf8a18;
}

.value.low {
  color: #1f8f4d;
}

.risk-indicator {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
}

.risk-indicator.high-risk {
  background: #fff4f2;
  border: 1px solid #ffd6d2;
  color: #be3f3f;
}

.risk-indicator.medium-risk {
  background: #fff9ec;
  border: 1px solid #f4deb0;
  color: #b97b12;
}

.risk-indicator.low-risk {
  background: #f3fbf4;
  border: 1px solid #cfe7d3;
  color: #2e7b45;
}

.indicator-icon {
  font-size: 17px;
}

.no-data {
  color: #8a9aab;
  font-size: 13px;
  padding: 16px 18px;
  border-radius: 16px;
  background: linear-gradient(180deg, #fbfdff 0%, #f5f8fb 100%);
  border: 1px dashed #d4e0ea;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.project-item {
  background: linear-gradient(180deg, #fbfdff 0%, #f5f8fb 100%);
  border-radius: 18px;
  padding: 16px;
  border: 1px solid #dfe7ef;
  box-shadow: 0 10px 22px rgba(46, 72, 98, 0.06);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.project-name {
  font-size: 15px;
  font-weight: 700;
  color: #25384a;
}

.project-status {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.project-status.completed {
  background: #edf9ef;
  color: #2e7b45;
}

.project-status.ongoing {
  background: #fff8e8;
  color: #b97b12;
}

.project-status.planned {
  background: #eef6ff;
  color: #1e6fc8;
}

.project-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 12px;
  padding-top: 8px;
  border-top: 1px dashed #dde6ee;
}

.detail-item .label {
  color: #718396;
}

.detail-item .value {
  color: #24384d;
  font-weight: 600;
  text-align: right;
}

.risk-analysis {
  background: linear-gradient(180deg, #f9fbfd 0%, #f4f8fb 100%);
  border-radius: 18px;
  padding: 16px;
  border: 1px solid #dce6ef;
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
  font-weight: 700;
  padding: 12px 14px;
  border-radius: 14px;
}

.risk-item.critical {
  background: #fff2f0;
  color: #bf3a3a;
}

.risk-item.high {
  background: #fff7ea;
  color: #bd6f14;
}

.risk-item.medium {
  background: #fffbea;
  color: #b58117;
}

.risk-item.low {
  background: #f1fbf3;
  color: #2e7b45;
}

.risk-icon {
  font-size: 18px;
}

.risk-details {
  padding: 12px 14px;
  background: white;
  border-radius: 14px;
  font-size: 13px;
  color: #627486;
  line-height: 1.7;
  border: 1px solid #e5edf4;
}

.detail-text {
  margin: 0;
}

.decision-recommendation {
  background: linear-gradient(180deg, #f4fbff 0%, #eef7fc 100%);
  border-radius: 18px;
  padding: 16px;
  border: 1px solid #d7e7f3;
}

.recommendation-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(255, 255, 255, 0.9);
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #e4edf4;
}

.recommendation-text {
  font-size: 14px;
  color: #314456;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .overlay-analysis-popup {
    min-width: 0;
    width: calc(100vw - 24px);
    max-width: calc(100vw - 24px);
    max-height: 78vh;
    border-radius: 20px;
  }

  .popup-header {
    padding: 20px 20px 18px;
    border-radius: 20px 20px 0 0;
  }

  .popup-header h3 {
    font-size: 24px;
  }

  .popup-content {
    padding: 16px 20px 22px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .project-header,
  .detail-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-item .value {
    text-align: left;
  }
}
</style>

