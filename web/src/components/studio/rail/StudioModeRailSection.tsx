import { Globe, PenTool } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { NovelShellStage } from '@/components/novel-shell/NovelShellRouteState'

export function StudioModeRailSection({
  activeStage,
  latestChapterReference,
  onContinuation,
  onOpenAtlas,
}: {
  activeStage: NovelShellStage | null
  latestChapterReference: string | null
  onContinuation: () => void
  onOpenAtlas: () => void
}) {
  return (
    <section className="space-y-2" data-testid="studio-rail-modes">
      <div className="px-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
        工作区
      </div>

      <div className="space-y-1.5">
        {latestChapterReference !== null ? (
          <button
            type="button"
            onClick={onContinuation}
            data-testid="studio-rail-continuation"
            className={cn(
              'w-full rounded-[14px] border px-3 py-3 text-left transition-all',
              'flex items-start gap-3',
              activeStage === 'write'
                ? 'border-accent/25 bg-accent/10 text-accent shadow-sm'
                : 'border-[var(--nw-glass-border)] bg-background/15 text-foreground/85 hover:bg-foreground/5',
            )}
          >
            <PenTool size={16} className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <div className="text-[13px] font-medium">续写设置</div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">
                基于{latestChapterReference}配置下一次续写
              </div>
            </div>
          </button>
        ) : null}

        <button
          type="button"
          onClick={onOpenAtlas}
          className={cn(
            'w-full rounded-[14px] border border-[var(--nw-glass-border)] bg-background/15 px-3 py-3 text-left transition-all',
            'flex items-start gap-3 text-foreground/85 hover:bg-foreground/5',
          )}
        >
          <Globe size={16} className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <div className="text-[13px] font-medium">Atlas 世界模型</div>
            <div className="mt-0.5 text-[11px] text-muted-foreground">
              进入关系图谱、审核与深度整理
            </div>
          </div>
        </button>
      </div>
    </section>
  )
}
