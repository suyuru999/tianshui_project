<template>
  <ErrorBoundary>
    <div class="remote-sensing-analysis">
      <!-- 全局加载遮罩 -->
      <LoadingSpinner 
        v-if="globalLoading" 
        type="default" 
        :overlay="true" 
        text="系统处理中，请稍候..."
      />
      
      <!-- 左侧控制面板 -->
      <div class="control-panel">
        <AnalysisSidebar
          :selected-index="selectedIndex"
          :file-name="fileName"
          :uploading="uploading"
          :index-options="indexOptions"
          :cached-indices="cachedIndices"
          :disabled-indices="disabledIndices"
          :supported-index-labels="supportedIndexLabels"
          :capabilities-known="capabilitiesKnown"
          :history-items="historyItems"
          :history-expanded="historyExpanded"
          @file-change="handleFileChange"
          @start-analysis="handleStartAnalysis"
          @index-change="handleIndexChange"
          @clear-cache="clearCache"
          @toggle-history="historyExpanded = !historyExpanded"
          @clear-history="clearHistoryItems"
          @delete-history="deleteHistoryItem"
          @restore-history="restoreHistoryItem"
        />
      </div>
      
      <!-- 右侧结果区域 -->
      <div class="result-area">
        <!-- 分析进度 -->
        <div v-if="status === 'analyzing'" class="analysis-progress">
          <h3 class="progress-title">正在分析遥感影像...</h3>
          <ProgressBar
            :value="analysisProgress"
            title="分析进度"
            type="primary"
            :show-info="true"
            :current="`${Math.round(analysisProgress)}%`"
            :total="100"
            :speed="analysisSpeed"
            :eta="analysisEta"
            :show-actions="true"
            :can-pause="true"
            :can-cancel="true"
            @pause="pauseAnalysis"
            @resume="resumeAnalysis"
            @cancel="cancelAnalysis"
          />
          
          <div class="analysis-status">
            <p class="status-text">{{ currentStep }}</p>
            <p class="status-detail">{{ stepDetail }}</p>
          </div>
        </div>
        
        <!-- 分析结果 -->
        <AnalysisResult
          v-else
          :status="status"
          :result-data="resultData"
          :selected-index="selectedIndex"
          :task-id="currentTaskId"
        />
      </div>
    </div>
  </ErrorBoundary>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import AnalysisSidebar from '../components/RemoteSensing/AnalysisSidebar.vue';
import AnalysisResult from '../components/RemoteSensing/AnalysisResult.vue';
import LoadingSpinner from '../components/Common/LoadingSpinner.vue';
import ProgressBar from '../components/Common/ProgressBar.vue';
import ErrorBoundary from '../components/Common/ErrorBoundary.vue';
import { authService, remoteSensingService } from '../services/api.js';
import { useLoadingStore } from '../store/loading.js';
import { useMessageStore } from '../store/message.js';
import { buildOwnerSnapshot, canViewHistoryItem, getCurrentUserContext, setCurrentUserContext } from '../utils/userContext.js';

const OVERLAY_RSEI_REFRESH_KEY = 'overlay_rsei_refresh_signal';
const CACHE_MAX_AGE_MS = 90 * 24 * 60 * 60 * 1000;
const INDEX_OPTIONS = [
  { key: 'rsei', label: '遥感生态指数 (RSEI)' },
  { key: 'ndvi', label: '绿化指数 (NDVI)' },
  { key: 'ndwi', label: '湿度指数 (NDWI)' },
  { key: 'dryness', label: '干度指数 (NDBSI)' },
  { key: 'heat', label: '热度指数 (LST)' }
];
const INDEX_LABEL_MAP = Object.fromEntries(INDEX_OPTIONS.map((item) => [item.key, item.label]));

// 状态管理
const loadingStore = useLoadingStore();
const messageStore = useMessageStore();

// 组件状态
const selectedIndex = ref('rsei');
const fileName = ref('');
const uploading = ref(false);
const status = ref('waiting'); // waiting | analyzing | done | error
const resultData = ref(null);
const currentTaskId = ref(null);
const currentFile = ref(null);
const currentImageId = ref(null); // 存储当前影像ID
const historyExpanded = ref(false);

// 结果缓存管理
const analysisResultsCache = ref(new Map()); // 存储不同指数类型的分析结果

// 分析进度相关
const analysisProgress = ref(0);
const analysisSpeed = ref('');
const analysisEta = ref('');
const currentStep = ref('准备分析环境...');
const stepDetail = ref('正在初始化分析参数');
const isPaused = ref(false);
const capabilitiesResolvedFromBackend = ref(false);
const supportedIndicesFromBackend = ref([]);
const supportedIndexLabelsFromBackend = ref([]);
const backendIndexMap = {
  ndvi: 'ndvi',
  ndwi: 'ndwi',
  ndbi: 'ndbi',
  heat: 'heat',
  dryness: 'dryness',
  wetness: 'wetness',
  greenness: 'greenness',
  rsei: 'rsei'
};
const indexOptions = INDEX_OPTIONS;
const allIndexKeys = INDEX_OPTIONS.map((item) => item.key);
const capabilitiesKnown = computed(() => capabilitiesResolvedFromBackend.value);
const supportedIndexLabels = computed(() => {
  if (supportedIndexLabelsFromBackend.value.length > 0) {
    return supportedIndexLabelsFromBackend.value;
  }
  return supportedIndicesFromBackend.value.map((key) => INDEX_LABEL_MAP[key] || key.toUpperCase());
});

