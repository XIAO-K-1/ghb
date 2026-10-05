import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
// 注册 echarts-gl 3D 扩展（map3D / bar3D / scatter3D），供风险态势沙盘河南3D地图使用
import 'echarts-gl'

import './styles/tokens.css'
import './styles/base.css'

createApp(App).use(router).mount('#app')
