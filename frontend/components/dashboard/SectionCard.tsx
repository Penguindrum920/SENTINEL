import { ReactNode } from 'react';

interface SectionCardProps {
  title: string;
  subtitle?: string;
  rightSlot?: ReactNode;
  children: ReactNode;
  className?: string;
}

export default function SectionCard({
  title,
  subtitle,
  rightSlot,
  children,
  className = '',
}: SectionCardProps) {
  return (
    <section className={`sentinel-card ${className}`}>
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--text-strong)]">
            {title}
          </h3>
          {subtitle ? (
            <p className="mt-1 text-xs text-[var(--text-soft)]">{subtitle}</p>
          ) : null}
        </div>
        {rightSlot}
      </header>
      {children}
    </section>
  );
}
