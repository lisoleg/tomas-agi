/**
 * 语料 API 调用模块（使用统一客户端）
 * 替代 corpusStore.ts 中的 localStorage 调用
 */

import { apiGet, apiPost, apiDelete } from './apiClient'

export interface CorpusEntry {
  id: number
  text: string
  domain: string
  conceptsCount: number
  relationsCount: number
  createdAt: number
}

export async function fetchCorpusEntries(): Promise<CorpusEntry[]> {
  const data = await apiGet<{ success: boolean; data: CorpusEntry[] }>('/corpus')
  return data.success ? data.data : []
}

export async function addCorpusEntry(entry: Omit<CorpusEntry, 'id' | 'createdAt'>): Promise<number> {
  const data = await apiPost<{ success: boolean; id: number }>('/corpus', entry)
  return data.success ? data.id : -1
}

export async function deleteCorpusEntry(id: number): Promise<boolean> {
  const data = await apiDelete<{ success: boolean }>(`/corpus/${id}`)
  return data.success
}
