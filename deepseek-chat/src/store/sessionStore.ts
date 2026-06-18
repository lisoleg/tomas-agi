// 会话持久化层：后端 API 优先，localStorage 作为降级/离线方案
import type { ChatSession } from '../types'

const API_BASE = 'http://localhost:5000/api'
const LS_KEY = 'tomas_chat_sessions'

// ---- localStorage 读写 ----
function loadFromLocalStorage(): ChatSession[] {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch { /* 忽略解析错误 */ }
  return []
}

function saveToLocalStorage(sessions: ChatSession[]): boolean {
  try {
    // 只保留最近 10 个会话，避免 5MB 超限
    const trimmed = sessions
      .sort((a, b) => (b.updatedAt || b.createdAt) - (a.updatedAt || a.createdAt))
      .slice(0, 10)
    localStorage.setItem(LS_KEY, JSON.stringify(trimmed))
    return true
  } catch { /* 忽略存储错误 */ }
  return false
}

// ---- 后端 API 调用 ----
async function apiGetSessions(): Promise<ChatSession[] | null> {
  try {
    const res = await fetch(`${API_BASE}/sessions`)
    const data = await res.json()
    if (data.success) return data.data as ChatSession[]
  } catch { /* 忽略网络错误 */ }
  return null
}

async function apiSaveSessions(sessions: ChatSession[]): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sessions),
    })
    const data = await res.json()
    return !!data.success
  } catch { /* 忽略网络错误 */ }
  return false
}

async function apiGetApiKey(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/apikey`)
    const data = await res.json()
    if (data.success) return data.data as string
  } catch { /* 忽略网络错误 */ }
  return null
}

async function apiSaveApiKey(apiKey: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/apikey`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKey }),
    })
    const data = await res.json()
    return !!data.success
  } catch { /* 忽略网络错误 */ }
  return false
}

// ---- 缓存 + 公开 API ----

let cachedSessions: ChatSession[] = []
let sessionsLoaded = false
let cachedApiKey = ''
let apiKeyLoaded = false

/** 读取全部会话：后端优先，失败降级 localStorage */
export async function loadSessions(): Promise<ChatSession[]> {
  if (sessionsLoaded) return cachedSessions

  // 先试后端
  const apiData = await apiGetSessions()
  if (apiData !== null) {
    cachedSessions = apiData
    sessionsLoaded = true
    // 同时备份到 localStorage
    saveToLocalStorage(apiData)
    return apiData
  }

  // 后端不可用 → 降级 localStorage
  const localData = loadFromLocalStorage()
  cachedSessions = localData
  sessionsLoaded = true
  console.log(`[sessionStore] 后端不可用，已降级到 localStorage，加载 ${localData.length} 个会话`)
  return localData
}

/** 保存全部会话：双写（后端 + localStorage） */
export async function saveSessions(sessions: ChatSession[]): Promise<void> {
  // 更新缓存
  cachedSessions = sessions

  // 同时写后端和 localStorage
  const [apiOk] = await Promise.all([
    apiSaveSessions(sessions),
    new Promise<boolean>(resolve => {
      const ok = saveToLocalStorage(sessions)
      resolve(ok)
    }),
  ])

  if (!apiOk) {
    console.warn('[sessionStore] 后端保存失败，数据已保存到 localStorage')
  }
}

/** 读取 API Key：后端优先，失败降级 localStorage / 环境变量 */
export async function loadApiKey(): Promise<string> {
  if (apiKeyLoaded && cachedApiKey) return cachedApiKey

  // 先试后端
  const apiData = await apiGetApiKey()
  if (apiData !== null) {
    cachedApiKey = apiData
    apiKeyLoaded = true
    return apiData
  }

  // 后端不可用 → 降级 localStorage
  try {
    const raw = localStorage.getItem('tomas_api_key')
    if (raw) {
      cachedApiKey = raw
      apiKeyLoaded = true
      return raw
    }
  } catch { /* 忽略本地存储错误 */ }

  // 再降级到 Vite 环境变量
  const envKey = import.meta.env.VITE_DEEPSEEK_API_KEY as string
  if (envKey && envKey.trim() !== '') {
    cachedApiKey = envKey
    apiKeyLoaded = true
    return envKey
  }

  apiKeyLoaded = true
  return ''
}

/** 保存 API Key：双写 */
export async function saveApiKey(apiKey: string): Promise<void> {
  cachedApiKey = apiKey

  // 写后端
  const apiOk = await apiSaveApiKey(apiKey)

  // 同时写 localStorage
  try {
    localStorage.setItem('tomas_api_key', apiKey)
  } catch { /* 忽略本地存储错误 */ }

  if (!apiOk) {
    console.warn('[sessionStore] 后端保存 API Key 失败，已保存到 localStorage')
  }
}

/** 清空所有会话 */
export async function clearAllSessions(): Promise<void> {
  // 后端删除
  for (const session of cachedSessions) {
    try {
      await fetch(`${API_BASE}/sessions/${session.id}`, { method: 'DELETE' })
    } catch { /* 忽略删除错误 */ }
  }
  // localStorage 也清空
  try { localStorage.removeItem(LS_KEY) } catch { /* 忽略清空错误 */ }
  cachedSessions = []
  sessionsLoaded = true
}
