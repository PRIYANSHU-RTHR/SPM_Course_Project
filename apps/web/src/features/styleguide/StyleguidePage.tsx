import { PageHeader } from '@/components/PageHeader'
import { ComponentSections } from './ComponentSections'
import { TaskTableSection } from './TaskTableSection'
import { TokenSections } from './TokenSections'

export function StyleguidePage() {
  return (
    <>
      <PageHeader label="Design system" title="Styleguide">
        Tokens and shared components. Check new UI against this page.
      </PageHeader>
      <div className="flex flex-col gap-10">
        <TokenSections />
        <ComponentSections />
        <TaskTableSection />
      </div>
    </>
  )
}
