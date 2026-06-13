# 聊天模式 EML 路由 UI 改进

## 修复内容

### 1. 滚动条可见性修复
- `index.css`: WebKit 滚动条从 0.08 提升到 0.18 不透明度，hover 0.35，active 0.45
- 新增 Firefox `scrollbar-width: thin` + `scrollbar-color` 支持
- `MessageList.tsx`: 新增 `min-h-0` 确保 flex 子元素可溢出

### 2. EML/LLM 模式指示器
- **ChatArea**: 消息区和输入框之间新增模式状态栏：
  - 🔗 EML 路由（绿脉冲灯）→ 显示文件名/V/E 统计 + "卸载 EML" 按钮
  - 🌐 直连 LLM（灰灯）→ 显示"纯 DeepSeek 对话"
- **ChatInput**: 动态 placeholder，EML 加载时显示 "EML 路由已激活…"
- **WelcomeScreen**: EML 加载时显示绿色激活横幅
- **App.tsx**: 顶部模式标签 `💬 聊天模式` / `💬 聊天模式 + EML`

## 修改文件
- `src/index.css` — 滚动条 CSS 增强
- `src/components/MessageList.tsx` — min-h-0
- `src/components/ChatArea.tsx` — 模式状态栏 + 动态 placeholder
- `src/components/WelcomeScreen.tsx` — EML 状态横幅
- `src/components/ChatInput.tsx` — 已有 placeholder prop，无需改动

## 验证
- TypeScript 编译零报错
- Vite 前端正常运行于 http://localhost:5173
