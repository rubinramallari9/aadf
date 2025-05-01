// client/src/pages/vendors/VendorDetail.tsx
import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { useVendor } from '../../contexts/VendorContext'; // Import useVendor

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
}

interface VendorCompany {
  id: number;
  name: string;
  registration_number: string;
  email: string;
  phone: string;
  address: string;
  created_at: string;
  updated_at: string;
  users: User[];
}

interface Offer {
  id: number;
  tender_title: string;
  status: string;
  submitted_at: string;
  price: number;
  total_score: number;
}

interface Stats {
  total_offers: number;
  submitted_offers: number;
  awarded_offers: number;
  rejected_offers: number;
  average_score: number;
}

const VendorDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { getVendorById, fetchVendorStatistics, assignUser, removeUser, users, fetchUsers } = useVendor(); // Use the vendor context
  const navigate = useNavigate();
  const [vendor, setVendor] = useState<VendorCompany | null>(null);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddUserModal, setShowAddUserModal] = useState<boolean>(false);
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);

  useEffect(() => {
    fetchVendorDetails();
  }, [id]);

  const fetchVendorDetails = async () => {
    try {
      setLoading(true);
      
      if (!id) {
        setError("No vendor ID provided");
        setLoading(false);
        return;
      }
      
      // Fetch vendor details
      const vendorResponse = await getVendorById(Number(id));
      setVendor(vendorResponse);

      // Fetch vendor statistics
      const statsResponse = await fetchVendorStatistics(Number(id));
      setStats(statsResponse);

      // If admin, fetch available users that can be added
      if (user?.role === 'admin') {
        await fetchUsers('vendor');
        
        // Filter users that are not already part of this vendor
        const vendorUserIds = vendorResponse.users?.map(u => u.id) || [];
        const filteredUsers = users.filter(u => !vendorUserIds.includes(u.id));
        setAvailableUsers(filteredUsers);
      }
    } catch (err: any) {
      console.error('Error fetching vendor details:', err);
      setError(err.message || 'Failed to load vendor details');
    } finally {
      setLoading(false);
    }
  };

  const handleAddUser = async () => {
    if (!selectedUserId) {
      return;
    }

    try {
      if (!id) {
        setError("No vendor ID provided");
        return;
      }
      
      await assignUser(Number(id), Number(selectedUserId));
      setShowAddUserModal(false);
      setSelectedUserId('');
      // Refresh vendor details
      fetchVendorDetails();
    } catch (err: any) {
      console.error('Error adding user to vendor:', err);
      alert(err.message || 'Failed to add user to vendor');
    }
  };

  const handleRemoveUser = async (userId: number) => {
    if (!confirm('Are you sure you want to remove this user from the vendor?')) {
      return;
    }

    try {
      if (!id) {
        setError("No vendor ID provided");
        return;
      }
      
      await removeUser(Number(id), userId);
      // Refresh vendor details
      fetchVendorDetails();
    } catch (err: any) {
      console.error('Error removing user from vendor:', err);
      alert(err.message || 'Failed to remove user from vendor');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </Layout>
    );
  }

  if (error || !vendor) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error || 'Vendor not found'}</span>
        </div>
        <div className="mt-4">
          <Link to="/vendors" className="text-blue-600 hover:text-blue-800">
            &larr; Back to vendors
          </Link>
        </div>
      </Layout>
    );
  }

  // Only allow staff and admin to view vendor details
  if (user?.role !== 'staff' && user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Access Denied</strong>
          <span className="block sm:inline"> You do not have permission to view vendor details.</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{vendor.name}</h1>
            <p className="text-gray-600">Registration: {vendor.registration_number || 'N/A'}</p>
          </div>
          <div className="flex space-x-4">
            {user?.role === 'admin' && (
              <>
                <button
                  onClick={() => setShowAddUserModal(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Add User
                </button>
                <Link
                  to={`/vendors/${vendor.id}/edit`}
                  className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
                >
                  Edit Vendor
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Vendor Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Details Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Vendor Details</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500">Company Name</label>
                  <p className="mt-1">{vendor.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Registration Number</label>
                  <p className="mt-1">{vendor.registration_number || 'N/A'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Email</label>
                  <p className="mt-1">{vendor.email || 'N/A'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Phone</label>
                  <p className="mt-1">{vendor.phone || 'N/A'}</p>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-500">Address</label>
                  <p className="mt-1">{vendor.address || 'N/A'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Created At</label>
                  <p className="mt-1">{new Date(vendor.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Updated At</label>
                  <p className="mt-1">{new Date(vendor.updated_at).toLocaleString()}</p>
                </div>
              </div>
            </div>

            {/* Users Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Associated Users</h2>
              {vendor.users && vendor.users.length > 0 ? (
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
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {vendor.users.map((vendorUser) => (
                      <tr key={vendorUser.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {vendorUser.username}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {vendorUser.first_name} {vendorUser.last_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {vendorUser.email}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          {user?.role === 'admin' && (
                            <button
                              onClick={() => handleRemoveUser(vendorUser.id)}
                              className="text-red-600 hover:text-red-900"
                            >
                              Remove
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-gray-500 text-center">No users associated with this vendor</p>
              )}
            </div>

            {/* Rest of the component remains the same */}
          </div>

          {/* Right Column - Statistics */}
          <div className="space-y-6">
            {/* Statistics Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Vendor Statistics</h2>
              {stats ? (
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Total Offers</span>
                      <span className="font-semibold">{stats.total_offers}</span>
                    </div>
                    <div className="mt-1 h-2 w-full bg-gray-200 rounded">
                      <div 
                        className="h-full bg-blue-600 rounded" 
                        style={{ width: `${stats.total_offers > 0 ? '100' : '0'}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Submitted Offers</span>
                      <span className="font-semibold">{stats.submitted_offers}</span>
                    </div>
                    <div className="mt-1 h-2 w-full bg-gray-200 rounded">
                      <div 
                        className="h-full bg-green-600 rounded" 
                        style={{ width: `${stats.total_offers > 0 ? (stats.submitted_offers / stats.total_offers) * 100 : 0}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Awarded Offers</span>
                      <span className="font-semibold">{stats.awarded_offers}</span>
                    </div>
                    <div className="mt-1 h-2 w-full bg-gray-200 rounded">
                      <div 
                        className="h-full bg-blue-600 rounded" 
                        style={{ width: `${stats.total_offers > 0 ? (stats.awarded_offers / stats.total_offers) * 100 : 0}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Rejected Offers</span>
                      <span className="font-semibold">{stats.rejected_offers}</span>
                    </div>
                    <div className="mt-1 h-2 w-full bg-gray-200 rounded">
                      <div 
                        className="h-full bg-red-600 rounded" 
                        style={{ width: `${stats.total_offers > 0 ? (stats.rejected_offers / stats.total_offers) * 100 : 0}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t border-gray-200">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Average Score</span>
                      <span className="font-semibold">{stats.average_score ? `${stats.average_score.toFixed(2)}%` : 'N/A'}</span>
                    </div>
                    <div className="mt-1 h-2 w-full bg-gray-200 rounded">
                      <div 
                        className="h-full bg-yellow-600 rounded" 
                        style={{ width: `${stats.average_score ? stats.average_score : 0}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500 text-center">No statistics available</p>
              )}
            </div>

            {/* Actions Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Actions</h2>
              <div className="space-y-2">
                <Link
                  to={`/vendors/${vendor.id}/offers`}
                  className="block w-full text-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  View All Offers
                </Link>
                {user?.role === 'admin' && (
                  <>
                    <button
                      onClick={() => navigate(`/vendors/${vendor.id}/edit`)}
                      className="block w-full text-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-yellow-600 hover:bg-yellow-700"
                    >
                      Edit Vendor
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to deactivate this vendor?')) {
                          // Implement vendor deactivation
                          alert('Vendor deactivation feature will be implemented soon');
                        }
                      }}
                      className="block w-full text-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700"
                    >
                      Deactivate Vendor
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>

            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                    <h3 className="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                      Add User to Vendor
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500 mb-4">
                        Select a user to add to this vendor. Only users with the vendor role are shown.
                      </p>
                      <select
                        value={selectedUserId}
                        onChange={(e) => setSelectedUserId(e.target.value)}
                        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                      >
                        <option value="">Select a user</option>
                        {availableUsers.map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.username} ({user.email})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={handleAddUser}
                >
                  Add User
                </button>
                <button
                  type="button"
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={() => setShowAddUserModal(false)}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default VendorDetail;