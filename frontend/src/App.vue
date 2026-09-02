<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="navbar">
      <div class="nav-content">
        <div class="logo-section">
          <div class="logo">Car Helper</div>
          <div class="slogan">找车，就这么简单</div>
        </div>
        <nav class="nav-links">
          <a href="#" class="nav-link active">选车</a>
          <a href="#" class="nav-link">对比</a>
          <a href="#" class="nav-link">资讯</a>
        </nav>
      </div>
    </header>

    <!-- 主体内容 -->
    <main class="main-content">
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
  width: 100%;
  min-height: 100vh;
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
}

.navbar {
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 70px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo {
  font-size: 1.8rem;
  font-weight: 700;
  color: #2c3e50;
  letter-spacing: -0.5px;
}

.slogan {
  color: #7f8c8d;
  font-size: 0.9rem;
  padding-left: 1rem;
  border-left: 2px solid #e0e0e0;
}

.nav-links {
  display: flex;
  gap: 2rem;
}

.nav-link {
  color: #555;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: all 0.2s;
}

.nav-link:hover {
  background: #f0f0f0;
  color: #2c3e50;
}

.nav-link.active {
  background: #3498db;
  color: white;
}

.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}
</style>
