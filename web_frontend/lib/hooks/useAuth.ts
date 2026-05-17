// lib/hooks/useAuth.ts
'use client'
import { useState, useEffect } from "react";
import { supabase } from "../supabase/client";

export function useAuth() {
    const [token, setToken] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {

        const initializeAuth = async () => {
            try{
                const { data: { session }, error } = await supabase.auth.getSession();
                if (error) throw error
                setToken(session?.access_token ?? null);
            } catch (err) {
                console.error('Failed to get initial session:', err);
            } finally {
                setLoading(false);
            }
        };

        initializeAuth();

        const { data: authListener } = supabase.auth.onAuthStateChange(
            (_event, session) => {
                setToken(session?.access_token ?? null);
            }
        );
        return () => authListener.subscription.unsubscribe();
    }, []);

    return { token, loading };
}