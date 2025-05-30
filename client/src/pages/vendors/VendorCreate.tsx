// client/src/pages/vendors/VendorCreate.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../api/api';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
}


const VendorCreate: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    registration_number: '',
    email: '',
    phone: '',
    address: '',
  });
  
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([]);

  useEffect(() => {
    // Fetch vendor users
    if (user?.role === 'admin') {
      fetchVendorUsers();
    }
  }, []);

  const fetchVendorUsers = async () => {
    try {
      const response = await api.users.getAll({ role: 'vendor' });
      
      // Handle different response structures
      let usersData = [];
      if (response) {
        if (Array.isArray(response)) {
          usersData = response;
        } else if (response.results && Array.isArray(response.results)) {
          usersData = response.results;
        } else if (typeof response === 'object') {
          usersData = Object.values(response);
        }
      }
      
      setAvailableUsers(usersData);
    } catch (err: any) {
      console.error('Error fetching vendor users:', err);
      setError(err.message || 'Failed to load vendor users');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleUserSelection = (userId: number) => {
    setSelectedUserIds(prev => {
      if (prev.includes(userId)) {
        return prev.filter(id => id !== userId);
      } else {
        return [...prev, userId];
      }
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name) {
      setError('Company name is required');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Create the vendor
      const vendorData = {
        ...formData,
        user_ids: selectedUserIds
      };
      
      const createdVendor = await api.vendor.create(vendorData);
      
      // Redirect to vendor detail page
      navigate(`/vendors/${createdVendor.id}`);
    } catch (err: any) {
      console.error('Error creating vendor:', err);
      setError(err.message || 'Failed to create vendor');
    } finally {
      setLoading(false);
    }
  };

  // Only allow admin to create vendors
  if (user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Access Denied</strong>
          <span className="block sm:inline"> You do not have permission to create vendors.</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Create New Vendor</h1>
          <p className="mt-1 text-sm text-gray-600">
            Fill in the details below to create a new vendor company.
          </p>
        </div>

        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        <form className="space-y-6" onSubmit={handleSubmit}>
          {/* Company Information */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Company Information</h2>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                  Company Name *
                </label>
                <input
                  type="text"
                  name="name"
                  id="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <div>
                <label htmlFor="registration_number" className="block text-sm font-medium text-gray-700">
                  Registration Number
                </label>
                <input
                  type="text"
                  name="registration_number"
                  id="registration_number"
                  value={formData.registration_number}
                  onChange={handleInputChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  Email
                </label>
                <input
                  type="email"
                  name="email"
                  id="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
                  Phone
                </label>
                <input
                  type="text"
                  name="phone"
                  id="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="address" className="block text-sm font-medium text-gray-700">
                  Address
                </label>
                <textarea
                  name="address"
                  id="address"
                  rows={3}
                  value={formData.address}
                  onChange={handleInputChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
          </div>

          {/* Associated Users */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Associated Users</h2>
            <p className="text-sm text-gray-600 mb-4">
              Select the users that should be associated with this vendor company. Only users with the vendor role are shown.
            </p>
            
            {availableUsers.length > 0 ? (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {availableUsers.map(vendorUser => (
                  <div key={vendorUser.id} className="flex items-center p-2 hover:bg-gray-50 rounded">
                    <input
                      type="checkbox"
                      id={`user-${vendorUser.id}`}
                      checked={selectedUserIds.includes(vendorUser.id)}
                      onChange={() => handleUserSelection(vendorUser.id)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor={`user-${vendorUser.id}`} className="ml-3 block text-sm font-medium text-gray-700">
                      <div>{vendorUser.username}</div>
                      <div className="text-xs text-gray-500">
                        {vendorUser.email} {vendorUser.first_name ? `(${vendorUser.first_name} ${vendorUser.last_name})` : ''}
                      </div>
                    </label>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">
                <p>No vendor users available. Please create users with the vendor role first.</p>
              </div>
            )}
          </div>

          {/* Submit Buttons */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex justify-end space-x-4">
              <button
                type="button"
                onClick={() => navigate('/vendors')}
                className="px-6 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {loading ? 'Creating...' : 'Create Vendor'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default VendorCreate;