const disabledIndices = computed(() => {
  if (!capabilitiesKnown.value) {
    return [];
  }

  const supported = new Set(supportedIndicesFromBackend.value);
  return allIndexKeys.filter((key) => !supported.has(key));
});

const cachedIndices = computed(() => {
  const currentResultKeys = ensureResultDataIndices(resultData.value)
    .map((item) => normalizeCacheIndexType(item?.index_type))
    .filter((key) => allIndexKeys.includes(key));
  if (!currentImageId.value) {
    return currentResultKeys;
  }

  const now = Date.now();
  const currentUser = getCurrentUserContext();
  const cacheKeys = allIndexKeys.filter((key) => {
    return Array.from(analysisResultsCache.value.values()).some((cached) => (
      String(cached?.imageId || '') === String(currentImageId.value || '')
      && normalizeCacheIndexType(cached?.indexType) === key
      && canViewHistoryItem(cached, currentUser, {
        adminCanViewAll: true,
        adminCanViewOwnerless: true
      })
      && now - Number(cached.timestamp || 0) <= CACHE_MAX_AGE_MS
    ));
  });
  return [...new Set([...currentResultKeys, ...cacheKeys])];
});
const historyItems = computed(() => {
  const currentUser = getCurrentUserContext();
  return Array.from(analysisResultsCache.value.values())
    .filter((item) => canViewHistoryItem(item, currentUser, {
      adminCanViewAll: true,
      adminCanViewOwnerless: true
    }))
    .filter((item) => item?.resultData)
    .sort((a, b) => Number(b.timestamp || 0) - Number(a.timestamp || 0));
});

// 计算属性
const globalLoading = computed(() => loadingStore.globalLoading);

// 组件挂载时检查用户登录状态
onMounted(async () => {
  if (getCurrentUserContext()) {
    try {
      const user = await authService.getProfile({ silentError: true });
      setCurrentUserContext(user);
    } catch {
      setCurrentUserContext(null);
    }
  }
  loadCacheFromStorage();
  await validateHistoryCacheInBackground();
});

function notifyOverlayRSEIUpdate(payload = {}) {
  try {
    localStorage.setItem(OVERLAY_RSEI_REFRESH_KEY, JSON.stringify({
      timestamp: Date.now(),
      remote_sensing_image_id: payload.remote_sensing_image_id || '',
      remote_sensing_image_name: payload.remote_sensing_image_name || '',
      index_type: selectedIndex.value || '',
    }));
  } catch (error) {
    console.warn('写入叠加分析刷新信号失败:', error);
  }
}

function resetRemoteCapabilities() {
  capabilitiesResolvedFromBackend.value = false;
  supportedIndicesFromBackend.value = [];
  supportedIndexLabelsFromBackend.value = [];
}

function normalizeSupportedIndices(payload) {
  const rawIndices = payload?.supported_indices ?? payload?.source?.supported_indices ?? [];
  if (!Array.isArray(rawIndices)) {
    return [];
  }

  return [...new Set(
    rawIndices
      .map((item) => String(item || '').toLowerCase().trim())
      .filter((item) => allIndexKeys.includes(item))
  )];
}

function syncRemoteCapabilities(payload) {
  const hasIndices = Array.isArray(payload?.supported_indices) || Array.isArray(payload?.source?.supported_indices);
  const hasLabels = Array.isArray(payload?.supported_index_labels) || Array.isArray(payload?.source?.supported_index_labels);
  const normalizedIndices = normalizeSupportedIndices(payload);
  capabilitiesResolvedFromBackend.value = hasIndices || hasLabels;
  supportedIndicesFromBackend.value = normalizedIndices;

  const rawLabels = payload?.supported_index_labels ?? payload?.source?.supported_index_labels;
  if (Array.isArray(rawLabels) && rawLabels.length > 0) {
    supportedIndexLabelsFromBackend.value = rawLabels;
    return normalizedIndices;
  }

  supportedIndexLabelsFromBackend.value = normalizedIndices.map((key) => INDEX_LABEL_MAP[key] || key.toUpperCase());
  return normalizedIndices;
}

