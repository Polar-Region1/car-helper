<template>
  <div class="car-hub" :class="{ 'dark-mode': isDark }">
    <!-- Hero区域 -->
    <section class="hero-section">
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
          />
          <button @click="handleSearch" class="hero-button">
            <span class="button-text">立即搜索</span>
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
          >
            {{ tag.label }}
          </button>
        </div>
      </div>

      <!-- 滚动提示 -->
      <div class="scroll-indicator">
        <div class="scroll-arrow">↓</div>
      </div>
    </section>

    <!-- 结果展示区域 -->
    <section class="results-section" v-if="hasResults">
      <div class="container">
        <!-- 查询信息栏 -->
        <div class="query-info">
          <div class="query-left">
            <span class="query-label">当前搜索：</span>
            <span class="query-text">{{ currentQuery }}</span>
          </div>
          <div class="query-right">
            <button class="icon-btn" @click="toggleView">
              <span v-if="viewMode === 'grid'">☷</span>
              <span v-else>⊞</span>
            </button>
          </div>
        </div>

        <!-- AI分析面板 -->
        <div class="ai-analysis" v-if="aiAnalysis">
          <div class="analysis-header">
            <div class="ai-badge">
              <span class="ai-icon">✨</span>
              <span>AI分析</span>
            </div>
            <button @click="showThinking = !showThinking" class="toggle-btn">
              {{ showThinking ? '收起' : '展开' }}
            </button>
          </div>

          <div class="analysis-content" v-show="!showThinking">
            <div class="analysis-text" v-html="formatText(aiAnalysis)"></div>
          </div>

          <div class="thinking-process" v-show="showThinking" v-if="thinkingProcess">
            <div class="thinking-title">💭 思考过程</div>
            <div class="thinking-text">{{ thinkingProcess }}</div>
          </div>
        </div>

        <!-- 车型卡片网格 -->
        <div class="cars-grid" :class="viewMode">
          <div
            v-for="(car, index) in displayCars"
            :key="index"
            class="car-card"
            :style="{ animationDelay: `${index * 0.1}s` }"
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

        <!-- 加载更多 -->
        <div class="load-more" v-if="hasMore">
          <button @click="loadMore" class="load-more-btn">
            加载更多车型
          </button>
        </div>
      </div>
    </section>

    <!-- 加载状态 -->
    <div class="loading-overlay" v-if="isLoading">
      <div class="loading-spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
      </div>
      <div class="loading-text">正在为您查询最合适的车型...</div>
    </div>

    <!-- 深色模式切换 -->
    <button class="theme-toggle" @click="toggleTheme">
      <span v-if="isDark">☀️</span>
      <span v-else>🌙</span>
    </button>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { sendChatMessage } from '@/utils/api'

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
    const sessionId = ref(`session_${Date.now()}`)

    const quickTags = [
      { id: 1, label: '10-20万新能源', query: '推荐10-20万新能源车' },
      { id: 2, label: '比亚迪SUV', query: '比亚迪有哪些SUV' },
      { id: 3, label: '纯电轿车', query: '推荐纯电动轿车' },
      { id: 4, label: '混动车型', query: '有哪些混动车型' },
    ]

    const hasResults = computed(() => displayCars.value.length > 0 || aiAnalysis.value)
    const hasMore = ref(false)

    const formatText = (text) => {
      return text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
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

    const handleSearch = async () => {
      if (!searchQuery.value.trim() || isLoading.value) return

      currentQuery.value = searchQuery.value
      isLoading.value = true
      aiAnalysis.value = ''
      thinkingProcess.value = ''
      displayCars.value = []

      try {
        await sendChatMessage(
          searchQuery.value,
          sessionId.value,
          (chunk) => {
            if (chunk.type === 'reasoning_content') {
              thinkingProcess.value += chunk.content
            } else if (chunk.type === 'content') {
              aiAnalysis.value += chunk.content
            }
          }
        )

        // 模拟提取车型数据（实际应该从AI响应中解析）
        displayCars.value = [
          { name: '比亚迪海豹', energy: '纯电动', level: '中型车', price: '18.98-28.68万', badge: '热门' },
          { name: '特斯拉Model 3', energy: '纯电动', level: '中型车', price: '25.99-33.99万', badge: '推荐' },
          { name: '问界M5', energy: '增程式', level: 'SUV', price: '24.98-31.98万' },
        ]

      } catch (error) {
        console.error('搜索失败:', error)
        aiAnalysis.value = '抱歉，查询出错了，请稍后重试。'
      } finally {
        isLoading.value = false
      }
    }

    const loadMore = () => {
      // TODO: 加载更多逻辑
    }

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
      hasMore,
      formatText,
      toggleTheme,
      toggleView,
      quickFilter,
      handleSearch,
      loadMore
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

.hero-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}

.button-icon {
  font-size: 1.5rem;
  transition: transform 0.3s;
}

.hero-button:hover .button-icon {
  transform: translateX(4px);
}

.quick-filters {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  animation: fadeInUp 0.8s ease-out 0.6s both;
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

.filter-tag:hover {
  background: rgba(255,255,255,0.25);
  transform: translateY(-2px);
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
  padding: 4rem 0;
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

.query-label {
  color: #888;
  margin-right: 0.5rem;
}

.query-text {
  font-weight: 600;
  color: #667eea;
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
}

.toggle-btn:hover {
  background: rgba(255,255,255,0.3);
}

.analysis-content {
  line-height: 1.8;
  font-size: 1.05rem;
}

.thinking-process {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(0,0,0,0.2);
  border-radius: 12px;
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

/* 加载状态 */
.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.8);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.loading-spinner {
  position: relative;
  width: 100px;
  height: 100px;
}

.spinner-ring {
  position: absolute;
  inset: 0;
  border: 4px solid transparent;
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1.5s cubic-bezier(0.5, 0, 0.5, 1) infinite;
}

.spinner-ring:nth-child(1) {
  animation-delay: -0.45s;
}

.spinner-ring:nth-child(2) {
  animation-delay: -0.3s;
}

.spinner-ring:nth-child(3) {
  animation-delay: -0.15s;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 2rem;
  color: white;
  font-size: 1.1rem;
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

.load-more {
  text-align: center;
  padding: 2rem 0;
}

.load-more-btn {
  padding: 1rem 3rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.load-more-btn:hover {
  background: #5568d3;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
}
</style>
