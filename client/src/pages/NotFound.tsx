// client/src/pages/NotFound.tsx
import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const NotFound: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100 p-4">
      <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full">
        <div className="flex items-center justify-center mb-6 text-blue-500">
          <span className="material-icons text-6xl">search_off</span>
        </div>
        <h1 className="text-3xl font-bold text-center text-gray-800 mb-4">
          404 - Page Not Found
        </h1>
        <p className="text-gray-600 text-center mb-8">
          The page you are looking for doesn't exist or has been moved.
        </p>
        <div className="flex justify-center space-x-4">
          <button
            onClick={() => window.history.back()}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
          >
            Go Back
          </button>
          <Link
            to={isAuthenticated ? "/dashboard" : "/"}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {isAuthenticated ? "Go to Dashboard" : "Go to Home"}
          </Link>
        </div>
      </div>
    </div>
  );
};

export default NotFound;