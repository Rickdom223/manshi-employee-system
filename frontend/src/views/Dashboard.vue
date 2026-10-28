<script setup>
import {ref,onActivated,computed} from 'vue'
import {http} from '../api/http'
import Chart from '../components/Chart.vue'
const data=ref(null),busy=ref(false),error=ref(false)
async function load(){busy.value=true;error.value=false;try{data.value=(await http.get('/dashboard')).data}catch{error.value=true}finally{busy.value=false}}
const pie=computed(()=>({tooltip:{trigger:'item'},legend:{bottom:0},series:[{type:'pie',radius:['35%','64%'],data:data.value?.department_distribution.map(r=>({name:r.name,value:r.count}))||[]}]}))
const bars=computed(()=>({tooltip:{trigger:'axis'},xAxis:{type:'category',data:data.value?.attendance_trend.map(r=>r.date.slice(5))||[]},yAxis:{type:'value',minInterval:1},series:[{name:'正常出勤人数',type:'bar',data:data.value?.attendance_trend.map(r=>r.count)||[],itemStyle:{color:'#458467'}}]}))
onActivated(load)
</script>
<template><div class="page-title"><div><div class="eyebrow">OVERVIEW</div><h1>首页概览</h1><p>组织、出勤与制琴业务概况 · 日期按北京时间统计。</p></div><el-button @click="load" :loading="busy">刷新统计</el-button></div><div v-loading="busy"><el-result v-if="error" icon="error" title="数据加载失败"><template #extra><el-button @click="load">重试</el-button></template></el-result><template v-if="data"><div class="stat-grid" style="grid-template-columns:repeat(3,1fr)"><el-card v-for="[key,title] in [['active','在职员工总人数'],['departments','有效部门总数量'],['today_attendance','今日正常出勤人数'],['today_leave','今日请假人数'],['pending_leaves','待审批申请数'],['in_progress_tasks','进行中制琴任务数']]" :key="key" shadow="never"><p>{{title}}</p><strong>{{data[key]}}</strong></el-card></div><div class="chart-grid"><el-card shadow="never"><template #header>在职员工部门分布</template><el-empty v-if="!data.active" description="暂无在职员工"/><Chart v-else :option="pie"/></el-card><el-card shadow="never"><template #header>最近7天正常出勤人数</template><Chart :option="bars"/></el-card></div></template></div></template>
