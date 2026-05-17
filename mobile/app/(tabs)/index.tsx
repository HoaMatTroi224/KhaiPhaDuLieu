import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useEffect, useState } from 'react';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { getRecentProjects } from '@/lib/backend';

export default function DashboardScreen() {
  const router = useRouter();
  const [projectsData, setProjectsData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError('');
        const data = await getRecentProjects();
        setProjectsData(data);
      } catch (err) {
        console.error(err);
        setError('Unable to load recent projects');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <ThemedView style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.hero}> 
          <ThemedText type="subtitle" style={styles.heroLabel}>
            Dashboard
          </ThemedText>
          <ThemedText type="title" style={styles.heroTitle}>
            Curating knowledge with precision.
          </ThemedText>
          <ThemedText style={styles.heroCopy}>
            Explore your research projects and jump straight into summaries.
          </ThemedText>
        </View>

        <View style={styles.projectsHeader}>
          <ThemedText type="subtitle">Recent Projects</ThemedText>
          <TouchableOpacity onPress={() => router.push('/(tabs)/library' as any)} style={styles.viewAllButton}>
            <ThemedText style={styles.viewAllText}>View all</ThemedText>
          </TouchableOpacity>
        </View>

        <View style={styles.projectGrid}>
          {error ? <ThemedText style={styles.emptyState}>{error}</ThemedText> : null}
          {loading ? <ThemedText style={styles.emptyState}>Loading...</ThemedText> : null}
          {!loading && projectsData.map((project) => (
            <TouchableOpacity key={project.id} style={styles.projectCard} onPress={() => router.push(`/Summary?projectId=${project.id}` as any)}>
              <View style={styles.projectTop}>
                <View style={styles.projectStatus}></View>
                <IconSymbol size={24} name="ellipsis" color="#6B7280" />
              </View>
              <ThemedText type="subtitle" style={styles.projectTitle}>{project.name}</ThemedText>
              <ThemedText style={styles.projectDescription}>{project.description ?? project.domain ?? 'General research'}</ThemedText>
              <View style={styles.projectFooter}>
                <ThemedText style={styles.projectMeta}>{project.updated_at ? `Updated ${new Date(project.updated_at).toLocaleDateString()}` : ''}</ThemedText>
                <View style={styles.projectTagContainer}>
                  <ThemedText style={styles.projectTag}>{project.is_draft ? 'Draft' : 'Cloud'}</ThemedText>
                </View>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: '#F8F9FA',
  },
  content: {
    padding: 24,
    gap: 24,
  },
  hero: {
    gap: 12,
  },
  heroLabel: {
    color: '#047857',
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  heroTitle: {
    fontSize: 34,
    lineHeight: 40,
  },
  heroCopy: {
    color: '#4B5563',
    lineHeight: 24,
    maxWidth: 360,
  },
  projectsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  viewAllButton: {
    paddingVertical: 4,
  },
  viewAllText: {
    color: '#0040E0',
    fontWeight: '700',
  },
  projectGrid: {
    gap: 16,
  },
  projectCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 28,
    padding: 22,
    gap: 14,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 14,
    elevation: 2,
  },
  projectTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  projectStatus: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
  },
  projectTitle: {
    fontSize: 20,
  },
  projectDescription: {
    color: '#6B7280',
    lineHeight: 22,
  },
  projectFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  projectMeta: {
    color: '#6B7280',
    fontSize: 12,
  },
  projectTagContainer: {
    backgroundColor: '#E0F2FE',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  projectTag: {
    color: '#0369A1',
    fontSize: 10,
    fontWeight: '700',
  },
  emptyState: {
    color: '#6B7280',
    fontSize: 13,
  },
});

