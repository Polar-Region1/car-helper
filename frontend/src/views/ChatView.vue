<template>
  <div class="car-finder">
    <!-- Hero区域 - 展厅风格 -->
    <section class="hero-showroom" v-show="!hasResults">
      <div class="hero-container">
        <!-- 主标题区 -->
        <div class="title-block">
          <div class="title-line">
            <span class="title-number">40,912</span>
            <span class="title-text">款车型</span>
          </div>
          <h1 class="main-title">
            FIND YOUR
            <span class="title-highlight">PERFECT</span>
            CAR
          </h1>
          <p class="subtitle">AI驱动的智能选车系统 · 精准匹配您的需求</p>
        </div>

        <!-- 搜索框 - 简约大气 -->
        <div class="search-container">
          <div class="search-wrapper">
            <input
              v-model="searchQuery"
              @keydown.enter="handleSearch"
              placeholder="描述您的需求，例如：预算20万，新能源SUV，适合家用"
              class="search-input"
              :disabled="isLoading"
            />
            <button @click="handleSearch" class="search-submit" :disabled="isLoading">
              <span v-if="!isLoading">搜索</span>
              <span v-else class="loading-spinner"></span>
            </button>
          </div>

          <!-- 快捷标签 - 扁平化设计 -->
          <div class="quick-tags">
            <button
              v-for="tag in quickTags"
              :key="tag.id"
              @click="quickFilter(tag.query)"
              class="tag-btn"
              :disabled="isLoading"
            >
              {{ tag.label }}
            </button>
          </div>
        </div>

        <!-- 历史会话 - 卡片式 -->
        <div class="history-panel" v-if="sessions.length > 0">
          <div class="panel-header">
            <span class="panel-title">最近搜索</span>
            <span class="panel-count">{{ sessions.length }}</span>
          </div>
          <div class="session-grid">
            <div
              v-for="(session, idx) in sessions.slice(0, 6)"
              :key="session.id"
              @click="resumeSession(session.id)"
              class="session-card"
              :style="{ animationDelay: `${idx * 0.1}s` }"
            >
              <div class="session-index">{{ String(idx + 1).padStart(2, '0') }}</div>
              <div class="session-content">
                <div class="session-query">{{ session.last_query || '(无标题)' }}</div>
                <div class="session-meta">{{ formatTime(session.update_time) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 装饰元素 -->
      <div class="hero-decoration">
        <div class="deco-line deco-line-1"></div>
        <div class="deco-line deco-line-2"></div>
      </div>
    </section>

    <!-- 结果区域 - 画廊风格 -->
    <section class="results-gallery" v-if="hasResults">
      <div class="gallery-container">
        <!-- 顶部操作栏 -->
        <div class="gallery-header">
          <button @click="resetSearch" class="back-button">
            <span class="back-arrow">←</span>
            <span class="back-text">返回搜索</span>
          </button>

          <div class="header-info">
            <span class="query-badge">{{ currentQuery }}</span>
            <div class="view-controls" v-if="displayCars.length > 0">
              <button
                @click="viewMode = 'grid'"
                class="view-btn"
                :class="{ active: viewMode === 'grid' }"
              >
                网格
              </button>
              <button
                @click="viewMode = 'list'"
                class="view-btn"
                :class="{ active: viewMode === 'list' }"
              >
                列表
              </button>
            </div>
          </div>
        </div>

        <!-- AI分析面板 - 高端设计 -->
        <div class="analysis-panel" v-if="aiAnalysis || isLoading">
          <div class="panel-decoration">
            <div class="deco-bar"></div>
          </div>

          <div class="panel-content">
            <div class="panel-header-row">
              <div class="panel-badge">
                <span class="badge-icon">✦</span>
                <span class="badge-text">AI 分析报告</span>
              </div>
              <button
                v-if="thinkingProcess"
                @click="showThinking = !showThinking"
                class="thinking-toggle"
              >
                {{ showThinking ? '隐藏思考过程' : '查看思考过程' }}
              </button>
            </div>

            <!-- 思考过程 -->
            <div class="thinking-section" v-if="showThinking && thinkingProcess">
              <div class="thinking-header">推理过程</div>
              <div class="thinking-content">{{ thinkingProcess }}</div>
            </div>

            <!-- 分析内容 -->
            <div class="analysis-content">
              <div class="content-text" v-html="formatText(aiAnalysis)"></div>
              <div v-if="isLoading && !aiAnalysis" class="loading-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 车型展示区 - 豪华卡片 -->
        <div class="cars-showcase" v-if="displayCars.length > 0">
          <div class="showcase-header">
            <h2 class="showcase-title">推荐车型</h2>
            <div class="showcase-count">{{ displayCars.length }} 款</div>
          </div>

          <div class="cars-grid" :class="`view-${viewMode}`">
            <div
              v-for="(car, index) in displayCars"
              :key="index"
              class="car-card"
              :style="{ animationDelay: `${index * 0.08}s` }"
            >
              <!-- 车型图片区 -->
              <div class="card-visual">
                <div class="visual-placeholder">
                  <svg class="car-icon" viewBox="0 0 24 24" fill="none">
                    <path d="M5 13L3 15H6L5 13Z" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M19 13L21 15H18L19 13Z" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M5 17H19" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M6 11L8 6H16L18 11" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M4 15V11L6 11" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M20 15V11L18 11" stroke="currentColor" stroke-width="1.5"/>
                  </svg>
                </div>
                <div class="card-badge" v-if="car.badge">{{ car.badge }}</div>
              </div>

              <!-- 车型信息 -->
              <div class="card-info">
                <h3 class="car-title">{{ car.name }}</h3>

                <div class="car-specs">
                  <div class="spec-item">
                    <span class="spec-label">能源</span>
                    <span class="spec-value">{{ car.energy }}</span>
                  </div>
                  <div class="spec-divider"></div>
                  <div class="spec-item">
                    <span class="spec-label">级别</span>
                    <span class="spec-value">{{ car.level }}</span>
                  </div>
                </div>

                <div class="car-pricing">
                  <div class="price-label">指导价</div>
                  <div class="price-value">{{ car.price }}</div>
                </div>

                <div class="card-actions">
                  <button class="action-btn action-primary">
                    <span>详情</span>
                  </button>
                  <button class="action-btn action-secondary">
                    <span>对比</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 主题切换按钮 -->
    <button class="theme-switcher" @click="toggleTheme" title="切换主题">
      <span v-if="isDark">☀</span>
      <span v-else>☾</span>
    </button>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick } from 'vue'
import { sendChatMessage } from '@/utils/api'
import { marked } from 'marked'

export default {
  name: 'ChatView',
  setup() {
    const isDark = ref(true) // 默认深色主题
    const searchQuery = ref('')
    const currentQuery = ref('')
    const aiAnalysis = ref('')
    const thinkingProcess = ref('')
    const showThinking = ref(false)
    const isLoading = ref(false)
    const viewMode = ref('grid')
    const displayCars = ref([])
    const sessions = ref([])

    let sessionId = ref(localStorage.getItem('current_session_id'))
    if (!sessionId.value) {
      sessionId.value = `session_${Date.now()}`
      localStorage.setItem('current_session_id', sessionId.value)
    }

    marked.setOptions({
      breaks: true,
      gfm: true,
      headerIds: false,
      mangle: false
    })

    const quickTags = [
      { id: 1, label: '10-20万新能源', query: '推荐10-20万新能源车' },
      { id: 2, label: '比亚迪SUV', query: '比亚迪有哪些SUV' },
      { id: 3, label: '纯电轿车', query: '推荐纯电动轿车' },
      { id: 4, label: '混动车型', query: '有哪些混动车型' },
    ]

    const hasResults = computed(() => displayCars.value.length > 0 || aiAnalysis.value || isLoading.value)

    const formatText = (text) => {
      if (!text) return ''
      try {
        return marked.parse(text)
      } catch (e) {
        return text.replace(/\n/g, '<br>')
      }
    }

    const formatTime = (timeStr) => {
      if (!timeStr) return ''
      try {
        const date = new Date(timeStr)
        const now = new Date()
        const diff = Math.floor((now - date) / 1000)
        if (diff < 60) return '刚刚'
        if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
        if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
        return `${Math.floor(diff / 86400)}天前`
      } catch (e) {
        return timeStr
      }
    }

    const toggleTheme = () => {
      isDark.value = !isDark.value
    }

    const quickFilter = (query) => {
      searchQuery.value = query
      handleSearch()
    }

    const resetSearch = () => {
      currentQuery.value = ''
      aiAnalysis.value = ''
      thinkingProcess.value = ''
      displayCars.value = []
      showThinking.value = false
      isLoading.value = false
      searchQuery.value = ''
    }

    const handleSearch = async () => {
      if (!searchQuery.value.trim() || isLoading.value) return

      currentQuery.value = searchQuery.value
      isLoading.value = true
      aiAnalysis.value = ''
      thinkingProcess.value = ''
      displayCars.value = []
      showThinking.value = false

      try {
        await sendChatMessage(
          searchQuery.value,
          sessionId.value,
          (chunk) => {
            if (chunk.type === 'reasoning_content') {
              thinkingProcess.value += chunk.content
            } else if (chunk.type === 'content') {
              aiAnalysis.value += chunk.content
            } else if (chunk.type === 'cars_data') {
              displayCars.value = chunk.cars
            }
          }
        )
        loadSessions()
      } catch (error) {
        console.error('搜索失败:', error)
        aiAnalysis.value = `抱歉，查询出错了：${error.message}`
      } finally {
        isLoading.value = false
      }
    }

    const loadSessions = async () => {
      try {
        const response = await fetch('/api/sessions')
        const data = await response.json()
        sessions.value = data.sessions || []
      } catch (e) {
        console.error('加载会话失败:', e)
      }
    }

    const resumeSession = (sid) => {
      sessionId.value = sid
      localStorage.setItem('current_session_id', sid)
      const session = sessions.value.find(s => s.id === sid)
      if (session && session.last_query) {
        searchQuery.value = session.last_query
        handleSearch()
      }
    }

    onMounted(() => {
      loadSessions()
    })

    return {
      isDark,
      searchQuery,
      currentQuery,
      aiAnalysis,
      thinkingProcess,
      showThinking,
      isLoading,
      viewMode,
      displayCars,
      quickTags,
      hasResults,
      sessions,
      formatText,
      formatTime,
      toggleTheme,
      quickFilter,
      handleSearch,
      resetSearch,
      resumeSession
    }
  }
}
</script>

<style scoped>
.car-finder {
  min-height: 100vh;
  position: relative;
}

/* ========== Hero Showroom ========== */
.hero-showroom {
  min-height: calc(100vh - 80px);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 4rem 2rem;
}

.hero-container {
  max-width: 1200px;
  width: 100%;
  z-index: 2;
}

/* 标题区 */
.title-block {
  margin-bottom: 4rem;
  animation: fadeInUp 0.8s ease-out;
}

.title-line {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.title-number {
  font-family: var(--font-display);
  font-size: 4rem;
  color: var(--color-accent);
  line-height: 1;
  letter-spacing: 0.05em;
}

.title-text {
  font-size: 1.2rem;
  color: var(--color-text-muted);
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.main-title {
  font-family: var(--font-display);
  font-size: 5.5rem;
  font-weight: 700;
  line-height: 0.9;
  letter-spacing: 0.02em;
  margin-bottom: 1rem;
  color: var(--color-text);
}

.title-highlight {
  display: block;
  color: var(--color-accent);
  font-size: 6.5rem;
  font-style: italic;
}

.subtitle {
  font-size: 1.1rem;
  color: var(--color-text-muted);
  letter-spacing: 0.05em;
  font-weight: 300;
}

/* 搜索容器 */
.search-container {
  margin-bottom: 4rem;
  animation: fadeInUp 0.8s ease-out 0.2s both;
}

.search-wrapper {
  display: flex;
  gap: 0;
  margin-bottom: 2rem;
  border: 2px solid var(--color-border);
  transition: border-color var(--duration-normal);
}

.search-wrapper:focus-within {
  border-color: var(--color-accent);
}

.search-input {
  flex: 1;
  padding: 1.5rem 2rem;
  background: transparent;
  border: none;
  color: var(--color-text);
  font-size: 1.1rem;
  font-family: var(--font-body);
  font-weight: 300;
  letter-spacing: 0.02em;
  outline: none;
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.search-input:disabled {
  opacity: 0.5;
}

.search-submit {
  padding: 1.5rem 3rem;
  background: var(--color-accent);
  border: none;
  color: var(--color-primary);
  font-family: var(--font-display);
  font-size: 1.2rem;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: all var(--duration-normal);
  position: relative;
  overflow: hidden;
}

.search-submit::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  transition: left 0.5s;
}

.search-submit:hover::before {
  left: 100%;
}

.search-submit:hover {
  background: #e5c158;
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.search-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 快捷标签 */
.quick-tags {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.tag-btn {
  padding: 0.6rem 1.5rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 0.9rem;
  font-weight: 400;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.tag-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
  transform: translateY(-2px);
}

.tag-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* 历史面板 */
.history-panel {
  animation: fadeInUp 0.8s ease-out 0.4s both;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--color-border);
}

.panel-title {
  font-family: var(--font-display);
  font-size: 1.5rem;
  letter-spacing: 0.1em;
  color: var(--color-text);
}

.panel-count {
  font-family: var(--font-display);
  font-size: 1.2rem;
  color: var(--color-accent);
}

.session-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.session-card {
  display: flex;
  gap: 1rem;
  padding: 1.25rem;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all var(--duration-normal);
  animation: slideInRight 0.6s ease-out both;
}

.session-card:hover {
  border-color: var(--color-accent);
  transform: translateX(8px);
  background: rgba(26, 26, 26, 0.8);
}

.session-index {
  font-family: var(--font-display);
  font-size: 1.5rem;
  color: var(--color-accent);
  flex-shrink: 0;
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-query {
  color: var(--color-text);
  font-weight: 500;
  margin-bottom: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

/* 装饰元素 */
.hero-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.deco-line {
  position: absolute;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-accent), transparent);
  opacity: 0.2;
}

.deco-line-1 {
  top: 20%;
  left: 0;
  right: 0;
  animation: slideLineRight 3s ease-in-out infinite;
}

.deco-line-2 {
  bottom: 30%;
  left: 0;
  right: 0;
  animation: slideLineLeft 3s ease-in-out infinite 1.5s;
}

@keyframes slideLineRight {
  0%, 100% { transform: translateX(-100%); }
  50% { transform: translateX(100%); }
}

@keyframes slideLineLeft {
  0%, 100% { transform: translateX(100%); }
  50% { transform: translateX(-100%); }
}

/* ========== Results Gallery ========== */
.results-gallery {
  min-height: calc(100vh - 80px);
  padding: 3rem 2rem;
}

.gallery-container {
  max-width: 1600px;
  margin: 0 auto;
}

/* 顶部操作栏 */
.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
  animation: fadeInUp 0.6s ease-out;
}

.back-button {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text);
  font-size: 0.95rem;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.back-button:hover {
  border-color: var(--color-accent);
  transform: translateX(-4px);
}

.back-arrow {
  font-size: 1.2rem;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.query-badge {
  padding: 0.5rem 1.5rem;
  background: rgba(212, 175, 55, 0.1);
  border: 1px solid var(--color-accent);
  color: var(--color-accent);
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0.05em;
}

.view-controls {
  display: flex;
  gap: 0;
  border: 1px solid var(--color-border);
}

.view-btn {
  padding: 0.5rem 1.25rem;
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.view-btn:first-child {
  border-right: 1px solid var(--color-border);
}

.view-btn.active {
  background: var(--color-accent);
  color: var(--color-primary);
}

/* AI分析面板 */
.analysis-panel {
  position: relative;
  margin-bottom: 4rem;
  padding: 3rem;
  background: rgba(26, 26, 26, 0.8);
  border: 1px solid var(--color-border);
  animation: slideInRight 0.8s ease-out;
}

.panel-decoration {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 4px;
  overflow: hidden;
}

.deco-bar {
  height: 40%;
  width: 100%;
  background: var(--color-accent);
  animation: slideDecoBar 3s ease-in-out infinite;
}

@keyframes slideDecoBar {
  0%, 100% { transform: translateY(-100%); }
  50% { transform: translateY(250%); }
}

.panel-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.panel-badge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.badge-icon {
  font-size: 1.5rem;
  color: var(--color-accent);
}

.badge-text {
  font-family: var(--font-display);
  font-size: 1.3rem;
  letter-spacing: 0.1em;
  color: var(--color-text);
}

.thinking-toggle {
  padding: 0.5rem 1.25rem;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.thinking-toggle:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.thinking-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: rgba(10, 10, 10, 0.6);
  border-left: 2px solid var(--color-accent);
}

.thinking-header {
  font-family: var(--font-display);
  font-size: 1.1rem;
  letter-spacing: 0.1em;
  color: var(--color-accent);
  margin-bottom: 1rem;
}

.thinking-content {
  font-size: 0.95rem;
  line-height: 1.8;
  color: var(--color-text-muted);
  white-space: pre-wrap;
}

.analysis-content {
  font-size: 1.05rem;
  line-height: 1.9;
  color: var(--color-text);
}

.content-text :deep(h2) {
  font-family: var(--font-display);
  font-size: 1.8rem;
  margin: 2rem 0 1rem;
  color: var(--color-accent);
  letter-spacing: 0.05em;
}

.content-text :deep(table) {
  width: 100%;
  margin: 2rem 0;
  border-collapse: collapse;
}

.content-text :deep(th),
.content-text :deep(td) {
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border);
  text-align: left;
}

.content-text :deep(th) {
  background: rgba(212, 175, 55, 0.1);
  font-weight: 600;
  color: var(--color-accent);
}

.content-text :deep(ul),
.content-text :deep(ol) {
  margin: 1rem 0;
  padding-left: 2rem;
}

.content-text :deep(li) {
  margin: 0.5rem 0;
}

.loading-dots {
  display: flex;
  gap: 0.5rem;
  padding: 1rem 0;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  background: var(--color-accent);
  border-radius: 50%;
  animation: bounce-dot 1.4s infinite;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce-dot {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-10px); opacity: 1; }
}

/* 车型展示 */
.cars-showcase {
  animation: fadeInUp 0.8s ease-out 0.2s both;
}

.showcase-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2rem;
}

.showcase-title {
  font-family: var(--font-display);
  font-size: 2.5rem;
  letter-spacing: 0.1em;
  color: var(--color-text);
}

.showcase-count {
  font-family: var(--font-display);
  font-size: 1.5rem;
  color: var(--color-accent);
}

.cars-grid {
  display: grid;
  gap: 2rem;
}

.cars-grid.view-grid {
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
}

.cars-grid.view-list {
  grid-template-columns: 1fr;
}

.car-card {
  background: rgba(26, 26, 26, 0.8);
  border: 1px solid var(--color-border);
  overflow: hidden;
  transition: all var(--duration-normal);
  animation: fadeInUp 0.6s ease-out both;
}

.car-card:hover {
  border-color: var(--color-accent);
  transform: translateY(-8px);
  box-shadow: var(--shadow-lg);
}

.card-visual {
  position: relative;
  height: 240px;
  background: linear-gradient(135deg, rgba(212, 175, 55, 0.1) 0%, rgba(196, 30, 58, 0.1) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.card-visual::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(45deg, transparent 48%, var(--color-accent) 49%, var(--color-accent) 51%, transparent 52%),
    linear-gradient(-45deg, transparent 48%, var(--color-accent) 49%, var(--color-accent) 51%, transparent 52%);
  background-size: 40px 40px;
  opacity: 0.03;
}

.visual-placeholder {
  position: relative;
  z-index: 1;
}

.car-icon {
  width: 120px;
  height: 120px;
  color: var(--color-accent);
  opacity: 0.4;
}

.card-badge {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  padding: 0.4rem 1rem;
  background: var(--color-accent);
  color: var(--color-primary);
  font-family: var(--font-display);
  font-size: 0.85rem;
  letter-spacing: 0.1em;
}

.card-info {
  padding: 2rem;
}

.car-title {
  font-size: 1.4rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: var(--color-text);
  line-height: 1.3;
}

.car-specs {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.spec-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.spec-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.spec-value {
  font-weight: 600;
  color: var(--color-text);
}

.spec-divider {
  width: 1px;
  height: 30px;
  background: var(--color-border);
}

.car-pricing {
  margin-bottom: 1.5rem;
}

.price-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.5rem;
}

.price-value {
  font-family: var(--font-display);
  font-size: 1.8rem;
  color: var(--color-accent-red);
  letter-spacing: 0.05em;
}

.card-actions {
  display: flex;
  gap: 1rem;
}

.action-btn {
  flex: 1;
  padding: 0.875rem;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text);
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.action-btn:hover {
  transform: translateY(-2px);
}

.action-primary {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.action-primary:hover {
  background: var(--color-accent);
  color: var(--color-primary);
}

.action-secondary:hover {
  border-color: var(--color-text);
}

/* 主题切换 */
.theme-switcher {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: rgba(26, 26, 26, 0.9);
  backdrop-filter: blur(10px);
  color: var(--color-accent);
  font-size: 1.5rem;
  cursor: pointer;
  transition: all var(--duration-normal);
  z-index: 50;
  box-shadow: var(--shadow-md);
}

.theme-switcher:hover {
  transform: rotate(180deg) scale(1.1);
  border-color: var(--color-accent);
}

/* 响应式 */
@media (max-width: 768px) {
  .main-title {
    font-size: 3.5rem;
  }

  .title-highlight {
    font-size: 4.5rem;
  }

  .title-number {
    font-size: 2.5rem;
  }

  .search-wrapper {
    flex-direction: column;
  }

  .cars-grid.view-grid {
    grid-template-columns: 1fr;
  }

  .gallery-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
}
</style>
