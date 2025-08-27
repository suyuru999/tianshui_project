// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import MapView from '../views/MapView.vue'
import RemoteSensingAnalysis from '../views/RemoteSensingAnalysis.vue'

const routes = [
  {
    path: '/',
    name: 'MapView',
    component: MapView
  },
  // 可以继续添加其他路由
  {
    path: '/remote-sensing-analysis',
    name: 'RemoteSensingAnalysis',
    component: RemoteSensingAnalysis
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router