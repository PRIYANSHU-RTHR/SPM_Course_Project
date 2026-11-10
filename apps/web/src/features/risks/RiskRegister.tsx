import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Risk } from '@/lib/api/schemas'
import { formatRiskId, formatShortDate } from '@/lib/format'
import { parseRmmm } from './riskMetrics'

const STATUS = {
  open: { label: 'Open', variant: 'warning' },
  mitigating: { label: 'Mitigating', variant: 'secondary' },
  closed: { label: 'Closed', variant: 'outline' },
} as const

export function RiskStatusBadge({ status }: { status: Risk['status'] }) {
  return <Badge variant={STATUS[status].variant}>{STATUS[status].label}</Badge>
}

interface RiskRegisterProps {
  risks: Risk[]
  onSelect: (riskId: number) => void
}

export function RiskRegister({ risks, onSelect }: RiskRegisterProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-20">ID</TableHead>
          <TableHead>Risk</TableHead>
          <TableHead>Category</TableHead>
          <TableHead className="text-right">P</TableHead>
          <TableHead className="text-right">I</TableHead>
          <TableHead className="text-right">Score</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Owner role</TableHead>
          <TableHead className="text-right">Detected</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {risks.map((risk) => {
          const owner = parseRmmm(risk.rmmm)?.ownerRole
          return (
            <TableRow key={risk.id} className="cursor-pointer" onClick={() => onSelect(risk.id)}>
              <TableCell className="numeric text-muted-foreground">
                {formatRiskId(risk.id)}
              </TableCell>
              <TableCell className="max-w-96">
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation()
                    onSelect(risk.id)
                  }}
                  className="block max-w-full cursor-pointer truncate rounded-sm text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {risk.title}
                </button>
              </TableCell>
              <TableCell className="text-muted-foreground capitalize">{risk.category}</TableCell>
              <TableCell className="numeric text-right">{risk.probability}</TableCell>
              <TableCell className="numeric text-right">{risk.impact}</TableCell>
              <TableCell className="numeric text-right">{risk.score}</TableCell>
              <TableCell>
                <RiskStatusBadge status={risk.status} />
              </TableCell>
              <TableCell className={owner ? undefined : 'text-subtle'}>{owner || '—'}</TableCell>
              <TableCell className="numeric text-right text-muted-foreground">
                {formatShortDate(risk.created_at.slice(0, 10))}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
