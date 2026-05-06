// dashboard/app/users/page.tsx
"use client";

import { useEffect, useState } from "react";

const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL || "https://yourdomain.com";

interface UserRecord {
  user_id:    string;
  username:   string;
  role:       string;
  is_active:  boolean;
  created_at: string;
}

const ROLE_COLORS: Record<string, string> = {
  Administrator: "bg-purple-900/60 text-purple-300",
  Operator:      "bg-blue-900/60 text-blue-300",
  Viewer:        "bg-gray-700/60 text-gray-300",
};

const BLANK_USER = { username: "", password: "", role: "Viewer" };

export default function UsersPage() {
  const [users, setUsers]         = useState<UserRecord[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [form, setForm]           = useState(BLANK_USER);
  const [creating, setCreating]   = useState(false);

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem("zt_token") ?? "";
      const r = await fetch(`${GATEWAY}/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setUsers(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const deactivate = async (userId: string) => {
    try {
      const token = localStorage.getItem("zt_token") ?? "";
      const r = await fetch(`${GATEWAY}/admin/users/${userId}/deactivate`, {
        method:  "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setActionMsg("User deactivated.");
      fetchUsers();
    } catch (e: any) {
      setActionMsg(`Error: ${e.message}`);
    }
  };

  const createUser = async () => {
    if (!form.username || !form.password) {
      setActionMsg("Error: Username and password are required.");
      return;
    }
    setCreating(true);
    try {
      const token = localStorage.getItem("zt_token") ?? "";
      const r = await fetch(`${GATEWAY}/admin/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(form),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${r.status}`);
      }
      setActionMsg(`User '${form.username}' created successfully.`);
      setForm(BLANK_USER);
      fetchUsers();
    } catch (e: any) {
      setActionMsg(`Error: ${e.message}`);
    } finally {
      setCreating(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-2">Users</h2>
      <p className="text-gray-500 text-sm mb-6">
        All registered identities and their role assignments.
      </p>

      {/* Create user form */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Add New User</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <label className="block">
            <span className="text-xs text-gray-500">Username</span>
            <input
              type="text"
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-cyan-600"
              placeholder="newuser"
            />
          </label>
          <label className="block">
            <span className="text-xs text-gray-500">Password</span>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-cyan-600"
              placeholder="••••••••"
            />
          </label>
          <label className="block">
            <span className="text-xs text-gray-500">Role</span>
            <select
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
              className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none"
            >
              <option>Administrator</option>
              <option>Operator</option>
              <option>Viewer</option>
            </select>
          </label>
        </div>
        <button
          onClick={createUser}
          disabled={creating}
          className="bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-md"
        >
          {creating ? "Creating…" : "Create User"}
        </button>
      </div>

      {loading && <p className="text-gray-500">Loading…</p>}
      {error   && <p className="text-red-400">Error: {error}</p>}
      {actionMsg && (
        <div className="mb-4 text-sm text-cyan-300 bg-cyan-900/20 border border-cyan-800 rounded px-4 py-2">
          {actionMsg}
        </div>
      )}

      {!loading && !error && (
        <div className="overflow-auto rounded-xl border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-800 bg-gray-900">
                {["Username", "Role", "Status", "Created", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.user_id}
                  className="border-b border-gray-800/50 hover:bg-gray-900/50 transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-gray-200">{u.username}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        ROLE_COLORS[u.role] ?? "bg-gray-700 text-gray-300"
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        u.is_active
                          ? "bg-green-900/60 text-green-300"
                          : "bg-red-900/60 text-red-300"
                      }`}
                    >
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active && (
                      <button
                        onClick={() => deactivate(u.user_id)}
                        className="text-xs text-red-400 hover:text-red-300 underline"
                      >
                        Deactivate
                      </button>
                    )}
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
