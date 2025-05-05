// client/src/api/reportsApi.ts
import { API_ENDPOINTS, getAuthHeaders } from './config';
import { documentApi } from './DocumentApi';

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

// Helper function to check if the response is HTML instead of JSON
const isHtmlResponse = async (response: Response): Promise<boolean> => {
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('text/html')) {
    return true;
  }
  
  // Try to peek at the response
  const clonedResponse = response.clone();
  try {
    const text = await clonedResponse.text();
    return text.trim().startsWith('<!DOCTYPE') || text.trim().startsWith('<html');
  } catch (error) {
    return false;
  }
};

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
      
      // Check if we got HTML instead of JSON (auth issue)
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response. Your session may have expired.');
      }
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication failed. Please log in again.');
        }
        
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
      
      // Check if we got HTML instead of JSON (auth issue)
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response. Your session may have expired.');
      }
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication failed. Please log in again.');
        }
        
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
      
      // Stringently validate all required fields
      if (!data.tender_id || typeof data.tender_id !== 'number' || data.tender_id <= 0) {
        throw new Error('Valid tender ID is required');
      }
      
      // Ensure report_type is a valid non-empty string
      if (!data.report_type || typeof data.report_type !== 'string') {
        data.report_type = 'tender_commission';
      }
      
      // Create a complete request object with defaults for optional fields 
      const requestData = {
        tender_id: data.tender_id,
        report_type: data.report_type,
        include_attachments: data.include_attachments !== undefined ? data.include_attachments : false,
        include_ai_analysis: data.include_ai_analysis !== undefined ? data.include_ai_analysis : true,
        date_range: data.date_range || undefined,
        additional_notes: data.additional_notes || ''
      };
      
      console.log("Sending request to API endpoint:", API_ENDPOINTS.REPORTS.GENERATE);
      console.log("Request data:", JSON.stringify(requestData, null, 2)); // Pretty print JSON
      
      // Explicitly set Content-Type header
      const headers = {
        ...getAuthHeaders(),
        'Content-Type': 'application/json'
      };
      
      const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(requestData),
      });
      
      console.log("Generate report response status:", response.status);
      console.log("Response headers:", Object.fromEntries([...response.headers]));
      
      // Check if we got HTML instead of JSON (auth issue)
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response. Your session may have expired.');
      }
      
      // If response isn't successful, try to get error information
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication failed. Please log in again.');
        }
        
        const contentType = response.headers.get('content-type');
        let errorMessage = `Failed to generate report (Status: ${response.status})`;
        
        try {
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json();
            console.error("API error response:", errorData);
            errorMessage = errorData.error || errorData.message || errorMessage;
          } else {
            // Try to get text error
            const errorText = await response.text();
            console.error("API error text response:", errorText);
            if (errorText && errorText.length < 500) {
              errorMessage = `${errorMessage}: ${errorText}`;
            }
          }
        } catch (parseError) {
          console.error("Error parsing error response:", parseError);
        }
        
        throw new Error(errorMessage);
      }
      
      // Process successful response
      const result = await response.json();
      console.log("Report generation result:", result);
      return result;
    } catch (err: any) {
      console.error("Error in generateReport:", err);
      throw err;
    }
  },
  
  // Use secure download method for downloading reports
  downloadReport: async (id: number) => {
    try {
      console.log("downloadReport called with ID:", id);
      
      // Use the secure download method
      return await documentApi.downloadWithSecureLink('report', id);
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
      
      // Check if we got HTML instead of JSON (auth issue)
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response. Your session may have expired.');
      }
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication failed. Please log in again.');
        }
        
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
  }
};