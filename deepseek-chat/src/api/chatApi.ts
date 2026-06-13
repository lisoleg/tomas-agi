/**
 * 聊天会话 API 调用模块（使用统一客户端）
 * 替代 sessionStore.ts 中的 localStorage 调用
 */

import { apiGet, apiPost, apiDelete } from './apiClient'

export interface ChatSession {
  sessionId: string
  title: string
  messages: any[]
  createdAt: number
  updatedAt: number
}

export async function fetchSessions(): Promise<ChatSession[]> {
  const data = await apiGet<{ success: boolean; data: ChatSession[] }>('/sessions')
  return data.success ? data.data : []
}

export async function saveSessions(sessions: ChatSession[]): Promise<boolean> {
  const data = await apiPost<{ success: boolean }>('/sessions', sessions)
  return data.success
}

export async function deleteSession(sessionId: string): Promise<boolean> {
  const data = await apiDelete<{ success: boolean }>(`/sessions/${sessionId}`)
  return data.success
}

export async function fetchApiKey(): Promise<string> {
  const data = await apiGet<{ success: boolean; data: string }>('/apikey')
  return data.success ? data.data : ''
}

export async function saveApiKey(apiKey: string): Promise<boolean> {
  const data = await apiPost<{ success: boolean }>('/apikey', { apiKey })
  return data.success
}
