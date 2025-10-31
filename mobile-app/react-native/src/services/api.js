import axios from 'axios';

// Base configuration
const API_BASE_URL = 'https://your-domain.com/api/v1'; // Update with your actual API URL
const API_TIMEOUT = 10000; // 10 seconds

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for consistent error handling
apiClient.interceptors.response.use(
  (response) => {
    return {
      success: true,
      data: response.data,
      status: response.status,
    };
  },
  (error) => {
    console.error('API Error:', error);
    
    const errorMessage = error.response?.data?.error || 
                        error.response?.data?.message || 
                        error.message || 
                        'Network error occurred';
    
    return {
      success: false,
      error: errorMessage,
      status: error.response?.status || 0,
    };
  }
);

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    // Token will be added by individual API calls when needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Helper function to add auth token
const addAuthToken = (token) => {
  return {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  };
};

// Authentication API
export const authAPI = {
  login: async (email, password) => {
    return await apiClient.post('/auth/login', { email, password });
  },

  register: async (userData) => {
    return await apiClient.post('/auth/register', userData);
  },
};

// App API
export const appAPI = {
  // Health check
  healthCheck: async () => {
    return await apiClient.get('/health');
  },

  // Configuration
  getConfig: async () => {
    return await apiClient.get('/config');
  },

  // User profile
  getUserProfile: async (token) => {
    return await apiClient.get('/users/profile', addAuthToken(token));
  },

  updateProfile: async (token, profileData) => {
    return await apiClient.put('/users/profile', profileData, addAuthToken(token));
  },

  // Work requests
  getWorkRequests: async (token) => {
    return await apiClient.get('/work-requests', addAuthToken(token));
  },

  createWorkRequest: async (token, requestData) => {
    return await apiClient.post('/work-requests', requestData, addAuthToken(token));
  },

  updateWorkRequest: async (token, requestId, updateData) => {
    return await apiClient.put(`/work-requests/${requestId}`, updateData, addAuthToken(token));
  },

  // Contractor search
  searchContractors: async (token, searchCriteria) => {
    return await apiClient.post('/contractors/search', searchCriteria, addAuthToken(token));
  },

  // Invoices
  getInvoices: async (token) => {
    return await apiClient.get('/invoices', addAuthToken(token));
  },

  // Statistics
  getUserStats: async (token) => {
    return await apiClient.get('/stats', addAuthToken(token));
  },
};

// Export API client for custom requests
export default apiClient;