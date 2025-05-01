// client/src/contexts/VendorContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '../api/api';

// Define types for vendor-related data
interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
}

interface VendorCompany {
  id: number;
  name: string;
  registration_number: string;
  email: string;
  phone: string;
  address: string;
  created_at: string;
  updated_at: string;
  users: User[];
}

interface VendorContextType {
  vendors: VendorCompany[];
  loading: boolean;
  error: string | null;
  fetchVendors: () => Promise<void>;
  getVendorById: (id: number) => Promise<VendorCompany>;
  createVendor: (data: any) => Promise<VendorCompany>;
  updateVendor: (id: number, data: any) => Promise<VendorCompany>;
  assignUser: (vendorId: number, userId: number) => Promise<any>;
  removeUser: (vendorId: number, userId: number) => Promise<any>;
  fetchVendorStatistics: (vendorId: number) => Promise<any>;
  users: User[];
  fetchUsers: (role?: string) => Promise<void>;
}

// Create the context
const VendorContext = createContext<VendorContextType | undefined>(undefined);

// Create a provider component
export const VendorProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [vendors, setVendors] = useState<VendorCompany[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Function to fetch all vendors
  const fetchVendors = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.vendor.getAll();
      
      // Handle different response formats
      let vendorsData = [];
      if (response) {
        if (Array.isArray(response)) {
          vendorsData = response;
        } else if (response.results && Array.isArray(response.results)) {
          vendorsData = response.results;
        } else if (typeof response === 'object') {
          vendorsData = Object.values(response);
        }
      }
      
      setVendors(vendorsData);
    } catch (err: any) {
      console.error('Error fetching vendors:', err);
      setError(err.message || 'Failed to load vendors');
    } finally {
      setLoading(false);
    }
  };

  // Function to get a vendor by ID
  const getVendorById = async (id: number): Promise<VendorCompany> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.vendor.getById(id);
      return response;
    } catch (err: any) {
      console.error('Error fetching vendor:', err);
      setError(err.message || 'Failed to load vendor');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Function to create a new vendor
  const createVendor = async (data: any): Promise<VendorCompany> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.vendor.create(data);
      
      // Update the vendors list
      setVendors(prevVendors => [...prevVendors, response]);
      
      return response;
    } catch (err: any) {
      console.error('Error creating vendor:', err);
      setError(err.message || 'Failed to create vendor');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Function to update a vendor
  const updateVendor = async (id: number, data: any): Promise<VendorCompany> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.vendor.update(id, data);
      
      // Update the vendors list
      setVendors(prevVendors => 
        prevVendors.map(vendor => 
          vendor.id === id ? response : vendor
        )
      );
      
      return response;
    } catch (err: any) {
      console.error('Error updating vendor:', err);
      setError(err.message || 'Failed to update vendor');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Function to assign a user to a vendor
  const assignUser = async (vendorId: number, userId: number) => {
    try {
      setLoading(true);
      setError(null);
      return await api.vendor.assignUser(vendorId, userId);
    } catch (err: any) {
      console.error('Error assigning user to vendor:', err);
      setError(err.message || 'Failed to assign user to vendor');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Function to remove a user from a vendor
  const removeUser = async (vendorId: number, userId: number) => {
    try {
      setLoading(true);
      setError(null);
      return await api.vendor.removeUser(vendorId, userId);
    } catch (err: any) {
      console.error('Error removing user from vendor:', err);
      setError(err.message || 'Failed to remove user from vendor');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Function to fetch vendor statistics
  const fetchVendorStatistics = async (vendorId: number) => {
    try {
      setLoading(true);
      setError(null);
      return await api.vendor.getStatistics(vendorId);
    } catch (err: any) {
      console.error('Error fetching vendor statistics:', err);
      setError(err.message || 'Failed to fetch vendor statistics');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Function to fetch users with optional role filter
  const fetchUsers = async (role?: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // Prepare query parameters
      const params: any = {};
      if (role) {
        params.role = role;
      }
      
      const response = await api.users.getAll(params);
      
      // Handle different response formats
      let usersData = [];
      if (response) {
        if (Array.isArray(response)) {
          usersData = response;
        } else if (response.results && Array.isArray(response.results)) {
          usersData = response.results;
        } else if (typeof response === 'object') {
          usersData = Object.values(response);
        }
      }
      
      setUsers(usersData);
    } catch (err: any) {
      console.error('Error fetching users:', err);
      setError(err.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  // Provide the context value
  const contextValue: VendorContextType = {
    vendors,
    loading,
    error,
    fetchVendors,
    getVendorById,
    createVendor,
    updateVendor,
    assignUser,
    removeUser,
    fetchVendorStatistics,
    users,
    fetchUsers
  };

  return (
    <VendorContext.Provider value={contextValue}>
      {children}
    </VendorContext.Provider>
  );
};

// Create a custom hook to use the vendor context
export const useVendor = () => {
  const context = useContext(VendorContext);
  if (context === undefined) {
    throw new Error('useVendor must be used within a VendorProvider');
  }
  return context;
};