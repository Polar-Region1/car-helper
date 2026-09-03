<template>
  <div class="search-interface">
    <!-- Hero区域 - 极简 -->
    <section class="hero" v-show="!hasResults">
      <div class="container">
        <div class="hero-content">
          <!-- 标题 -->
          <h1 class="hero-title">Find Your Car</h1>
          <p class="hero-subtitle">AI-powered intelligent search system</p>

          <!-- 搜索框 -->
          <div class="search-box">
            <input
              v-model="searchQuery"
              @keydown.enter="handleSearch"
              placeholder="Describe your needs, e.g., 10-20万 new energy SUV"
              class="search-input"
              :disabled="isLoading"
            />
            <button @click="handleSearch" class="search-button" :disabled="isLoading || !searchQuery.trim()">
              {{ isLoading ? 'Searching...' : 'Search' }}
            </button>
          </div>

          <!-- 快速标签 -->
          <div class="tags">
            <button
              v-for="tag in quickTags"
              :key="tag.id"
              @click="quickFilter(tag.query)"
              class="tag"
              :disabled="isLoading"
            >
              {{ tag.label }}
            </button>
          </div>

          <!-- 历史会话 -->
          <div class="history" v-if="sessions.length > 0">
            <h2 class="history-title">Recent Searches</h2>
            <div class="history-grid">
              <button
                v-for="(session, idx) in sessions.slice(0, 6)"
                :key="session.id"
                @click="resumeSession(session.id)"
                class="history-item"
              >
                <span class="history-number">{{ String(idx + 1).padStart(2, '0') }}</span>
                <span class="history-query">{{ session.last_query || '(Untitled)' }}</span>
                <span class="history-time">{{ formatTime(session.update_time) }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 结果区域 -->
    <section class="results" v-if="hasResults">
      <div class="container">
        <!-- 返回按钮 -->
        <button @click="resetSearch" class="back-button">
          ← Back to Search
        </button>

        <!-- AI分析 -->
        <div class="analysis" v-if="aiAnalysis || isLoading">
          <div class="analysis-header">
            <h2 class="analysis-title">Analysis</h2>
            <button
              v-if="thinkingProcess"
              @click="showThinking = !showThinking"
              class="toggle-button"
            >
              {{ showThinking ? 'Hide Process' : 'Show Process' }}
            </button>
          </div>

          <!-- 思考过程 -->
          <div class="thinking" v-if="showThinking && thinkingProcess">
            <h3 class="thinking-title">Reasoning</h3>
            <pre class="thinking-content">{{ thinkingProcess }}</pre>
          </div>

          <!-- 分析内容 -->
          <div class="analysis-content">
            <div v-html="formatText(aiAnalysis)" class="prose"></div>
            <div v-if="isLoading && !aiAnalysis" class="loading">
              <div class="loading-bar"></div>
            </div>
          </div>
        </div>

        <!-- 车型列表 -->
        <div class="cars" v-if="displayCars.length > 0">
          <div class="cars-header">
            <h2 class="cars-title">Results</h2>
            <span class="cars-count">{{ displayCars.length }} cars</span>
          </div>

          <div class="cars-grid">
            <article
              v-for="(car, index) in displayCars"
              :key="index"
              class="car-card"
            >
              <div class="car-image">
                <div class="car-placeholder">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <path d="M5 17h14M5 17v-4M5 17l-2 2M19 17v-4M19 17l2 2M7 13V7l2-2h6l2 2v6"/>
                    <circle cx="8" cy="17" r="1"/>
                    <circle cx="16" cy="17" r="1"/>
                  </svg>
                </div>
                <span v-if="car.badge" class="car-badge">{{ car.badge }}</span>
              </div>

              <div class="car-content">
                <h3 class="car-name">{{ car.name }}</h3>

                <dl class="car-specs">
                  <div class="spec">
                    <dt>Energy</dt>
                    <dd>{{ car.energy }}</dd>
                  </div>
                  <div class="spec">
                    <dt>Type</dt>
                    <dd>{{ car.level }}</dd>
                  </div>
                </dl>

                <div class="car-price">
                  <span class="price-label">Price</span>
                  <span class="price-value">{{ car.price }}</span>
                </div>

                <div class="car-actions">
                  <button class="action-button primary">Details</button>
                  <button class="action-button secondary">Compare</button>
                </div>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { sendChatMessage } from '@/utils/api'
import { marked } from 'marked'

export default {
  name: 'ChatView',
  setup() {
    const searchQuery = ref('')
    const currentQuery = ref('')
    const aiAnalysis = ref('')
    const thinkingProcess = ref('')
    const showThinking = ref(false)
    const isLoading = ref(false)
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
      { id: 1, label: '10-20万 EV', query: '推荐10-20万新能源车' },
      { id: 2, label: 'BYD SUV', query: '比亚迪有哪些SUV' },
      { id: 3, label: 'Pure EV', query: '推荐纯电动轿车' },
      { id: 4, label: 'Hybrid', query: '有哪些混动车型' },
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
        if (diff < 60) return 'Just now'
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
        return `${Math.floor(diff / 86400)}d ago`
      } catch (e) {
        return timeStr
      }
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

        // 缓存结果
        const resultCache = {
          query: currentQuery.value,
          analysis: aiAnalysis.value,
          thinking: thinkingProcess.value,
          cars: displayCars.value,
          timestamp: Date.now()
        }
        localStorage.setItem(`session_result_${sessionId.value}`, JSON.stringify(resultCache))

      } catch (error) {
        console.error('Search failed:', error)
        aiAnalysis.value = `Error: ${error.message}`
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
        console.error('Failed to load sessions:', e)
      }
    }

    const resumeSession = async (sid) => {
      const cachedResult = localStorage.getItem(`session_result_${sid}`)

      if (cachedResult) {
        try {
          const cached = JSON.parse(cachedResult)
          sessionId.value = sid
          localStorage.setItem('current_session_id', sid)

          currentQuery.value = cached.query
          aiAnalysis.value = cached.analysis
          thinkingProcess.value = cached.thinking || ''
          displayCars.value = cached.cars || []

          return
        } catch (e) {
          console.error('Failed to parse cache:', e)
        }
      }

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
      searchQuery,
      currentQuery,
      aiAnalysis,
      thinkingProcess,
      showThinking,
      isLoading,
      displayCars,
      quickTags,
      hasResults,
      sessions,
      formatText,
      formatTime,
      quickFilter,
      handleSearch,
      resetSearch,
      resumeSession
    }
  }
}
</script>

