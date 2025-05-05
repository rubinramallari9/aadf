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
      const response = await fetch(`${API_ENDPOINTS.DOCUMENTS.TENDER.BY_TENDER(tenderId)}`, {
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
      
      const response = await fetch(API_ENDPOINTS.DOCUMENTS.TENDER.BASE, {
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
      const response = await fetch(`${API_ENDPOINTS.DOCUMENTS.TENDER.DETAIL(documentId)}`, {
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
      const response = await fetch(`${API_ENDPOINTS.DOCUMENTS.OFFER.BY_OFFER(offerId)}`, {
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
      
      const response = await fetch(API_ENDPOINTS.DOCUMENTS.OFFER.BASE, {
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
      const response = await fetch(`${API_ENDPOINTS.DOCUMENTS.OFFER.DETAIL(documentId)}`, {
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
  
  // Secure download methods
  getSecureDownloadLink: async (documentType: string, documentId: number): Promise<{ download_url: string, filename: string }> => {
    try {
      // Determine the correct endpoint based on document type
      let endpoint = '';
      switch(documentType) {
        case 'report':
          endpoint = `${API_ENDPOINTS.DOCUMENTS.SECURE_DOWNLOAD.REPORT(documentId)}`;
          break;
        case 'tender':
          endpoint = `${API_ENDPOINTS.DOCUMENTS.SECURE_DOWNLOAD.TENDER(documentId)}`;
          break;
        case 'offer':
          endpoint = `${API_ENDPOINTS.DOCUMENTS.SECURE_DOWNLOAD.OFFER(documentId)}`;
          break;
        default:
          throw new Error(`Unsupported document type: ${documentType}`);
      }
      
      // Make the request to get the secure download link
      const response = await fetch(endpoint, {
        method: 'GET',
        headers: getAuthHeaders()
      });
      
      // Check if the response is HTML (possible auth issue)
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response. Your session may have expired.');
      }
      
      if (!response.ok) {
        throw new Error(`Failed to get secure download link: ${response.status}`);
      }
      
      // Parse the response to get the download URL
      const data = await response.json();
      return {
        download_url: data.download_url,
        filename: data.report_filename || data.filename || `${documentType}-${documentId}`
      };
    } catch (error) {
      console.error(`Error getting secure download link for ${documentType} ${documentId}:`, error);
      throw error;
    }
  },
  
  // Download document using secure link
  downloadWithSecureLink: async (documentType: 'report' | 'tender' | 'offer', documentId: number): Promise<boolean> => {
    try {
      console.log(`Starting secure download for ${documentType} ${documentId}`);
      
      // Get the secure download URL
      const { download_url, filename } = await documentApi.getSecureDownloadLink(documentType, documentId);
      console.log("Received secure download URL:", download_url);
      
      // Create an anchor element to trigger the download
      const a = document.createElement('a');
      a.href = download_url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      setTimeout(() => {
        document.body.removeChild(a);
      }, 100);
      
      return true;
    } catch (error) {
      console.error(`Error downloading ${documentType} ${documentId}:`, error);
      throw error;
    }
  }
};