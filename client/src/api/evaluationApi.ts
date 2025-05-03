// client/src/api/evaluationApi.ts
import { API_ENDPOINTS, getAuthHeaders } from './config';

export interface EvaluationCriteria {
  id: number;
  name: string;
  description?: string;
  weight: number;
  max_score: number;
  category: string;
  tender: number;
  created_at: string;
}

export interface Evaluation {
  id: number;
  offer: number;
  evaluator: number;
  evaluator_username: string;
  criteria: number;
  criteria_name: string;
  criteria_category: string;
  score: number;
  comment?: string;
  created_at: string;
  updated_at: string;
}

export interface EvaluationFormData {
  offer_id: number;
  criteria_id: number;
  score: number;
  comment?: string;
}

export interface EvaluationSuggestion {
  suggested_score: number;
  confidence: number;
  max_score: number;
  criteria_name: string;
  criteria_category: string;
}

export interface PendingTask {
  tender_id: number;
  tender_reference: string;
  offer_id: number;
  vendor_name: string;
  pending_criteria: Array<{
    category: string;
    criteria: Array<{
      id: number;
      name: string;
      weight: number;
      max_score: number;
    }>;
  }>;
  total_pending: number;
  total_criteria: number;
  progress: number;
  deadline: {
    date: string;
    days_remaining: number;
    is_overdue: boolean;
  };
}

export interface EvaluationSummary {
  tender_id: number;
  tender_reference: string;
  tender_title: string;
  tender_status: string;
  total_offers: number;
  total_evaluations: number;
  evaluators: Array<{
    evaluator__username: string;
    count: number;
  }>;
  avg_score: number;
  max_score: number;
  min_score: number;
  avg_scores_by_criteria: Array<{
    criteria__name: string;
    criteria__category: string;
    avg: number;
  }>;
  evaluation_status: {
    completed: number;
    total: number;
    percentage: number;
    evaluator_progress: Array<{
      evaluator_id: number;
      evaluator_name: string;
      completed: number;
      total: number;
      percentage: number;
    }>;
  };
  offers_summary: Array<{
    offer_id: number;
    vendor_name: string;
    price: number;
    technical_score: number;
    financial_score: number;
    total_score: number;
    status: string;
    evaluation_count: number;
    evaluation_progress: {
      completed: number;
      total: number;
      percentage: number;
    };
    avg_score: number;
    criteria_scores: Array<{
      criteria__name: string;
      criteria__category: string;
      avg_score: number;
    }>;
  }>;
  consistency_analysis?: Array<{
    offer_id: number;
    vendor_name: string;
    criteria_id: number;
    criteria_name: string;
    variance: number;
    scores: number[];
  }>;
}

