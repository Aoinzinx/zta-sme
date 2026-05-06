// dashboard/components/Sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const NAV_ITEMS = [
  { href: "/status",   label: "System Status",  icon: "⬡" },
  { href: "/users",    label: "Users",           icon: "👤" },
  { href: "/policies", label: "Policies",        icon: "🔐" },
  { href: "/audit",    label: "Audit Log",       icon: "📋" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router   = useRouter();

  const logout = () => {
    localStorage.removeItem("zt_token");
    localStorage.removeItem("zt_refresh");
    localStorage.removeItem("zt_username");
    router.replace("/login");
  };

  const username = typeof window !== "undefined"
    ? localStorage.getItem("zt_username") ?? "admin"
    : "admin";

  return (
    <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col min-h-screen">
      <div className="p-5 border-b border-gray-800">
        <h1 className="text-sm font-bold text-cyan-400 tracking-widest uppercase">
          ZT-SME
        </h1>
        <p className="text-xs text-gray-500 mt-0.5">Zero Trust Framework</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                active
                  ? "bg-cyan-900/40 text-cyan-300 font-medium"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
              }`}
            >
              <span>{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-800 space-y-2">
        <p className="text-xs text-gray-500">
          Signed in as <span className="text-gray-300 font-mono">{username}</span>
        </p>
        <button
          onClick={logout}
          className="w-full text-xs text-red-400 hover:text-red-300 border border-red-900/40 hover:border-red-700 rounded px-2 py-1.5 transition-colors text-left"
        >
          Sign Out
        </button>
        <p className="text-xs text-gray-700">
          London Metropolitan University
          <br />FC7P01NI — Level 7 Project
        </p>
      </div>
    </aside>
  );
}
