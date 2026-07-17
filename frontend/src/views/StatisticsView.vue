<template>
  <div class="stats-page">
    <div class="page-header">
      <h1 class="page-title">数据统计</h1>
      <p class="page-desc" v-if="!loading">{{ isAdmin ? '全局视图 — 所有用户的推送数据汇总' : '你的推送数据汇总' }}</p>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>

    <template v-else>
      <!-- ── Overview Cards ── -->
      <div class="overview-cards">
        <div class="stat-card">
          <div class="stat-number">{{ overview.total_meetings }}</div>
          <div class="stat-label">已推送会议</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ overview.total_projects }}</div>
          <div class="stat-label">关联项目</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ overview.total_schedules }}</div>
          <div class="stat-label">日程总数</div>
        </div>
        <div class="stat-card stat-card--success">
          <div class="stat-number">{{ overview.active_schedules }}</div>
          <div class="stat-label">进行中日程</div>
        </div>
        <div class="stat-card stat-card--danger">
          <div class="stat-number">{{ overview.expired_schedules }}</div>
          <div class="stat-label">已过期日程</div>
        </div>
      </div>

      <!-- ── Two-column layout ── -->
      <div class="stats-grid">
        <!-- Left: Project Stats -->
        <div class="stats-panel">
          <h2 class="panel-title">项目统计</h2>
          <div v-if="projectStats.length === 0" class="empty">暂无项目数据</div>
          <table v-else class="data-table">
            <thead>
              <tr>
                <th>项目名称</th>
                <th class="col-num">会议数</th>
                <th class="col-num">日程数</th>
                <th class="col-date">最近会议</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in projectStats" :key="p.name">
                <td>{{ p.name }}</td>
                <td class="col-num">{{ p.meeting_count }}</td>
                <td class="col-num">{{ p.schedule_count }}</td>
                <td class="col-date">{{ formatDate(p.last_meeting) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Right: Person Stats -->
        <div class="stats-panel">
          <h2 class="panel-title">人员任务分配</h2>
          <div v-if="personStats.length === 0" class="empty">暂无日程数据</div>
          <table v-else class="data-table">
            <thead>
              <tr>
                <th>负责人</th>
                <th class="col-num">总任务</th>
                <th class="col-num">进行中</th>
                <th class="col-num">已过期</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in personStats" :key="p.name">
                <td>{{ p.name }}</td>
                <td class="col-num">{{ p.total }}</td>
                <td class="col-num text-success">{{ p.active }}</td>
                <td class="col-num text-danger">{{ p.expired }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ── Schedule Detail ── -->
      <div class="stats-panel">
        <div class="panel-header">
          <h2 class="panel-title">日程状态明细</h2>
          <div class="filter-tabs">
            <button :class="['filter-tab', { active: scheduleFilter === 'all' }]" @click="scheduleFilter = 'all'">全部 ({{ schedules.length }})</button>
            <button :class="['filter-tab', { active: scheduleFilter === 'active' }]" @click="scheduleFilter = 'active'">进行中 ({{ activeCount }})</button>
            <button :class="['filter-tab', { active: scheduleFilter === 'expired' }]" @click="scheduleFilter = 'expired'">已过期 ({{ expiredCount }})</button>
          </div>
        </div>
        <div v-if="filteredSchedules.length === 0" class="empty">暂无日程数据</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>日程标题</th>
              <th>负责人</th>
              <th>截止时间</th>
              <th>所属会议</th>
              <th>所属项目</th>
              <th class="col-status">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(s, i) in filteredSchedules" :key="i">
              <td>{{ s.title || '(无标题)' }}</td>
              <td>{{ s.owners.join('、') || '-' }}</td>
              <td>{{ s.end_time || '-' }}</td>
              <td>{{ s.meeting_name || '-' }}</td>
              <td>{{ s.project_name }}</td>
              <td class="col-status">
                <span :class="['status-badge', s.status === 'active' ? 'status-active' : 'status-expired']">
                  {{ s.status === 'active' ? '进行中' : '已过期' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api/index.js'
import { authStore } from '../store/auth.js'

const loading = ref(true)
const error = ref('')
const overview = ref({
  total_meetings: 0,
  total_projects: 0,
  total_schedules: 0,
  active_schedules: 0,
  expired_schedules: 0,
})
const projectStats = ref([])
const personStats = ref([])
const schedules = ref([])
const scheduleFilter = ref('all')

const isAdmin = computed(() => authStore.isAdmin)

const activeCount = computed(() => schedules.value.filter(s => s.status === 'active').length)
const expiredCount = computed(() => schedules.value.filter(s => s.status === 'expired').length)

const filteredSchedules = computed(() => {
  if (scheduleFilter.value === 'all') return schedules.value
  return schedules.value.filter(s => s.status === scheduleFilter.value)
})

function formatDate(val) {
  if (!val) return '-'
  const d = new Date(val)
  if (isNaN(d.getTime())) return val
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

onMounted(async () => {
  try {
    const data = await api.getStatistics()
    overview.value = data.overview
    projectStats.value = data.project_stats
    personStats.value = data.person_stats
    schedules.value = data.schedules
  } catch (e) {
    error.value = e.message || '加载统计数据失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stats-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
}

.page-header {
  margin-bottom: var(--space-6);
}

.page-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--gray-900);
  margin: 0 0 var(--space-1);
}

.page-desc {
  font-size: var(--text-sm);
  color: var(--gray-500);
  margin: 0;
}

.loading, .error-msg, .empty {
  text-align: center;
  padding: var(--space-10);
  color: var(--gray-500);
  font-size: var(--text-base);
}

.error-msg {
  color: var(--danger-text);
}

/* ── Overview Cards ── */
.overview-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--surface);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  text-align: center;
}

.stat-number {
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--gray-900);
  line-height: 1.2;
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--gray-500);
  margin-top: var(--space-1);
}

.stat-card--success .stat-number {
  color: var(--success);
}

.stat-card--danger .stat-number {
  color: var(--danger);
}

/* ── Grid ── */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

/* ── Panels ── */
.stats-panel {
  background: var(--surface);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  margin-bottom: var(--space-4);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.panel-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--gray-800);
  margin: 0;
}

/* ── Filter Tabs ── */
.filter-tabs {
  display: flex;
  gap: 2px;
  background: var(--gray-100);
  border-radius: var(--radius-md);
  padding: 2px;
}

.filter-tab {
  font-size: var(--text-xs);
  padding: 4px 12px;
  border: none;
  background: transparent;
  color: var(--gray-500);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s;
}

.filter-tab:hover {
  color: var(--gray-700);
}

.filter-tab.active {
  background: var(--surface);
  color: var(--primary-600);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,.06);
}

/* ── Table ── */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.data-table th {
  text-align: left;
  font-weight: 600;
  color: var(--gray-500);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: var(--space-2) var(--space-3);
  border-bottom: 2px solid var(--gray-100);
}

.data-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--gray-50);
  color: var(--gray-700);
}

.data-table tbody tr:hover {
  background: var(--gray-50);
}

.col-num {
  text-align: center;
  width: 80px;
}

.col-date {
  width: 120px;
}

.col-status {
  width: 80px;
}

.text-success { color: var(--success); font-weight: 600; }
.text-danger { color: var(--danger); font-weight: 600; }

/* ── Status Badge ── */
.status-badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-weight: 600;
}

.status-active {
  background: var(--success-bg);
  color: var(--success-text);
}

.status-expired {
  background: var(--danger-bg);
  color: var(--danger-text);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .overview-cards {
    grid-template-columns: repeat(3, 1fr);
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .overview-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
