// client/src/contexts/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi } from '../api/api';

// Define types
interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: any) => Promise<void>;
  updateProfile: (data: any) => Promise<void>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
  refreshToken: () => Promise<boolean>;
  checkTokenValidity: () => boolean;
}

// Create the context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Function to check if a token is expired (if it's a JWT)
const isTokenExpired = (token: string): boolean => {
  try {
    // For JWT tokens
    if (token.split('.').length === 3) {
      const payload = JSON.parse(atob(token.split('.')[1]));
      // Check if token has exp claim
      if (payload.exp) {
        // Convert exp to milliseconds and compare with current time
        return Date.now() >= payload.exp * 1000;
      }
    }
    // If we can't determine, let's assume it's not expired
    return false;
  } catch (error) {
    console.error('Error checking token expiration:', error);
    // If parsing fails, assume token is invalid/expired
    return true;
  }
};

// Create a provider component
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastTokenRefresh, setLastTokenRefresh] = useState<number>(0);
  
  // Minimum time between token refresh attempts in milliseconds (5 minutes)
  const MIN_REFRESH_INTERVAL = 5 * 60 * 1000;

  // Check if the user is authenticated
  const isAuthenticated = !!token && !!user;
  
  // Check token validity
  const checkTokenValidity = (): boolean => {
    if (!token) return false;
    return !isTokenExpired(token);
  };
  
  // Refresh token function
  const refreshToken = async (): Promise<boolean> => {
    // Don't attempt refresh if we just did it recently
    if (Date.now() - lastTokenRefresh < MIN_REFRESH_INTERVAL) {
      return false;
    }
    
    try {
      // This is a placeholder - implement actual token refresh with your backend
      // const response = await authApi.refreshToken();
      // const newToken = response.token;
      
      // For now, just try to get the profile to check if token is still valid
      const userData = await authApi.getProfile();
      
      // If we got user data, the token is still valid
      if (userData) {
        setUser(userData);
        setLastTokenRefresh(Date.now());
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  };

  // Load user from token on initial render
  useEffect(() => {
    const loadUser = async () => {
      if (token) {
        try {
          // Check if token is expired (for JWT tokens)
          if (isTokenExpired(token)) {
            const refreshed = await refreshToken();
            if (!refreshed) {
              throw new Error('Token expired and refresh failed');
            }
          }
          
          const userData = await authApi.getProfile();
          setUser(userData);
        } catch (error) {
          console.error('Failed to load user:', error);
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
        } finally {
          setIsLoading(false);
        }
      } else {
        setIsLoading(false);
      }
    };

    loadUser();
  }, [token]);

  // Login function
  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await authApi.login({ username, password });
      localStorage.setItem('token', response.token);
      setToken(response.token);
      setLastTokenRefresh(Date.now());
      setUser({
        id: response.user_id,
        username: response.username,
        email: response.email,
        first_name: response.first_name,
        last_name: response.last_name,
        role: response.role,
      });
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    setIsLoading(true);
    try {
      if (token) {
        await authApi.logout();
      }
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
      setLastTokenRefresh(0);
      setIsLoading(false);
    }
  };

  // Register function
  const register = async (data: any) => {
    setIsLoading(true);
    try {
      const response = await authApi.register(data);
      localStorage.setItem('token', response.token);
      setToken(response.token);
      setLastTokenRefresh(Date.now());
      setUser(response.user);
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Update profile function
  const updateProfile = async (data: any) => {
    setIsLoading(true);
    try {
      const updatedUser = await authApi.updateProfile(data);
      setUser(updatedUser);
    } catch (error) {
      console.error('Profile update failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Change password function
  const changePassword = async (oldPassword: string, newPassword: string) => {
    setIsLoading(true);
    try {
      const response = await authApi.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
      });
      
      // Update token if it was refreshed
      if (response.token) {
        localStorage.setItem('token', response.token);
        setToken(response.token);
        setLastTokenRefresh(Date.now());
      }
    } catch (error) {
      console.error('Password change failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Provide the context value
  const contextValue: AuthContextType = {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    logout,
    register,
    updateProfile,
    changePassword,
    refreshToken,
    checkTokenValidity
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Create a custom hook to use the auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};