// client/src/pages/users/UserEdit.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { usersApi } from '../../api/api';

// Define the form data type
interface UserFormData {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
}

const UserEdit: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [formData, setFormData] = useState<UserFormData>({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    role: 'staff',
    is_active: true
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Only admin can access this page
  if (user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded-lg shadow-sm" role="alert">
          <div className="flex items-center">
            <span className="material-icons mr-2">warning</span>
            <strong className="font-bold">Access Denied</strong>
          </div>
          <span className="block sm:inline mt-1"> You do not have permission to edit users.</span>
        </div>
      </Layout>
    );
  }

  // Fetch user data on component mount
  useEffect(() => {
    if (id) {
      fetchUserData(parseInt(id));
    }
  }, [id]);

  const fetchUserData = async (userId: number) => {
    try {
      setLoading(true);
      setError(null);
      
      const userData = await usersApi.getById(userId);
      
      // Set form data with fetched user data
      setFormData({
        username: userData.username,
        email: userData.email,
        first_name: userData.first_name || '',
        last_name: userData.last_name || '',
        role: userData.role,
        is_active: userData.is_active
      });
    } catch (err: any) {
      console.error('Error fetching user data:', err);
      setError(err.message || 'Failed to fetch user data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checkbox = e.target as HTMLInputElement;
      setFormData(prev => ({
        ...prev,
        [name]: checkbox.checked
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!formData.username || !formData.email) {
      setError('Please fill out all required fields.');
      return;
    }
    
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      if (id) {
        await usersApi.update(parseInt(id), formData);
        setSuccess('User updated successfully.');
        
        // Wait a moment before redirecting
        setTimeout(() => {
          navigate('/users');
        }, 1500);
      }
    } catch (err: any) {
      console.error('Error updating user:', err);
      setError(err.message || 'Failed to update user. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleActivateOrDeactivate = async () => {
    if (!id) return;
    
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      if (formData.is_active) {
        await usersApi.deactivate(parseInt(id));
        setFormData(prev => ({ ...prev, is_active: false }));
        setSuccess('User deactivated successfully.');
      } else {
        await usersApi.activate(parseInt(id));
        setFormData(prev => ({ ...prev, is_active: true }));
        setSuccess('User activated successfully.');
      }
    } catch (err: any) {
      console.error('Error changing user status:', err);
      setError(err.message || 'Failed to change user status. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleResetPassword = () => {
    // Navigate to reset password page
    if (id) {
      navigate(`/users/${id}/reset-password`);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Edit User</h1>
          <div>
            <button
              type="button"
              onClick={handleActivateOrDeactivate}
              className={`mr-3 inline-flex items-center px-3 py-2 border rounded-md shadow-sm text-sm leading-4 font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                formData.is_active 
                  ? 'border-red-300 text-red-700 bg-white hover:bg-red-50' 
                  : 'border-green-300 text-green-700 bg-white hover:bg-green-50'
              }`}
              disabled={saving}
            >
              <span className="material-icons text-sm mr-1">
                {formData.is_active ? 'block' : 'check_circle'}
              </span>
              {formData.is_active ? 'Deactivate' : 'Activate'}
            </button>
            
            <button
              type="button"
              onClick={handleResetPassword}
              className="inline-flex items-center px-3 py-2 border border-blue-300 rounded-md shadow-sm text-sm leading-4 font-medium text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              disabled={saving}
            >
              <span className="material-icons text-sm mr-1">lock_reset</span>
              Reset Password
            </button>
          </div>
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
        
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              {/* Username field - disabled because we don't allow editing username */}
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                  Username
                </label>
                <input
                  type="text"
                  id="username"
                  name="username"
                  value={formData.username}
                  disabled
                  className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
                <p className="mt-1 text-xs text-gray-500">Username cannot be changed</p>
              </div>
              
              {/* Email field */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              
              {/* First name field */}
              <div>
                <label htmlFor="first_name" className="block text-sm font-medium text-gray-700">
                  First Name
                </label>
                <input
                  type="text"
                  id="first_name"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              
              {/* Last name field */}
              <div>
                <label htmlFor="last_name" className="block text-sm font-medium text-gray-700">
                  Last Name
                </label>
                <input
                  type="text"
                  id="last_name"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
              
              {/* Role field */}
              <div>
                <label htmlFor="role" className="block text-sm font-medium text-gray-700">
                  Role <span className="text-red-500">*</span>
                </label>
                <select
                  id="role"
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option value="admin">Admin</option>
                  <option value="staff">Staff</option>
                  <option value="evaluator">Evaluator</option>
                  <option value="vendor">Vendor</option>
                </select>
              </div>
              
              {/* Active status */}
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_active"
                  name="is_active"
                  checked={formData.is_active}
                  onChange={handleChange}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900">
                  Active Account
                </label>
              </div>
            </div>
            
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => navigate('/users')}
                className="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Layout>
  );
};

export default UserEdit;