// 缓存管理函数
function saveAnalysisResult(resultData, imageId, indexType) {
  if (!resultData || !imageId || !indexType) {
    console.warn('保存缓存失败：缺少必要参数', { resultData: !!resultData, imageId, indexType });
    return;
  }
  
  const normalizedIndexType = normalizeCacheIndexType(indexType);
  const owner = buildOwnerSnapshot();
  const key = buildCacheMapKey(imageId, normalizedIndexType, owner);
  
  // 检查是否已经有相同的缓存
  const existingCache = analysisResultsCache.value.get(key);
  if (existingCache && JSON.stringify(existingCache.resultData) === JSON.stringify(resultData)) {
    return;
  }
  
  const cacheData = {
    resultData: {
      ...resultData,
      indices: ensureResultDataIndices(resultData),
      remote_sensing_image_id: resolveBackendImageId(resultData, imageId),
      owner
    },
    imageId,
    indexType: normalizedIndexType,
    backendImageId: resolveBackendImageId(resultData, imageId),
    timestamp: Date.now(),
    fileName: fileName.value,
    owner
  };
  analysisResultsCache.value.set(key, cacheData);
  
  // 同时保存到localStorage作为持久化存储，使用单独的键以避免覆盖
  try {
    // 为每个指数类型使用单独的localStorage键
    const storageKey = buildCacheStorageKey(imageId, normalizedIndexType, owner);
    
    // 直接保存当前指数的结果，不影响其他指数的缓存
    localStorage.setItem(storageKey, JSON.stringify(cacheData));
    
    // 同时维护一个索引，记录所有缓存的键
    let cacheIndex = [];
    try {
      const existingIndex = localStorage.getItem('analysis_cache_index');
      if (existingIndex) {
        cacheIndex = JSON.parse(existingIndex);
      }
    } catch (e) {
      console.warn('读取缓存索引失败，创建新索引');
    }
    
    // 添加当前键到索引（如果不存在）
    if (!cacheIndex.includes(storageKey)) {
      cacheIndex.push(storageKey);
      localStorage.setItem('analysis_cache_index', JSON.stringify(cacheIndex));
    }
  } catch (error) {
    console.warn('保存缓存到localStorage失败:', error);
  }
}

function normalizeCacheIndexType(indexType) {
  return String(indexType || '').toLowerCase();
}

function getOwnerCacheNamespace(owner = buildOwnerSnapshot()) {
  if (owner?.id !== undefined && owner?.id !== null && owner.id !== '') {
    return `user_${owner.id}`;
  }
  if (owner?.username) {
    return `user_${String(owner.username).replace(/[^\w-]/g, '_')}`;
  }
  return 'anonymous';
}

function getCacheItemOwner(cacheItem) {
  return cacheItem?.owner || cacheItem?.resultData?.owner || null;
}

function buildCacheMapKey(imageId, indexType, owner = buildOwnerSnapshot()) {
  return `${getOwnerCacheNamespace(owner)}_${imageId}_${normalizeCacheIndexType(indexType)}`;
}

function buildCacheStorageKey(imageId, indexType, owner = buildOwnerSnapshot()) {
  return `analysis_result_${getOwnerCacheNamespace(owner)}_${imageId}_${normalizeCacheIndexType(indexType)}`;
}

function isUuidLike(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || '').trim());
}

function resolveBackendImageId(payload, fallbackImageId = null) {
  const candidates = [
    payload?.backendImageId,
    payload?.resultData?.remote_sensing_image_id,
    payload?.remote_sensing_image_id,
    fallbackImageId
  ];

  for (const candidate of candidates) {
    if (isUuidLike(candidate)) {
      return String(candidate).trim();
    }
  }

  return null;
}

function ensureResultDataIndices(resultData) {
  if (!resultData || typeof resultData !== 'object') {
    return [];
  }

  if (Array.isArray(resultData.indices) && resultData.indices.length > 0) {
    return resultData.indices;
  }

  if (resultData.result && typeof resultData.result === 'object') {
    return [resultData.result];
  }

  return [];
}

function resultContainsIndex(resultData, indexType) {
  const normalizedIndex = normalizeCacheIndexType(indexType);
  return ensureResultDataIndices(resultData).some((item) => (
    normalizeCacheIndexType(item?.index_type) === normalizedIndex
  ));
}

function buildNormalizedCacheItem(cacheItem, normalizedIndex = normalizeCacheIndexType(cacheItem?.indexType)) {
  if (!cacheItem?.resultData) {
    return cacheItem;
  }

  const backendImageId = resolveBackendImageId(cacheItem, cacheItem.imageId);
  const normalizedResultData = {
    ...cacheItem.resultData,
    indices: ensureResultDataIndices(cacheItem.resultData),
    remote_sensing_image_id: backendImageId,
  };

  return {
    ...cacheItem,
    indexType: normalizedIndex,
    backendImageId,
    resultData: normalizedResultData
  };
}

function removeStorageCacheKey(storageKey) {
  if (!storageKey) {
    return;
  }

  try {
    localStorage.removeItem(storageKey);
    const cacheIndex = JSON.parse(localStorage.getItem('analysis_cache_index') || '[]');
    const nextCacheIndex = Array.isArray(cacheIndex)
      ? cacheIndex.filter((key) => key !== storageKey)
      : [];
    localStorage.setItem('analysis_cache_index', JSON.stringify(nextCacheIndex));
  } catch (error) {
    console.warn('移除本地缓存键失败:', storageKey, error);
  }
}

function removeOwnedStorageCaches(imageId, indexType) {
  const currentUser = getCurrentUserContext();
  const normalizedIndex = normalizeCacheIndexType(indexType);
  try {
    const cacheIndex = JSON.parse(localStorage.getItem('analysis_cache_index') || '[]');
    if (!Array.isArray(cacheIndex)) {
      return;
    }

    const nextCacheIndex = [];
    cacheIndex.forEach((storageKey) => {
      const cacheItem = JSON.parse(localStorage.getItem(storageKey) || 'null');
      const sameResult = String(cacheItem?.imageId || '') === String(imageId || '')
        && normalizeCacheIndexType(cacheItem?.indexType) === normalizedIndex;
      if (sameResult && canViewHistoryItem(cacheItem, currentUser, {
        adminCanViewAll: true,
        adminCanViewOwnerless: true
      })) {
        localStorage.removeItem(storageKey);
      } else {
        nextCacheIndex.push(storageKey);
      }
    });
    localStorage.setItem('analysis_cache_index', JSON.stringify(nextCacheIndex));
  } catch (error) {
    console.warn('移除当前账号缓存失败:', error);
  }
}

