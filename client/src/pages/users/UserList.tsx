// client/src/pages/users/UserList.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { usersApi } from '../../api/usersApi';

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

const UserList: React.FC = () => {
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const usersPerPage = 10;

  useEffect(() => {
    fetchUsers();
  }, [currentPage, roleFilter, statusFilter]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      // Prepare query parameters
      const params: Record<string, string> = {};
      if (roleFilter) params.role = roleFilter;
      if (statusFilter) params.is_active = statusFilter;
      params.page = currentPage.toString();
      params.limit = usersPerPage.toString();

      const response = await usersApi.getAll(params);
      
      // Handle different response formats
      let usersData = [];
      let totalItems = 0;
      
      if (Array.isArray(response)) {
        usersData = response;
        totalItems = response.length;
      } else if (response.results && Array.isArray(response.results)) {
        usersData = response.results;
        totalItems = response.count || response.results.length;
      } else if (typeof response === 'object') {
        usersData = Object.values(response).filter(item => 
          item && typeof item === 'object' && 'id' in item
        ) as User[];
        totalItems = usersData.length;
      }
      
      setUsers(usersData);
      setTotalPages(Math.ceil(totalItems / usersPerPage));
    } catch (err: any) {
      console.error('Error fetching users:', err);
      setError(err.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    if (searchQuery.trim()) {
      searchUsers(searchQuery);
    } else {
      fetchUsers();
    }
  };

  const searchUsers = async (query: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await usersApi.search(query);
      
      // Handle different response formats
      let usersData = [];
      
      if (Array.isArray(response)) {
        usersData = response;
      } else if (response.results && Array.isArray(response.results)) {
        usersData = response.results;
      } else if (typeof response === 'object') {
        usersData = Object.values(response).filter(item => 
          item && typeof item === 'object' && 'id' in item
        ) as User[];
      }
      
      setUsers(usersData);
      setTotalPages(Math.ceil(usersData.length / usersPerPage));
      setCurrentPage(1);
    } catch (err: any) {
      console.error('Error searching users:', err);
      setError(err.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleActivateDeactivate = async (userId: number, activate: boolean) => {
    try {
      if (activate) {
        await usersApi.activate(userId);
      } else {
        await usersApi.deactivate(userId);
      }
      
      // Refresh user list
      fetchUsers();
    } catch (err: any) {
      console.error(`Error ${activate ? 'activating' : 'deactivating'} user:`, err);
      setError(err.message || `Failed to ${activate ? 'activate' : 'deactivate'} user`);
    }
  };

  const handleResetPassword = async (userId: number) => {
    // In a real implementation, this would likely open a modal for inputting a new password
    // For now, we'll just use a simple prompt
    const newPassword = prompt('Enter new password for user:');
    
    if (newPassword) {
      try {
        await usersApi.resetPassword(userId, newPassword);
        alert('Password reset successfully');
      } catch (err: any) {
        console.error('Error resetting password:', err);
        setError(err.message || 'Failed to reset password');
      }
    }
  };

  // Filter users based on search query (client-side filtering)
  const filteredUsers = users.filter(user => {
    const searchLower = searchQuery.toLowerCase();
    return (
      user.username.toLowerCase().includes(searchLower) ||
      user.email.toLowerCase().includes(searchLower) ||
      (user.first_name && user.first_name.toLowerCase().includes(searchLower)) ||
      (user.last_name && user.last_name.toLowerCase().includes(searchLower))
    );
  });

  // Only allow admin to access this page
  if (user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded-lg shadow-sm" role="alert">
          <div className="flex items-center">
            <span className="material-icons mr-2">warning</span>
            <strong className="font-bold">Access Denied</strong>
          </div>
          <span className="block sm:inline mt-1"> You do not have permission to access user management.</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <p className="text-gray-600">Manage user accounts and permissions</p>
        </div>
        <Link
          to="/users/create"
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
        >
          <span className="material-icons mr-2 text-sm">person_add</span>
          Create User
        </Link>
      </div>

      {error && (
        <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white shadow rounded-lg mb-6">
        <div className="p-4 sm:p-6 border-b border-gray-200">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Search */}
            <div className="sm:col-span-2">
              <label htmlFor="search" className="block text-sm font-medium text-gray-700">Search</label>
              <div className="mt-1 flex rounded-md shadow-sm">
                <input
                  type="text"
                  name="search"
                  id="search"
                  className="focus:ring-blue-500 focus:border-blue-500 flex-1 block w-full rounded-none rounded-l-md sm:text-sm border-gray-300"
                  placeholder="Search by username, email, or name"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                />
                <button
                  type="button"
                  onClick={handleSearch}
                  className="inline-flex items-center px-3 py-2 border border-l-0 border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-r-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <span className="material-icons text-sm">search</span>
                </button>
              </div>
            </div>

            {/* Role Filter */}
            <div>
              <label htmlFor="role-filter" className="block text-sm font-medium text-gray-700">Role</label>
              <select
                id="role-filter"
                name="role-filter"
                className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
              >
                <option value="">All Roles</option>
                <option value="admin">Admin</option>
                <option value="staff">Staff</option>
                <option value="vendor">Vendor</option>
                <option value="evaluator">Evaluator</option>
              </select>
            </div>

            {/* Status Filter */}
            <div>
              <label htmlFor="status-filter" className="block text-sm font-medium text-gray-700">Status</label>
              <select
                id="status-filter"
                name="status-filter"
                className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All Status</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-6 flex justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="p-6 text-center">
            <p className="text-gray-500">No users found matching your criteria</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
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
                {filteredUsers.map((userData) => (
                  <tr key={userData.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 bg-gray-200 rounded-full flex items-center justify-center">
                          <span className="material-icons text-gray-500">person</span>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{userData.username}</div>
                          <div className="text-sm text-gray-500">{userData.email}</div>
                          {(userData.first_name || userData.last_name) && (
                            <div className="text-sm text-gray-500">
                              {userData.first_name} {userData.last_name}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        userData.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                        userData.role === 'staff' ? 'bg-blue-100 text-blue-800' :
                        userData.role === 'evaluator' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {userData.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        userData.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {userData.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(userData.date_joined).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex space-x-3">
                        <Link to={`/users/${userData.id}`} className="text-blue-600 hover:text-blue-900">
                          View
                        </Link>
                        <Link to={`/users/${userData.id}/edit`} className="text-blue-600 hover:text-blue-900">
                          Edit
                        </Link>
                        <button 
                          onClick={() => handleResetPassword(userData.id)} 
                          className="text-yellow-600 hover:text-yellow-900"
                        >
                          Reset Password
                        </button>
                        {userData.id !== user?.id && (
                          userData.is_active ? (
                            <button 
                              onClick={() => handleActivateDeactivate(userData.id, false)} 
                              className="text-red-600 hover:text-red-900"
                            >
                              Deactivate
                            </button>
                          ) : (
                            <button 
                              onClick={() => handleActivateDeactivate(userData.id, true)} 
                              className="text-green-600 hover:text-green-900"
                            >
                              Activate
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing page <span className="font-medium">{currentPage}</span> of{' '}
                  <span className="font-medium">{totalPages}</span>
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                  <button
                    onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                    disabled={currentPage === 1}
                    className={`relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium ${
                      currentPage === 1 ? 'text-gray-300' : 'text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    <span className="sr-only">Previous</span>
                    <span className="material-icons text-sm">chevron_left</span>
                  </button>
                  
                  {/* Page numbers */}
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    // Show pages around current page
                    const pagesToShow = 5;
                    const startPage = Math.max(1, currentPage - Math.floor(pagesToShow / 2));
                    const endPage = Math.min(totalPages, startPage + pagesToShow - 1);
                    
                    const page = startPage + i;
                    return page <= endPage ? (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                          currentPage === page
                            ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                            : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                        }`}
                      >
                        {page}
                      </button>
                    ) : null;
                  })}
                  
                  <button
                    onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                    disabled={currentPage === totalPages}
                    className={`relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium ${
                      currentPage === totalPages ? 'text-gray-300' : 'text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    <span className="sr-only">Next</span>
                    <span className="material-icons text-sm">chevron_right</span>
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default UserList;