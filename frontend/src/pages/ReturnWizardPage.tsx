import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { UserRole } from '../types';
import {
  CheckCircle2, AlertTriangle, ShieldAlert, Cpu, ChevronRight, ChevronLeft,
  Package, ShieldCheck, Sparkles, FileText, CheckSquare, RefreshCw, XCircle, AlertOctagon
} from 'lucide-react';

interface ReturnWizardPageProps {
  currentRole: UserRole;
  onReturnCompleted: () => void;
}

export const ReturnWizardPage: React.FC<ReturnWizardPageProps> = ({ currentRole, onReturnCompleted }) => {
  const [step, setStep] = useState(1);
  const [deviceIdInput, setDeviceIdInput] = useState('');
  const [receivedByInput, setReceivedByInput] = useState('Sarah Connor (Field Staff)');
  const [activeReturn, setActiveReturn] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form states for return checklist
  const [accessoriesList, setAccessoriesList] = useState<any[]>([]);
  const [conditionForm, setConditionForm] = useState({
    exterior: 'Good', screen: 'Good', buttons: 'Functional',
    power: 'Normal', battery: 'Normal', ports: 'Good',
    sensors: 'Functional', physical_cleanliness: 'Clean', notes: ''
  });
  const [patientAckForm, setPatientAckForm] = useState({
    status: 'RECEIVED', method: 'Signed Paper Form', notes: ''
  });
  const [cleaningForm, setCleaningForm] = useState({
    status: 'COMPLETED', notes: ''
  });
  const [evaluationResult, setEvaluationResult] = useState<any>(null);

  // HITL decision states
  const [overrideReason, setOverrideReason] = useState('');
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Step 1: Initiate Return Check-in
  const handleStartReturn = async () => {
    if (!deviceIdInput.trim()) {
      setErrorMsg('Please enter or scan a valid Device ID.');
      return;
    }
    setErrorMsg(null);
    setLoading(true);
    try {
      const res = await api.startReturn(deviceIdInput.trim().toUpperCase(), receivedByInput);
      const details = await api.getReturnDetails(res.return_id);
      setActiveReturn(details);
      setAccessoriesList(details.returned_accessories || []);
      setStep(2);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start return check-in.');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Save Accessories
  const handleSaveAccessories = async () => {
    if (!activeReturn) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      await api.saveAccessories(activeReturn.return_id, accessoriesList);
      setStep(3);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save accessories.');
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Save Condition
  const handleSaveCondition = async () => {
    if (!activeReturn) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      await api.saveCondition(activeReturn.return_id, conditionForm);
      setStep(4);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save condition checklist.');
    } finally {
      setLoading(false);
    }
  };

  // Step 4: Save Patient Ack
  const handleSaveAck = async () => {
    if (!activeReturn) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      await api.saveAcknowledgement(activeReturn.return_id, patientAckForm);
      setStep(5);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save patient acknowledgement.');
    } finally {
      setLoading(false);
    }
  };

  // Step 5: Save Cleaning & Evaluate
  const handleSaveCleaningAndEvaluate = async () => {
    if (!activeReturn) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      await api.saveCleaning(activeReturn.return_id, cleaningForm);
      const evalRes = await api.evaluateReturn(activeReturn.return_id);
      setEvaluationResult(evalRes);
      const updatedDetails = await api.getReturnDetails(activeReturn.return_id);
      setActiveReturn(updatedDetails);
      setStep(6);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to run rule engine evaluation.');
    } finally {
      setLoading(false);
    }
  };

  // Step 7: HITL Confirm or Override
  const handleConfirmRec = async (recId: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      await api.confirmRecommendation(recId, 'Confirmed by clinician review.');
      setActionSuccess('Recommendation confirmed successfully. Audit entry recorded.');
      const updated = await api.getReturnDetails(activeReturn.return_id);
      setActiveReturn(updated);
    } catch (err: any) {
      setErrorMsg(err.message || 'Confirmation failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleOverrideRec = async (recId: string) => {
    if (!overrideReason.trim()) {
      setErrorMsg('Edge Case 9 Validation Error: Mandatory non-empty override reason required to override safety recommendation.');
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      await api.overrideRecommendation(recId, overrideReason);
      setActionSuccess(`Recommendation overridden successfully. Reason logged: "${overrideReason}"`);
      setOverrideReason('');
      const updated = await api.getReturnDetails(activeReturn.return_id);
      setActiveReturn(updated);
    } catch (err: any) {
      setErrorMsg(err.message || 'Override failed.');
    } finally {
      setLoading(false);
    }
  };

  const stepsList = [
    { num: 1, name: 'Identification' },
    { num: 2, name: 'Accessories' },
    { num: 3, name: 'Condition' },
    { num: 4, name: 'Patient Ack' },
    { num: 5, name: 'Cleaning' },
    { num: 6, name: 'Risk Rules' },
    { num: 7, name: 'Human Review' },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Wizard Step Progress Header */}
      <div className="p-4 glass-card rounded-2xl">
        <div className="flex items-center justify-between overflow-x-auto scrollbar-none">
          {stepsList.map((s) => (
            <div key={s.num} className="flex items-center gap-2 min-w-max px-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  step === s.num
                    ? 'bg-teal-500 text-slate-950 shadow-md ring-2 ring-teal-400/50'
                    : step > s.num
                    ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40'
                    : 'bg-slate-800 text-slate-500 border border-slate-700'
                }`}
              >
                {step > s.num ? <CheckCircle2 className="w-4 h-4" /> : s.num}
              </div>
              <span className={`text-xs font-semibold ${step === s.num ? 'text-white' : 'text-slate-400'}`}>
                {s.name}
              </span>
              {s.num < 7 && <ChevronRight className="w-4 h-4 text-slate-700" />}
            </div>
          ))}
        </div>
      </div>

      {/* Error Alert Box */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/40 text-rose-300 text-xs flex items-start gap-3">
          <AlertOctagon className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold">Checklist Validation Alert</span>
            <p>{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Action Success Alert Box */}
      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* STEP 1: Device Identification */}
      {step === 1 && (
        <div className="p-6 glass-card rounded-2xl space-y-6">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Cpu className="w-5 h-5 text-teal-400" />
              <span>Step 1: Device Identification & Check-in</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">Scan or type the unique device barcode / ID to retrieve expected accessory inventory.</p>
          </div>

          <div className="space-y-4 max-w-md">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5">Device ID / Serial Number</label>
              <input
                type="text"
                placeholder="e.g. DEV-001"
                value={deviceIdInput}
                onChange={(e) => setDeviceIdInput(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Try DEV-001 (standard), DEV-002 (damaged), or DEV-003</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5">Receiving Staff Member</label>
              <input
                type="text"
                value={receivedByInput}
                onChange={(e) => setReceivedByInput(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500"
              />
            </div>

            <button
              onClick={handleStartReturn}
              disabled={loading}
              className="w-full py-3 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-teal-500/20 flex items-center justify-center gap-2 transition-all"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <span>Start Return Check-in</span>}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: Accessory Check */}
      {step === 2 && activeReturn && (
        <div className="p-6 glass-card rounded-2xl space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Package className="w-5 h-5 text-teal-400" />
                <span>Step 2: Accessory Reconciliation</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Device: <strong className="text-teal-300">{activeReturn.device_id}</strong> | Check present, missing, or damaged accessories.
              </p>
            </div>
          </div>

          <div className="border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Accessory Name</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Criticality</th>
                  <th className="px-4 py-3 text-center">Expected</th>
                  <th className="px-4 py-3 text-center">Returned Qty</th>
                  <th className="px-4 py-3">Condition Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {accessoriesList.map((acc, idx) => (
                  <tr key={acc.accessory_id} className="hover:bg-slate-800/30">
                    <td className="px-4 py-3 font-semibold text-white">{acc.accessory_name}</td>
                    <td className="px-4 py-3 text-slate-400">{acc.category}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        acc.criticality === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-slate-800 text-slate-400'
                      }`}>
                        {acc.criticality}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center font-bold">{acc.expected_quantity}</td>
                    <td className="px-4 py-3 text-center">
                      <input
                        type="number"
                        min="0"
                        value={acc.returned_quantity}
                        onChange={(e) => {
                          const val = parseInt(e.target.value) || 0;
                          const updated = [...accessoriesList];
                          updated[idx].returned_quantity = val;
                          if (val < acc.expected_quantity) updated[idx].condition = 'MISSING';
                          else if (val > acc.expected_quantity) updated[idx].condition = 'PRESENT';
                          setAccessoriesList(updated);
                        }}
                        className="w-16 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-center font-bold text-white focus:outline-none focus:border-teal-500"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={acc.condition}
                        onChange={(e) => {
                          const updated = [...accessoriesList];
                          updated[idx].condition = e.target.value;
                          setAccessoriesList(updated);
                        }}
                        className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-teal-500"
                      >
                        <option value="PRESENT">PRESENT</option>
                        <option value="MISSING">MISSING</option>
                        <option value="DAMAGED">DAMAGED</option>
                        <option value="UNKNOWN">UNKNOWN</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex justify-between items-center pt-2">
            <button onClick={() => setStep(1)} className="px-4 py-2 bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl hover:bg-slate-700">
              Back
            </button>
            <button onClick={handleSaveAccessories} disabled={loading} className="px-5 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold rounded-xl flex items-center gap-2">
              <span>Save & Continue to Condition</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Condition Checklist */}
      {step === 3 && (
        <div className="p-6 glass-card rounded-2xl space-y-6">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-teal-400" />
              <span>Step 3: Return Condition Checklist</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">Assess physical hardware integrity, display screen, power, and sensors.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Exterior Casing</label>
              <select
                value={conditionForm.exterior}
                onChange={(e) => setConditionForm({ ...conditionForm, exterior: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="Good">Good</option>
                <option value="Minor damage">Minor damage</option>
                <option value="Major damage">Major damage</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Display Screen</label>
              <select
                value={conditionForm.screen}
                onChange={(e) => setConditionForm({ ...conditionForm, screen: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="Good">Good</option>
                <option value="Cracked">Cracked</option>
                <option value="Not functioning">Not functioning</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Buttons / Keypad</label>
              <select
                value={conditionForm.buttons}
                onChange={(e) => setConditionForm({ ...conditionForm, buttons: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="Functional">Functional</option>
                <option value="Partially functional">Partially functional</option>
                <option value="Not functional">Not functional</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Power System</label>
              <select
                value={conditionForm.power}
                onChange={(e) => setConditionForm({ ...conditionForm, power: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="Normal">Normal</option>
                <option value="Charging issue">Charging issue</option>
                <option value="Does not power on">Does not power on</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Sensors / Probes</label>
              <select
                value={conditionForm.sensors}
                onChange={(e) => setConditionForm({ ...conditionForm, sensors: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="Functional">Functional</option>
                <option value="Damaged">Damaged</option>
                <option value="Unknown">Unknown</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Physical Cleanliness</label>
              <select
                value={conditionForm.physical_cleanliness}
                onChange={(e) => setConditionForm({ ...conditionForm, physical_cleanliness: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="Clean">Clean</option>
                <option value="Needs cleaning">Needs cleaning</option>
                <option value="Contaminated/uncertain">Contaminated/uncertain</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">Field Inspection Notes</label>
            <textarea
              rows={2}
              placeholder="Add physical condition notes or details..."
              value={conditionForm.notes}
              onChange={(e) => setConditionForm({ ...conditionForm, notes: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-white"
            />
          </div>

          <div className="flex justify-between items-center pt-2">
            <button onClick={() => setStep(2)} className="px-4 py-2 bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl">Back</button>
            <button onClick={handleSaveCondition} disabled={loading} className="px-5 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold rounded-xl flex items-center gap-2">
              <span>Save & Continue to Patient Ack</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: Patient Acknowledgement */}
      {step === 4 && (
        <div className="p-6 glass-card rounded-2xl space-y-6">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-teal-400" />
              <span>Step 4: Patient Acknowledgement Verification</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">Log receipt of signed return form or verbal confirmation.</p>
          </div>

          <div className="space-y-4 max-w-md">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Acknowledgement Status</label>
              <select
                value={patientAckForm.status}
                onChange={(e) => setPatientAckForm({ ...patientAckForm, status: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="RECEIVED">RECEIVED (Acknowledgement attached)</option>
                <option value="MISSING">MISSING (Follow-up task will be generated)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Method of Acknowledgement</label>
              <select
                value={patientAckForm.method}
                onChange={(e) => setPatientAckForm({ ...patientAckForm, method: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="Signed Paper Form">Signed Paper Form</option>
                <option value="Digital Signature">Digital Signature</option>
                <option value="Verbal Phone Confirmation">Verbal Phone Confirmation</option>
              </select>
            </div>

            <button onClick={handleSaveAck} disabled={loading} className="w-full py-3 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl flex items-center justify-center gap-2">
              <span>Save & Continue to Cleaning Verification</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: Cleaning Verification */}
      {step === 5 && (
        <div className="p-6 glass-card rounded-2xl space-y-6">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-teal-400" />
              <span>Step 5: Cleaning & Sanitisation Status</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">Medical sanitisation verification before device re-issue.</p>
          </div>

          <div className="space-y-4 max-w-md">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Sanitisation Protocol Status</label>
              <select
                value={cleaningForm.status}
                onChange={(e) => setCleaningForm({ ...cleaningForm, status: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="COMPLETED">COMPLETED (Decontaminated)</option>
                <option value="PENDING">PENDING (Requires sanitisation batch)</option>
                <option value="FAILED_UNCERTAIN">FAILED / UNCERTAIN (Quarantine mandatory)</option>
              </select>
            </div>

            <button onClick={handleSaveCleaningAndEvaluate} disabled={loading} className="w-full py-3 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl flex items-center justify-center gap-2">
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <span>Run Rule Engine Evaluation & View Recommendations</span>}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 6: Risk & Rule Engine Breakdown */}
      {step === 6 && activeReturn && (
        <div className="p-6 glass-card rounded-2xl space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-teal-400" />
                <span>Step 6: Transparent Risk & Rule Engine Evaluation</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">System rules evaluated for return ID: {activeReturn.return_id}</p>
            </div>

            <div className={`px-4 py-2 rounded-xl border text-xs font-extrabold flex items-center gap-2 ${
              activeReturn.overall_risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' :
              activeReturn.overall_risk_level === 'HIGH' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' :
              activeReturn.overall_risk_level === 'MEDIUM' ? 'bg-orange-500/20 text-orange-300 border-orange-500/40' :
              'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
            }`}>
              <ShieldAlert className="w-4 h-4" />
              <span>Overall Risk Level: {activeReturn.overall_risk_level}</span>
            </div>
          </div>

          {/* Triggered Rules Breakdown */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Triggered Safety Rules & Recommendations</h4>
            {activeReturn.recommendations.map((rec: any) => (
              <div key={rec.recommendation_id} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-teal-300">{rec.rule_id || 'RULE-07'} - {rec.rule_name}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    rec.risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-amber-500/20 text-amber-300'
                  }`}>
                    {rec.risk_level} RISK
                  </span>
                </div>
                <p className="text-xs text-white font-medium">{rec.recommendation}</p>
                <div className="text-[11px] text-slate-400 bg-slate-950 p-2 rounded-lg">
                  <strong>Required Human Action:</strong> {rec.required_human_action}
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center pt-2">
            <button onClick={() => setStep(5)} className="px-4 py-2 bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl">Back</button>
            <button onClick={() => setStep(7)} className="px-5 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold rounded-xl flex items-center gap-2">
              <span>Proceed to Human Review & Decision</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 7: Human-in-the-Loop Review & Decision */}
      {step === 7 && activeReturn && (
        <div className="p-6 glass-card rounded-2xl space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-teal-400" />
                <span>Step 7: Mandatory Human-in-the-Loop Review</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">Authorised staff review requirement. System will NOT auto-release without human decision.</p>
            </div>
          </div>

          <div className="space-y-4">
            {activeReturn.recommendations.map((rec: any) => (
              <div key={rec.recommendation_id} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-extrabold text-teal-300">{rec.rule_id} Recommendation</span>
                    <h4 className="text-sm font-bold text-white mt-1">{rec.recommendation}</h4>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                    rec.status === 'CONFIRMED' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                    rec.status === 'OVERRIDDEN' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40' :
                    'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  }`}>
                    STATUS: {rec.status}
                  </span>
                </div>

                {rec.status === 'PENDING' ? (
                  <div className="space-y-3 pt-2 border-t border-slate-800">
                    <div className="flex flex-col sm:flex-row gap-3">
                      <button
                        onClick={() => handleConfirmRec(rec.recommendation_id)}
                        disabled={loading}
                        className="px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs rounded-xl flex items-center justify-center gap-2"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Confirm System Recommendation</span>
                      </button>

                      <div className="flex-1 space-y-2">
                        <input
                          type="text"
                          placeholder="Compulsory override justification reason..."
                          value={overrideReason}
                          onChange={(e) => setOverrideReason(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                        />
                        <button
                          onClick={() => handleOverrideRec(rec.recommendation_id)}
                          disabled={loading}
                          className="w-full py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2"
                        >
                          <AlertTriangle className="w-4 h-4" />
                          <span>Override System Recommendation</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-xl bg-slate-950 text-xs text-slate-300 space-y-1">
                    <span className="font-bold text-slate-400">Review Decision Trail:</span>
                    {rec.decisions && rec.decisions.map((d: any) => (
                      <div key={d.decision_id} className="text-slate-300">
                        • Decision: <strong className="text-white">{d.decision}</strong> | Reason: "{d.override_reason}" ({new Date(d.timestamp).toLocaleString()})
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="pt-4 flex items-center justify-between">
            <button onClick={() => setStep(6)} className="px-4 py-2 bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl">Back</button>
            <button
              onClick={onReturnCompleted}
              className="px-6 py-3 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-teal-500/20"
            >
              Finish Return Checklist & Return to Dashboard
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
