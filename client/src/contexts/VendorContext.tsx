// client/src/contexts/VendorContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/api';
import { useAuth } from './AuthContext';

// Define interface for VendorCompany
interface VendorCompany {
  id: number;
  name: string;
  registration_number: string;
  email: string;
  phone: string;
  address: string;
  created_at: string;
  updated_at: string;
}

// Define interface for User
interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
}

// Define the context interface
interface VendorContextType {
  vendors: VendorCompany[];
  loading: boolean;
  error: string | null;
  fetchVendors: () => Promise<void>;
  getVendorById: (vendorId: number) => Promise<VendorCompany>;
  fetchVendorStatistics: (vendorId: number) => Promise<any>;
  assignUser: (vendorId: number, userId: number) => Promise<void>;
  removeUser: (vendorId: number, userId: number) => Promise<void>;
  users: User[];
  fetchUsers: (role?: string) => Promise<void>;
  currentVendor: VendorCompany | null;
}

// Create the context with a default value
const VendorContext = createContext<VendorContextType>({
  vendors: [],
  loading: false,
  error: null,
  fetchVendors: async () => {},
  getVendorById: async () => ({} as VendorCompany),
  fetchVendorStatistics: async () => ({}),
  assignUser: async () => {},
  removeUser: async () => {},
  users: [],
  fetchUsers: async () => {},
  currentVendor: null,
});

// Export the hook to use this context
export const useVendor = () => useContext(VendorContext);

// Create the provider component
export const VendorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [vendors, setVendors] = useState<VendorCompany[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentVendor, setCurrentVendor] = useState<VendorCompany | null>(null);
  const { user } = useAuth();

  // Fetch vendors on initial load
  useEffect(() => {
    if (user) {
      fetchVendors();
      
      // If user is a vendor, try to load their associated company
      if (user.role === 'vendor') {
        fetchCurrentVendor();
      }
    }
  }, [user]);

  // Fetch the current vendor company for the logged-in vendor user
  const fetchCurrentVendor = async () => {
    try {
      setLoading(true);
      const response = await api.vendor.getAll();
      
      // Handle different response structures
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
      
      // Find the vendor company that this user belongs to
      const userVendor = vendorsData.find((vendor: any) => 
        vendor.users && vendor.users.some((u: any) => u.id === user?.id)
      );
      
      if (userVendor) {
        setCurrentVendor(userVendor);
      }
      
    } catch (err: any) {
      console.error('Error fetching current vendor:', err);
      setError(err.message || 'Failed to load current vendor');
    } finally {
      setLoading(false);
    }
  };

  // Fetch all vendors
  const fetchVendors = async () => {
    try {
      setLoading(true);
      const response = await api.vendor.getAll();
      
      // Handle different response structures
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

  // Get vendor by ID
  const getVendorById = async (vendorId: number): Promise<VendorCompany> => {
    try {
      const vendor = await api.vendor.getById(vendorId);
      return vendor;
    } catch (err: any) {
      console.error(`Error fetching vendor ${vendorId}:`, err);
      throw new Error(err.message || 'Failed to load vendor');
    }
  };

  // Fetch vendor statistics
  const fetchVendorStatistics = async (vendorId: number) => {
    try {
      const statistics = await api.vendor.getStatistics(vendorId);
      return statistics;
    } catch (err: any) {
      console.error(`Error fetching vendor statistics ${vendorId}:`, err);
      throw new Error(err.message || 'Failed to load vendor statistics');
    }
  };

  // Assign user to vendor
  const assignUser = async (vendorId: number, userId: number) => {
    try {
      await api.vendor.assignUser(vendorId, userId);
      // Refresh vendors after assignment
      fetchVendors();
    } catch (err: any) {
      console.error('Error assigning user to vendor:', err);
      throw new Error(err.message || 'Failed to assign user to vendor');
    }
  };

  // Remove user from vendor
  const removeUser = async (vendorId: number, userId: number) => {
    try {
      await api.vendor.removeUser(vendorId, userId);
      // Refresh vendors after removal
      fetchVendors();
    } catch (err: any) {
      console.error('Error removing user from vendor:', err);
      throw new Error(err.message || 'Failed to remove user from vendor');
    }
  };

  // Fetch users
  const fetchUsers = async (role?: string) => {
    try {
      const params: any = {};
      if (role) params.role = role;
      
      const response = await api.users.getAll(params);
      
      // Handle different response structures
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
    }
  };

  // Create the context value
  const value = {
    vendors,
    loading,
    error,
    fetchVendors,
    getVendorById,
    fetchVendorStatistics,
    assignUser,
    removeUser,
    users,
    fetchUsers,
    currentVendor,
  };

  return (
    <VendorContext.Provider value={value}>
      {children}
    </VendorContext.Provider>
  );
};

export default VendorContext;