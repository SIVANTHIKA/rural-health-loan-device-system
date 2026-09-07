import React from 'react';
import { UserRole } from '../types';
import { RoleSwitcher } from './RoleSwitcher';
import { Activity, ShieldCheck, RefreshCw, BarChart2, CheckSquare, Layers, ShieldAlert, Cpu } from 'lucide-react';

interface NavbarProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentRole, onRoleChange, activeTab, setActiveTab }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <Activity className="w-4 h-4" /> },
    { id: 'return-wizard', label: 'Start Return', icon: <CheckSquare className="w-4 h-4" /> },
    { id: 'review-queue', label: 'Human Review Queue', icon: <ShieldCheck className="w-4 h-4" /> },
    { id: 'tasks-escalation', label: 'Follow-ups & Escalation', icon: <ShieldAlert className="w-4 h-4" /> },
    { id: 'device-issues', label: 'Device Issues', icon: <Layers className="w-4 h-4" /> },
    { id: 'inventory', label: 'Device Inventory', icon: <Cpu className="w-4 h-4" /> },
    { id: 'experiment', label: 'Baseline & Experiment', icon: <BarChart2 className="w-4 h-4" /> },
    { id: 'audit-logs', label: 'Audit Trail', icon: <RefreshCw className="w-4 h-4" /> },
  ];

  return (
    <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between py-3 gap-3">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="p-2 bg-teal-500/10 border border-teal-500/30 rounded-xl text-teal-400">
              <Activity className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-white tracking-tight">Rural Health Return Checklist</h1>
                <span className="text-[10px] uppercase tracking-wider font-extrabold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  HITL Safety Active
                </span>
              </div>
              <p className="text-xs text-slate-400">Accessory Reconciliation & Device Safety System</p>
            </div>
          </div>

          {/* Role Switcher */}
          <RoleSwitcher currentRole={currentRole} onRoleChange={onRoleChange} />
        </div>

        {/* Tab Navigation */}
        <nav className="flex space-x-1 overflow-x-auto pb-2 scrollbar-none">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
