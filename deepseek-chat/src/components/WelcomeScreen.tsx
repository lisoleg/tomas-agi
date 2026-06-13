// 空状态欢迎页：无消息时展示
import { IconChat, IconSparkles } from './icons'
import type { ChatEMLState } from '../types'

interface WelcomeScreenProps {
  hasApiKey: boolean
  onOpenApiKey: () => void
  onSuggest: (text: string) => void
  /** 切换到蒸馏模式 */
  onSwitchToDistill?: () => void
  /** EML 状态 */
  emlState?: ChatEMLState
}

const SUGGESTIONS: Array<{ title: string; prompt: string; icon?: string }> = [
  {
    title: '解释概念',
    prompt: '请用通俗易懂的语言解释一下「Transformer 架构」的核心思想。'
  },
  {
    title: '写代码',
    prompt: '帮我写一个 Python 函数，输入一个字符串列表，返回去重后按字母排序的结果。'
  },
  {
    title: '翻译润色',
    prompt: '请把下面这段中文翻译成地道的英文：今天天气真好，我想去公园散步。'
  },
  {
    title: '头脑风暴',
    prompt: '请帮我头脑风暴 5 个面向大学生的轻量级副业项目，要求启动成本低、可远程。'
  }
]

/** EML 路由示例（加载知识库后显示，演示翻译官/作家分流） */
const EML_SUGGESTIONS: Array<{ title: string; prompt: string; mode: 'translator' | 'creative'; desc: string }> = [
  {
    title: '概念定义',
    mode: 'translator',
    desc: 'EML 图谱精确命中 → 翻译官模板回复',
    prompt: '牛顿第二定律是什么'
  },
  {
    title: '关系查询',
    mode: 'translator',
    desc: '匹配 EML 中已有关系 → 本地推理',
    prompt: '力和加速度之间有什么关系'
  },
  {
    title: '知识关联',
    mode: 'translator',
    desc: '搜索子图概念 → 翻译官拼接知识',
    prompt: '深度学习与Transformer有什么联系'
  },
  {
    title: '推测未来',
    mode: 'creative',
    desc: 'EML 置信度低 → DeepSeek 作家 + 图谱上下文',
    prompt: '物理学未来50年可能有哪些重大突破'
  },
  {
    title: '开放思辨',
    mode: 'creative',
    desc: '无匹配概念 → 全量走 DeepSeek LLM',
    prompt: '如果AI拥有了真正的意识，社会会发生什么变化'
  },
  {
    title: '跨域联想',
    mode: 'creative',
    desc: '混合检索 → φ-Gate 防幻觉监管',
    prompt: '量子力学原理是否能解释生物进化的某些现象'
  }
]

export function WelcomeScreen({ hasApiKey, onOpenApiKey, onSuggest, onSwitchToDistill, emlState }: WelcomeScreenProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-10 text-center">
      <div className="w-14 h-14 rounded-2xl bg-accent/20 flex items-center justify-center mb-5">
        <IconSparkles size={28} className="text-accent" />
      </div>
      <h1 className="text-2xl md:text-3xl font-semibold mb-2">
        太极AGI
      </h1>
      <p className="text-textSecondary text-sm md:text-base max-w-md mb-4">
        基于 DeepSeek 大模型的对话助手，支持流式输出、Markdown 渲染与知识图谱蒸馏。
      </p>

      {/* EML 加载状态 */}
      {emlState?.loaded && (
        <div className="mb-4 inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-green-600/10 border border-green-600/20 text-sm">
          <span className="inline-flex items-center gap-1 text-green-400">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            🔗 EML 路由已激活
          </span>
          <span className="text-textSecondary/70 text-xs">
            {emlState.fileName} · V={emlState.vertexCount} E={emlState.edgeCount}
          </span>
        </div>
      )}

      {!hasApiKey && (
        <button
          onClick={onOpenApiKey}
          className="mb-8 px-4 py-2 rounded-md bg-accent hover:bg-accentHover text-white text-sm font-medium"
        >
          先配置 API Key 以开始对话
        </button>
      )}

      {/* 推荐提示词 / EML 路由示例 */}
      <div className="w-full max-w-3xl space-y-3">
        {emlState?.loaded ? (
          <>
            {/* EML 路由示例：翻译官 + 作家 分组 */}
            <div className="text-xs text-textSecondary/60 font-medium text-left">🔗 EML 路由示例 — 点击发送，观察分流：</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {EML_SUGGESTIONS.map((s) => (
                <button
                  key={s.title}
                  onClick={() => onSuggest(s.prompt)}
                  className={`text-left p-4 rounded-lg border transition-all group ${
                    s.mode === 'translator'
                      ? 'border-blue-600/20 hover:border-blue-400/40 hover:bg-blue-600/5'
                      : 'border-purple-600/20 hover:border-purple-400/40 hover:bg-purple-600/5'
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <span className="text-xs px-1.5 py-0.5 rounded-full font-medium border"
                      style={s.mode === 'translator'
                        ? { color: '#93c5fd', backgroundColor: 'rgba(37,99,235,0.15)', borderColor: 'rgba(37,99,235,0.3)' }
                        : { color: '#c4b5fd', backgroundColor: 'rgba(124,58,237,0.15)', borderColor: 'rgba(124,58,237,0.3)' }
                      }
                    >
                      {s.mode === 'translator' ? '📖 翻译官' : '✍️ 作家'}
                    </span>
                    <span className="text-sm font-medium text-textPrimary">{s.title}</span>
                  </div>
                  <div className="text-xs text-textSecondary line-clamp-2 mb-1">{s.prompt}</div>
                  <div className="text-[11px] text-textSecondary/40">{s.desc}</div>
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            {/* 通用提示词（无 EML 时） */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-textSecondary/60 font-medium">🌐 直连 LLM 示例：</span>
              <span className="text-[11px] text-textSecondary/40">
                提示：加载 EML 知识库可启用 📖翻译官 + ✍️作家 智能分流
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.title}
                  onClick={() => onSuggest(s.prompt)}
                  className="text-left p-4 rounded-lg border border-white/10 hover:bg-white/5 transition-colors group"
                >
                  <div className="flex items-center gap-2 text-sm font-medium mb-1 text-textPrimary">
                    <IconChat size={14} className="opacity-70" />
                    {s.title}
                  </div>
                  <div className="text-xs text-textSecondary line-clamp-2 group-hover:text-gray-300">
                    {s.prompt}
                  </div>
                </button>
              ))}
              {/* 蒸馏模式入口卡片 */}
              <button
                onClick={() => onSwitchToDistill?.()}
                className="text-left p-4 rounded-lg border border-accent/30 bg-accent/5 hover:bg-accent/10 transition-colors group"
              >
                <div className="flex items-center gap-2 text-sm font-medium mb-1 text-accent">
                  <span>🔬</span>
                  知识蒸馏
                </div>
                <div className="text-xs text-textSecondary line-clamp-2 group-hover:text-gray-300">
                  将文本压缩为 EML 知识图谱（概念 + 关系 + 𝕀(X) 存在度）
                </div>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
