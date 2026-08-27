import { FileText } from 'lucide-react'

export default function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><FileText size={38} /><strong>{title}</strong><p>{text}</p></div>
}
