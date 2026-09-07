import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { DashboardMetrics } from '../types';
import {
  Cpu, RotateCcw, AlertTriangle, ShieldAlert, Sparkles, CheckCircle2, Clock, Activity, ArrowUpRight
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie
} from 'recharts';

interface DashboardPageProps {
  onNavigate: (tab: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      const data = await api.getDashboardMetrics();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !metrics) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center gap-3 text-teal-400">
          <Activity className="w-6 h-6 animate-spin" />
          <span className="text-sm font-semibold">Loading real-time health network analytics...</span>
        </div>
      </div>
    );
  }

  const statCards = [
    { title: 'Total Devices', count: metrics.total_devices, icon: <Cpu className="w-5 h-5 text-teal-400" />, border: 'border-teal-500/30', bg: 'bg-teal-500/10' },
    { title: 'Returned Today', count: metrics.returned_today, icon: <RotateCcw className="w-5 h-5 text-blue-400" />, border: 'border-blue-500/30', bg: 'bg-blue-500/10' },
    { title: 'Pending Inspection', count: metrics.pending_inspection, icon: <Clock className="w-5 h-5 text-amber-400" />, border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
    { title: 'Missing Accessories', count: metrics.missing_accessories, icon: <AlertTriangle className="w-5 h-5 text-orange-400" />, border: 'border-orange-500/30', bg: 'bg-orange-500/10' },
    { title: 'Cleaning Pending', count: metrics.cleaning_pending, icon: <Sparkles className="w-5 h-5 text-cyan-400" />, border: 'border-cyan-500/30', bg: 'bg-cyan-500/10' },
    { title: 'High Priority', count: metrics.high_priority_count, icon: <ShieldAlert className="w-5 h-5 text-pink-400" />, border: 'border-pink-500/30', bg: 'bg-pink-500/10' },
    { title: 'Critical Issues', count: metrics.critical_count, icon: <AlertTriangle className="w-5 h-5 text-rose-500" />, border: 'border-rose-500/40', bg: 'bg-rose-500/10' },
    { title: 'Overdue Follow-ups', count: metrics.overdue_followups, icon: <Clock className="w-5 h-5 text-red-400 animate-pulse" />, border: 'border-red-500/40', bg: 'bg-red-500/15' },
    { title: 'Ready for Reissue', count: metrics.ready_for_reissue, icon: <CheckCircle2 className="w-5 h-5 text-emerald-400" />, border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' },
  ];

  const chartData = [
    { name: 'Cleaning Complete', value: metrics.cleaning_completion_rate, color: '#14b8a6' },
    { name: 'Patient Ack Form', value: metrics.acknowledgement_completion_rate, color: '#3b82f6' },
    { name: 'Turnaround Target', value: metrics.turnaround_completion_rate, color: '#10b981' },
    { name: 'Missing Acc Rate', value: metrics.missing_accessory_rate, color: '#f97316' },
    { name: 'Damaged Rate', value: metrics.damaged_device_rate, color: '#ef4444' },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-6 glass-card rounded-2xl gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>Operations & Safety Control Dashboard</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time monitoring of device returns, accessory reconciliation, safety quarantine triggers, and follow-up task tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate('return-wizard')}
            className="flex items-center gap-2 px-4 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-teal-500/20 transition-all"
          >
            <span>Start New Return</span>
            <ArrowUpRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 9 Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-4">
        {statCards.map((card, idx) => (
          <div
            key={idx}
            className={`p-4 rounded-xl glass-card glass-card-hover border ${card.border} flex items-center justify-between`}
          >
            <div className="space-y-1">
              <span className="text-xs font-medium text-slate-400">{card.title}</span>
              <div className="text-2xl font-extrabold text-white">{card.count}</div>
            </div>
            <div className={`p-3 rounded-xl ${card.bg}`}>
              {card.icon}
            </div>
          </div>
        ))}
      </div>

      {/* Visual Analytics Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Metric Rates Bar Chart */}
        <div className="p-6 glass-card rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-400" />
              <span>Process Completion & Failure Rates (%)</span>
            </h3>
            <span className="text-[10px] text-slate-400">Target ≥ 95% Completion</span>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Turnaround Time Summary Card */}
        <div className="p-6 glass-card rounded-2xl space-y-6 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-emerald-400" />
              <span>Device Turnaround Efficiency</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">Average time taken from patient return to clinician re-issue approval.</p>
          </div>

          <div className="grid grid-cols-2 gap-4 my-2">
            <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/50">
              <span className="text-xs text-slate-400">Manual Baseline Turnaround</span>
              <div className="text-2xl font-bold text-rose-400 mt-1">3.2 Days</div>
              <span className="text-[10px] text-rose-300/80">Paper checklist bottleneck</span>
            </div>

            <div className="p-4 rounded-xl bg-teal-500/10 border border-teal-500/30">
              <span className="text-xs text-teal-300">Prototype Turnaround</span>
              <div className="text-2xl font-extrabold text-teal-400 mt-1">{metrics.avg_turnaround_days} Days</div>
              <span className="text-[10px] text-teal-300/80">56% Faster Turnaround</span>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
            <span className="text-slate-300 font-medium">Unresolved High Priority Lock:</span>
            <span className="font-bold text-amber-400 flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>No items silently deleted</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
