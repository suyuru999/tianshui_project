// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import MapView from '../views/MapView.vue'
import RemoteSensingAnalysis from '../views/RemoteSensingAnalysis.vue'
import CitizenFeedback from '../views/CitizenFeedback.vue'
import EcologicalIndex from '../views/EcologicalIndex.vue'
import ClimateMonitoring from '../views/ClimateMonitoring.vue'

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
  },
  {
    path: '/feedback',
    name: 'CitizenFeedback',
    component: CitizenFeedback
  },
  {
    path: '/ecological-index',
    name: 'EcologicalIndex',
    component: EcologicalIndex
  },
  {
    path: '/climate-monitoring',
    name: 'ClimateMonitoring',
    component: ClimateMonitoring
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router