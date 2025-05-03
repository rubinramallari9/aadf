// client/src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { VendorProvider } from './contexts/VendorContext'; // Import VendorProvider

// Import pages
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import AdminDashboard from './pages/AdminDashboard';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import Profile from './pages/auth/Profile';
import ChangePassword from './pages/auth/ChangePassword';
import TenderList from './pages/tenders/TenderList';
import TenderCreate from './pages/tenders/TenderCreate';
import TenderDetail from './pages/tenders/TenderDetail';
import TenderEdit from './pages/tenders/TenderEdit';
import OfferList from './pages/offers/OfferList';
import OfferCreate from './pages/offers/OfferCreate';
import OfferDetail from './pages/offers/OfferDetail';
import OfferEdit from './pages/offers/OfferEdit';
import VendorList from './pages/vendors/VendorList';
import VendorCreate from './pages/vendors/VendorCreate';
import VendorDetail from './pages/vendors/VendorDetail';
import VendorEdit from './pages/vendors/VendorEdit';
import UserList from './pages/users/UserList';
import UserDetail from './pages/users/UserDetail';
import UserCreate from './pages/users/UserCreate';
import UserEdit from './pages/users/UserEdit';
import NotificationList from './pages/notifications/NotificationList';
import EvaluationList from './pages/evaluations/EvaluationList';
import EvaluationDetail from './pages/evaluations/EvaluationDetail';
import RequireAuth from './components/auth/RequireAuth';
import NotFound from './pages/NotFound';

function App() {
  return (
    <Router>
      <AuthProvider>
        <VendorProvider> {/* Wrap with VendorProvider */}
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* Dashboard routes */}
            <Route path="/dashboard" element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            } />
            <Route path="/admin" element={
              <RequireAuth allowedRoles={['admin']}>
                <AdminDashboard />
              </RequireAuth>
            } />
            
            {/* Auth routes */}
            <Route path="/profile" element={
              <RequireAuth>
                <Profile />
              </RequireAuth>
            } />
            <Route path="/change-password" element={
              <RequireAuth>
                <ChangePassword />
              </RequireAuth>
            } />
            
            {/* Tender routes */}
            <Route path="/tenders" element={<TenderList />} />
            <Route path="/tenders/create" element={
              <RequireAuth allowedRoles={['admin', 'staff']}>
                <TenderCreate />
              </RequireAuth>
            } />
            <Route path="/tenders/:id" element={<TenderDetail />} />
            <Route path="/tenders/edit/:id" element={
              <RequireAuth allowedRoles={['admin', 'staff']}>
                <TenderEdit />
              </RequireAuth>
            } />
            
            {/* Offer routes */}
            <Route path="/offers" element={
              <RequireAuth>
                <OfferList />
              </RequireAuth>
            } />
            <Route path="/offers/create" element={
              <RequireAuth allowedRoles={['vendor']}>
                <OfferCreate />
              </RequireAuth>
            } />
            <Route path="/offers/:id" element={
              <RequireAuth>
                <OfferDetail />
              </RequireAuth>
            } />
            <Route path="/offers/edit/:id" element={
              <RequireAuth allowedRoles={['vendor']}>
                <OfferEdit />
              </RequireAuth>
            } />
            
            {/* Vendor routes */}
            <Route path="/vendors" element={
              <RequireAuth allowedRoles={['admin', 'staff']}>
                <VendorList />
              </RequireAuth>
            } />
            <Route path="/vendors/create" element={
              <RequireAuth allowedRoles={['admin']}>
                <VendorCreate />
              </RequireAuth>
            } />
            <Route path="/vendors/:id" element={
              <RequireAuth allowedRoles={['admin', 'staff']}>
                <VendorDetail />
              </RequireAuth>
            } />
            <Route path="/vendors/:id/edit" element={
              <RequireAuth allowedRoles={['admin']}>
                <VendorEdit />
              </RequireAuth>
            } />
            
            {/* User routes */}
            <Route path="/users" element={
              <RequireAuth allowedRoles={['admin']}>
                <UserList />
              </RequireAuth>
            } />
            <Route path="/users/create" element={
              <RequireAuth allowedRoles={['admin']}>
                <UserCreate />
              </RequireAuth>
            } />
            <Route path="/users/:id" element={
              <RequireAuth allowedRoles={['admin']}>
                <UserDetail />
              </RequireAuth>
            } />
            <Route path="/users/:id/edit" element={
              <RequireAuth allowedRoles={['admin']}>
                <UserEdit />
              </RequireAuth>
            } />
            
            {/* Notifications */}
            <Route path="/notifications" element={
              <RequireAuth>
                <NotificationList />
              </RequireAuth>
            } />
            
            {/* Evaluations */}
            <Route path="/evaluations" element={
              <RequireAuth allowedRoles={['evaluator', 'admin', 'staff']}>
                <EvaluationList />
              </RequireAuth>
            } />
            <Route path="/evaluations/:id" element={
              <RequireAuth allowedRoles={['evaluator', 'admin', 'staff']}>
                <EvaluationDetail />
              </RequireAuth>
            } />
            
            {/* Catch all - 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </VendorProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;