import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { UserRole } from '../types';
import { ShieldCheck, CheckCircle2, AlertTriangle, RefreshCw, AlertOctagon } from 'lucide-react';

interface HumanReviewQueuePageProps {
  currentRole: UserRole;
}

export const HumanReviewQueuePage: React.FC<HumanReviewQueuePageProps> = ({ currentRole }) => {
  const [reviews, setReviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRec, setSelectedRec] = useState<any | null>(null);
  const [overrideReason, setOverrideReason] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadPendingReviews();
  }, []);

  const loadPendingReviews = async () => {
    setLoading(true);
    try {
      const data = await api.getPendingReviews();
      setReviews(data || []);
    } catch (err) {
      console.error('Failed to load pending reviews:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (recId: string) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await api.confirmRecommendation(recId, 'Clinician confirmed system recommendation.');
      setSuccessMsg(`Recommendation '${recId}' confirmed successfully.`);
      setSelectedRec(null);
      loadPendingReviews();
    } catch (err: any) {
      setErrorMsg(err.message || 'Confirmation failed.');
    }
  };

  const handleOverride = async (recId: string) => {
    if (!overrideReason.trim()) {
      setErrorMsg('Edge Case 9 Validation Error: Compulsory non-empty override justification reason required.');
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await api.overrideRecommendation(recId, overrideReason);
      setSuccessMsg(`Recommendation '${recId}' overridden. Reason: "${overrideReason}"`);
      setOverrideReason('');
      setSelectedRec(null);
      loadPendingReviews();
    } catch (err: any) {
      setErrorMsg(err.message || 'Override failed.');
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="p-6 glass-card rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-teal-400" />
            <span>Clinician / Authorised Human Review Queue</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Governance dashboard enforcing Human-in-the-Loop decision control. Autonomous release is strictly prohibited.
          </p>
        </div>
        <button
          onClick={loadPendingReviews}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh Queue</span>
        </button>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/40 text-rose-300 text-xs flex items-start gap-3">
          <AlertOctagon className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center p-12 text-teal-400">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          <span>Loading pending clinician reviews...</span>
        </div>
      ) : reviews.length === 0 ? (
        <div className="p-12 glass-card rounded-2xl text-center space-y-3">
          <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
          <h3 className="text-base font-bold text-white">Review Queue Clean</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            All flagged return recommendations have been reviewed and approved by authorised clinicians.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reviews.map((r) => (
            <div key={r.recommendation_id} className="p-5 glass-card rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-teal-300">Device: {r.device_id} ({r.device_type})</span>
                  <span className={`px-2.5 py-0.5 rounded text-[10px] font-extrabold ${
                    r.risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                    r.risk_level === 'HIGH' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                    'bg-cyan-500/20 text-cyan-300'
                  }`}>
                    {r.risk_level} RISK
                  </span>
                </div>

                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-white">{r.rule_name}</h4>
                  <p className="text-xs text-slate-300 bg-slate-900/80 p-3 rounded-xl border border-slate-800">{r.recommendation}</p>
                </div>

                <div className="text-[11px] text-slate-400 space-y-1">
                  <div><strong>Evidence:</strong> {r.evidence_description}</div>
                  <div><strong>Required Action:</strong> {r.required_human_action}</div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleConfirm(r.recommendation_id)}
                    className="py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 shadow-md shadow-emerald-500/20"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>CONFIRM</span>
                  </button>

                  <button
                    onClick={() => setSelectedRec(selectedRec?.recommendation_id === r.recommendation_id ? null : r)}
                    className="py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 shadow-md shadow-purple-500/20"
                  >
                    <AlertTriangle className="w-4 h-4" />
                    <span>OVERRIDE</span>
                  </button>
                </div>

                {selectedRec?.recommendation_id === r.recommendation_id && (
                  <div className="p-3 bg-slate-950 rounded-xl border border-purple-500/40 space-y-2">
                    <label className="text-[11px] font-bold text-purple-300 block">Required Non-empty Override Justification:</label>
                    <input
                      type="text"
                      placeholder="Specify clinically valid reason for overriding..."
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
                    />
                    <button
                      onClick={() => handleOverride(r.recommendation_id)}
                      className="w-full py-1.5 bg-purple-500 text-white text-xs font-bold rounded-lg"
                    >
                      Submit Override Sign-Off
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
