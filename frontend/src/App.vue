<script setup>
import { onMounted } from 'vue'
import { authService } from './services/api.js'
import { getCurrentUserContext, setCurrentUserContext } from './utils/userContext.js'

onMounted(async () => {
  if (!getCurrentUserContext()) {
    return
  }
  try {
    const user = await authService.getProfile({ silentError: true })
    setCurrentUserContext(user)
  } catch {
    setCurrentUserContext(null)
  }
})
</script>

<template>
  <div class="app-shell">
    <main class="app-workspace">
      <router-view />
    </main>
  </div>
</template>

<style>
/* 全局样式 */
:root {
  --ds-page: #06182d;
  --ds-workspace: #06182d;
  --ds-sidebar: #0b2340;
  --ds-header: #06182d;
  --ds-card: #102d4d;
  --ds-panel: #122f50;
  --ds-module: #0d2745;
  --ds-hover: #183b61;
  --ds-primary: #1677ff;
  --ds-primary-hover: #2688ff;
  --ds-primary-active: #0e62dd;
  --ds-accent: #26b6e8;
  --ds-success: #2fc26b;
  --ds-warning: #f59e0b;
  --ds-danger: #ef4444;
  --ds-border: #1c4265;
  --ds-border-soft: #1d4264;
  --ds-border-strong: #285a82;
  --ds-text: #ffffff;
  --ds-muted: #c4d4eb;
  --ds-subtle: #8299bc;
  --ds-disabled: #5d7494;
  --ds-radius-button: 6px;
  --ds-radius-input: 6px;
  --ds-radius-card: 10px;
  --ds-radius-module: 8px;
  --ds-radius-dialog: 12px;
  --ds-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
  --ds-shadow-hover: 0 8px 28px rgba(0, 0, 0, 0.34);
  --ds-space-4: 4px;
  --ds-space-8: 8px;
  --ds-space-10: 10px;
  --ds-space-12: 12px;
  --ds-space-16: 16px;
  --ds-space-20: 20px;
  --ds-space-24: 24px;
  --ds-space-32: 32px;
  font-family: 'HarmonyOS Sans SC', 'PingFang SC', 'Microsoft YaHei', Inter, Roboto, Arial, sans-serif;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'HarmonyOS Sans SC', 'PingFang SC', 'Microsoft YaHei', Inter, Roboto, Arial, sans-serif;
  overflow: hidden;
  background: var(--ds-page);
  color: var(--ds-text);
}

#app {
  min-height: 100vh;
  background: var(--ds-page);
}

button,
input,
select,
textarea {
  font: inherit;
}

.app-shell {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--ds-page);
}

.app-workspace {
  height: 100vh;
  min-height: 0;
  overflow: hidden;
  background: var(--ds-workspace);
}
</style>
