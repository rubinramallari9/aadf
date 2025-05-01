// client/src/pages/Dashboard.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { useAuth } from '../contexts/AuthContext';
import { dashboardApi } from '../api/api';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
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

    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-full">
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
        <div className="mt-4">
          <button 
            onClick={() => window.location.reload()} 
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </Layout>
    );
  }

  if (!dashboardData) {
    return (
      <Layout>
        <div className="text-center">No data available</div>
      </Layout>
    );
  }

  // Render admin/staff dashboard
  if (user?.role === 'admin' || user?.role === 'staff') {
    return (
      <Layout>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {/* Tender Stats Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <span className="material-icons">business_center</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Total Tenders</p>
                <p className="text-2xl font-bold text-gray-800">{dashboardData.tenders?.total || 0}</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <div className="text-sm">
                <p className="text-gray-500">Published</p>
                <p className="font-medium">{dashboardData.tenders?.published || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Draft</p>
                <p className="font-medium">{dashboardData.tenders?.draft || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Closed</p>
                <p className="font-medium">{dashboardData.tenders?.closed || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Awarded</p>
                <p className="font-medium">{dashboardData.tenders?.awarded || 0}</p>
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
                <p className="text-2xl font-bold text-gray-800">{dashboardData.offers?.total || 0}</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <div className="text-sm">
                <p className="text-gray-500">Submitted</p>
                <p className="font-medium">{dashboardData.offers?.submitted || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Draft</p>
                <p className="font-medium">{dashboardData.offers?.draft || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Evaluated</p>
                <p className="font-medium">{dashboardData.offers?.evaluated || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Awarded</p>
                <p className="font-medium">{dashboardData.offers?.awarded || 0}</p>
              </div>
            </div>
          </div>

          {/* Users Stats Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-purple-100 text-purple-600">
                <span className="material-icons">people</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Total Users</p>
                <p className="text-2xl font-bold text-gray-800">{dashboardData.users?.total || 0}</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <div className="text-sm">
                <p className="text-gray-500">Staff</p>
                <p className="font-medium">{dashboardData.users?.staff || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Admin</p>
                <p className="font-medium">{dashboardData.users?.admin || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Vendors</p>
                <p className="font-medium">{dashboardData.users?.vendor || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Evaluators</p>
                <p className="font-medium">{dashboardData.users?.evaluator || 0}</p>
              </div>
            </div>
          </div>

          {/* Activity Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
                <span className="material-icons">notifications</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">User Activity</p>
                <p className="text-2xl font-bold text-gray-800">
                  {dashboardData.user?.unread_notifications || 0}
                  <span className="text-sm text-gray-500 font-normal"> unread</span>
                </p>
              </div>
            </div>
            <div className="mt-4">
              <Link 
                to="/notifications" 
                className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center"
              >
                View all notifications
                <span className="material-icons text-base ml-1">arrow_forward</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Recent Tenders */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">Recent Tenders</h2>
            <Link to="/tenders" className="text-blue-600 hover:text-blue-800 flex items-center text-sm font-medium">
              View all
              <span className="material-icons text-base ml-1">arrow_forward</span>
            </Link>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reference
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created At
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dashboardData.recent_tenders?.map((tender: any) => (
                  <tr key={tender.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {tender.reference_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {tender.title}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        tender.status === 'published' 
                          ? 'bg-green-100 text-green-800' 
                          : tender.status === 'draft' 
                          ? 'bg-gray-100 text-gray-800'
                          : tender.status === 'closed'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {tender.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(tender.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <Link to={`/tenders/${tender.id}`} className="text-blue-600 hover:text-blue-900">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
                {(!dashboardData.recent_tenders || dashboardData.recent_tenders.length === 0) && (
                  <tr>
                    <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                      No recent tenders found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Offers */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">Recent Offers</h2>
            <Link to="/offers" className="text-blue-600 hover:text-blue-800 flex items-center text-sm font-medium">
              View all
              <span className="material-icons text-base ml-1">arrow_forward</span>
            </Link>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tender
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Vendor
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created At
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dashboardData.recent_offers?.map((offer: any) => (
                  <tr key={offer.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {offer.tender__reference_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {offer.vendor__name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        offer.status === 'submitted' 
                          ? 'bg-green-100 text-green-800' 
                          : offer.status === 'draft' 
                          ? 'bg-gray-100 text-gray-800'
                          : offer.status === 'evaluated'
                          ? 'bg-yellow-100 text-yellow-800'
                          : offer.status === 'awarded'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {offer.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(offer.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <Link to={`/offers/${offer.id}`} className="text-blue-600 hover:text-blue-900">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
                {(!dashboardData.recent_offers || dashboardData.recent_offers.length === 0) && (
                  <tr>
                    <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                      No recent offers found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Layout>
    );
  }

  // Render vendor dashboard
  if (user?.role === 'vendor') {
    return (
      <Layout>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {/* My Offers Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <span className="material-icons">local_offer</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">My Offers</p>
                <p className="text-2xl font-bold text-gray-800">{dashboardData.offers?.total || 0}</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <div className="text-sm">
                <p className="text-gray-500">Submitted</p>
                <p className="font-medium">{dashboardData.offers?.submitted || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Draft</p>
                <p className="font-medium">{dashboardData.offers?.draft || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Awarded</p>
                <p className="font-medium">{dashboardData.offers?.awarded || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Rejected</p>
                <p className="font-medium">{dashboardData.offers?.rejected || 0}</p>
              </div>
            </div>
          </div>

          {/* Tenders Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-green-100 text-green-600">
                <span className="material-icons">business_center</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Tenders</p>
                <p className="text-2xl font-bold text-gray-800">{dashboardData.tenders?.published || 0}</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <div className="text-sm">
                <p className="text-gray-500">Published</p>
                <p className="font-medium">{dashboardData.tenders?.published || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Participated</p>
                <p className="font-medium">{dashboardData.tenders?.participated || 0}</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Won</p>
                <p className="font-medium">{dashboardData.tenders?.won || 0}</p>
              </div>
            </div>
          </div>

          {/* Notifications Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
                <span className="material-icons">notifications</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Notifications</p>
                <p className="text-2xl font-bold text-gray-800">
                  {dashboardData.unread_notifications || 0}
                  <span className="text-sm text-gray-500 font-normal"> unread</span>
                </p>
              </div>
            </div>
            <div className="mt-4">
              <Link 
                to="/notifications" 
                className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center"
              >
                View all notifications
                <span className="material-icons text-base ml-1">arrow_forward</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Company Info */}
        {dashboardData.companies && dashboardData.companies.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">My Company</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {dashboardData.companies.map((company: any) => (
                <div key={company.id} className="border rounded-lg p-4">
                  <h3 className="text-xl font-medium">{company.name}</h3>
                  <p className="text-gray-500 mt-1">{company.registration_number}</p>
                  <div className="mt-3">
                    {company.email && (
                      <p className="text-sm">
                        <span className="font-medium">Email:</span> {company.email}
                      </p>
                    )}
                    {company.phone && (
                      <p className="text-sm">
                        <span className="font-medium">Phone:</span> {company.phone}
                      </p>
                    )}
                    {company.address && (
                      <p className="text-sm">
                        <span className="font-medium">Address:</span> {company.address}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Tenders */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">Open Tenders</h2>
            <Link to="/tenders" className="text-blue-600 hover:text-blue-800 flex items-center text-sm font-medium">
              View all
              <span className="material-icons text-base ml-1">arrow_forward</span>
            </Link>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reference
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Deadline
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Participated
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dashboardData.recent_tenders?.map((tender: any) => (
                  <tr key={tender.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {tender.reference_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {tender.title}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(tender.submission_deadline).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        tender.has_participated 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {tender.has_participated ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <Link to={`/tenders/${tender.id}`} className="text-blue-600 hover:text-blue-900 mr-4">
                        View
                      </Link>
                      {!tender.has_participated && (
                        <Link to={`/offers/create?tender=${tender.id}`} className="text-green-600 hover:text-green-900">
                          Submit Offer
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
                {(!dashboardData.recent_tenders || dashboardData.recent_tenders.length === 0) && (
                  <tr>
                    <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                      No open tenders found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* My Recent Offers */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">My Recent Offers</h2>
            <Link to="/offers" className="text-blue-600 hover:text-blue-800 flex items-center text-sm font-medium">
              View all
              <span className="material-icons text-base ml-1">arrow_forward</span>
            </Link>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tender
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Submitted At
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dashboardData.recent_offers?.map((offer: any) => (
                  <tr key={offer.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {offer.tender__reference_number} - {offer.tender__title}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        offer.status === 'submitted' 
                          ? 'bg-green-100 text-green-800' 
                          : offer.status === 'draft' 
                          ? 'bg-gray-100 text-gray-800'
                          : offer.status === 'evaluated'
                          ? 'bg-yellow-100 text-yellow-800'
                          : offer.status === 'awarded'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {offer.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {offer.submitted_at 
                        ? new Date(offer.submitted_at).toLocaleDateString() 
                        : 'Not submitted'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <Link to={`/offers/${offer.id}`} className="text-blue-600 hover:text-blue-900 mr-4">
                        View
                      </Link>
                      {offer.status === 'draft' && (
                        <Link to={`/offers/edit/${offer.id}`} className="text-green-600 hover:text-green-900">
                          Edit
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
                {(!dashboardData.recent_offers || dashboardData.recent_offers.length === 0) && (
                  <tr>
                    <td colSpan={4} className="px-6 py-4 text-center text-sm text-gray-500">
                      No recent offers found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Layout>
    );
  }

  // Render evaluator dashboard
  if (user?.role === 'evaluator') {
    return (
      <Layout>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {/* Tenders to Evaluate Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <span className="material-icons">grade</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Tenders to Evaluate</p>
                <p className="text-2xl font-bold text-gray-800">{dashboardData.tenders?.total_to_evaluate || 0}</p>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-sm">
                <p className="text-gray-500">Evaluated</p>
                <p className="font-medium">{dashboardData.tenders?.evaluated || 0}</p>
              </div>
            </div>
          </div>

          {/* Evaluations Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-green-100 text-green-600">
                <span className="material-icons">assignment</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">My Evaluations</p>
                <p className="text-2xl font-bold text-gray-800">{dashboardData.evaluations?.completed || 0}</p>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-sm">
                <p className="text-gray-500">Pending</p>
                <p className="font-medium">{dashboardData.pending_evaluations || 0}</p>
              </div>
            </div>
          </div>

          {/* Notifications Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
                <span className="material-icons">notifications</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Notifications</p>
                <p className="text-2xl font-bold text-gray-800">
                  {dashboardData.unread_notifications || 0}
                  <span className="text-sm text-gray-500 font-normal"> unread</span>
                </p>
              </div>
            </div>
            <div className="mt-4">
              <Link 
                to="/notifications" 
                className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center"
              >
                View all notifications
                <span className="material-icons text-base ml-1">arrow_forward</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Recent Tenders */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">Recent Tenders for Evaluation</h2>
            <Link to="/evaluations" className="text-blue-600 hover:text-blue-800 flex items-center text-sm font-medium">
              View all
              <span className="material-icons text-base ml-1">arrow_forward</span>
            </Link>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reference
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Offers
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dashboardData.recent_tenders?.map((tender: any) => (
                  <tr key={tender.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {tender.reference_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {tender.title}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        tender.status === 'closed' 
                          ? 'bg-yellow-100 text-yellow-800' 
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {tender.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {tender.offer_count || 0} offers
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <Link to={`/tenders/${tender.id}/evaluate`} className="text-blue-600 hover:text-blue-900">
                        Evaluate
                      </Link>
                    </td>
                  </tr>
                ))}
                {(!dashboardData.recent_tenders || dashboardData.recent_tenders.length === 0) && (
                  <tr>
                    <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                      No tenders available for evaluation
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* My Recent Evaluations */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">My Recent Evaluations</h2>
            <Link to="/evaluations" className="text-blue-600 hover:text-blue-800 flex items-center text-sm font-medium">
              View all
              <span className="material-icons text-base ml-1">arrow_forward</span>
            </Link>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tender
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Criteria
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dashboardData.evaluations?.recent?.map((evaluation: any) => (
                  <tr key={evaluation.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {evaluation.offer__tender__reference_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {evaluation.criteria__name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {evaluation.score}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(evaluation.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <Link to={`/evaluations/${evaluation.id}`} className="text-blue-600 hover:text-blue-900">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
                {(!dashboardData.evaluations?.recent || dashboardData.evaluations.recent.length === 0) && (
                  <tr>
                    <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                      No recent evaluations found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Layout>
    );
  }

  // Default fallback
  return (
    <Layout>
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900">Welcome to AADF Procurement Platform</h1>
        <p className="mt-4 text-gray-600">Please select an option from the navigation menu.</p>
      </div>
    </Layout>
  );
}
export default Dashboard