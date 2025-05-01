// client/src/pages/tenders/TenderSearch.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { tenderApi } from '../../api/api';

interface SearchFilters {
  search: string;
  status: string;
  category: string;
  start_date: string;
  end_date: string;
  deadline_before: string;
  deadline_after: string;
}

const TenderSearch: React.FC = () => {
  const { user } = useAuth();
  const [tenders, setTenders] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);

  const [filters, setFilters] = useState<SearchFilters>({
    search: '',
    status: '',
    category: '',
    start_date: '',
    end_date: '',
    deadline_before: '',
    deadline_after: '',
  });

  useEffect(() => {
    // Load search results on component mount if there are any filters
    if (Object.values(filters).some(value => value !== '')) {
      performSearch();
    }
  }, []);

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    performSearch();
  };

  const performSearch = async () => {
    try {
      setLoading(true);
      setError(null);

      // Filter out empty values from the search parameters
      const searchParams: Record<string, string> = {};
      Object.entries(filters).forEach(([key, value]) => {
        if (value) {
          searchParams[key] = value;
        }
      });

      const response = await tenderApi.search(searchParams);
      setTenders(response);
    } catch (err: any) {
      console.error('Error searching tenders:', err);
      setError(err.message || 'Failed to search tenders');
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = () => {
    setFilters({
      search: '',
      status: '',
      category: '',
      start_date: '',
      end_date: '',
      deadline_before: '',
      deadline_after: '',
    });
    setTenders([]);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published':
        return 'bg-green-100 text-green-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'closed':
        return 'bg-yellow-100 text-yellow-800';
      case 'awarded':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Search Tenders</h1>
          <p className="mt-1 text-sm text-gray-600">
            Find tenders using various search criteria
          </p>
        </div>

        {/* Search Form */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <form onSubmit={handleSearch}>
            {/* Basic Search */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="lg:col-span-2">
                <label htmlFor="search" className="block text-sm font-medium text-gray-700">
                  Search Terms
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <span className="material-icons absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                    search
                  </span>
                  <input
                    type="text"
                    name="search"
                    id="search"
                    value={filters.search}
                    onChange={handleFilterChange}
                    placeholder="Enter keywords, reference number..."
                    className="pl-10 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="status" className="block text-sm font-medium text-gray-700">
                  Status
                </label>
                <select
                  name="status"
                  id="status"
                  value={filters.status}
                  onChange={handleFilterChange}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option value="">All Categories</option>
                  <option value="goods">Goods</option>
                  <option value="services">Services</option>
                  <option value="works">Works</option>
                </select>
              </div>
            </div>

            {/* Advanced Search Toggle */}
            <div className="mb-4">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
              >
                <span className="material-icons text-lg mr-1">
                  {showAdvanced ? 'expand_less' : 'expand_more'}
                </span>
                {showAdvanced ? 'Hide' : 'Show'} Advanced Search
              </button>
            </div>

            {/* Advanced Search Options */}
            {showAdvanced && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 pt-4 border-t border-gray-200">
                <div>
                  <label htmlFor="start_date" className="block text-sm font-medium text-gray-700">
                    Created After
                  </label>
                  <input
                    type="date"
                    name="start_date"
                    id="start_date"
                    value={filters.start_date}
                    onChange={handleFilterChange}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="end_date" className="block text-sm font-medium text-gray-700">
                    Created Before
                  </label>
                  <input
                    type="date"
                    name="end_date"
                    id="end_date"
                    value={filters.end_date}
                    onChange={handleFilterChange}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="deadline_after" className="block text-sm font-medium text-gray-700">
                    Deadline After
                  </label>
                  <input
                    type="date"
                    name="deadline_after"
                    id="deadline_after"
                    value={filters.deadline_after}
                    onChange={handleFilterChange}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="deadline_before" className="block text-sm font-medium text-gray-700">
                    Deadline Before
                  </label>
                  <input
                    type="date"
                    name="deadline_before"
                    id="deadline_before"
                    value={filters.deadline_before}
                    onChange={handleFilterChange}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>
              </div>
            )}

            {/* Search Actions */}
            <div className="flex justify-between items-center">
              <button
                type="button"
                onClick={clearFilters}
                className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Clear Filters
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </form>
        </div>

        {/* Search Results */}
        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold">Error!</strong>
            <span className="block sm:inline"> {error}</span>
          </div>
        )}

        {tenders.length > 0 && (
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Search Results</h2>
              <p className="text-sm text-gray-500">{tenders.length} tenders found</p>
            </div>
            <div className="overflow-x-auto">
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
                      Category
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Deadline
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Participation
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tenders.map((tender) => (
                    <tr key={tender.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {tender.reference_number}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{tender.title}</div>
                        <div className="text-sm text-gray-500">{tender.description.substring(0, 50)}...</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {tender.category || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(tender.status)}`}>
                          {tender.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(tender.submission_deadline).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {user?.role === 'vendor' && tender.has_participated && (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                            Participated
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link to={`/tenders/${tender.id}`} className="text-blue-600 hover:text-blue-900 mr-4">
                          View
                        </Link>
                        {user?.role === 'vendor' && tender.status === 'published' && !tender.has_participated && (
                          <Link to={`/offers/create?tender=${tender.id}`} className="text-green-600 hover:text-green-900">
                            Submit Offer
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tenders.length === 0 && !loading && !error && (
          <div className="bg-white shadow rounded-lg p-6 text-center">
            <span className="material-icons text-4xl text-gray-400 mb-4">search</span>
            <p className="text-gray-500">
              {Object.values(filters).some(value => value !== '') 
                ? 'No tenders found matching your search criteria'
                : 'Enter search terms above to find tenders'}
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default TenderSearch;