import React, { useState } from 'react';
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
  const { isAuthenticated, token, checkTokenValidity, refreshToken } = useAuth();
  
  // Button size classes based on size prop
  const sizeClasses = {
    small: 'px-2 py-1 text-xs',
    medium: 'px-4 py-2 text-sm',
    large: 'px-6 py-3 text-base'
  };

  // Helper function to download file from blob
  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    setTimeout(() => {
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }, 100);
  };

  // Helper function to get filename from response headers
  const getFilenameFromResponse = (response: Response, fallback: string): string => {
    const contentDisposition = response.headers.get('content-disposition');
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        return filenameMatch[1].replace(/['"]/g, '');
      }
    }
    return fallback;
  };

  // Method 1: Direct download (if your backend supports it)
  const downloadDirect = async (): Promise<boolean> => {
    try {
      const apiUrl = `/api/${documentType}-documents/${documentId}/download/`;
      
      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${token}`,
        }
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }

      // Check if response is actually a file
      const contentType = response.headers.get('content-type');
      
      // If we get HTML content, it's likely an error/login page
      if (contentType && (contentType.includes('text/html') || contentType.includes('application/json'))) {
        console.log('Received HTML/JSON instead of file, checking content...');
        
        if (contentType.includes('application/json')) {
          const errorData = await response.json();
          throw new Error(errorData.message || 'Download failed');
        } else {
          // HTML response - likely authentication issue
          const htmlContent = await response.text();
          if (htmlContent.includes('<!DOCTYPE') || htmlContent.includes('<html')) {
            throw new Error('Authentication failed - received HTML page instead of file');
          }
        }
      }

      // Validate content type for actual documents
      const validFileTypes = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/octet-stream',
        'text/plain',
        'image/'
      ];

      const isValidFileType = validFileTypes.some(type => 
        contentType && contentType.includes(type)
      );

      if (!isValidFileType && contentType) {
        console.warn(`Unexpected content type: ${contentType}`);
        // Don't fail here, but log the warning
      }

      const blob = await response.blob();
      
      // Double-check blob size
      if (blob.size === 0) {
        throw new Error('Received empty file');
      }

      // If blob is very small and content type suggests HTML, it might be an error page
      if (blob.size < 1024 && contentType && contentType.includes('text/html')) {
        const text = await blob.text();
        if (text.includes('<!DOCTYPE') || text.includes('<html')) {
          throw new Error('Received HTML error page instead of document');
        }
      }

      const filename = getFilenameFromResponse(response, `${documentType}-document-${documentId}.pdf`);
      
      downloadBlob(blob, filename);
      return true;
    } catch (error) {
      console.error('Direct download failed:', error);
      return false;
    }
  };

  // Method 2: Secure URL download (your current approach, improved)
  const downloadViaSecureUrl = async (): Promise<boolean> => {
    try {
      const apiUrl = `/api/${documentType}-documents/${documentId}/secure-download-link/`;
      
      const secureUrlResponse = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!secureUrlResponse.ok) {
        throw new Error(`Failed to get secure download link: ${secureUrlResponse.status} ${secureUrlResponse.statusText}`);
      }

      // Check for HTML response (auth error)
      const contentType = secureUrlResponse.headers.get('content-type');
      if (contentType && contentType.includes('text/html')) {
        throw new Error('Authentication error. Your session may have expired.');
      }

      const secureUrlData = await secureUrlResponse.json();
      
      if (!secureUrlData.download_url) {
        throw new Error('Invalid response: No download URL provided');
      }

      // For external URLs, use window.open or location.href
      if (secureUrlData.download_url.startsWith('http')) {
        // External URL - open in new tab or redirect
        const link = document.createElement('a');
        link.href = secureUrlData.download_url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        if (secureUrlData.filename) {
          link.download = secureUrlData.filename;
        }
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        // Internal URL - fetch with authorization
        const fileResponse = await fetch(secureUrlData.download_url, {
          method: 'GET',
          headers: {
            'Authorization': `Token ${token}`,
          }
        });

        if (!fileResponse.ok) {
          throw new Error(`File download failed: ${fileResponse.status}`);
        }

        // Validate the file response content type
        const fileContentType = fileResponse.headers.get('content-type');
        if (fileContentType && fileContentType.includes('text/html')) {
          const htmlContent = await fileResponse.text();
          if (htmlContent.includes('<!DOCTYPE') || htmlContent.includes('<html')) {
            throw new Error('Authentication failed - received HTML page instead of file');
          }
        }

        const blob = await fileResponse.blob();
        
        // Check if we received an empty or suspicious file
        if (blob.size === 0) {
          throw new Error('Received empty file');
        }

        // If it's a small file with HTML content type, check if it's an error page
        if (blob.size < 1024 && fileContentType && fileContentType.includes('text/html')) {
          const text = await blob.text();
          if (text.includes('<!DOCTYPE') || text.includes('<html')) {
            throw new Error('Received HTML error page instead of document');
          }
        }

        const filename = secureUrlData.filename || getFilenameFromResponse(fileResponse, `${documentType}-document-${documentId}.pdf`);
        downloadBlob(blob, filename);
      }

      return true;
    } catch (error) {
      console.error('Secure URL download failed:', error);
      return false;
    }
  };

  const handleDownload = async () => {
    if (isLoading) return;
    
    // Check authentication
    if (!isAuthenticated || !token) {
      setError('You must be logged in to download documents.');
      if (onError) onError(new Error('Authentication required'));
      return;
    }

    // Check token validity
    if (!checkTokenValidity()) {
      try {
        const refreshed = await refreshToken();
        if (!refreshed) {
          setError('Your session has expired. Please log in again.');
          if (onError) onError(new Error('Session expired'));
          return;
        }
      } catch (error) {
        setError('Session validation failed. Please log in again.');
        if (onError) onError(new Error('Session validation failed'));
        return;
      }
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Debug: Log the request details
      console.log(`Attempting to download ${documentType} document with ID: ${documentId}`);
      console.log(`Token present: ${!!token}`);
      console.log(`Auth header will be: Token ${token?.substring(0, 10)}...`);
      
      // Try direct download first, then fall back to secure URL
      let success = await downloadDirect();
      
      if (!success) {
        console.log('Direct download failed, trying secure URL method...');
        success = await downloadViaSecureUrl();
      }

      if (!success) {
        throw new Error('All download methods failed');
      }

      if (onSuccess) onSuccess();
      
    } catch (err: any) {
      console.error('Download failed:', err);
      
      let errorMessage = 'Download failed';
      
      if (err.message?.includes('401') || err.message?.includes('Authentication')) {
        errorMessage = 'Authentication failed. Please log in again.';
      } else if (err.message?.includes('403') || err.message?.includes('forbidden')) {
        errorMessage = 'You do not have permission to download this document.';
      } else if (err.message?.includes('404') || err.message?.includes('not found')) {
        errorMessage = 'Document not found.';
      } else if (err.message?.includes('429')) {
        errorMessage = 'Too many requests. Please try again later.';
      } else if (err.message?.includes('500')) {
        errorMessage = 'Server error. Please try again later.';
      } else if (err.message?.includes('HTML') || err.message?.includes('error page')) {
        errorMessage = 'Authentication error. Please check your login status and try again.';
      } else if (err.message) {
        errorMessage = `Download failed: ${err.message}`;
      }
      
      setError(errorMessage);
      if (onError) onError(err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const buttonSizeClass = sizeClasses[size];
  
  return (
    <div>
      {error && (
        <div className="text-red-600 text-sm mb-2 p-2 bg-red-50 border border-red-200 rounded">
          {error}
        </div>
      )}
      
      <button 
        className={`${className} ${buttonSizeClass} flex items-center justify-center rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed`}
        onClick={handleDownload} 
        disabled={isLoading || !isAuthenticated}
        title={!isAuthenticated ? 'Please log in to download documents' : ''}
      >
        {isLoading ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Downloading...
          </>
        ) : (
          <>
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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