import { useEffect, useState } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { getProjectDocuments, getSummary } from '@/lib/backend';
import { ActivityIndicator, ScrollView, StyleSheet, View, TouchableOpacity } from 'react-native';

export default function ProjectSummary() {
  const params = useLocalSearchParams();
  const projectId = params.projectId as string;
  const router = useRouter();

  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!projectId) return;
    const load = async () => {
      try {
        setLoading(true);
        setError('');
        const docs = await getProjectDocuments(projectId);
        // If each doc contains a summary_id, fetch it
        const docsWithSummaries = await Promise.all(
          docs.map(async (d: any) => {
            if (d.summary_id) {
              try {
                const s = await getSummary(d.summary_id);
                return { ...d, summary: s };
              } catch (_) {
                return { ...d, summary: null };
              }
            }
            return { ...d, summary: null };
          })
        );
        setDocuments(docsWithSummaries);
      } catch (err) {
        console.error(err);
        setError('Unable to load project summaries');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [projectId]);

  return (
    <ThemedView style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <ThemedText type="subtitle">Summary</ThemedText>
          <TouchableOpacity onPress={() => router.push(`/chat?projectId=${projectId}` as any)}>
            <ThemedText style={styles.chatButton}>Chat</ThemedText>
          </TouchableOpacity>
        </View>

        {error ? <ThemedText style={styles.error}>{error}</ThemedText> : null}
        {loading ? <ActivityIndicator /> : null}

        {documents.map((doc) => (
          <View key={doc.id} style={styles.card}>
            <ThemedText type="defaultSemiBold">{doc.title ?? doc.file_name ?? 'Untitled'}</ThemedText>
            <ThemedText style={styles.desc}>{doc.summary?.text ?? doc.summary?.content ?? 'No summary available'}</ThemedText>
          </View>
        ))}
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: '#F8F9FA' },
  content: { padding: 24, gap: 16 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  chatButton: { color: '#0040E0', fontWeight: '700' },
  card: { backgroundColor: '#FFFFFF', borderRadius: 16, padding: 16 },
  desc: { color: '#6B7280', marginTop: 8 },
  error: { color: '#B91C1C' },
});
