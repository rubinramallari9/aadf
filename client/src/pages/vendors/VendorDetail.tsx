// src/pages/vendors/VendorDetail.tsx
import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { vendorApi, offerApi } from '../../api/api';

// Define interfaces that match the API response structure
interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
}

interface VendorCompany {
  id: number;
  name: string;
  registration_number?: string;
  email?: string;
  phone?: string;
  address?: string;
  created_at: string;
  updated_at: string;
  users?: User[];
}

interface Offer {
  id: number;
  tender_id: number;
  tender_title: string;
  tender_reference: string;
  status: string;
  price: number;
  submitted_at?: string;
  created_at: string;
}

interface VendorStatistics {
  total_offers: number;
  total_awarded: number;
  total_rejected: number;
  total_active: number;
  recent_activity: string[];
}

const VendorDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [vendor, setVendor] = useState<VendorCompany | null>(null);
  const [vendorUsers, setVendorUsers] = useState<User[]>([]);
  const [statistics, setStatistics] = useState<VendorStatistics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // These state variables are declared but not used, consider removing them
  // Keeping them commented to show they were originally there
  // const [offers, setOffers] = useState<Offer[]>([]);
  
  useEffect(() => {
    if (!id) return;
    fetchVendorDetails(parseInt(id));
  }, [id]);

  const fetchVendorDetails = async (vendorId: number) => {
    try {
      setLoading(true);
      setError(null);
      
      // Get vendor details
      const vendorData = await vendorApi.getById(vendorId);
      
      // Create a local copy that matches our VendorCompany interface
      const vendorWithCorrectType: VendorCompany = {
        id: vendorData.id,
        name: vendorData.name,
        registration_number: vendorData.registration_number,
        email: vendorData.email,
        phone: vendorData.phone,
        address: vendorData.address,
        created_at: vendorData.created_at,
        updated_at: vendorData.updated_at,
      };
      
      setVendor(vendorWithCorrectType);
      
      // Set vendor users if available
      if (vendorData.users && Array.isArray(vendorData.users)) {
        const typedUsers: User[] = vendorData.users.map((u: any) => ({
          id: u.id,
          username: u.username,
          email: u.email,
          first_name: u.first_name,
          last_name: u.last_name,
          role: u.role,
        }));
        setVendorUsers(typedUsers);
      }
      
      // Get vendor statistics
      const statsData = await vendorApi.getStatistics(vendorId);
      setStatistics(statsData);
      
    } catch (err: any) {
      console.error('Error fetching vendor details:', err);
      setError(err.message || 'Failed to load vendor details');
    } finally {
      setLoading(false);
    }
  };

  // Only allow staff and admin to access this page
  if (user?.role !== 'staff' && user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded-lg shadow-sm" role="alert">
          <div className="flex items-center">
            <span className="material-icons mr-2">warning</span>
            <strong className="font-bold">Access Denied</strong>
          </div>
          <span className="block sm:inline mt-1"> You do not have permission to view vendor details.</span>
        </div>
      </Layout>
    );
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
      </Layout>
    );
  }

  if (!vendor) {
    return (
      <Layout>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Vendor Not Found</h1>
          <p className="mt-2 text-gray-600">The vendor you are looking for does not exist or has been removed.</p>
          <Link to="/vendors" className="mt-4 inline-block text-blue-600 hover:text-blue-800">
            Back to Vendors
          </Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{vendor.name}</h1>
          <div className="flex space-x-3">
            <Link
              to="/vendors"
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <span className="material-icons mr-2 text-sm">arrow_back</span>
              Back to Vendors
            </Link>
            
            {user?.role === 'admin' && (
              <Link
                to={`/vendors/${vendor.id}/edit`}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                <span className="material-icons mr-2 text-sm">edit</span>
                Edit Vendor
              </Link>
            )}
          </div>
        </div>

        <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Vendor Details</h3>
            <p className="mt-1 max-w-2xl text-sm text-gray-500">Vendor company information and registration details.</p>
          </div>
          <div className="border-t border-gray-200">
            <dl>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Company name</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{vendor.name}</dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Registration number</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{vendor.registration_number || 'Not provided'}</dd>
              </div>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Email address</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{vendor.email || 'Not provided'}</dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Phone number</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{vendor.phone || 'Not provided'}</dd>
              </div>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Address</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{vendor.address || 'Not provided'}</dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Registered</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {new Date(vendor.created_at).toLocaleDateString()}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Associated Users */}
        <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
          <div className="px-4 py-5 sm:px-6 flex justify-between items-center">
            <div>
              <h3 className="text-lg leading-6 font-medium text-gray-900">Associated Users</h3>
              <p className="mt-1 max-w-2xl text-sm text-gray-500">Users who have access to this vendor account.</p>
            </div>
            {user?.role === 'admin' && (
              <button
                onClick={() => navigate(`/vendors/${vendor.id}/users`)}
                className="inline-flex items-center px-3 py-1 border border-transparent text-sm leading-4 font-medium rounded-md text-blue-600 bg-blue-100 hover:bg-blue-200"
              >
                <span className="material-icons mr-1 text-sm">person_add</span>
                Manage Users
              </button>
            )}
          </div>
          <div className="border-t border-gray-200">
            {vendorUsers.length > 0 ? (
              <ul className="divide-y divide-gray-200">
                {vendorUsers.map((vendorUser) => (
                  <li key={vendorUser.id} className="px-4 py-4 sm:px-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          <span className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                            <span className="material-icons text-blue-600">person</span>
                          </span>
                        </div>
                        <div className="ml-3">
                          <p className="text-sm font-medium text-gray-900">{vendorUser.username}</p>
                          <p className="text-sm text-gray-500">{vendorUser.email}</p>
                        </div>
                      </div>
                      <div>
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          {vendorUser.role}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="px-4 py-5 sm:px-6 text-center">
                <p className="text-sm text-gray-500">No users associated with this vendor.</p>
              </div>
            )}
          </div>
        </div>

        {/* Vendor Statistics */}
        {statistics && (
          <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">Vendor Statistics</h3>
              <p className="mt-1 max-w-2xl text-sm text-gray-500">Performance metrics and activity statistics.</p>
            </div>
            <div className="border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-6">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm font-medium text-gray-500">Total Offers</p>
                  <p className="mt-1 text-3xl font-semibold text-gray-900">{statistics.total_offers}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm font-medium text-gray-500">Awarded Offers</p>
                  <p className="mt-1 text-3xl font-semibold text-green-600">{statistics.total_awarded}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm font-medium text-gray-500">Rejected Offers</p>
                  <p className="mt-1 text-3xl font-semibold text-red-600">{statistics.total_rejected}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm font-medium text-gray-500">Active Offers</p>
                  <p className="mt-1 text-3xl font-semibold text-blue-600">{statistics.total_active}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Recent Activity */}
        {statistics && statistics.recent_activity && statistics.recent_activity.length > 0 && (
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">Recent Activity</h3>
              <p className="mt-1 max-w-2xl text-sm text-gray-500">Latest activity and interactions with this vendor.</p>
            </div>
            <div className="border-t border-gray-200">
              <ul className="divide-y divide-gray-200">
                {statistics.recent_activity.map((activity, index) => (
                  <li key={index} className="px-4 py-4 sm:px-6">
                    <p className="text-sm text-gray-900">{activity}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default VendorDetail;