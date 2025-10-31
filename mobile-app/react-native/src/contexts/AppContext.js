import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { appAPI } from '../services/api';

// Initial state
const initialState = {
  profile: null,
  workRequests: [],
  invoices: [],
  contractors: [],
  config: null,
  stats: null,
  loading: false,
  error: null,
};

// App actions
const AppActions = {
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
  SET_PROFILE: 'SET_PROFILE',
  SET_WORK_REQUESTS: 'SET_WORK_REQUESTS',
  ADD_WORK_REQUEST: 'ADD_WORK_REQUEST',
  UPDATE_WORK_REQUEST: 'UPDATE_WORK_REQUEST',
  SET_INVOICES: 'SET_INVOICES',
  SET_CONTRACTORS: 'SET_CONTRACTORS',
  SET_CONFIG: 'SET_CONFIG',
  SET_STATS: 'SET_STATS',
};

// App reducer
const appReducer = (state, action) => {
  switch (action.type) {
    case AppActions.SET_LOADING:
      return { ...state, loading: action.payload };
    
    case AppActions.SET_ERROR:
      return { ...state, error: action.payload, loading: false };
    
    case AppActions.CLEAR_ERROR:
      return { ...state, error: null };
    
    case AppActions.SET_PROFILE:
      return { ...state, profile: action.payload };
    
    case AppActions.SET_WORK_REQUESTS:
      return { ...state, workRequests: action.payload };
    
    case AppActions.ADD_WORK_REQUEST:
      return { 
        ...state, 
        workRequests: [action.payload, ...state.workRequests] 
      };
    
    case AppActions.UPDATE_WORK_REQUEST:
      return {
        ...state,
        workRequests: state.workRequests.map(req =>
          req.id === action.payload.id ? action.payload : req
        ),
      };
    
    case AppActions.SET_INVOICES:
      return { ...state, invoices: action.payload };
    
    case AppActions.SET_CONTRACTORS:
      return { ...state, contractors: action.payload };
    
    case AppActions.SET_CONFIG:
      return { ...state, config: action.payload };
    
    case AppActions.SET_STATS:
      return { ...state, stats: action.payload };
    
    default:
      return state;
  }
};

// Create context
const AppContext = createContext();

