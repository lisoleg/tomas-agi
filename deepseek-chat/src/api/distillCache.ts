/**
 * DistillPanel 三级缓存模块
 * Level 1: localStorage 缓存（TTL 5分钟，0ms 显示）
 * Level 2: Flask API + retryFetch（3次尝试，指数退避）
 * Level 3: 内置 TOMAS 示例概念（离线兜底）
 */

const CACHE_KEY = 'tomas_distill_cache'
const CACHE_TTL = 5 * 60 * 1000 // 5分钟

export interface CachedGraphData {
  concepts: any[]
  relations: any[]
  stats: {
    conceptCount: number
    relationCount: number
    avgIWeight: number
    dikwpDistribution: Record<string, number>
  }
  timestamp: number
}

/**
 * 保存图谱数据到 localStorage 缓存
 */
export function saveGraphToCache(data: CachedGraphData): void {
  try {
    const cacheItem = {
      ...data,
      timestamp: Date.now()
    }
    localStorage.setItem(CACHE_KEY, JSON.stringify(cacheItem))
    console.log('[DistillCache] Saved to cache:', data.concepts.length, 'concepts,', data.relations.length, 'relations')
  } catch (e) {
    console.warn('[DistillCache] Failed to save to cache:', e)
  }
}

/**
 * 从 localStorage 缓存加载数据
 * 如果缓存过期或不存在，返回 null
 */
export function loadGraphFromCache(): CachedGraphData | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY)
    if (!cached) return null
    
    const cacheItem = JSON.parse(cached)
    const age = Date.now() - cacheItem.timestamp
    
    if (age > CACHE_TTL) {
      console.log('[DistillCache] Cache expired, age:', age, 'ms')
      localStorage.removeItem(CACHE_KEY)
      return null
    }
    
    console.log('[DistillCache] Loaded from cache, age:', age, 'ms')
    return cacheItem
  } catch (e) {
    console.warn('[DistillCache] Failed to load from cache:', e)
    return null
  }
}

/**
 * 带指数退避的重试 fetch
 */
export async function retryFetch(
  url: string, 
  options?: RequestInit, 
  maxRetries: number = 3
): Promise<Response> {
  let lastError: Error | null = null
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(url, options)
      if (response.ok) return response
      
      // 如果是不重试的错误（400, 401, 403），直接抛出
      if (response.status === 400 || response.status === 401 || response.status === 403) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      lastError = new Error(`HTTP ${response.status}: ${response.statusText}`)
    } catch (e) {
      lastError = e instanceof Error ? e : new Error(String(e))
    }
    
    // 如果不是最后一次尝试，等待后重试
    if (attempt < maxRetries - 1) {
      const delay = Math.pow(2, attempt) * 1000 // 1s, 2s, 4s
      console.log(`[DistillCache] Retry ${attempt + 1}/${maxRetries} after ${delay}ms`)
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
  
  throw lastError || new Error('Unknown fetch error')
}

/**
 * 检查 Flask 服务器健康状态
 */
export async function checkFlaskHealth(): Promise<boolean> {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 2000)
    
    const response = await fetch('http://localhost:5000/api/health', {
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    return response.ok
  } catch (e) {
    console.log('[DistillCache] Flask server not reachable')
    return false
  }
}

/**
 * 从 Flask API 加载图谱数据
 */
