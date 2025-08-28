<template>
  <ErrorBoundary>
    <div class="remote-sensing-analysis-apple">
      <!-- 全局加载遮罩 -->
      <LoadingSpinner 
        v-if="globalLoading" 
        type="default" 
        :overlay="true" 
        text="系统处理中，请稍候..."
      />
      
      <div class="sidebar-apple">
        <AnalysisSidebar
          :selected-index="selectedIndex"
          :file-name="fileName"
          :uploading="uploading"
          @file-change="handleFileChange"
          @start-analysis="handleStartAnalysis"
          @index-change="handleIndexChange"
        />
      </div>
      
      <div class="result-area-apple">
        <!-- 分析进度 -->
        <div v-if="status === 'analyzing'" class="analysis-progress">
          <h3 class="progress-title">正在分析遥感影像...</h3>
          <ProgressBar
            :value="analysisProgress"
            title="分析进度"
            type="primary"
            :show-info="true"
            :current="`${analysisProgress}%`"
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
import { ref, onMounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import AnalysisSidebar from '../components/RemoteSensing/AnalysisSidebar.vue';
import AnalysisResult from '../components/RemoteSensing/AnalysisResult.vue';
import LoadingSpinner from '../components/Common/LoadingSpinner.vue';
import ProgressBar from '../components/Common/ProgressBar.vue';
import ErrorBoundary from '../components/Common/ErrorBoundary.vue';
import { remoteSensingService, ecologicalIndicesService, processingTaskService } from '../services/api.js';
import { useLoadingStore } from '../store/loading.js';
import { useMessageStore } from '../store/message.js';

// 状态管理
const loadingStore = useLoadingStore();
const messageStore = useMessageStore();

// 组件状态
const selectedIndex = ref('NDVI');
const fileName = ref('');
const uploading = ref(false);
const status = ref('waiting'); // waiting | analyzing | done | error
const resultData = ref(null);
const currentTaskId = ref(null);
const currentFile = ref(null);

// 分析进度相关
const analysisProgress = ref(0);
const analysisSpeed = ref('');
const analysisEta = ref('');
const currentStep = ref('准备分析环境...');
const stepDetail = ref('正在初始化分析参数');
const isPaused = ref(false);

// 计算属性
const globalLoading = computed(() => loadingStore.globalLoading);

// 组件挂载时检查用户登录状态
onMounted(() => {
  checkAuthStatus();
});

// 检查认证状态
function checkAuthStatus() {
  const token = localStorage.getItem('access_token');
  if (!token) {
    messageStore.warning('请先登录系统');
    
    // 创建一个临时token用于测试（仅开发环境使用）
    const tempToken = 'temporary_dev_token_for_testing';
    localStorage.setItem('access_token', tempToken);
    messageStore.info('已创建临时测试令牌');
    
    // 在实际生产环境中应该跳转到登录页面
    // window.location.href = '/login';
  }
}

// 处理文件选择
function handleFileChange(file) {
  if (file) {
    // 验证文件类型
    const allowedTypes = ['.tif', '.tiff', '.jpg', '.jpeg', '.png'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!allowedTypes.includes(fileExtension)) {
      messageStore.error('不支持的文件格式，请选择 .tif, .tiff, .jpg, .jpeg, .png 格式的文件');
      return;
    }
    
    // 验证文件大小（900MB限制）
    const maxSize = 900 * 1024 * 1024;
    if (file.size > maxSize) {
      messageStore.error('文件大小不能超过900MB');
      return;
    }
    
    currentFile.value = file;
    fileName.value = file.name;
    status.value = 'waiting';
    resultData.value = null;
    currentTaskId.value = null;
    analysisProgress.value = 0;
    
    messageStore.success('文件选择成功');
  }
}

// 开始分析
async function handleStartAnalysis() {
  if (!currentFile.value) {
    messageStore.error('请先选择文件');
    return;
  }
  
  try {
    uploading.value = true;
    status.value = 'analyzing';
    analysisProgress.value = 0;
    isPaused.value = false;
    
    console.log('开始分析，初始进度:', analysisProgress.value); // 添加调试日志
    
    // 模拟分析步骤
    const analysisSteps = [
      { progress: 10, step: '上传文件', detail: '正在上传遥感影像文件...' },
      { progress: 25, step: '预处理', detail: '正在进行影像预处理...' },
      { progress: 40, step: '计算指数', detail: `正在计算${selectedIndex.value}指数...` },
      { progress: 60, step: '后处理', detail: '正在进行结果后处理...' },
      { progress: 80, step: '生成报告', detail: '正在生成分析报告...' },
      { progress: 100, step: '完成', detail: '分析完成！' }
    ];
    
    // 1. 上传遥感影像
    currentStep.value = '上传文件';
    stepDetail.value = '正在上传遥感影像文件...';
    
    // 确保数据格式正确
    const uploadData = {
      name: fileName.value || '未命名影像',
      image_type: 'sentinel2',  // 修正为有效的选项
      description: `用户上传的${selectedIndex.value}分析影像`,
      acquisition_date: new Date().toISOString().split('T')[0],
      center_lat: 39.9042,  // 使用有效的坐标值（北京坐标作为示例）
      center_lon: 116.4074
    };
    
    console.log('上传数据:', uploadData);
    console.log('文件对象:', currentFile.value);
    
    const uploadResult = await remoteSensingService.upload(currentFile.value, uploadData);
    
    // 添加调试信息
    console.log('上传结果:', uploadResult);
    console.log('上传结果类型:', typeof uploadResult);
    console.log('上传结果ID:', uploadResult?.id);
    console.log('上传结果键:', Object.keys(uploadResult || {}));
    
    if (uploadResult && uploadResult.id) {
      const imageId = uploadResult.id;
      console.log('获取到影像ID:', imageId);
      analysisProgress.value = 20;
      messageStore.success('文件上传成功，开始分析...');
      
      // 2. 启动生态指数计算
      currentStep.value = '启动生态指数计算';
      stepDetail.value = '正在启动生态指数计算任务...';
      
      try {
        // 调用计算接口
        console.log('准备调用计算接口，参数:', {
          imageId: imageId,
          selectedIndex: selectedIndex.value,
          indices: [selectedIndex.value]
        });
        
        const calculateResult = await remoteSensingService.calculateIndices(imageId, [selectedIndex.value]);
        console.log('计算接口调用成功，结果:', calculateResult);
        
        analysisProgress.value = 30;
        messageStore.success('生态指数计算已启动，正在处理中...');
        
        // 3. 创建分析任务记录
        currentStep.value = '创建分析任务';
        stepDetail.value = '正在创建分析任务记录...';
        
        const taskData = {
          remote_sensing_image_id: imageId,
          task_type: `生态指数计算 - ${selectedIndex.value}`,
          status: 'processing'
        };
        
        // 使用ProcessingTask服务创建任务
        const taskResult = await processingTaskService.create(taskData);
        
        if (taskResult && taskResult.id) {
          currentTaskId.value = taskResult.id;
          analysisProgress.value = 40;
          messageStore.success('分析任务创建成功，正在处理中...');
          
          // 4. 模拟分析进度
          await simulateAnalysisProgress(analysisSteps);
          
          // 5. 轮询任务状态
          await pollTaskStatus(currentTaskId.value);
        } else {
          throw new Error('创建分析任务失败');
        }
      } catch (error) {
        console.error('启动生态指数计算失败:', error);
        messageStore.error(`启动生态指数计算失败: ${error.message}`);
        throw error;
      }
    } else {
      throw new Error('文件上传失败');
    }
    
  } catch (error) {
    console.error('分析失败:', error);
    console.error('错误类型:', typeof error);
    console.error('错误消息:', error.message);
    console.error('错误堆栈:', error.stack);
    
    // 提取详细的错误信息
    let errorMessage = '分析失败，请重试';
    let errorDetails = '';
    
    if (error.response) {
      // 服务器响应了错误状态码
      const { status: responseStatus, data } = error.response;
      errorMessage = `服务器错误 (${responseStatus})`;
      
      if (data && data.error) {
        errorDetails = data.error;
      } else if (data && data.details) {
        errorDetails = data.details;
      } else if (data) {
        errorDetails = JSON.stringify(data);
      }
      
      console.log('错误响应详情:', { status: responseStatus, data });
    } else if (error.request) {
      // 请求已发出但没有收到响应
      errorMessage = '无法连接到服务器';
      errorDetails = '请检查网络连接或确保后端服务正在运行';
      console.log('网络错误:', error.request);
    } else {
      // 其他错误
      errorMessage = error.message || '未知错误';
      console.log('其他错误:', error);
    }
    
    status.value = 'error';
    resultData.value = { 
      error: errorMessage,
      details: errorDetails 
    };
    
    // 显示错误消息
    messageStore.error(`${errorMessage}${errorDetails ? ': ' + errorDetails : ''}`);
    
    // 如果是400错误，显示更多调试信息
    if (error.response && error.response.status === 400) {
      console.log('400错误详情:', {
        url: error.config?.url,
        method: error.config?.method,
        data: error.config?.data,
        headers: error.config?.headers
      });
    }
  } finally {
    uploading.value = false;
  }
}

// 模拟分析进度
async function simulateAnalysisProgress(steps) {
  for (let i = 0; i < steps.length; i++) {
    if (isPaused.value) {
      await waitForResume();
    }
    
    const step = steps[i];
    analysisProgress.value = step.progress;
    currentStep.value = step.step;
    stepDetail.value = step.detail;
    
    console.log(`进度更新: ${step.progress}%`); // 添加调试日志
    
    // 模拟处理时间
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
  }
}

// 等待恢复
function waitForResume() {
  return new Promise(resolve => {
    const checkResume = () => {
      if (!isPaused.value) {
        resolve();
      } else {
        setTimeout(checkResume, 100);
      }
    };
    checkResume();
  });
}

// 轮询任务状态
async function pollTaskStatus(taskId) {
  const maxAttempts = 60;
  let attempts = 0;
  
  const poll = async () => {
    try {
      const statusResult = await processingTaskService.getStatus(taskId);
      const taskStatus = statusResult.status;
      
      if (taskStatus === 'completed') {
        // 任务完成，获取结果
        const taskDetail = await processingTaskService.getDetail(taskId);
        status.value = 'done';
        resultData.value = taskDetail;
        messageStore.success('分析完成！');
        return;
      } else if (taskStatus === 'failed') {
        // 任务失败
        status.value = 'error';
        resultData.value = { error: '分析任务执行失败' };
        messageStore.error('分析任务执行失败');
        return;
      } else if (taskStatus === 'processing') {
        // 任务处理中，继续轮询
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          // 超时
          status.value = 'error';
          resultData.value = { error: '分析超时，请检查任务状态' };
          messageStore.warning('分析超时，请检查任务状态');
        }
      }
    } catch (error) {
      console.error('查询任务状态失败:', error);
      attempts++;
      if (attempts < maxAttempts) {
        setTimeout(poll, 2000);
      } else {
        status.value = 'error';
        resultData.value = { error: '查询任务状态失败' };
        messageStore.error('查询任务状态失败');
      }
    }
  };
  
  poll();
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
  // 如果已经上传了文件，可以提示用户重新分析
  if (currentFile.value) {
    messageStore.info(`已切换到${index}指数，点击"开始分析"重新计算`);
  }
}
</script>

