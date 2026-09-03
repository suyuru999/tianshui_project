import { buildOwnerSnapshot, canViewHistoryItem } from './userContext.js'

const STORAGE_KEY = 'tianshui_main_map_analysis_layers_v1'
const MAX_ITEMS = 24

function safeParse(rawValue, fallback) {
  if (!rawValue) return fallback
  try {
    return JSON.parse(rawValue)
  } catch (error) {
    console.warn('解析主地图分析图层失败:', error)
    return fallback
  }
}

function normalizeMediaUrl(url) {
  const value = String(url || '').trim()
  if (!value) return ''
  if (/^(https?:|data:|blob:)/i.test(value)) return value
  if (value.startsWith('/')) return value
  if (value.startsWith('media/')) return `/${value}`
  return value.includes('/') ? `/media/${value.replace(/^\/+/, '')}` : ''
}

function normalizeCompareOverlay(compareOverlay) {
  if (!compareOverlay || typeof compareOverlay !== 'object') return null
  const overlay = {
    ...compareOverlay,
    overlay_image_url: normalizeMediaUrl(compareOverlay.overlay_image_url),
    visualization_file_url: normalizeMediaUrl(compareOverlay.visualization_file_url),
    result_file_url: normalizeMediaUrl(compareOverlay.result_file_url)
  }
  return overlay.overlay_image_url ? overlay : null
}

export function saveMainMapAnalysisLayer(item) {
  if (typeof window === 'undefined') {
    return { success: false, message: '当前环境不支持添加到主地图' }
  }

  const owner = buildOwnerSnapshot()
  if (!owner) {
    return { success: false, message: '请先登录后再添加到主地图界面' }
  }

  const compareOverlay = normalizeCompareOverlay(item?.compareOverlay)
  if (!compareOverlay) {
    return { success: false, message: '当前结果缺少可叠加图层，无法添加到主地图界面' }
  }

  const id = String(item.id || `analysis-result-${Date.now()}`)
  const nextItem = {
    id,
    name: '分析结果图层',
    title: item.title || compareOverlay.source_filename || '分析结果图层',
    subtitle: item.subtitle || '',
    feature: item.feature || '分析结果',
    timestamp: Number(item.timestamp || Date.now()),
    opacity: Number(item.opacity || 0.68),
    owner,
    compareOverlay
  }

  const items = safeParse(localStorage.getItem(STORAGE_KEY), [])
  const nextItems = Array.isArray(items)
    ? items.filter(entry => entry.id !== id && entry.compareOverlay?.overlay_image_url !== compareOverlay.overlay_image_url)
    : []
  nextItems.unshift(nextItem)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nextItems.slice(0, MAX_ITEMS)))
  window.dispatchEvent(new CustomEvent('tianshui-main-map-analysis-layers-updated'))
  return { success: true, item: nextItem }
}

export function loadMainMapAnalysisLayers(user, options = {}) {
  if (typeof window === 'undefined' || !user) return []
  const items = safeParse(localStorage.getItem(STORAGE_KEY), [])
  if (!Array.isArray(items)) return []
  return items
    .filter(item => canViewHistoryItem(item, user, options))
    .map(item => ({
      ...item,
      name: '分析结果图层',
      compareOverlay: normalizeCompareOverlay(item.compareOverlay)
    }))
    .filter(item => item.compareOverlay?.overlay_image_url)
    .sort((a, b) => Number(b.timestamp || 0) - Number(a.timestamp || 0))
}

export function removeMainMapAnalysisLayer(layerId, options = {}) {
  if (typeof window === 'undefined' || (!layerId && !options.overlayImageUrl)) return
  const items = safeParse(localStorage.getItem(STORAGE_KEY), [])
  if (!Array.isArray(items)) return
  const overlayImageUrl = normalizeMediaUrl(options.overlayImageUrl)
  const nextItems = items.filter(item => (
    (layerId && String(item.id) === String(layerId))
    || (overlayImageUrl && normalizeMediaUrl(item.compareOverlay?.overlay_image_url) === overlayImageUrl)
  ) === false)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nextItems))
  window.dispatchEvent(new CustomEvent('tianshui-main-map-analysis-layers-updated'))
}
