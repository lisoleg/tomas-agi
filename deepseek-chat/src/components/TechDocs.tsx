// 技术文档页：展示 TOMAS / 太极OS 项目全貌
// 类似首页风格的文档浏览体验
import { useState } from 'react'

/** 文档章节 */
interface DocSection {
  id: string
  title: string
  icon: string
  color: string
  content: React.ReactNode
}

const SECTIONS: DocSection[] = [
  {
    id: 'overview',
    title: '项目概览',
    icon: '🌐',
    color: 'from-cyan-600/20 to-blue-700/20',
    content: (
      <div className="space-y-5">
        <div>
          <h3 className="text-lg font-bold text-cyan-300 mb-2">TOMAS-AGI · 太极OS</h3>
          <p className="text-sm text-textSecondary leading-relaxed">
            基于非结合谱图代数（NASGA）的通用人工智能系统。从纯软件仿真到内核模块、忆阻器硬件加速，
            打通从理论到物理实现的完整路径。核心创新在于用八元数（Octonion）Moufang 乘法构建非结合推理引擎，
            用 EML 谱图（Existence-Mapped Laplacian）实现知识表示与 I(X) 守恒。
          </p>
        </div>

        {/* 核心指标卡片 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'V3 架构', value: '翻译官 + 作家', color: 'border-cyan-500/25 bg-cyan-900/10' },
            { label: '知识表示', value: 'EML 谱图', color: 'border-purple-500/25 bg-purple-900/10' },
            { label: '代数基础', value: '八元数 NASGA', color: 'border-amber-500/25 bg-amber-900/10' },
            { label: '治理框架', value: '双环正义', color: 'border-emerald-500/25 bg-emerald-900/10' },
          ].map((item) => (
            <div key={item.label} className={`rounded-lg border p-3 text-center ${item.color}`}>
              <div className="text-xs text-textSecondary/60 mb-1">{item.label}</div>
              <div className="text-sm font-semibold text-textPrimary">{item.value}</div>
            </div>
          ))}
        </div>

        {/* 用户故事 */}
        <div className="bg-white/[0.03] rounded-xl p-4">
          <h4 className="text-sm font-semibold text-textPrimary mb-3">📖 适用场景</h4>
          <div className="space-y-2">
            {[
              { role: 'AGI 研究者', desc: '运行 A6-BS 基准测试，验证 NASGA 理论正确性，量化 ξ_c 效能指标' },
              { role: '应用开发者', desc: '通过 Token Bridge API 将自然语言转为 NASGA 符号，调用非结合推理能力' },
              { role: '安全审计员', desc: '查看双环正义日志（MNQ 校验 + STA 审计），确认认知与行为可控' },
              { role: '知识工程师', desc: '将领域文本蒸馏为 EML 知识图谱，构建专业领域的结构化知识库' },
            ].map((s) => (
              <div key={s.role} className="flex gap-3 items-start text-xs sm:text-sm">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center text-[11px] font-medium text-accent mt-0.5">
                  {s.role[0]}
                </span>
                <div>
                  <span className="font-medium text-textPrimary">{s.role}</span>
                  <span className="text-textSecondary ml-1.5">{s.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  },
  {
    id: 'architecture',
    title: '系统架构',
    icon: '🏗️',
    color: 'from-violet-600/20 to-purple-700/20',
    content: (
      <div className="space-y-5">
        <div>
          <h3 className="text-lg font-bold text-violet-300 mb-2">V3 混合架构：翻译官 + 作家</h3>
          <p className="text-sm text-textSecondary leading-relaxed">
            TOMAS V3 采用双引擎混合架构。用户提问后，系统先计算 EML 图谱匹配置信度：
            高置信度走翻译官路径（精确检索 + 模板组织），低置信度走作家路径（DeepSeek LLM 创造性回答 + EML 上下文辅助）。
          </p>
        </div>

        {/* 路由决策流程 */}
        <div className="bg-white/[0.03] rounded-xl p-5 overflow-x-auto">
          <h4 className="text-sm font-semibold text-textPrimary mb-4">🔄 推理路由流程</h4>
          <div className="min-w-[520px]">
            <svg viewBox="0 0 560 200" className="w-full h-auto" xmlns="http://www.w3.org/2000/svg">
              {/* 用户输入 */}
              <rect x="20" y="75" width="90" height="50" rx="8" fill="rgba(34,211,238,0.15)" stroke="rgba(34,211,238,0.4)" strokeWidth="1.5"/>
              <text x="65" y="104" textAnchor="middle" fill="#e2e8f0" fontSize="12" fontWeight="600">用户提问</text>
              
              {/* 箭头 → EML 检索 */}
              <line x1="110" y1="100" x2="145" y2="100" stroke="#22d3ee" strokeWidth="1.5" markerEnd="url(#arrowCyan)"/>
              
              {/* EML 图谱检索 */}
              <rect x="145" y="70" width="100" height="60" rx="8" fill="rgba(168,85,247,0.15)" stroke="rgba(168,85,247,0.4)" strokeWidth="1.5"/>
              <text x="195" y="95" textAnchor="middle" fill="#c4b5fd" fontSize="11" fontWeight="600">EML 图谱检索</text>
              <text x="195" y="115" textAnchor="middle" fill="#94a3b8" fontSize="10">φ 编码 → 概念匹配</text>

              {/* 箭头 → 置信度判断 */}
              <line x1="245" y1="100" x2="280" y2="100" stroke="#a855f7" strokeWidth="1.5" markerEnd="url(#arrowPurple)"/>

              {/* 置信度判断菱形 */}
              <polygon points="330,65 370,100 330,135 290,100" fill="rgba(245,158,11,0.15)" stroke="rgba(245,158,11,0.5)" strokeWidth="1.5"/>
              <text x="330" y="96" textAnchor="middle" fill="#fbbf24" fontSize="10" fontWeight="600">置信度</text>
              <text x="330" y="110" textAnchor="middle" fill="#94a3b8" fontSize="9">≥ 0.5 ?</text>

              {/* ≥ 0.5 → 翻译官 */}
              <line x1="370" y1="100" x2="405" y2="100" stroke="#22c55e" strokeWidth="1.5" markerEnd="url(#arrowGreen)"/>
              <text x="385" y="92" fill="#22c55e" fontSize="9" fontWeight="600">是</text>
              <rect x="405" y="70" width="80" height="60" rx="8" fill="rgba(34,197,94,0.15)" stroke="rgba(34,197,94,0.4)" strokeWidth="1.5"/>
              <text x="445" y="95" textAnchor="middle" fill="#86efac" fontSize="11" fontWeight="600">📖 翻译官</text>
              <text x="445" y="112" textAnchor="middle" fill="#94a3b8" fontSize="9">精确回答</text>
              <text x="445" y="124" textAnchor="middle" fill="#94a3b8" fontSize="9">LSTM/模板</text>

              {/* < 0.5 → 作家 */}
              <line x1="330" y1="135" x2="330" y2="165" stroke="#ef4444" strokeWidth="1.5"/>
              <line x1="330" y1="165" x2="445" y2="165" stroke="#ef4444" strokeWidth="1.5"/>
              <line x1="445" y1="165" x2="445" y2="135" stroke="#ef4444" strokeWidth="1.5" markerEnd="url(#arrowRed)"/>
              <text x="338" y="155" fill="#ef4444" fontSize="9" fontWeight="600">否</text>
              <rect x="405" y="140" width="80" height="50" rx="8" fill="rgba(239,68,68,0.12)" stroke="rgba(239,68,68,0.35)" strokeWidth="1.5"/>
              <text x="445" y="162" textAnchor="middle" fill="#fca5a5" fontSize="11" fontWeight="600">✍️ 作家</text>
              <text x="445" y="178" textAnchor="middle" fill="#94a3b8" fontSize="9">LLM + EML</text>

              {/* 箭头定义 */}
              <defs>
                <marker id="arrowCyan" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#22d3ee"/></marker>
                <marker id="arrowPurple" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#a855f7"/></marker>
                <marker id="arrowGreen" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#22c55e"/></marker>
                <marker id="arrowRed" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#ef4444"/></marker>
              </defs>
            </svg>
          </div>
        </div>

        {/* 双引擎对比 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="rounded-xl border border-green-600/20 bg-green-900/5 p-4">
            <h4 className="text-sm font-bold text-green-300 mb-2 flex items-center gap-1.5">
              📖 翻译官 (Translator)
            </h4>
            <ul className="text-xs text-textSecondary space-y-1.5">
              <li>• 触发条件：置信度 ≥ 0.5</li>
              <li>• 数据源：EML 知识图谱精确匹配</li>
              <li>• 回答方式：模板填充 + LSTM 补全</li>
              <li>• 特点：事实准确、可追溯来源</li>
              <li>• 典型场景：概念定义、关系查询</li>
            </ul>
          </div>
          <div className="rounded-xl border border-red-600/20 bg-red-900/5 p-4">
            <h4 className="text-sm font-bold text-red-300 mb-2 flex items-center gap-1.5">
              ✍️ 作家 (Creative)
            </h4>
            <ul className="text-xs text-textSecondary space-y-1.5">
              <li>• 触发条件：置信度 &lt; 0.5</li>
              <li>• 数据源：DeepSeek LLM + EML 上下文</li>
              <li>• 回答方式：创造性生成（带 φ-Gate 监管）</li>
              <li>• 特点：灵活开放、支持跨域联想</li>
              <li>• 典型场景：推测未来、开放思辨</li>
            </ul>
          </div>
        </div>
      </div>
    )
  },
  {
    id: 'eml',
    title: 'EML 知识图谱',
    icon: '🕸️',
    color: 'from-purple-600/20 to-pink-700/20',
    content: (
      <div className="space-y-5">
        <div>
          <h3 className="text-lg font-bold text-purple-300 mb-2">EML — Existence-Mapped Laplacian</h3>
          <p className="text-sm text-textSecondary leading-relaxed">
            EML 是 TOMAS 的核心数据结构。每个概念是图中的一个顶点，携带八元数场向量和 δ（信息存在度 Delta）；
            关系是有权边，携带结合子标志。EML 的设计哲学是<strong className="text-amber-300">容纳冲突而非覆盖</strong>——新旧知识冲突时不自动删除，
            由用户逐条决定处理方式。
          </p>
        </div>

        {/* 核心概念 */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { symbol: 'δ (Delta)', name: '信息存在度', desc: '量化概念在当前知识域中的确定性，范围 [0,1]。值越高说明该概念越"真实"。', unit: '𝕀(X)' },
            { symbol: 'Octonion', name: '八元数场向量', desc: '每个顶点关联一个 8 维八元数编码语义方向，用于余弦相似度计算和子图搜索。', unit: 'ℝ⁸' },
            { symbol: 'Associator', name: '结合子标志', desc: '边的特殊标记，标识该关系是否为非结合关系（即 A·B≠B·A 的关键连接）。', unit: '{0,1}' },
          ].map((item) => (
            <div key={item.symbol} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <div className="text-base font-mono font-bold text-amber-300 mb-1">{item.symbol}</div>
              <div className="text-xs font-semibold text-textPrimary mb-1.5">{item.name} <span className="text-textSecondary/40 ml-1">{item.unit}</span></div>
              <div className="text-[11px] text-textSecondary leading-relaxed">{item.desc}</div>
            </div>
          ))}
        </div>

        {/* 冲突哲学 */}
        <div className="rounded-xl border border-amber-600/20 bg-amber-900/5 p-4">
          <h4 className="text-sm font-semibold text-amber-300 mb-2">⚖️ EML 冲突哲学</h4>
          <div className="text-xs text-textSecondary space-y-2 leading-relaxed">
            <p><strong className="text-textPrimary">核心原则：</strong>EML 容纳冲突，不自动覆盖旧知识。</p>
            <p>当新蒸馏的知识与已有知识存在重叠时，系统检测冲突并展示对比视图，提供四种决策：</p>
            <div className="flex flex-wrap gap-2 mt-2">
              {[
                { emoji: '📌', text: '保留旧的', hint: '新知识冗余，以旧为准' },
                { emoji: '🆕', text: '保留新的', hint: '新知识更准确完整' },
                { emoji: '🔀', text: '合并两者', hint: '新旧互补，都保留' },
                { emoji: '👁️', text: '忽略', hint: '误报，无需处理' },
              ].map((d) => (
                <span key={d.text} className="px-2.5 py-1 rounded-md bg-black/20 border border-white/10 text-[11px]">
                  {d.emoji} <strong>{d.text}</strong>
                  <span className="text-textSecondary/50 ml-1">{d.hint}</span>
                </span>
              ))}
            </div>
            <p className="mt-2 text-amber-400/60">所有决策持久化到本地存储，即使刷新页面也不丢失。</p>
          </div>
        </div>

        {/* 蒸馏流水线 */}
        <div className="bg-white/[0.03] rounded-xl p-4">
          <h4 className="text-sm font-semibold text-textPrimary mb-3">🔬 文本蒸馏流水线</h4>
          <div className="flex items-center justify-between gap-2 text-[11px] sm:text-xs overflow-x-auto pb-1">
            {[
              { step: '原始文本', icon: '📄' },
              { step: 'LLM 提取概念', icon: '🧠' },
              { step: '提取关系', icon: '🔗' },
              { step: '计算 𝕀(X)', icon: '📊' },
              { step: '生成 .eml 二进制', icon: '💾' },
            ].map((s, i) => (
              <div key={i} className="flex items-center gap-2 flex-shrink-0">
                <div className="px-3 py-2 rounded-lg bg-purple-600/10 border border-purple-600/20 whitespace-nowrap">
                  <span className="mr-1">{s.icon}</span>
                  {s.step}
                </div>
                {i < 4 && <span className="text-textSecondary/30">→</span>}
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  },
  {
    id: 'governance',
    title: '双环正义治理',
    icon: '⚖️',
    color: 'from-emerald-600/20 to-teal-700/20',
    content: (
      <div className="space-y-5">
        <div>
          <h3 className="text-lg font-bold text-emerald-300 mb-2">认知环 + 行为环 — 双层安全保障</h3>
          <p className="text-sm text-textSecondary leading-relaxed">
            TOMAS 通过「双环正义」体系确保 AI 系统的可审计性和安全性。
            认知环负责 I(X) 信息守恒校验（Lean MNQ 形式化证明），行为环负责防止主观倾向漂移（CI Gate + STA 审计）。
          </p>
        </div>

        {/* 双环图示 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="rounded-xl border border-cyan-600/20 bg-cyan-900/5 p-4">
            <h4 className="text-sm font-bold text-cyan-300 mb-3 flex items-center gap-1.5">
              🧠 认知环 (Cognitive Loop)
            </h4>
            <ul className="text-xs text-textSecondary space-y-2">
              <li><strong className="text-cyan-300">I-守恒：</strong>信息存在度总量守恒，不凭空产生也不无故消失</li>
              <li><strong className="text-cyan-300">MNQ 校验：</strong>Lean 形式化证明，确保推理步骤符合代数公理</li>
              <li><strong className="text-cyan-300">认知函子映射：</strong>验证从问题空间到答案空间的变换保持结构一致</li>
              <li><strong className="text-cyan-300">可回滚快照：</strong>Continuation 思维态保存/恢复，延迟 &lt;10ms</li>
            </ul>
          </div>
          <div className="rounded-xl border border-orange-600/20 bg-orange-900/5 p-4">
            <h4 className="text-sm font-bold text-orange-300 mb-3 flex items-center gap-1.5">
              🛡️ 行为环 (Behavioral Loop)
            </h4>
            <ul className="text-xs text-textSecondary space-y-2">
              <li><strong className="text-orange-300">Φ-Gate 门控：</strong>余弦相似度阈值过滤，防止幻觉输出</li>
              <li><strong className="text-orange-300">CI Gate 副作用守恒：</strong>TXN Port 操作全部经权限校验</li>
              <li><strong className="text-orange-300">STA 倾向审计：</strong>KL 散度超阈值触发 κ 重置</li>
              <li><strong className="text-orange-300">κ-调节器：</strong>κ=7 稳态锁定，响应时间 &lt;1ms</li>
            </ul>
          </div>
        </div>

        {/* 安全机制示意 */}
        <div className="bg-white/[0.03] rounded-xl p-4">
          <h4 className="text-sm font-semibold text-textPrimary mb-3">🛡️ φ-Gate 语义门控</h4>
          <p className="text-xs text-textSecondary mb-3">
            作家模式输出前经过 φ-Gate 过滤。将 LLM 生成的回复编码为八元数向量，与 EML 子图做余弦相似度计算：
            超过阈值的片段放行（可信），低于阈值的片段标记或拦截（潜在幻觉）。这是 TOMAS 防止 LLM 幻觉的核心防线。
          </p>
          <div className="flex items-center gap-3 text-xs">
            <span className="px-3 py-1.5 rounded-lg bg-green-600/10 border border-green-600/20 text-green-300">✅ 相似度高 → 放行</span>
            <span className="px-3 py-1.5 rounded-lg bg-yellow-600/10 border border-yellow-600/20 text-yellow-300">⚠️ 中等 → 标记提示</span>
            <span className="px-3 py-1.5 rounded-lg bg-red-600/10 border border-red-600/20 text-red-300">❌ 过低 → 拦截重试</span>
          </div>
        </div>
      </div>
    )
  },
  {
    id: 'tech-stack',
    title: '技术栈',
    icon: '⚙️',
    color: 'from-slate-600/20 to-gray-700/20',
    content: (
      <div className="space-y-5">
        <div>
          <h3 className="text-lg font-bold text-gray-300 mb-2">分层技术栈</h3>
          <p className="text-sm text-textSecondary leading-relaxed">
            从理论层到物理层的完整技术栈。当前前端实现了 Token Bridge 桥接层和 EML 可视化，
            后端 Python 实现了蒸馏引擎和推理引擎。
          </p>
        </div>

        {/* 分层展示 */}
        {[
          {
            layer: '应用层',
            color: 'border-cyan-600/25 bg-cyan-900/5',
            items: [
              { name: 'deepseek-chat/', desc: 'React + TypeScript + Vite 前端界面', lang: 'TSX/Tailwind' },
              { name: 'Token Bridge Client', desc: '前端桥接组件（distiller.ts）', lang: 'TypeScript' },
            ]
          },
          {
            layer: '推理层',
            color: 'border-purple-600/25 bg-purple-900/5',
            items: [
              { name: 'token_bridge.py', desc: 'Python 推理入口，翻译官/作家路由', lang: 'Python' },
              { name: 'token_generator.py', desc: 'LSTM PhiToTokenDecoder + 模板生成', lang: 'Python' },
              { name: 'llm_distiller.py', desc: '文本→概念+关系→EML二进制蒸馏器', lang: 'Python' },
            ]
          },
          {
            layer: '理论层',
            color: 'border-amber-600/25 bg-amber-900/5',
            items: [
              { name: 'NASGA', desc: '非结合谱图代数（八元数 Moufang 乘法）', lang: 'Math' },
              { name: 'EML Format', desc: 'Existence-Mapped Laplacian 二进制格式', lang: 'Binary' },
              { name: 'Φ-Gate', desc: '八元数编码相似度门控', lang: 'Algorithm' },
            ]
          },
          {
            layer: '硬件层（远景）',
            color: 'border-emerald-600/25 bg-emerald-900/5',
            items: [
              { name: 'T-Processor 内核模块', desc: 'Linux tproc_core.ko + USCS 4KB 谱页文件系统', lang: 'C/Kernel' },
              { name: '忆阻器阵列驱动', desc: '电导映射 EML 边权重', lang: 'C/Driver' },
              { name: 'FPGA RTL', desc: 'moufang_alu.v + eml_graph_ctrl.v', lang: 'Verilog' },
            ]
          },
        ].map((section) => (
          <div key={section.layer} className={`rounded-xl border ${section.color} p-4`}>
            <h4 className="text-xs font-bold uppercase tracking-wider text-textSecondary/60 mb-2.5">{section.layer}</h4>
            <div className="space-y-2">
              {section.items.map((item) => (
                <div key={item.name} className="flex items-start gap-3 text-xs sm:text-sm group">
                  <code className="flex-shrink-0 px-1.5 py-0.5 rounded bg-black/30 font-mono text-cyan-300 text-[11px] mt-0.5">{item.name}</code>
                  <span className="text-textSecondary group-hover:text-textPrimary transition-colors">{item.desc}</span>
                  <span className="flex-shrink-0 px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-textSecondary/40 hidden sm:inline-block">{item.lang}</span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* 当前文件清单 */}
        <div className="bg-white/[0.02] rounded-xl p-4 border border-white/5">
          <h4 className="text-xs font-semibold text-textSecondary/60 mb-2.5">📁 关键文件索引</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-[11px] font-mono">
            {[
              ['tomas_agi/sim/token_bridge.py', '推理引擎入口'],
              ['tomas_agi/sim/token_generator.py', '模板/LSTM 生成'],
              ['tomas_agi/sim/llm_distiller.py', 'EML 蒸馏器'],
              ['deepseek-chat/src/App.tsx', '前端根组件'],
              ['deepseek-chat/src/hooks/useChat.ts', '聊天状态管理'],
              ['deepseek-chat/src/components/DistillPanel.tsx', '蒸馏面板'],
              ['deepseek-chat/src/api/distiller.ts', 'EML 加载/合并/可视化'],
              ['deepseek-chat/src/components/EMLGraphVisualization.tsx', 'D3.js 力导向图'],
            ].map(([file, desc]) => (
              <div key={file} className="flex gap-2">
                <code className="text-cyan-400/70 truncate">{file}</code>
                <span className="text-textSecondary/40 flex-shrink-0">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }
]

export function TechDocs() {
  const [activeSection, setActiveSection] = useState<string>(SECTIONS[0].id)
  const current = SECTIONS.find(s => s.id === activeSection) ?? SECTIONS[0]

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* 页面头部横幅 */}
      <div className="flex-shrink-0 px-6 py-8 text-center relative overflow-hidden">
        {/* 背景装饰 */}
        <div className="absolute inset-0 opacity-30 pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse at 50% 30%, rgba(139,92,246,0.15), transparent 70%), radial-gradient(ellipse at 80% 70%, rgba(34,211,238,0.08), transparent 50%)'
          }}
        />
        <div className="relative">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-600/30 to-cyan-600/30 border border-white/10 mb-4 shadow-lg shadow-violet-900/20">
            <span className="text-3xl">☯️</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-violet-300 via-cyan-300 to-emerald-300 bg-clip-text text-transparent">
            TOMAS-AGI · 太极OS
          </h1>
          <p className="text-sm text-textSecondary mt-2 max-w-lg mx-auto">
            基于非结合谱图代数的通用人工智能系统<br />
            <span className="text-textSecondary/50 text-xs">Existence-Mapped Laplacian Knowledge Graph + Dual-Loop Governance</span>
          </p>
        </div>
      </div>

      {/* 主内容区：左侧导航 + 右侧内容 */}
      <div className="flex-1 flex min-h-0 px-4 pb-4 gap-4 overflow-hidden">
        {/* 左侧章节导航 */}
        <nav className="hidden md:flex flex-col w-48 flex-shrink-0 gap-1 overflow-y-auto pr-2">
          {SECTIONS.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={[
                'text-left px-3 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2.5 group',
                activeSection === section.id
                  ? 'bg-accent/15 text-accent border border-accent/20 shadow-sm'
                  : 'text-textSecondary hover:text-textPrimary hover:bg-white/5 border border-transparent'
              ].join(' ')}
            >
              <span className="text-base">{section.icon}</span>
              {section.title}
            </button>
          ))}
        </nav>

        {/* 右侧内容区域 */}
        <main className="flex-1 overflow-y-auto rounded-xl border border-white/5 bg-white/[0.02] backdrop-blur-sm">
          {/* 移动端 tab 栏 */}
          <div className="md:hidden sticky top-0 z-10 flex gap-1 p-3 bg-chatBg/95 backdrop-blur border-b border-white/5 overflow-x-auto">
            {SECTIONS.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={[
                  'flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
                  activeSection === section.id
                    ? 'bg-accent/20 text-accent'
                    : 'text-textSecondary/70 hover:text-textPrimary'
                ].join(' ')}
              >
                {section.icon} {section.title}
              </button>
            ))}
          </div>

          {/* 内容 */}
          <div className="p-5 sm:p-6 lg:p-8">
            {/* 章节标题 */}
            <div className={`mb-6 inline-flex items-center gap-2.5 px-4 py-2 rounded-xl bg-gradient-to-r ${current.color} border border-white/5`}>
              <span className="text-lg">{current.icon}</span>
              <h2 className="text-base font-bold text-textPrimary">{current.title}</h2>
            </div>

            {/* 章节内容 */}
            <div className="max-w-3xl">
              {current.content}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
