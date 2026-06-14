// 语料持久化存储 —— 后端 API 优先，localStorage 兜底
// 后端不可用时自动降级到 localStorage（key: tomas_corpus_entries）

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

const LS_KEY = 'tomas_corpus_entries'

/** 从 localStorage 读取语料条目 */
function loadFromLS(): CorpusEntry[] {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

/** 写入 localStorage */
function saveToLS(entries: CorpusEntry[]): void {
  try { localStorage.setItem(LS_KEY, JSON.stringify(entries)) } catch {}
}

// 缓存
let cachedEntries: CorpusEntry[] = []
let cacheLoaded = false
let loading = false
let loadPromise: Promise<void> | null = null

const API_BASE = 'http://localhost:5000/api'

// 加载缓存 —— 后端优先，失败则降级 localStorage
async function ensureLoaded() {
  if (cacheLoaded) return
  loading = true
  if (!loadPromise) {
    loadPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/corpus`, { signal: AbortSignal.timeout(3000) })
        const data = await res.json()
        cachedEntries = data.success ? data.data : []
      } catch {
        // 后端不可用 → 降级到 localStorage
        cachedEntries = loadFromLS()
        console.log('[corpusStore] 后端不可用，已降级到 localStorage (' + LS_KEY + ')')
      } finally {
        cacheLoaded = true
        loading = false
      }
    })()
  }
  await loadPromise
}

// 读取全部语料条目，按时间倒序（最新在前）
// 注意：首次调用需要等待后端 API 加载完成
export async function getAllCorpusEntries(): Promise<CorpusEntry[]> {
  await ensureLoaded()
  return [...cachedEntries].sort((a, b) => b.createdAt - a.createdAt)
}

// 追加一条语料 —— 后端优先，失败则 localStorage 兜底
export async function saveCorpusEntry(entry: Omit<CorpusEntry, 'id' | 'createdAt'>): Promise<CorpusEntry[]> {
  await ensureLoaded()
  let saved = false
  try {
    const res = await fetch(`${API_BASE}/corpus`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entry),
      signal: AbortSignal.timeout(3000),
    })
    const data = await res.json()
    if (data.success) {
      cacheLoaded = false
      await ensureLoaded()
      saved = true
    }
  } catch (e) {
    console.warn('[corpusStore] 后端保存失败，降级到 localStorage:', e)
  }
  // 后端失败时写入 localStorage
  if (!saved) {
    const newEntry: CorpusEntry = {
      ...entry,
      id: Date.now(), // 用时间戳作为临时 ID
      createdAt: Date.now(),
    }
    cachedEntries = [newEntry, ...cachedEntries]
    saveToLS(cachedEntries)
  }
  return getAllCorpusEntries()
}

// 删除指定语料 —— 后端优先，失败则 localStorage 兜底
export async function deleteCorpusEntry(id: number): Promise<CorpusEntry[]> {
  await ensureLoaded()
  try {
    await fetch(`${API_BASE}/corpus/${id}`, { method: 'DELETE', signal: AbortSignal.timeout(3000) })
    cacheLoaded = false
    await ensureLoaded()
  } catch {
    // 后端不可用 → 从 localStorage 删除
    cachedEntries = cachedEntries.filter(e => e.id !== id)
    saveToLS(cachedEntries)
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
  try {
    for (const entry of cachedEntries) {
      await fetch(`${API_BASE}/corpus/${entry.id}`, { method: 'DELETE', signal: AbortSignal.timeout(2000) })
    }
    cacheLoaded = false
    cachedEntries = []
  } catch {
    // 后端不可用 → 清空 localStorage
    cachedEntries = []
    saveToLS([])
  }
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
