// client/src/components/reports/ReportGeneratorModal.tsx
import React, { useState, useEffect, useRef } from 'react';
import { tenderApi } from '../../api/api';

interface Tender {
  id: number;
  reference_number: string;
  title: string;
}

interface ReportGeneratorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (data: ReportGenerationData) => Promise<void>;
}

interface ReportGenerationData {
  tender_id: number;
  report_type: string;
  include_attachments?: boolean;
  include_ai_analysis?: boolean;
  date_range?: {
    from: string;
    to: string;
  };
  additional_notes?: string;
}

const ReportGeneratorModal: React.FC<ReportGeneratorModalProps> = ({ 
  isOpen, 
  onClose,
  onGenerate 
}) => {
  const [formData, setFormData] = useState<ReportGenerationData>({
    tender_id: 0,
    report_type: 'tender_commission',
    include_attachments: false,
    include_ai_analysis: true,
    date_range: {
      from: '',
      to: ''
    },
    additional_notes: ''
  });
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Report types with enhanced AI options
  const reportTypes = [
    { value: 'tender_commission', label: 'Tender Commission Report' },
    { value: 'ai_tender_analysis', label: 'AI Tender Analysis' },
    { value: 'tender_data', label: 'Tender Data Export (CSV)' },
    { value: 'vendor_performance', label: 'Vendor Performance Analysis' },
    { value: 'ai_market_insights', label: 'AI Market Insights' },
    { value: 'evaluation_summary', label: 'Evaluation Summary Report' },
  ];

  useEffect(() => {
    if (isOpen) {
      fetchTenders();
      document.body.style.overflow = 'hidden';
      
      // Add escape key handler
      const handleEscape = (event: KeyboardEvent) => {
        if (event.key === 'Escape') {
          onClose();
        }
      };
      
      document.addEventListener('keydown', handleEscape);
      return () => {
        document.removeEventListener('keydown', handleEscape);
        document.body.style.overflow = 'unset';
      };
    }
  }, [isOpen, onClose]);

  const fetchTenders = async () => {
    try {
      setLoading(true);
      const response = await tenderApi.getAll({ status: 'closed,awarded' });

      // Handle different response formats
      let tendersData: Tender[] = [];
      if (response) {
        if (Array.isArray(response)) {
          tendersData = response;
        } else if (response.results && Array.isArray(response.results)) {
          tendersData = response.results;
        } else if (typeof response === 'object') {
          tendersData = Object.values(response) as Tender[];
        }
      }
      
      setTenders(tendersData);
      
      // Set the first tender as default if any exist
      if (tendersData.length > 0) {
        setFormData(prev => ({
          ...prev,
          tender_id: tendersData[0].id
        }));
      }
    } catch (err: any) {
      console.error('Error fetching tenders:', err);
      setError(err.message || 'Failed to load tenders');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checkbox = e.target as HTMLInputElement;
      setFormData(prev => ({
        ...prev,
        [name]: checkbox.checked
      }));
    } else if (name.startsWith('date_range.')) {
      const dateField = name.split('.')[1];
      setFormData(prev => ({
        ...prev,
        date_range: {
          ...prev.date_range!,
          [dateField]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: type === 'select-one' && name === 'tender_id' ? parseInt(value) : value
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.tender_id === 0) {
      setError('Please select a tender');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      await onGenerate(formData);
      onClose();
    } catch (err: any) {
      console.error('Error generating report:', err);
      setError(err.message || 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  // Check if the selected report type is AI-enabled
  const isAiReportType = formData.report_type.startsWith('ai_');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div 
          className="fixed inset-0 bg-transparent transition-opacity" 
          aria-hidden="true"
          onClick={onClose}
        ></div>

        {/* Center modal */}
        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        
        {/* Modal panel */}
        <div 
          ref={modalRef}
          className="relative inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full z-50"
          role="dialog" 
          aria-modal="true" 
          aria-labelledby="modal-headline"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg leading-6 font-medium text-gray-900" id="modal-headline">
                    Generate New Report
                  </h3>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-500 focus:outline-none"
                  >
                    <span className="material-icons">close</span>
                  </button>
                </div>
                
                {error && (
                  <div className="mt-2 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                    <span className="block sm:inline">{error}</span>
                  </div>
                )}
                
                <div className="mt-4">
                  <form onSubmit={handleSubmit}>
                    <div className="space-y-4">
                      {/* Tender Selection */}
                      <div>
                        <label htmlFor="tender_id" className="block text-sm font-medium text-gray-700">
                          Select Tender *
                        </label>
                        <select
                          id="tender_id"
                          name="tender_id"
                          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                          value={formData.tender_id}
                          onChange={handleInputChange}
                          required
                        >
                          <option value="">Select a tender</option>
                          {tenders.map((tender) => (
                            <option key={tender.id} value={tender.id}>
                              {tender.reference_number} - {tender.title}
                            </option>
                          ))}
                        </select>
                      </div>
                      
                      {/* Report Type */}
                      <div>
                        <label htmlFor="report_type" className="block text-sm font-medium text-gray-700">
                          Report Type *
                        </label>
                        <select
                          id="report_type"
                          name="report_type"
                          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                          value={formData.report_type}
                          onChange={handleInputChange}
                          required
                        >
                          {reportTypes.map((type) => (
                            <option key={type.value} value={type.value}>
                              {type.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* AI Analysis Option */}
                      {!isAiReportType && (
                        <div className="flex items-start">
                          <div className="flex items-center h-5">
                            <input
                              id="include_ai_analysis"
                              name="include_ai_analysis"
                              type="checkbox"
                              className="focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300 rounded"
                              checked={formData.include_ai_analysis}
                              onChange={handleInputChange}
                            />
                          </div>
                          <div className="ml-3 text-sm">
                            <label htmlFor="include_ai_analysis" className="font-medium text-gray-700">
                              Include AI Analysis
                            </label>
                            <p className="text-gray-500">Use AI to generate insights, recommendations, and enhanced visualizations</p>
                          </div>
                        </div>
                      )}

                      {/* AI Info Box */}
                      {(isAiReportType || formData.include_ai_analysis) && (
                        <div className="bg-blue-50 rounded p-4">
                          <div className="flex">
                            <div className="flex-shrink-0">
                              <span className="material-icons text-blue-600">smart_toy</span>
                            </div>
                            <div className="ml-3">
                              <h3 className="text-sm font-medium text-blue-800">AI-Enhanced Report</h3>
                              <div className="mt-2 text-sm text-blue-700">
                                <p>This report will include AI-generated insights such as:</p>
                                <ul className="list-disc pl-5 mt-1 space-y-1">
                                  <li>Trend identification and pattern recognition</li>
                                  <li>Anomaly detection and risk assessment</li>
                                  <li>Predictive analytics and forecasting</li>
                                  <li>Custom visualizations and comparative analysis</li>
                                  <li>Actionable recommendations</li>
                                </ul>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Include Attachments */}
                      <div className="flex items-start">
                        <div className="flex items-center h-5">
                          <input
                            id="include_attachments"
                            name="include_attachments"
                            type="checkbox"
                            className="focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300 rounded"
                            checked={formData.include_attachments}
                            onChange={handleInputChange}
                          />
                        </div>
                        <div className="ml-3 text-sm">
                          <label htmlFor="include_attachments" className="font-medium text-gray-700">
                            Include Attachments
                          </label>
                          <p className="text-gray-500">Include all related documents and attachments in the report</p>
                        </div>
                      </div>
                      
                      {/* Date Range */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label htmlFor="date_range.from" className="block text-sm font-medium text-gray-700">
                            From Date
                          </label>
                          <input
                            type="date"
                            id="date_range.from"
                            name="date_range.from"
                            className="mt-1 focus:ring-blue-500 focus:border-blue-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                            value={formData.date_range?.from || ''}
                            onChange={handleInputChange}
                          />
                        </div>
                        <div>
                          <label htmlFor="date_range.to" className="block text-sm font-medium text-gray-700">
                            To Date
                          </label>
                          <input
                            type="date"
                            id="date_range.to"
                            name="date_range.to"
                            className="mt-1 focus:ring-blue-500 focus:border-blue-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                            value={formData.date_range?.to || ''}
                            onChange={handleInputChange}
                          />
                        </div>
                      </div>
                      
                      {/* Additional Notes */}
                      <div>
                        <label htmlFor="additional_notes" className="block text-sm font-medium text-gray-700">
                          Additional Notes
                        </label>
                        <textarea
                          id="additional_notes"
                          name="additional_notes"
                          rows={3}
                          className="mt-1 focus:ring-blue-500 focus:border-blue-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                          value={formData.additional_notes || ''}
                          onChange={handleInputChange}
                          placeholder="Any specific information or sections to include..."
                        />
                      </div>
                    </div>

                    <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                      <button
                        type="submit"
                        className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:col-start-2 sm:text-sm"
                        disabled={loading}
                      >
                        {loading ? 'Generating...' : 'Generate Report'}
                      </button>
                      <button
                        type="button"
                        className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                        onClick={onClose}
                        disabled={loading}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportGeneratorModal;