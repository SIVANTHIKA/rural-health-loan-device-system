import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { FollowUpTask, UserRole } from '../types';
import { ShieldAlert, Clock, CheckCircle2, UserCheck, AlertTriangle, RefreshCw } from 'lucide-react';

interface TasksEscalationPageProps {
  currentRole: UserRole;
}

export const TasksEscalationPage: React.FC<TasksEscalationPageProps> = ({ currentRole }) => {
  const [tasks, setTasks] = useState<FollowUpTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [selectedTask, setSelectedTask] = useState<FollowUpTask | null>(null);
  const [resolutionText, setResolutionText] = useState('');

  useEffect(() => {
    loadTasks();
  }, [statusFilter, priorityFilter]);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const data = await api.getFollowUps(statusFilter || undefined, priorityFilter || undefined);
      setTasks(data || []);
    } catch (err) {
      console.error('Failed to load follow-up tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleResolveTask = async (taskId: string) => {
    if (!resolutionText.trim()) return;
    try {
      await api.updateFollowUp(taskId, {
        status: 'RESOLVED',
        resolution: resolutionText.trim()
      });
      setSelectedTask(null);
      setResolutionText('');
      loadTasks();
    } catch (err) {
      console.error('Failed to resolve task:', err);
    }
  };

  const handleEscalate = async (taskId: string) => {
    try {
      await api.escalateTask(taskId);
      loadTasks();
    } catch (err) {
      console.error('Failed to escalate task:', err);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header & Filter Controls */}
      <div className="p-6 glass-card rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-teal-400" />
            <span>Follow-up Tasks & Escalation Management</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Unresolved high-priority issues NEVER disappear from the queue until formally resolved by authorised personnel.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="IN_PROGRESS">IN_PROGRESS</option>
            <option value="ESCALATED">ESCALATED</option>
            <option value="RESOLVED">RESOLVED</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white"
          >
            <option value="">All Priorities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12 text-teal-400">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          <span>Loading follow-up tasks and escalation queue...</span>
        </div>
      ) : (
        <div className="border border-slate-800 rounded-2xl glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Task ID / Device</th>
                  <th className="px-4 py-3">Issue Type & Description</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Assigned Owner</th>
                  <th className="px-4 py-3">Due Date</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {tasks.map((task) => {
                  const isOverdue = new Date(task.due_date) < new Date() && task.status !== 'RESOLVED' && task.status !== 'CLOSED';
                  return (
                    <tr key={task.task_id} className={`hover:bg-slate-800/30 ${task.escalation_level > 0 ? 'bg-amber-500/5' : ''}`}>
                      <td className="px-4 py-3.5 font-bold text-white">
                        <div>{task.task_id}</div>
                        <span className="text-[10px] text-teal-300 font-normal">{task.device_id}</span>
                      </td>

                      <td className="px-4 py-3.5 max-w-xs space-y-0.5">
                        <div className="font-semibold text-white">{task.issue_type}</div>
                        <p className="text-[11px] text-slate-400 line-clamp-2">{task.description}</p>
                      </td>

                      <td className="px-4 py-3.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold ${
                          task.priority === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                          task.priority === 'HIGH' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                          'bg-slate-800 text-slate-400'
                        }`}>
                          {task.priority}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 text-slate-300 font-medium">
                        {task.assigned_to}
                      </td>

                      <td className="px-4 py-3.5">
                        <div className={`flex items-center gap-1 font-semibold ${isOverdue ? 'text-rose-400 font-bold' : 'text-slate-300'}`}>
                          <Clock className="w-3.5 h-3.5" />
                          <span>{new Date(task.due_date).toLocaleDateString()}</span>
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold flex items-center w-max gap-1 ${
                          task.status === 'ESCALATED' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse' :
                          task.status === 'RESOLVED' ? 'bg-emerald-500/20 text-emerald-300' :
                          'bg-slate-800 text-slate-300'
                        }`}>
                          {task.status}
                          {task.escalation_level > 0 && <span>(Level {task.escalation_level})</span>}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 text-right space-x-2">
                        {task.status !== 'RESOLVED' && task.status !== 'CLOSED' && (
                          <>
                            <button
                              onClick={() => setSelectedTask(task)}
                              className="px-2.5 py-1 bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 rounded text-[11px] font-bold"
                            >
                              Resolve
                            </button>
                            {task.escalation_level === 0 && (
                              <button
                                onClick={() => handleEscalate(task.task_id)}
                                className="px-2.5 py-1 bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 rounded text-[11px] font-bold"
                              >
                                Escalate
                              </button>
                            )}
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Resolution Dialog Modal */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4">
            <h3 className="text-base font-bold text-white">Resolve Task: {selectedTask.task_id}</h3>
            <p className="text-xs text-slate-400">{selectedTask.description}</p>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Resolution Summary</label>
              <textarea
                rows={3}
                placeholder="Detail resolution steps completed..."
                value={resolutionText}
                onChange={(e) => setResolutionText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-teal-500"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button onClick={() => setSelectedTask(null)} className="px-4 py-2 bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl">Cancel</button>
              <button onClick={() => handleResolveTask(selectedTask.task_id)} className="px-4 py-2 bg-teal-500 text-slate-950 text-xs font-bold rounded-xl">Confirm Resolution</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
