import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/services/api"
import { novelKeys } from "@/hooks/novel/keys"
import type { ChapterMeta, Novel } from "@/types/api"

export function useDeleteChapter(novelId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (chapterNum: number) => api.deleteChapter(novelId, chapterNum),
    onMutate: async (chapterNum) => {
      await qc.cancelQueries({ queryKey: novelKeys.chaptersMeta(novelId) })
      await qc.cancelQueries({ queryKey: novelKeys.detail(novelId) })

      const previousMeta = qc.getQueryData<ChapterMeta[]>(novelKeys.chaptersMeta(novelId))
      const previousNovel = qc.getQueryData<Novel>(novelKeys.detail(novelId))

      if (previousMeta) {
        qc.setQueryData<ChapterMeta[]>(
          novelKeys.chaptersMeta(novelId),
          previousMeta.filter((chapter) => chapter.chapter_number !== chapterNum),
        )
      }

      if (previousNovel) {
        qc.setQueryData<Novel>(novelKeys.detail(novelId), {
          ...previousNovel,
          total_chapters: Math.max(previousNovel.total_chapters - 1, 0),
        })
      }

      qc.removeQueries({ queryKey: novelKeys.chapter(novelId, chapterNum), exact: true })

      return { previousMeta, previousNovel }
    },
    onError: (_error, _chapterNum, context) => {
      if (context?.previousMeta) {
        qc.setQueryData(novelKeys.chaptersMeta(novelId), context.previousMeta)
      }
      if (context?.previousNovel) {
        qc.setQueryData(novelKeys.detail(novelId), context.previousNovel)
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: novelKeys.chaptersMeta(novelId) })
      qc.invalidateQueries({ queryKey: novelKeys.detail(novelId) })
    },
  })
}