export const evaluationApi = {
  // Get all evaluations
  getAll: async (params = {}) => {
    const queryString = new URLSearchParams(params as Record<string, string>).toString();
    const url = queryString ? `${API_ENDPOINTS.EVALUATIONS.BASE}?${queryString}` : API_ENDPOINTS.EVALUATIONS.BASE;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get evaluations');
    }
    
    return response.json();
  },

  // Get evaluation by ID
  getById: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.DETAIL(id), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get evaluation');
    }
    
    return response.json();
  },

  // Create evaluation
  create: async (data: EvaluationFormData) => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.BASE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to create evaluation');
    }
    
    return response.json();
  },

  // Update evaluation
  update: async (id: number, data: Partial<EvaluationFormData>) => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.DETAIL(id), {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to update evaluation');
    }
    
    return response.json();
  },

  // Get evaluation summary for a tender
  getSummary: async (tenderId: number) => {
    const response = await fetch(`${API_ENDPOINTS.EVALUATIONS.SUMMARY}?tender_id=${tenderId}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get evaluation summary');
    }
    
    return response.json() as Promise<EvaluationSummary>;
  },

  // Get pending evaluation tasks
  getPendingTasks: async () => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.PENDING_TASKS, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get pending tasks');
    }
    
    return response.json();
  },

  // Get AI suggestion for evaluation
  getSuggestion: async (offerId: number, criteriaId: number) => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.SUGGEST_SCORE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        offer_id: offerId,
        criteria_id: criteriaId
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get AI suggestion');
    }
    
    return response.json() as Promise<EvaluationSuggestion>;
  },

  // Bulk evaluate
  bulkEvaluate: async (evaluations: EvaluationFormData[]) => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.BULK_EVALUATE, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ evaluations }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to save evaluations');
    }
    
    return response.json();
  },

  // Get evaluator's own evaluations
  getMyEvaluations: async () => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.MY_EVALUATIONS, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get my evaluations');
    }
    
    return response.json();
  },

  // Get evaluator performance metrics
  getPerformance: async () => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.PERFORMANCE, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get performance metrics');
    }
    
    return response.json();
  },

  // Get score distribution
  getScoreDistribution: async (params = {}) => {
    const queryString = new URLSearchParams(params as Record<string, string>).toString();
    const url = queryString 
      ? `${API_ENDPOINTS.EVALUATIONS.SCORE_DISTRIBUTION}?${queryString}` 
      : API_ENDPOINTS.EVALUATIONS.SCORE_DISTRIBUTION;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get score distribution');
    }
    
    return response.json();
  },

  // Export evaluations to CSV
  exportEvaluations: async (params = {}) => {
    const queryString = new URLSearchParams(params as Record<string, string>).toString();
    const url = queryString 
      ? `${API_ENDPOINTS.EVALUATIONS.EXPORT}?${queryString}` 
      : API_ENDPOINTS.EVALUATIONS.EXPORT;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to export evaluations');
    }
    
    // Create blob from response for file download
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = 'evaluations_export.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
    
    return true;
  },

  // Get evaluation history
  getHistory: async () => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.HISTORY, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get evaluation history');
    }
    
    return response.json();
  },

  // Get evaluator statistics
  getStatistics: async () => {
    const response = await fetch(API_ENDPOINTS.EVALUATIONS.STATISTICS, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get evaluation statistics');
    }
    
    return response.json();
  },

  // Criteria management
  criteria: {
    getAll: async (params = {}) => {
      const queryString = new URLSearchParams(params as Record<string, string>).toString();
      const url = queryString 
        ? `${API_ENDPOINTS.EVALUATION_CRITERIA.BASE}?${queryString}` 
        : API_ENDPOINTS.EVALUATION_CRITERIA.BASE;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get evaluation criteria');
      }
      
      return response.json();
    },

    getById: async (id: number) => {
      const response = await fetch(API_ENDPOINTS.EVALUATION_CRITERIA.DETAIL(id), {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get evaluation criteria');
      }
      
      return response.json();
    },

    getByTender: async (tenderId: number) => {
      const response = await fetch(API_ENDPOINTS.EVALUATION_CRITERIA.BY_TENDER(tenderId), {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get tender criteria');
      }
      
      return response.json();
    },

    create: async (data: any) => {
      const response = await fetch(API_ENDPOINTS.EVALUATION_CRITERIA.BASE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create evaluation criteria');
      }
      
      return response.json();
    },

    update: async (id: number, data: any) => {
      const response = await fetch(API_ENDPOINTS.EVALUATION_CRITERIA.DETAIL(id), {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update evaluation criteria');
      }
      
      return response.json();
    },

    delete: async (id: number) => {
      const response = await fetch(API_ENDPOINTS.EVALUATION_CRITERIA.DETAIL(id), {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete evaluation criteria');
      }
      
      return response.ok;
    },

    bulkCreate: async (data: any) => {
      const response = await fetch(API_ENDPOINTS.EVALUATION_CRITERIA.BULK_CREATE, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to bulk create criteria');
      }
      
      return response.json();
    },

    getTemplate: async (category?: string) => {
      const url = category 
        ? `${API_ENDPOINTS.EVALUATION_CRITERIA.TEMPLATE}?category=${category}`
        : API_ENDPOINTS.EVALUATION_CRITERIA.TEMPLATE;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get criteria template');
      }
      
      return response.json();
    },

    copyFromTender: async (sourceTenderId: number, targetTenderId: number) => {
      const response = await fetch(API_ENDPOINTS.EVALUATION_CRITERIA.COPY_FROM_TENDER, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          source_tender_id: sourceTenderId,
          target_tender_id: targetTenderId
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to copy criteria');
      }
      
      return response.json();
    },

    getStatistics: async () => {
      const response = await fetch(API_ENDPOINTS.EVALUATION_CRITERIA.STATISTICS, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get criteria statistics');
      }
      
      return response.json();
    },
  },
};