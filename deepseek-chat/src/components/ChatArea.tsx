// 聊天主区域：顶部标题栏 + 中间消息区 + 底部输入区
import { useRef } from 'react'
import type { ChatEMLState, ChatSession } from '../types'
import { ChatInput } from './ChatInput'
import { MessageList } from './MessageList'
import { WelcomeScreen } from './WelcomeScreen'
import { IconFile, IconMenu, IconRefresh, IconSparkles } from './icons'

interface ChatAreaProps {
  currentSession: ChatSession | null
  isLoading: boolean
  hasApiKey: boolean
  onSend: (text: string) => void
  onAbort: () => void
  onClear: () => void
  onOpenApiKey: () => void
  onToggleSidebar: () => void
  /** 切换到蒸馏模式 */
  onSwitchToDistill?: () => void
  /** EML 状态 */
  emlState?: ChatEMLState
  /** 加载 EML 文件 */
  onLoadEML?: (file: File, conceptsFile?: File) => void
  /** 清除 EML */
  onClearEML?: () => void
  /** 对 EML 路由回复不满意，直连 LLM 重试 */
  onRetryDirect?: (messageId: string) => void
  /** 用户反馈 */
  onFeedback?: (messageId: string, feedback: 'like' | 'dislike' | null) => void
}

export function ChatArea(props: ChatAreaProps) {
  const {
    currentSession,
    isLoading,
    hasApiKey,
    onSend,
    onAbort,
    onClear,
    onOpenApiKey,
    onToggleSidebar,
    onSwitchToDistill,
    emlState,
    onLoadEML,
    onClearEML,
    onRetryDirect,
    onFeedback
  } = props

  const emlInputRef = useRef<HTMLInputElement>(null)

  // 当消息列表变化时强制让 MessageList 区域滚到底部（由 MessageList 自行处理）
  const hasMessages = (currentSession?.messages.length ?? 0) > 0
  const title = currentSession?.title ?? '新对话'

  // EML 加载处理
  const handleEMLChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !onLoadEML) return
    onLoadEML(file)
    // 重置 file input 以便同一文件可再次选择
    e.target.value = ''
  }

  // 移动端：消息发送后自动收起侧边栏
  // 该逻辑由 Sidebar onCloseMobile 处理

  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-chatBg">
      {/* 顶部标题栏 */}
      <header className="h-14 flex items-center justify-between px-3 md:px-4 border-b border-white/5 bg-chatBg/95 backdrop-blur sticky top-0 z-10">
        <div className="flex items-center gap-2 min-w-0">
          {/* 移动端菜单按钮 */}
          <button
            onClick={onToggleSidebar}
            className="md:hidden p-2 rounded hover:bg-white/10"
            aria-label="打开侧边栏"
          >
            <IconMenu size={18} />
          </button>
          <div className="w-7 h-7 rounded-md bg-accent/20 flex items-center justify-center flex-shrink-0">
            <IconSparkles size={14} className="text-accent" />
          </div>
          <h1 className="text-sm md:text-base font-semibold truncate">{title}</h1>
        </div>
        <div className="flex items-center gap-1">
          {/* EML 状态指示器 */}
          {emlState?.loaded && (
            <span
              className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-md border border-accent/30 bg-accent/10 text-accent"
              title={`${emlState.fileName} · V=${emlState.vertexCount} E=${emlState.edgeCount} · 𝕀̄=${emlState.avgDelta.toFixed(3)}`}
            >
              🔗 {emlState.fileName.length > 12 ? emlState.fileName.slice(0, 12) + '…' : emlState.fileName}
              <button
                onClick={(e) => { e.stopPropagation(); onClearEML?.() }}
                className="ml-1 w-4 h-4 rounded-full hover:bg-red-500/30 flex items-center justify-center text-[10px]"
                title="清除 EML"
              >
                ×
              </button>
            </span>
          )}
          {/* 加载 EML 按钮 */}
          <label className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-md hover:bg-white/10 transition-colors cursor-pointer"
            title={emlState?.loaded ? '更换 EML 知识库' : '加载 EML 知识库到聊天'}
          >
            <IconFile size={12} />
            <span>{emlState?.loaded ? '换库' : 'EML'}</span>
            <input
              ref={emlInputRef}
              type="file"
              accept=".eml"
              onChange={handleEMLChange}
              className="hidden"
            />
          </label>
          {hasMessages && (
            <button
              onClick={() => {
                if (window.confirm('确定清空当前会话的全部消息？')) {
                  onClear()
                }
              }}
              className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-md hover:bg-white/10"
              title="清空当前会话"
            >
              <IconRefresh size={14} />
              <span>清空</span>
            </button>
          )}
        </div>
      </header>

      {/* 中间内容区 */}
      {hasMessages ? (
        <MessageList messages={currentSession?.messages ?? []} onRetryDirect={onRetryDirect} onFeedback={onFeedback} />
      ) : (
        <WelcomeScreen
          hasApiKey={hasApiKey}
          onOpenApiKey={onOpenApiKey}
          onSuggest={(text) => onSend(text)}
          onSwitchToDistill={onSwitchToDistill}
          emlState={emlState}
        />
      )}

      {/* 模式状态横幅（醒目指示当前路由模式） */}
      {emlState?.loaded ? (
        <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 text-sm bg-gradient-to-r from-green-900/40 via-green-800/25 to-chatBg border-t border-green-600/25">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-500/20 border border-green-400/30 text-green-300 font-semibold text-sm">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse shadow-[0_0_6px_rgba(74,222,128,0.6)]" />
              🔗 EML 路由
            </span>
            <span className="text-green-300/80 font-medium">
              {emlState.fileName.length > 20
                ? emlState.fileName.slice(0, 20) + '…'
                : emlState.fileName}
            </span>
            <span className="text-green-400/50 text-xs font-mono">
              V={emlState.vertexCount} · E={emlState.edgeCount}
            </span>
            <span className="text-green-300/60 text-xs hidden sm:inline">
              知识检索→LLM 组织自然语言 · 低置信→作家创作
            </span>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onClearEML?.() }}
            className="px-3 py-1 rounded text-xs text-red-300/80 hover:text-red-200 hover:bg-red-600/20 border border-red-500/20 hover:border-red-500/40 transition-all"
            title="卸载 EML 知识库，切换到纯 LLM 直连模式"
          >
            卸载 EML
          </button>
        </div>
      ) : (
        <div className="flex-shrink-0 flex items-center justify-center gap-3 px-4 py-2 text-sm bg-gradient-to-r from-amber-900/25 via-amber-800/15 to-chatBg border-t border-amber-600/20">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-400/25 text-amber-300 font-semibold text-sm">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            🌐 直连 LLM
          </span>
          <span className="text-amber-300/60 text-xs hidden sm:inline">
            纯 DeepSeek 对话，不经过知识图谱 — 点击顶部 EML 按钮加载知识库
          </span>
        </div>
      )}

      {/* 底部输入区 */}
      <div className="border-t border-white/5 bg-chatBg">
        <ChatInput
          isLoading={isLoading}
          disabled={!hasApiKey}
          placeholder={
            !hasApiKey
              ? '请先在左侧栏配置 API Key'
              : emlState?.loaded
                ? 'EML 路由已激活…（Enter 发送，Shift+Enter 换行）'
                : '发消息给 DeepSeek…（Enter 发送，Shift+Enter 换行）'
          }
          onSend={onSend}
          onAbort={onAbort}
        />
      </div>
    </div>
  )
}
