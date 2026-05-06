// dashboard/app/status/page.tsx
"use client";

import { useEffect, useState } from "react";

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL || "https://yourdomain.com";

interface StatusData {
  users:        { total: number; active: number };
  policies:     { active: number };
  requests:     { total: number; denied: number };
  deny_rate_pct: number;
}

function StatCard({
  label,
  value,
  sub,
  color = "cyan",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    cyan:   "text-cyan-400",
    green:  "text-green-400",
    red:    "text-red-400",
    yellow: "text-yellow-400",
  };
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-bold ${colorMap[color] ?? "text-cyan-400"}`}>{value}</p>
      {sub && <p className="text-sm text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

export default function StatusPage() {
  const [data, setData]     = useState<StatusData | null>(null);
  const [error, setError]   = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const token = localStorage.getItem("zt_token") ?? "";
      const r = await fetch(`${GATEWAY}/admin/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-white">System Status</h2>
          <p className="text-gray-500 text-sm mt-1">Live metrics — refreshes every 30 s</p>
        </div>
        <button
          onClick={fetchStatus}
          className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded-md"
        >
          Refresh
        </button>
      </div>

      {loading && <p className="text-gray-500">Loading…</p>}
      {error   && <p className="text-red-400">Error: {error}</p>}

      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Users"
            value={data.users.total}
            sub={`${data.users.active} active`}
            color="cyan"
          />
          <StatCard
            label="Active Policies"
            value={data.policies.active}
            color="green"
          />
          <StatCard
            label="Total Requests"
            value={data.requests.total.toLocaleString()}
            sub={`${data.requests.denied} denied`}
            color="cyan"
          />
          <StatCard
            label="Deny Rate"
            value={`${data.deny_rate_pct}%`}
            color={data.deny_rate_pct > 20 ? "red" : "yellow"}
          />
        </div>
      )}
    </div>
  );
}
