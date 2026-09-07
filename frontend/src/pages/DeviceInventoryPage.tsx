import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Cpu, Search, Filter } from 'lucide-react';

export const DeviceInventoryPage: React.FC = () => {
  const [devices, setDevices] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDevices();
  }, [searchQuery, statusFilter]);

  const loadDevices = async () => {
    setLoading(true);
    try {
      const data = await api.getDevices(searchQuery, statusFilter);
      setDevices(data || []);
    } catch (err) {
      console.error('Failed to load devices:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="p-6 glass-card rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Cpu className="w-6 h-6 text-teal-400" />
            <span>Portable Medical Device Inventory</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">Manage portable medical devices across rural clinics and field mobile units.</p>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search Device ID or Serial..."
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
            <option value="READY_FOR_REISSUE">READY_FOR_REISSUE</option>
            <option value="ISSUED">ISSUED</option>
            <option value="QUARANTINED">QUARANTINED</option>
            <option value="INSPECTION_REQUIRED">INSPECTION_REQUIRED</option>
          </select>
        </div>
      </div>

      <div className="border border-slate-800 rounded-2xl glass-card overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/90 text-slate-400 font-semibold uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Device ID</th>
              <th className="px-4 py-3">Device Type</th>
              <th className="px-4 py-3">Serial Number</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Current Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {devices.map((dev) => (
              <tr key={dev.device_id} className="hover:bg-slate-800/30">
                <td className="px-4 py-3.5 font-bold text-teal-300">{dev.device_id}</td>
                <td className="px-4 py-3.5 font-semibold text-white">{dev.device_type}</td>
                <td className="px-4 py-3.5 text-slate-400 font-mono text-[11px]">{dev.serial_number}</td>
                <td className="px-4 py-3.5 text-slate-300">{dev.location}</td>
                <td className="px-4 py-3.5">
                  <span className={`px-2.5 py-0.5 rounded text-[10px] font-extrabold ${
                    dev.status === 'READY_FOR_REISSUE' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                    dev.status === 'QUARANTINED' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                    dev.status === 'ISSUED' ? 'bg-amber-500/20 text-amber-300' :
                    'bg-slate-800 text-slate-300'
                  }`}>
                    {dev.status}
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
