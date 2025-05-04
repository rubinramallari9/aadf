// client/src/api/api.ts
// API service layer for making HTTP requests

import { API_ENDPOINTS, getAuthHeaders, getMultipartHeaders } from './config';
import { evaluationApi } from './evaluationApi';
import { reportsApi } from './reportsApi';
import { usersApi } from './usersApi';

// Types
export interface LoginData {
  username: string;
  password: string;
}

export interface UserData {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
}

export interface VendorCompanyData {
  id: number;
  name: string;
  registration_number?: string;
  email?: string;
  phone?: string;
  address?: string;
  created_at: string;
  updated_at: string;
  users?: UserData[];
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  company_name?: string;
  registration_number?: string;
  phone?: string;
  address?: string;
}

export interface ChangePasswordData {
  old_password: string;
  new_password: string;
}

// Authentication API
export const authApi = {
  login: async (data: LoginData) => {
    const response = await fetch(API_ENDPOINTS.AUTH.LOGIN, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Login failed');
    }
    
    return response.json();
  },
  
  logout: async () => {
    const response = await fetch(API_ENDPOINTS.AUTH.LOGOUT, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Logout failed');
    }
    
    return response.json();
  },
  
  register: async (data: RegisterData) => {
    const response = await fetch(API_ENDPOINTS.AUTH.REGISTER, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Registration failed');
    }
    
    return response.json();
  },
  
  // New method for admin user creation
  adminCreateUser: async (data: RegisterData) => {
    const response = await fetch(API_ENDPOINTS.AUTH.ADMIN_CREATE_USER, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to create user');
    }
    
    return response.json();
  },
  
  changePassword: async (data: ChangePasswordData) => {
    const response = await fetch(API_ENDPOINTS.AUTH.CHANGE_PASSWORD, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Password change failed');
    }
    
    return response.json();
  },
  
  getProfile: async () => {
    const response = await fetch(API_ENDPOINTS.AUTH.PROFILE, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get profile');
    }
    
    return response.json();
  },
  
  updateProfile: async (data: any) => {
    const response = await fetch(API_ENDPOINTS.AUTH.PROFILE, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to update profile');
    }
    
    return response.json();
  },
};


// Vendor API
export const vendorApi = {
  getAll: async (params = {}) => {
    const queryString = new URLSearchParams(params as Record<string, string>).toString();
    const url = queryString ? `${API_ENDPOINTS.VENDORS.BASE}?${queryString}` : API_ENDPOINTS.VENDORS.BASE;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get vendors');
    }
    
    return response.json();
  },
  
  getById: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.VENDORS.DETAIL(id), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get vendor');
    }
    
    return response.json();
  },
  
  create: async (data: any) => {
    const response = await fetch(API_ENDPOINTS.VENDORS.BASE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to create vendor');
    }
    
    return response.json();
  },
  
  update: async (id: number, data: any) => {
    const response = await fetch(API_ENDPOINTS.VENDORS.DETAIL(id), {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to update vendor');
    }
    
    return response.json();
  },
  
  delete: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.VENDORS.DETAIL(id), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to delete vendor');
    }
    
    return response.ok;
  },
  
  assignUser: async (id: number, userId: number) => {
    const response = await fetch(API_ENDPOINTS.VENDORS.ASSIGN_USER(id), {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ user_id: userId }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to assign user to vendor');
    }
    
    return response.json();
  },
  
  removeUser: async (id: number, userId: number) => {
    const response = await fetch(API_ENDPOINTS.VENDORS.REMOVE_USER(id), {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ user_id: userId }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to remove user from vendor');
    }
    
    return response.json();
  },
  
  getStatistics: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.VENDORS.STATISTICS(id), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get vendor statistics');
    }
    
    return response.json();
  },
};

