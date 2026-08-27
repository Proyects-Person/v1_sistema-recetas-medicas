import { LucideIcon } from 'lucide-react'

export default function StatCard({ title, value, helper, icon: Icon }: { title: string; value: string | number; helper: string; icon: LucideIcon }) {
  return (
    <article className="stat-card">
      <div className="stat-icon"><Icon size={20} /></div>
      <span>{helper}</span>
      <strong>{value}</strong>
      <p>{title}</p>
    </article>
  )
}
