// client/src/pages/offers/OfferList.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { offerApi } from '../../api/api';

interface Offer {
  id: number;
  tender_title: string;
  tender: {
    id: number;
    reference_number: string;
    title: string;
  };
  vendor_name: string;
  status: string;
  submitted_at: string;
  price: number;
  technical_score: number;
  financial_score: number;
  total_score: number;
  created_at: string;
  [key: string]: any; // Add index signature to allow string indexing
}

const OfferList: React.FC = () => {
  const { user } = useAuth();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('-created_at');

  useEffect(() => {
    fetchOffers();
  }, [statusFilter, sortBy]);

  const fetchOffers = async () => {
    try {
      setLoading(true);
      const params: any = {};
      
      if (statusFilter) params.status = statusFilter;
      
      const response = await offerApi.getAll(params);
      
      // Handle different response formats
      let offersData: Offer[] = [];
      
      if (response) {
        // Check if response is an array
        if (Array.isArray(response)) {
          offersData = response;
        } 
        // Check if response has a results property that is an array
        else if (response.results && Array.isArray(response.results)) {
          offersData = response.results;
        } 
        // If it's some other object structure, try to convert to array
        else if (typeof response === 'object') {
          offersData = Object.values(response);
        }
      }
      
      // Sort the offers
      const sortedOffers = [...offersData];
      
      if (sortBy.startsWith('-')) {
        const field = sortBy.slice(1);
        sortedOffers.sort((a, b) => {
          // Handle the total_score case
          if (field === 'total_score') {
            const aValue = a.total_score || 0;
            const bValue = b.total_score || 0;
            return bValue - aValue;
          }
          
          // Handle date fields
          if (field === 'created_at' || field === 'submitted_at') {
            const aDate = a[field] ? new Date(a[field]).getTime() : 0;
            const bDate = b[field] ? new Date(b[field]).getTime() : 0;
            return bDate - aDate;
          }
          
          return 0;
        });
      } else {
        sortedOffers.sort((a, b) => {
          // Handle the total_score case
          if (sortBy === 'total_score') {
            const aValue = a.total_score || 0;
            const bValue = b.total_score || 0;
            return aValue - bValue;
          }
          
          // Handle date fields
          if (sortBy === 'created_at' || sortBy === 'submitted_at') {
            const aDate = a[sortBy] ? new Date(a[sortBy]).getTime() : 0;
            const bDate = b[sortBy] ? new Date(b[sortBy]).getTime() : 0;
            return aDate - bDate;
          }
          
          return 0;
        });
      }
      
      setOffers(sortedOffers);
    } catch (err: any) {
      console.error('Error fetching offers:', err);
      setError(err.message || 'Failed to load offers');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'submitted':
        return 'bg-green-100 text-green-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'evaluated':
        return 'bg-yellow-100 text-yellow-800';
      case 'awarded':
        return 'bg-blue-100 text-blue-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
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

  if (error) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
        <div className="mt-4">
          <button 
            onClick={fetchOffers} 
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold text-gray-900">
            {user?.role === 'vendor' ? 'My Offers' : 'All Offers'}
          </h1>
          {user?.role === 'vendor' && (
            <Link
              to="/tenders?status=published"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center"
            >
              <span className="material-icons mr-2">add</span>
              Browse Tenders
            </Link>
          )}
        </div>

        {/* Filter and Sort Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Status Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="">All Status</option>
                <option value="draft">Draft</option>
                <option value="submitted">Submitted</option>
                <option value="evaluated">Evaluated</option>
                <option value="awarded">Awarded</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            {/* Sort By */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="-created_at">Newest First</option>
                <option value="created_at">Oldest First</option>
                <option value="-submitted_at">Recently Submitted</option>
                <option value="submitted_at">Earliest Submitted</option>
                <option value="-total_score">Highest Score</option>
                <option value="total_score">Lowest Score</option>
              </select>
            </div>
          </div>
        </div>

        {/* Offers List */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tender
                </th>
                {user?.role !== 'vendor' && (
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Vendor
                  </th>
                )}
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Price
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Score
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
              {offers.map((offer) => (
                <tr key={offer.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {offer.tender?.reference_number} - {offer.tender_title || offer.tender?.title}
                    </div>
                    <div className="text-sm text-gray-500">
                      {offer.tender?.title?.substring(0, 50) || ""}...
                    </div>
                  </td>
                  {user?.role !== 'vendor' && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {offer.vendor_name}
                    </td>
                  )}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(offer.status)}`}>
                      {offer.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {offer.price ? `$${Number(offer.price).toLocaleString()}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {offer.total_score ? `${offer.total_score.toFixed(2)}%` : '-'}
                    </div>
                    {offer.technical_score && offer.financial_score && (
                      <div className="text-xs text-gray-500">
                        Tech: {offer.technical_score.toFixed(1)}% / 
                        Fin: {offer.financial_score.toFixed(1)}%
                      </div>
                    )}
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
                    {user?.role === 'vendor' && offer.status === 'draft' && (
                      <Link to={`/offers/${offer.id}/edit`} className="text-green-600 hover:text-green-900">
                        Edit
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
              {offers.length === 0 && (
                <tr>
                  <td colSpan={user?.role === 'vendor' ? 6 : 7} className="px-6 py-4 text-center text-sm text-gray-500">
                    No offers found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
};

export default OfferList;