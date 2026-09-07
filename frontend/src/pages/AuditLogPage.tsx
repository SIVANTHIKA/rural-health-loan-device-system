import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { AuditLogItem } from '../types';
import { RefreshCw, Clock, UserCheck, ShieldCheck } from 'lucide-react';

export const AuditLogPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs();
      setLogs(data || []);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="p-6 glass-card rounded-2xl flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-teal-400" />
            <span>Immutable System Audit Trail</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">Full compliance logging of return check-ins, rule engine evaluations, clinician confirmations, and overrides.</p>
        </div>
        <button
          onClick={loadAuditLogs}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh Logs</span>
        </button>
      </div>

      <div className="border border-slate-800 rounded-2xl glass-card overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/90 text-slate-400 font-semibold uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">User & Role</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Entity & ID</th>
              <th className="px-4 py-3">Action Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {logs.map((log) => (
              <tr key={log.log_id} className="hover:bg-slate-800/30">
                <td className="px-4 py-3.5 text-slate-400 font-mono text-[11px]">
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-3.5">
                  <div className="font-bold text-white">{log.user_name}</div>
                  <span className="text-[10px] text-teal-300">{log.user_role}</span>
                </td>
                <td className="px-4 py-3.5 font-bold text-amber-300">{log.action}</td>
                <td className="px-4 py-3.5 text-slate-300">
                  <span className="text-slate-400">{log.entity}:</span> <strong className="text-white">{log.entity_id}</strong>
                </td>
                <td className="px-4 py-3.5 text-slate-300 max-w-sm truncate">{log.details || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
