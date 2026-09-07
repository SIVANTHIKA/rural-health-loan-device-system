import React from 'react';
import { UserRole } from '../types';
import { UserCheck, Stethoscope, ShieldAlert, ShieldCheck } from 'lucide-react';

interface RoleSwitcherProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
}

export const RoleSwitcher: React.FC<RoleSwitcherProps> = ({ currentRole, onRoleChange }) => {
  const roles: { role: UserRole; label: string; icon: React.ReactNode; color: string }[] = [
    { role: 'field_staff', label: 'Field Staff', icon: <UserCheck className="w-4 h-4" />, color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
    { role: 'clinician', label: 'Clinician / Reviewer', icon: <Stethoscope className="w-4 h-4" />, color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40' },
    { role: 'ops_manager', label: 'Ops Manager', icon: <ShieldAlert className="w-4 h-4" />, color: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
    { role: 'admin', label: 'Administrator', icon: <ShieldCheck className="w-4 h-4" />, color: 'bg-purple-500/20 text-purple-300 border-purple-500/40' },
  ];

  return (
    <div className="flex items-center gap-1.5 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800">
      <span className="text-xs font-semibold text-slate-400 px-2 uppercase tracking-wider hidden sm:inline">Active Role:</span>
      <div className="flex flex-wrap gap-1">
        {roles.map((r) => {
          const isActive = currentRole === r.role;
          return (
            <button
              key={r.role}
              onClick={() => onRoleChange(r.role)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all border ${
                isActive
                  ? `${r.color} shadow-lg ring-1 ring-teal-500/50`
                  : 'bg-slate-800/60 text-slate-400 border-transparent hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              {r.icon}
              <span>{r.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
