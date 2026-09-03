<template>
  <div class="app-container">
    <!-- Skip link -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <!-- 顶部导航 - 极简设计 -->
    <header class="header" role="banner">
      <div class="container">
        <div class="header-content">
          <div class="logo">
            <span class="logo-text">CAR HELPER</span>
          </div>
          <nav class="nav" role="navigation" aria-label="Main navigation">
            <a href="#" class="nav-link" aria-current="page">Search</a>
            <a href="#" class="nav-link">Compare</a>
            <a href="#" class="nav-link">About</a>
          </nav>
          <div class="header-meta">
            <span class="meta-count">40,912 cars</span>
          </div>
        </div>
      </div>
    </header>

    <!-- 主要内容 -->
    <main class="main" id="main-content" role="main">
      <ChatView />
    </main>
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
  min-height: 100vh;
  background: var(--color-background);
}

/* Header */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: var(--color-background);
  border-bottom: 1px solid var(--color-border);
  z-index: 100;
}

.container {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 0 var(--space-md);
}

.header-content {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-lg);
  height: 64px;
}

.logo {
  display: flex;
  align-items: center;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--color-foreground);
}

.nav {
  display: flex;
  gap: var(--space-md);
  justify-content: center;
}

.nav-link {
  font-size: 14px;
  font-weight: 400;
  color: var(--color-muted-foreground);
  text-decoration: none;
  padding: var(--space-xs) 0;
  border-bottom: 2px solid transparent;
  transition: all var(--duration) var(--easing);
}

.nav-link:hover {
  color: var(--color-foreground);
}

.nav-link[aria-current="page"] {
  color: var(--color-foreground);
  border-bottom-color: var(--color-foreground);
}

.nav-link:active {
  transform: translateY(1px);
}

.header-meta {
  text-align: right;
}

.meta-count {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-foreground);
}

.main {
  padding-top: 64px;
}

/* 响应式 */
@media (max-width: 768px) {
  .header-content {
    grid-template-columns: 1fr;
    height: auto;
    padding: var(--space-sm) 0;
    gap: var(--space-sm);
  }

  .nav {
    justify-content: flex-start;
  }

  .header-meta {
    text-align: left;
  }
}
</style>
