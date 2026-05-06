// dashboard/app/policies/page.tsx
"use client";

import { useEffect, useState } from "react";

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL || "https://yourdomain.com";

interface PolicyRecord {
  policy_id:        string;
  role_binding:     string;
  resource_pattern: string;
  http_method:      string;
  effect:           string;
  priority:         number;
  is_active:        boolean;
}

interface NewPolicy {
  role_binding:     string;
  resource_pattern: string;
  http_method:      string;
  effect:           string;
  priority:         number;
}

const BLANK: NewPolicy = {
  role_binding:     "Viewer",
  resource_pattern: "/aws/*",
  http_method:      "GET",
  effect:           "permit",
  priority:         300,
};

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<PolicyRecord[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [form, setForm]         = useState<NewPolicy>(BLANK);
  const [msg, setMsg]           = useState<string | null>(null);

  const token = () => (typeof localStorage !== "undefined" ? localStorage.getItem("zt_token") ?? "" : "");

  const fetchPolicies = async () => {
    try {
      const r = await fetch(`${GATEWAY}/admin/policies`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setPolicies(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const createPolicy = async () => {
    try {
      const r = await fetch(`${GATEWAY}/admin/policies`, {
        method:  "POST",
        headers: {
          "Content-Type":  "application/json",
          Authorization:   `Bearer ${token()}`,
        },
        body: JSON.stringify(form),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setMsg("Policy created.");
      setForm(BLANK);
      fetchPolicies();
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    }
  };

  const deletePolicy = async (id: string) => {
    try {
      await fetch(`${GATEWAY}/admin/policies/${id}`, {
        method:  "DELETE",
        headers: { Authorization: `Bearer ${token()}` },
      });
      setMsg("Policy deactivated.");
      fetchPolicies();
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    }
  };

  useEffect(() => { fetchPolicies(); }, []);

  const field = (key: keyof NewPolicy, value: string | number) =>
    setForm((f) => ({ ...f, [key]: value }));

  const conflicts = policies.filter(
    (p) =>
      p.role_binding === form.role_binding &&
      p.resource_pattern === form.resource_pattern &&
      (p.http_method === form.http_method || p.http_method === "*" || form.http_method === "*") &&
      p.effect !== form.effect
  );

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-2">Policies</h2>
      <p className="text-gray-500 text-sm mb-6">
        RBAC rules evaluated by the Policy Engine. Higher priority wins.
      </p>

      {msg && (
        <div className="mb-4 text-sm text-cyan-300 bg-cyan-900/20 border border-cyan-800 rounded px-4 py-2">
          {msg}
        </div>
      )}

      {/* Create-policy form */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-300 mb-1">Add New Rule</h3>
        <p className="text-xs text-gray-600 mb-4">
          Rules are evaluated highest-priority first. Use wildcards in patterns (e.g. <code className="text-gray-500">/aws/*</code>). A deny-by-default posture applies when no rule matches.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
          {(
            [
              ["Role Binding", "role_binding", "text"],
              ["Resource Pattern", "resource_pattern", "text"],
              ["HTTP Method", "http_method", "text"],
            ] as const
          ).map(([label, key, type]) => (
            <label key={key} className="block">
              <span className="text-xs text-gray-500">{label}</span>
              <input
                type={type}
                value={form[key]}
                onChange={(e) => field(key, e.target.value)}
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-cyan-600"
              />
            </label>
          ))}

          <label className="block">
            <span className="text-xs text-gray-500">Effect</span>
            <select
              value={form.effect}
              onChange={(e) => field("effect", e.target.value)}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none"
            >
              <option value="permit">permit</option>
              <option value="deny">deny</option>
            </select>
          </label>

          <label className="block">
            <span className="text-xs text-gray-500">Priority</span>
            <input
              type="number"
              value={form.priority}
              onChange={(e) => field("priority", Number(e.target.value))}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none"
            />
          </label>
        </div>
        {conflicts.length > 0 && (
          <div className="mb-3 text-xs text-yellow-300 bg-yellow-900/20 border border-yellow-800 rounded px-4 py-2">
            ⚠ Conflict detected: {conflicts.length} existing rule{conflicts.length > 1 ? "s" : ""} with opposite effect for this role/resource/method combination. Higher priority wins.
          </div>
        )}
        <button
          onClick={createPolicy}
          className="bg-cyan-700 hover:bg-cyan-600 text-white text-sm px-4 py-2 rounded-md"
        >
          Create Rule
        </button>
      </div>

      {/* Policy table */}
      {loading && <p className="text-gray-500">Loading…</p>}
      {error   && <p className="text-red-400">Error: {error}</p>}

      {!loading && !error && (
        <div className="overflow-auto rounded-xl border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-800 bg-gray-900">
                {["Role", "Resource Pattern", "Method", "Effect", "Priority", ""].map((h) => (
                  <th key={h} className="px-4 py-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {policies.map((p) => (
                <tr
                  key={p.policy_id}
                  className="border-b border-gray-800/50 hover:bg-gray-900/50"
                >
                  <td className="px-4 py-3 text-gray-200">{p.role_binding}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{p.resource_pattern}</td>
                  <td className="px-4 py-3 text-gray-400">{p.http_method}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        p.effect === "permit"
                          ? "bg-green-900/60 text-green-300"
                          : "bg-red-900/60 text-red-300"
                      }`}
                    >
                      {p.effect}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{p.priority}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => deletePolicy(p.policy_id)}
                      className="text-xs text-red-400 hover:text-red-300 underline"
                    >
                      Disable
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
