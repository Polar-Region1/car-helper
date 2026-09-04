import { useState } from 'react'

import {
  deleteMemory,
  getMemories,
  getProfile,
  updateMemory,
  type LongTermMemory,
  type Profile
} from '@/utils/api'

const CATEGORY_LABELS: Record<string, string> = {
  budget_preference: '预算偏好',
  energy_preference: '能源偏好',
  body_type_preference: '车型偏好',
  brand_preference: '品牌偏好',
  usage_preference: '使用场景',
  family_context: '家庭情况',
  charging_context: '充电条件',
  excluded_feature: '排除条件',
  other: '其他'
}

export function MemoryPanel() {
  const [open, setOpen] = useState(false)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [memories, setMemories] = useState<LongTermMemory[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [editingMemoryId, setEditingMemoryId] = useState<string | null>(null)
  const [draftValue, setDraftValue] = useState('')
  const [saving, setSaving] = useState(false)

  const openPanel = async () => {
    setOpen(true)
    setLoading(true)
    setError('')
    setEditingMemoryId(null)
    setDraftValue('')
    try {
      const [loadedProfile, loadedMemories] = await Promise.all([getProfile(), getMemories()])
      setProfile(loadedProfile)
      setMemories(loadedMemories)
    } catch (reason) {
      console.error('Failed to load memories:', reason)
      setError('长期记忆加载失败，请稍后重试。')
    } finally {
      setLoading(false)
    }
  }

  const removeMemory = async (memoryId: string) => {
    try {
      await deleteMemory(memoryId)
      setMemories(current => current.filter(memory => memory.memory_id !== memoryId))
    } catch (reason) {
      console.error('Failed to delete memory:', reason)
      setError('记忆删除失败，请稍后重试。')
    }
  }

  const startEditing = (memory: LongTermMemory) => {
    setEditingMemoryId(memory.memory_id)
    setDraftValue(memory.value)
    setError('')
  }

  const cancelEditing = () => {
    setEditingMemoryId(null)
    setDraftValue('')
  }

  const closePanel = () => {
    setOpen(false)
    cancelEditing()
    setError('')
  }

  const saveMemory = async (memoryId: string) => {
    const value = draftValue.trim()
    if (!value) {
      setError('记忆内容不能为空。')
      return
    }
    setSaving(true)
    setError('')
    try {
      const updated = await updateMemory(memoryId, value)
      setMemories(current =>
        current.map(memory => (memory.memory_id === memoryId ? updated : memory))
      )
      cancelEditing()
    } catch (reason) {
      console.error('Failed to update memory:', reason)
      setError('记忆修改失败，请稍后重试。')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => void openPanel()}
        className="px-5 py-3 border border-border bg-background text-sm hover:bg-foreground hover:text-background transition-all"
      >
        Memory{profile ? ` (${memories.length})` : ''}
      </button>

      {open && (
        <div className="fixed inset-0 z-[100] bg-black/30 flex items-center justify-center p-6">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="memory-panel-title"
            className="w-full max-w-2xl max-h-[80vh] overflow-hidden bg-background border border-border shadow-xl"
          >
            <header className="flex items-center justify-between px-6 py-5 border-b border-border">
              <div>
                <h2 id="memory-panel-title" className="text-sm font-semibold tracking-widest uppercase">
                  Long-term Memory
                </h2>
                {profile && <p className="text-xs text-muted-foreground mt-1">{profile.display_name}</p>}
              </div>
              <button
                type="button"
                onClick={closePanel}
                className="px-3 py-2 border border-border text-sm hover:bg-muted"
                aria-label="关闭长期记忆"
              >
                Close
              </button>
            </header>

            <div className="max-h-[calc(80vh-5rem)] overflow-y-auto p-6">
              {loading && <p className="text-sm text-muted-foreground">加载中...</p>}
              {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
              {!loading && memories.length === 0 && !error && (
                <p className="text-sm text-muted-foreground">
                  暂无长期记忆。只有你明确要求记住的稳定偏好才会出现在这里。
                </p>
              )}
              <div className="space-y-3">
                {memories.map(memory => (
                  <article key={memory.memory_id} className="border border-border p-4">
                    <div className="flex justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-muted-foreground mb-2">
                          {CATEGORY_LABELS[memory.category] || memory.category} · {memory.key}
                        </p>
                        {editingMemoryId === memory.memory_id ? (
                          <textarea
                            value={draftValue}
                            onChange={event => setDraftValue(event.target.value)}
                            maxLength={500}
                            rows={3}
                            autoFocus
                            className="w-full resize-y border border-border bg-background p-3 text-sm outline-none focus:border-foreground"
                            aria-label="修改记忆内容"
                          />
                        ) : (
                          <p className="text-sm whitespace-pre-wrap break-words">{memory.value}</p>
                        )}
                      </div>
                      <div className="flex shrink-0 gap-2">
                        {editingMemoryId === memory.memory_id ? (
                          <>
                            <button
                              type="button"
                              onClick={() => void saveMemory(memory.memory_id)}
                              disabled={saving || !draftValue.trim()}
                              className="self-start px-3 py-2 border border-foreground bg-foreground text-background text-xs disabled:opacity-40"
                            >
                              {saving ? '保存中' : '保存'}
                            </button>
                            <button
                              type="button"
                              onClick={cancelEditing}
                              disabled={saving}
                              className="self-start px-3 py-2 border border-border text-xs hover:bg-muted disabled:opacity-40"
                            >
                              取消
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => startEditing(memory)}
                              className="self-start px-3 py-2 border border-border text-xs hover:bg-foreground hover:text-background transition-colors"
                            >
                              编辑
                            </button>
                            <button
                              type="button"
                              onClick={() => void removeMemory(memory.memory_id)}
                              className="self-start px-3 py-2 border border-border text-xs hover:bg-foreground hover:text-background transition-colors"
                            >
                              删除
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </div>
      )}
    </>
  )
}
