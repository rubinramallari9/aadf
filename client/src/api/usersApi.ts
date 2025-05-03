// client/src/api/usersApi.ts
import { API_ENDPOINTS, getAuthHeaders } from './config';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
  is_active: boolean;
  date_joined: string;
}

export interface UserFormData {
  username: string;
  email: string;
  password?: string;
  first_name?: string;
  last_name?: string;
  role: string;
  is_active: boolean;
}

export const usersApi = {
  // Get all users
  getAll: async (params = {}) => {
    const queryString = new URLSearchParams(params as Record<string, string>).toString();
    const url = queryString ? `${API_ENDPOINTS.USERS.BASE}?${queryString}` : API_ENDPOINTS.USERS.BASE;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get users');
    }
    
    return response.json();
  },

  // Get user by ID
  getById: async (id: number) => {
    const response = await fetch(API_ENDPOINTS.USERS.DETAIL(id), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get user');
    }
    
    return response.json();
  },

  // Create a new user
  create: async (data: UserFormData) => {
    const response = await fetch(API_ENDPOINTS.USERS.BASE, {
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

  // Update an existing user
  update: async (id: number, data: Partial<UserFormData>) => {
    const response = await fetch(API_ENDPOINTS.USERS.DETAIL(id), {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to update user');
    }
    
    return response.json();
  },

  // Reset a user's password
  resetPassword: async (id: number, newPassword: string) => {
    const response = await fetch(API_ENDPOINTS.USERS.RESET_PASSWORD(id), {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ new_password: newPassword }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to reset password');
    }
    
    return response.json();
  },

  // Deactivate a user
  deactivate: async (id: number) => {
    return await usersApi.update(id, { is_active: false });
  },

  // Activate a user
  activate: async (id: number) => {
    return await usersApi.update(id, { is_active: true });
  },

  // Get users by role
  getByRole: async (role: string) => {
    return await usersApi.getAll({ role });
  },

  // Search users
  search: async (query: string) => {
    return await usersApi.getAll({ search: query });
  }
};