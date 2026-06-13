// 知识持久化存储 —— 现在使用后端 API（替代 localStorage）

export interface KnowledgeItem {
  /** 自增 ID */
  id: number
  /** 类型：概念或关系 */
  type: 'concept' | 'relation'
  /** 显示标签（概念名 / "源→目标"） */
  label: string
  /** 补充信息（概念：φ值，关系：关系类型） */
  extra: string
  /** 创建时间戳（毫秒） */
  createdAt: number
  /** 来源域名（物理/化学/AI/医学/蒸馏等） */
  domain: string
}

const API_BASE = 'http://localhost:5000/api'

// 缓存
let cachedItems: KnowledgeItem[] = []
let cacheLoaded = false

async function ensureLoaded() {
  if (cacheLoaded) return
  try {
    const res = await fetch(`${API_BASE}/knowledge`)
    const data = await res.json()
    cachedItems = data.success ? data.data : []
    cacheLoaded = true
  } catch {
    cachedItems = []
    cacheLoaded = true
  }
}

/** 读取全部知识条目，按时间倒序 */
export async function getAllKnowledgeItems(): Promise<KnowledgeItem[]> {
  await ensureLoaded()
  return [...cachedItems].sort((a, b) => b.createdAt - a.createdAt)
}

/** 批量追加知识条目 */
export async function saveKnowledgeItems(items: Omit<KnowledgeItem, 'id' | 'createdAt'>[]): Promise<KnowledgeItem[]> {
  await ensureLoaded()
  const now = Date.now()
  for (const item of items) {
    try {
      await fetch(`${API_BASE}/knowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...item,
          createdAt: now
        })
      })
    } catch (e) {
      console.error('保存知识条目失败', e)
    }
  }
  // 重新加载
  cacheLoaded = false
  await ensureLoaded()
  return getAllKnowledgeItems()
}

/** 清空知识库 */
export async function clearKnowledgeItems(): Promise<void> {
  await ensureLoaded()
  for (const item of cachedItems) {
    try {
      await fetch(`${API_BASE}/knowledge/${item.id}`, { method: 'DELETE' })
    } catch {}
  }
  cachedItems = []
  cacheLoaded = true
}

/** 知识总数 */
export function getKnowledgeCount(): number {
  return cachedItems.length
}
