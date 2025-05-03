// client/src/pages/Reports.tsx - Enhanced with AI features
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

// Report type definitions
interface ReportType {
  id: string;
  name: string;
  description: string;
}

const Reports: React.FC = () => {
  const { user } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showGeneratorModal, setShowGeneratorModal] = useState<boolean>(false);
  const [showComparativeModal, setShowComparativeModal] = useState<boolean>(false);
  const [showVendorAnalysisModal, setShowVendorAnalysisModal] = useState<boolean>(false);
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

  // Get available report types
  const fetchReportTypes = async () => {
    try {
      const types = await reportsApi.getReportTypes();
      setReportTypes(types);
    } catch (err) {
      console.error('Error fetching report types:', err);
    }
  };

  useEffect(() => {
    fetchReports();
    fetchReportTypes();
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
          // If it's some other object structure, try to extract reports
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
      setGeneratingReport(true);
      
      // Add AI analysis flag to the request
      data.enableAiAnalysis = isAiAnalysisEnabled;
      
      await reportsApi.generateReport(data);
      await fetchReports(); // Refresh the list
      setShowGeneratorModal(false);
    } catch (err: any) {
      console.error('Error generating report:', err);
      setError(err.message || 'Failed to generate report');
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleComparativeReport = async (data: any) => {
    try {
      setGeneratingReport(true);
      data.enableAiAnalysis = isAiAnalysisEnabled;
      await reportsApi.generateComparativeReport(data);
      await fetchReports();
      setShowComparativeModal(false);
    } catch (err: any) {
      console.error('Error generating comparative report:', err);
      setError(err.message || 'Failed to generate comparative report');
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleVendorAnalysisReport = async (data: any) => {
    try {
      setGeneratingReport(true);
      data.enableAiAnalysis = isAiAnalysisEnabled;
      await reportsApi.generateVendorReport(data);
      await fetchReports();
      setShowVendorAnalysisModal(false);
    } catch (err: any) {
      console.error('Error generating vendor analysis:', err);
      setError(err.message || 'Failed to generate vendor analysis report');
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleArchiveGeneration = async (tenderId: number) => {
    try {
      setGeneratingReport(true);
      await reportsApi.generateArchive({ tender_id: tenderId, include_offers: true });
      await fetchReports();
    } catch (err: any) {
      console.error('Error generating archive:', err);
      setError(err.message || 'Failed to generate archive');
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
            <div className="dropdown inline-block relative">
              <button className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                <span className="material-icons mr-2 text-sm">add</span>
                Generate Report
                <span className="material-icons ml-1">arrow_drop_down</span>
              </button>
              <ul className="dropdown-menu absolute hidden text-gray-700 pt-1 right-0 z-10 w-56">
                <li>
                  <button
                    onClick={() => setShowGeneratorModal(true)}
                    className="rounded-t bg-white hover:bg-gray-100 py-2 px-4 block whitespace-no-wrap w-full text-left"
                  >
                    Tender Report
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setShowComparativeModal(true)}
                    className="bg-white hover:bg-gray-100 py-2 px-4 block whitespace-no-wrap w-full text-left"
                  >
                    Comparative Analysis
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setShowVendorAnalysisModal(true)}
                    className="bg-white hover:bg-gray-100 py-2 px-4 block whitespace-no-wrap w-full text-left"
                  >
                    Vendor Analysis
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => alert('Please select a tender first to generate an archive')}
                    className="rounded-b bg-white hover:bg-gray-100 py-2 px-4 block whitespace-no-wrap w-full text-left"
                  >
                    Document Archive
                  </button>
                </li>
              </ul>
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
                        <button 
                          onClick={() => downloadReport(report.id)}
                          className="inline-flex items-center text-blue-600 hover:text-blue-900 mr-3"
                        >
                          <span className="material-icons mr-1 text-sm">file_download</span>
                          Download
                        </button>
                        {report.report_type === 'archive' && (
                          <button 
                            onClick={() => alert('Opening archive...')}
                            className="inline-flex items-center text-green-600 hover:text-green-900"
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

      {/* Comparative Analysis Modal */}
      {showComparativeModal && (
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
                      Generate Comparative Analysis
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        Compare multiple tenders to identify patterns and insights.
                      </p>
                      {/* Comparative analysis form would go here */}
                      <div className="mt-4">
                        <div className="form-group mb-4">
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Select Tenders to Compare
                          </label>
                          <select multiple className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md h-32">
                            <option>TND-20250101-ABCDEF - Office Supplies</option>
                            <option>TND-20250215-123456 - IT Equipment</option>
                            <option>TND-20250305-XYZ123 - Consulting Services</option>
                          </select>
                          <p className="mt-1 text-xs text-gray-500">Hold Ctrl/Cmd to select multiple tenders</p>
                        </div>
                        
                        <div className="form-group mb-4">
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Format
                          </label>
                          <div className="flex space-x-4">
                            <div className="flex items-center">
                              <input type="radio" id="format-pdf" name="format" value="pdf" className="h-4 w-4 text-blue-600" defaultChecked />
                              <label htmlFor="format-pdf" className="ml-2 text-sm text-gray-700">PDF Report</label>
                            </div>
                            <div className="flex items-center">
                              <input type="radio" id="format-csv" name="format" value="csv" className="h-4 w-4 text-blue-600" />
                              <label htmlFor="format-csv" className="ml-2 text-sm text-gray-700">CSV Data</label>
                            </div>
                          </div>
                        </div>
                        
                        <div className="form-group flex items-center mt-4">
                          <input 
                            type="checkbox" 
                            id="include-ai-analysis" 
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            checked={isAiAnalysisEnabled}
                            onChange={() => setIsAiAnalysisEnabled(!isAiAnalysisEnabled)}
                          />
                          <label htmlFor="include-ai-analysis" className="ml-2 block text-sm text-gray-900">
                            Include AI Analysis
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button 
                  type="button" 
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={() => alert('Generating comparative analysis...')}
                  disabled={generatingReport}
                >
                  {generatingReport ? 'Generating...' : 'Generate Analysis'}
                </button>
                <button 
                  type="button" 
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={() => setShowComparativeModal(false)}
                  disabled={generatingReport}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Vendor Analysis Modal */}
      {showVendorAnalysisModal && (
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
                      Generate Vendor Analysis
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        Analyze vendor performance and participation over time.
                      </p>
                      <div className="mt-4">
                        <div className="form-group mb-4">
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Select Vendor
                          </label>
                          <select className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
                            <option value="">Select a vendor</option>
                            <option value="1">TechSolutions Inc</option>
                            <option value="2">Global Supplies Ltd</option>
                            <option value="3">Consulting Partners Group</option>
                          </select>
                        </div>
                        
                        <div className="form-group mb-4">
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Analysis Period
                          </label>
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">From</label>
                              <input type="date" className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md" />
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">To</label>
                              <input type="date" className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md" />
                            </div>
                          </div>
                        </div>
                        
                        <div className="form-group mb-4">
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Report Format
                          </label>
                          <div className="flex space-x-4">
                            <div className="flex items-center">
                              <input type="radio" id="v-format-pdf" name="v-format" value="pdf" className="h-4 w-4 text-blue-600" defaultChecked />
                              <label htmlFor="v-format-pdf" className="ml-2 text-sm text-gray-700">PDF Report</label>
                            </div>
                            <div className="flex items-center">
                              <input type="radio" id="v-format-csv" name="v-format" value="csv" className="h-4 w-4 text-blue-600" />
                              <label htmlFor="v-format-csv" className="ml-2 text-sm text-gray-700">CSV Data</label>
                            </div>
                          </div>
                        </div>
                        
                        <div className="form-group flex items-center mt-4">
                          <input 
                            type="checkbox" 
                            id="v-include-ai-analysis" 
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            checked={isAiAnalysisEnabled}
                            onChange={() => setIsAiAnalysisEnabled(!isAiAnalysisEnabled)}
                          />
                          <label htmlFor="v-include-ai-analysis" className="ml-2 block text-sm text-gray-900">
                            Include AI Analysis
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button 
                  type="button" 
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={() => alert('Generating vendor analysis...')}
                  disabled={generatingReport}
                >
                  {generatingReport ? 'Generating...' : 'Generate Analysis'}
                </button>
                <button 
                  type="button" 
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                  onClick={() => setShowVendorAnalysisModal(false)}
                  disabled={generatingReport}
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

export default Reports;