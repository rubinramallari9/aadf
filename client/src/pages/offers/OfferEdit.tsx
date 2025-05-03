// client/src/pages/offers/OfferEdit.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { useVendor } from '../../contexts/VendorContext';
import { OfferDocumentList, ManualDocumentUpload } from '../../components/documents/DocumentUpload';
import api from '../../api/api';

// Define interfaces
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

const OfferEdit: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { currentVendor } = useVendor();
  const navigate = useNavigate();
  
  // State
  const [offer, setOffer] = useState<Offer | null>(null);
  const [tender, setTender] = useState<Tender | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Form data
  const [formData, setFormData] = useState({
    price: '',
    notes: ''
  });
  
  // Document section states
  const [documentsChanged, setDocumentsChanged] = useState<boolean>(false);
  
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
      
      // Initialize form data
      setFormData({
        price: offerResponse.price.toString(),
        notes: offerResponse.notes || ''
      });
      
      // Fetch tender details
      if (offerResponse?.tender) {
        const tenderResponse = await api.tenders.getById(offerResponse.tender);
        setTender(tenderResponse);
      }
      
    } catch (err: any) {
      console.error('Error fetching offer details:', err);
      setError(err.message || 'Failed to load offer details');
    } finally {
      setLoading(false);
    }
  };

export default OfferEdit;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      if (!id || !offer) return;
      
      setSubmitting(true);
      setError(null);
      
      // Prepare offer data
      const offerData = {
        price: parseFloat(formData.price),
        notes: formData.notes
      };
      
      // Update the offer
      await api.offers.update(parseInt(id), offerData);
      
      // Show success message
      setSuccessMessage('Offer updated successfully!');
      
      // Refresh offer data
      fetchOfferDetails();
      
      // Clear success message after a few seconds
      setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
      
    } catch (err: any) {
      console.error('Error updating offer:', err);
      setError(err.message || 'Failed to update offer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDocumentsUploaded = () => {
    setDocumentsChanged(true);
  };

  // Check if user has permission to edit this offer
  const checkPermission = () => {
    if (!user || !offer) return false;
    
    // Only vendor users who own the offer and if offer is in draft status
    if (user.role === 'vendor' && currentVendor && offer.vendor === currentVendor.id && offer.status === 'draft') {
      return true;
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

  // Check if user has permission to edit this offer
  if (!checkPermission()) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Access Denied</strong>
          <span className="block sm:inline"> You do not have permission to edit this offer.</span>
        </div>
        <div className="mt-4">
          <button 
            onClick={() => navigate(`/offers/${id}`)} 
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            View Offer
          </button>
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
              <h1 className="text-2xl font-bold text-gray-900">Edit Offer</h1>
              <p className="mt-1 text-sm text-gray-600">
                {tender?.reference_number} - {tender?.title}
              </p>
            </div>
            <div className="flex mt-4 md:mt-0 space-x-4">
              <button
                onClick={() => navigate(`/offers/${id}`)}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 inline-flex items-center"
              >
                <span className="material-icons mr-1 text-sm">cancel</span>
                Cancel
              </button>
            </div>
          </div>
        </div>

        {/* Offer status warning */}
        <div className="mb-6 bg-yellow-100 border border-yellow-300 p-4 rounded-md text-yellow-700">
          <div className="flex items-center">
            <span className="material-icons mr-2">warning</span>
            <p>
              <strong>Note:</strong> You are editing a draft offer. Once submitted, the offer cannot be edited.
            </p>
          </div>
        </div>

        {/* Edit Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Offer Details */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Offer Details</h2>
            <div className="grid grid-cols-1 gap-6">
              <div>
                <label htmlFor="price" className="block text-sm font-medium text-gray-700">
                  Price (in local currency) *
                </label>
                <input
                  type="number"
                  id="price"
                  name="price"
                  value={formData.price}
                  onChange={handleInputChange}
                  required
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              
              <div>
                <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
                  Additional Notes
                </label>
                <textarea
                  id="notes"
                  name="notes"
                  rows={4}
                  value={formData.notes}
                  onChange={handleInputChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
            
            <div className="mt-6 flex justify-end">
              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {submitting ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </form>

        {/* Documents */}
        <div className="bg-white shadow rounded-lg p-6 mt-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Documents</h2>
          
          {tender && tender.requirements && tender.requirements.length > 0 ? (
            <OfferDocumentList 
              offerId={parseInt(id || '0')}
              requirements={tender.requirements}
              onDocumentsUploaded={handleDocumentsUploaded}
            />
          ) : (
            <div className="text-gray-500 text-center py-4">
              No document requirements defined for this tender.
            </div>
          )}
          
          {/* Add more documents */}
          <div className="mt-6">
            <h3 className="text-md font-medium text-gray-900 mb-4">Upload Additional Documents</h3>
            <ManualDocumentUpload 
              offerId={parseInt(id || '0')}
              onSuccess={handleDocumentsUploaded}
            />
          </div>
        </div>

        {/* Tender Information */}
        {tender && (
          <div className="bg-white shadow rounded-lg p-6 mt-6">
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
            </div>
          </div>
        )}
        
        {/* Submit button at the bottom */}
        <div className="bg-white shadow rounded-lg p-6 mt-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-medium text-gray-900">Ready to Submit?</h2>
              <p className="mt-1 text-sm text-gray-600">
                Once you submit your offer, you won't be able to make any changes.
              </p>
            </div>
            <div>
              <button
                type="button"
                onClick={() => navigate(`/offers/${id}`)}
                className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                Go to Submission Page
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};