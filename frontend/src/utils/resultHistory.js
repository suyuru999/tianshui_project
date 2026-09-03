import { buildOwnerSnapshot, getCurrentUserContext, isOwnedByUser } from './userContext.js'

const STORAGE_PREFIX = 'tianshui_result_history_v1'
const DEFAULT_LIMIT = 6

function getStorageKey(featureKey) {
  return `${STORAGE_PREFIX}:${featureKey}`
}

function safeParse(rawValue, fallback) {
  if (!rawValue) {
    return fallback
  }

  try {
    return JSON.parse(rawValue)
  } catch (error) {
    console.warn('解析历史结果失败:', error)
    return fallback
  }
}

function ensureArray(value) {
  return Array.isArray(value) ? value : []
}

function loadAllResultHistory(featureKey) {
  if (typeof window === 'undefined') {
    return []
  }

  const items = safeParse(localStorage.getItem(getStorageKey(featureKey)), [])
  return ensureArray(items).sort((a, b) => Number(b.timestamp || 0) - Number(a.timestamp || 0))
}

function sameOwner(a, b) {
  if (!a && !b) return true
  if (!a || !b) return false
  if (a.id !== undefined && b.id !== undefined && String(a.id) === String(b.id)) return true
  return Boolean(a.username && b.username && String(a.username) === String(b.username))
}

export function loadResultHistory(featureKey, options = {}) {
  const items = loadAllResultHistory(featureKey)
  if (options.includeAllOwners) {
    return items
  }
  const currentUser = getCurrentUserContext()
  return items.filter(item => isOwnedByUser(item, currentUser))
}

export function saveResultHistory(featureKey, item, options = {}) {
  if (typeof window === 'undefined' || !item) {
    return []
  }

  const maxItems = Number(options.maxItems) > 0 ? Number(options.maxItems) : DEFAULT_LIMIT
  const owner = item.owner === undefined ? buildOwnerSnapshot() : item.owner
  const nextItem = {
    id: item.id || `${featureKey}_${Date.now()}`,
    title: item.title || '未命名结果',
    subtitle: item.subtitle || '',
    timestamp: Number(item.timestamp || Date.now()),
    owner,
    payload: item.payload || null
  }

  const allHistory = loadAllResultHistory(featureKey).filter((entry) => (
    entry.id !== nextItem.id || !sameOwner(entry.owner || entry.payload?.owner, owner)
  ))
  allHistory.unshift(nextItem)

  const ownerCount = new Map()
  const trimmed = []
  allHistory.forEach((entry) => {
    const entryOwner = entry.owner || entry.payload?.owner || null
    const ownerKey = entryOwner?.id !== undefined
      ? `id:${entryOwner.id}`
      : entryOwner?.username
        ? `name:${entryOwner.username}`
        : 'anonymous'
    const count = ownerCount.get(ownerKey) || 0
    if (count >= maxItems && sameOwner(entryOwner, owner)) {
      return
    }
    ownerCount.set(ownerKey, count + 1)
    trimmed.push(entry)
  })

  localStorage.setItem(getStorageKey(featureKey), JSON.stringify(trimmed))
  return loadResultHistory(featureKey)
}

export function removeResultHistory(featureKey, itemId, options = {}) {
  if (typeof window === 'undefined') {
    return []
  }

  const currentUser = getCurrentUserContext()
  const nextItems = loadAllResultHistory(featureKey).filter((item) => (
    item.id !== itemId || (!options.ignoreOwner && !isOwnedByUser(item, currentUser))
  ))
  localStorage.setItem(getStorageKey(featureKey), JSON.stringify(nextItems))
  return loadResultHistory(featureKey)
}

export function clearResultHistory(featureKey, options = {}) {
  if (typeof window === 'undefined') {
    return
  }

  if (options.ignoreOwner) {
    localStorage.removeItem(getStorageKey(featureKey))
    return
  }

  const currentUser = getCurrentUserContext()
  const nextItems = loadAllResultHistory(featureKey).filter(item => !isOwnedByUser(item, currentUser))
  if (nextItems.length > 0) {
    localStorage.setItem(getStorageKey(featureKey), JSON.stringify(nextItems))
  } else {
    localStorage.removeItem(getStorageKey(featureKey))
  }
}

export function formatHistoryTime(timestamp) {
  if (!timestamp) {
    return ''
  }

  try {
    return new Date(timestamp).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    return ''
  }
}
