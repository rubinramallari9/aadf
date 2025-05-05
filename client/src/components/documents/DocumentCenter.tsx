// components/DocumentCenter.tsx
import React, { useEffect, useState } from 'react';
import { reportsApi } from '../../api/reportsApi';
import { documentApi } from '../../api/DocumentApi';
import SecureDocumentDownloader from '../documents/SecureDocumentDownloader';

interface DocumentCenterProps {
  tenderId?: number;
  title?: string;
  showHeader?: boolean;
}

interface Document {
  id: number;
  filename: string;
  original_filename: string;
  document_type: string;
  created_at: string;
}

const DocumentCenter: React.FC<DocumentCenterProps> = ({ 
  tenderId,
  title = "Document Center",
  showHeader = true
}) => {
  const [reports, setReports] = useState<any[]>([]);
  const [tenderDocs, setTenderDocs] = useState<Document[]>([]);
  const [offerDocs, setOfferDocs] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchDocuments = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Fetch reports
        const reportsParams = tenderId ? { tender_id: tenderId.toString() } : {};
        const reportsData = await reportsApi.getAll(reportsParams);
        setReports(Array.isArray(reportsData) ? reportsData : []);
        
        // Fetch tender documents if tenderId is provided
        if (tenderId) {
          const tenderDocsData = await documentApi.getTenderDocuments(tenderId);
          setTenderDocs(tenderDocsData);
          
          // Fetch offer documents for this tender
          try {
            const response = await fetch(`/api/offers/?tender_id=${tenderId}`, {
              headers: {
                'Authorization': `Token ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
              }
            });
            
            if (!response.ok) {
              throw new Error('Failed to fetch offers');
            }
            
            const offersData = await response.json();
            
            // Get documents for each offer
            let allOfferDocs: Document[] = [];
            for (const offer of offersData) {
              try {
                const offerDocs = await documentApi.getOfferDocuments(offer.id);
                allOfferDocs = [...allOfferDocs, ...offerDocs];
              } catch (offerDocError) {
                console.error(`Error fetching documents for offer ${offer.id}:`, offerDocError);
              }
            }
            
            setOfferDocs(allOfferDocs);
          } catch (offersError) {
            console.error('Error fetching offers:', offersError);
          }
        }
      } catch (error: any) {
        console.error('Error fetching documents:', error);
        setError(error.message || 'Failed to load documents');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchDocuments();
  }, [tenderId]);

  // Handle download success
  const handleDownloadSuccess = () => {
    setSuccessMessage('Download started successfully!');
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  // Handle download error
  const handleDownloadError = (err: Error) => {
    console.error('Download error:', err);
    setError(`Download failed: ${err.message}`);
    setTimeout(() => setError(null), 5000);
  };
  
  const getDocumentTypeIcon = (documentType: string) => {
    switch(documentType) {
      case 'technical_proposal':
        return '🔧';
      case 'financial_proposal':
        return '💰';
      case 'company_profile':
        return '🏢';
      case 'tender_commission':
        return '📋';
      case 'tender_data':
        return '📊';
      case 'ai_tender_analysis':
        return '🤖';
      case 'evaluation_summary':
        return '📝';
      default:
        return '📄';
    }
  };
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  return (
    <div className="bg-white shadow rounded-lg overflow-hidden">
      {showHeader && (
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <h3 className="text-lg leading-6 font-medium text-gray-900">{title}</h3>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">
            Access and download all documents related to this tender
          </p>
        </div>
      )}
      
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 m-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="bg-green-50 border-l-4 border-green-400 p-4 m-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-green-700">{successMessage}</p>
            </div>
          </div>
        </div>
      )}
      
      <div className="p-4 sm:p-6">
        {/* Reports Section */}
        <section className="mb-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Reports</h3>
          {reports.length === 0 ? (
            <p className="text-sm text-gray-500">No reports available.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {reports.map(report => (
                <div key={report.id} className="border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                  <div className="bg-blue-50 px-4 py-3 border-b">
                    <div className="flex items-center">
                      <span className="text-xl mr-2">{getDocumentTypeIcon(report.report_type)}</span>
                      <div>
                        <h4 className="font-medium text-blue-800 truncate" title={report.filename}>
                          {report.filename}
                        </h4>
                        <p className="text-xs text-gray-500">
                          {formatDate(report.created_at)}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="px-4 py-3">
                    <div className="flex justify-between items-center">
                      <span className="text-xs bg-blue-100 text-blue-800 rounded-full px-2 py-1">
                        {report.report_type.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </span>
                      <SecureDocumentDownloader 
                        documentType="report" 
                        documentId={report.id}
                        buttonText="Download"
                        className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        size="small"
                        onSuccess={handleDownloadSuccess}
                        onError={handleDownloadError}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
        
        {/* Tender Documents Section */}
        {tenderId && (
          <section className="mb-8">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Tender Documents</h3>
            {tenderDocs.length === 0 ? (
              <p className="text-sm text-gray-500">No tender documents available.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {tenderDocs.map(doc => (
                  <div key={doc.id} className="border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                    <div className="bg-green-50 px-4 py-3 border-b">
                      <div className="flex items-center">
                        <span className="text-xl mr-2">📋</span>
                        <div>
                          <h4 className="font-medium text-green-800 truncate" title={doc.original_filename}>
                            {doc.original_filename}
                          </h4>
                          <p className="text-xs text-gray-500">
                            {formatDate(doc.created_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="px-4 py-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs bg-green-100 text-green-800 rounded-full px-2 py-1">
                          Tender Document
                        </span>
                        <SecureDocumentDownloader 
                          documentType="tender" 
                          documentId={doc.id}
                          buttonText="Download"
                          className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                          size="small"
                          onSuccess={handleDownloadSuccess}
                          onError={handleDownloadError}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
        
        {/* Offer Documents Section */}
        {tenderId && (
          <section>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Offer Documents</h3>
            {offerDocs.length === 0 ? (
              <p className="text-sm text-gray-500">No offer documents available.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {offerDocs.map(doc => (
                  <div key={doc.id} className="border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                    <div className="bg-amber-50 px-4 py-3 border-b">
                      <div className="flex items-center">
                        <span className="text-xl mr-2">{getDocumentTypeIcon(doc.document_type)}</span>
                        <div>
                          <h4 className="font-medium text-amber-800 truncate" title={doc.original_filename}>
                            {doc.original_filename}
                          </h4>
                          <p className="text-xs text-gray-500">
                            {formatDate(doc.created_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="px-4 py-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs bg-amber-100 text-amber-800 rounded-full px-2 py-1">
                          {doc.document_type ? doc.document_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Offer Document'}
                        </span>
                        <SecureDocumentDownloader 
                          documentType="offer" 
                          documentId={doc.id}
                          buttonText="Download"
                          className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500"
                          size="small"
                          onSuccess={handleDownloadSuccess}
                          onError={handleDownloadError}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
        
        {/* Empty state */}
        {reports.length === 0 && tenderDocs.length === 0 && offerDocs.length === 0 && (
          <div className="text-center py-8">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No documents</h3>
            <p className="mt-1 text-sm text-gray-500">
              There are no documents available for this tender yet.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentCenter;