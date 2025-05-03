// client/src/pages/AdminDashboard.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { useAuth } from '../contexts/AuthContext';
import { dashboardApi, usersApi, authApi } from '../api/api';

// Define interfaces for user management
interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
  date_joined: string;
}

interface UserFormData {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
}

const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // States for user management modal
  const [showUserModal, setShowUserModal] = useState<boolean>(false);
  const [userFormData, setUserFormData] = useState<UserFormData>({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    role: 'staff',
    is_active: true
  });
  const [isEditMode, setIsEditMode] = useState<boolean>(false);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [resetPasswordMode, setResetPasswordMode] = useState<boolean>(false);
  const [newPassword, setNewPassword] = useState<string>('');

  useEffect(() => {
    fetchDashboardData();
    fetchUsers();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const data = await dashboardApi.getDashboardData();
      setDashboardData(data);
    } catch (err: any) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await usersApi.getAll();
      // Handle different response formats
      let usersData = [];
      if (Array.isArray(response)) {
        usersData = response;
      } else if (response?.results && Array.isArray(response.results)) {
        usersData = response.results;
      } else if (typeof response === 'object') {
        usersData = Object.values(response);
      }
      setUsers(usersData);
    } catch (err: any) {
      console.error('Error fetching users:', err);
      setError(err.message || 'Failed to load users');
    }
  };

  const handleUserFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checkbox = e.target as HTMLInputElement;
      setUserFormData({ ...userFormData, [name]: checkbox.checked });
    } else {
      setUserFormData({ ...userFormData, [name]: value });
    }
  };

  // client/src/pages/AdminDashboard.tsx

