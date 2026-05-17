import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, TextInput, View } from 'react-native';

import { supabase } from '@/lib/supabase';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

export default function RegisterScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const isValidEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

  const handleCreateAccount = async () => {
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

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
      });

      if (error) {
        console.error('Supabase sign-up error:', error);
        setError(error.message || 'Could not create account. Please try again later!');
        return;
      }

      router.replace('/login');
    } catch (err: any) {
      console.error('Unexpected error during sign-up:', err);
      setError('Could not create account. Please try again later!');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ThemedView style={styles.page}>
      <View style={styles.header}>
        <ThemedText type="title" style={styles.branding}>
          Create Account
        </ThemedText>
        <ThemedText type="subtitle" style={styles.subtitle}>
          Start your curated summarization journey.
        </ThemedText>
      </View>

      <View style={styles.form}>
        <View style={styles.fieldGroup}>
          <ThemedText type="defaultSemiBold" style={styles.label}>
            Email Address
          </ThemedText>
          <TextInput
            style={styles.input}
            placeholder="name@example.com"
            placeholderTextColor="#6B7280"
            keyboardType="email-address"
            autoCapitalize="none"
            value={email}
            onChangeText={setEmail}
          />
        </View>

        <View style={styles.fieldGroup}>
          <ThemedText type="defaultSemiBold" style={styles.label}>
            Password
          </ThemedText>
          <TextInput
            style={styles.input}
            placeholder="••••••••"
            placeholderTextColor="#6B7280"
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />
          <ThemedText style={styles.helper}>
            Must be at least 8 characters with one special symbol.
          </ThemedText>
        </View>

        {error ? <ThemedText style={styles.error}>{error}</ThemedText> : null}
        <Pressable style={styles.actionButton} onPress={handleCreateAccount} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <ThemedText type="subtitle" style={styles.actionText}>
              Create Account
            </ThemedText>
          )}
        </Pressable>

        <View style={styles.signInRow}>
          <ThemedText style={styles.signInText}>Already have an account?</ThemedText>
          <Link href="/login">
            <ThemedText type="defaultSemiBold" style={styles.signInLink}>
              Sign In
            </ThemedText>
          </Link>
        </View>
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
    fontSize: 36,
    lineHeight: 44,
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
  label: {
    color: '#6B7280',
    letterSpacing: 0.5,
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
  helper: {
    marginTop: 4,
    color: '#6B7280',
    fontSize: 12,
    lineHeight: 18,
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
  signInRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
  },
  signInText: {
    color: '#6B7280',
  },
  signInLink: {
    color: '#0040E0',
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
