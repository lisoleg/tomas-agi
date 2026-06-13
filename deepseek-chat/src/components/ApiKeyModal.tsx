// API Key 配置弹窗
import { useEffect, useState, type FormEvent } from 'react'
import { IconClose, IconKey } from './icons'

interface ApiKeyModalProps {
  open: boolean
  initialValue: string
  onSave: (key: string) => void
  onClose: () => void
}

export function ApiKeyModal({ open, initialValue, onSave, onClose }: ApiKeyModalProps) {
  const [value, setValue] = useState(initialValue)
  const [show, setShow] = useState(false)

  // 打开时重置为最新值
  useEffect(() => {
    if (open) {
      setValue(initialValue)
      setShow(false)
    }
  }, [open, initialValue])

  if (!open) return null

  /** 提交 */
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    onSave(value.trim())
  }

  /** 清除 */
  const handleClear = () => {
    setValue('')
    onSave('')
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-[#2A2B32] rounded-xl shadow-2xl border border-white/10 animate-slide-up"
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <IconKey size={18} className="text-accent" />
            <h2 className="text-base font-semibold">API Key 设置</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-white/10"
            aria-label="关闭"
          >
            <IconClose size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-5 py-4 space-y-3">
          <div className="text-sm text-textSecondary leading-relaxed">
            请输入你的 <span className="text-textPrimary font-medium">DeepSeek API Key</span>。
            Key 仅保存在浏览器 localStorage，不会上传服务器。
          </div>

          <div>
            <label className="block text-xs text-textSecondary mb-1.5">API Key</label>
            <div className="relative">
              <input
                type={show ? 'text' : 'password'}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="sk-..."
                spellCheck={false}
                autoComplete="off"
                className="w-full px-3 py-2.5 pr-20 rounded-md bg-black/30 border border-white/10 outline-none text-sm font-mono focus:border-accent"
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs px-2 py-1 rounded hover:bg-white/10 text-textSecondary"
              >
                {show ? '隐藏' : '显示'}
              </button>
            </div>
          </div>

          <div className="text-[12px] text-textSecondary">
            还没有？前往
            <a
              href="https://platform.deepseek.com/api_keys"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent hover:underline mx-1"
            >
              DeepSeek 开放平台
            </a>
            申请。
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleClear}
              className="text-sm text-rose-300 hover:text-rose-200 px-3 py-2"
            >
              清除
            </button>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm rounded-md hover:bg-white/10"
              >
                取消
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm rounded-md bg-accent hover:bg-accentHover text-white"
              >
                保存
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
