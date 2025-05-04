// client/src/pages/Reports.tsx
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { useAuth } from '../contexts/AuthContext';
import { reportsApi } from '../api/reportsApi';
import ReportGeneratorModal, { ReportGenerationData } from '../components/reports/ReportGeneratorModal';
import SecureDocumentDownloader from '../components/documents/SecureDocumentDownloader';

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

// Report type definitions
interface ReportType {
  id: string;
  name: string;
  description: string;
}

const Reports: React.FC = () => {
  const { user, isAuthenticated, token } = useAuth();
  const navigate = useNavigate();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showGeneratorModal, setShowGeneratorModal] = useState<boolean>(false);
  const [filters, setFilters] = useState<ReportFilters>({
    reportType: '',
    dateFrom: '',
    dateTo: '',
    searchTerm: '',
  });
  const [reportTypes, setReportTypes] = useState<ReportType[]>([]);
  const [selectedReportType, setSelectedReportType] = useState<string>('tender_commission');
  const [isAiAnalysisEnabled, setIsAiAnalysisEnabled] = useState<boolean>(true);
  const [generatingReport, setGeneratingReport] = useState<boolean>(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  // Check authentication on page load
  useEffect(() => {
    if (!isAuthenticated || !token) {
      navigate('/login', { state: { from: '/reports', message: 'Please log in to view reports' } });
    }
  }, [isAuthenticated, token, navigate]);

  // Get available report types
  const fetchReportTypes = async () => {
    try {
      const types = await reportsApi.getReportTypes();
      setReportTypes(types);
    } catch (err: any) {
      console.error('Error fetching report types:', err);
      if (err.message?.includes('authentication') || err.message?.includes('HTML')) {
        setError('Session expired. Please log in again.');
      }
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchReports();
      fetchReportTypes();
    }
  }, [isAuthenticated]);

  const fetchReports = async () => {
    try {
      setLoading(true);
      setError(null);
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
          // If it's some other object structure, try to extract reports
          reportsData = Object.values(response);
        }
      }
      
      setReports(reportsData);
    } catch (err: any) {
      console.error('Error fetching reports:', err);
      if (err.message?.includes('authentication') || err.message?.includes('HTML')) {
        setError('Session expired. Please log in again.');
      } else {
        setError(err.message || 'Failed to load reports');
      }
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
    // For now, just filter client-side
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

  // Handle download success
  const handleDownloadSuccess = () => {
    setSuccessMessage('Download started successfully!');
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  // Handle download error
  const handleDownloadError = (err: Error) => {
    console.error('Download error:', err);
    
    if (err.message.includes('authentication') || err.message.includes('session') || err.message.includes('HTML')) {
      setDownloadError('Authentication issue. Please try logging in again.');
      
      // Auto redirect to login after a delay
      setTimeout(() => {
        navigate('/login', { state: { from: '/reports', message: 'Your session has expired. Please log in again.' } });
      }, 3000);
    } else {
      setDownloadError(`Download failed: ${err.message}`);
      setTimeout(() => setDownloadError(null), 5000);
    }
  };

  const handleReportGeneration = async (data: ReportGenerationData) => {
    try {
      setGeneratingReport(true);
      setError(null);
      
      // Add AI analysis flag to the request
      data.include_ai_analysis = isAiAnalysisEnabled;
      
      console.log("Generating report with data:", data);
      
      // Call the API with improved error handling
      const result = await reportsApi.generateReport(data);
      
      if (result) {
        // Success - refresh the reports list
        await fetchReports();
        setShowGeneratorModal(false);
        
        // Show temporary success message
        setSuccessMessage("Report generated successfully");
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } catch (err: any) {
      console.error('Error generating report:', err);
      
      if (err.message?.includes('authentication') || err.message?.includes('HTML')) {
        setError('Session expired. Please log in again.');
        
        // Auto redirect to login after a delay
        setTimeout(() => {
          navigate('/login', { state: { from: '/reports', message: 'Your session has expired. Please log in again.' } });
        }, 3000);
      } else {
        setError(err.message || 'Failed to generate report. Please try again later.');
      }
    } finally {
      setGeneratingReport(false);
    }
  };

  // Filter reports based on search term and other filters
  const filteredReports = reports.filter(report => {
    const matchesSearch = !filters.searchTerm || 
      report.tender.reference_number.toLowerCase().includes(filters.searchTerm.toLowerCase()) ||
      report.tender.title.toLowerCase().includes(filters.searchTerm.toLowerCase()) ||
      report.filename.toLowerCase().includes(filters.searchTerm.toLowerCase());
    
    const matchesType = !filters.reportType || report.report_type === filters.reportType;
    
    let matchesDate = true;
    if (filters.dateFrom && filters.dateTo) {
      const reportDate = new Date(report.created_at);
      const fromDate = new Date(filters.dateFrom);
      const toDate = new Date(filters.dateTo);
      toDate.setHours(23, 59, 59, 999); // Set to end of day
      
      matchesDate = reportDate >= fromDate && reportDate <= toDate;
    }
    
    return matchesSearch && matchesType && matchesDate;
  });

  // Get report type name from ID
  const getReportTypeName = (typeId: string) => {
    const reportType = reportTypes.find(type => type.id === typeId);
    return reportType ? reportType.name : typeId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

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
          <div className="flex gap-2">
            <div className="relative inline-block text-left">
              <button 
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                onClick={() => setShowGeneratorModal(true)}
              >
                <span className="material-icons mr-2 text-sm">add</span>
                Generate Report
              </button>
            </div>
          </div>
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
                  <option value="">All Types</option>
                  {reportTypes.map((type) => (
                    <option key={type.id} value={type.id}>
                      {type.name}
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

        {/* AI Analysis Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                <span className="material-icons text-blue-600">smart_toy</span>
              </span>
              <div>
                <h3 className="text-lg font-medium text-gray-900">AI Analysis</h3>
                <p className="text-sm text-gray-500">Enable AI-powered insights in your reports</p>
              </div>
            </div>
            <div className="flex items-center">
              <span className="text-sm font-medium text-gray-700 mr-2">
                {isAiAnalysisEnabled ? 'Enabled' : 'Disabled'}
              </span>
              <button
                onClick={() => setIsAiAnalysisEnabled(!isAiAnalysisEnabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full ${
                  isAiAnalysisEnabled ? 'bg-blue-600' : 'bg-gray-200'
                } transition-colors focus:outline-none`}
              >
                <span
                  className={`${
                    isAiAnalysisEnabled ? 'translate-x-6' : 'translate-x-1'
                  } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                />
              </button>
            </div>
          </div>
          <div className="mt-4 bg-blue-50 rounded p-4">
            <p className="text-sm text-blue-800">
              AI-powered reporting provides intelligent insights, pattern detection, and recommendations based on your procurement data. 
              Reports will include visualizations, trend analysis, and suggested optimizations.
            </p>
          </div>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {successMessage && (
          <div className="bg-green-50 border-l-4 border-green-400 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-green-700">{successMessage}</p>
              </div>
            </div>
          </div>
        )}

        {downloadError && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{downloadError}</p>
              </div>
            </div>
          </div>
        )}

        {/* Reports List */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {filteredReports.length > 0 ? (
            <div className="overflow-x-auto">
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
                          {getReportTypeName(report.report_type)}
                        </span>
                        {report.report_type.includes('ai_') && (
                          <span className="ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">
                            AI Enhanced
                          </span>
                        )}
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
                        {/* Using SecureDocumentDownloader component for report downloads */}
                        <SecureDocumentDownloader 
                          documentType="report" 
                          documentId={report.id}
                          buttonText="Download"
                          className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                          size="small"
                          onSuccess={handleDownloadSuccess}
                          onError={handleDownloadError}
                        />
                        
                        {report.report_type === 'archive' && (
                          <button 
                            onClick={() => alert('Opening archive view...')}
                            className="inline-flex items-center ml-2 px-3 py-1 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                          >
                            <span className="material-icons mr-1 text-sm">folder_open</span>
                            View
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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