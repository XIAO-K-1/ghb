import { createRouter, createWebHashHistory } from 'vue-router'

/**
 * 路由结构
 *  /            演示入口（双端选择）
 *  /bank/*      银行客户经理端 Web 后台 —— 贷后风控指挥舱（深色）
 *  /app         民宿老板端 App —— AI经营助手（浅色，手机壳内运行）
 */
const routes = [
  {
    path: '/',
    name: 'entry',
    component: () => import('@/views/Entry.vue')
  },
  {
    path: '/bank',
    component: () => import('@/views/bank/BankLayout.vue'),
    redirect: '/bank/dashboard',
    children: [
      { path: 'dashboard', name: 'bank-dashboard', component: () => import('@/views/bank/Dashboard.vue'), meta: { title: '贷后驾驶舱', sub: 'POST-LOAN COMMAND DECK' } },
      { path: 'warnings', name: 'bank-warnings', component: () => import('@/views/bank/Warnings.vue'), meta: { title: '预警中心', sub: 'RISK ALERT CENTER' } },
      { path: 'archive', name: 'bank-archive', component: () => import('@/views/bank/Archive.vue'), meta: { title: '民宿数字档案', sub: 'DIGITAL ARCHIVE' } },
      { path: 'report', name: 'bank-report', component: () => import('@/views/bank/ReportCenter.vue'), meta: { title: 'AI巡检报告', sub: 'AI INSPECTION REPORT' } },
      { path: 'rag', name: 'bank-rag', component: () => import('@/views/bank/RagManage.vue'), meta: { title: 'RAG 系统管理', sub: 'RAG KNOWLEDGE BASE' } },
      { path: 'messages', name: 'bank-messages', component: () => import('@/views/bank/MessageCenter.vue'), meta: { title: '消息中心', sub: 'OWNER MESSAGE CENTER' } },
      { path: 'models', name: 'bank-models', component: () => import('@/views/bank/ModelManage.vue'), meta: { title: '模型管理', sub: 'MODEL CONFIGURATION' } }
    ]
  },
  {
    path: '/app',
    name: 'app',
    component: () => import('@/views/app/AppShell.vue')
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.afterEach((to) => {
  const t = to.meta?.title
  document.title = t ? `豫宿巡 · ${t}` : '豫宿巡 · 贷后风控指挥舱'
})

export default router
