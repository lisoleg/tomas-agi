/**
 * EMLGraphVisualization 组件单元测试
 * 
 * 测试 D3.js 力导向知识图谱可视化组件的核心行为
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import React from 'react'
import { EMLGraphVisualization, type EMLGraphData } from '../components/EMLGraphVisualization'

// Mock D3 — 避免 JSDOM 中 D3 SVG 操作的复杂性
vi.mock('d3', () => {
  const mockSelection = {
    attr: vi.fn().mockReturnThis(),
    style: vi.fn().mockReturnThis(),
    text: vi.fn().mockReturnThis(),
    append: vi.fn().mockReturnThis(),
    selectAll: vi.fn().mockReturnThis(),
    data: vi.fn().mockReturnThis(),
    join: vi.fn().mockReturnThis(),
    enter: vi.fn().mockReturnThis(),
    merge: vi.fn().mockReturnThis(),
    call: vi.fn().mockReturnThis(),
    on: vi.fn().mockReturnThis(),
    remove: vi.fn().mockReturnThis(),
    node: vi.fn(() => null),
  }

  const mockForceSimulation = vi.fn(() => ({
    force: vi.fn().mockReturnThis(),
    alphaTarget: vi.fn().mockReturnThis(),
    restart: vi.fn().mockReturnThis(),
    stop: vi.fn().mockReturnThis(),
    on: vi.fn().mockReturnThis(),
    nodes: vi.fn().mockReturnThis(),
    tick: vi.fn(),
  }))

  return {
    __esModule: true,
    default: {
      select: vi.fn(() => mockSelection),
      forceSimulation: mockForceSimulation,
      forceLink: vi.fn(() => ({ id: vi.fn(), distance: vi.fn().mockReturnThis() })),
      forceManyBody: vi.fn(() => ({ strength: vi.fn().mockReturnThis() })),
      forceCollide: vi.fn(() => ({ radius: vi.fn().mockReturnThis() })),
      forceCenter: vi.fn(() => ({})),
      zoom: vi.fn(() => ({ scaleExtent: vi.fn().mockReturnThis(), on: vi.fn().mockReturnThis() })),
      drag: vi.fn(() => ({ on: vi.fn().mockReturnThis() })),
    },
    forceSimulation: mockForceSimulation,
    forceLink: vi.fn(),
    forceManyBody: vi.fn(),
    forceCollide: vi.fn(),
    forceCenter: vi.fn(),
    zoom: vi.fn(),
    drag: vi.fn(),
    select: vi.fn(() => mockSelection),
  }
})

// Mock ResizeObserver (not in JSDOM)
global.ResizeObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// 构造测试数据
function makeGraphData(vertexCount: number, edgeCount: number): EMLGraphData {
  const vertices = Array.from({ length: vertexCount }, (_, i) => ({
    id: i,
    label: `概念_${i}`,
    delta: 0.5 + Math.random() * 0.5,
    info_existence: 0.5 + Math.random() * 0.5,
    corpusName: i < vertexCount / 2 ? '物理' : '化学',
  }))

  const edges = Array.from({ length: edgeCount }, (_, i) => ({
    src: i % vertexCount,
    dst: (i + 1) % vertexCount,
    weight: 0.3 + Math.random() * 0.7,
    associator_flag: i % 4,
  }))

  return { vertices, edges }
}


describe('EMLGraphVisualization', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染空状态提示（graphData=null）', () => {
    render(
      <EMLGraphVisualization
        graphData={null}
        height={400}
      />
    )

    expect(screen.getByText(/选择语料或知识/i)).toBeInTheDocument()
  })

  it('渲染空数据状态（vertices=[]）', () => {
    render(
      <EMLGraphVisualization
        graphData={{ vertices: [], edges: [] }}
        height={400}
        showAllByDefault={true}
      />
    )

    expect(screen.getByText(/没有可显示的图谱数据/i)).toBeInTheDocument()
  })

  it('渲染性能模式标签（节点数 > 500）', () => {
    const bigData = makeGraphData(600, 1000)

    render(
      <EMLGraphVisualization
        graphData={bigData}
        height={400}
        showAllByDefault={true}
      />
    )

    expect(screen.getByText(/性能模式/i)).toBeInTheDocument()
  })

  it('超过1000节点时显示对应提示', () => {
    const hugeData = makeGraphData(1500, 3000)

    render(
      <EMLGraphVisualization
        graphData={hugeData}
        height={400}
        showAllByDefault={true}
      />
    )

    expect(screen.getByText(/性能模式/i)).toBeInTheDocument()
  })

  it('正确显示节点和边计数', () => {
    const data = makeGraphData(10, 15)

    render(
      <EMLGraphVisualization
        graphData={data}
        height={400}
        showAllByDefault={true}
      />
    )

    expect(screen.getByText(/性能模式/)).toBeInTheDocument()
  })

  it('支持搜索框输入', () => {
    const data = makeGraphData(50, 100)

    render(
      <EMLGraphVisualization
        graphData={data}
        height={400}
        showAllByDefault={true}
      />
    )

    const input = screen.getByPlaceholderText(/搜索概念/i)
    expect(input).toBeInTheDocument()

    fireEvent.change(input, { target: { value: '物理' } })
    expect(input).toHaveValue('物理')
  })

  it('边权重阈值滑块存在', () => {
    const data = makeGraphData(50, 100)
    const onThresholdChange = vi.fn()

    render(
      <EMLGraphVisualization
        graphData={data}
        height={400}
        showAllByDefault={true}
        edgeWeightThreshold={0.3}
        onEdgeWeightThresholdChange={onThresholdChange}
      />
    )

    const slider = screen.getByRole('slider')
    expect(slider).toBeInTheDocument()
  })
})
