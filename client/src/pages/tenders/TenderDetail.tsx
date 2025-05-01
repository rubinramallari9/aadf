// client/src/pages/tenders/TenderDetail.tsx
import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { tenderApi, offerApi, documentApi } from '../../api/api';

interface Tender {
  id: number;
  title: string;
  description: string;
  status: string;
  reference_number: string;
  submission_deadline: string;
  opening_date: string;
  estimated_value: number;
  category: string;
  created_at: string;
  created_by_username: string;
  requirements?: any[];
  documents?: any[];
  evaluation_criteria?: any[];
}

interface Offer {
  id: number;
  vendor_name: string;
  status: string;
  submitted_at: string;
  price: number;
  total_score: number;
}

const TenderDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tender, setTender] = useState<Tender | null>(null);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showPublishModal, setShowPublishModal] = useState<boolean>(false);
  const [showCloseModal, setShowCloseModal] = useState<boolean>(false);
  const [showAwardModal, setShowAwardModal] = useState<boolean>(false);
  const [selectedOffer, setSelectedOffer] = useState<number | null>(null);

  useEffect(() => {
    fetchTenderDetails();
  }, [id]);

  useEffect(() => {
    if (tender && (user?.role === 'admin' || user?.role === 'staff')) {
      fetchOffers();
    }
  }, [tender, user]);

  const fetchTenderDetails = async () => {
    try {
      setLoading(true);
      const response = await tenderApi.getById(Number(id));
      setTender(response);
    } catch (err: any) {
      console.error('Error fetching tender details:', err);
      setError(err.message || 'Failed to load tender details');
    } finally {
      setLoading(false);
    }
  };

  const fetchOffers = async () => {
    try {
      const response = await offerApi.getByTender(Number(id));
      setOffers(response);
    } catch (err: any) {
      console.error('Error fetching offers:', err);
    }
  };

  const handlePublish = async () => {
    try {
      await tenderApi.publish(Number(id));
      await fetchTenderDetails();
      setShowPublishModal(false);
    } catch (err: any) {
      console.error('Error publishing tender:', err);
      alert(err.message || 'Failed to publish tender');
    }
  };

  const handleClose = async () => {
    try {
      await tenderApi.close(Number(id));
      await fetchTenderDetails();
      setShowCloseModal(false);
    } catch (err: any) {
      console.error('Error closing tender:', err);
      alert(err.message || 'Failed to close tender');
    }
  };

  const handleAward = async () => {
    if (!selectedOffer) {
      alert('Please select an offer to award');
      return;
    }
    try {
      await tenderApi.award(Number(id), selectedOffer);
      await fetchTenderDetails();
      setShowAwardModal(false);
    } catch (err: any) {
      console.error('Error awarding tender:', err);
      alert(err.message || 'Failed to award tender');
    }
  };

  const handleDownloadDocument = (documentId: number) => {
    const downloadUrl = documentApi.getDocumentDownloadUrl('tender', documentId);
    window.open(downloadUrl, '_blank');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published':
        return 'bg-green-100 text-green-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'closed':
        return 'bg-yellow-100 text-yellow-800';
      case 'awarded':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </Layout>
    );
  }

  if (error || !tender) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error || 'Tender not found'}</span>
        </div>
        <div className="mt-4">
          <Link to="/tenders" className="text-blue-600 hover:text-blue-800">
            &larr; Back to tenders
          </Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{tender.title}</h1>
            <p className="text-gray-600">Reference: {tender.reference_number}</p>
          </div>
          <div className="flex items-center space-x-4">
            <span className={`px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full ${getStatusColor(tender.status)}`}>
              {tender.status}
            </span>
            {(user?.role === 'admin' || user?.role === 'staff') && (
              <div className="flex space-x-2">
                {tender.status === 'draft' && (
                  <button
                    onClick={() => setShowPublishModal(true)}
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Publish
                  </button>
                )}
                {tender.status === 'published' && (
                  <button
                    onClick={() => setShowCloseModal(true)}
                    className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
                  >
                    Close
                  </button>
                )}
                {tender.status === 'closed' && (
                  <button
                    onClick={() => setShowAwardModal(true)}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Award
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Details and Documents */}
          <div className="lg:col-span-2 space-y-6">
            {/* Details Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Tender Details</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500">Category</label>
                  <p className="mt-1">{tender.category || '-'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Estimated Value</label>
                  <p className="mt-1">{tender.estimated_value ? `${Number(tender.estimated_value).toLocaleString()}` : '-'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Submission Deadline</label>
                  <p className="mt-1">{new Date(tender.submission_deadline).toLocaleString()}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Opening Date</label>
                  <p className="mt-1">{tender.opening_date ? new Date(tender.opening_date).toLocaleString() : '-'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Created By</label>
                  <p className="mt-1">{tender.created_by_username}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Created At</label>
                  <p className="mt-1">{new Date(tender.created_at).toLocaleString()}</p>
                </div>
              </div>
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-500">Description</label>
                <p className="mt-1 whitespace-pre-wrap">{tender.description}</p>
              </div>
            </div>

            {/* Requirements */}
            {tender.requirements && tender.requirements.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4">Requirements</h2>
                <div className="space-y-4">
                  {tender.requirements.map((requirement, index) => (
                    <div key={requirement.id || index} className="border-l-4 border-blue-500 pl-4 py-2">
                      <p className="font-medium">{requirement.description}</p>
                      <div className="flex items-center mt-1 text-sm text-gray-500">
                        <span className={`px-2 py-1 ${requirement.is_mandatory ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'} rounded`}>
                          {requirement.is_mandatory ? 'Mandatory' : 'Optional'}
                        </span>
                        {requirement.document_type && (
                          <span className="ml-2">{requirement.document_type}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Documents */}
            {tender.documents && tender.documents.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4">Documents</h2>
                <div className="space-y-4">
                  {tender.documents.map((document, index) => (
                    <div key={document.id || index} className="flex items-center justify-between border border-gray-200 rounded p-3">
                      <div className="flex items-center">
                        <span className="material-icons text-gray-400 mr-2">description</span>
                        <div>
                          <p className="font-medium">{document.original_filename}</p>
                          <p className="text-sm text-gray-500">
                            Uploaded on {new Date(document.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDownloadDocument(document.id)}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <span className="material-icons">download</span>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Offers (for staff/admin) */}
            {(user?.role === 'admin' || user?.role === 'staff') && tender.status !== 'draft' && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4">Submitted Offers</h2>
                {offers.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Vendor
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Price
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Score
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Submitted At
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {offers.map((offer) => (
                          <tr key={offer.id}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-gray-900">{offer.vendor_name}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-gray-900">
                                {offer.price ? `${Number(offer.price).toLocaleString()}` : '-'}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-gray-900">
                                {offer.total_score ? offer.total_score.toFixed(2) : '-'}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                offer.status === 'submitted' 
                                  ? 'bg-green-100 text-green-800' 
                                  : offer.status === 'evaluated'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : offer.status === 'awarded'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-gray-100 text-gray-800'
                              }`}>
                                {offer.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {offer.submitted_at ? new Date(offer.submitted_at).toLocaleString() : '-'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                              <Link to={`/offers/${offer.id}`} className="text-blue-600 hover:text-blue-900">
                                View
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">No offers submitted yet</p>
                )}
              </div>
            )}
          </div>

          {/* Right Column - Actions and Evaluation Criteria */}
          <div className="space-y-6">
            {/* Actions Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Actions</h2>
              <div className="space-y-4">
                {user?.role === 'vendor' && tender.status === 'published' && (
                  <Link
                    to={`/offers/create?tender=${tender.id}`}
                    className="block w-full text-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Submit Offer
                  </Link>
                )}
                {(user?.role === 'admin' || user?.role === 'staff') && (
                  <>
                    <Link
                      to={`/tenders/${tender.id}/edit`}
                      className="block w-full text-center px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
                    >
                      Edit Tender
                    </Link>
                    {tender.status === 'published' && (
                      <button
                        onClick={() => navigate(`/tenders/${tender.id}/add-requirement`)}
                        className="block w-full text-center px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
                      >
                        Add Requirement
                      </button>
                    )}
                  </>
                )}
                {user?.role === 'evaluator' && tender.status === 'closed' && (
                  <Link
                    to={`/tenders/${tender.id}/evaluate`}
                    className="block w-full text-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Evaluate Offers
                  </Link>
                )}
              </div>
            </div>

            {/* Evaluation Criteria */}
            {tender.evaluation_criteria && tender.evaluation_criteria.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4">Evaluation Criteria</h2>
                <div className="space-y-4">
                  {tender.evaluation_criteria.map((criteria, index) => (
                    <div key={criteria.id || index} className="border border-gray-200 rounded p-3">
                      <div className="flex justify-between items-start">
                        <h3 className="font-medium">{criteria.name}</h3>
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">
                          {criteria.weight}%
                        </span>
                      </div>
                      {criteria.description && (
                        <p className="text-sm text-gray-600 mt-1">{criteria.description}</p>
                      )}
                      <div className="mt-2 text-sm text-gray-500">
                        Max Score: {criteria.max_score}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Publish Modal */}
      {showPublishModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Publish Tender</h3>
            <p className="text-sm text-gray-500 mb-4">
              Are you sure you want to publish this tender? Once published, vendors will be able to submit offers.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowPublishModal(false)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Publish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Close Modal */}
      {showCloseModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Close Tender</h3>
            <p className="text-sm text-gray-500 mb-4">
              Are you sure you want to close this tender? No more offers will be accepted after closing.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowCloseModal(false)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleClose}
                className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
              >
                Close Tender
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Award Modal */}
      {showAwardModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Award Tender</h3>
            <p className="text-sm text-gray-500 mb-4">
              Select the offer to award the tender to:
            </p>
            <select
              value={selectedOffer || ''}
              onChange={(e) => setSelectedOffer(Number(e.target.value))}
              className="block w-full mt-1 mb-4 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="">Select an offer...</option>
              {offers
                .filter(offer => offer.status === 'evaluated')
                .map((offer) => (
                  <option key={offer.id} value={offer.id}>
                    {offer.vendor_name} - Score: {offer.total_score?.toFixed(2)}
                  </option>
                ))}
            </select>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowAwardModal(false)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleAward}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Award Tender
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default TenderDetail;