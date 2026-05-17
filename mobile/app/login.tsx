import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, TextInput, View } from 'react-native';

import { supabase } from '@/lib/supabase';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const isValidEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

  const getErrorMessage = (supabaseError: any) => {
    const message = supabaseError?.message || '';

    if (message.includes('Invalid login credentials')) {
      return 'Your email or password is incorrect. Please try again!';
    }

    return 'Can not login. Please try again later!';
  };

  const handleSignIn = async () => {
    if (!email && !password) {
      setError('Please enter your email and password!');
      return;
    }

    if (!email) {
      setError('Please enter your email!');
      return;
    }

    if (!password) {
      setError('Please enter your password!');
      return;
    }

    if (!isValidEmail(email)) {
      setError('Your email is invalid. Please check again!');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        console.error('Supabase login error:', error);
        setError(getErrorMessage(error));
        return;
      }

      router.replace('/(tabs)');
    } catch (err: any) {
      console.error('Unexpected error during login:', err);
      setError('Can not login. Please try again later!');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ThemedView style={styles.page}>
      <View style={styles.header}>
        <ThemedText type="title" style={styles.branding}>
          Lumen
        </ThemedText>
        <ThemedText type="subtitle" style={styles.subtitle}>
          Sign in to your research library.
        </ThemedText>
      </View>

      <View style={styles.form}>
        <View style={styles.fieldGroup}>
          <ThemedText type="defaultSemiBold" style={styles.label}>
            Email
          </ThemedText>
          <TextInput
            style={styles.input}
            placeholder="email@lumen.io"
            placeholderTextColor="#6B7280"
            keyboardType="email-address"
            autoCapitalize="none"
            value={email}
            onChangeText={setEmail}
          />
        </View>

        <View style={styles.fieldGroup}>
          <View style={styles.fieldHeader}>
            <ThemedText type="defaultSemiBold" style={styles.label}>
              Password
            </ThemedText>
            <Pressable style={styles.linkLabel} onPress={() => router.push('/register' as any)}>
              <ThemedText type="defaultSemiBold">Create account</ThemedText>
            </Pressable>
          </View>
          <TextInput
            style={styles.input}
            placeholder="••••••••"
            placeholderTextColor="#6B7280"
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />
        </View>

        <Pressable style={styles.actionButton} onPress={handleSignIn} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <ThemedText type="subtitle" style={styles.actionText}>
              Sign In
            </ThemedText>
          )}
        </Pressable>

        {error ? <ThemedText style={styles.error}>{error}</ThemedText> : null}

        <View style={styles.dividerRow}>
          <View style={styles.dividerLine} />
          <ThemedText style={styles.dividerLabel}>OR</ThemedText>
          <View style={styles.dividerLine} />
        </View>

        <View style={styles.socialRow}>
          <Pressable style={styles.socialButton}>
            <ThemedText style={styles.socialText}>Google</ThemedText>
          </Pressable>
          <Pressable style={styles.socialButton}>
            <ThemedText style={styles.socialText}>Apple</ThemedText>
          </Pressable>
        </View>
      </View>

      <View style={styles.footer}>
        <ThemedText style={styles.footerText}>
          By signing in, you agree to Lumen’s Terms of Service and Privacy Policy.
        </ThemedText>
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: '#F8F9FA',
    paddingHorizontal: 24,
    justifyContent: 'space-between',
    paddingTop: 80,
    paddingBottom: 32,
  },
  header: {
    gap: 16,
  },
  branding: {
    fontSize: 42,
    lineHeight: 48,
  },
  subtitle: {
    color: '#4B5563',
  },
  form: {
    gap: 20,
  },
  fieldGroup: {
    gap: 10,
  },
  fieldHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    color: '#6B7280',
    letterSpacing: 0.5,
  },
  linkLabel: {
    paddingVertical: 2,
  },
  input: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    paddingHorizontal: 18,
    paddingVertical: 16,
    fontSize: 16,
    color: '#111827',
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 10,
    elevation: 2,
  },
  actionButton: {
    backgroundColor: '#0040E0',
    borderRadius: 28,
    paddingVertical: 16,
    alignItems: 'center',
  },
  actionText: {
    color: '#FFFFFF',
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#D1D5DB',
  },
  dividerLabel: {
    color: '#6B7280',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  socialRow: {
    flexDirection: 'row',
    gap: 12,
  },
  socialButton: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    paddingVertical: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  socialText: {
    color: '#374151',
    fontWeight: '700',
  },
  footer: {
    alignItems: 'center',
    paddingHorizontal: 12,
  },
  footerText: {
    color: '#6B7280',
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
  error: {
    color: '#B91C1C',
    backgroundColor: '#FEE2E2',
    padding: 12,
    borderRadius: 16,
    marginTop: 4,
    fontSize: 13,
  },
});
