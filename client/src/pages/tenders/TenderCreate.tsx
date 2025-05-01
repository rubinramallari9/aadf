// client/src/pages/tenders/TenderCreate.tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { tenderApi, documentApi } from '../../api/api';

const TenderCreate: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

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
    description: string;
    document_type: string;
    is_mandatory: boolean;
  }>>([]);

  const [documents, setDocuments] = useState<File[]>([]);

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

  const handleSubmit = async (e: React.FormEvent, status: 'draft' | 'published') => {
    e.preventDefault();
    
    if (!formData.title || !formData.description || !formData.submission_deadline) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Create the tender
      const tenderData = {
        ...formData,
        estimated_value: formData.estimated_value ? parseFloat(formData.estimated_value) : null,
        status: status
      };

      const createdTender = await tenderApi.create(tenderData);

      // Add requirements
      for (const requirement of requirements) {
        if (requirement.description) {
          await tenderApi.addRequirement(createdTender.id, requirement);
        }
      }

      // Upload documents
      for (const file of documents) {
        await documentApi.uploadTenderDocument(createdTender.id, file);
      }

      // Redirect to tender detail page
      navigate(`/tenders/${createdTender.id}`);
    } catch (err: any) {
      console.error('Error creating tender:', err);
      setError(err.message || 'Failed to create tender');
    } finally {
      setLoading(false);
    }
  };

  // Only allow staff and admin to create tenders
  if (user?.role !== 'staff' && user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Access Denied</strong>
          <span className="block sm:inline"> You do not have permission to create tenders.</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Create New Tender</h1>
          <p className="mt-1 text-sm text-gray-600">
            Fill in the details below to create a new tender.
          </p>
        </div>

        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
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
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
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
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
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
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
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
                    className="pl-7 mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
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

          {/* Requirements */}
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

          {/* Documents */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Documents</h2>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">
                Upload Documents
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
          </div>

          {/* Submit Buttons */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex justify-end space-x-4">
              <button
                type="button"
                onClick={(e) => handleSubmit(e, 'draft')}
                disabled={loading}
                className="px-6 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {loading ? 'Saving...' : 'Save as Draft'}
              </button>
              <button
                type="button"
                onClick={(e) => handleSubmit(e, 'published')}
                disabled={loading}
                className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {loading ? 'Publishing...' : 'Publish Tender'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default TenderCreate;