function removeCachedEntry(imageId, indexType, options = {}) {
  if (!imageId || !indexType) {
    return;
  }

  const { notify = false, message = '历史记录已删除' } = options;
  const currentUser = getCurrentUserContext();
  const normalizedIndex = normalizeCacheIndexType(indexType);
  Array.from(analysisResultsCache.value.entries()).forEach(([cacheMapKey, cacheItem]) => {
    const sameResult = String(cacheItem?.imageId || '') === String(imageId || '')
      && normalizeCacheIndexType(cacheItem?.indexType) === normalizedIndex;
    if (sameResult && canViewHistoryItem(cacheItem, currentUser, {
      adminCanViewAll: true,
      adminCanViewOwnerless: true
    })) {
      analysisResultsCache.value.delete(cacheMapKey);
    }
  });
  removeOwnedStorageCaches(imageId, indexType);

  if (notify) {
    messageStore.success(message);
  }
}

async function validateCachedResult(cacheItem, options = {}) {
  const { showMessage = false } = options;

  if (!cacheItem?.imageId || !cacheItem?.indexType || !cacheItem?.resultData) {
    removeCachedEntry(cacheItem?.imageId, cacheItem?.indexType);
    if (showMessage) {
      messageStore.warning('该历史结果已失效，请重新分析');
    }
    return null;
  }

  const normalizedIndex = normalizeCacheIndexType(cacheItem.indexType);
  const normalizedCacheItem = buildNormalizedCacheItem(cacheItem, normalizedIndex);
  const backendImageId = normalizedCacheItem?.backendImageId || null;
  const isExpired = Date.now() - Number(cacheItem.timestamp || 0) > CACHE_MAX_AGE_MS;
  if (isExpired) {
    removeCachedEntry(cacheItem.imageId, normalizedIndex);
    if (showMessage) {
      messageStore.warning('该历史结果缓存已过期，请重新分析');
    }
    return null;
  }

  const localIndices = ensureResultDataIndices(normalizedCacheItem?.resultData);
  const localMatchedIndex = localIndices.find(
    (item) => normalizeCacheIndexType(item?.index_type) === normalizedIndex
  );
  if (localMatchedIndex) {
    const cacheMapKey = buildCacheMapKey(cacheItem.imageId, normalizedIndex, getCacheItemOwner(normalizedCacheItem));
    const storageKey = buildCacheStorageKey(cacheItem.imageId, normalizedIndex, getCacheItemOwner(normalizedCacheItem));
    analysisResultsCache.value.set(cacheMapKey, normalizedCacheItem);
    localStorage.setItem(storageKey, JSON.stringify(normalizedCacheItem));
    return normalizedCacheItem;
  }

  if (!backendImageId) {
    removeCachedEntry(cacheItem.imageId, normalizedIndex);
    if (showMessage) {
      messageStore.warning('该历史结果已失效，请重新分析');
    }
    return null;
  }

  try {
    const response = await remoteSensingService.getIndices(backendImageId, { silentError: true });
    const remoteIndices = Array.isArray(response?.indices) ? response.indices : [];
    const matchedIndex = remoteIndices.find(
      (item) => normalizeCacheIndexType(item?.index_type) === normalizedIndex
    );

    if (!matchedIndex) {
      removeCachedEntry(cacheItem.imageId, normalizedIndex);
      if (showMessage) {
        messageStore.warning('该历史结果对应的后台数据已被清理，请重新分析');
      }
      return null;
    }

    const refreshedResultData = {
      ...normalizedCacheItem.resultData,
      remote_sensing_image_id: backendImageId,
      indices: remoteIndices
    };
    const refreshedCacheItem = {
      ...normalizedCacheItem,
      backendImageId,
      resultData: refreshedResultData
    };

    const cacheMapKey = buildCacheMapKey(cacheItem.imageId, normalizedIndex, getCacheItemOwner(refreshedCacheItem));
    const storageKey = buildCacheStorageKey(cacheItem.imageId, normalizedIndex, getCacheItemOwner(refreshedCacheItem));
    analysisResultsCache.value.set(cacheMapKey, refreshedCacheItem);
    localStorage.setItem(storageKey, JSON.stringify(refreshedCacheItem));
    return refreshedCacheItem;
  } catch (error) {
    console.warn('校验历史缓存失败:', cacheItem.imageId, normalizedIndex, error);

    if (error?.response?.status === 404) {
      removeCachedEntry(cacheItem.imageId, normalizedIndex);
      if (showMessage) {
        messageStore.warning('该历史结果对应的后台记录已不存在，请重新分析');
      }
      return null;
    }

    if (showMessage) {
      messageStore.warning('暂时无法校验历史结果，请确认后端服务正常后重试');
    }
    return cacheItem;
  }
}

async function validateHistoryCacheInBackground() {
  const cacheItems = Array.from(analysisResultsCache.value.values());
  if (cacheItems.length === 0) {
    return;
  }

  for (const cacheItem of cacheItems) {
    await validateCachedResult(cacheItem, { showMessage: false });
  }
}

