// client/src/api/documentApi.ts
import { API_ENDPOINTS, getAuthHeaders, getMultipartHeaders } from './config';

// Document type interfaces
export interface Document {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  document_type: string;
  created_at: string;
}

export interface SecureDownloadLinkResponse {
  download_url: string;
  expires_at: string;
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

// Helper function to refresh token if needed (stub - implement based on your auth system)
const refreshAuthToken = async (): Promise<boolean> => {
  // This is a placeholder - implement your actual token refresh logic
  // For example, you might want to call your auth service's refresh endpoint
  try {
    // Example:
    // const response = await fetch(API_ENDPOINTS.AUTH.REFRESH_TOKEN, {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ refresh_token: localStorage.getItem('refreshToken') })
    // });
    // if (response.ok) {
    //   const data = await response.json();
    //   localStorage.setItem('token', data.token);
    //   return true;
    // }
    
    // For now, just returning false since this is a stub
    return false;
  } catch (error) {
    console.error('Token refresh failed:', error);
    return false;
  }
};

// Document API methods
export const documentApi = {
  // Secure download link methods
  getSecureDownloadLink: async (documentType: string, documentId: number, expiresInMinutes = 60): Promise<SecureDownloadLinkResponse> => {
    let endpoint;
    
    switch(documentType) {
      case 'report':
        endpoint = API_ENDPOINTS.DOCUMENTS.SECURE_DOWNLOAD.REPORT(documentId);
        break;
      case 'tender':
        endpoint = API_ENDPOINTS.DOCUMENTS.SECURE_DOWNLOAD.TENDER(documentId);
        break;
      case 'offer':
        endpoint = API_ENDPOINTS.DOCUMENTS.SECURE_DOWNLOAD.OFFER(documentId);
        break;
      default:
        throw new Error(`Unsupported document type: ${documentType}`);
    }
    
    // Add expiration parameter if provided
    if (expiresInMinutes !== 60) {
      endpoint += `?expires_in=${expiresInMinutes}`;
    }
    
    try {
      console.log(`Getting secure download link for ${documentType} document ID: ${documentId}`);
      
      const response = await fetch(endpoint, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      // Check if the response is HTML (usually means auth issue)
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response instead of JSON. You may need to log in again.');
      }
      
      // Handle authentication failure
      if (response.status === 401) {
        console.log('Authentication failed, attempting to refresh token...');
        
        // Try to refresh the token
        const refreshed = await refreshAuthToken();
        
        if (refreshed) {
          // Retry the request with the new token
          const retryResponse = await fetch(endpoint, {
            method: 'GET',
            headers: getAuthHeaders(),
          });
          
          if (!retryResponse.ok) {
            throw new Error('Failed to get secure download link even after token refresh');
          }
          
          return retryResponse.json();
        } else {
          throw new Error('Authentication failed and token refresh was unsuccessful');
        }
      }
      
      if (!response.ok) {
        // Try to get error details from the response
        try {
          const errorData = await response.json();
          throw new Error(errorData.error || `Failed to get secure download link: ${response.status} ${response.statusText}`);
        } catch (jsonError) {
          throw new Error(`Failed to get secure download link: ${response.status} ${response.statusText}`);
        }
      }
      
      const data = await response.json();
      console.log('Received secure download link:', data);
      return data;
    } catch (error) {
      console.error('Error getting secure download link:', error);
      throw error;
    }
  },
  
  downloadWithSecureLink: async (documentType: string, documentId: number): Promise<boolean> => {
    try {
      console.log(`Downloading ${documentType} document ID: ${documentId} with secure link`);
      
      // Get a secure link
      const linkData = await documentApi.getSecureDownloadLink(documentType, documentId);
      
      if (!linkData || !linkData.download_url) {
        throw new Error('Invalid download URL received');
      }
      
      // Use the secure link to download the file
      window.open(linkData.download_url, '_blank');
      
      return true;
    } catch (error) {
      console.error('Error downloading document:', error);
      throw error;
    }
  },
  
  // Tender documents
  uploadTenderDocument: async (tenderId: number, file: File): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('tender_id', tenderId.toString());
    
    try {
      const response = await fetch(API_ENDPOINTS.DOCUMENTS.TENDER.BASE, {
        method: 'POST',
        headers: getMultipartHeaders(),
        body: formData,
      });
      
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response instead of JSON. You may need to log in again.');
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to upload document');
      }
      
      return response.json();
    } catch (error) {
      console.error('Error uploading tender document:', error);
      throw error;
    }
  },
  
  getTenderDocuments: async (tenderId: number): Promise<Document[]> => {
    try {
      const response = await fetch(API_ENDPOINTS.DOCUMENTS.TENDER.BY_TENDER(tenderId), {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response instead of JSON. You may need to log in again.');
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get tender documents');
      }
      
      return response.json();
    } catch (error) {
      console.error('Error getting tender documents:', error);
      throw error;
    }
  },
  
  deleteTenderDocument: async (id: number): Promise<boolean> => {
    try {
      const response = await fetch(API_ENDPOINTS.DOCUMENTS.TENDER.DETAIL(id), {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response instead of JSON. You may need to log in again.');
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete document');
      }
      
      return response.ok;
    } catch (error) {
      console.error('Error deleting tender document:', error);
      throw error;
    }
  },
  
  // Offer documents
  uploadOfferDocument: async (offerId: number, file: File, documentType?: string): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('offer_id', offerId.toString());
    if (documentType) {
      formData.append('document_type', documentType);
    }
    
    try {
      const response = await fetch(API_ENDPOINTS.DOCUMENTS.OFFER.BASE, {
        method: 'POST',
        headers: getMultipartHeaders(),
        body: formData,
      });
      
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response instead of JSON. You may need to log in again.');
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to upload document');
      }
      
      return response.json();
    } catch (error) {
      console.error('Error uploading offer document:', error);
      throw error;
    }
  },
  
  getOfferDocuments: async (offerId: number): Promise<Document[]> => {
    try {
      const response = await fetch(API_ENDPOINTS.DOCUMENTS.OFFER.BY_OFFER(offerId), {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response instead of JSON. You may need to log in again.');
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get offer documents');
      }
      
      return response.json();
    } catch (error) {
      console.error('Error getting offer documents:', error);
      throw error;
    }
  },
  
  deleteOfferDocument: async (id: number): Promise<boolean> => {
    try {
      const response = await fetch(API_ENDPOINTS.DOCUMENTS.OFFER.DETAIL(id), {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      
      if (await isHtmlResponse(response)) {
        throw new Error('Received HTML response instead of JSON. You may need to log in again.');
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete document');
      }
      
      return response.ok;
    } catch (error) {
      console.error('Error deleting offer document:', error);
      throw error;
    }
  },
  
  // Legacy download method (to be replaced with secure downloads)
  getDocumentDownloadUrl: (documentType: string, documentId: number): string => {
    const token = localStorage.getItem('token');
    return `${API_ENDPOINTS.DOCUMENTS.DOWNLOAD(documentType, documentId)}?token=${token}`;
  }
};

export default documentApi;