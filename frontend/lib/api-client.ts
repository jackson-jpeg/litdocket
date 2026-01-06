import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include JWT token from localStorage
apiClient.interceptors.request.use(
  (config) => {
    // Get token from localStorage (set by auth context)
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

// Add response interceptor to handle 401 errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - clear it and redirect to login
      localStorage.removeItem('accessToken');
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        console.log('Authentication failed - token may be expired');
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
