// 语料持久化存储 —— 现在使用后端 API（替代 localStorage）
// 使用缓存机制保持同步接口兼容

export interface CorpusEntry {
  /** 自增 ID */
  id: number
  /** 完整原始文本 */
  text: string
  /** 来源域标签（物理 / 化学 / AI/ML / 医学 / 蒸馏 等） */
  domain: string
  /** 蒸馏出的概念数 */
  conceptsCount: number
  /** 蒸馏出的关系数 */
  relationsCount: number
  /** 导入时间戳（毫秒） */
  createdAt: number
}

// 缓存
let cachedEntries: CorpusEntry[] = []
let cacheLoaded = false
let loading = false
let loadPromise: Promise<void> | null = null

const API_BASE = 'http://localhost:5000/api'

// 加载缓存
async function ensureLoaded() {
  if (cacheLoaded || loading) return
  loading = true
  if (!loadPromise) {
    loadPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/corpus`)
        const data = await res.json()
        cachedEntries = data.success ? data.data : []
        cacheLoaded = true
      } catch {
        cachedEntries = []
        cacheLoaded = true
      } finally {
        loading = false
      }
    })()
  }
  await loadPromise
}

// 读取全部语料条目，按时间倒序（最新在前）
export function getAllCorpusEntries(): CorpusEntry[] {
  // 同步返回缓存（如果已加载）
  if (cacheLoaded) {
    return [...cachedEntries].sort((a, b) => b.createdAt - a.createdAt)
  }
  // 未加载时返回空数组，并触发后台加载
  ensureLoaded()
  return []
}

// 追加一条语料
export async function saveCorpusEntry(entry: Omit<CorpusEntry, 'id' | 'createdAt'>): Promise<CorpusEntry[]> {
  await ensureLoaded()
  try {
    const res = await fetch(`${API_BASE}/corpus`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entry)
    })
    const data = await res.json()
    if (data.success) {
      // 重新加载
      cacheLoaded = false
      await ensureLoaded()
    }
  } catch (e) {
    console.error('保存语料失败', e)
  }
  return getAllCorpusEntries()
}

// 删除指定语料
export async function deleteCorpusEntry(id: number): Promise<CorpusEntry[]> {
  await ensureLoaded()
  try {
    await fetch(`${API_BASE}/corpus/${id}`, { method: 'DELETE' })
    // 重新加载
    cacheLoaded = false
    await ensureLoaded()
  } catch (e) {
    console.error('删除语料失败', e)
  }
  return getAllCorpusEntries()
}

// 语料总数
export function getCorpusCount(): number {
  return getAllCorpusEntries().length
}

// 清空语料库
export async function clearCorpusEntries(): Promise<void> {
  await ensureLoaded()
  for (const entry of cachedEntries) {
    try {
      await fetch(`${API_BASE}/corpus/${entry.id}`, { method: 'DELETE' })
    } catch {}
  }
  cacheLoaded = false
  cachedEntries = []
}

// ===================== 冲突决策存储 =====================

export interface ConflictDecision {
  conflictId: string
  conceptName: string
  domain: string
  decision: 'keep_old' | 'keep_new' | 'merge' | 'ignore'
  resolvedAt: number
}

let cachedDecisions: ConflictDecision[] = []
let decisionsLoaded = false

async function ensureDecisionsLoaded() {
  if (decisionsLoaded) return
  try {
    const res = await fetch(`${API_BASE}/conflicts`)
    const data = await res.json()
    cachedDecisions = data.success ? data.data : []
    decisionsLoaded = true
  } catch {
    cachedDecisions = []
    decisionsLoaded = true
  }
}

export function getConflictDecisions(): ConflictDecision[] {
  if (decisionsLoaded) return cachedDecisions
  ensureDecisionsLoaded()
  return []
}

export async function saveConflictDecision(decision: ConflictDecision): Promise<void> {
  await ensureDecisionsLoaded()
  try {
    await fetch(`${API_BASE}/conflicts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision)
    })
    // 重新加载
    decisionsLoaded = false
    await ensureDecisionsLoaded()
  } catch (e) {
    console.error('保存冲突决策失败', e)
  }
}

export async function clearConflictDecisions(): Promise<void> {
  // 后端暂不支持批量删除，先留空
  cachedDecisions = []
  decisionsLoaded = true
}
