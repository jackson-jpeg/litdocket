/**
 * Authentication Context
 *
 * Provides authentication state and methods throughout the app.
 */

'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  User as FirebaseUser,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  updateProfile
} from 'firebase/auth';
import { auth } from './firebase-config';

interface User {
  id: string;
  email: string;
  name: string;
  firm_name?: string;
  role?: string;
  jurisdictions?: string[];
}

interface AuthContextType {
  user: User | null;
  firebaseUser: FirebaseUser | null;
  loading: boolean;
  accessToken: string | null;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (email: string, password: string, name: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  completeSignup: (profile: Partial<User>) => Promise<void>;
  refreshUserData: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Get backend JWT token from Firebase ID token
  const getBackendToken = async (firebaseIdToken: string): Promise<string> => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/login/firebase`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: firebaseIdToken })
    });

    if (!response.ok) {
      throw new Error('Failed to authenticate with backend');
    }

    const data = await response.json();
    return data.access_token;
  };

  // Fetch user data from backend
  const fetchUserData = async (token: string): Promise<User> => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch user data');
    }

    return await response.json();
  };

  // Listen to Firebase auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setFirebaseUser(firebaseUser);

      if (firebaseUser) {
        try {
          // Get Firebase ID token
          const idToken = await firebaseUser.getIdToken();

          // Exchange for backend JWT
          const backendToken = await getBackendToken(idToken);
          setAccessToken(backendToken);

          // Save token to localStorage for API client
          localStorage.setItem('accessToken', backendToken);

          // Fetch user data
          const userData = await fetchUserData(backendToken);
          setUser(userData);

        } catch (error) {
          console.error('Error setting up user session:', error);
          setAccessToken(null);
          setUser(null);
          localStorage.removeItem('accessToken');
        }
      } else {
        setAccessToken(null);
        setUser(null);
        localStorage.removeItem('accessToken');
      }

      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // Email/password sign in
  const signInWithEmail = async (email: string, password: string) => {
    setLoading(true);
    try {
      await signInWithEmailAndPassword(auth, email, password);
      // Auth state change listener will handle the rest
    } catch (error: any) {
      setLoading(false);
      throw new Error(error.message || 'Failed to sign in');
    }
  };

  // Email/password sign up
  const signUpWithEmail = async (email: string, password: string, name: string) => {
    setLoading(true);
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);

      // Update Firebase profile with name
      await updateProfile(userCredential.user, { displayName: name });

      // Auth state change listener will handle backend sync
    } catch (error: any) {
      setLoading(false);
      throw new Error(error.message || 'Failed to sign up');
    }
  };

  // Google sign in
  const signInWithGoogle = async () => {
    setLoading(true);
    try {
      const provider = new GoogleAuthProvider();
      await signInWithPopup(auth, provider);
      // Auth state change listener will handle the rest
    } catch (error: any) {
      setLoading(false);
      throw new Error(error.message || 'Failed to sign in with Google');
    }
  };

  // Sign out
  const signOut = async () => {
    setLoading(true);
    try {
      await firebaseSignOut(auth);
      setAccessToken(null);
      setUser(null);
      localStorage.removeItem('accessToken');
    } catch (error: any) {
      throw new Error(error.message || 'Failed to sign out');
    } finally {
      setLoading(false);
    }
  };

  // Complete signup with additional profile info
  const completeSignup = async (profile: Partial<User>) => {
    if (!firebaseUser || !accessToken) {
      throw new Error('No authenticated user');
    }

    const idToken = await firebaseUser.getIdToken();

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/signup/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...profile,
        id_token: idToken
      })
    });

    if (!response.ok) {
      throw new Error('Failed to complete signup');
    }

    const data = await response.json();
    setAccessToken(data.access_token);
    setUser(data.user);
  };

  // Refresh user data
  const refreshUserData = async () => {
    if (!accessToken) return;

    try {
      const userData = await fetchUserData(accessToken);
      setUser(userData);
    } catch (error) {
      console.error('Failed to refresh user data:', error);
    }
  };

  const value = {
    user,
    firebaseUser,
    loading,
    accessToken,
    signInWithEmail,
    signUpWithEmail,
    signInWithGoogle,
    signOut,
    completeSignup,
    refreshUserData
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
