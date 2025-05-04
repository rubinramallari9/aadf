// client/src/pages/offers/OfferEdit.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { offerApi, documentApi } from '../../api/api';

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
}

interface Document {
  id: number;
  filename: string;
  file_type: string;
  document_type: string;
  created_at: string;
}

const OfferEdit: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [offer, setOffer] = useState<Offer | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [formData, setFormData] = useState({
    price: '',
    currency: 'USD',
    delivery_time: '',
    delivery_time_unit: 'days',
    warranty_period: '',
    warranty_period_unit: 'months',
    technical_description: '',
    comment: '',
  });
  
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [documentType, setDocumentType] = useState<string>('');
  
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const currencyOptions = [
    { value: 'USD', label: 'USD - US Dollar' },
    { value: 'EUR', label: 'EUR - Euro' },
    { value: 'GBP', label: 'GBP - British Pound' },
    // Add more currency options as needed
  ];

  const timeUnitOptions = [
    { value: 'days', label: 'Days' },
    { value: 'weeks', label: 'Weeks' },
    { value: 'months', label: 'Months' },
  ];

  const documentTypeOptions = [
    { value: 'technical_specification', label: 'Technical Specification' },
    { value: 'financial_document', label: 'Financial Document' },
    { value: 'company_profile', label: 'Company Profile' },
    { value: 'certification', label: 'Certification' },
    { value: 'other', label: 'Other' },
  ];

  useEffect(() => {
    const fetchOfferData = async () => {
      try {
        setLoading(true);
        setError(null);

        if (!id) return;

        const offerData = await offerApi.getById(Number(id));
        setOffer(offerData);

        // Initialize form data with offer data
        setFormData({
          price: offerData.price.toString(),
          currency: offerData.currency || 'USD',
          delivery_time: offerData.delivery_time.toString(),
          delivery_time_unit: offerData.delivery_time_unit || 'days',
          warranty_period: offerData.warranty_period.toString(),
          warranty_period_unit: offerData.warranty_period_unit || 'months',
          technical_description: offerData.technical_description || '',
          comment: offerData.comment || '',
        });

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

  // Check if current user can edit this offer
  useEffect(() => {
    if (user && offer) {
      const isVendorOwner = user.role === 'vendor' && 
        offer.vendor && user.id === offer.vendor.id;
      
      const isDraftStatus = offer.status === 'draft';
      
      if (!(isVendorOwner && isDraftStatus)) {
        // Redirect if user doesn't have permission to edit
        navigate(`/offers/${id}`, { replace: true });
      }
    }
  }, [user, offer, id, navigate]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      if (!offer) return;
      
      // Validate form
      if (!formData.price || !formData.delivery_time || !formData.warranty_period) {
        setError('Please fill in all required fields.');
        setSaving(false);
        return;
      }
      
      // Prepare data for API
      const updateData = {
        price: parseFloat(formData.price),
        currency: formData.currency,
        delivery_time: parseInt(formData.delivery_time),
        delivery_time_unit: formData.delivery_time_unit,
        warranty_period: parseInt(formData.warranty_period),
        warranty_period_unit: formData.warranty_period_unit,
        technical_description: formData.technical_description,
        comment: formData.comment,
      };
      
      // Update offer
      await offerApi.update(offer.id, updateData);
      
      // Upload files if any
      if (files.length > 0) {
        setUploading(true);
        
        // Upload each file
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          await documentApi.uploadOfferDocument(offer.id, file, documentType);
          
          // Update progress
          setUploadProgress(Math.round(((i + 1) / files.length) * 100));
        }
        
        setUploading(false);
        setFiles([]);
        setUploadProgress(0);
        
        // Refresh documents list
        const updatedDocuments = await offerApi.getDocuments(offer.id);
        setDocuments(updatedDocuments);
      }
      
      setSuccess('Offer updated successfully');
      
      // Refresh offer data
      const updatedOffer = await offerApi.getById(offer.id);
      setOffer(updatedOffer);
    } catch (err: any) {
      console.error('Error updating offer:', err);
      setError(err.message || 'Failed to update offer');
    } finally {
      setSaving(false);
    }
  };

  const deleteDocument = async (documentId: number) => {
    try {
      if (!offer) return;
      
      await documentApi.deleteOfferDocument(documentId);
      
      // Refresh documents list
      const updatedDocuments = await offerApi.getDocuments(offer.id);
      setDocuments(updatedDocuments);
      
      setSuccess('Document deleted successfully');
    } catch (err: any) {
      console.error('Error deleting document:', err);
      setError(err.message || 'Failed to delete document');
    }
  };

  const getDocumentDownloadUrl = (documentId: number) => {
    return documentApi.getDocumentDownloadUrl('offer-document', documentId);
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

  if (!offer) {
    return (
      <Layout>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Offer Not Found</h1>
          <p className="mt-2 text-gray-600">The offer you are trying to edit does not exist or you do not have permission to edit it.</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Edit Offer</h1>
            <p className="text-gray-600">
              For Tender: {offer.tender.reference_number} - {offer.tender.title}
            </p>
          </div>
          <button
            onClick={() => navigate(`/offers/${offer.id}`)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <span className="material-icons mr-2 text-sm">arrow_back</span>
            Back to Offer
          </button>
        </div>
        
        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}
        
        {success && (
          <div className="mb-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{success}</span>
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Financial Details */}
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Financial Details
              </h3>
            </div>
            <div className="px-4 py-5 sm:p-6">
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label htmlFor="price" className="block text-sm font-medium text-gray-700">
                    Price *
                  </label>
                  <div className="mt-1 relative rounded-md shadow-sm">
                    <input
                      type="number"
                      name="price"
                      id="price"
                      className="focus:ring-blue-500 focus:border-blue-500 block w-full pr-12 sm:text-sm border-gray-300 rounded-md"
                      placeholder="0.00"
                      step="0.01"
                      min="0"
                      value={formData.price}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                </div>
                
                <div>
                  <label htmlFor="currency" className="block text-sm font-medium text-gray-700">
                    Currency *
                  </label>
                  <select
                    id="currency"
                    name="currency"
                    className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    value={formData.currency}
                    onChange={handleInputChange}
                    required
                  >
                    {currencyOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>
          
          {/* Technical Details */}
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Technical Details
              </h3>
            </div>
            <div className="px-4 py-5 sm:p-6">
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label htmlFor="delivery_time" className="block text-sm font-medium text-gray-700">
                    Delivery Time *
                  </label>
                  <div className="mt-1 flex rounded-md shadow-sm">
                    <input
                      type="number"
                      name="delivery_time"
                      id="delivery_time"
                      className="focus:ring-blue-500 focus:border-blue-500 flex-1 block w-full rounded-none rounded-l-md sm:text-sm border-gray-300"
                      placeholder="0"
                      min="1"
                      value={formData.delivery_time}
                      onChange={handleInputChange}
                      required
                    />
                    <select
                      name="delivery_time_unit"
                      id="delivery_time_unit"
                      className="focus:ring-blue-500 focus:border-blue-500 inline-flex items-center px-3 rounded-r-md border border-l-0 border-gray-300 bg-gray-50 text-gray-500 sm:text-sm"
                      value={formData.delivery_time_unit}
                      onChange={handleInputChange}
                    >
                      {timeUnitOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                
                <div>
                  <label htmlFor="warranty_period" className="block text-sm font-medium text-gray-700">
                    Warranty Period *
                  </label>
                  <div className="mt-1 flex rounded-md shadow-sm">
                    <input
                      type="number"
                      name="warranty_period"
                      id="warranty_period"
                      className="focus:ring-blue-500 focus:border-blue-500 flex-1 block w-full rounded-none rounded-l-md sm:text-sm border-gray-300"
                      placeholder="0"
                      min="0"
                      value={formData.warranty_period}
                      onChange={handleInputChange}
                      required
                    />
                    <select
                      name="warranty_period_unit"
                      id="warranty_period_unit"
                      className="focus:ring-blue-500 focus:border-blue-500 inline-flex items-center px-3 rounded-r-md border border-l-0 border-gray-300 bg-gray-50 text-gray-500 sm:text-sm"
                      value={formData.warranty_period_unit}
                      onChange={handleInputChange}
                    >
                      {timeUnitOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                
                <div className="sm:col-span-2">
                  <label htmlFor="technical_description" className="block text-sm font-medium text-gray-700">
                    Technical Description
                  </label>
                  <div className="mt-1">
                    <textarea
                      id="technical_description"
                      name="technical_description"
                      rows={5}
                      className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
                      placeholder="Provide a detailed technical description of your offer..."
                      value={formData.technical_description}
                      onChange={handleInputChange}
                    />
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    Include specifications, features, and any other technical details relevant to your offer.
                  </p>
                </div>
                
                <div className="sm:col-span-2">
                  <label htmlFor="comment" className="block text-sm font-medium text-gray-700">
                    Additional Comments
                  </label>
                  <div className="mt-1">
                    <textarea
                      id="comment"
                      name="comment"
                      rows={3}
                      className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
                      placeholder="Any additional information or comments..."
                      value={formData.comment}
                      onChange={handleInputChange}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Documents */}
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Documents
              </h3>
            </div>
            <div className="px-4 py-5 sm:p-6">
              {/* Current Documents */}
              {documents.length > 0 && (
                <div className="mb-6">
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Current Documents</h4>
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
                        <div className="flex space-x-2">
                          <a
                            href={getDocumentDownloadUrl(document.id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center"
                          >
                            <span className="material-icons text-sm mr-1">download</span>
                            Download
                          </a>
                          <button
                            type="button"
                            onClick={() => deleteDocument(document.id)}
                            className="text-red-600 hover:text-red-800 text-sm font-medium flex items-center"
                          >
                            <span className="material-icons text-sm mr-1">delete</span>
                            Delete
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Upload New Documents */}
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">Upload New Documents</h4>
                <div className="mb-4">
                  <label htmlFor="documentType" className="block text-sm font-medium text-gray-700">
                    Document Type
                  </label>
                  <select
                    id="documentType"
                    name="documentType"
                    className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    value={documentType}
                    onChange={(e) => setDocumentType(e.target.value)}
                  >
                    <option value="">Select a document type</option>
                    {documentTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="mt-2">
                  <div className="flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                    <div className="space-y-1 text-center">
                      <svg
                        className="mx-auto h-12 w-12 text-gray-400"
                        stroke="currentColor"
                        fill="none"
                        viewBox="0 0 48 48"
                        aria-hidden="true"
                      >
                        <path
                          d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4h-12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                          strokeWidth={2}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      <div className="flex text-sm text-gray-600">
                        <label
                          htmlFor="file-upload"
                          className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500"
                        >
                          <span>Upload files</span>
                          <input
                            id="file-upload"
                            name="file-upload"
                            type="file"
                            className="sr-only"
                            multiple
                            onChange={handleFileChange}
                          />
                        </label>
                        <p className="pl-1">or drag and drop</p>
                      </div>
                      <p className="text-xs text-gray-500">
                        PDF, Word, Excel, or image files up to 10MB
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Show selected files */}
                {files.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Selected Files</h4>
                    <ul className="divide-y divide-gray-200 border rounded-md">
                      {files.map((file, index) => (
                        <li key={index} className="py-2 px-4 flex justify-between items-center">
                          <div className="flex items-center">
                            <span className="material-icons text-gray-400 mr-2">
                              {file.type.includes('pdf') ? 'picture_as_pdf' :
                              file.type.includes('word') ? 'description' :
                              file.type.includes('image') ? 'image' :
                              file.type.includes('excel') ? 'table_chart' : 'insert_drive_file'}
                            </span>
                            <span className="text-sm text-gray-900">{file.name}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeFile(index)}
                            className="text-red-600 hover:text-red-800"
                          >
                            <span className="material-icons">close</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {/* Upload progress */}
                {uploading && (
                  <div className="mt-4">
                    <div className="flex justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">Uploading</span>
                      <span className="text-sm font-medium text-gray-700">{uploadProgress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${uploadProgress}%` }}></div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Submit buttons */}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => navigate(`/offers/${offer.id}`)}
              className="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 mr-3"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || uploading}
              className={`inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                (saving || uploading) ? 'opacity-70 cursor-not-allowed' : ''
              }`}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default OfferEdit;