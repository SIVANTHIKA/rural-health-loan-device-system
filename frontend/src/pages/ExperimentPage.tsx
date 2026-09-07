import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { BarChart3, CheckCircle2, AlertOctagon, TrendingUp, RefreshCw } from 'lucide-react';

export const ExperimentPage: React.FC = () => {
  const [experimentData, setExperimentData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadExperiment();
  }, []);

  const loadExperiment = async () => {
    setLoading(true);
    try {
      const data = await api.getExperimentAnalytics();
      setExperimentData(data);
    } catch (err) {
      console.error('Failed to load experiment data:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !experimentData) {
    return (
      <div className="flex items-center justify-center min-h-[400px] text-teal-400">
        <RefreshCw className="w-6 h-6 animate-spin mr-2" />
        <span>Loading baseline experiment analytics...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header Banner */}
      <div className="p-6 glass-card rounded-2xl space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-teal-400" />
            <span>Baseline vs Prototype Experimental Evaluation</span>
          </h2>
          <span className="px-3 py-1 bg-teal-500/20 text-teal-300 border border-teal-500/40 rounded-full text-xs font-bold">
            Simulated 100 Return Evaluation Dataset
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Comparing historical manual return checklist workflow against prototype-assisted device return system.
        </p>
      </div>

      {/* Quantitative Before vs After Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span>Before / After Quantitative Metric Comparison</span>
          </h3>
          <span className="text-[11px] text-slate-400 font-medium">REAL MEASURED RESULT / SIMULATED DEMO</span>
        </div>

        <div className="border border-slate-800 rounded-2xl glass-card overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5">Metric</th>
                <th className="px-4 py-3.5 text-center">Baseline (Manual)</th>
                <th className="px-4 py-3.5 text-center">Configured Target</th>
                <th className="px-4 py-3.5 text-center">Measured Prototype</th>
                <th className="px-4 py-3.5 text-right">Net Improvement</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {experimentData.comparison_table.map((row: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-800/30">
                  <td className="px-4 py-3.5 font-bold text-white">{row.metric}</td>
                  <td className="px-4 py-3.5 text-center font-semibold text-rose-400">{row.baseline}</td>
                  <td className="px-4 py-3.5 text-center font-semibold text-slate-400">{row.target}</td>
                  <td className="px-4 py-3.5 text-center font-extrabold text-teal-400">{row.measured_prototype}</td>
                  <td className="px-4 py-3.5 text-right font-extrabold text-emerald-400">{row.improvement}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Error Analysis Matrix */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <AlertOctagon className="w-4 h-4 text-amber-400" />
            <span>Categorised Error Analysis & Root Cause Matrix</span>
          </h3>
          <span className="text-[11px] text-slate-400 font-medium">10 Error Categories Evaluated</span>
        </div>

        <div className="border border-slate-800 rounded-2xl glass-card overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5">Error Type</th>
                <th className="px-4 py-3.5 text-center">Count (%)</th>
                <th className="px-4 py-3.5">System Impact</th>
                <th className="px-4 py-3.5">Identified Root Cause</th>
                <th className="px-4 py-3.5">Corrective Action Taken</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {experimentData.error_analysis.map((errItem: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-800/30">
                  <td className="px-4 py-3.5 font-bold text-amber-300">{errItem.error_type}</td>
                  <td className="px-4 py-3.5 text-center font-bold text-white">{errItem.count} ({errItem.percentage})</td>
                  <td className="px-4 py-3.5 text-slate-300 max-w-xs">{errItem.impact}</td>
                  <td className="px-4 py-3.5 text-slate-400 max-w-xs">{errItem.root_cause}</td>
                  <td className="px-4 py-3.5 text-teal-300 max-w-xs">{errItem.corrective_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
