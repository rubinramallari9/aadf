// client/src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { VendorProvider } from './contexts/VendorContext';

// Import pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import Dashboard from './pages/Dashboard';

// Import tender pages
import TenderList from './pages/tenders/TenderList';
import TenderDetail from './pages/tenders/TenderDetail';
import TenderCreate from './pages/tenders/TenderCreate';
import TenderEdit from './pages/tenders/TenderEdit';
import TenderSearch from './pages/tenders/TenderSearch';

// Import offer pages
import OfferList from './pages/offers/OfferList';
import OfferCreate from './pages/offers/OfferCreate'; // Import the new component
import Home from './pages/Home';

// Import vendor pages
import VendorList from './pages/vendors/VendorList';
import VendorDetail from './pages/vendors/VendorDetail';
import VendorCreate from './pages/vendors/VendorCreate';
import VendorEdit from './pages/vendors/VendorEdit';
import Notifications from './pages/Notifications';

// Define a protected route component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isLoading } = useAuth();

  // If auth is still loading, show a loading indicator
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
      </div>
    );
  }

  // If not authenticated, redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // If authenticated, render the children
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <Router>
      <AuthProvider>
        <VendorProvider>
          <Routes>
            {/* Auth Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* Protected Routes */}
            <Route 
              path="/dashboard" 
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              } 
            />

            {/* Tender Routes */}
            <Route 
              path="/tenders" 
              element={
                <ProtectedRoute>
                  <TenderList />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/tenders/search" 
              element={
                <ProtectedRoute>
                  <TenderSearch />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/tenders/create" 
              element={
                <ProtectedRoute>
                  <TenderCreate />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/tenders/:id" 
              element={
                <ProtectedRoute>
                  <TenderDetail />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/tenders/:id/edit" 
              element={
                <ProtectedRoute>
                  <TenderEdit />
                </ProtectedRoute>
              } 
            />


            <Route 
              path="/notifications" 
              element={
                <ProtectedRoute>
                  <Notifications />
                </ProtectedRoute>
              } 
            />

            {/* Offer Routes */}
            <Route 
              path="/offers" 
              element={
                <ProtectedRoute>
                  <OfferList />
                </ProtectedRoute>
              } 
            />
            {/* Add the new OfferCreate route */}
            <Route 
              path="/offers/create" 
              element={
                <ProtectedRoute>
                  <OfferCreate />
                </ProtectedRoute>
              } 
            />
            
            {/* Vendor Routes */}
            <Route 
              path="/vendors" 
              element={
                <ProtectedRoute>
                  <VendorList />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/vendors/create" 
              element={
                <ProtectedRoute>
                  <VendorCreate />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/vendors/:id" 
              element={
                <ProtectedRoute>
                  <VendorDetail />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/vendors/:id/edit" 
              element={
                <ProtectedRoute>
                  <VendorEdit />
                </ProtectedRoute>
              } 
            />
            
            {/* Redirect root to dashboard or login */}
            <Route 
              path="/" 
              element={
                <Home/>
              } 
            />

            {/* 404 Route */}
            <Route 
              path="*" 
              element={
                <div className="flex flex-col items-center justify-center h-screen">
                  <h1 className="text-4xl font-bold mb-4">404 - Page Not Found</h1>
                  <p className="mb-8">The page you are looking for doesn't exist.</p>
                  <a 
                    href="/"
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Go to Home
                  </a>
                </div>
              } 
            />
          </Routes>
        </VendorProvider>
      </AuthProvider>
    </Router>
  );
};

export default App;