const handleSubmitUserForm = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEditMode && selectedUserId) {
        // Update existing user with authApi.updateProfile
        await authApi.updateProfile({
          ...userFormData,
          id: selectedUserId
        });
      } else {
        // Create new user with authApi.adminCreateUser instead of authApi.register
        await authApi.adminCreateUser({
          ...userFormData,
          // Ensure password is included for new users
          password: userFormData.password || ''
        });
      }
      
      // Refresh user list and close modal
      fetchUsers();
      closeUserModal();
    } catch (err: any) {
      console.error('Error saving user:', err);
      setError(err.message || 'Failed to save user');
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (selectedUserId && newPassword) {
        await usersApi.resetPassword(selectedUserId, newPassword);
        setResetPasswordMode(false);
        setNewPassword('');
        closeUserModal();
      }
    } catch (err: any) {
      console.error('Error resetting password:', err);
      setError(err.message || 'Failed to reset password');
    }
  };

  const openCreateUserModal = () => {
    setUserFormData({
      username: '',
      email: '',
      password: '',
      first_name: '',
      last_name: '',
      role: 'staff',
      is_active: true
    });
    setIsEditMode(false);
    setSelectedUserId(null);
    setShowUserModal(true);
  };

  const openEditUserModal = (user: User) => {
    setUserFormData({
      username: user.username,
      email: user.email,
      password: '', // Don't include password in edit mode
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      role: user.role,
      is_active: user.is_active
    });
    setIsEditMode(true);
    setSelectedUserId(user.id);
    setShowUserModal(true);
  };

  const openResetPasswordModal = (userId: number) => {
    setSelectedUserId(userId);
    setResetPasswordMode(true);
    setNewPassword('');
    setShowUserModal(true);
  };

  const closeUserModal = () => {
    setShowUserModal(false);
    setResetPasswordMode(false);
    setNewPassword('');
    // Clear any error message
    setError(null);
  };

  // Only allow admin to access this page
  if (user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded-lg shadow-sm" role="alert">
          <div className="flex items-center">
            <span className="material-icons mr-2">warning</span>
            <strong className="font-bold">Access Denied</strong>
          </div>
          <span className="block sm:inline mt-1"> You do not have permission to access the admin dashboard.</span>
        </div>
      </Layout>
    );
  }

  if (loading && !dashboardData) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Admin Dashboard</h1>
        <p className="text-gray-600">Manage users, view system statistics, and monitor platform activity</p>
      </div>

      {error && (
        <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {/* Overview Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {/* User Stats Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-purple-100 text-purple-600">
              <span className="material-icons">people</span>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500 font-semibold">Total Users</p>
              <p className="text-2xl font-bold text-gray-800">{dashboardData?.users?.total || 0}</p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <div className="text-sm">
              <p className="text-gray-500">Staff</p>
              <p className="font-medium">{dashboardData?.users?.staff || 0}</p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Admin</p>
              <p className="font-medium">{dashboardData?.users?.admin || 0}</p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Vendors</p>
              <p className="font-medium">{dashboardData?.users?.vendor || 0}</p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Evaluators</p>
              <p className="font-medium">{dashboardData?.users?.evaluator || 0}</p>
            </div>
          </div>
        </div>

        {/* Tender Stats Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100 text-blue-600">
              <span className="material-icons">business_center</span>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500 font-semibold">Total Tenders</p>
              <p className="text-2xl font-bold text-gray-800">{dashboardData?.tenders?.total || 0}</p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <div className="text-sm">
              <p className="text-gray-500">Published</p>
              <p className="font-medium">{dashboardData?.tenders?.published || 0}</p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Draft</p>
              <p className="font-medium">{dashboardData?.tenders?.draft || 0}</p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Closed</p>
              <p className="font-medium">{dashboardData?.tenders?.closed || 0}</p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Awarded</p>
              <p className="font-medium">{dashboardData?.tenders?.awarded || 0}</p>
            </div>
          </div>
        </div>

        {/* Offers Stats Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100 text-green-600">
              <span className="material-icons">local_offer</span>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500 font-semibold">Total Offers</p>
              <p className="text-2xl font-bold text-gray-800">{dashboardData?.offers?.total || 0}</p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <div className="text-sm">
              <p className="text-gray-500">Submitted</p>
              <p className="font-medium">{dashboardData?.offers?.submitted || 0}</p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Evaluated</p>
              <p className="font-medium">{dashboardData?.offers?.evaluated || 0}</p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Awarded</p>
              <p className="font-medium">{dashboardData?.offers?.awarded || 0}</p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Rejected</p>
              <p className="font-medium">{dashboardData?.offers?.rejected || 0}</p>
            </div>
          </div>
        </div>

        {/* Vendor Stats Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
              <span className="material-icons">store</span>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500 font-semibold">Vendor Companies</p>
              <p className="text-2xl font-bold text-gray-800">{dashboardData?.vendors?.total || 0}</p>
            </div>
          </div>
          <div className="mt-4">
            <Link 
              to="/vendors" 
              className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center"
            >
              View all vendors
              <span className="material-icons text-base ml-1">arrow_forward</span>
            </Link>
          </div>
        </div>
      </div>

      {/* User Management */}
      <div className="bg-white shadow rounded-lg mb-8">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-medium text-gray-900">User Management</h2>
          <button
            onClick={openCreateUserModal}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            <span className="material-icons mr-2 text-sm">add</span>
            Create User
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Username
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Joined
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {user.username}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {user.first_name} {user.last_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {user.email}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      user.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                      user.role === 'staff' ? 'bg-blue-100 text-blue-800' :
                      user.role === 'evaluator' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(user.date_joined).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => openEditUserModal(user)}
                      className="text-blue-600 hover:text-blue-900 mr-3"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => openResetPasswordModal(user.id)}
                      className="text-green-600 hover:text-green-900"
                    >
                      Reset Password
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Recent Activity</h2>
        </div>
        <div className="p-6">
          <div className="space-y-6">
            {/* Recent Tenders */}
            <div>
              <h3 className="text-md font-medium text-gray-700 mb-3">Recent Tenders</h3>
              {dashboardData?.recent_tenders && dashboardData.recent_tenders.length > 0 ? (
                <div className="space-y-3">
                  {dashboardData.recent_tenders.map((tender: any) => (
                    <div key={tender.id} className="flex items-start">
                      <span className="material-icons text-blue-500 mr-3">business_center</span>
                      <div>
                        <Link to={`/tenders/${tender.id}`} className="text-blue-600 hover:text-blue-800 font-medium">
                          {tender.reference_number}
                        </Link>
                        <p className="text-sm text-gray-600">{tender.title}</p>
                        <div className="mt-1 flex items-center text-xs text-gray-500">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            tender.status === 'published' ? 'bg-green-100 text-green-800' :
                            tender.status === 'draft' ? 'bg-gray-100 text-gray-800' :
                            tender.status === 'closed' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-blue-100 text-blue-800'
                          }`}>
                            {tender.status}
                          </span>
                          <span className="mx-2">•</span>
                          <span>{new Date(tender.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">No recent tenders found</p>
              )}
            </div>

            {/* Recent Offers */}
            <div>
              <h3 className="text-md font-medium text-gray-700 mb-3">Recent Offers</h3>
              {dashboardData?.recent_offers && dashboardData.recent_offers.length > 0 ? (
                <div className="space-y-3">
                  {dashboardData.recent_offers.map((offer: any) => (
                    <div key={offer.id} className="flex items-start">
                      <span className="material-icons text-green-500 mr-3">local_offer</span>
                      <div>
                        <Link to={`/offers/${offer.id}`} className="text-blue-600 hover:text-blue-800 font-medium">
                          {offer.tender__reference_number}
                        </Link>
                        <p className="text-sm text-gray-600">{offer.vendor__name}</p>
                        <div className="mt-1 flex items-center text-xs text-gray-500">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            offer.status === 'submitted' ? 'bg-green-100 text-green-800' :
                            offer.status === 'draft' ? 'bg-gray-100 text-gray-800' :
                            offer.status === 'evaluated' ? 'bg-yellow-100 text-yellow-800' :
                            offer.status === 'awarded' ? 'bg-blue-100 text-blue-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {offer.status}
                          </span>
                          <span className="mx-2">•</span>
                          <span>{new Date(offer.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">No recent offers found</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* User Modal - FIXED VERSION */}
      {showUserModal && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen p-4">
            {/* Background overlay - Make sure the onClick is directly on this element */}
            <div 
              className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
              onClick={closeUserModal}
              aria-hidden="true"
            ></div>
            
            {/* Modal panel - Stop propagation to prevent clicks from closing the modal */}
            <div 
              className="bg-white rounded-lg overflow-hidden shadow-xl transform transition-all max-w-lg w-full z-50 relative"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="bg-white px-4 py-5">
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                    <h3 className="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                      {resetPasswordMode ? 'Reset Password' : isEditMode ? 'Edit User' : 'Create User'}
                    </h3>
                    
                    {error && (
                      <div className="mt-2 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                        <span className="block sm:inline">{error}</span>
                      </div>
                    )}
                    
                    {resetPasswordMode ? (
                      <form onSubmit={handleResetPassword} className="mt-4">
                        <div className="mb-4">
                          <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700">New Password</label>
                          <input
                            type="password"
                            id="newPassword"
                            name="newPassword"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            required
                            minLength={8}
                          />
                        </div>
                        <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                          <button
                            type="submit"
                            className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:col-start-2 sm:text-sm"
                          >
                            Reset Password
                          </button>
                          <button
                            type="button"
                            onClick={closeUserModal}
                            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                          >
                            Cancel
                          </button>
                        </div>
                      </form>
                    ) : (
                      <form onSubmit={handleSubmitUserForm} className="mt-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="mb-4">
                            <label htmlFor="username" className="block text-sm font-medium text-gray-700">Username</label>
                            <input
                              type="text"
                              id="username"
                              name="username"
                              value={userFormData.username}
                              onChange={handleUserFormChange}
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                              required
                            />
                          </div>
                          
                          <div className="mb-4">
                            <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email</label>
                            <input
                              type="email"
                              id="email"
                              name="email"
                              value={userFormData.email}
                              onChange={handleUserFormChange}
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                              required
                            />
                          </div>
                        </div>
                        
                        {!isEditMode && (
                          <div className="mb-4">
                            <label htmlFor="password" className="block text-sm font-medium text-gray-700">Password</label>
                            <input
                              type="password"
                              id="password"
                              name="password"
                              value={userFormData.password}
                              onChange={handleUserFormChange}
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                              required={!isEditMode}
                              minLength={8}
                            />
                          </div>
                        )}
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div className="mb-4">
                            <label htmlFor="first_name" className="block text-sm font-medium text-gray-700">First Name</label>
                            <input
                              type="text"
                              id="first_name"
                              name="first_name"
                              value={userFormData.first_name}
                              onChange={handleUserFormChange}
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            />
                          </div>
                          
                          <div className="mb-4">
                            <label htmlFor="last_name" className="block text-sm font-medium text-gray-700">Last Name</label>
                            <input
                              type="text"
                              id="last_name"
                              name="last_name"
                              value={userFormData.last_name}
                              onChange={handleUserFormChange}
                              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            />
                          </div>
                        </div>
                        
                        <div className="mb-4">
                          <label htmlFor="role" className="block text-sm font-medium text-gray-700">Role</label>
                          <select
                            id="role"
                            name="role"
                            value={userFormData.role}
                            onChange={handleUserFormChange}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                            required
                          >
                            <option value="admin">Admin</option>
                            <option value="staff">Staff</option>
                            <option value="evaluator">Evaluator</option>
                            {isEditMode && <option value="vendor">Vendor</option>}
                          </select>
                          <p className="mt-1 text-xs text-gray-500">Note: Vendor users should be created through the vendor registration process.</p>
                        </div>
                        
                        <div className="mb-4 flex items-center">
                          <input
                            type="checkbox"
                            id="is_active"
                            name="is_active"
                            checked={userFormData.is_active}
                            onChange={handleUserFormChange}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900">
                            Active Account
                          </label>
                        </div>
                        
                        <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                          <button
                            type="submit"
                            className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:col-start-2 sm:text-sm"
                          >
                            {isEditMode ? 'Update User' : 'Create User'}
                          </button>
                          <button
                            type="button"
                            onClick={closeUserModal}
                            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                          >
                            Cancel
                          </button>
                        </div>
                      </form>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default AdminDashboard;