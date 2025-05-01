// client/src/api/reportsApi.ts
import { API_ENDPOINTS, getAuthHeaders } from './config';

export interface ReportGenerationData {
  tender_id: number;
  report_type: string;
  include_attachments?: boolean;
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
    const queryString = new URLSearchParams(params as Record<string, string>).toString();
    const url = queryString ? `${API_ENDPOINTS.REPORTS.BASE}?${queryString}` : API_ENDPOINTS.REPORTS.BASE;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get reports');
      } else {
        // If the response isn't JSON, throw a generic error
        throw new Error('Failed to get reports - authentication may have failed');
      }
    }
    
    return response.json();
  },
  
  getById: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.REPORTS.DETAIL(id), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get report');
      } else {
        throw new Error('Failed to get report - authentication may have failed');
      }
    }
    
    return response.json();
  },
  
  generateReport: async (data: ReportGenerationData) => {
    const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate report');
      } else {
        throw new Error('Failed to generate report - authentication may have failed');
      }
    }
    
    return response.json();
  },
  
  downloadReport: async (id: number) => {
    // Open the download URL in a new tab/window
    const token = localStorage.getItem('token');
    const downloadUrl = `${API_ENDPOINTS.REPORTS.DOWNLOAD(id)}?token=${token}`;
    window.open(downloadUrl, '_blank');
    
    return true;
  },
  
  // Generate a tender commission report
  generateTenderReport: async (tenderId: number, includeAttachments: boolean = false) => {
    const response = await fetch(API_ENDPOINTS.REPORTS.GENERATE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        tender_id: tenderId,
        report_type: 'tender_commission',
        include_attachments: includeAttachments
      }),
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate tender report');
      } else {
        throw new Error('Failed to generate tender report - authentication may have failed');
      }
    }
    
    return response.json();
  }
};