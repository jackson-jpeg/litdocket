import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import { API_URL } from './config';

// Configuration constants
const REQUEST_TIMEOUT = 15000; // 15 seconds
const MAX_RETRIES = 3;
const RETRY_DELAY_BASE = 1000; // 1 second base delay for exponential backoff

// Error extraction utility
export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  detail?: string;
}

export function extractApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string; message?: string }>;

    // Network error (no response)
    if (!axiosError.response) {
      if (axiosError.code === 'ECONNABORTED') {
        return {
          message: 'Request timed out. Please check your connection and try again.',
          code: 'TIMEOUT',
        };
      }
      return {
        message: 'Network error. Please check your internet connection.',
        code: 'NETWORK_ERROR',
      };
    }

    // Server responded with error
    const status = axiosError.response.status;
    const responseData = axiosError.response.data;

    // Extract detail from FastAPI error response
    const detail = responseData?.detail || responseData?.message;

    // Map common status codes to user-friendly messages
    switch (status) {
      case 400:
        return {
          message: detail || 'Invalid request. Please check your input.',
          status,
          detail,
        };
      case 401:
        return {
          message: 'Session expired. Please log in again.',
          status,
          code: 'UNAUTHORIZED',
        };
      case 403:
        return {
          message: 'Access denied. You do not have permission for this action.',
          status,
          code: 'FORBIDDEN',
        };
      case 404:
        return {
          message: detail || 'The requested resource was not found.',
          status,
          detail,
        };
      case 429:
        return {
          message: 'Too many requests. Please wait a moment and try again.',
          status,
          code: 'RATE_LIMITED',
        };
      case 500:
      case 502:
      case 503:
      case 504:
        return {
          message: 'Server error. Our team has been notified. Please try again later.',
          status,
          code: 'SERVER_ERROR',
        };
      default:
        return {
          message: detail || `Request failed (${status})`,
          status,
          detail,
        };
    }
  }

  // Non-axios error
  if (error instanceof Error) {
    return {
      message: error.message,
    };
  }

  return {
    message: 'An unexpected error occurred. Please try again.',
  };
}

// Retry configuration
interface RetryConfig {
  retries?: number;
  retryDelay?: number;
  retryCondition?: (error: AxiosError) => boolean;
}

// Default retry condition - retry on network errors and 5xx status codes
function defaultRetryCondition(error: AxiosError): boolean {
  // Retry on network errors
  if (!error.response) {
    return true;
  }

  // Retry on 5xx server errors and 429 rate limiting
  const status = error.response.status;
  return status >= 500 || status === 429;
}

// Calculate delay with exponential backoff and jitter
function calculateRetryDelay(attempt: number, baseDelay: number): number {
  const exponentialDelay = baseDelay * Math.pow(2, attempt);
  const jitter = Math.random() * 200; // Add up to 200ms jitter
  return Math.min(exponentialDelay + jitter, 10000); // Cap at 10 seconds
}

// Create axios instance with retry logic
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor with retry logic and auth handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as AxiosRequestConfig & { _retryCount?: number };

    // Handle 401 - clear token
    if (error.response?.status === 401) {
      localStorage.removeItem('accessToken');
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        console.log('Authentication failed - token may be expired');
        // Optionally redirect to login
        // window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    // Retry logic
    if (!config) {
      return Promise.reject(error);
    }

    config._retryCount = config._retryCount || 0;

    // Check if we should retry
    if (
      config._retryCount < MAX_RETRIES &&
      defaultRetryCondition(error)
    ) {
      config._retryCount += 1;

      const delay = calculateRetryDelay(config._retryCount, RETRY_DELAY_BASE);
      console.log(`Request failed, retrying (${config._retryCount}/${MAX_RETRIES}) in ${Math.round(delay)}ms...`);

      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, delay));

      // Retry the request
      return apiClient(config);
    }

    return Promise.reject(error);
  }
);

// Utility function to make requests with custom retry config
export async function fetchWithRetry<T>(
  config: AxiosRequestConfig,
  retryConfig?: RetryConfig
): Promise<AxiosResponse<T>> {
  const maxRetries = retryConfig?.retries ?? MAX_RETRIES;
  const baseDelay = retryConfig?.retryDelay ?? RETRY_DELAY_BASE;
  const shouldRetry = retryConfig?.retryCondition ?? defaultRetryCondition;

  let lastError: AxiosError | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await apiClient.request<T>(config);
    } catch (error) {
      if (!axios.isAxiosError(error)) {
        throw error;
      }

      lastError = error;

      // Check if we should retry
      if (attempt < maxRetries && shouldRetry(error)) {
        const delay = calculateRetryDelay(attempt, baseDelay);
        console.log(`Request failed, retrying (${attempt + 1}/${maxRetries}) in ${Math.round(delay)}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }

      throw error;
    }
  }

  throw lastError;
}

export default apiClient;
