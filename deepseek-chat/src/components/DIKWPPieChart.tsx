// DIKWP 层分布饼图 — SVG 实现
// 展示 D(Data)/I(Info)/K(Knowledge)/W(Wisdom)/P(Purpose) 五层 ℐ-密度分布
import React from 'react'

export interface DIKWPLayerInfo {
  layer: string       // "D" | "I" | "K" | "W" | "P"
  name: string        // 中文名
  count: number       // 边/概念数
  percentage: number  // 百分比
}

interface DIKWPPieChartProps {
  data: DIKWPLayerInfo[]
  totalEdges: number
  ontologyName?: string
  className?: string
}

// 层颜色映射 (与 TOMAS ℐ-bin 对应)
const LAYER_COLORS: Record<string, string> = {
  D: '#f59e0b',  // amber — 裸数据
  I: '#06b6d4',  // cyan  — 信息激活
  K: '#8b5cf6',  // violet— 知识稳定
  W: '#ec4899',  // pink  — 智慧跨域
  P: '#10b981',  // emerald— 目的锚点
}

const LAYER_NAMES: Record<string, string> = {
  D: '数据 Data',
  I: '信息 Info',
  K: '知识 Knowledge',
  W: '智慧 Wisdom',
  P: '目的 Purpose',
}

const LAYER_SHORT: Record<string, string> = {
  D: 'D', I: 'I', K: 'K', W: 'W', P: 'P',
}

export function DIKWPPieChart({ data, totalEdges, ontologyName, className }: DIKWPPieChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className={`border border-white/10 rounded-lg p-4 text-center ${className}`}>
        <div className="text-xs text-textSecondary">暂无 DIKWP 分布数据</div>
      </div>
    )
  }

  const size = 200
  const cx = size / 2
  const cy = size / 2
  const radius = 75
  const labelRadius = radius + 18

  // 计算饼图弧段
  let startAngle = -Math.PI / 2 // 从顶部开始
  const arcs: { layer: string; startAngle: number; endAngle: number; pct: number }[] = []

  for (const item of data) {
    const pct = item.percentage / 100
    if (pct === 0) continue
    const angle = pct * 2 * Math.PI
    arcs.push({
      layer: item.layer,
      startAngle,
      endAngle: startAngle + angle,
      pct,
    })
    startAngle += angle
  }

  // SVG 弧段路径
  function arcPath(start: number, end: number, r: number): string {
    const x1 = cx + r * Math.cos(start)
    const y1 = cy + r * Math.sin(start)
    const x2 = cx + r * Math.cos(end)
    const y2 = cy + r * Math.sin(end)
    const largeArc = end - start > Math.PI ? 1 : 0
    return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`
  }

  // 标签定位 (在外侧)
  function labelPos(start: number, end: number, r: number) {
    const mid = (start + end) / 2
    return {
      x: cx + r * Math.cos(mid),
      y: cy + r * Math.sin(mid),
    }
  }

  // 触发动画的工具: 每个弧段弹出 5px
  const [hoveredLayer, setHoveredLayer] = React.useState<string | null>(null)

  // 过滤掉占比 0% 的层
  const activeData = data.filter(d => d.count > 0)
  const activeArcs = arcs.filter((_a, i) => activeData[i] && activeData[i].count > 0)

  return (
    <div className={`border border-white/10 rounded-lg overflow-hidden ${className}`}>
      {/* 标题栏 */}
      <div className="px-3 py-2 bg-violet-600/10 text-sm font-medium border-b border-white/10 flex items-center gap-2">
        <span>📊</span>
        <span>DIKWP 层分布</span>
        {ontologyName && (
          <span className="text-xs text-textSecondary/60 ml-auto">{ontologyName}</span>
        )}
      </div>

      <div className="p-3">
        <div className="flex flex-col sm:flex-row items-center gap-4">
          {/* SVG 饼图 */}
          <svg
            viewBox={`0 0 ${size} ${size}`}
            width={size}
            height={size}
            className="shrink-0"
          >
            {/* 弧段 */}
            {activeArcs.map((arc, i) => {
              const layer = arc.layer
              const isHovered = hoveredLayer === layer
              const r = isHovered ? radius + 4 : radius
              const path = arcPath(arc.startAngle, arc.endAngle, r)
              const color = LAYER_COLORS[layer] || '#666'
              const mid = labelPos(arc.startAngle, arc.endAngle, labelRadius)
              const shortLabel = LAYER_SHORT[layer] || layer

              return (
                <g key={layer}>
                  <path
                    d={path}
                    fill={color}
                    opacity={isHovered ? 1 : 0.85}
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth={1}
                    onMouseEnter={() => setHoveredLayer(layer)}
                    onMouseLeave={() => setHoveredLayer(null)}
                    style={{ transition: 'opacity 0.2s, d 0.15s', cursor: 'pointer' }}
                  />
                  {/* 层标签 (外侧) */}
                  <text
                    x={mid.x}
                    y={mid.y}
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="text-xs font-bold"
                    fill={color}
                    style={{ fontSize: '11px', pointerEvents: 'none' }}
                  >
                    {shortLabel}
                  </text>
                </g>
              )
            })}
            {/* 中心文字 */}
            <text
              x={cx}
              y={cy - 8}
              textAnchor="middle"
              className="text-xs"
              fill="rgba(255,255,255,0.5)"
            >
              {totalEdges}
            </text>
            <text
              x={cx}
              y={cy + 8}
              textAnchor="middle"
              className="text-xs"
              fill="rgba(255,255,255,0.3)"
            >
              ℐ-edges
            </text>
          </svg>

          {/* 图例 + 数值 */}
          <div className="flex-1 space-y-1.5 min-w-0">
            {activeData.map((item) => {
              const color = LAYER_COLORS[item.layer] || '#666'
              const name = item.name || LAYER_NAMES[item.layer] || item.layer
              const isHovered = hoveredLayer === item.layer
              return (
                <div
                  key={item.layer}
                  className={`flex items-center gap-2 px-2 py-1 rounded transition-colors ${
                    isHovered ? 'bg-white/5' : ''
                  }`}
                  onMouseEnter={() => setHoveredLayer(item.layer)}
                  onMouseLeave={() => setHoveredLayer(null)}
                  style={{ cursor: 'default' }}
                >
                  {/* 颜色块 */}
                  <div
                    className="w-3 h-3 rounded-sm shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  {/* 名称 */}
                  <span className="text-xs text-textPrimary min-w-0 truncate">{name}</span>
                  {/* 数值 */}
                  <span className="text-xs text-textSecondary/60 ml-auto shrink-0">
                    {item.count} 条
                  </span>
                  {/* 百分比 */}
                  <span className="text-xs font-mono shrink-0 w-10 text-right"
                    style={{ color }}
                  >
                    {item.percentage}%
                  </span>
                </div>
              )
            })}
            {/* 空层提示 */}
            {data.filter(d => d.count === 0).length > 0 && (
              <div className="text-xs text-textSecondary/30 pt-1 border-t border-white/5">
                空: {data.filter(d => d.count === 0).map(d => LAYER_SHORT[d.layer] || d.layer).join(' ')}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DIKWPPieChart
