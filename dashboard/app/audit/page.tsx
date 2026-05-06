// dashboard/app/audit/page.tsx
"use client";

import { useEffect, useState } from "react";

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL || "https://yourdomain.com";

interface AuditEntry {
  log_id:              string;
  timestamp:           string;
  subject_id:          string | null;
  resource:            string;
  http_method:         string;
  policy_decision:     string;
  response_latency_ms: number;
  client_ip:           string;
}

function exportCSV(entries: AuditEntry[]) {
  const headers = ["Timestamp","Subject","Resource","Method","Decision","Latency(ms)","IP"];
  const rows = entries.map(e => [
    new Date(e.timestamp).toISOString(),
    e.subject_id ?? "",
    e.resource,
    e.http_method,
    e.policy_decision,
    String(e.response_latency_ms),
    e.client_ip,
  ]);
  const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url;
  a.download = `zt-audit-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [filter, setFilter]   = useState<string>("all");

  const fetchAudit = async (decision?: string) => {
    setLoading(true);
    try {
      const token = localStorage.getItem("zt_token") ?? "";
      const params = decision && decision !== "all"
        ? `?decision=${decision}&limit=200`
        : `?limit=200`;
      const r = await fetch(`${GATEWAY}/admin/audit${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setEntries(await r.json());
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit(filter);
  }, [filter]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Audit Log</h2>
          <p className="text-gray-500 text-sm mt-1">
            Immutable record of all access decisions. Last 200 entries.
          </p>
        </div>

        <div className="flex gap-2">
          {["all", "permit", "deny"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1.5 rounded-md capitalize transition-colors ${
                filter === f
                  ? "bg-cyan-700 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {f}
            </button>
          ))}
          <button
            onClick={() => exportCSV(entries)}
            disabled={entries.length === 0}
            className="text-xs px-3 py-1.5 rounded-md bg-gray-800 text-green-400 hover:bg-gray-700 disabled:opacity-40"
          >
            Export CSV
          </button>
        </div>
      </div>

      {loading && <p className="text-gray-500">Loading…</p>}
      {error   && <p className="text-red-400">Error: {error}</p>}

      {!loading && !error && (
        <div className="overflow-auto rounded-xl border border-gray-800">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-800 bg-gray-900">
                {["Timestamp", "Subject", "Resource", "Method", "Decision", "Latency", "IP"].map((h) => (
                  <th key={h} className="px-3 py-3 font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr
                  key={e.log_id}
                  className={`border-b border-gray-800/30 hover:bg-gray-900/50 ${
                    e.policy_decision === "deny" ? "bg-red-950/10" : ""
                  }`}
                >
                  <td className="px-3 py-2 text-gray-500 whitespace-nowrap">
                    {new Date(e.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 font-mono text-gray-400 max-w-[100px] truncate">
                    {e.subject_id ? e.subject_id.slice(0, 8) + "…" : "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-gray-300 max-w-[180px] truncate">
                    {e.resource}
                  </td>
                  <td className="px-3 py-2 text-gray-400">{e.http_method}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`px-2 py-0.5 rounded font-medium ${
                        e.policy_decision === "permit"
                          ? "bg-green-900/50 text-green-300"
                          : "bg-red-900/50 text-red-300"
                      }`}
                    >
                      {e.policy_decision}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-gray-500">{e.response_latency_ms} ms</td>
                  <td className="px-3 py-2 font-mono text-gray-500">{e.client_ip}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