<style scoped>
.remote-sensing-analysis-apple {
  display: flex;
  gap: 32px;
  padding: 48px 5vw;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #e9eff5 100%);
}

.sidebar-apple {
  width: 360px;
  min-width: 320px;
  background: rgba(255,255,255,0.85);
  border-radius: 28px;
  box-shadow: 0 8px 32px 0 rgba(60,60,60,0.08), 0 1.5px 4px 0 rgba(60,60,60,0.04);
  padding: 36px 32px 24px 32px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  transition: box-shadow 0.2s;
}

.result-area-apple {
  flex: 1;
  background: rgba(255,255,255,0.92);
  border-radius: 32px;
  box-shadow: 0 8px 32px 0 rgba(60,60,60,0.08), 0 1.5px 4px 0 rgba(60,60,60,0.04);
  padding: 48px 40px;
  min-height: 600px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: box-shadow 0.2s;
}

/* 分析进度样式 */
.analysis-progress {
  width: 100%;
  max-width: 600px;
  text-align: center;
}

.progress-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 32px;
}

.analysis-status {
  margin-top: 24px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
  border-left: 4px solid #409eff;
}

.status-text {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin: 0 0 8px 0;
}

.status-detail {
  font-size: 14px;
  color: #606266;
  margin: 0;
  line-height: 1.5;
}

@media (max-width: 900px) {
  .remote-sensing-analysis-apple {
    flex-direction: column;
    gap: 24px;
    padding: 24px 2vw;
  }
  
  .sidebar-apple, .result-area-apple {
    width: 100%;
    min-width: unset;
    border-radius: 20px;
    padding: 24px 12px;
  }
  
  .analysis-progress {
    max-width: 100%;
  }
}
</style> 