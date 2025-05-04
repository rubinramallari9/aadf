// client/src/components/documents/SecureDocumentDownloader.tsx
import React, { useState } from 'react';
import { documentApi } from '../../api/DocumentApi';
import { useAuth } from '../../contexts/AuthContext';

interface SecureDocumentDownloaderProps {
  documentType: 'report' | 'tender' | 'offer';
  documentId: number;
  buttonText?: string;
  className?: string;
  size?: 'small' | 'medium' | 'large';
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

const SecureDocumentDownloader: React.FC<SecureDocumentDownloaderProps> = ({
  documentType,
  documentId,
  buttonText = 'Download',
  className = 'btn btn-primary',
  size = 'medium',
  onSuccess,
  onError
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, token } = useAuth();
  
  // Button size classes based on size prop
  const sizeClasses = {
    small: 'px-2 py-1 text-xs',
    medium: 'px-4 py-2 text-sm',
    large: 'px-6 py-3 text-base'
  };
  
  const handleDownload = async () => {
    if (isLoading) return;
    
    // Check if user is authenticated
    if (!isAuthenticated || !token) {
      setError('You must be logged in to download documents. Please log in and try again.');
      if (onError) onError(new Error('Authentication required'));
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Get a secure download URL first
      const secureUrlResponse = await fetch(`/api/${documentType}s/${documentId}/secure-download-link/`, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!secureUrlResponse.ok) {
        throw new Error(`Failed to get secure download link: ${secureUrlResponse.status}`);
      }
      
      const secureUrlData = await secureUrlResponse.json();
      const downloadUrl = secureUrlData.download_url;
      
      // Perform the actual download using the Fetch API
      const response = await fetch(downloadUrl, {
        method: 'GET',
        // No need to include Authorization headers, the URL contains the token
      });
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }
      
      // Convert response to blob
      const blob = await response.blob();
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob);
      
      // Create a link element to trigger the download
      const a = document.createElement('a');
      a.href = url;
      a.download = secureUrlData.report_filename || `document-${documentId}`;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      if (onSuccess) onSuccess();
    } catch (err: any) {
      console.error('Failed to download document:', err);
      
      // Handle different error scenarios
      if (err.message?.includes('<!DOCTYPE') || err.message?.includes('<html')) {
        // Received HTML instead of JSON - likely an auth issue
        setError('Your session may have expired. Please try logging in again.');
        if (onError) onError(new Error('Session expired'));
      } else if (err.message?.includes('401') || err.message?.includes('unauthorized')) {
        // Explicit authentication error
        setError('Authentication failed. Please log in again.');
        if (onError) onError(new Error('Authentication failed'));
      } else if (err.message?.includes('403') || err.message?.includes('forbidden')) {
        // Permission error
        setError('You do not have permission to download this document.');
        if (onError) onError(new Error('Permission denied'));
      } else if (err.message?.includes('404') || err.message?.includes('not found')) {
        // Document not found
        setError('Document not found. It may have been deleted or moved.');
        if (onError) onError(new Error('Document not found'));
      } else {
        // Generic error
        const errorMessage = err.message || 'Unknown error occurred';
        setError(`Download failed: ${errorMessage}`);
        if (onError) onError(err);
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  const buttonSizeClass = sizeClasses[size];
  
  return (
    <div>
      {error && (
        <div className="text-red-600 text-sm mb-2">
          {error}
        </div>
      )}
      
      <button 
        className={`${className} ${buttonSizeClass} flex items-center justify-center rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed`}
        onClick={handleDownload} 
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Downloading...
          </>
        ) : (
          <>
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
            </svg>
            {buttonText}
          </>
        )}
      </button>
    </div>
  );
};

export default SecureDocumentDownloader;