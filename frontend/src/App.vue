<template>
  <div class="app-container">
    <!-- Skip link for keyboard users -->
    <a href="#main-content" class="skip-link">跳转到主要内容</a>

    <!-- 顶部导航栏 - 极简设计 -->
    <header class="navbar" role="banner">
      <div class="nav-content">
        <div class="logo-section">
          <div class="logo">CAR HELPER</div>
          <div class="logo-subtitle">智能选车系统</div>
        </div>
        <nav class="nav-links" role="navigation" aria-label="主导航">
          <a href="#" class="nav-link active" aria-current="page">
            <span class="link-number" aria-hidden="true">01</span>
            <span class="link-text">选车</span>
          </a>
          <a href="#" class="nav-link">
            <span class="link-number" aria-hidden="true">02</span>
            <span class="link-text">对比</span>
          </a>
          <a href="#" class="nav-link">
            <span class="link-number" aria-hidden="true">03</span>
            <span class="link-text">资讯</span>
          </a>
        </nav>
        <div class="nav-stats" aria-label="数据统计">
          <div class="stat-item">
            <div class="stat-value">40.9K</div>
            <div class="stat-label">车型</div>
          </div>
        </div>
      </div>
    </header>

    <!-- 主体内容 -->
    <main class="main-content" id="main-content" role="main">
      <ChatView />
    </main>

    <!-- 装饰性网格背景 -->
    <div class="grid-overlay" aria-hidden="true"></div>
  </div>
</template>

<script>
import ChatView from './views/ChatView.vue'

export default {
  name: 'App',
  components: {
    ChatView
  }
}
</script>

<style scoped>
.app-container {
  position: relative;
  width: 100%;
  min-height: 100vh;
  background: var(--color-primary);
}

/* 装饰性网格背景 */
.grid-overlay {
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(212, 175, 55, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(212, 175, 55, 0.03) 1px, transparent 1px);
  background-size: 100px 100px;
  pointer-events: none;
  z-index: 0;
}

/* 导航栏 */
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: rgba(10, 10, 10, 0.9);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--color-border);
  z-index: 100;
  animation: slideDown 0.6s ease-out;
}

@keyframes slideDown {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.nav-content {
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 3rem;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  height: 80px;
  gap: 3rem;
}

.logo-section {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.logo {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--color-text);
  position: relative;
}

.logo::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 40px;
  height: 2px;
  background: var(--color-accent);
}

.logo-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.nav-links {
  display: flex;
  gap: 2rem;
  justify-content: center;
}

.nav-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  text-decoration: none;
  color: var(--color-text-muted);
  transition: color var(--duration-fast);
  position: relative;
  padding: 0.5rem 0;
}

/* 改进hover和active状态 */
.nav-link:hover {
  color: var(--color-text);
}

.nav-link:active {
  transform: scale(0.98);
}

.link-number {
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
}

.link-text {
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0.05em;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%) scaleX(0);
  width: 100%;
  height: 2px;
  background: var(--color-accent);
  transition: transform var(--duration-normal);
}

.nav-link:hover::after,
.nav-link.active::after {
  transform: translateX(-50%) scaleX(1);
}

.nav-link.active {
  color: var(--color-text);
}

.nav-stats {
  display: flex;
  justify-content: flex-end;
}

.stat-item {
  text-align: right;
}

.stat-value {
  font-family: var(--font-display);
  font-size: 1.5rem;
  color: var(--color-accent);
  line-height: 1;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-top: 0.25rem;
}

.main-content {
  position: relative;
  z-index: 1;
  padding-top: 80px;
}

/* 响应式 */
@media (max-width: 1024px) {
  .nav-content {
    grid-template-columns: auto 1fr;
    padding: 0 2rem;
  }

  .nav-stats {
    display: none;
  }
}

@media (max-width: 768px) {
  .nav-content {
    grid-template-columns: 1fr;
    height: auto;
    padding: 1rem;
  }

  .nav-links {
    display: none;
  }
}
</style>

