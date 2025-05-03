// client/src/components/documents/DocumentUpload.tsx
import React, { useState, useEffect } from 'react';
import api from '../../api/api';

// UploadDocument Component - Handles uploading a single document
interface UploadDocumentProps {
  offerId: number;
  documentType: string;
  description?: string;
  isMandatory?: boolean;
  onSuccess?: (documentId: number) => void;
  onError?: (error: string) => void;
}

export const UploadDocument: React.FC<UploadDocumentProps> = ({ 
  offerId, 
  documentType, 
  description,
  isMandatory = false,
  onSuccess, 
  onError 
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      
      // Validate file size (10MB max)
      if (selectedFile.size > 10 * 1024 * 1024) {
        setError(`File is too large. Maximum file size is 10MB.`);
        setFile(null);
        if (onError) onError(`File is too large. Maximum file size is 10MB.`);
        return;
      }
      
      // Clear previous error if any
      setError(null);
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file to upload');
      if (onError) onError('Please select a file to upload');
      return;
    }
    
    try {
      setUploading(true);
      setProgress(0);
      
      // Simulate progress (in a real app, you might use XHR to track actual progress)
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 300);
      
      // Upload the file
      const response = await api.documents.uploadOfferDocument(offerId, file, documentType);
      
      // Clear interval and complete progress
      clearInterval(progressInterval);
      setProgress(100);
      
      // Handle success
      if (onSuccess) onSuccess(response.id);
      
      // Reset state
      setFile(null);
      setError(null);
      
      // Wait a moment before resetting uploading state
      setTimeout(() => {
        setUploading(false);
        setProgress(0);
      }, 1000);
      
    } catch (err: any) {
      // Clear interval if it exists
      clearInterval(progressInterval);
      
      // Handle error
      console.error('Error uploading document:', err);
      setError(err.message || 'Failed to upload document');
      if (onError) onError(err.message || 'Failed to upload document');
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
      {description && (
        <div className="mb-2">
          <h3 className="text-sm font-medium text-gray-700">
            {description}
            {isMandatory && <span className="text-red-500 ml-1">*</span>}
          </h3>
          <p className="text-xs text-gray-500">Document type: {documentType}</p>
        </div>
      )}
      
      <div className="mb-4">
        <input
          type="file"
          onChange={handleFileChange}
          disabled={uploading}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
      </div>
      
      {error && (
        <div className="mb-4 text-sm text-red-600">{error}</div>
      )}
      
      {file && !uploading && (
        <div className="mb-4">
          <p className="text-sm text-gray-600">
            Selected file: {file.name} ({(file.size / 1024).toFixed(2)} KB)
          </p>
        </div>
      )}
      
      {uploading && (
        <div className="mb-4">
          <div className="h-2 bg-gray-200 rounded-full">
            <div 
              className="h-full bg-blue-600 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <p className="text-xs text-gray-500 mt-1">Uploading... {progress}%</p>
        </div>
      )}
      
      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleUpload}
          disabled={!file || uploading}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </div>
    </div>
  );
};

// OfferDocumentList Component - Manages a list of documents for an offer
interface TenderRequirement {
  id: number;
  description: string;
  document_type: string;
  is_mandatory: boolean;
}

interface Document {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  document_type: string;
  created_at: string;
}

interface OfferDocumentListProps {
  offerId: number;
  requirements: TenderRequirement[];
  onDocumentsUploaded?: () => void;
}

