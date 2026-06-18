'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/',            label: 'Home',             icon: '◉' },
  { href: '/dashboard',   label: 'Agents',           icon: '⚡' },
  { href: '/run',         label: 'Live Run',         icon: '▶' },
  { href: '/ledger',      label: 'Prediction Ledger',icon: '📖' },
  { href: '/calibration', label: 'Calibration',      icon: '🎯' },
  { href: '/reserve',     label: 'Epistemic Reserve',icon: '🔐' },
  { href: '/memory',      label: 'Agent Memory',     icon: '🧠' },
  { href: '/civilization',label: 'Civilization',     icon: '🏛' },
  { href: '/override',    label: 'Override Queue',   icon: '🔒' },
  { href: '/audit',       label: 'Audit Log',        icon: '⛓' },
  { href: '/events',      label: 'Event Stream',     icon: '📡' },
  { href: '/settings',    label: 'Settings',         icon: '⚙️' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 bg-gray-900 text-white flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <div className="font-bold text-lg">AgentCo</div>
        <div className="text-gray-400 text-xs mt-0.5">Epistemic Governance</div>
      </div>
      <nav className="flex-1 p-3 overflow-y-auto">
        {NAV.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm mb-1 transition-colors ${
              pathname === href
                ? 'bg-gray-700 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            }`}
          >
            <span>{icon}</span>
            <span>{label}</span>
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        Human Governor Layer
      </div>
    </aside>
  );
}
