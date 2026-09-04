# Car Helper Web

Car Helper 的唯一 Web 前端，使用 React、TypeScript、Vite 和 Tailwind CSS。它支持同一会话内的多轮对话、SSE 流式回答、完整历史会话列表，以及本地长期记忆的查看、修改和逐条删除。

## 本地开发

先启动后端，再启动 Vite：

```powershell
E:\Anaconda_envs\envs\langchain_v1\python.exe -m src.api
cd frontend
npm install
npm run dev
```

访问 `http://localhost:3000`。3000 是前端开发服务器，负责热更新；它会把 `/api` 请求代理到本机 7860 端口。

## 生产构建

```powershell
cd frontend
npm run build
```

构建产物写入 `frontend/dist/`。FastAPI 检测到该目录后会在 `http://127.0.0.1:7860` 托管前端。生产模式无需再启动 3000 端口；前后端保持代码和构建职责分离，但部署为同一个本地服务。
