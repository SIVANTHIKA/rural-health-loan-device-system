import {
  DashboardMetrics, FollowUpTask, DeviceReturnDetails,
  Recommendation, AuditLogItem
} from '../types';

const API_BASE = '/api';

export const api = {
  // Auth
  login: async (username: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Login failed');
    }
    return res.json();
  },

  // Devices & Issues
  getDevices: async (query?: string, status?: string) => {
    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (status) params.append('status', status);
    const res = await fetch(`${API_BASE}/devices?${params.toString()}`);
    return res.json();
  },

  getDeviceById: async (deviceId: string) => {
    const res = await fetch(`${API_BASE}/devices/${deviceId}`);
    if (!res.ok) throw new Error('Device not found');
    return res.json();
  },

  getIssueRecords: async (query?: string, status?: string) => {
    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (status) params.append('status', status);
    const res = await fetch(`${API_BASE}/issue-records?${params.toString()}`);
    return res.json();
  },

  // Returns
  getAllReturns: async (status?: string) => {
    const url = status ? `${API_BASE}/returns?status=${status}` : `${API_BASE}/returns`;
    const res = await fetch(url);
    return res.json();
  },

  startReturn: async (deviceId: string, receivedBy: string, issueId?: string) => {
    const res = await fetch(`${API_BASE}/returns`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_id: deviceId, received_by: receivedBy, issue_id: issueId })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to start return');
    }
    return res.json();
  },

  getReturnDetails: async (returnId: string): Promise<DeviceReturnDetails> => {
    const res = await fetch(`${API_BASE}/returns/${returnId}`);
    if (!res.ok) throw new Error('Return record not found');
    return res.json();
  },

  saveAccessories: async (returnId: string, items: any[]) => {
    const res = await fetch(`${API_BASE}/returns/${returnId}/accessories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items })
    });
    return res.json();
  },

  saveCondition: async (returnId: string, conditionData: any) => {
    const res = await fetch(`${API_BASE}/returns/${returnId}/condition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(conditionData)
    });
    return res.json();
  },

  saveAcknowledgement: async (returnId: string, ackData: any) => {
    const res = await fetch(`${API_BASE}/returns/${returnId}/acknowledgement`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ackData)
    });
    return res.json();
  },

  saveCleaning: async (returnId: string, cleaningData: any) => {
    const res = await fetch(`${API_BASE}/returns/${returnId}/cleaning`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cleaningData)
    });
    return res.json();
  },

  evaluateReturn: async (returnId: string) => {
    const res = await fetch(`${API_BASE}/returns/${returnId}/evaluate`, {
      method: 'POST'
    });
    return res.json();
  },

  // Recommendations & Review (HITL)
  getPendingReviews: async () => {
    const res = await fetch(`${API_BASE}/recommendations/pending`);
    return res.json();
  },

  confirmRecommendation: async (recId: string, notes?: string) => {
    const res = await fetch(`${API_BASE}/recommendations/${recId}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Confirmation failed');
    }
    return res.json();
  },

  overrideRecommendation: async (recId: string, overrideReason: string, notes?: string) => {
    const res = await fetch(`${API_BASE}/recommendations/${recId}/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ override_reason: overrideReason, notes })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Override failed');
    }
    return res.json();
  },

  // Follow-up Tasks & Escalation
  getFollowUps: async (status?: string, priority?: string, escalatedOnly?: boolean): Promise<FollowUpTask[]> => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (priority) params.append('priority', priority);
    if (escalatedOnly) params.append('escalated_only', 'true');
    const res = await fetch(`${API_BASE}/follow-ups?${params.toString()}`);
    return res.json();
  },

  updateFollowUp: async (taskId: string, updateData: any) => {
    const res = await fetch(`${API_BASE}/follow-ups/${taskId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updateData)
    });
    return res.json();
  },

  escalateTask: async (taskId: string) => {
    const res = await fetch(`${API_BASE}/follow-ups/${taskId}/escalate`, {
      method: 'POST'
    });
    return res.json();
  },

  // Dashboard & Metrics
  getDashboardMetrics: async (): Promise<DashboardMetrics> => {
    const res = await fetch(`${API_BASE}/dashboard/metrics`);
    return res.json();
  },

  getExperimentAnalytics: async () => {
    const res = await fetch(`${API_BASE}/dashboard/experiment`);
    return res.json();
  },

  // Audit Logs
  getAuditLogs: async (action?: string, entity?: string): Promise<AuditLogItem[]> => {
    const params = new URLSearchParams();
    if (action) params.append('action', action);
    if (entity) params.append('entity', entity);
    const res = await fetch(`${API_BASE}/audit-logs?${params.toString()}`);
    return res.json();
  }
};
