// client/src/components/auth/RequireAuth.tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface RequireAuthProps {
  children: React.ReactNode;
  allowedRoles?: string[];
}

const RequireAuth: React.FC<RequireAuthProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, user, isLoading } = useAuth();
  const location = useLocation();

  // If auth is still loading, show a loading indicator
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
      </div>
    );
  }

  // If not authenticated, redirect to login with return URL
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If roles are specified, check if user has required role
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-gray-100 p-4">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full">
          <div className="flex items-center justify-center mb-6 text-red-500">
            <span className="material-icons text-4xl">error_outline</span>
          </div>
          <h1 className="text-2xl font-bold text-center text-gray-800 mb-4">
            Access Denied
          </h1>
          <p className="text-gray-600 text-center mb-6">
            You don't have permission to access this page. This page requires one of the following roles:
            {allowedRoles.map((role, index) => (
              <span key={role} className="font-semibold">
                {index === 0 ? ' ' : ', '}
                {role}
              </span>
            ))}
            .
          </p>
          <div className="flex justify-center">
            <button
              onClick={() => window.history.back()}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  // If authenticated and has required role, render the children
  return <>{children}</>;
};

export default RequireAuth;