function getCachedResult(imageId, indexType) {
  const key = buildCacheMapKey(imageId, indexType);
  
  // 尝试多种键格式
  const possibleKeys = [
    key,
    `${imageId}_${indexType}`, // 兼容旧版内存键
    `${imageId}_${indexType.toUpperCase()}`,
    `${imageId}_${indexType.toLowerCase()}`
  ];
  
  let cached = null;
  let matchedKey = null;
  
  // 1. 首先尝试从内存缓存中获取
  for (const testKey of possibleKeys) {
    cached = analysisResultsCache.value.get(testKey);
    if (cached) {
      matchedKey = testKey;
      break;
    }
  }
  if (!cached) {
    const currentUser = getCurrentUserContext();
    const normalizedIndex = normalizeCacheIndexType(indexType);
    const matchedEntry = Array.from(analysisResultsCache.value.entries()).find(([, cacheItem]) => (
      String(cacheItem?.imageId || '') === String(imageId || '')
      && normalizeCacheIndexType(cacheItem?.indexType) === normalizedIndex
      && canViewHistoryItem(cacheItem, currentUser, {
        adminCanViewAll: true,
        adminCanViewOwnerless: true
      })
    ));
    if (matchedEntry) {
      [matchedKey, cached] = matchedEntry;
    }
  }
  
  // 2. 如果内存中没有，尝试从localStorage直接获取
  if (!cached) {
    const storageKeys = [
      buildCacheStorageKey(imageId, indexType),
      `analysis_result_${imageId}_${indexType.toLowerCase()}`,
      `analysis_result_${imageId}_${indexType}`,
      `analysis_result_${imageId}_${indexType.toUpperCase()}`
    ];
    
    for (const storageKey of storageKeys) {
      try {
        const storedData = localStorage.getItem(storageKey);
        if (storedData) {
          const parsedData = buildNormalizedCacheItem(JSON.parse(storedData));
          
          if (parsedData && parsedData.resultData && canViewHistoryItem(parsedData, getCurrentUserContext(), {
            adminCanViewAll: true,
            adminCanViewOwnerless: true
          })) {
            // 将结果保存到内存缓存中
            const memKey = buildCacheMapKey(imageId, indexType, getCacheItemOwner(parsedData));
            analysisResultsCache.value.set(memKey, parsedData);
            
            cached = parsedData;
            matchedKey = memKey;
            break;
          }
        }
      } catch (e) {
        console.warn(`读取localStorage键 ${storageKey} 失败:`, e);
      }
    }
  }
  
  // 3. 处理找到的缓存
  if (cached) {
    if (!canViewHistoryItem(cached, getCurrentUserContext(), {
      adminCanViewAll: true,
      adminCanViewOwnerless: true
    })) {
      return null;
    }
    // 检查缓存是否过期（临时数据保留90天）
    const isExpired = Date.now() - cached.timestamp > CACHE_MAX_AGE_MS;
    if (isExpired) {
      removeCachedEntry(imageId, indexType);
      return null;
    }

    return cached;
  }

  return null;
}

function clearCache() {
  const currentUser = getCurrentUserContext();
  // 清空内存中的缓存
  analysisResultsCache.value.clear();
  
  // 只清空当前账号的缓存，保留其他账号结果
  try {
    const cacheIndex = localStorage.getItem('analysis_cache_index');
    const nextCacheKeys = [];
    if (cacheIndex) {
      const cacheKeys = JSON.parse(cacheIndex);
      if (Array.isArray(cacheKeys)) {
        cacheKeys.forEach(key => {
          const cacheItem = JSON.parse(localStorage.getItem(key) || 'null');
          if (canViewHistoryItem(cacheItem, currentUser, {
            adminCanViewAll: true,
            adminCanViewOwnerless: true
          })) {
            localStorage.removeItem(key);
          } else {
            nextCacheKeys.push(key);
          }
        });
      }
    }
    localStorage.setItem('analysis_cache_index', JSON.stringify(nextCacheKeys));
    // 兼容旧版缓存
    if (!currentUser) {
      localStorage.removeItem('analysis_results_cache');
    }
  } catch (error) {
    console.warn('清除缓存失败:', error);
  }
  
  messageStore.success('已清空所有缓存结果');
}

function clearHistoryItems() {
  if (historyItems.value.length === 0) {
    return;
  }

  if (!window.confirm('确定要清空当前所有历史记录吗？')) {
    return;
  }

  clearCache();
}

function deleteHistoryItem(item) {
  if (!item?.imageId || !item?.indexType) {
    return;
  }

  removeCachedEntry(item.imageId, item.indexType, {
    notify: true,
    message: '历史记录已删除'
  });
}

async function restoreHistoryItem(item) {
  const validatedItem = await validateCachedResult(item, { showMessage: true });
  if (!validatedItem?.resultData) {
    return;
  }

  selectedIndex.value = String(validatedItem.indexType || 'rsei').toLowerCase();
  fileName.value = validatedItem.fileName || '';
  currentFile.value = null;
  currentImageId.value = validatedItem.imageId || null;
  currentTaskId.value = validatedItem.resultData?.result?.id || null;
  syncRemoteCapabilities(validatedItem.resultData);
  resultData.value = validatedItem.resultData;
  status.value = 'done';
  analysisProgress.value = 100;
  currentStep.value = '历史结果恢复完成';
  stepDetail.value = '当前显示的是本地缓存结果，如需重新计算请重新选择文件';
  messageStore.success('已恢复历史分析结果');
}

