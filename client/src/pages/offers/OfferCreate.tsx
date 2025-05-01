// client/src/pages/offers/OfferCreate.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { tenderApi, offerApi, documentApi } from '../../api/api';

interface TenderRequirement {
  id: number;
  description: string;
  document_type: string;
  is_mandatory: boolean;
}

interface Tender {
  id: number;
  title: string;
  reference_number: string;
  description: string;
  submission_deadline: string;
  status: string;
  requirements: TenderRequirement[];
}

const OfferCreate: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [tender, setTender] = useState<Tender | null>(null);
  const [uploadedDocuments, setUploadedDocuments] = useState<Map<string, File[]>>(new Map());
  
  // Form state
  const [formData, setFormData] = useState({
    price: '',
    notes: '',
  });

  // Get tender ID from URL query parameter
  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const tenderId = queryParams.get('tender');
    
    if (tenderId) {
      fetchTender(parseInt(tenderId));
    } else {
      setError('No tender specified');
      setLoading(false);
    }
  }, [location]);

  const fetchTender = async (tenderId: number) => {
    try {
      setLoading(true);
      const response = await tenderApi.getById(tenderId);
      
      // Verify tender is published
      if (response.status !== 'published') {
        setError('Tender is not open for offers');
        setLoading(false);
        return;
      }
      
      // Verify deadline hasn't passed
      const deadline = new Date(response.submission_deadline);
      if (deadline < new Date()) {
        setError('Submission deadline has passed');
        setLoading(false);
        return;
      }
      
      setTender(response);
    } catch (err: any) {
      console.error('Error fetching tender:', err);
      setError(err.message || 'Failed to load tender');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, documentType: string) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      setUploadedDocuments(prev => {
        const newMap = new Map(prev);
        newMap.set(documentType, files);
        return newMap;
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent, saveAsDraft: boolean = true) => {
    e.preventDefault();
    
    if (!tender) return;
    
    // Validate price if not draft
    if (!saveAsDraft && !formData.price) {
      setError('Please provide a price');
      return;
    }
    
    // Check if all mandatory requirements have documents
    if (!saveAsDraft) {
      const missingDocuments = tender.requirements
        .filter(req => req.is_mandatory)
        .filter(req => !uploadedDocuments.has(req.document_type));
      
      if (missingDocuments.length > 0) {
        setError(`Missing required documents: ${missingDocuments.map(req => req.description).join(', ')}`);
        return;
      }
    }
    
    try {
      setSubmitting(true);
      setError(null);
      
      // Create offer
      const offerData = {
        tender: tender.id,
        price: formData.price ? parseFloat(formData.price) : null,
        notes: formData.notes,
      };
      
      const createdOffer = await offerApi.create(offerData);
      
      // Upload documents
      for (const [documentType, files] of uploadedDocuments.entries()) {
        for (const file of files) {
          const formData = new FormData();
          formData.append('file', file);
          formData.append('offer_id', createdOffer.id.toString());
          formData.append('document_type', documentType);
          
          await documentApi.uploadOfferDocument(createdOffer.id, file, documentType);
        }
      }
      
      // Submit offer if not draft
      if (!saveAsDraft) {
        await offerApi.submit(createdOffer.id);
      }
      
      // Redirect to offer detail page
      navigate(`/offers/${createdOffer.id}`);
    } catch (err: any) {
      console.error('Error creating offer:', err);
      setError(err.message || 'Failed to create offer');
    } finally {
      setSubmitting(false);
    }
  };

  // Only allow vendors to create offers
  if (user?.role !== 'vendor') {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Access Denied</strong>
          <span className="block sm:inline"> Only vendors can create offers.</span>
        </div>
      </Layout>
    );
  }

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
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Create Offer</h1>
          <p className="mt-1 text-sm text-gray-600">
            For tender: {tender.reference_number} - {tender.title}
          </p>
        </div>

        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
          {/* Tender Information */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Tender Details</h2>
            <div className="grid grid-cols-1 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">Reference Number</label>
                <div className="mt-1 text-gray-900">{tender.reference_number}</div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Title</label>
                <div className="mt-1 text-gray-900">{tender.title}</div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Submission Deadline</label>
                <div className="mt-1 text-gray-900">{new Date(tender.submission_deadline).toLocaleString()}</div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Description</label>
                <div className="mt-1 text-gray-900 whitespace-pre-wrap">{tender.description}</div>
              </div>
            </div>
          </div>

          {/* Offer Information */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Offer Details</h2>
            <div className="grid grid-cols-1 gap-6">
              <div>
                <label htmlFor="price" className="block text-sm font-medium text-gray-700">
                  Price *
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="text-gray-500 sm:text-sm">$</span>
                  </div>
                  <input
                    type="number"
                    name="price"
                    id="price"
                    value={formData.price}
                    onChange={handleInputChange}
                    min="0"
                    step="0.01"
                    className="pl-7 mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>
              </div>
              
              <div>
                <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
                  Notes
                </label>
                <textarea
                  name="notes"
                  id="notes"
                  rows={4}
                  value={formData.notes}
                  onChange={handleInputChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
          </div>

          {/* Requirements and Documents */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Document Requirements</h2>
            <div className="space-y-6">
              {tender.requirements.map((requirement) => (
                <div key={requirement.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-md font-medium text-gray-900">{requirement.description}</h3>
                      <p className="text-sm text-gray-500">
                        Document Type: {requirement.document_type || 'Not specified'}
                      </p>
                    </div>
                    <div>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        requirement.is_mandatory 
                          ? 'bg-red-100 text-red-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {requirement.is_mandatory ? 'Required' : 'Optional'}
                      </span>
                    </div>
                  </div>
                  
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Upload Document
                    </label>
                    <div className="mt-1 flex items-center">
                      <input
                        type="file"
                        onChange={(e) => handleFileChange(e, requirement.document_type)}
                        className="block w-full text-sm text-gray-500
                          file:mr-4 file:py-2 file:px-4
                          file:rounded-md file:border-0
                          file:text-sm file:font-semibold
                          file:bg-blue-50 file:text-blue-700
                          hover:file:bg-blue-100"
                      />
                    </div>
                    {uploadedDocuments.has(requirement.document_type) && (
                      <div className="mt-2">
                        <p className="text-sm text-green-600">
                          {uploadedDocuments.get(requirement.document_type)?.length} file(s) selected
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {tender.requirements.length === 0 && (
                <p className="text-gray-500">No document requirements specified for this tender.</p>
              )}
            </div>
          </div>

          {/* Submit Buttons */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex justify-end space-x-4">
              <button
                type="button"
                onClick={() => navigate(`/tenders/${tender.id}`)}
                className="px-6 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={(e) => handleSubmit(e, true)}
                disabled={submitting}
                className="px-6 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {submitting ? 'Saving...' : 'Save as Draft'}
              </button>
              <button
                type="button"
                onClick={(e) => handleSubmit(e, false)}
                disabled={submitting}
                className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {submitting ? 'Submitting...' : 'Submit Offer'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default OfferCreate;