import Constants from 'expo-constants';
import { createClient } from '@supabase/supabase-js';

const expoConfig = Constants.expoConfig ?? (Constants.manifest as any);
const expoExtra = (expoConfig?.extra ?? {}) as Record<string, string>;
const supabaseUrl = process.env.SUPABASE_URL ?? expoExtra.SUPABASE_URL ?? '';
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY ?? expoExtra.SUPABASE_ANON_KEY ?? '';

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    'Supabase configuration is missing. Set SUPABASE_URL and SUPABASE_ANON_KEY in environment variables or expo extra config.',
    {
      hasExpoConfig: Boolean(expoConfig),
      expoExtraKeys: Object.keys(expoExtra),
    }
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
