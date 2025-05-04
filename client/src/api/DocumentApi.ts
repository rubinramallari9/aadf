// client/src/api/DocumentApi.ts
import { API_ENDPOINTS, getAuthHeaders } from './config';

export interface DocumentUploadResponse {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  document_type?: string;
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

export const documentApi = {
  // Tender document methods
  getTenderDocuments: async (tenderId: number): Promise<any[]> => {
    try {
      const response = await fetch(`${API_ENDPOINTS.TENDER_DOCUMENTS}?tender_id=${tenderId}`, {
        method: 'GET',
        headers: getAuthHeaders()
      });
      
      if (!response.ok) {
        throw new Error(`Failed to get tender documents: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Error fetching tender documents:", error);
      throw error;
    }
  },
  
  uploadTenderDocument: async (tenderId: number, file: File, documentType?: string): Promise<DocumentUploadResponse> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tender_id', tenderId.toString());
      
      if (documentType) {
        formData.append('document_type', documentType);
      }
      
      const response = await fetch(API_ENDPOINTS.TENDER_DOCUMENTS, {
        method: 'POST',
        headers: {
          // Do not include Content-Type header when using FormData
          'Authorization': getAuthHeaders().Authorization
        },
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Failed to upload document: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Error uploading tender document:", error);
      throw error;
    }
  },
  
  deleteTenderDocument: async (documentId: number): Promise<void> => {
    try {
      const response = await fetch(`${API_ENDPOINTS.TENDER_DOCUMENTS}/${documentId}/`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      
      if (!response.ok) {
        throw new Error(`Failed to delete document: ${response.status}`);
      }
    } catch (error) {
      console.error("Error deleting tender document:", error);
      throw error;
    }
  },
  
  // Offer document methods
  getOfferDocuments: async (offerId: number): Promise<any[]> => {
    try {
      const response = await fetch(`${API_ENDPOINTS.OFFER_DOCUMENTS}?offer_id=${offerId}`, {
        method: 'GET',
        headers: getAuthHeaders()
      });
      
      if (!response.ok) {
        throw new Error(`Failed to get offer documents: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Error fetching offer documents:", error);
      throw error;
    }
  },
  
  uploadOfferDocument: async (offerId: number, file: File, documentType?: string): Promise<DocumentUploadResponse> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('offer_id', offerId.toString());
      
      if (documentType) {
        formData.append('document_type', documentType);
      }
      
      const response = await fetch(API_ENDPOINTS.OFFER_DOCUMENTS, {
        method: 'POST',
        headers: {
          // Do not include Content-Type header when using FormData
          'Authorization': getAuthHeaders().Authorization
        },
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Failed to upload document: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Error uploading offer document:", error);
      throw error;
    }
  },
  
  deleteOfferDocument: async (documentId: number): Promise<void> => {
    try {
      const response = await fetch(`${API_ENDPOINTS.OFFER_DOCUMENTS}/${documentId}/`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      
      if (!response.ok) {
        throw new Error(`Failed to delete document: ${response.status}`);
      }
    } catch (error) {
      console.error("Error deleting offer document:", error);
      throw error;
    }
  },
  
  // Secure download method using programmatic fetch with auth headers
  downloadWithSecureLink: async (documentType: 'report' | 'tender' | 'offer', documentId: number): Promise<boolean> => {
    try {
      console.log(`Starting secure download for ${documentType} ${documentId}`);
      
      // First, get the secure download URL
      const secureUrlEndpoint = `${API_ENDPOINTS[`${documentType.toUpperCase()}S`].BASE}/${documentId}/secure-download-link/`;
      console.log("Requesting secure URL from:", secureUrlEndpoint);
      
      const secureUrlResponse = await fetch(secureUrlEndpoint, {
        method: 'GET',
        headers: getAuthHeaders()
      });
      
      // Check if the response is HTML (possible auth issue)
      if (await isHtmlResponse(secureUrlResponse)) {
        throw new Error('Received HTML response. Your session may have expired.');
      }
      
      if (!secureUrlResponse.ok) {
        throw new Error(`Failed to get secure download link: ${secureUrlResponse.status}`);
      }
      
      const secureUrlData = await secureUrlResponse.json();
      const downloadUrl = secureUrlData.download_url;
      console.log("Received secure download URL:", downloadUrl);
      
      // Use the secure URL to download the file
      const response = await fetch(downloadUrl, {
        method: 'GET',
        // Note: No auth headers required here as the URL is already authenticated
      });
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }
      
      // Convert response to blob
      const blob = await response.blob();
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob);
      
      // Create a link element to trigger the download
      const a = document.createElement('a');
      a.href = url;
      a.download = secureUrlData.filename || `${documentType}-${documentId}`;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 0);
      
      return true;
    } catch (error) {
      console.error(`Error downloading ${documentType} ${documentId}:`, error);
      throw error;
    }
  }
};