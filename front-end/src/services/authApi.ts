/**
 * Authentication API Service for Operator Login.
 */

import { apiClient } from './client';
import { ApiResponse } from '@/types';

export interface OperatorProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  jurisdiction_code?: string;
}

export interface TokenResponseData {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  operator: OperatorProfile;
}

export const authApi = {
  /**
   * Authenticates operator credentials and returns access token.
   */
  async login(username: string, password: string): Promise<ApiResponse<TokenResponseData>> {
    return apiClient<ApiResponse<TokenResponseData>>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },
};
