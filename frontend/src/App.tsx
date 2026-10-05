import React, { useState } from 'react';
import { UserRole } from './types';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { ReturnWizardPage } from './pages/ReturnWizardPage';
import { HumanReviewQueuePage } from './pages/HumanReviewQueuePage';
import { TasksEscalationPage } from './pages/TasksEscalationPage';
import { DeviceIssuesPage } from './pages/DeviceIssuesPage';
import { DeviceInventoryPage } from './pages/DeviceInventoryPage';
import { AuditLogPage } from './pages/AuditLogPage';
import { ExperimentPage } from './pages/ExperimentPage';
import { ErrorBoundary } from './components/ErrorBoundary';

export function App() {
  const [currentRole, setCurrentRole] = useState<UserRole>('field_staff');
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-teal-500 selection:text-white">
      <Navbar
        currentRole={currentRole}
        onRoleChange={(r) => setCurrentRole(r)}
        activeTab={activeTab}
        setActiveTab={(tab) => setActiveTab(tab)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <ErrorBoundary fallbackTitle="Field Operations Display Notice" onReset={() => setActiveTab('dashboard')}>
          {activeTab === 'dashboard' && <DashboardPage onNavigate={(tab) => setActiveTab(tab)} />}
          {activeTab === 'return-wizard' && (
            <ReturnWizardPage
              currentRole={currentRole}
              onReturnCompleted={() => setActiveTab('dashboard')}
            />
          )}
          {activeTab === 'review-queue' && <HumanReviewQueuePage currentRole={currentRole} />}
          {activeTab === 'tasks-escalation' && <TasksEscalationPage currentRole={currentRole} />}
          {activeTab === 'device-issues' && <DeviceIssuesPage />}
          {activeTab === 'inventory' && <DeviceInventoryPage />}
          {activeTab === 'experiment' && <ExperimentPage />}
          {activeTab === 'audit-logs' && <AuditLogPage />}
        </ErrorBoundary>
      </main>

      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        Rural Health Loan-Device Return & Reconciliation System • HITL Governance Active • Healthcare Field Prototype MVP
      </footer>
    </div>
  );
}

export default App;
