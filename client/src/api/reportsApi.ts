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
  },
  
  getById: async (id: number) => {
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
  },
  
  generateReport: async (data: ReportGenerationData) => {
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
  },
  
  downloadReport: async (id: number) => {
    console.log("downloadReport called with ID:", id);
    // Open the download URL in a new tab/window
    const token = localStorage.getItem('token');
    const downloadUrl = `${API_ENDPOINTS.REPORTS.DOWNLOAD(id)}?token=${token}`;
    console.log("Opening download URL:", downloadUrl);
    window.open(downloadUrl, '_blank');
    
    return true;
  },
  
  // Get report types
  getReportTypes: async () => {
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
  },
  
  // Generate a comparative report
  generateComparativeReport: async (data: any) => {
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
  },
  
  // Generate a vendor report
  generateVendorReport: async (data: any) => {
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
  },
  
  // Generate a document archive
  generateArchive: async (data: any) => {
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
  },
  
  // Advanced AI analysis report
  generateAIAnalysis: async (data: any) => {
    console.log("Generating AI analysis with data:", data);
    console.log("API endpoint:", API_ENDPOINTS.REPORTS.GENERATE);
    
    // For AI analysis, we set a special report_type
    const requestData = {
      ...data,
      report_type: 'ai_tender_analysis',
      include_ai_analysis: true
    };
    
    const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(requestData),
    });
    
    console.log("Generate AI analysis response status:", response.status);
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || 'Failed to generate AI analysis');
      } else {
        console.error("Non-JSON error response");
        throw new Error('Failed to generate AI analysis - authentication may have failed');
      }
    }
    
    const result = await response.json();
    console.log("AI analysis generation result:", result);
    return result;
  },
  
  // Get a list of generated reports for a specific tender
  getReportsByTender: async (tenderId: number) => {
    console.log(`Getting reports for tender ${tenderId}`);
    const url = `${API_ENDPOINTS.REPORTS.BASE}?tender_id=${tenderId}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || `Failed to get reports for tender ${tenderId}`);
      } else {
        console.error("Non-JSON error response");
        throw new Error(`Failed to get reports for tender ${tenderId} - authentication may have failed`);
      }
    }
    
    const data = await response.json();
    console.log(`Reports for tender ${tenderId}:`, data);
    return data;
  },
  
  // Delete a report
  deleteReport: async (id: number) => {
    console.log(`Deleting report ${id}`);
    const response = await fetch(API_ENDPOINTS.REPORTS.DETAIL(id), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || `Failed to delete report ${id}`);
      } else {
        console.error("Non-JSON error response");
        throw new Error(`Failed to delete report ${id} - authentication may have failed`);
      }
    }
    
    console.log(`Successfully deleted report ${id}`);
    return true;
  },
  
  // Update report metadata
  updateReport: async (id: number, data: any) => {
    console.log(`Updating report ${id} with data:`, data);
    const response = await fetch(API_ENDPOINTS.REPORTS.DETAIL(id), {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || `Failed to update report ${id}`);
      } else {
        console.error("Non-JSON error response");
        throw new Error(`Failed to update report ${id} - authentication may have failed`);
      }
    }
    
    const result = await response.json();
    console.log(`Successfully updated report ${id}:`, result);
    return result;
  },
  
  // Generate market insights report
  generateMarketInsights: async (data: any) => {
    console.log("Generating market insights with data:", data);
    
    // For market insights, we set a special report_type
    const requestData = {
      ...data,
      report_type: 'ai_market_insights',
      include_ai_analysis: true
    };
    
    const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(requestData),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || 'Failed to generate market insights');
      } else {
        console.error("Non-JSON error response");
        throw new Error('Failed to generate market insights - authentication may have failed');
      }
    }
    
    const result = await response.json();
    console.log("Market insights generation result:", result);
    return result;
  },
  
  // Generate evaluation summary report
  generateEvaluationSummary: async (data: any) => {
    console.log("Generating evaluation summary with data:", data);
    
    const requestData = {
      ...data,
      report_type: 'evaluation_summary'
    };
    
    const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(requestData),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || 'Failed to generate evaluation summary');
      } else {
        console.error("Non-JSON error response");
        throw new Error('Failed to generate evaluation summary - authentication may have failed');
      }
    }
    
    const result = await response.json();
    console.log("Evaluation summary generation result:", result);
    return result;
  },
  
  // Export report as different format (e.g., CSV, XLSX)
  exportReport: async (id: number, format: string) => {
    console.log(`Exporting report ${id} as ${format}`);
    
    const token = localStorage.getItem('token');
    const downloadUrl = `${API_ENDPOINTS.REPORTS.DOWNLOAD(id)}?format=${format}&token=${token}`;
    
    window.open(downloadUrl, '_blank');
    return true;
  },
  
  // Schedule a recurring report
  scheduleReport: async (data: any) => {
    console.log("Scheduling recurring report with data:", data);
    
    // This would be a custom endpoint your backend would need to implement
    const schedulerEndpoint = `${API_BASE_URL}/reports/schedule/`;
    
    const response = await fetch(schedulerEndpoint, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        console.error("API error response:", errorData);
        throw new Error(errorData.error || 'Failed to schedule report');
      } else {
        console.error("Non-JSON error response");
        throw new Error('Failed to schedule report - authentication may have failed');
      }
    }
    
    const result = await response.json();
    console.log("Report scheduling result:", result);
    return result;
  }
};