// 从localStorage加载缓存
function loadCacheFromStorage() {
  try {
    // 初始化缓存Map
    analysisResultsCache.value = new Map();
    
    // 从索引中获取所有缓存键
    const cacheIndex = localStorage.getItem('analysis_cache_index');
    if (!cacheIndex) {
      return;
    }
    
    let cacheKeys = [];
    try {
      cacheKeys = JSON.parse(cacheIndex);
      if (!Array.isArray(cacheKeys)) {
        console.warn('缓存索引格式无效，应为数组');
        return;
      }
    } catch (e) {
      console.warn('解析缓存索引失败:', e);
      return;
    }
    
    // 加载每个缓存项
    for (const storageKey of cacheKeys) {
      try {
        const cachedData = localStorage.getItem(storageKey);
        if (!cachedData) {
          console.warn(`索引中的缓存键 ${storageKey} 不存在`);
          continue;
        }
        
        const cacheData = JSON.parse(cachedData);
        
        // 验证缓存数据
        if (!cacheData || !cacheData.imageId || !cacheData.indexType || !cacheData.resultData) {
          console.warn(`缓存键 ${storageKey} 的数据无效:`, cacheData);
          removeStorageCacheKey(storageKey);
          continue;
        }

        const normalizedCacheData = buildNormalizedCacheItem(cacheData);
        if (!canViewHistoryItem(normalizedCacheData, getCurrentUserContext(), {
          adminCanViewAll: true,
          adminCanViewOwnerless: true
        })) {
          continue;
        }

        const isExpired = Date.now() - Number(normalizedCacheData.timestamp || 0) > CACHE_MAX_AGE_MS;
        if (isExpired) {
          console.warn(`缓存键 ${storageKey} 已过期，自动移除`);
          removeCachedEntry(normalizedCacheData.imageId, normalizedCacheData.indexType);
          continue;
        }
        
        // 构建内存缓存键
        const memKey = buildCacheMapKey(
          normalizedCacheData.imageId,
          normalizedCacheData.indexType,
          getCacheItemOwner(normalizedCacheData)
        );
        
        // 保存到内存缓存
        analysisResultsCache.value.set(memKey, normalizedCacheData);
        localStorage.setItem(storageKey, JSON.stringify(normalizedCacheData));
      } catch (e) {
        console.warn(`加载缓存键 ${storageKey} 失败:`, e);
      }
    }
    
    // 尝试加载旧版缓存格式（兼容性）
    try {
      const oldCache = localStorage.getItem('analysis_results_cache');
      if (oldCache) {
        const oldCacheArray = JSON.parse(oldCache);
        
        if (Array.isArray(oldCacheArray)) {
          oldCacheArray.forEach(item => {
            if (Array.isArray(item) && item.length === 2) {
              const [key, value] = item;
              if (key && value && value.imageId && value.indexType && value.resultData) {
                const normalizedValue = buildNormalizedCacheItem(value);
                if (!canViewHistoryItem(normalizedValue, getCurrentUserContext(), {
                  adminCanViewAll: true,
                  adminCanViewOwnerless: true
                })) {
                  return;
                }
                // 检查是否已经加载过这个缓存
                const memKey = `${normalizedValue.imageId}_${normalizedValue.indexType.toLowerCase()}`;
                if (!analysisResultsCache.value.has(memKey)) {
                  analysisResultsCache.value.set(memKey, normalizedValue);
                  
                  // 同时迁移到新格式
                  const newStorageKey = buildCacheStorageKey(
                    normalizedValue.imageId,
                    normalizedValue.indexType,
                    getCacheItemOwner(normalizedValue)
                  );
                  localStorage.setItem(newStorageKey, JSON.stringify(normalizedValue));
                  
                  // 更新索引
                  if (!cacheKeys.includes(newStorageKey)) {
                    cacheKeys.push(newStorageKey);
                    localStorage.setItem('analysis_cache_index', JSON.stringify(cacheKeys));
                  }
                }
              }
            }
          });
        }
      }
    } catch (e) {
      console.warn('加载旧版缓存失败:', e);
    }
  } catch (error) {
    console.warn('从localStorage加载缓存失败:', error);
    // 如果加载失败，确保缓存Map被初始化为空
    analysisResultsCache.value = new Map();
  }
}

// 处理文件选择
function handleFileChange(file) {
  if (file) {
    // 验证文件类型
    const allowedTypes = ['.tif', '.tiff', '.jpg', '.jpeg', '.png', '.zip'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!allowedTypes.includes(fileExtension)) {
      messageStore.error('不支持的文件格式，请选择 .tif, .tiff, .jpg, .jpeg, .png，或ADF完整文件夹ZIP');
      return;
    }
    
    // 验证文件大小（后端会落盘并分块处理）
    const maxSize = 20 * 1024 * 1024 * 1024;
    if (file.size > maxSize) {
      messageStore.error('文件大小不能超过20GB；更大的遥感成果建议先裁剪或走后台分片上传');
      return;
    }
    
    currentFile.value = file;
    fileName.value = file.name;
    currentImageId.value = null;
    status.value = 'waiting';
    resultData.value = null;
    currentTaskId.value = null;
    analysisProgress.value = 0;
    resetRemoteCapabilities();

    messageStore.success('文件选择成功');
  }
}

