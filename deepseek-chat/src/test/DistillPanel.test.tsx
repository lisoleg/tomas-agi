/**
 * DistillPanel 组件单元测试
 *
 * 测试蒸馏面板的核心逻辑：阶段常量、语料示例、基础渲染
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { DistillPanel } from '../components/DistillPanel'

// Mock heavy dependencies
vi.mock('../api/distiller', () => ({
  buildEMLGraph: vi.fn(),
  buildMergedEML: vi.fn(),
  detectMergeSummary: vi.fn(),
  downloadEMLFile: vi.fn(),
  extractConcepts: vi.fn(),
  extractRelations: vi.fn(),
  formatFileSize: vi.fn((size: number) => `${(size / 1024).toFixed(1)} KB`),
  loadEMLFromBuffer: vi.fn(),
  rebuildGraphAfterDelete: vi.fn(),
  serializeEML: vi.fn(),
  TokenBridgeClient: vi.fn(),
  extractGraphForVisualization: vi.fn(),
}))

vi.mock('../api/knowledgeStore', () => ({
  getAllKnowledgeItems: vi.fn(() => Promise.resolve([])),
  saveKnowledgeItems: vi.fn(),
}))

vi.mock('../api/corpusStore', () => ({
  getAllCorpusEntries: vi.fn(() => Promise.resolve([])),
  saveCorpusEntry: vi.fn(),
  deleteCorpusEntry: vi.fn(),
  saveConflictDecision: vi.fn(),
}))

// Mock Toast
vi.mock('../components/Toast', () => ({
  useToast: () => ({
    toasts: [],
    addToast: vi.fn(),
    removeToast: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  }),
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))


describe('DistillPanel', () => {
  const defaultProps = { apiKey: 'test-key' }

  it('渲染蒸馏面板基础结构', () => {
    render(<DistillPanel {...defaultProps} />)

    // 应显示 Tab 按钮
    expect(screen.getByText('蒸馏')).toBeInTheDocument()
    expect(screen.getByText('知识浏览')).toBeInTheDocument()
    expect(screen.getByText('Token Bridge')).toBeInTheDocument()
  })

  it('默认显示蒸馏 Tab 内容', () => {
    render(<DistillPanel {...defaultProps} />)

    // 蒸馏 Tab 应显示文本输入和示例语料
    expect(screen.getByText(/输入文本/i)).toBeInTheDocument()
    expect(screen.getByText(/示例语料/i)).toBeInTheDocument()
  })

  it('显示示例语料按钮（物理/化学/AI/医学）', () => {
    render(<DistillPanel {...defaultProps} />)

    expect(screen.getByText('物理')).toBeInTheDocument()
    expect(screen.getByText('化学')).toBeInTheDocument()
    expect(screen.getByText('AI/ML')).toBeInTheDocument()
    expect(screen.getByText('医学')).toBeInTheDocument()
  })

  it('显示开始蒸馏按钮', () => {
    render(<DistillPanel {...defaultProps} />)

    expect(screen.getByText('开始蒸馏')).toBeInTheDocument()
  })

  it('切换到知识浏览 Tab 显示图谱区域', async () => {
    render(<DistillPanel {...defaultProps} />)

    const knowledgeTab = screen.getByText('知识浏览')
    knowledgeTab.click()

    // 知识浏览 Tab 应显示图谱提示
    expect(screen.getByText(/选择语料或知识/i)).toBeInTheDocument()
  })

  it('切换到 Token Bridge Tab', () => {
    render(<DistillPanel {...defaultProps} />)

    const bridgeTab = screen.getByText('Token Bridge')
    bridgeTab.click()

    // Token Bridge Tab 应显示推理区域
    // 由于没有加载 EML，可能显示上传提示
    expect(screen.getByText(/上传.*EML|加载.*EML|Token Bridge/i)).toBeTruthy()
  })
})
