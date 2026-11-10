import { OwnerChip } from '@/components/OwnerChip'
import { Badge } from '@/components/ui/badge'
import type { Candidate } from '@/lib/api/schemas'
import { formatRatio } from '@/lib/format'
import { SCORE_PARTS } from './teamMetrics'

interface CandidateCardProps {
  candidate: Candidate
  name: string
  recommended: boolean
}

export function CandidateCard({ candidate, name, recommended }: CandidateCardProps) {
  const { member_id: id, score } = candidate

  return (
    <li className="rounded-lg border p-3">
      <div className="flex items-center gap-2">
        <OwnerChip id={id} name={name} decorative />
        <span className="min-w-0 flex-1 truncate">{name}</span>
        {recommended ? <Badge>Recommended</Badge> : null}
        <span className="numeric text-[15px]">{formatRatio(score.total, 1)}</span>
      </div>
      <div
        role="img"
        aria-label={`Score ${formatRatio(score.total, 1)}: skill ${formatRatio(score.skill_part, 1)}, capacity ${formatRatio(score.capacity_part, 1)}, balance ${formatRatio(score.balance_part, 1)}`}
        className="mt-2 flex h-2 gap-0.5"
      >
        {SCORE_PARTS.filter(({ key }) => score[key] > 0).map(({ key, colour }) => (
          <span
            key={key}
            className="h-full first:rounded-l-sm last:rounded-r-sm"
            style={{ width: `${score[key]}%`, background: colour }}
          />
        ))}
      </div>
      <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
        {SCORE_PARTS.map(({ key, label, colour }) => (
          <div key={key}>
            <dt className="flex items-center gap-1.5 text-muted-foreground">
              <span aria-hidden className="size-2 rounded-sm" style={{ background: colour }} />
              {label}
            </dt>
            <dd className="numeric mt-0.5">{formatRatio(score[key], 1)}</dd>
          </div>
        ))}
      </dl>
    </li>
  )
}
