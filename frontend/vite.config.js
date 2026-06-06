import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  define: {
    global: 'globalThis',
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      buffer: 'buffer'
    }
  },
  optimizeDeps: {
    include: ['buffer']
  },
  server: {
    port: 3000,
    proxy: {
      // 代理API请求到Django后端
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // 代理媒体文件
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      onwarn(warning, warn) {
        if (warning.code === 'INVALID_ANNOTATION' && warning.id?.includes('@vueuse/core')) {
          return
        }
        warn(warning)
      },
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return
          }
          if (id.includes('/ol/')) {
            return 'vendor-ol'
          }
          if (id.includes('/element-plus/') || id.includes('/@element-plus/')) {
            return 'vendor-element-plus'
          }
          if (id.includes('/vue') || id.includes('/@vue/')) {
            return 'vendor-vue'
          }
          if (id.includes('/axios/')) {
            return 'vendor-axios'
          }
          return 'vendor'
        }
      }
    }
  }
})