export async function loadFromAPI(
  limit: number = 200,
  minIWeight: number = 1.0
): Promise<CachedGraphData | null> {
  try {
    console.log('[DistillCache] Loading from API...')
    
    const response = await retryFetch(
      `http://localhost:5000/api/knowledge/graph?limit=${limit}&min_i_weight=${minIWeight}`,
      { method: 'GET' }
    )
    
    const data = await response.json()
    
    if (!data.success) {
      throw new Error(data.error || 'API returned error')
    }
    
    const result: CachedGraphData = {
      concepts: data.concepts || [],
      relations: data.triples?.map((t: any) => ({
        source: t.subject,
        target: t.object,
        type: t.predicate,
        iWeight: t.i_weight
      })) || [],
      stats: {
        conceptCount: data.concepts?.length || 0,
        relationCount: data.triples?.length || 0,
        avgIWeight: 0,
        dikwDistribution: {}
      },
      timestamp: Date.now()
    }
    
    // 计算平均 iWeight 和 DIKWP 分布
    if (result.relations.length > 0) {
      const totalIWeight = result.relations.reduce((sum, r) => sum + (r.iWeight || 1.0), 0)
      result.stats.avgIWeight = totalIWeight / result.relations.length
      
      // 简化的 DIKWP 分类（基于 predicate）
      result.stats.dikwpDistribution = {
        'Data': result.relations.filter(r => r.type === 'has_property').length,
        'Information': result.relations.filter(r => r.type === 'is_a').length,
        'Knowledge': result.relations.filter(r => r.type === 'part_of').length,
        'Wisdom': result.relations.filter(r => r.type === 'causes').length,
        'Purpose': result.relations.filter(r => r.type === 'related_to').length,
      }
    }
    
    console.log('[DistillCache] Loaded from API:', result.concepts.length, 'concepts,', result.relations.length, 'relations')
    
    // 保存到缓存
    saveGraphToCache(result)
    
    return result
  } catch (e) {
    console.warn('[DistillCache] Failed to load from API:', e)
    return null
  }
}

/**
 * 内置 TOMAS 示例概念（离线兜底）
 */
export function loadFallbackData(): CachedGraphData {
  console.log('[DistillCache] Loading fallback data...')
  
  const concepts = [
    { id: 1, label: '牛顿力学', type: 'Knowledge', iWeight: 2.5 },
    { id: 2, label: '能量守恒', type: 'Law', iWeight: 2.8 },
    { id: 3, label: '相对论', type: 'Theory', iWeight: 2.3 },
    { id: 4, label: '元素周期表', type: 'Knowledge', iWeight: 2.6 },
    { id: 5, label: '化学键', type: 'Concept', iWeight: 2.1 },
    { id: 6, label: '有机化学', type: 'Field', iWeight: 1.9 },
    { id: 7, label: '人工智能', type: 'Field', iWeight: 2.7 },
    { id: 8, label: '机器学习', type: 'Subfield', iWeight: 2.5 },
    { id: 9, label: '深度学习', type: 'Subfield', iWeight: 2.4 },
    { id: 10, label: '大语言模型', type: 'Technology', iWeight: 2.6 },
  ]
  
  const relations = [
    { source: 1, target: 2, type: 'related_to', iWeight: 2.3 },
    { source: 1, target: 3, type: 'inspired_by', iWeight: 2.1 },
    { source: 4, target: 5, type: 'used_in', iWeight: 2.0 },
    { source: 5, target: 6, type: 'part_of', iWeight: 1.8 },
    { source: 7, target: 8, type: 'is_a', iWeight: 2.5 },
    { source: 8, target: 9, type: 'is_a', iWeight: 2.3 },
    { source: 9, target: 10, type: 'used_in', iWeight: 2.4 },
  ]
  
  return {
    concepts,
    relations,
    stats: {
      conceptCount: concepts.length,
      relationCount: relations.length,
      avgIWeight: 2.3,
      dikwDistribution: {
        'Data': 2,
        'Information': 2,
        'Knowledge': 3,
        'Wisdom': 2,
        'Purpose': 1,
      }
    },
    timestamp: Date.now()
  }
}

/**
 * 三级数据加载主函数
 * Level 1: 缓存
 * Level 2: API
 * Level 3: 兜底
 */
export async function loadFromCacheOrAPI(
  limit: number = 200,
  minIWeight: number = 1.0
): Promise<{ data: CachedGraphData; source: 'cache' | 'api' | 'fallback' }> {
  // Level 1: 尝试从缓存加载
  const cached = loadGraphFromCache()
  if (cached) {
    return { data: cached, source: 'cache' }
  }
  
  // Level 2: 尝试从 API 加载
  const isHealthy = await checkFlaskHealth()
  if (isHealthy) {
    const apiData = await loadFromAPI(limit, minIWeight)
    if (apiData) {
      return { data: apiData, source: 'api' }
    }
  }
  
  // Level 3: 使用兜底数据
  return { data: loadFallbackData(), source: 'fallback' }
}
