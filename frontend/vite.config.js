import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: { output: { manualChunks: { 'element-plus': ['element-plus'], vue: ['vue', 'vue-router'], charts:['echarts'] } } },
  },
  server: {
    host: '0.0.0.0', port: 3000, strictPort: true,
    allowedHosts: process.env.CLOUDSTUDIO_PREVIEW_HOST ? [process.env.CLOUDSTUDIO_PREVIEW_HOST] : [],
    hmr: process.env.CLOUDSTUDIO_PREVIEW_HOST ? {
      host: process.env.CLOUDSTUDIO_PREVIEW_HOST,
      protocol: process.env.CLOUDSTUDIO_HMR_PROTOCOL || 'wss',
      clientPort: Number(process.env.CLOUDSTUDIO_HMR_PORT || 443),
    } : undefined,
    proxy: {
      '/api': { target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000', changeOrigin: false },
      '/health': { target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
})