<style scoped>
.search-interface {
  min-height: calc(100vh - 64px);
}

/* Hero区域 */
.hero {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  padding: var(--space-xl) 0;
}

.hero-content {
  max-width: 720px;
  margin: 0 auto;
}

.hero-title {
  font-size: 48px;
  font-weight: 900;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin-bottom: var(--space-sm);
  color: var(--color-foreground);
}

.hero-subtitle {
  font-size: 18px;
  font-weight: 400;
  color: var(--color-muted-foreground);
  margin-bottom: var(--space-lg);
}

/* 搜索框 */
.search-box {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0;
  border: 2px solid var(--color-border);
  margin-bottom: var(--space-md);
  transition: border-color var(--duration) var(--easing);
}

.search-box:focus-within {
  border-color: var(--color-foreground);
}

.search-input {
  padding: var(--space-md);
  border: none;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 16px;
  color: var(--color-foreground);
}

.search-input:focus {
  outline: none;
}

.search-input::placeholder {
  color: var(--color-muted-foreground);
}

.search-button {
  padding: var(--space-md) var(--space-lg);
  background: var(--color-foreground);
  color: var(--color-background);
  border: none;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--duration) var(--easing);
}

.search-button:hover:not(:disabled) {
  opacity: 0.8;
}

.search-button:active:not(:disabled) {
  transform: translateY(1px);
}

.search-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 标签 */
.tags {
  display: flex;
  gap: var(--space-xs);
  flex-wrap: wrap;
  margin-bottom: var(--space-lg);
}

.tag {
  padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--color-border);
  background: transparent;
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--color-foreground);
  cursor: pointer;
  transition: all var(--duration) var(--easing);
}

.tag:hover:not(:disabled) {
  background: var(--color-foreground);
  color: var(--color-background);
}

.tag:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* 历史记录 */
.history {
  margin-top: var(--space-xl);
  padding-top: var(--space-xl);
  border-top: 1px solid var(--color-border);
}

.history-title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: var(--space-md);
  color: var(--color-muted-foreground);
}

.history-grid {
  display: grid;
  gap: 1px;
  background: var(--color-border);
  border: 1px solid var(--color-border);
}

.history-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--space-sm);
  align-items: center;
  padding: var(--space-md);
  background: var(--color-background);
  border: none;
  text-align: left;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: background var(--duration) var(--easing);
}

.history-item:hover {
  background: var(--color-muted);
}

