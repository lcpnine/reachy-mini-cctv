'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Navigation() {
  const pathname = usePathname();

  const navItems = [
    { href: '/', label: 'Live Feed', icon: '📹' },
    { href: '/users', label: 'Users', icon: '👥' },
    { href: '/photos', label: 'Photos', icon: '📷' },
  ];

  return (
    <nav className="bg-gray-900 text-white w-64 min-h-screen p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Reachy CCTV</h1>
        <p className="text-gray-400 text-sm mt-1">Face Recognition System</p>
      </div>

      <ul className="space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800'
                }`}
              >
                <span className="text-xl">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="mt-auto pt-8 text-xs text-gray-500">
        <p>Version 1.0.0</p>
      </div>
    </nav>
  );
}