// Tender API
export const tenderApi = {
  getAll: async (params = {}) => {
    const queryString = new URLSearchParams(params as Record<string, string>).toString();
    const url = queryString ? `${API_ENDPOINTS.TENDERS.BASE}?${queryString}` : API_ENDPOINTS.TENDERS.BASE;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get tenders');
    }
    
    return response.json();
  },
  
  getById: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.DETAIL(id), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get tender');
    }
    
    return response.json();
  },
  
  create: async (data: any) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.BASE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to create tender');
    }
    
    return response.json();
  },
  
  update: async (id: number, data: any) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.DETAIL(id), {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to update tender');
    }
    
    return response.json();
  },
  
  delete: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.DETAIL(id), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to delete tender');
    }
    
    return response.ok;
  },
  
  publish: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.PUBLISH(id), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to publish tender');
    }
    
    return response.json();
  },
  
  close: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.CLOSE(id), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to close tender');
    }
    
    return response.json();
  },
  
  award: async (id: number, offerId: number) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.AWARD(id), {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ offer_id: offerId }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to award tender');
    }
    
    return response.json();
  },
  
  getStatistics: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.STATISTICS(id), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get tender statistics');
    }
    
    return response.json();
  },
  
  search: async (params: any) => {
    const queryString = new URLSearchParams(params).toString();
    const url = `${API_ENDPOINTS.TENDERS.SEARCH}?${queryString}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Search failed');
    }
    
    return response.json();
  },
  
  addRequirement: async (tenderId: number, data: any) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.ADD_REQUIREMENT(tenderId), {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to add requirement');
    }
    
    return response.json();
  },
  
  addEvaluationCriteria: async (tenderId: number, data: any) => {
    const response = await fetch(API_ENDPOINTS.TENDERS.ADD_EVALUATION_CRITERIA(tenderId), {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to add evaluation criteria');
    }
    
    return response.json();
  },
};

// Offer API
export const offerApi = {
  getAll: async (params = {}) => {
    const queryString = new URLSearchParams(params as Record<string, string>).toString();
    const url = queryString ? `${API_ENDPOINTS.OFFERS.BASE}?${queryString}` : API_ENDPOINTS.OFFERS.BASE;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get offers');
    }
    
    return response.json();
  },
  
  getById: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.OFFERS.DETAIL(id), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get offer');
    }
    
    return response.json();
  },
  
  getByTender: async (tenderId: number) => {
    const response = await fetch(API_ENDPOINTS.OFFERS.BY_TENDER(tenderId), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get offers for tender');
    }
    
    return response.json();
  },
  
  create: async (data: any) => {
    const response = await fetch(API_ENDPOINTS.OFFERS.BASE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to create offer');
    }
    
    return response.json();
  },
  
  update: async (id: number, data: any) => {
    const response = await fetch(API_ENDPOINTS.OFFERS.DETAIL(id), {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to update offer');
    }
    
    return response.json();
  },
  
  delete: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.OFFERS.DETAIL(id), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to delete offer');
    }
    
    return response.ok;
  },
  
  submit: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.OFFERS.SUBMIT(id), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to submit offer');
    }
    
    return response.json();
  },
  
  evaluate: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.OFFERS.EVALUATE(id), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to evaluate offer');
    }
    
    return response.json();
  },
  
  getDocuments: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.OFFERS.DOCUMENTS(id), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get offer documents');
    }
    
    return response.json();
  },
};

// Document APIs
export const documentApi = {
  getSecureDownloadLink: async (documentType: string, documentId: number, expiresInMinutes = 60) => {
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
    
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get secure download link');
    }
    
    return response.json();
  },
  
  downloadWithSecureLink: async (documentType: string, documentId: number) => {
    try {
      // Get a secure link
      const linkData = await documentApi.getSecureDownloadLink(documentType, documentId);
      
      // Use the secure link to download the file
      window.open(linkData.download_url, '_blank');
      
      return true;
    } catch (error) {
      console.error('Error downloading document:', error);
      throw error;
    },
  },
  // Tender documents
  uploadTenderDocument: async (tenderId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('tender_id', tenderId.toString());
    
    const response = await fetch(API_ENDPOINTS.DOCUMENTS.TENDER.BASE, {
      method: 'POST',
      headers: getMultipartHeaders(),
      body: formData,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to upload document');
    }
    
    return response.json();
  },
  
  deleteTenderDocument: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.DOCUMENTS.TENDER.DETAIL(id), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to delete document');
    }
    
    return response.ok;
  },
  
  getTenderDocuments: async (tenderId: number) => {
    const response = await fetch(API_ENDPOINTS.DOCUMENTS.TENDER.BY_TENDER(tenderId), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get tender documents');
    }
    
    return response.json();
  },
  
  // Offer documents
  uploadOfferDocument: async (offerId: number, file: File, documentType?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('offer_id', offerId.toString());
    if (documentType) {
      formData.append('document_type', documentType);
    }
    
    const response = await fetch(API_ENDPOINTS.DOCUMENTS.OFFER.BASE, {
      method: 'POST',
      headers: getMultipartHeaders(),
      body: formData,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to upload document');
    }
    
    return response.json();
  },
  
  deleteOfferDocument: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.DOCUMENTS.OFFER.DETAIL(id), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to delete document');
    }
    
    return response.ok;
  },
  
  getOfferDocuments: async (offerId: number) => {
    const response = await fetch(API_ENDPOINTS.DOCUMENTS.OFFER.BY_OFFER(offerId), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get offer documents');
    }
    
    return response.json();
  },
  
  // Document download
  getDocumentDownloadUrl: (documentType: string, documentId: number) => {
    const token = localStorage.getItem('token');
    return `${API_ENDPOINTS.DOCUMENTS.DOWNLOAD(documentType, documentId)}?token=${token}`;
  },
};

// Dashboard API
export const dashboardApi = {
  getDashboardData: async () => {
    const response = await fetch(API_ENDPOINTS.DASHBOARD.BASE, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get dashboard data');
    }
    
    return response.json();
  },
};

// Notification API
export const notificationApi = {
  getAll: async () => {
    const response = await fetch(API_ENDPOINTS.NOTIFICATIONS.BASE, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get notifications');
    }
    
    return response.json();
  },
  
  markAsRead: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.NOTIFICATIONS.MARK_AS_READ(id), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to mark notification as read');
    }
    
    return response.json();
  },
  
  markAllAsRead: async () => {
    const response = await fetch(API_ENDPOINTS.NOTIFICATIONS.MARK_ALL_AS_READ, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to mark all notifications as read');
    }
    
    return response.json();
  },
  
  getUnreadCount: async () => {
    const response = await fetch(API_ENDPOINTS.NOTIFICATIONS.UNREAD_COUNT, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get unread count');
    }
    
    return response.json();
  },
};

// Export all APIs
export default {
  auth: authApi,
  tenders: tenderApi,
  offers: offerApi,
  documents: documentApi,
  dashboard: dashboardApi,
  notifications: notificationApi,
  vendor: vendorApi,
  users: usersApi,
  evaluations: evaluationApi, 
  reports: reportsApi,
};

export { evaluationApi, usersApi };