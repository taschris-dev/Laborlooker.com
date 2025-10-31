import React, { createContext, useContext, useEffect, useReducer } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authAPI } from '../services/api';

// Initial state
const initialState = {
  user: null,
  token: null,
  loading: true,
  error: null,
};

// Auth actions
const AuthActions = {
  SET_LOADING: 'SET_LOADING',
  LOGIN_SUCCESS: 'LOGIN_SUCCESS',
  LOGIN_FAILURE: 'LOGIN_FAILURE',
  LOGOUT: 'LOGOUT',
  CLEAR_ERROR: 'CLEAR_ERROR',
  SET_USER: 'SET_USER',
};

// Auth reducer
const authReducer = (state, action) => {
  switch (action.type) {
    case AuthActions.SET_LOADING:
      return { ...state, loading: action.payload };
    
    case AuthActions.LOGIN_SUCCESS:
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        loading: false,
        error: null,
      };
    
    case AuthActions.LOGIN_FAILURE:
      return {
        ...state,
        user: null,
        token: null,
        loading: false,
        error: action.payload,
      };
    
    case AuthActions.LOGOUT:
      return {
        ...state,
        user: null,
        token: null,
        loading: false,
        error: null,
      };
    
    case AuthActions.CLEAR_ERROR:
      return { ...state, error: null };
    
    case AuthActions.SET_USER:
      return { ...state, user: action.payload };
    
    default:
      return state;
  }
};

// Create context
const AuthContext = createContext();

// Auth provider component
export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Load user from storage on app start
  useEffect(() => {
    loadUserFromStorage();
  }, []);

  const loadUserFromStorage = async () => {
    try {
      const token = await AsyncStorage.getItem('userToken');
      const userData = await AsyncStorage.getItem('userData');
      
      if (token && userData) {
        const user = JSON.parse(userData);
        dispatch({
          type: AuthActions.LOGIN_SUCCESS,
          payload: { user, token },
        });
      } else {
        dispatch({ type: AuthActions.SET_LOADING, payload: false });
      }
    } catch (error) {
      console.error('Error loading user from storage:', error);
      dispatch({ type: AuthActions.SET_LOADING, payload: false });
    }
  };

  const login = async (email, password) => {
    dispatch({ type: AuthActions.SET_LOADING, payload: true });
    
    try {
      const response = await authAPI.login(email, password);
      
      if (response.success) {
        const { user, token } = response.data;
        
        // Store in AsyncStorage
        await AsyncStorage.setItem('userToken', token);
        await AsyncStorage.setItem('userData', JSON.stringify(user));
        
        dispatch({
          type: AuthActions.LOGIN_SUCCESS,
          payload: { user, token },
        });
        
        return { success: true };
      } else {
        dispatch({
          type: AuthActions.LOGIN_FAILURE,
          payload: response.error || 'Login failed',
        });
        return { success: false, error: response.error };
      }
    } catch (error) {
      dispatch({
        type: AuthActions.LOGIN_FAILURE,
        payload: error.message || 'Network error',
      });
      return { success: false, error: error.message };
    }
  };

  const register = async (userData) => {
    dispatch({ type: AuthActions.SET_LOADING, payload: true });
    
    try {
      const response = await authAPI.register(userData);
      
      if (response.success) {
        dispatch({ type: AuthActions.SET_LOADING, payload: false });
        return { success: true, message: response.data.message };
      } else {
        dispatch({
          type: AuthActions.LOGIN_FAILURE,
          payload: response.error || 'Registration failed',
        });
        return { success: false, error: response.error };
      }
    } catch (error) {
      dispatch({
        type: AuthActions.LOGIN_FAILURE,
        payload: error.message || 'Network error',
      });
      return { success: false, error: error.message };
    }
  };

  const logout = async () => {
    try {
      // Remove from AsyncStorage
      await AsyncStorage.removeItem('userToken');
      await AsyncStorage.removeItem('userData');
      
      dispatch({ type: AuthActions.LOGOUT });
    } catch (error) {
      console.error('Error during logout:', error);
    }
  };

  const updateUser = (userData) => {
    dispatch({ type: AuthActions.SET_USER, payload: userData });
  };

  const clearError = () => {
    dispatch({ type: AuthActions.CLEAR_ERROR });
  };

  const value = {
    user: state.user,
    token: state.token,
    loading: state.loading,
    error: state.error,
    login,
    register,
    logout,
    updateUser,
    clearError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;