// App provider component
export const AppProvider = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const { user, token } = useAuth();

  // Load app config when user is available
  useEffect(() => {
    if (user && token) {
      loadAppConfig();
      loadUserProfile();
      loadUserStats();
    }
  }, [user, token]);

  const loadAppConfig = async () => {
    try {
      const response = await appAPI.getConfig();
      if (response.success) {
        dispatch({ type: AppActions.SET_CONFIG, payload: response.data });
      }
    } catch (error) {
      console.error('Error loading app config:', error);
    }
  };

  const loadUserProfile = async () => {
    try {
      const response = await appAPI.getUserProfile(token);
      if (response.success) {
        dispatch({ type: AppActions.SET_PROFILE, payload: response.data });
      }
    } catch (error) {
      console.error('Error loading user profile:', error);
    }
  };

  const loadUserStats = async () => {
    try {
      const response = await appAPI.getUserStats(token);
      if (response.success) {
        dispatch({ type: AppActions.SET_STATS, payload: response.data });
      }
    } catch (error) {
      console.error('Error loading user stats:', error);
    }
  };

  const updateProfile = async (profileData) => {
    dispatch({ type: AppActions.SET_LOADING, payload: true });
    
    try {
      const response = await appAPI.updateProfile(token, profileData);
      
      if (response.success) {
        dispatch({ type: AppActions.SET_PROFILE, payload: response.data });
        dispatch({ type: AppActions.SET_LOADING, payload: false });
        return { success: true };
      } else {
        dispatch({ type: AppActions.SET_ERROR, payload: response.error });
        return { success: false, error: response.error };
      }
    } catch (error) {
      dispatch({ type: AppActions.SET_ERROR, payload: error.message });
      return { success: false, error: error.message };
    }
  };

  const loadWorkRequests = async () => {
    dispatch({ type: AppActions.SET_LOADING, payload: true });
    
    try {
      const response = await appAPI.getWorkRequests(token);
      
      if (response.success) {
        dispatch({ type: AppActions.SET_WORK_REQUESTS, payload: response.data });
        dispatch({ type: AppActions.SET_LOADING, payload: false });
      } else {
        dispatch({ type: AppActions.SET_ERROR, payload: response.error });
      }
    } catch (error) {
      dispatch({ type: AppActions.SET_ERROR, payload: error.message });
    }
  };

  const createWorkRequest = async (requestData) => {
    dispatch({ type: AppActions.SET_LOADING, payload: true });
    
    try {
      const response = await appAPI.createWorkRequest(token, requestData);
      
      if (response.success) {
        const newRequest = { ...requestData, id: response.data.id };
        dispatch({ type: AppActions.ADD_WORK_REQUEST, payload: newRequest });
        dispatch({ type: AppActions.SET_LOADING, payload: false });
        return { success: true, data: response.data };
      } else {
        dispatch({ type: AppActions.SET_ERROR, payload: response.error });
        return { success: false, error: response.error };
      }
    } catch (error) {
      dispatch({ type: AppActions.SET_ERROR, payload: error.message });
      return { success: false, error: error.message };
    }
  };

  const updateWorkRequest = async (requestId, updateData) => {
    try {
      const response = await appAPI.updateWorkRequest(token, requestId, updateData);
      
      if (response.success) {
        // Find and update the work request in state
        const updatedRequest = state.workRequests.find(req => req.id === requestId);
        if (updatedRequest) {
          const updated = { ...updatedRequest, ...updateData };
          dispatch({ type: AppActions.UPDATE_WORK_REQUEST, payload: updated });
        }
        return { success: true };
      } else {
        dispatch({ type: AppActions.SET_ERROR, payload: response.error });
        return { success: false, error: response.error };
      }
    } catch (error) {
      dispatch({ type: AppActions.SET_ERROR, payload: error.message });
      return { success: false, error: error.message };
    }
  };

  const searchContractors = async (searchCriteria) => {
    dispatch({ type: AppActions.SET_LOADING, payload: true });
    
    try {
      const response = await appAPI.searchContractors(token, searchCriteria);
      
      if (response.success) {
        dispatch({ type: AppActions.SET_CONTRACTORS, payload: response.data });
        dispatch({ type: AppActions.SET_LOADING, payload: false });
        return { success: true, data: response.data };
      } else {
        dispatch({ type: AppActions.SET_ERROR, payload: response.error });
        return { success: false, error: response.error };
      }
    } catch (error) {
      dispatch({ type: AppActions.SET_ERROR, payload: error.message });
      return { success: false, error: error.message };
    }
  };

  const loadInvoices = async () => {
    dispatch({ type: AppActions.SET_LOADING, payload: true });
    
    try {
      const response = await appAPI.getInvoices(token);
      
      if (response.success) {
        dispatch({ type: AppActions.SET_INVOICES, payload: response.data });
        dispatch({ type: AppActions.SET_LOADING, payload: false });
      } else {
        dispatch({ type: AppActions.SET_ERROR, payload: response.error });
      }
    } catch (error) {
      dispatch({ type: AppActions.SET_ERROR, payload: error.message });
    }
  };

  const clearError = () => {
    dispatch({ type: AppActions.CLEAR_ERROR });
  };

  const value = {
    profile: state.profile,
    workRequests: state.workRequests,
    invoices: state.invoices,
    contractors: state.contractors,
    config: state.config,
    stats: state.stats,
    loading: state.loading,
    error: state.error,
    updateProfile,
    loadWorkRequests,
    createWorkRequest,
    updateWorkRequest,
    searchContractors,
    loadInvoices,
    clearError,
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};

// Custom hook to use app context
export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export default AppContext;