// 开始分析
async function handleStartAnalysis() {
  if (!currentFile.value) {
    messageStore.error('请先选择文件');
    return;
  }

  if (capabilitiesKnown.value && disabledIndices.value.includes(selectedIndex.value)) {
    const supportedText = supportedIndexLabels.value.join('、');
    messageStore.warning(
      supportedText
        ? `当前影像不支持 ${INDEX_LABEL_MAP[selectedIndex.value] || selectedIndex.value}，请改选：${supportedText}`
        : '当前影像不支持所选指数，请切换后重试'
    );
    return;
  }
  
  try {
    // 在开始新分析前，保存当前结果到缓存（如果有的话）
    if (status.value === 'done' && resultData.value && currentImageId.value) {
      const currentIndex = selectedIndex.value;
      saveAnalysisResult(resultData.value, currentImageId.value, currentIndex);
    }
    
    uploading.value = true;
    status.value = 'analyzing';
    analysisProgress.value = 0;
    isPaused.value = false;
    
    currentStep.value = '上传并分析影像';
    stepDetail.value = '正在按公式计算指数并生成可视化结果...';
    analysisProgress.value = 15;

    const backendIndex = backendIndexMap[selectedIndex.value];
    if (!backendIndex) {
      throw new Error(`不支持的指数类型: ${selectedIndex.value}`);
    }

    startProgressSimulator();
    const analyzeResult = await remoteSensingService.analyzeUpload(currentFile.value, backendIndex, {
      name: fileName.value || '未命名影像'
    });
    stopProgressSimulator();

    analysisProgress.value = 100;
    currentStep.value = '分析完成';
    stepDetail.value = '计算结果已生成';
    const persistedRemoteImageId = resolveBackendImageId(analyzeResult);
    currentTaskId.value = analyzeResult?.result?.id || null;
    currentImageId.value = persistedRemoteImageId || `${fileName.value}_${backendIndex}`;
    const normalizedSupportedIndices = syncRemoteCapabilities(analyzeResult);
    resultData.value = {
      ...analyzeResult,
      remote_sensing_image_id: persistedRemoteImageId,
      supported_indices: normalizedSupportedIndices,
      supported_index_labels: supportedIndexLabels.value,
    };
    status.value = 'done';
    if (backendIndex === 'rsei' && analyzeResult?.remote_sensing_image_id) {
      notifyOverlayRSEIUpdate({
        remote_sensing_image_id: analyzeResult.remote_sensing_image_id,
        remote_sensing_image_name: analyzeResult.remote_sensing_image_name
      });
    }
    if (analyzeResult?.preview_message) {
      messageStore.warning(analyzeResult.preview_message);
    }
    saveAnalysisResult(resultData.value, currentImageId.value, selectedIndex.value);
    messageStore.success('分析完成！');
    
  } catch (error) {
    // 提取详细的错误信息
    let errorMessage = '分析失败，请重试';
    let errorDetails = '';
    
    if (error.response) {
      // 服务器响应了错误状态码
      const { status: responseStatus, data } = error.response;
      syncRemoteCapabilities(data);
      errorMessage = `服务器错误 (${responseStatus})`;
      
      if (data && data.error) {
        errorDetails = data.error;
      } else if (data && data.details) {
        errorDetails = data.details;
      } else if (data) {
        errorDetails = JSON.stringify(data);
      }
      if (Array.isArray(data?.supported_index_labels) && data.supported_index_labels.length > 0) {
        errorDetails = `${errorDetails} 建议选择：${data.supported_index_labels.join('、')}。`;
      }
      if (data?.bands_count) {
        errorDetails = `${errorDetails} 当前影像识别到 ${data.bands_count} 个波段。`.trim();
      }
      if (selectedIndex.value === 'rsei' && data?.bands_count === 1) {
        errorDetails = `${errorDetails} RSEI 需要原始多波段遥感影像，单波段成果栅格不会被系统作为可同步的 RSEI 结果保存。`.trim();
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      errorMessage = '无法连接到服务器';
      errorDetails = '请检查网络连接或确保后端服务正在运行';
    } else {
      // 其他错误
      errorMessage = error.message || '未知错误';
    }
    
    status.value = 'error';
    resultData.value = { 
      error: errorMessage,
      details: errorDetails,
      bands_count: error.response?.data?.bands_count,
      supported_indices: supportedIndicesFromBackend.value,
      supported_index_labels: supportedIndexLabels.value,
    };
    
    // 显示错误消息
    messageStore.error(`${errorMessage}${errorDetails ? ': ' + errorDetails : ''}`);
  } finally {
    uploading.value = false;
  }
}

// 进度模拟器
let progressInterval = null;

function startProgressSimulator() {
  // 清除之前的定时器
  if (progressInterval) {
    clearInterval(progressInterval);
  }
  
  // 每3秒更新一次进度
  progressInterval = setInterval(() => {
    if (status.value === 'analyzing' && analysisProgress.value < 95) {
      const increment = Math.random() * 2 + 0.5; // 每次增加0.5-2.5%
      analysisProgress.value = Math.min(95, analysisProgress.value + increment);
      
      // 更新步骤信息
      if (analysisProgress.value < 60) {
        currentStep.value = '数据预处理';
        stepDetail.value = '正在处理遥感影像数据...';
      } else if (analysisProgress.value < 80) {
        currentStep.value = '计算生态指数';
        stepDetail.value = '正在计算生态指数...';
      } else {
        currentStep.value = '结果生成';
        stepDetail.value = '正在生成分析结果...';
      }
    }
  }, 3000);
}

function stopProgressSimulator() {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
}

// 暂停分析
function pauseAnalysis() {
  isPaused.value = true;
  messageStore.info('分析已暂停');
}

// 恢复分析
function resumeAnalysis() {
  isPaused.value = false;
  messageStore.info('分析已恢复');
}

// 取消分析
async function cancelAnalysis() {
  try {
    const confirmed = await ElMessageBox.confirm(
      '确定要取消当前分析任务吗？',
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    if (confirmed) {
      status.value = 'waiting';
      analysisProgress.value = 0;
      isPaused.value = false;
      // 停止进度模拟器
      stopProgressSimulator();
      messageStore.info('分析任务已取消');
      
      // 这里可以调用后端API取消任务
      if (currentTaskId.value) {
        // await processingTaskService.cancel(currentTaskId.value);
      }
    }
  } catch (error) {
    // 用户取消操作
  }
}

// 处理指数类型变化
function handleIndexChange(index) {
  selectedIndex.value = index;
  const normalizedIndex = normalizeCacheIndexType(index);
  if (resultContainsIndex(resultData.value, normalizedIndex)) {
    status.value = 'done';
    messageStore.success(`已切换到${INDEX_LABEL_MAP[normalizedIndex] || normalizedIndex}结果`);
    return;
  }

  if (currentImageId.value) {
    const cached = getCachedResult(currentImageId.value, normalizedIndex);
    if (cached?.resultData) {
      resultData.value = cached.resultData;
      syncRemoteCapabilities(cached.resultData);
      status.value = 'done';
      analysisProgress.value = 100;
      messageStore.success(`已恢复${INDEX_LABEL_MAP[normalizedIndex] || normalizedIndex}缓存结果`);
      return;
    }
  }

  resultData.value = null;
  status.value = 'waiting';
  messageStore.info(`已切换到${INDEX_LABEL_MAP[normalizedIndex] || normalizedIndex}，请点击"开始分析"进行计算`);
}

// 组件卸载时清理
onUnmounted(() => {
  // 清理定时器等资源
  stopProgressSimulator();
});
</script>

<style scoped>
.remote-sensing-analysis {
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #06182d;
}

/* 左侧控制面板 */
.control-panel {
  width: var(--ds-sidebar-width, 360px);
  flex: 0 0 var(--ds-sidebar-width, 360px);
  background: #0b2340;
  border-right: 1px solid #1c4265;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  box-shadow: 2px 0 18px rgba(0, 0, 0, 0.22);
}

/* 自定义滚动条样式 */
.control-panel::-webkit-scrollbar {
  width: 6px;
}

.control-panel::-webkit-scrollbar-track {
  background: #06182d;
  border-radius: 3px;
}

.control-panel::-webkit-scrollbar-thumb {
  background: rgba(130, 153, 188, 0.45);
  border-radius: 3px;
  transition: background 0.2s ease;
}

.control-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(196, 212, 235, 0.55);
}

/* 右侧结果区域 */
.result-area {
  flex: 1;
  position: relative;
  background: #06182d;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  overflow-y: auto;
  padding: 24px;
}

/* 右侧结果区域滚动条样式 */
.result-area::-webkit-scrollbar {
  width: 6px;
}

.result-area::-webkit-scrollbar-track {
  background: #06182d;
  border-radius: 3px;
}

.result-area::-webkit-scrollbar-thumb {
  background: rgba(130, 153, 188, 0.45);
  border-radius: 3px;
  transition: background 0.2s ease;
}

.result-area::-webkit-scrollbar-thumb:hover {
  background: rgba(196, 212, 235, 0.55);
}

/* 分析进度样式 */
.analysis-progress {
  width: 100%;
  max-width: 720px;
  text-align: center;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 40px 32px;
  border: 1px solid #1c4265;
  border-radius: 12px;
  background: #102d4d;
  box-shadow: none;
}

:deep(.result-area > *) {
  width: 100%;
  max-width: 1280px;
}

:deep(.result-area .placeholder),
:deep(.result-area .empty-state),
:deep(.result-area .result-card),
:deep(.result-area .chart-card),
:deep(.result-area .stats-card) {
  border-radius: 10px;
}

.progress-title {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 28px;
}

.analysis-status {
  margin-top: 24px;
  width: 100%;
  padding: 18px 20px;
  background: #0d2745;
  border-radius: 10px;
  border: 1px solid #1c4265;
  text-align: left;
}

.status-text {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px 0;
}

.status-detail {
  font-size: 14px;
  color: #8299bc;
  margin: 0;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .remote-sensing-analysis-apple {
    flex-direction: column;
    gap: 24px;
    padding: 24px 2vw;
    max-height: none;
    overflow: visible;
  }
  
  .sidebar-apple, .result-area-apple {
    width: 100%;
    min-width: unset;
    border-radius: 20px;
    padding: 24px 12px;
    max-height: none;
    overflow-y: visible;
  }
  
  .analysis-progress {
    max-width: 100%;
  }
}
</style> 
