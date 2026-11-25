import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '../routes/ProtectedRoute';
import { AppLayout } from '../layouts/AppLayout';

import { LoginPage } from '../pages/auth/LoginPage';
import { RegisterTrainerPage } from '../pages/auth/RegisterTrainerPage';

import { TrainerDashboardPage } from '../pages/trainer/DashboardPage';
import { ClientsPage } from '../pages/trainer/ClientsPage';
import { ClientDetailPage } from '../pages/trainer/ClientDetailPage';
import { AttendancePage } from '../pages/trainer/AttendancePage';
import { FeesPage } from '../pages/trainer/FeesPage';
import { WorkoutsPage } from '../pages/trainer/WorkoutsPage';
import { ExercisesPage } from '../pages/trainer/ExercisesPage';
import { NotificationsPage } from '../pages/NotificationsPage';

export const AppRouter: React.FC = () => {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register-trainer" element={<RegisterTrainerPage />} />
      <Route path="/setup" element={<RegisterTrainerPage />} />

      {/* Trainer app */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<TrainerDashboardPage />} />
        <Route path="clients" element={<ClientsPage />} />
        <Route path="clients/:id" element={<ClientDetailPage />} />
        <Route path="attendance" element={<AttendancePage />} />
        <Route path="fees" element={<FeesPage />} />
        <Route path="workouts" element={<WorkoutsPage />} />
        <Route path="exercises" element={<ExercisesPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        {/* Old bookmarks */}
        <Route path="exercise-log" element={<Navigate to="/workouts" replace />} />
        <Route path="sessions" element={<Navigate to="/workouts" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};
