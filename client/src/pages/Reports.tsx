// client/src/pages/Reports.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { useAuth } from '../contexts/AuthContext';
import { reportsApi } from '../api/reportsApi';
import ReportGeneratorModal from '../components/reports/ReportGeneratorModal';

// Define the types for our report objects
interface Report {
  id: number;
  tender: {
    id: number;
    reference_number: string;
    title: string;
  };
  report_type: string;
  filename: string;
  generated_by: string;
  created_at: string;
}

// Define filters for reports
interface ReportFilters {
  reportType: string;
  dateFrom: string;
  dateTo: string;
  searchTerm: string;
}

const Reports: React.FC = () => {
  const { user } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showGeneratorModal, setShowGeneratorModal] = useState<boolean>(false);
  const [filters, setFilters] = useState<ReportFilters>({
    reportType: '',
    dateFrom: '',
    dateTo: '',
    searchTerm: '',
  });

  // Report types for the filter
  const reportTypes = [
    { value: '', label: 'All Types' },
    { value: 'tender_commission', label: 'Tender Commission' },
    { value: 'tender_data', label: 'Tender Data Export' },
    { value: 'vendor_performance', label: 'Vendor Performance' },
    { value: 'evaluation_summary', label: 'Evaluation Summary' },
  ];

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      setLoading(true);
      // Use the reportsApi which properly handles authentication
      const response = await reportsApi.getAll();
      
      // Handle different response formats
      let reportsData = [];
      if (response) {
        if (Array.isArray(response)) {
          reportsData = response;
        } else if (response.results && Array.isArray(response.results)) {
          reportsData = response.results;
        } else if (typeof response === 'object') {
          reportsData = Object.values(response);
        }
      }
      
      setReports(reportsData);
    } catch (err: any) {
      console.error('Error fetching reports:', err);
      setError(err.message || 'Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const applyFilters = () => {
    // Implement filters application logic
    // This would typically involve API calls with filter parameters
    // For now, we'll just simulate filtering on the client side
    fetchReports();
  };

  const resetFilters = () => {
    setFilters({
      reportType: '',
      dateFrom: '',
      dateTo: '',
      searchTerm: '',
    });
    fetchReports();
  };

  const downloadReport = async (reportId: number) => {
    try {
      await reportsApi.downloadReport(reportId);
    } catch (error) {
      console.error('Error downloading report:', error);
      alert('Failed to download report');
    }
  };

  const handleReportGeneration = async (data: any) => {
    try {
      await reportsApi.generateReport(data);
      await fetchReports(); // Refresh the list
    } catch (err: any) {
      console.error('Error generating report:', err);
      alert(err.message || 'Failed to generate report');
    }
  };

  // Filter reports based on search term
  const filteredReports = reports.filter(report => {
    const matchesSearch = !filters.searchTerm || 
      report.tender.reference_number.toLowerCase().includes(filters.searchTerm.toLowerCase()) ||
      report.tender.title.toLowerCase().includes(filters.searchTerm.toLowerCase()) ||
      report.filename.toLowerCase().includes(filters.searchTerm.toLowerCase());
    
    const matchesType = !filters.reportType || report.report_type === filters.reportType;
    
    return matchesSearch && matchesType;
  });

  // Only allow staff and admin to view reports
  if (user?.role !== 'staff' && user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded-lg shadow-sm" role="alert">
          <div className="flex items-center">
            <span className="material-icons mr-2">warning</span>
            <strong className="font-bold">Access Denied</strong>
          </div>
          <span className="block sm:inline mt-1"> You do not have permission to access reports.</span>
        </div>
      </Layout>
    );
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-full min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
            <p className="mt-1 text-sm text-gray-500">Generate and manage procurement reports</p>
          </div>
          <button
            onClick={() => setShowGeneratorModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <span className="material-icons mr-2 text-sm">add</span>
            Generate New Report
          </button>
        </div>

        {/* Filters Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Filter Reports</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Search */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Search
                </label>
                <div className="relative">
                  <span className="material-icons absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                    search
                  </span>
                  <input
                    type="text"
                    name="searchTerm"
                    placeholder="Search reports..."
                    value={filters.searchTerm}
                    onChange={handleFilterChange}
                    className="pl-10 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  />
                </div>
              </div>

              {/* Report Type Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Report Type
                </label>
                <select
                  name="reportType"
                  value={filters.reportType}
                  onChange={handleFilterChange}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  {reportTypes.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  From Date
                </label>
                <input
                  type="date"
                  name="dateFrom"
                  value={filters.dateFrom}
                  onChange={handleFilterChange}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  To Date
                </label>
                <input
                  type="date"
                  name="dateTo"
                  value={filters.dateTo}
                  onChange={handleFilterChange}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>

            <div className="mt-4 flex justify-end space-x-4">
              <button
                onClick={resetFilters}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <span className="material-icons mr-2 text-sm">refresh</span>
                Reset
              </button>
              <button
                onClick={applyFilters}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <span className="material-icons mr-2 text-sm">filter_list</span>
                Apply Filters
              </button>
            </div>
          </div>
        </div>

        {/* Reports List */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {error && (
            <div className="bg-red-50 border-l-4 border-red-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <span className="material-icons text-red-400">error</span>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {filteredReports.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tender Reference
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Report Type
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Filename
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Generated By
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
                {filteredReports.map((report) => (
                  <tr key={report.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link 
                        to={`/tenders/${report.tender.id}`} 
                        className="text-blue-600 hover:text-blue-900 flex items-center"
                      >
                        <span className="material-icons mr-1 text-sm">receipt_long</span>
                        {report.tender.reference_number}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                        {report.report_type.replace('_', ' ').charAt(0).toUpperCase() + report.report_type.replace('_', ' ').slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="flex items-center">
                        <span className="material-icons mr-1 text-sm">description</span>
                        {report.filename}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {report.generated_by}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(report.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button 
                        onClick={() => downloadReport(report.id)}
                        className="inline-flex items-center text-blue-600 hover:text-blue-900"
                      >
                        <span className="material-icons mr-1 text-sm">file_download</span>
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12">
              <span className="material-icons text-4xl text-gray-400 mb-4">description</span>
              <h3 className="text-lg font-medium text-gray-900">No reports found</h3>
              <p className="mt-1 text-sm text-gray-500">Try adjusting your filters or generate a new report</p>
              <div className="mt-6">
                <button
                  onClick={() => setShowGeneratorModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <span className="material-icons mr-2 text-sm">add</span>
                  Generate Report
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Report Generator Modal */}
      <ReportGeneratorModal
        isOpen={showGeneratorModal}
        onClose={() => setShowGeneratorModal(false)}
        onGenerate={handleReportGeneration}
      />
    </Layout>
  );
};

export default Reports;