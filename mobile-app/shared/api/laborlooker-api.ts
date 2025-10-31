// LaborLooker Mobile API Client
// TypeScript/JavaScript API client for React Native

export interface User {
  id: number;
  email: string;
  account_type: 'customer' | 'contractor' | 'developer';
  email_verified: boolean;
  created_at: string;
  contractor_profile?: ContractorProfile;
  customer_profile?: CustomerProfile;
}

export interface ContractorProfile {
  business_name: string;
  contact_name: string;
  phone: string;
  location: string;
  services: string;
  geographic_area: string;
}

export interface CustomerProfile {
  first_name: string;
  last_name: string;
  phone: string;
  address: string;
  city: string;
  state: string;
}

export interface Rating {
  user_id: number;
  average_rating: number;
  total_ratings: number;
  rating_breakdown: Record<string, number>;
  recent_reviews: Array<{
    rating: number;
    comment: string;
    date: string;
  }>;
}

export interface Contractor {
  id: number;
  business_name: string;
  contact_name: string;
  location: string;
  services: string;
  rating: number;
  rating_count: number;
  geographic_area: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  user: User;
  token: string;
}

export interface SearchContractorsRequest {
  service_category: string;
  geographic_area: string;
  customer_rating?: number;
}

export interface SearchContractorsResponse {
  contractors: Contractor[];
  total: number;
}

export interface SubmitRatingRequest {
  ratee_id: number;
  rating: number;
  comment?: string;
  work_request_id: number;
  transaction_type?: string;
}

export class LaborLookerAPI {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = 'https://your-domain.com/api/v1') {
    this.baseUrl = baseUrl;
  }

  setToken(token: string) {
    this.token = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    
    if (response.success && response.token) {
      this.setToken(response.token);
    }
    
    return response;
  }

  async getProfile(): Promise<{ user: User }> {
    return this.request<{ user: User }>('/users/profile');
  }

  async getRatings(userId: number): Promise<Rating> {
    return this.request<Rating>(`/ratings/${userId}`);
  }

  async searchContractors(
    searchParams: SearchContractorsRequest
  ): Promise<SearchContractorsResponse> {
    return this.request<SearchContractorsResponse>('/contractors/search', {
      method: 'POST',
      body: JSON.stringify(searchParams),
    });
  }

  async submitRating(
    ratingData: SubmitRatingRequest
  ): Promise<{ success: boolean; message: string; rating_id: number }> {
    return this.request('/ratings', {
      method: 'POST',
      body: JSON.stringify(ratingData),
    });
  }

  async healthCheck(): Promise<{
    status: string;
    api_version: string;
    timestamp: string;
    service: string;
  }> {
    return this.request('/health');
  }
}

export default LaborLookerAPI;