.history-number {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-muted-foreground);
}

.history-query {
  font-size: 14px;
  color: var(--color-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-time {
  font-size: 12px;
  color: var(--color-muted-foreground);
}

/* 结果区域 */
.results {
  padding: var(--space-lg) 0;
}

.back-button {
  padding: var(--space-sm) var(--space-md);
  margin-bottom: var(--space-lg);
  border: 1px solid var(--color-border);
  background: transparent;
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--color-foreground);
  cursor: pointer;
  transition: all var(--duration) var(--easing);
}

.back-button:hover {
  background: var(--color-foreground);
  color: var(--color-background);
}

/* AI分析 */
.analysis {
  margin-bottom: var(--space-xl);
  padding: var(--space-lg);
  border: 1px solid var(--color-border);
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border);
}

.analysis-title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-foreground);
}

.toggle-button {
  padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--color-border);
  background: transparent;
  font-family: var(--font-sans);
  font-size: 12px;
  color: var(--color-foreground);
  cursor: pointer;
  transition: all var(--duration) var(--easing);
}

.toggle-button:hover {
  background: var(--color-muted);
}

.thinking {
  margin-bottom: var(--space-md);
  padding: var(--space-md);
  background: var(--color-muted);
}

.thinking-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: var(--space-sm);
  color: var(--color-muted-foreground);
}

.thinking-content {
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-foreground);
  white-space: pre-wrap;
}

.analysis-content {
  font-size: 16px;
  line-height: 1.6;
}

.prose :deep(h2) {
  font-size: 20px;
  font-weight: 700;
  margin: var(--space-md) 0 var(--space-sm);
}

.prose :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: var(--space-md) 0;
}

.prose :deep(th),
.prose :deep(td) {
  padding: var(--space-sm);
  border: 1px solid var(--color-border);
  text-align: left;
}

.prose :deep(th) {
  font-weight: 600;
  background: var(--color-muted);
}

.prose :deep(ul),
.prose :deep(ol) {
  margin: var(--space-sm) 0;
  padding-left: var(--space-md);
}

.loading {
  padding: var(--space-md) 0;
}

.loading-bar {
  height: 2px;
  background: var(--color-foreground);
  animation: loading 1.5s ease-in-out infinite;
}

@keyframes loading {
  0%, 100% {
    transform: translateX(-100%);
  }
  50% {
    transform: translateX(100%);
  }
}

/* 车型列表 */
.cars {
  margin-top: var(--space-xl);
}

.cars-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border);
}

.cars-title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-foreground);
}

.cars-count {
  font-size: 14px;
  color: var(--color-muted-foreground);
}

.cars-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-md);
}

.car-card {
  border: 1px solid var(--color-border);
  transition: border-color var(--duration) var(--easing);
}

.car-card:hover {
  border-color: var(--color-foreground);
}

.car-image {
  position: relative;
  aspect-ratio: 16 / 9;
  background: var(--color-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--color-border);
}

.car-placeholder {
  width: 80px;
  height: 80px;
  color: var(--color-muted-foreground);
}

.car-badge {
  position: absolute;
  top: var(--space-sm);
  right: var(--space-sm);
  padding: var(--space-xs) var(--space-sm);
  background: var(--color-foreground);
  color: var(--color-background);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.car-content {
  padding: var(--space-md);
}

.car-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: var(--space-sm);
  color: var(--color-foreground);
}

.car-specs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border);
}

.spec {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.spec dt {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-muted-foreground);
}

.spec dd {
  font-size: 14px;
  color: var(--color-foreground);
}

.car-price {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: var(--space-md);
}

.price-label {
  font-size: 12px;
  color: var(--color-muted-foreground);
}

.price-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-foreground);
}

.car-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-xs);
}

.action-button {
  padding: var(--space-sm);
  border: 1px solid var(--color-border);
  background: transparent;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-foreground);
  cursor: pointer;
  transition: all var(--duration) var(--easing);
}

.action-button.primary {
  background: var(--color-foreground);
  color: var(--color-background);
}

.action-button.primary:hover {
  opacity: 0.8;
}

.action-button.secondary:hover {
  background: var(--color-muted);
}

.action-button:active {
  transform: translateY(1px);
}

/* 响应式 */
@media (max-width: 768px) {
  .hero-title {
    font-size: 36px;
  }

  .search-box {
    grid-template-columns: 1fr;
  }

  .cars-grid {
    grid-template-columns: 1fr;
  }
}
</style>
