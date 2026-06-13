// 会话持久化层：现在使用后端 API（替代 localStorage）
import type { ChatSession } from '../types'

const API_BASE = 'http://localhost:5000/api'

// 缓存
let cachedSessions: ChatSession[] = []
let sessionsLoaded = false
let cachedApiKey = ''
let apiKeyLoaded = false

// 加载会话
async function ensureSessionsLoaded() {
  if (sessionsLoaded) return
  try {
    const res = await fetch(`${API_BASE}/sessions`)
    const data = await res.json()
    cachedSessions = data.success ? data.data : []
    sessionsLoaded = true
  } catch {
    cachedSessions = []
    sessionsLoaded = true
  }
}

// 加载 API Key
async function ensureApiKeyLoaded() {
  if (apiKeyLoaded) return
  try {
    const res = await fetch(`${API_BASE}/apikey`)
    const data = await res.json()
    cachedApiKey = data.success ? data.data : ''
    apiKeyLoaded = true
  } catch {
    cachedApiKey = ''
    apiKeyLoaded = true
  }
}

/** 读取全部会话 */
export async function loadSessions(): Promise<ChatSession[]> {
  await ensureSessionsLoaded()
  return cachedSessions
}

/** 保存全部会话 */
export async function saveSessions(sessions: ChatSession[]): Promise<void> {
  try {
    await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sessions)
    })
    // 更新缓存
    cachedSessions = sessions
  } catch (e) {
    console.error('保存会话失败', e)
  }
}

/** 读取 API Key */
export async function loadApiKey(): Promise<string> {
  await ensureApiKeyLoaded()
  if (cachedApiKey && cachedApiKey.trim() !== '') return cachedApiKey
  // 回退：从 Vite 环境变量读取
  const envKey = import.meta.env.VITE_DEEPSEEK_API_KEY
  if (envKey && envKey.trim() !== '') return envKey
  return ''
}

/** 保存 API Key */
export async function saveApiKey(apiKey: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/apikey`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKey })
    })
    cachedApiKey = apiKey
  } catch (e) {
    console.error('保存 API Key 失败', e)
  }
}

/** 清空所有会话 */
export async function clearAllSessions(): Promise<void> {
  for (const session of cachedSessions) {
    try {
      await fetch(`${API_BASE}/sessions/${session.id}`, { method: 'DELETE' })
    } catch {}
  }
  cachedSessions = []
  sessionsLoaded = true
}
