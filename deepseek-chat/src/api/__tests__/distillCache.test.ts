/**
 * distillCache.ts 单元测试
 * 测试三级缓存模块的所有核心功能
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  saveGraphToCache,
  loadGraphFromCache,
  retryFetch,
  checkFlaskHealth,
  loadFallbackData,
  loadFromCacheOrAPI,
  CachedGraphData,
} from '../distillCache'

const CACHE_KEY = 'tomas_distill_cache'

// 模拟 localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
  }
})()

// 构造测试数据
function makeTestData(timestamp?: number): CachedGraphData {
  return {
    concepts: [{ id: 1, label: '测试概念', type: 'Knowledge', iWeight: 2.5 }],
    relations: [{ source: 1, target: 2, type: 'is_a', iWeight: 2.3 }],
    stats: {
      conceptCount: 1,
      relationCount: 1,
      avgIWeight: 2.3,
      dikwpDistribution: { Data: 1, Information: 1, Knowledge: 1, Wisdom: 0, Purpose: 0 },
    },
    timestamp: timestamp ?? Date.now(),
  }
}

describe('distillCache', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.stubGlobal('localStorage', localStorageMock)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  // ========== saveGraphToCache + loadGraphFromCache ==========

  it('saveGraphToCache + loadGraphFromCache 正常读写', () => {
    const data = makeTestData()
    saveGraphToCache(data)
    const loaded = loadGraphFromCache()
    expect(loaded).not.toBeNull()
    expect(loaded!.concepts).toEqual(data.concepts)
    expect(loaded!.relations).toEqual(data.relations)
    expect(loaded!.stats.conceptCount).toBe(1)
  })

  it('缓存过期（TTL 5min）返回 null', () => {
    // saveGraphToCache 内部会覆盖 timestamp，所以直接写 localStorage
    const expiredData = makeTestData(Date.now() - 6 * 60 * 1000)
    localStorageMock.setItem(CACHE_KEY, JSON.stringify(expiredData))
    const loaded = loadGraphFromCache()
    expect(loaded).toBeNull()
  })

  it('损坏 JSON 返回 null', () => {
    localStorageMock.setItem(CACHE_KEY, '{invalid json!!!')
    const loaded = loadGraphFromCache()
    expect(loaded).toBeNull()
  })

  it('缓存不存在时返回 null', () => {
    const loaded = loadGraphFromCache()
    expect(loaded).toBeNull()
  })

  // ========== retryFetch ==========

  it('retryFetch 成功路径', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 200 }))
    vi.stubGlobal('fetch', mockFetch)
    const result = await retryFetch('http://test.com/api')
    expect(result.ok).toBe(true)
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })

  it('retryFetch 重试后成功', async () => {
    vi.useFakeTimers()
    const mockFetch = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 500 }))
      .mockResolvedValueOnce(new Response(null, { status: 200 }))
    vi.stubGlobal('fetch', mockFetch)

    const promise = retryFetch('http://test.com/api')
    await vi.advanceTimersByTimeAsync(1000)
    const result = await promise
    expect(result.ok).toBe(true)
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })

  it('retryFetch 3次全失败抛错', async () => {
    vi.useFakeTimers()
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 500 }))
    vi.stubGlobal('fetch', mockFetch)

    // 先捕获 promise 防止 unhandled rejection
    let caught = false
    const promise = retryFetch('http://test.com/api').catch(() => { caught = true })
    await vi.advanceTimersByTimeAsync(7000)
    await promise
    expect(caught).toBe(true)
    expect(mockFetch).toHaveBeenCalledTimes(3)
  })

  it('retryFetch HTTP 400 不重试直接抛错', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 400 }))
    vi.stubGlobal('fetch', mockFetch)
    await expect(retryFetch('http://test.com/api')).rejects.toThrow('HTTP 400')
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })

  it('retryFetch HTTP 401 不重试直接抛错', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 401 }))
    vi.stubGlobal('fetch', mockFetch)
    await expect(retryFetch('http://test.com/api')).rejects.toThrow('HTTP 401')
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })

  it('retryFetch HTTP 403 不重试直接抛错', async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 403 }))
    vi.stubGlobal('fetch', mockFetch)
    await expect(retryFetch('http://test.com/api')).rejects.toThrow('HTTP 403')
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })

  it('retryFetch 网络异常重试后成功', async () => {
    vi.useFakeTimers()
    const mockFetch = vi.fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(new Response(null, { status: 200 }))
    vi.stubGlobal('fetch', mockFetch)

    const promise = retryFetch('http://test.com/api')
    await vi.advanceTimersByTimeAsync(1000)
    const result = await promise
    expect(result.ok).toBe(true)
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })

  // ========== checkFlaskHealth ==========

  it('checkFlaskHealth 成功返回 true', async () => {
    vi.useFakeTimers()
    const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 200 }))
    vi.stubGlobal('fetch', mockFetch)

    const promise = checkFlaskHealth()
    await vi.advanceTimersByTimeAsync(3000)
    const result = await promise
    expect(result).toBe(true)
  })

  it('checkFlaskHealth 失败返回 false', async () => {
    vi.useFakeTimers()
    const mockFetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', mockFetch)

    const promise = checkFlaskHealth()
    await vi.advanceTimersByTimeAsync(3000)
    const result = await promise
    expect(result).toBe(false)
  })

  // ========== loadFallbackData ==========

  it('loadFallbackData 返回正确结构', () => {
    const data = loadFallbackData()
    expect(data.concepts).toBeDefined()
    expect(data.concepts.length).toBeGreaterThan(0)
    expect(data.relations).toBeDefined()
    expect(data.relations.length).toBeGreaterThan(0)
    expect(data.stats).toBeDefined()
    expect(data.stats.conceptCount).toBe(data.concepts.length)
    expect(data.stats.relationCount).toBe(data.relations.length)
    expect(data.stats.avgIWeight).toBeGreaterThan(0)
    expect(data.stats.dikwpDistribution).toBeDefined()
    expect(data.timestamp).toBeGreaterThan(0)
  })

  // ========== loadFromCacheOrAPI ==========

  it('loadFromCacheOrAPI Level 1 缓存命中', async () => {
    const data = makeTestData()
    saveGraphToCache(data)

    const result = await loadFromCacheOrAPI()
    expect(result.source).toBe('cache')
    expect(result.data.concepts).toEqual(data.concepts)
  })

  it('loadFromCacheOrAPI Level 3 API 不可用时返回 fallback', async () => {
    vi.useFakeTimers()
    const mockFetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', mockFetch)

    const promise = loadFromCacheOrAPI()
    await vi.advanceTimersByTimeAsync(5000)
    const result = await promise
    expect(result.source).toBe('fallback')
    expect(result.data.concepts.length).toBeGreaterThan(0)
  })
})
