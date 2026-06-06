<template>
  <ErrorBoundary>
    <div class="feedback-page-apple">
      <div class="feedback-card-apple">
        <RouterLink to="/" class="feedback-back-link" title="返回主界面">
          <ArrowLeft class="back-home-icon" />
          <span>主界面</span>
        </RouterLink>
        <h1 class="title-apple">民众意见反馈</h1>
        <p class="subtitle-apple">我们期待你的声音，以帮助我们做得更好。</p>

        <el-form :model="form" :rules="rules" ref="formRef" label-position="top" class="form-apple">
          <el-form-item label="反馈类型" prop="category">
            <el-select v-model="form.category" placeholder="选择一种类型">
              <el-option label="功能建议" value="suggestion" />
              <el-option label="问题报告" value="bug" />
              <el-option label="数据纠错" value="data_issue" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>

          <el-form-item label="标题" prop="title">
            <el-input v-model="form.title" maxlength="80" show-word-limit placeholder="一句话概述你的反馈" />
          </el-form-item>

          <el-form-item label="详细描述" prop="content">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="6"
              maxlength="1000"
              show-word-limit
              placeholder="请描述现象、期望、复现步骤或截图链接等"
            />
          </el-form-item>

          <el-form-item label="联系方式（可选）" prop="contact">
            <el-input v-model="form.contact" placeholder="邮箱/电话/微信（可选）" />
          </el-form-item>

          <div class="actions-apple">
            <el-button :loading="submitting" type="primary" round size="large" @click="onSubmit">
              提交反馈
            </el-button>
            <el-button round size="large" @click="onReset">重置</el-button>
          </div>
        </el-form>

        <p class="privacy-apple">
          提交即表示你同意我们用于改进产品。我们会谨慎处理你的信息。
        </p>
      </div>
    </div>
  </ErrorBoundary>
  
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import ErrorBoundary from '../components/Common/ErrorBoundary.vue'
import { feedbackService } from '../services/api.js'

const formRef = ref(null)
const submitting = ref(false)
const form = ref({
  category: '',
  title: '',
  content: '',
  contact: ''
})

const rules = {
  category: [
    { required: true, message: '请选择反馈类型', trigger: 'change' }
  ],
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    { min: 4, max: 80, message: '标题长度 4-80 字', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请输入详细描述', trigger: 'blur' },
    { min: 10, max: 1000, message: '描述长度 10-1000 字', trigger: 'blur' }
  ]
}

function onReset() {
  form.value = { category: '', title: '', content: '', contact: '' }
}

function toBackendPayload(v) {
  return {
    category: v.category,
    title: v.title,
    content: v.content,
    contact: v.contact
  }
}

function onSubmit() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      submitting.value = true
      const payload = toBackendPayload(form.value)
      await feedbackService.create(payload)
      ElMessage.success('感谢你的反馈，我们已收到！')
      onReset()
    } catch (e) {
      ElMessage.error('提交失败，请稍后重试')
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped>
.feedback-page-apple {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f8fafc 0%, #e9eff5 100%);
  padding: 48px 24px;
}

.feedback-card-apple {
  width: 100%;
  max-width: 760px;
  background: rgba(255,255,255,0.92);
  border-radius: 28px;
  padding: 40px 36px;
  box-shadow: 0 8px 32px rgba(60,60,60,0.08), 0 1.5px 4px rgba(60,60,60,0.04);
}

.title-apple {
  margin: 0 0 8px 0;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 0.2px;
  color: #1f2937;
}

.subtitle-apple {
  margin: 0 0 24px 0;
  color: #6b7280;
  font-size: 14px;
}

.form-apple :deep(.el-form-item__label) {
  font-weight: 600;
  color: #374151;
}

.actions-apple {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.privacy-apple {
  margin-top: 20px;
  color: #9ca3af;
  font-size: 12px;
}

@media (max-width: 640px) {
  .feedback-card-apple {
    padding: 24px 16px;
    border-radius: 20px;
  }

  .title-apple { font-size: 24px; }
}
</style>


