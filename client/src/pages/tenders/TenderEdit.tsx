// client/src/pages/tenders/TenderEdit.tsx
import React, { useState, useEffect, ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { tenderApi, documentApi } from '../../api/api';

interface Tender {
  reference_number: ReactNode;
  id: number;
  title: string;
  description: string;
  category: string;
  estimated_value: number;
  submission_deadline: string;
  opening_date: string;
  status: string;
  requirements?: any[];
  documents?: any[];
}

const TenderEdit: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [tender, setTender] = useState<Tender | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    estimated_value: '',
    submission_deadline: '',
    opening_date: '',
  });

  const [requirements, setRequirements] = useState<Array<{
    id?: number;
    description: string;
    document_type: string;
    is_mandatory: boolean;
  }>>([]);

  const [documents, setDocuments] = useState<File[]>([]);
  const [existingDocuments, setExistingDocuments] = useState<any[]>([]);

  useEffect(() => {
    fetchTender();
  }, [id]);

  const fetchTender = async () => {
    try {
      setLoading(true);
      const response = await tenderApi.getById(Number(id));
      setTender(response);
      
      // Format dates for datetime-local input
      const formattedData = {
        title: response.title,
        description: response.description,
        category: response.category || '',
        estimated_value: response.estimated_value ? response.estimated_value.toString() : '',
        submission_deadline: response.submission_deadline ? new Date(response.submission_deadline).toISOString().slice(0, 16) : '',
        opening_date: response.opening_date ? new Date(response.opening_date).toISOString().slice(0, 16) : '',
      };
      
      setFormData(formattedData);
      setRequirements(response.requirements || []);
      setExistingDocuments(response.documents || []);
    } catch (err: any) {
      console.error('Error fetching tender:', err);
      setError(err.message || 'Failed to load tender');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleAddRequirement = () => {
    setRequirements([...requirements, {
      description: '',
      document_type: '',
      is_mandatory: true
    }]);
  };

  const handleRequirementChange = (index: number, field: string, value: string | boolean) => {
    const newRequirements = [...requirements];
    newRequirements[index] = {
      ...newRequirements[index],
      [field]: value
    };
    setRequirements(newRequirements);
  };

  const handleRemoveRequirement = (index: number) => {
    setRequirements(requirements.filter((_, i) => i !== index));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setDocuments([...documents, ...Array.from(e.target.files)]);
    }
  };

  const handleRemoveDocument = (index: number) => {
    setDocuments(documents.filter((_, i) => i !== index));
  };

  const handleRemoveExistingDocument = async (documentId: number) => {
    try {
      await documentApi.deleteTenderDocument(documentId);
      setExistingDocuments(existingDocuments.filter(doc => doc.id !== documentId));
    } catch (err: any) {
      console.error('Error removing document:', err);
      alert(err.message || 'Failed to remove document');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!tender) return;

    if (!formData.title || !formData.description || !formData.submission_deadline) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      // Update the tender
      const tenderData = {
        ...formData,
        estimated_value: formData.estimated_value ? parseFloat(formData.estimated_value) : null,
      };

      await tenderApi.update(tender.id, tenderData);

      // Handle requirements
      // For simplicity, we'll delete all existing requirements and add new ones
      // In a production app, you'd want to implement proper CRUD for requirements
      if (tender.status === 'draft') {
        for (const requirement of requirements) {
          if (requirement.description && !requirement.id) {
            await tenderApi.addRequirement(tender.id, requirement);
          }
        }
      }

      // Upload new documents
      for (const file of documents) {
        await documentApi.uploadTenderDocument(tender.id, file);
      }

      // Redirect to tender detail page
      navigate(`/tenders/${tender.id}`);
    } catch (err: any) {
      console.error('Error updating tender:', err);
      setError(err.message || 'Failed to update tender');
    } finally {
      setSaving(false);
    }
  };

  // Only allow staff and admin to edit tenders
  if (user?.role !== 'staff' && user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Access Denied</strong>
          <span className="block sm:inline"> You do not have permission to edit tenders.</span>
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
          <h1 className="text-2xl font-bold text-gray-900">Edit Tender</h1>
          <p className="mt-1 text-sm text-gray-600">
            Update the details for tender {tender.reference_number}
          </p>
        </div>

        {tender.status !== 'draft' && (
          <div className="mb-4 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">
              This tender is {tender.status}. Some fields may not be editable.
            </span>
          </div>
        )}

        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Basic Information</h2>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                  Title *
                </label>
                <input
                  type="text"
                  name="title"
                  id="title"
                  value={formData.title}
                  onChange={handleInputChange}
                  required
                  disabled={tender.status !== 'draft'}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm disabled:bg-gray-100"
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                  Description *
                </label>
                <textarea
                  name="description"
                  id="description"
                  rows={4}
                  value={formData.description}
                  onChange={handleInputChange}
                  required
                  disabled={tender.status !== 'draft'}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm disabled:bg-gray-100"
                />
              </div>

              <div>
                <label htmlFor="category" className="block text-sm font-medium text-gray-700">
                  Category
                </label>
                <select
                  name="category"
                  id="category"
                  value={formData.category}
                  onChange={handleInputChange}
                  disabled={tender.status !== 'draft'}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm disabled:bg-gray-100"
                >
                  <option value="">Select category</option>
                  <option value="goods">Goods</option>
                  <option value="services">Services</option>
                  <option value="works">Works</option>
                </select>
              </div>

              <div>
                <label htmlFor="estimated_value" className="block text-sm font-medium text-gray-700">
                  Estimated Value
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="text-gray-500 sm:text-sm">$</span>
                  </div>
                  <input
                    type="number"
                    name="estimated_value"
                    id="estimated_value"
                    value={formData.estimated_value}
                    onChange={handleInputChange}
                    min="0"
                    step="0.01"
                    disabled={tender.status !== 'draft'}
                    className="pl-7 mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm disabled:bg-gray-100"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="submission_deadline" className="block text-sm font-medium text-gray-700">
                  Submission Deadline *
                </label>
                <input
                  type="datetime-local"
                  name="submission_deadline"
                  id="submission_deadline"
                  value={formData.submission_deadline}
                  onChange={handleInputChange}
                  required
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <div>
                <label htmlFor="opening_date" className="block text-sm font-medium text-gray-700">
                  Opening Date
                </label>
                <input
                  type="datetime-local"
                  name="opening_date"
                  id="opening_date"
                  value={formData.opening_date}
                  onChange={handleInputChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
          </div>

          {/* Requirements (only editable in draft status) */}
          {tender.status === 'draft' && (
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-medium text-gray-900">Requirements</h2>
                <button
                  type="button"
                  onClick={handleAddRequirement}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Add Requirement
                </button>
              </div>
              <div className="space-y-4">
                {requirements.map((requirement, index) => (
                  <div key={index} className="flex space-x-4 items-start">
                    <div className="flex-1">
                      <textarea
                        placeholder="Requirement description"
                        value={requirement.description}
                        onChange={(e) => handleRequirementChange(index, 'description', e.target.value)}
                        rows={2}
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      />
                    </div>
                    <div className="w-48">
                      <input
                        type="text"
                        placeholder="Document type"
                        value={requirement.document_type}
                        onChange={(e) => handleRequirementChange(index, 'document_type', e.target.value)}
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      />
                    </div>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        checked={requirement.is_mandatory}
                        onChange={(e) => handleRequirementChange(index, 'is_mandatory', e.target.checked)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <label className="ml-2 text-sm text-gray-700">Mandatory</label>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveRequirement(index)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <span className="material-icons">delete</span>
                    </button>
                  </div>
                ))}
                {requirements.length === 0 && (
                  <p className="text-gray-500 text-sm">No requirements added yet</p>
                )}
              </div>
            </div>
          )}

          {/* Documents */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Documents</h2>
            
            {/* Existing Documents */}
            {existingDocuments.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Existing Documents</h3>
                <div className="space-y-2">
                  {existingDocuments.map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                      <div className="flex items-center">
                        <span className="material-icons text-gray-400 mr-2">description</span>
                        <span className="text-sm text-gray-700">{doc.original_filename}</span>
                      </div>
                      {tender.status === 'draft' && (
                        <button
                          type="button"
                          onClick={() => handleRemoveExistingDocument(doc.id)}
                          className="text-red-600 hover:text-red-800"
                        >
                          <span className="material-icons">delete</span>
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Upload New Documents */}
            {tender.status === 'draft' && (
              <>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700">
                    Upload New Documents
                  </label>
                  <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                    <div className="space-y-1 text-center">
                      <span className="material-icons text-4xl text-gray-400">upload</span>
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
                            multiple
                            onChange={handleFileChange}
                            className="sr-only"
                          />
                        </label>
                        <p className="pl-1">or drag and drop</p>
                      </div>
                      <p className="text-xs text-gray-500">PDF, DOC, DOCX, XLS, XLSX up to 10MB</p>
                    </div>
                  </div>
                </div>
                {documents.length > 0 && (
                  <div className="space-y-2">
                    {documents.map((file, index) => (
                      <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                        <div className="flex items-center">
                          <span className="material-icons text-gray-400 mr-2">description</span>
                          <span className="text-sm text-gray-700">{file.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveDocument(index)}
                          className="text-red-600 hover:text-red-800"
                        >
                          <span className="material-icons">delete</span>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
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
                type="submit"
                disabled={saving}
                className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default TenderEdit;