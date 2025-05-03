// client/src/pages/offers/OfferCreate.tsx - Updated with VendorContext
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { useVendor } from '../../contexts/VendorContext'; // Import VendorContext
import api from '../../api/api';

// Add interface for tender
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

const OfferCreate: React.FC = () => {
  const { user } = useAuth();
  const { currentVendor } = useVendor(); // Use the VendorContext to get the current vendor
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get tender_id from query params if present
  const queryParams = new URLSearchParams(location.search);
  const tenderId = queryParams.get('tender');
  
  const [loading, setLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // State for form data
  const [formData, setFormData] = useState({
    tender: tenderId ? parseInt(tenderId) : 0,
    price: '',
    notes: '',
  });
  
  // State for files
  const [files, setFiles] = useState<Record<string, File | null>>({});
  
  // State for tender and requirements
  const [tender, setTender] = useState<Tender | null>(null);
  const [availableTenders, setAvailableTenders] = useState<Tender[]>([]);

  useEffect(() => {
    // Fetch available tenders
    const fetchTenders = async () => {
      try {
        setLoading(true);
        const response = await api.tenders.getAll({ status: 'published' });
        
        // Handle different response structures
        let tendersData = [];
        if (response) {
          if (Array.isArray(response)) {
            tendersData = response;
          } else if (response.results && Array.isArray(response.results)) {
            tendersData = response.results;
          } else if (typeof response === 'object') {
            tendersData = Object.values(response);
          }
        }
        
        setAvailableTenders(tendersData);
        
        // If tenderId is provided, fetch that tender specifically
        if (tenderId) {
          const tenderResponse = await api.tenders.getById(parseInt(tenderId));
          setTender(tenderResponse);
        }
      } catch (err: any) {
        console.error('Error fetching tenders:', err);
        setError(err.message || 'Failed to load tenders');
      } finally {
        setLoading(false);
      }
    };
    
    fetchTenders();
  }, [tenderId]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    
    if (name === 'tender') {
      // If tender is changed, fetch that tender's details
      const selectedTenderId = parseInt(value);
      
      if (selectedTenderId) {
        const fetchTender = async () => {
          try {
            setLoading(true);
            const tenderResponse = await api.tenders.getById(selectedTenderId);
            setTender(tenderResponse);
            
            // Clear any existing files when tender changes
            setFiles({});
          } catch (err: any) {
            console.error('Error fetching tender:', err);
            setError(err.message || 'Failed to load tender');
          } finally {
            setLoading(false);
          }
        };
        
        fetchTender();
      } else {
        setTender(null);
        setFiles({});
      }
    }
    
    setFormData(prev => ({
      ...prev,
      [name]: name === 'tender' || name === 'price' ? parseInt(value) || value : value
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, documentType: string) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      
      // Validate file size (10MB max)
      if (file.size > 10 * 1024 * 1024) {
        setError(`File ${file.name} is too large. Maximum file size is 10MB.`);
        return;
      }
      
      // Add file to state
      setFiles(prev => ({
        ...prev,
        [documentType]: file
      }));
      
      // Clear error if any
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate form
    if (!formData.tender) {
      setError('Please select a tender');
      return;
    }
    
    // Validate vendor company
    if (!currentVendor) {
      setError('No vendor company associated with your account');
      return;
    }
    
    // Validate required files
    if (tender && tender.requirements) {
      const missingFiles = tender.requirements
        .filter(req => req.is_mandatory && !files[req.document_type])
        .map(req => req.description);
        
      if (missingFiles.length > 0) {
        setError(`Missing required documents: ${missingFiles.join(', ')}`);
        return;
      }
    }
    
    try {
      setSubmitting(true);
      setError(null);
      
      // Create the offer
      const offerData = {
        ...formData,
        vendor: currentVendor.id // Use the vendor from context
      };
      
      console.log('Submitting offer data:', offerData); // Debug log
      
      const createdOffer = await api.offers.create(offerData);
      
      // Upload files if any
      const offerId = createdOffer.id;
      const filePromises = Object.entries(files)
        .filter(([_, file]) => file !== null)
        .map(([documentType, file]) => {
          if (file) {
            return api.documents.uploadOfferDocument(offerId, file, documentType);
          }
          return Promise.resolve();
        });
        
      await Promise.all(filePromises);
      
      // Show success message
      setSuccessMessage('Offer created successfully!');
      
      // Redirect to offer detail after a short delay
      setTimeout(() => {
        navigate(`/offers/${offerId}`);
      }, 2000);
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
  
  // Show error if user doesn't have a vendor company
  if (!loading && !currentVendor) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error</strong>
          <span className="block sm:inline"> You must be associated with a vendor company to create offers. Please contact an administrator.</span>
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
            Fill in the details below to create a new offer for a tender.
          </p>
          {currentVendor && (
            <p className="mt-1 text-sm font-medium text-blue-600">
              Creating offer as: {currentVendor.name}
            </p>
          )}
        </div>

        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}
        
        {successMessage && (
          <div className="mb-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{successMessage}</span>
          </div>
        )}

        <form className="space-y-6" onSubmit={handleSubmit}>
          {/* Tender Selection */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Tender Information</h2>
            
            <div className="mb-4">
              <label htmlFor="tender" className="block text-sm font-medium text-gray-700">
                Select Tender *
              </label>
              <select
                id="tender"
                name="tender"
                value={formData.tender || ''}
                onChange={handleInputChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                required
                disabled={tenderId !== null || loading}
              >
                <option value="">-- Select a Tender --</option>
                {availableTenders.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.reference_number} - {t.title}
                  </option>
                ))}
              </select>
            </div>
            
            {tender && (
              <div className="mt-4 p-4 bg-gray-50 rounded">
                <h3 className="text-md font-semibold">{tender.reference_number}</h3>
                <p className="text-sm text-gray-600">{tender.title}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Deadline: {new Date(tender.submission_deadline).toLocaleString()}
                </p>
              </div>
            )}
          </div>

          {/* Offer Details */}
          {tender && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Offer Details</h2>
              
              <div className="mb-4">
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
              
              <div className="mb-4">
                <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
                  Additional Notes
                </label>
                <textarea
                  id="notes"
                  name="notes"
                  rows={3}
                  value={formData.notes}
                  onChange={handleInputChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
          )}

          {/* Required Documents */}
          {tender && tender.requirements && tender.requirements.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Required Documents</h2>
              
              {tender.requirements.map((requirement) => (
                <div key={requirement.id} className="mb-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {requirement.description}
                    {requirement.is_mandatory && <span className="text-red-500">*</span>}
                  </label>
                  <div className="mt-1 flex items-center">
                    <input
                      type="file"
                      onChange={(e) => handleFileChange(e, requirement.document_type)}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                      required={requirement.is_mandatory}
                    />
                    {files[requirement.document_type] && (
                      <span className="ml-2 text-green-600">
                        <span className="material-icons text-sm">check_circle</span>
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-gray-500">Document type: {requirement.document_type}</p>
                </div>
              ))}
            </div>
          )}

          {/* Submit Buttons */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex justify-end space-x-4">
              <button
                type="button"
                onClick={() => navigate('/tenders')}
                className="px-6 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || !tender}
                className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {submitting ? 'Creating...' : 'Create Offer'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default OfferCreate;