export const OfferDocumentList: React.FC<OfferDocumentListProps> = ({ 
  offerId, 
  requirements,
  onDocumentsUploaded
}) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Fetch documents when the component mounts
  useEffect(() => {
    fetchDocuments();
  }, [offerId]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await api.documents.getOfferDocuments(offerId);
      
      // Handle different response structures
      let docs = [];
      if (response) {
        if (Array.isArray(response)) {
          docs = response;
        } else if (response.results && Array.isArray(response.results)) {
          docs = response.results;
        } else if (typeof response === 'object') {
          docs = Object.values(response);
        }
      }
      
      setDocuments(docs);
    } catch (err: any) {
      console.error('Error fetching documents:', err);
      setError(err.message || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSuccess = (documentId: number) => {
    // Refresh the document list
    fetchDocuments();
    
    // Show success message
    setUploadSuccess('Document uploaded successfully!');
    
    // Clear success message after a few seconds
    setTimeout(() => {
      setUploadSuccess(null);
    }, 3000);
    
    // Notify parent component if needed
    if (onDocumentsUploaded) onDocumentsUploaded();
  };

  const handleDeleteDocument = async (documentId: number) => {
    if (!confirm('Are you sure you want to delete this document?')) {
      return;
    }
    
    try {
      await api.documents.deleteOfferDocument(documentId);
      
      // Refresh the document list
      fetchDocuments();
      
      // Show success message
      setUploadSuccess('Document deleted successfully!');
      
      // Clear success message after a few seconds
      setTimeout(() => {
        setUploadSuccess(null);
      }, 3000);
      
    } catch (err: any) {
      console.error('Error deleting document:', err);
      setError(err.message || 'Failed to delete document');
    }
  };

  // Check which requirements are already fulfilled
  const getDocumentForType = (documentType: string) => {
    return documents.find(doc => doc.document_type === documentType);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <span className="block sm:inline">{error}</span>
          <button
            className="absolute top-0 bottom-0 right-0 px-4 py-3"
            onClick={() => setError(null)}
          >
            <span className="material-icons">close</span>
          </button>
        </div>
      )}
      
      {uploadSuccess && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
          <span className="block sm:inline">{uploadSuccess}</span>
          <button
            className="absolute top-0 bottom-0 right-0 px-4 py-3"
            onClick={() => setUploadSuccess(null)}
          >
            <span className="material-icons">close</span>
          </button>
        </div>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {requirements.map(requirement => {
          const existingDocument = getDocumentForType(requirement.document_type);
          
          return (
            <div key={requirement.id} className="border rounded-lg overflow-hidden">
              <div className="bg-gray-50 px-4 py-2 border-b">
                <h3 className="text-sm font-medium text-gray-700">
                  {requirement.description}
                  {requirement.is_mandatory && <span className="text-red-500 ml-1">*</span>}
                </h3>
                <p className="text-xs text-gray-500">Document type: {requirement.document_type}</p>
              </div>
              
              <div className="p-4">
                {existingDocument ? (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-900">{existingDocument.original_filename}</span>
                      <span className="text-xs text-gray-500">
                        {(existingDocument.file_size / 1024).toFixed(2)} KB
                      </span>
                    </div>
                    
                    <div className="flex space-x-2">
                      <a 
                        href={api.documents.getDocumentDownloadUrl('offer', existingDocument.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                      >
                        <span className="material-icons text-sm mr-1">download</span>
                        Download
                      </a>
                      
                      <button
                        onClick={() => handleDeleteDocument(existingDocument.id)}
                        className="inline-flex items-center px-3 py-1 border border-red-300 text-xs font-medium rounded text-red-700 bg-white hover:bg-red-50"
                      >
                        <span className="material-icons text-sm mr-1">delete</span>
                        Delete
                      </button>
                    </div>
                  </div>
                ) : (
                  <UploadDocument 
                    offerId={offerId}
                    documentType={requirement.document_type}
                    onSuccess={handleUploadSuccess}
                    onError={err => setError(err)}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* No requirements message */}
      {requirements.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-400 text-yellow-700 px-4 py-3 rounded relative" role="alert">
          <span className="block sm:inline">No document requirements defined for this tender.</span>
        </div>
      )}

      {/* Document status summary */}
      <div className="mt-6 bg-gray-50 p-4 rounded-lg">
        <h3 className="text-md font-medium text-gray-900 mb-2">Document Status</h3>
        <div className="space-y-2">
          <p className="text-sm text-gray-600">
            <strong>Total Requirements:</strong> {requirements.length}
          </p>
          <p className="text-sm text-gray-600">
            <strong>Uploaded Documents:</strong> {documents.length}
          </p>
          <p className="text-sm text-gray-600">
            <strong>Missing Required Documents:</strong> {
              requirements
                .filter(req => req.is_mandatory && !getDocumentForType(req.document_type))
                .length
            }
          </p>
        </div>
      </div>
    </div>
  );
};

// ManualDocumentUpload Component - For uploading a document without a specific requirement
interface ManualDocumentUploadProps {
  offerId: number;
  onSuccess?: (documentId: number) => void;
}

export const ManualDocumentUpload: React.FC<ManualDocumentUploadProps> = ({
  offerId,
  onSuccess
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState<string>('other');
  const [customType, setCustomType] = useState<string>('');
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Common document types
  const documentTypes = [
    { value: 'other', label: 'Other' },
    { value: 'technical_proposal', label: 'Technical Proposal' },
    { value: 'financial_proposal', label: 'Financial Proposal' },
    { value: 'company_profile', label: 'Company Profile' },
    { value: 'registration_certificate', label: 'Registration Certificate' },
    { value: 'tax_certificate', label: 'Tax Certificate' },
    { value: 'compliance_certificate', label: 'Compliance Certificate' },
    { value: 'reference_letter', label: 'Reference Letter' },
    { value: 'custom', label: 'Custom Type...' }
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      
      // Validate file size (10MB max)
      if (selectedFile.size > 10 * 1024 * 1024) {
        setError(`File is too large. Maximum file size is 10MB.`);
        setFile(null);
        return;
      }
      
      // Clear previous error if any
      setError(null);
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    // Determine final document type
    const finalDocumentType = documentType === 'custom' ? customType : documentType;
    
    if (documentType === 'custom' && !customType.trim()) {
      setError('Please enter a custom document type');
      return;
    }
    
    try {
      setUploading(true);
      setError(null);
      
      // Upload the file
      const response = await api.documents.uploadOfferDocument(offerId, file, finalDocumentType);
      
      // Handle success
      setSuccess('Document uploaded successfully!');
      setFile(null);
      if (documentType === 'custom') {
        setCustomType('');
      }
      
      if (onSuccess) onSuccess(response.id);
      
      // Clear success message after a few seconds
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
      
    } catch (err: any) {
      console.error('Error uploading document:', err);
      setError(err.message || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Additional Document</h3>
      
      {error && (
        <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
          <span className="block sm:inline">{error}</span>
          <button
            className="absolute top-0 bottom-0 right-0 px-4 py-3"
            onClick={() => setError(null)}
          >
            <span className="material-icons">close</span>
          </button>
        </div>
      )}
      
      {success && (
        <div className="mb-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative">
          <span className="block sm:inline">{success}</span>
          <button
            className="absolute top-0 bottom-0 right-0 px-4 py-3"
            onClick={() => setSuccess(null)}
          >
            <span className="material-icons">close</span>
          </button>
        </div>
      )}
      
      <div className="space-y-4">
        <div>
          <label htmlFor="documentType" className="block text-sm font-medium text-gray-700">
            Document Type
          </label>
          <select
            id="documentType"
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            {documentTypes.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
        </div>
        
        {documentType === 'custom' && (
          <div>
            <label htmlFor="customType" className="block text-sm font-medium text-gray-700">
              Custom Document Type
            </label>
            <input
              type="text"
              id="customType"
              value={customType}
              onChange={(e) => setCustomType(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              placeholder="Enter a custom document type"
            />
          </div>
        )}
        
        <div>
          <label htmlFor="file" className="block text-sm font-medium text-gray-700">
            File
          </label>
          <input
            type="file"
            id="file"
            onChange={handleFileChange}
            disabled={uploading}
            className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>
        
        {file && (
          <div className="text-sm text-gray-600">
            Selected file: {file.name} ({(file.size / 1024).toFixed(2)} KB)
          </div>
        )}
        
        <div className="flex justify-end pt-4">
          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || uploading}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {uploading ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>
      </div>
    </div>
  );
};