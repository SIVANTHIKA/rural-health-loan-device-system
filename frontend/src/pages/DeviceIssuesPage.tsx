import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Search, Layers, Clock, CheckCircle2 } from 'lucide-react';

export const DeviceIssuesPage: React.FC = () => {
  const [issues, setIssues] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadIssues();
  }, [searchQuery, statusFilter]);

  const loadIssues = async () => {
    setLoading(true);
    try {
      const data = await api.getIssueRecords(searchQuery, statusFilter);
      setIssues(data || []);
    } catch (err) {
      console.error('Failed to load issue records:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="p-6 glass-card rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Layers className="w-6 h-6 text-teal-400" />
            <span>Device Issue Records Search</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">Look up active device issue transactions by Device ID, Serial, or Patient Reference ID.</p>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search Device ID, Patient Ref..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
          >
            <option value="">All Statuses</option>
            <option value="ISSUED">ISSUED</option>
            <option value="RETURNED">RETURNED</option>
            <option value="OVERDUE">OVERDUE</option>
          </select>
        </div>
      </div>

      <div className="border border-slate-800 rounded-2xl glass-card overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/90 text-slate-400 font-semibold uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Issue ID</th>
              <th className="px-4 py-3">Device ID</th>
              <th className="px-4 py-3">Patient Reference</th>
              <th className="px-4 py-3">Issued Date</th>
              <th className="px-4 py-3">Expected Return</th>
              <th className="px-4 py-3">Issued By</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {issues.map((rec) => (
              <tr key={rec.issue_id} className="hover:bg-slate-800/30">
                <td className="px-4 py-3.5 font-bold text-white">{rec.issue_id}</td>
                <td className="px-4 py-3.5 font-semibold text-teal-300">{rec.device_id}</td>
                <td className="px-4 py-3.5">{rec.patient_reference}</td>
                <td className="px-4 py-3.5 text-slate-400">{new Date(rec.issued_date).toLocaleDateString()}</td>
                <td className="px-4 py-3.5 text-slate-400">{new Date(rec.expected_return_date).toLocaleDateString()}</td>
                <td className="px-4 py-3.5 text-slate-400">{rec.issued_by}</td>
                <td className="px-4 py-3.5">
                  <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${
                    rec.status === 'ISSUED' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                    'bg-emerald-500/20 text-emerald-300'
                  }`}>
                    {rec.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
