"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Queue" },
  { href: "/outcomes", label: "Call outcomes" },
];

export function SideNav() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 border-r border-hairline flex flex-col">
      <div className="px-5 py-6">
        <span className="font-[family-name:var(--font-display)] font-semibold text-lg tracking-tight">
          ORVYRA
        </span>
        <p className="text-xs text-text-muted mt-0.5">Operator</p>
      </div>
      <nav className="flex flex-col gap-0.5 px-3">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-2 rounded-md text-sm transition-colors ${
                active
                  ? "bg-surface-raised text-cyan"
                  : "text-text-muted hover:text-text hover:bg-surface"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto px-5 py-4 text-xs text-text-muted border-t border-hairline">
        Klesos reference implementation
      </div>
    </aside>
  );
}
