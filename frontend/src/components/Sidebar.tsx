'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  BookOpen,
  Building2,
  CircleDollarSign,
  ClipboardCheck,
  FileClock,
  Gauge,
  GitBranch,
  History,
  Landmark,
  LockKeyhole,
  Map,
  Radio,
  Scale,
  Settings,
  ShieldAlert,
} from 'lucide-react';

const NAV = [
  { href: '/civilization', label: 'Civilization Map', icon: Map },
  { href: '/civilization/institution', label: 'Institution', icon: Building2 },
  { href: '/civilization/reviews', label: 'Reviews', icon: ClipboardCheck },
  { href: '/civilization/governance', label: 'Governance', icon: Scale },
  { href: '/civilization/memory', label: 'Memory', icon: BookOpen },
  { href: '/civilization/calibration', label: 'Calibration', icon: GitBranch },
  { href: '/dashboard', label: 'Agent Status', icon: Gauge },
  { href: '/override', label: 'Override Queue', icon: LockKeyhole },
  { href: '/audit', label: 'Audit Log', icon: FileClock },
  { href: '/events', label: 'Event Stream', icon: Radio },
  { href: '/performance', label: 'Performance', icon: BarChart3 },
  { href: '/config', label: 'Config History', icon: Settings },
  { href: '/finance', label: 'Finance', icon: CircleDollarSign },
  { href: '/incidents', label: 'Incidents', icon: ShieldAlert },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <div className="font-bold text-lg">Agentco</div>
        <div className="text-gray-400 text-xs mt-0.5">Civilization Dashboard</div>
      </div>
      <nav className="flex-1 p-3">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm mb-1 transition-colors ${
              pathname === href || (href !== '/civilization' && pathname.startsWith(href))
                ? 'bg-gray-700 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            }`}
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{label}</span>
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        Calibration-first governance
      </div>
    </aside>
  );
}
