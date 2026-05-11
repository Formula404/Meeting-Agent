<template>
  <div class="app-shell">
    <nav class="nav-bar">
      <div class="nav-inner">
        <router-link to="/" class="nav-brand">会议纪要管理</router-link>
        <div class="nav-links">
          <router-link to="/" class="nav-link">上传</router-link>
          <router-link to="/admin" class="nav-link">管理</router-link>
        </div>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
// App shell — nothing more needed
</script>
