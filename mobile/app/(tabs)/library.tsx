import { useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { getAllProjects } from '@/lib/backend';
import { ActivityIndicator, ScrollView, StyleSheet, TextInput, View, TouchableOpacity } from 'react-native';


type Project = {
  id: string;
  name: string;
  domain: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  is_draft: boolean;
};

export default function LibraryScreen() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [projectError, setProjectError] = useState('');

  useEffect(() => {
    const loadProjects = async () => {
      try {
        setLoadingProjects(true);
        setProjectError('');
        const data = await getAllProjects();
        setProjects(data);
      } catch (err: unknown) {
        console.error('Failed to load projects', err);
        setProjectError('Unable to load projects right now.');
      } finally {
        setLoadingProjects(false);
      }
    };

    loadProjects();
  }, []);

  return (
    <ThemedView style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <View>
            <ThemedText type="subtitle" style={styles.sectionTitle}>
              Library
            </ThemedText>
            <ThemedText style={styles.sectionDescription}>
              Search saved projects.
            </ThemedText>
          </View>
          <View style={styles.searchCard}>
            <TextInput
              style={styles.searchInput}
              placeholder="Search documents and tags"
              placeholderTextColor="#6B7280"
            />
          </View>
        </View>

        <View style={styles.recentProjectsSection}>
          <View style={styles.sectionHeader}>
            <ThemedText type="subtitle">Projects</ThemedText>
            <ThemedText style={styles.smallAction}>Refresh</ThemedText>
          </View>
          {projectError ? (
            <ThemedText style={styles.errorMessage}>{projectError}</ThemedText>
          ) : null}
          {loadingProjects ? (
            <ActivityIndicator color="#0040E0" />
          ) : projects.length === 0 ? (
            <ThemedText style={styles.emptyState}>No projects were found.</ThemedText>
          ) : (
            projects.map((project) => (
              <TouchableOpacity key={project.id} style={styles.projectCard} onPress={() => router.push(`/Summary?projectId=${project.id}` as any)}>
                <View style={styles.projectCardRow}>
                  <View style={styles.projectIcon}>
                    <IconSymbol size={22} name="books.vertical.fill" color="#0040E0" />
                  </View>
                  <View style={styles.projectText}>
                    <ThemedText type="defaultSemiBold" style={styles.projectTitle}>{project.name}</ThemedText>
                    <ThemedText style={styles.projectDescription}>{project.domain ?? 'General research'}</ThemedText>
                  </View>
                </View>
                <ThemedText style={styles.projectMeta}>Updated {project.updated_at ? new Date(project.updated_at).toLocaleDateString() : ''}</ThemedText>
              </TouchableOpacity>
            ))
          )}
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
  headerRow: {
    gap: 18,
  },
  sectionTitle: {
    fontSize: 28,
    marginBottom: 6,
  },
  sectionDescription: {
    color: '#6B7280',
    maxWidth: 320,
  },
  searchCard: {
    marginTop: 16,
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 10,
  },
  searchInput: {
    color: '#111827',
  },
  cardsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
    justifyContent: 'space-between',
  },
  collectionCard: {
    width: '48%',
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 18,
    gap: 16,
    minHeight: 150,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 14,
    elevation: 2,
  },
  collectionIcon: {
    width: 42,
    height: 42,
    borderRadius: 14,
    backgroundColor: '#EFF6FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  collectionText: {
    gap: 6,
  },
  collectionTitle: {
    fontSize: 18,
  },
  collectionSubtitle: {
    color: '#6B7280',
    fontSize: 12,
  },
  collectionBadge: {
    marginTop: 'auto',
    alignSelf: 'flex-start',
    backgroundColor: '#E5E7EB',
    borderRadius: 999,
    paddingVertical: 6,
    paddingHorizontal: 10,
  },
  collectionBadgeText: {
    fontSize: 10,
    color: '#374151',
    fontWeight: '700',
  },
  documentSection: {
    gap: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  smallAction: {
    color: '#0040E0',
    fontSize: 12,
    fontWeight: '700',
  },
  documentCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 18,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 14,
    elevation: 2,
  },
  documentIcon: {
    width: 54,
    height: 54,
    borderRadius: 18,
    backgroundColor: '#EFF6FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  documentBody: {
    flex: 1,
    gap: 6,
  },
  documentTitle: {
    fontSize: 16,
  },
  documentDescription: {
    color: '#6B7280',
  },
  documentTag: {
    borderRadius: 999,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  tagText: {
    fontSize: 10,
    fontWeight: '700',
  },
  recentProjectsSection: {
    gap: 12,
  },
  projectCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    padding: 16,
    gap: 10,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 12,
    elevation: 2,
  },
  projectCardRow: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
  },
  projectIcon: {
    width: 42,
    height: 42,
    borderRadius: 14,
    backgroundColor: '#EFF6FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  projectText: {
    flex: 1,
    gap: 4,
  },
  projectTitle: {
    fontSize: 16,
  },
  projectDescription: {
    color: '#6B7280',
    fontSize: 13,
  },
  projectMeta: {
    color: '#6B7280',
    fontSize: 12,
  },
  emptyState: {
    color: '#6B7280',
    fontSize: 13,
  },
  errorMessage: {
    color: '#B91C1C',
    fontSize: 13,
  },
});
