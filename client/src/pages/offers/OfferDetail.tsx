// client/src/pages/offers/OfferDetail.tsx
import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { useVendor } from '../../contexts/VendorContext';
import { OfferDocumentList } from '../../components/documents/DocumentUpload';
import api from '../../api/api';

// Define interfaces for the component
interface Offer {
  id: number;
  tender: number;
  tender_title: string;
  tender_reference: string;
  vendor: number;
  vendor_name: string;
  status: string;
  price: number;
  notes: string;
  submitted_at: string;
  technical_score: number | null;
  financial_score: number | null;
  total_score: number | null;
  created_at: string;
  updated_at: string;
}

interface Tender {
  id: number;
  reference_number: string;
  title: string;
  description: string;
  status: string;
  submission_deadline: string;
  requirements: TenderRequirement[];
}

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

const OfferDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { currentVendor } = useVendor();
  const navigate = useNavigate();
  
  const [offer, setOffer] = useState<Offer | null>(null);
  const [tender, setTender] = useState<Tender | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitConfirmOpen, setSubmitConfirmOpen] = useState<boolean>(false);

  useEffect(() => {
    fetchOfferDetails();
  }, [id]);

  const fetchOfferDetails = async () => {
    try {
      setLoading(true);
      if (!id) {
        throw new Error('No offer ID provided');
      }
      
      // Convert id to number
      const offerId = parseInt(id);
      
      // Fetch offer details
      const offerResponse = await api.offers.getById(offerId);
      setOffer(offerResponse);
      
      // Fetch tender details
      if (offerResponse?.tender) {
        const tenderResponse = await api.tenders.getById(offerResponse.tender);
        setTender(tenderResponse);
      }
      
      // Fetch documents
      const documentsResponse = await api.documents.getOfferDocuments(offerId);
      
      // Handle different response structures
      let docs = [];
      if (documentsResponse) {
        if (Array.isArray(documentsResponse)) {
          docs = documentsResponse;
        } else if (documentsResponse.results && Array.isArray(documentsResponse.results)) {
          docs = documentsResponse.results;
        } else if (typeof documentsResponse === 'object') {
          docs = Object.values(documentsResponse);
        }
      }
      
      setDocuments(docs);
      
    } catch (err: any) {
      console.error('Error fetching offer details:', err);
      setError(err.message || 'Failed to load offer details');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitOffer = async () => {
    try {
      if (!id) return;
      
      setLoading(true);
      const offerId = parseInt(id);
      
      // Submit the offer
      await api.offers.submit(offerId);
      
      // Update offer data
      const updatedOffer = await api.offers.getById(offerId);
      setOffer(updatedOffer);
      
      // Show success message
      setSuccessMessage('Offer submitted successfully!');
      setSubmitConfirmOpen(false);
      
      // Clear success message after a few seconds
      setTimeout(() => {
        setSuccessMessage(null);
      }, 5000);
      
    } catch (err: any) {
      console.error('Error submitting offer:', err);
      setError(err.message || 'Failed to submit offer');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteOffer = async () => {
    if (!id || !window.confirm('Are you sure you want to delete this offer? This action cannot be undone.')) {
      return;
    }
    
    try {
      setLoading(true);
      const offerId = parseInt(id);
      
      // Delete the offer
      await api.offers.delete(offerId);
      
      // Redirect to offers list
      navigate('/offers');
      
    } catch (err: any) {
      console.error('Error deleting offer:', err);
      setError(err.message || 'Failed to delete offer');
      setLoading(false);
    }
  };

  // Check if user has permission to view this offer
  const checkPermission = () => {
    if (!user || !offer) return false;
    
    // Admin and staff can view all offers
    if (user.role === 'admin' || user.role === 'staff') {
      return true;
    }
    
    // Evaluators can view offers for closed or awarded tenders
    if (user.role === 'evaluator' && tender && ['closed', 'awarded'].includes(tender.status)) {
      return true;
    }
    
    // Vendors can only view their own offers
    if (user.role === 'vendor') {
      return currentVendor && offer.vendor === currentVendor.id;
    }
    
    return false;
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
        <div className="mt-4">
          <button 
            onClick={() => navigate('/offers')} 
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Back to Offers
          </button>
        </div>
      </Layout>
    );
  }

  if (!offer) {
    return (
      <Layout>
        <div className="text-center">
          <h2 className="text-lg font-medium">Offer not found</h2>
          <p className="mt-2">The offer you are looking for does not exist or has been deleted.</p>
          <div className="mt-4">
            <button 
              onClick={() => navigate('/offers')} 
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Back to Offers
            </button>
          </div>
        </div>
      </Layout>
    );
  }

  // Check if user has permission to view this offer
  if (!checkPermission()) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Access Denied</strong>
          <span className="block sm:inline"> You do not have permission to view this offer.</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-5xl mx-auto">
        {/* Success Message */}
        {successMessage && (
          <div className="mb-6 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{successMessage}</span>
            <button
              className="absolute top-0 bottom-0 right-0 px-4 py-3"
              onClick={() => setSuccessMessage(null)}
            >
              <span className="material-icons">close</span>
            </button>
          </div>
        )}

        {/* Header */}
        <div className="mb-6">
          <div className="flex flex-col md:flex-row md:justify-between md:items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Offer Details</h1>
              <p className="mt-1 text-sm text-gray-600">
                {tender?.reference_number} - {tender?.title}
              </p>
            </div>
            <div className="flex mt-4 md:mt-0 space-x-4">
              {/* Show edit button only if offer is in draft status and user is the vendor */}
              {user.role === 'vendor' && offer.status === 'draft' && currentVendor && offer.vendor === currentVendor.id && (
                <Link
                  to={`/offers/edit/${offer.id}`}
                  className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 inline-flex items-center"
                >
                  <span className="material-icons mr-1 text-sm">edit</span>
                  Edit
                </Link>
              )}
              
              {/* Show submit button only if offer is in draft status and user is the vendor */}
              {user.role === 'vendor' && offer.status === 'draft' && currentVendor && offer.vendor === currentVendor.id && (
                <button
                  onClick={() => setSubmitConfirmOpen(true)}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 inline-flex items-center"
                >
                  <span className="material-icons mr-1 text-sm">send</span>
                  Submit
                </button>
              )}
              
              {/* Show delete button only if offer is in draft status and user is the vendor */}
              {user.role === 'vendor' && offer.status === 'draft' && currentVendor && offer.vendor === currentVendor.id && (
                <button
                  onClick={handleDeleteOffer}
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 inline-flex items-center"
                >
                  <span className="material-icons mr-1 text-sm">delete</span>
                  Delete
                </button>
              )}
              
              {/* Show back button for all users */}
              <button
                onClick={() => navigate('/offers')}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 inline-flex items-center"
              >
                <span className="material-icons mr-1 text-sm">arrow_back</span>
                Back
              </button>
            </div>
          </div>
        </div>

        {/* Offer status banner */}
        <div className={`mb-6 p-4 rounded-md ${
          offer.status === 'draft' 
            ? 'bg-gray-100 text-gray-700 border border-gray-300' 
            : offer.status === 'submitted' 
            ? 'bg-green-100 text-green-700 border border-green-300'
            : offer.status === 'evaluated'
            ? 'bg-yellow-100 text-yellow-700 border border-yellow-300'
            : offer.status === 'awarded'
            ? 'bg-blue-100 text-blue-700 border border-blue-300'
            : 'bg-red-100 text-red-700 border border-red-300'
        }`}>
          <div className="flex items-center">
            <span className="material-icons mr-2">
              {offer.status === 'draft' ? 'edit' 
                : offer.status === 'submitted' ? 'send' 
                : offer.status === 'evaluated' ? 'grade'
                : offer.status === 'awarded' ? 'verified'
                : 'cancel'}
            </span>
            <div>
              <p className="font-medium">
                {offer.status === 'draft' ? 'Draft Offer' 
                  : offer.status === 'submitted' ? 'Submitted Offer' 
                  : offer.status === 'evaluated' ? 'Evaluated Offer'
                  : offer.status === 'awarded' ? 'Awarded Offer'
                  : 'Rejected Offer'}
              </p>
              <p className="text-sm">
                {offer.status === 'draft' ? 'This offer has not been submitted yet and can be edited.' 
                  : offer.status === 'submitted' ? `Submitted on ${new Date(offer.submitted_at).toLocaleString()}` 
                  : offer.status === 'evaluated' ? 'This offer has been evaluated.'
                  : offer.status === 'awarded' ? 'This offer has been awarded the tender!'
                  : 'This offer was not selected.'}
              </p>
            </div>
          </div>
        </div>

        {/* Offer Details */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Offer Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="text-sm font-medium text-gray-500">Vendor</p>
              <p className="mt-1 text-lg text-gray-900">{offer.vendor_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Price</p>
              <p className="mt-1 text-lg text-gray-900">${offer.price.toLocaleString()}</p>
            </div>
            <div className="md:col-span-2">
              <p className="text-sm font-medium text-gray-500">Additional Notes</p>
              <p className="mt-1 text-gray-900">{offer.notes || 'No notes provided'}</p>
            </div>
          </div>
        </div>

        {/* Evaluation Results - Only show if offer has been evaluated */}
        {offer.technical_score !== null && offer.financial_score !== null && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Evaluation Results</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm font-medium text-gray-500">Technical Score</p>
                <div className="mt-1 flex items-center">
                  <span className="text-lg font-medium text-gray-900">{offer.technical_score.toFixed(2)}</span>
                  <span className="text-sm text-gray-500 ml-1">/ 100</span>
                </div>
                <div className="mt-2 h-2 w-full bg-gray-200 rounded-full">
                  <div 
                    className="h-full bg-blue-600 rounded-full" 
                    style={{ width: `${offer.technical_score}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Financial Score</p>
                <div className="mt-1 flex items-center">
                  <span className="text-lg font-medium text-gray-900">{offer.financial_score.toFixed(2)}</span>
                  <span className="text-sm text-gray-500 ml-1">/ 100</span>
                </div>
                <div className="mt-2 h-2 w-full bg-gray-200 rounded-full">
                  <div 
                    className="h-full bg-green-600 rounded-full" 
                    style={{ width: `${offer.financial_score}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Total Score</p>
                <div className="mt-1 flex items-center">
                  <span className="text-lg font-medium text-gray-900">{offer.total_score?.toFixed(2)}</span>
                  <span className="text-sm text-gray-500 ml-1">/ 100</span>
                </div>
                <div className="mt-2 h-2 w-full bg-gray-200 rounded-full">
                  <div 
                    className="h-full bg-purple-600 rounded-full" 
                    style={{ width: `${offer.total_score}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Documents */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Documents</h2>
          
          {tender && tender.requirements && tender.requirements.length > 0 ? (
            <OfferDocumentList 
              offerId={parseInt(id || '0')}
              requirements={tender.requirements}
              onDocumentsUploaded={fetchOfferDetails}
            />
          ) : (
            <div className="text-gray-500 text-center py-4">
              {documents.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {documents.map(doc => (
                    <div key={doc.id} className="border rounded-lg overflow-hidden">
                      <div className="bg-gray-50 px-4 py-2 border-b">
                        <h3 className="text-sm font-medium text-gray-700">
                          {doc.document_type}
                        </h3>
                      </div>
                      <div className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-gray-900">{doc.original_filename}</span>
                          <span className="text-xs text-gray-500">
                            {(doc.file_size / 1024).toFixed(2)} KB
                          </span>
                        </div>
                        <div className="flex space-x-2">
                          <a 
                            href={api.documents.getDocumentDownloadUrl('offer', doc.id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                          >
                            <span className="material-icons text-sm mr-1">download</span>
                            Download
                          </a>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                'No documents attached to this offer'
              )}
            </div>
          )}
        </div>

        {/* Tender Information */}
        {tender && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Tender Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm font-medium text-gray-500">Reference Number</p>
                <p className="mt-1 text-lg text-gray-900">{tender.reference_number}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Status</p>
                <p className="mt-1">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    tender.status === 'published' 
                      ? 'bg-green-100 text-green-800' 
                      : tender.status === 'draft' 
                      ? 'bg-gray-100 text-gray-800'
                      : tender.status === 'closed'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {tender.status}
                  </span>
                </p>
              </div>
              <div className="md:col-span-2">
                <p className="text-sm font-medium text-gray-500">Title</p>
                <p className="mt-1 text-lg text-gray-900">{tender.title}</p>
              </div>
              <div className="md:col-span-2">
                <p className="text-sm font-medium text-gray-500">Description</p>
                <p className="mt-1 text-gray-900">{tender.description}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Submission Deadline</p>
                <p className="mt-1 text-gray-900">{new Date(tender.submission_deadline).toLocaleString()}</p>
              </div>
              <div className="text-right">
                <Link 
                  to={`/tenders/${tender.id}`}
                  className="inline-flex items-center text-blue-600 hover:text-blue-800"
                >
                  View Tender Details
                  <span className="material-icons ml-1 text-sm">arrow_forward</span>
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Submit Confirmation Modal */}
      {submitConfirmOpen && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>

            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
                    <span className="material-icons text-blue-600">send</span>
                  </div>
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                    <h3 className="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                      Submit Offer
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        Are you sure you want to submit this offer? Once submitted, you will not be able to make any changes.
                      </p>
                      
                      {/* Check if all mandatory documents are uploaded */}
                      {tender && tender.requirements && tender.requirements.some(req => req.is_mandatory) && (
                        <div className="mt-2 bg-yellow-50 border border-yellow-200 p-3 rounded-md">
                          <p className="text-sm text-yellow-700">
                            <strong>Important:</strong> Make sure you have uploaded all required documents before submitting.
                          </p>
                          <ul className="mt-1 text-xs text-yellow-600 list-disc list-inside">
                            {tender.requirements
                              .filter(req => req.is_mandatory)
                              .map(req => {
                                const docExists = documents.some(doc => doc.document_type === req.document_type);
                                return (
                                  <li key={req.id} className={docExists ? 'text-green-600' : 'text-red-600'}>
                                    {req.description} {docExists ? '✓' : '✗'}
                                  </li>
                                );
                              })}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button 
                  type="button" 
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={handleSubmitOffer}
                >
                  Submit Offer
                </button>
                <button 
                  type="button" 
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={() => setSubmitConfirmOpen(false)}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default OfferDetail;