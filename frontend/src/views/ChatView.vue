<template>
  <div class="car-hub" :class="{ 'dark-mode': isDark }">
    <!-- Hero区域 -->
    <section class="hero-section" v-show="!hasResults">
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <h1 class="hero-title">
          <span class="gradient-text">智能选车</span>
          <br>从这里开始
        </h1>
        <p class="hero-subtitle">40,912款车型 · AI智能推荐 · 一键对比</p>

        <!-- 主搜索栏 -->
        <div class="hero-search">
          <input
            v-model="searchQuery"
            @keydown.enter="handleSearch"
            placeholder="说说你的需求，比如：20万左右的新能源SUV"
            class="hero-input"
            :disabled="isLoading"
          />
          <button @click="handleSearch" class="hero-button" :disabled="isLoading">
            <span class="button-text">{{ isLoading ? '搜索中...' : '立即搜索' }}</span>
            <span class="button-icon">→</span>
          </button>
        </div>

        <!-- 快速筛选标签 -->
        <div class="quick-filters">
          <button
            v-for="tag in quickTags"
            :key="tag.id"
            @click="quickFilter(tag.query)"
            class="filter-tag"
            :disabled="isLoading"
          >
            {{ tag.label }}
          </button>
        </div>

        <!-- 历史会话 -->
        <div class="history-section" v-if="sessions.length > 0">
          <h3 class="history-title">最近会话</h3>
          <div class="session-list">
            <div
              v-for="session in sessions.slice(0, 5)"
              :key="session.id"
              @click="resumeSession(session.id)"
              class="session-item"
            >
              <div class="session-query">{{ session.last_query || '(无标题)' }}</div>
              <div class="session-time">{{ formatTime(session.update_time) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 滚动提示 -->
      <div class="scroll-indicator" v-if="!isLoading">
        <div class="scroll-arrow">↓</div>
      </div>
    </section>

    <!-- 结果展示区域 -->
    <section class="results-section" v-if="hasResults" ref="resultsArea">
      <div class="container">
        <!-- 查询信息栏 -->
        <div class="query-info">
          <div class="query-left">
            <button @click="resetSearch" class="back-btn">← 返回</button>
            <span class="query-label">当前搜索：</span>
            <span class="query-text">{{ currentQuery }}</span>
          </div>
          <div class="query-right">
            <button class="icon-btn" @click="toggleView" v-if="displayCars.length > 0">
              <span v-if="viewMode === 'grid'">☷</span>
              <span v-else>⊞</span>
            </button>
          </div>
        </div>

        <!-- AI分析面板 -->
        <div class="ai-analysis" v-if="aiAnalysis || isLoading">
          <div class="analysis-header">
            <div class="ai-badge">
              <span class="ai-icon">✨</span>
              <span>AI分析</span>
            </div>
            <button @click="showThinking = !showThinking" class="toggle-btn" v-if="thinkingProcess">
              {{ showThinking ? '收起思考' : '展开思考' }}
            </button>
          </div>

          <div class="thinking-process" v-show="showThinking" v-if="thinkingProcess">
            <div class="thinking-title">💭 思考过程</div>
            <div class="thinking-text">{{ thinkingProcess }}</div>
          </div>

          <div class="analysis-content">
            <div class="analysis-text" v-html="formatText(aiAnalysis)"></div>
            <div v-if="isLoading && !aiAnalysis" class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <!-- 车型卡片网格 -->
        <div class="cars-grid" :class="viewMode" v-if="displayCars.length > 0">
          <div
            v-for="(car, index) in displayCars"
            :key="index"
            class="car-card"
            :style="{ animationDelay: `${index * 0.05}s` }"
          >
            <div class="card-image">
              <div class="image-placeholder">
                <span class="car-emoji">🚗</span>
              </div>
              <div class="card-badge" v-if="car.badge">{{ car.badge }}</div>
            </div>

            <div class="card-content">
              <h3 class="car-name">{{ car.name }}</h3>
              <div class="car-meta">
                <span class="meta-item">
                  <span class="meta-icon">⚡</span>
                  {{ car.energy }}
                </span>
                <span class="meta-item">
                  <span class="meta-icon">🏷️</span>
                  {{ car.level }}
                </span>
              </div>

              <div class="car-price">
                <span class="price-label">指导价</span>
                <span class="price-value">{{ car.price }}</span>
              </div>

              <div class="card-actions">
                <button class="action-btn primary">查看详情</button>
                <button class="action-btn secondary">加入对比</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 深色模式切换 -->
    <button class="theme-toggle" @click="toggleTheme">
      <span v-if="isDark">☀️</span>
      <span v-else>🌙</span>
    </button>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick } from 'vue'
import { sendChatMessage, getSessionHistory } from '@/utils/api'
import { marked } from 'marked'

export default {
  name: 'ChatView',
  setup() {
    const isDark = ref(false)
    const searchQuery = ref('')
    const currentQuery = ref('')
    const aiAnalysis = ref('')
    const thinkingProcess = ref('')
    const showThinking = ref(false)
    const isLoading = ref(false)
    const viewMode = ref('grid')
    const displayCars = ref([])
    const resultsArea = ref(null)
    const sessions = ref([])

    // 从localStorage恢复session_id或创建新的
    let sessionId = ref(localStorage.getItem('current_session_id'))
    if (!sessionId.value) {
      sessionId.value = `session_${Date.now()}`
      localStorage.setItem('current_session_id', sessionId.value)
    }

    // 配置marked
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
        console.error('Markdown parse error:', e)
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

    const toggleView = () => {
      viewMode.value = viewMode.value === 'grid' ? 'list' : 'grid'
    }

    const quickFilter = (query) => {
      searchQuery.value = query
      handleSearch()
    }

    const scrollToBottom = () => {
      nextTick(() => {
        if (resultsArea.value) {
          resultsArea.value.scrollTop = resultsArea.value.scrollHeight
        }
      })
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

      // 滚动到结果区域
      setTimeout(scrollToBottom, 100)

      try {
        await sendChatMessage(
          searchQuery.value,
          sessionId.value,
          (chunk) => {
            if (chunk.type === 'reasoning_content') {
              thinkingProcess.value += chunk.content
            } else if (chunk.type === 'content') {
              aiAnalysis.value += chunk.content
              scrollToBottom()
            } else if (chunk.type === 'cars_data') {
              displayCars.value = chunk.cars
              scrollToBottom()
            }
          }
        )

        // 查询完成后刷新会话列表
        loadSessions()

      } catch (error) {
        console.error('搜索失败:', error)
        aiAnalysis.value = `抱歉，查询出错了：${error.message}`
      } finally {
        isLoading.value = false
        scrollToBottom()
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

      // 找到会话的最后一个查询
      const session = sessions.value.find(s => s.id === sid)
      if (session && session.last_query) {
        searchQuery.value = session.last_query
        handleSearch()
      }
    }

    // 组件挂载时加载会话列表
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
      resultsArea,
      sessions,
      formatText,
      formatTime,
      toggleTheme,
      toggleView,
      quickFilter,
      handleSearch,
      resetSearch,
      resumeSession
    }
  }
}
</script>

<style scoped>
.car-hub {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transition: all 0.3s ease;
}

.dark-mode {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

/* Hero区域 */
.hero-section {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(255,255,255,0.1) 0%, transparent 50%);
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 10;
  text-align: center;
  padding: 2rem;
  max-width: 900px;
  width: 100%;
}

.hero-title {
  font-size: 4rem;
  font-weight: 800;
  color: white;
  margin-bottom: 1rem;
  line-height: 1.2;
  animation: fadeInUp 0.8s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.gradient-text {
  background: linear-gradient(45deg, #fff, #a8edea);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 1.3rem;
  color: rgba(255,255,255,0.9);
  margin-bottom: 3rem;
  animation: fadeInUp 0.8s ease-out 0.2s both;
}

.hero-search {
  display: flex;
  gap: 1rem;
  max-width: 700px;
  margin: 0 auto 2rem;
  animation: fadeInUp 0.8s ease-out 0.4s both;
}

.hero-input {
  flex: 1;
  padding: 1.2rem 1.5rem;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 16px;
  font-size: 1rem;
  background: rgba(255,255,255,0.1);
  backdrop-filter: blur(10px);
  color: white;
  transition: all 0.3s;
}

.hero-input::placeholder {
  color: rgba(255,255,255,0.6);
}

.hero-input:focus {
  outline: none;
  border-color: rgba(255,255,255,0.6);
  background: rgba(255,255,255,0.15);
}

.hero-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hero-button {
  padding: 1.2rem 2.5rem;
  background: white;
  border: none;
  border-radius: 16px;
  font-size: 1.1rem;
  font-weight: 600;
  color: #667eea;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.3s;
}

.hero-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}

.hero-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.button-icon {
  font-size: 1.5rem;
  transition: transform 0.3s;
}

.hero-button:hover:not(:disabled) .button-icon {
  transform: translateX(4px);
}

.quick-filters {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  animation: fadeInUp 0.8s ease-out 0.6s both;
  margin-bottom: 2rem;
}

.filter-tag {
  padding: 0.6rem 1.5rem;
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 24px;
  color: white;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s;
}

.filter-tag:hover:not(:disabled) {
  background: rgba(255,255,255,0.25);
  transform: translateY(-2px);
}

.filter-tag:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 历史会话 */
.history-section {
  margin-top: 3rem;
  animation: fadeInUp 0.8s ease-out 0.8s both;
}

.history-title {
  color: white;
  font-size: 1.2rem;
  margin-bottom: 1rem;
  opacity: 0.9;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  max-width: 600px;
  margin: 0 auto;
}

.session-item {
  background: rgba(255,255,255,0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 12px;
  padding: 1rem 1.5rem;
  cursor: pointer;
  transition: all 0.3s;
}

.session-item:hover {
  background: rgba(255,255,255,0.2);
  transform: translateX(4px);
}

.session-query {
  color: white;
  font-weight: 500;
  margin-bottom: 0.3rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  color: rgba(255,255,255,0.6);
  font-size: 0.85rem;
}

.scroll-indicator {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50% { transform: translateX(-50%) translateY(10px); }
}

.scroll-arrow {
  color: white;
  font-size: 2rem;
  opacity: 0.7;
}

/* 结果区域 */
.results-section {
  background: #f8f9fa;
  min-height: 100vh;
  padding: 2rem 0;
  overflow-y: auto;
}

.dark-mode .results-section {
  background: #0f0f1e;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
}

.query-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  background: white;
  border-radius: 16px;
  margin-bottom: 2rem;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

.dark-mode .query-info {
  background: #1a1a2e;
  color: white;
}

.query-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.back-btn {
  padding: 0.5rem 1rem;
  background: #f0f0f0;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s;
}

.back-btn:hover {
  background: #e0e0e0;
  transform: translateX(-2px);
}

.query-label {
  color: #888;
}

.query-text {
  font-weight: 600;
  color: #667eea;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: #f0f0f0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.2rem;
  transition: all 0.3s;
}

.icon-btn:hover {
  background: #e0e0e0;
  transform: scale(1.05);
}

/* AI分析面板 */
.ai-analysis {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 2rem;
  margin-bottom: 2rem;
  color: white;
  animation: slideIn 0.5s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.ai-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 1.1rem;
}

.ai-icon {
  font-size: 1.3rem;
}

.toggle-btn {
  padding: 0.5rem 1rem;
  background: rgba(255,255,255,0.2);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 0.9rem;
}

.toggle-btn:hover {
  background: rgba(255,255,255,0.3);
}

.analysis-content {
  line-height: 1.8;
  font-size: 1.05rem;
  min-height: 2rem;
}

.analysis-text {
  word-wrap: break-word;
}

.analysis-text :deep(h1),
.analysis-text :deep(h2),
.analysis-text :deep(h3) {
  margin-top: 1.5rem;
  margin-bottom: 0.8rem;
}

.analysis-text :deep(h2) {
  font-size: 1.3rem;
  border-bottom: 1px solid rgba(255,255,255,0.3);
  padding-bottom: 0.5rem;
}

.analysis-text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  background: rgba(255,255,255,0.1);
  border-radius: 8px;
  overflow: hidden;
}

.analysis-text :deep(th),
.analysis-text :deep(td) {
  padding: 0.8rem;
  border: 1px solid rgba(255,255,255,0.2);
  text-align: left;
}

.analysis-text :deep(th) {
  background: rgba(255,255,255,0.15);
  font-weight: 600;
}

.analysis-text :deep(ul),
.analysis-text :deep(ol) {
  margin: 1rem 0;
  padding-left: 2rem;
}

.analysis-text :deep(li) {
  margin: 0.5rem 0;
}

.analysis-text :deep(code) {
  background: rgba(0,0,0,0.2);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
}

.analysis-text :deep(pre) {
  background: rgba(0,0,0,0.2);
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1rem 0;
}

.thinking-process {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: rgba(0,0,0,0.2);
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.2);
}

.thinking-title {
  font-weight: 600;
  margin-bottom: 0.8rem;
  opacity: 0.9;
}

.thinking-text {
  opacity: 0.8;
  font-size: 0.95rem;
  white-space: pre-wrap;
  line-height: 1.6;
}

.typing-indicator {
  display: inline-flex;
  gap: 4px;
  padding: 0.5rem 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255,255,255,0.8);
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
}

/* 车型卡片网格 */
.cars-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

.car-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  animation: cardFadeIn 0.5s ease-out both;
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dark-mode .car-card {
  background: #1a1a2e;
  color: white;
}

.car-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.3);
}

.card-image {
  position: relative;
  height: 200px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-placeholder {
  font-size: 4rem;
}

.card-badge {
  position: absolute;
  top: 1rem;
  right: 1rem;
  padding: 0.4rem 1rem;
  background: rgba(255,255,255,0.95);
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #667eea;
}

.card-content {
  padding: 1.5rem;
}

.car-name {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: #2c3e50;
}

.dark-mode .car-name {
  color: white;
}

.car-meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.9rem;
  color: #666;
}

.dark-mode .meta-item {
  color: #aaa;
}

.meta-icon {
  font-size: 1.1rem;
}

.car-price {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-top: 1px solid #eee;
  border-bottom: 1px solid #eee;
  margin-bottom: 1rem;
}

.dark-mode .car-price {
  border-color: #333;
}

.price-label {
  font-size: 0.85rem;
  color: #888;
}

.price-value {
  font-size: 1.2rem;
  font-weight: 700;
  color: #e74c3c;
}

.card-actions {
  display: flex;
  gap: 0.8rem;
}

.action-btn {
  flex: 1;
  padding: 0.8rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.action-btn.primary {
  background: #667eea;
  color: white;
}

.action-btn.primary:hover {
  background: #5568d3;
  transform: translateY(-2px);
}

.action-btn.secondary {
  background: #f0f0f0;
  color: #555;
}

.action-btn.secondary:hover {
  background: #e0e0e0;
}

/* 主题切换 */
.theme-toggle {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  border: none;
  background: white;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
  font-size: 1.5rem;
  cursor: pointer;
  transition: all 0.3s;
  z-index: 100;
}

.theme-toggle:hover {
  transform: scale(1.1) rotate(20deg);
}
</style>
