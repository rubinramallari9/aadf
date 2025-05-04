// client/src/api/config.ts
// Base API URL configuration

export const API_BASE_URL = 'http://localhost:8000';

// API endpoint paths
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: `${API_BASE_URL}/api/auth/login/`,
    LOGOUT: `${API_BASE_URL}/api/auth/logout/`,
    REGISTER: `${API_BASE_URL}/api/auth/register/`,
    CHANGE_PASSWORD: `${API_BASE_URL}/api/auth/change-password/`,
    PROFILE: `${API_BASE_URL}/api/auth/profile/`,
    ADMIN_CREATE_USER: `${API_BASE_URL}/api/auth/admin-create-user/`,
    REFRESH_TOKEN: `${API_BASE_URL}/api/auth/refresh-token/`, // Add this if your backend supports token refresh
  },
  TENDERS: {
    BASE: `${API_BASE_URL}/api/tenders/`,
    DETAIL: (id: number) => `${API_BASE_URL}/api/tenders/${id}/`,
    SEARCH: `${API_BASE_URL}/api/tenders/search/`,
    PUBLISH: (id: number) => `${API_BASE_URL}/api/tenders/${id}/publish/`,
    CLOSE: (id: number) => `${API_BASE_URL}/api/tenders/${id}/close/`,
    AWARD: (id: number) => `${API_BASE_URL}/api/tenders/${id}/award/`,
    STATISTICS: (id: number) => `${API_BASE_URL}/api/tenders/${id}/statistics/`,
    EXPORT_REPORT: (id: number) => `${API_BASE_URL}/api/tenders/${id}/export_report/`,
    EXPORT_CSV: (id: number) => `${API_BASE_URL}/api/tenders/${id}/export_csv/`,
    ADD_REQUIREMENT: (id: number) => `${API_BASE_URL}/api/tenders/${id}/add_requirement/`,
    ADD_EVALUATION_CRITERIA: (id: number) => `${API_BASE_URL}/api/tenders/${id}/add_evaluation_criteria/`,
  },
  OFFERS: {
    BASE: `${API_BASE_URL}/api/offers/`,
    DETAIL: (id: number) => `${API_BASE_URL}/api/offers/${id}/`,
    BY_TENDER: (tenderId: number) => `${API_BASE_URL}/api/offers/?tender_id=${tenderId}`,
    SUBMIT: (id: number) => `${API_BASE_URL}/api/offers/${id}/submit/`,
    EVALUATE: (id: number) => `${API_BASE_URL}/api/offers/${id}/evaluate/`,
    DOCUMENTS: (id: number) => `${API_BASE_URL}/api/offers/${id}/documents/`,
  },
  DOCUMENTS: {
    TENDER: {
      BASE: `${API_BASE_URL}/api/tender-documents/`,
      DETAIL: (id: number) => `${API_BASE_URL}/api/tender-documents/${id}/`,
      BY_TENDER: (tenderId: number) => `${API_BASE_URL}/api/tender-documents/?tender_id=${tenderId}`,
    },
    OFFER: {
      BASE: `${API_BASE_URL}/api/offer-documents/`,
      DETAIL: (id: number) => `${API_BASE_URL}/api/offer-documents/${id}/`,
      BY_OFFER: (offerId: number) => `${API_BASE_URL}/api/offer-documents/?offer_id=${offerId}`,
    },
    DOWNLOAD: (documentType: string, documentId: number) => 
      `${API_BASE_URL}/api/download/${documentType}/${documentId}/`,
    SECURE_DOWNLOAD: {
      REPORT: (id: number) => `${API_BASE_URL}/api/reports/${id}/secure-download-link/`,
      TENDER: (id: number) => `${API_BASE_URL}/api/tender-documents/${id}/secure-download-link/`,
      OFFER: (id: number) => `${API_BASE_URL}/api/offer-documents/${id}/secure-download-link/`
    }
  },
  EVALUATIONS: {
    BASE: `${API_BASE_URL}/api/evaluations/`,
    DETAIL: (id: number) => `${API_BASE_URL}/api/evaluations/${id}/`,
    SUMMARY: `${API_BASE_URL}/api/evaluations/summary/`,
    PENDING_TASKS: `${API_BASE_URL}/api/evaluations/pending_tasks/`,
    SUGGEST_SCORE: `${API_BASE_URL}/api/evaluations/suggest_score/`,
    BULK_EVALUATE: `${API_BASE_URL}/api/evaluations/bulk_evaluate/`,
    MY_EVALUATIONS: `${API_BASE_URL}/api/evaluations/my_evaluations/`,
    PERFORMANCE: `${API_BASE_URL}/api/evaluations/evaluator_performance/`,
    SCORE_DISTRIBUTION: `${API_BASE_URL}/api/evaluations/score_distribution/`,
    EXPORT: `${API_BASE_URL}/api/evaluations/export_evaluations/`,
    HISTORY: `${API_BASE_URL}/api/evaluations/evaluation_history/`,
    STATISTICS: `${API_BASE_URL}/api/evaluations/statistics/`,
  },
  
  EVALUATION_CRITERIA: {
    BASE: `${API_BASE_URL}/api/evaluation-criteria/`,
    DETAIL: (id: number) => `${API_BASE_URL}/api/evaluation-criteria/${id}/`,
    BY_TENDER: (tenderId: number) => `${API_BASE_URL}/api/evaluation-criteria/?tender_id=${tenderId}`,
    BULK_CREATE: `${API_BASE_URL}/api/evaluation-criteria/bulk_create/`,
    TEMPLATE: `${API_BASE_URL}/api/evaluation-criteria/template/`,
    COPY_FROM_TENDER: `${API_BASE_URL}/api/evaluation-criteria/copy_from_tender/`,
    STATISTICS: `${API_BASE_URL}/api/evaluation-criteria/statistics/`,
  },
  VENDORS: {
    BASE: `${API_BASE_URL}/api/vendor-companies/`,
    DETAIL: (id: number) => `${API_BASE_URL}/api/vendor-companies/${id}/`,
    ASSIGN_USER: (id: number) => `${API_BASE_URL}/api/vendor-companies/${id}/assign_user/`,
    REMOVE_USER: (id: number) => `${API_BASE_URL}/api/vendor-companies/${id}/remove_user/`,
    STATISTICS: (id: number) => `${API_BASE_URL}/api/vendor-companies/${id}/statistics/`,
  },
  APPROVALS: {
    BASE: `${API_BASE_URL}/api/approvals/`,
    DETAIL: (id: number) => `${API_BASE_URL}/api/approvals/${id}/`,
    BY_TENDER: (tenderId: number) => `${API_BASE_URL}/api/approvals/?tender_id=${tenderId}`,
    APPROVE: (id: number) => `${API_BASE_URL}/api/approvals/${id}/approve/`,
    REJECT: (id: number) => `${API_BASE_URL}/api/approvals/${id}/reject/`,
  },
  REPORTS: {
    BASE: `${API_BASE_URL}/api/reports/`,
    DETAIL: (id: number) => `${API_BASE_URL}/api/reports/${id}/`,
    GENERATE: `${API_BASE_URL}/api/reports/generate_tender_report/`,
    DOWNLOAD: (id: number) => `${API_BASE_URL}/api/reports/${id}/download/`,
    REPORT_TYPES: `${API_BASE_URL}/api/reports/report_types/`,
    GENERATE_COMPARATIVE: `${API_BASE_URL}/api/reports/generate_comparative_report/`,
    GENERATE_VENDOR: `${API_BASE_URL}/api/reports/generate_vendor_report/`,
    GENERATE_ARCHIVE: `${API_BASE_URL}/api/reports/generate_archive/`
  },
  NOTIFICATIONS: {
    BASE: `${API_BASE_URL}/api/notifications/`,
    DETAIL: (id: number) => `${API_BASE_URL}/api/notifications/${id}/`,
    MARK_AS_READ: (id: number) => `${API_BASE_URL}/api/notifications/${id}/mark_as_read/`,
    MARK_ALL_AS_READ: `${API_BASE_URL}/api/notifications/mark_all_as_read/`,
    UNREAD_COUNT: `${API_BASE_URL}/api/notifications/unread_count/`,
  },
  DASHBOARD: {
    BASE: `${API_BASE_URL}/api/dashboard/`,
  },
  USERS: {
    BASE: `${API_BASE_URL}/api/users/`,
    DETAIL: (id: number) => `${API_BASE_URL}/api/users/${id}/`,
    RESET_PASSWORD: (id: number) => `${API_BASE_URL}/api/users/${id}/reset-password/`,
  },
};

// HTTP request headers with token checking
export const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  
  // Check if token exists
  if (!token) {
    console.warn('No authentication token found');
  }
  
  return {
    'Content-Type': 'application/json',
    'Authorization': token ? `Token ${token}` : '',
  };
};

// For file uploads (multipart/form-data)
export const getMultipartHeaders = () => {
  const token = localStorage.getItem('token');
  
  // Check if token exists
  if (!token) {
    console.warn('No authentication token found for file upload');
  }
  
  return {
    'Authorization': token ? `Token ${token}` : '',
  };
};