// client/src/pages/offers/OfferDetail.tsx
import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { offerApi, documentApi, tenderApi } from '../../api/api';

interface Offer {
  id: number;
  tender: {
    id: number;
    reference_number: string;
    title: string;
  };
  vendor: {
    id: number;
    name: string;
  };
  price: number;
  currency: string;
  delivery_time: number;
  delivery_time_unit: string;
  warranty_period: number;
  warranty_period_unit: string;
  technical_description: string;
  comment: string;
  status: string;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
}

interface Document {
  id: number;
  filename: string;
  file_type: string;
  document_type: string;
  created_at: string;
}

const OfferDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [offer, setOffer] = useState<Offer | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [submitLoading, setSubmitLoading] = useState<boolean>(false);
  const [showConfirmSubmit, setShowConfirmSubmit] = useState<boolean>(false);

  useEffect(() => {
    const fetchOfferData = async () => {
      try {
        setLoading(true);
        setError(null);

        if (!id) return;

        const offerData = await offerApi.getById(Number(id));
        setOffer(offerData);

        // Fetch related documents
        const documentsData = await offerApi.getDocuments(Number(id));
        setDocuments(documentsData);
      } catch (err: any) {
        console.error('Error fetching offer data:', err);
        setError(err.message || 'Failed to load offer data');
      } finally {
        setLoading(false);
      }
    };

    fetchOfferData();
  }, [id]);

  const handleSubmitOffer = async () => {
    if (!offer) return;

    try {
      setSubmitLoading(true);
      await offerApi.submit(offer.id);
      
      // Refresh offer data
      const updatedOffer = await offerApi.getById(offer.id);
      setOffer(updatedOffer);
      
      setShowConfirmSubmit(false);
    } catch (err: any) {
      console.error('Error submitting offer:', err);
      setError(err.message || 'Failed to submit offer');
    } finally {
      setSubmitLoading(false);
    }
  };

  const getDocumentDownloadUrl = (documentId: number) => {
    return documentApi.getDocumentDownloadUrl('offer-document', documentId);
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
    }).format(amount);
  };

  const formatTimeUnit = (value: number, unit: string) => {
    if (value === 1) {
      // Remove trailing 's' for singular
      return `${value} ${unit.endsWith('s') ? unit.slice(0, -1) : unit}`;
    }
    // Ensure plural has 's'
    return `${value} ${unit.endsWith('s') ? unit : unit + 's'}`;
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'submitted':
        return 'bg-green-100 text-green-800';
      case 'evaluated':
        return 'bg-yellow-100 text-yellow-800';
      case 'awarded':
        return 'bg-blue-100 text-blue-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Check if current user can edit this offer
  const canEdit = () => {
    if (!user || !offer) return false;
    
    // Only vendor who created the offer can edit it, and only in draft status
    const isVendorOwner = user.role === 'vendor' && 
      offer.vendor && user.id === offer.vendor.id;
    
    return isVendorOwner && offer.status === 'draft';
  };

  // Check if current user can evaluate this offer
  const canEvaluate = () => {
    if (!user || !offer) return false;
    
    // Only evaluators and admin/staff can evaluate offers
    const hasEvaluatorRole = user.role === 'evaluator' || 
      user.role === 'admin' || user.role === 'staff';
    
    // Offer must be submitted and tender must be closed
    return hasEvaluatorRole && offer.status === 'submitted';
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-screen">
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
      </Layout>
    );
  }

  if (!offer) {
    return (
      <Layout>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Offer Not Found</h1>
          <p className="mt-2 text-gray-600">The offer you are looking for does not exist or you do not have permission to view it.</p>
          <Link to="/offers" className="mt-4 inline-block text-blue-600 hover:text-blue-800">
            Back to Offers
          </Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Offer Details</h1>
          <p className="text-gray-600">
            For Tender: {offer.tender.reference_number} - {offer.tender.title}
          </p>
        </div>
        <div className="flex gap-2">
          {canEdit() && (
            <Link
              to={`/offers/${offer.id}/edit`}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              <span className="material-icons mr-2 text-sm">edit</span>
              Edit Offer
            </Link>
          )}
          {offer.status === 'draft' && user?.role === 'vendor' && (
            <button
              onClick={() => setShowConfirmSubmit(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700"
            >
              <span className="material-icons mr-2 text-sm">send</span>
              Submit Offer
            </button>
          )}
          {canEvaluate() && (
            <Link
              to={`/offers/${offer.id}/evaluate`}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-yellow-600 hover:bg-yellow-700"
            >
              <span className="material-icons mr-2 text-sm">grade</span>
              Evaluate
            </Link>
          )}
        </div>
      </div>

      {/* Status Badge */}
      <div className="mb-6">
        <span className={`px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full ${getStatusBadgeColor(offer.status)}`}>
          {offer.status.charAt(0).toUpperCase() + offer.status.slice(1)}
        </span>
        {offer.submitted_at && (
          <span className="ml-2 text-sm text-gray-500">
            Submitted on {new Date(offer.submitted_at).toLocaleDateString()} at {new Date(offer.submitted_at).toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Offer Details */}
      <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Offer Information
          </h3>
        </div>
        <div className="border-t border-gray-200">
          <dl>
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Vendor</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {offer.vendor.name}
              </dd>
            </div>
            <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Price</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {formatCurrency(offer.price, offer.currency)}
              </dd>
            </div>
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Delivery Time</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {formatTimeUnit(offer.delivery_time, offer.delivery_time_unit)}
              </dd>
            </div>
            <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Warranty Period</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {formatTimeUnit(offer.warranty_period, offer.warranty_period_unit)}
              </dd>
            </div>
            <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Created At</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {new Date(offer.created_at).toLocaleString()}
              </dd>
            </div>
            <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
              <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {new Date(offer.updated_at).toLocaleString()}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Technical Description */}
      <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Technical Description
          </h3>
        </div>
        <div className="px-4 py-5 sm:px-6">
          <div className="prose max-w-none">
            {offer.technical_description ? (
              <div dangerouslySetInnerHTML={{ __html: offer.technical_description }} />
            ) : (
              <p className="text-gray-500 italic">No technical description provided</p>
            )}
          </div>
        </div>
      </div>

      {/* Comment */}
      {offer.comment && (
        <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
          <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Additional Comments
            </h3>
          </div>
          <div className="px-4 py-5 sm:px-6">
            <p className="text-sm text-gray-900">{offer.comment}</p>
          </div>
        </div>
      )}

      {/* Documents */}
      <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Documents
          </h3>
        </div>
        <div className="px-4 py-5 sm:px-6">
          {documents.length > 0 ? (
            <ul className="divide-y divide-gray-200">
              {documents.map((document) => (
                <li key={document.id} className="py-3 flex justify-between items-center">
                  <div className="flex items-center">
                    <span className="material-icons text-gray-400 mr-2">
                      {document.file_type.includes('pdf') ? 'picture_as_pdf' :
                       document.file_type.includes('word') ? 'description' :
                       document.file_type.includes('image') ? 'image' :
                       document.file_type.includes('excel') ? 'table_chart' : 'insert_drive_file'}
                    </span>
                    <div>
                      <span className="text-sm font-medium text-gray-900">{document.filename}</span>
                      {document.document_type && (
                        <span className="ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                          {document.document_type}
                        </span>
                      )}
                      <p className="text-xs text-gray-500">
                        Uploaded on {new Date(document.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <a
                    href={getDocumentDownloadUrl(document.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center"
                  >
                    <span className="material-icons text-sm mr-1">download</span>
                    Download
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No documents attached to this offer</p>
          )}
        </div>
      </div>

      {/* Submit Confirmation Modal */}
      {showConfirmSubmit && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-green-100 sm:mx-0 sm:h-10 sm:w-10">
                    <span className="material-icons text-green-600">send</span>
                  </div>
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Submit Offer
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        Are you sure you want to submit this offer? Once submitted, you will not be able to make further changes.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  className={`w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 sm:ml-3 sm:w-auto sm:text-sm ${
                    submitLoading ? 'opacity-70 cursor-not-allowed' : ''
                  }`}
                  onClick={handleSubmitOffer}
                  disabled={submitLoading}
                >
                  {submitLoading ? 'Submitting...' : 'Submit'}
                </button>
                <button
                  type="button"
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={() => setShowConfirmSubmit(false)}
                  disabled={submitLoading}
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