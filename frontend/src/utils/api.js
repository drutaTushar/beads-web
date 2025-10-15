const API_BASE = 'http://localhost:8080/api';

class APIError extends Error {
  constructor(message, status, response) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.response = response;
  }
}

export const api = {
  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      
      // Parse response body
      let data;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        const errorMessage = data?.detail || data?.message || `HTTP ${response.status}: ${response.statusText}`;
        throw new APIError(errorMessage, response.status, data);
      }

      return data;
    } catch (error) {
      if (error instanceof APIError) {
        throw error;
      }
      
      // Network or other errors
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new APIError('Network error: Unable to connect to server', 0, null);
      }
      
      throw new APIError(error.message || 'Unknown error occurred', 0, null);
    }
  },

  get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  },

  post(endpoint, data) {
    return this.request(endpoint, { method: 'POST', body: data });
  },

  put(endpoint, data) {
    return this.request(endpoint, { method: 'PUT', body: data });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  },
};

// React Query error handler
export const handleQueryError = (error, showError) => {
  if (error instanceof APIError) {
    showError(error.message, {
      details: error.status ? `Status: ${error.status}` : 'Network Error',
    });
  } else {
    showError('An unexpected error occurred', {
      details: error.message,
    });
  }
};

export { APIError };