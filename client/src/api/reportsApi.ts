// client/src/api/reportsApi.ts
import { API_ENDPOINTS, getAuthHeaders, API_BASE_URL } from './config';

export interface ReportGenerationData {
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
  
export interface Report {
  id: number;
  tender: {
    id: number;
    reference_number: string;
    title: string;
  };
  generated_by: string;
  report_type: string;
  filename: string;
  file_path: string;
  created_at: string;
}

export const reportsApi = {
  getAll: async (params = {}) => {
    try {
      console.log("getAll reports called with params:", params);
      const queryString = new URLSearchParams(params as Record<string, string>).toString();
      const url = queryString ? `${API_ENDPOINTS.REPORTS.BASE}?${queryString}` : API_ENDPOINTS.REPORTS.BASE;
      
      console.log("Fetching reports from URL:", url);
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      console.log("Reports API response status:", response.status);
      
      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          console.error("API error response:", errorData);
          throw new Error(errorData.error || 'Failed to get reports');
        } else {
          // If the response isn't JSON, throw a generic error
          console.error("Non-JSON error response");
          throw new Error('Failed to get reports - authentication may have failed');
        }
      }
      
      const data = await response.json();
      console.log("Reports data received:", data);
      return data;
    } catch (err) {
      console.error("Error in getAll reports:", err);
      // Return empty array instead of failing
      return [];
    }
  },
  
  getById: async (id: number) => {
    try {
      console.log("getById report called with ID:", id);
      const response = await fetch(API_ENDPOINTS.REPORTS.DETAIL(id), {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          console.error("API error response:", errorData);
          throw new Error(errorData.error || 'Failed to get report');
        } else {
          console.error("Non-JSON error response");
          throw new Error('Failed to get report - authentication may have failed');
        }
      }
      
      const data = await response.json();
      console.log("Report data received:", data);
      return data;
    } catch (err) {
      console.error("Error in getById report:", err);
      throw err;
    }
  },
  
  generateReport: async (data: ReportGenerationData) => {
    try {
      console.log("generateReport called with data:", data);
      console.log("API endpoint:", API_ENDPOINTS.REPORTS.GENERATE);
      
      const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      
      console.log("Generate report response status:", response.status);
      
      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          console.error("API error response:", errorData);
          throw new Error(errorData.error || 'Failed to generate report');
        } else {
          console.error("Non-JSON error response");
          throw new Error('Failed to generate report - authentication may have failed');
        }
      }
      
      const result = await response.json();
      console.log("Report generation result:", result);
      return result;
    } catch (err) {
      console.error("Error in generateReport:", err);
      throw err;
    }
  },
  
  downloadReport: async (id: number) => {
    try {
      console.log("downloadReport called with ID:", id);
      // Open the download URL in a new tab/window
      const token = localStorage.getItem('token');
      const downloadUrl = `${API_ENDPOINTS.REPORTS.DOWNLOAD(id)}?token=${token}`;
      console.log("Opening download URL:", downloadUrl);
      window.open(downloadUrl, '_blank');
      
      return true;
    } catch (err) {
      console.error("Error in downloadReport:", err);
      throw err;
    }
  },
  
  // Get report types
  getReportTypes: async () => {
    try {
      console.log("getReportTypes called");
      console.log("API endpoint:", API_ENDPOINTS.REPORTS.REPORT_TYPES);
      
      const response = await fetch(API_ENDPOINTS.REPORTS.REPORT_TYPES, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      console.log("Report types response status:", response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || 'Failed to get report types');
      }
      
      const data = await response.json();
      console.log("Report types received:", data);
      return data;
    } catch (err) {
      console.error("Error in getReportTypes:", err);
      // Return some default report types instead of failing
      return [
        {
          id: 'tender_commission',
          name: 'Tender Commission Report',
          description: 'Detailed report for the tender commission'
        },
        {
          id: 'tender_data',
          name: 'Tender Data Export',
          description: 'Export of tender data in CSV format'
        },
        {
          id: 'ai_tender_analysis',
          name: 'AI-Enhanced Analysis',
          description: 'Advanced AI analysis of tender and offers'
        },
        {
          id: 'evaluation_summary',
          name: 'Evaluation Summary',
          description: 'Summary of all evaluations for a tender'
        }
      ];
    }
  },
  
  // Generate a comparative report
  generateComparativeReport: async (data: any) => {
    try {
      console.log("generateComparativeReport called with data:", data);
      console.log("API endpoint:", API_ENDPOINTS.REPORTS.GENERATE_COMPARATIVE);
      
      const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE_COMPARATIVE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      
      console.log("Generate comparative report response status:", response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || 'Failed to generate comparative report');
      }
      
      const result = await response.json();
      console.log("Comparative report generation result:", result);
      return result;
    } catch (err) {
      console.error("Error in generateComparativeReport:", err);
      throw err;
    }
  },
  
  // Generate a vendor report
  generateVendorReport: async (data: any) => {
    try {
      console.log("generateVendorReport called with data:", data);
      console.log("API endpoint:", API_ENDPOINTS.REPORTS.GENERATE_VENDOR);
      
      const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE_VENDOR, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      
      console.log("Generate vendor report response status:", response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || 'Failed to generate vendor report');
      }
      
      const result = await response.json();
      console.log("Vendor report generation result:", result);
      return result;
    } catch (err) {
      console.error("Error in generateVendorReport:", err);
      throw err;
    }
  },
  
  // Generate a document archive
  generateArchive: async (data: any) => {
    try {
      console.log("generateArchive called with data:", data);
      console.log("API endpoint:", API_ENDPOINTS.REPORTS.GENERATE_ARCHIVE);
      
      const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE_ARCHIVE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      
      console.log("Generate archive response status:", response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || 'Failed to generate archive');
      }
      
      const result = await response.json();
      console.log("Archive generation result:", result);
      return result;
    } catch (err) {
      console.error("Error in generateArchive:", err);
      throw err;
    }
  }
};