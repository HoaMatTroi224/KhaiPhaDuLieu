import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';

import { supabase } from '@/lib/supabase';
import { initializeProject, finalizeProject } from '@/lib/backend';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';


const MAX_FILE_COUNT = 4;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

interface SelectedFile {
  id: string;
  name: string;
  uri: string;
  size: number;
  mimeType?: string;
}



export default function NewProjectScreen() {
  const router = useRouter();
  const [projectId, setProjectId] = useState<string>('');
  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const createProject = async () => {
      try {
        setError('');
        const project = await initializeProject();
        setProjectId(project.id);
      } catch (err: unknown) {
        console.error('Project initialization failed:', err);
        setError('Unable to create a new project. Please try again later.');
      }
    };

    createProject();
  }, []);

  const normalizeDocumentResult = (
  result: DocumentPicker.DocumentPickerResult
): SelectedFile[] => {
  if (result.canceled) {
    return [];
  }

  return result.assets.map((file) => ({
    id: `${file.uri}-${file.name}`,
    name: file.name,
    uri: file.uri,
    size: file.size ?? 0,
    mimeType: file.mimeType ?? 'application/pdf',
  }));
};

  const handlePickFiles = async () => {
  setError('');

  try {
    const result =
      await DocumentPicker.getDocumentAsync({
        type: 'application/pdf',
        multiple: true,
        copyToCacheDirectory: true,
      });

    console.log(
      'DOCUMENT PICKER RESULT:',
      JSON.stringify(result, null, 2)
    );

    const pickedFiles =
      normalizeDocumentResult(result);

    console.log(
      'PICKED FILES:',
      pickedFiles
    );

    if (pickedFiles.length === 0) {
      return;
    }

    const invalidFile = pickedFiles.find(
      (file) =>
        file.size > MAX_FILE_SIZE ||
        !file.name
          .toLowerCase()
          .endsWith('.pdf')
    );

    if (invalidFile) {
      setError(
        'Only PDF files under 10MB are supported.'
      );
      return;
    }

    const combinedFiles = [
      ...selectedFiles,
      ...pickedFiles,
    ];

    if (combinedFiles.length > MAX_FILE_COUNT) {
      setError(
        `Maximum ${MAX_FILE_COUNT} PDFs allowed.`
      );

      setSelectedFiles(
        combinedFiles.slice(0, MAX_FILE_COUNT)
      );

      return;
    }

    setSelectedFiles(combinedFiles);
  } catch (err) {
    console.error(
      'Document picker error:',
      err
    );

    setError(
      'Could not open file picker. Please try again.'
    );
  }
};

  const removeFile = (id: string) => {
    setSelectedFiles((prev) => prev.filter((file) => file.id !== id));
  };

  const uploadFiles = async () => {
  if (selectedFiles.length === 0) {
    setError('Please choose at least one PDF to upload.');
    return;
  }

  if (!projectId) {
    setError('Project not initialized.');
    return;
  }

  setUploading(true);
  setError('');

  try {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      throw new Error('Authentication required');
    }

    const uploadedDocuments: Array<{
      file_name: string;
      file_path: string;
      file_url: string;
      file_type: 'pdf';
      file_size: number;
    }> = [];

    // for (const file of selectedFiles) {
    //   console.log('Uploading:', file.name);

    //   const timestamp = Date.now();

    //   const randomSuffix = Math.random()
    //     .toString(36)
    //     .substring(2, 8);

    //   const safeName = file.name.replace(
    //     /[^a-zA-Z0-9._-]/g,
    //     '_'
    //   );

    //   const storagePath =
    //     `${user.id}/mobile_uploads/` +
    //     `${timestamp}_${randomSuffix}_${safeName}`;

    //   const fileToUpload = {
    //     uri: file.uri,
    //     name: safeName,
    //     type: file.mimeType || 'application/pdf',
    //   };

    //   const { data, error } = await supabase.storage
    //     .from('documents')
    //     .upload(
    //       storagePath,
    //       fileToUpload as any,
    //       {
    //         contentType:
    //           file.mimeType || 'application/pdf',
    //         upsert: false,
    //       }
    //     );

    //   console.log('UPLOAD DATA:', data);
    //   console.log('UPLOAD ERROR:', error);

    //   if (error) {
    //     throw error;
    //   }

    //   const { data: publicUrlData } =
    //     supabase.storage
    //       .from('documents')
    //       .getPublicUrl(storagePath);

    //   uploadedDocuments.push({
    //     file_name: file.name,
    //     file_path: storagePath,
    //     file_url: publicUrlData.publicUrl,
    //     file_type: 'pdf',
    //     file_size: file.size,
    //   });
    // }

    for (const file of selectedFiles) {
      console.log('Uploading:', file.name);

      const timestamp = Date.now();

      const randomSuffix = Math.random()
        .toString(36)
        .substring(2, 8);

      const safeName = file.name.replace(
        /[^a-zA-Z0-9._-]/g,
        '_'
      );

      const storagePath =
        `${user.id}/mobile_uploads/` +
        `${timestamp}_${randomSuffix}_${safeName}`;

      // IMPORTANT:
      // fetch local file URI -> convert to Blob

      // 
      
      const response = await fetch(file.uri);

      const arrayBuffer = await response.arrayBuffer();

      console.log('FILE URI:', file.uri);

      console.log('ARRAY BUFFER SIZE:', arrayBuffer.byteLength);

      console.log('STORAGE PATH:', storagePath);


      const { data, error } = await supabase.storage
        .from('documents')
        .upload(
          storagePath,
          arrayBuffer,
          {
            contentType: 'application/pdf',
            upsert: false,
          }
        );

      console.log('UPLOAD DATA:', data);
      console.log('UPLOAD ERROR:', error);

      
      if (error) {
        throw error;
      }

      const { data: publicUrlData } =
        supabase.storage
          .from('documents')
          .getPublicUrl(storagePath);

      uploadedDocuments.push({
        file_name: file.name,
        file_path: storagePath,
        file_url: publicUrlData.publicUrl,
        file_type: 'pdf',
        file_size: file.size,
      });
    }

    console.log(
      'Calling finalizeProject...'
    );

    await finalizeProject(projectId, {
      name: 'Untitled Mobile Project',
      domain: null,
      documents: uploadedDocuments,
    });

    console.log('Finalize success');
    console.log('Navigating to summary with projectId:', projectId);

    router.push(
      `/Summary?projectId=${projectId}` as any
    );
  } catch (err: any) {
    console.error('UPLOAD FLOW ERROR:', err);

    setError(
      err?.message ||
        'Upload failed. Please try again.'
    );
  } finally {
    setUploading(false);
  }
};

  return (
    <ThemedView style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.hero}> 
          <ThemedText type="title" style={styles.heroTitle}>
            New Project
          </ThemedText>
          <ThemedText style={styles.heroSubtitle}>
            Add your research PDFs and generate a concise summary in one flow.
          </ThemedText>
        </View>

        <Pressable style={styles.dropZone} onPress={handlePickFiles} disabled={uploading}>
          <View style={styles.uploadIcon}>
            <IconSymbol size={32} name="cloud_upload" color="#FFFFFF" />
          </View>
          <ThemedText type="subtitle" style={styles.dropTitle}>
            Tap to add PDFs
          </ThemedText>
          <ThemedText style={styles.dropText}>Select files from device storage</ThemedText>
          <View style={styles.fileBadge}>
            <ThemedText style={styles.fileBadgeText}>PDF ONLY</ThemedText>
          </View>
        </Pressable>

        {error ? <ThemedText style={styles.error}>{error}</ThemedText> : null}

        {selectedFiles.length > 0 ? (
          <View style={styles.selectedSection}>
            <ThemedText type="subtitle" style={styles.sectionHeading}>
              Selected files
            </ThemedText>
            {selectedFiles.map((file) => (
              <View key={file.id} style={styles.selectedFileCard}>
                <View style={styles.fileInfo}>
                  <IconSymbol size={20} name="picture_as_pdf" color="#DC2626" />
                  <View style={styles.fileMeta}>
                    <ThemedText type="defaultSemiBold" style={styles.fileName}>
                      {file.name}
                    </ThemedText>
                    <ThemedText style={styles.fileDescription}>
                      {(file.size / (1024 * 1024)).toFixed(1)} MB
                    </ThemedText>
                  </View>
                </View>
                <Pressable onPress={() => removeFile(file.id)} style={styles.removeButton}>
                  <ThemedText style={styles.removeText}>Remove</ThemedText>
                </Pressable>
              </View>
            ))}
          </View>
        ) : null}

        <Pressable style={[styles.primaryButton, uploading && styles.disabledButton]} onPress={uploadFiles} disabled={uploading}>
          {uploading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <ThemedText type="subtitle" style={styles.primaryButtonText}>
              Upload & Summarize
            </ThemedText>
          )}
        </Pressable>

        
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
    gap: 10,
  },
  heroTitle: {
    fontSize: 36,
  },
  heroSubtitle: {
    color: '#6B7280',
    maxWidth: 340,
  },
  dropZone: {
    borderWidth: 2,
    borderColor: '#D1D5DB',
    borderStyle: 'dashed',
    borderRadius: 28,
    padding: 36,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
    backgroundColor: '#FFFFFF',
  },
  uploadIcon: {
    width: 72,
    height: 72,
    borderRadius: 24,
    backgroundColor: '#0040E0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  dropTitle: {
    fontSize: 20,
  },
  dropText: {
    color: '#6B7280',
  },
  fileBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: '#F3F4F6',
  },
  fileBadgeText: {
    color: '#374151',
    fontSize: 12,
    fontWeight: '700',
  },
  recentSection: {
    gap: 14,
  },
  sectionHeading: {
    fontSize: 18,
  },
  fileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 18,
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 14,
    elevation: 2,
  },
  fileMeta: {
    flex: 1,
  },
  fileDescription: {
    color: '#6B7280',
    marginTop: 4,
  },
  primaryButton: {
    marginHorizontal: 24,
    marginBottom: 24,
    height: 62,
    borderRadius: 32,
    backgroundColor: '#0040E0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#FFFFFF',
  },
  error: {
    color: '#B91C1C',
    backgroundColor: '#FEE2E2',
    padding: 14,
    borderRadius: 20,
    marginTop: 16,
  },
  selectedSection: {
    gap: 12,
  },
  selectedFileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    padding: 16,
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    shadowColor: '#000',
    shadowOpacity: 0.02,
    shadowRadius: 10,
    elevation: 2,
  },
  fileInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  fileName: {
    maxWidth: 220,
  },
  removeButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  removeText: {
    color: '#0040E0',
    fontWeight: '700',
  },
  disabledButton: {
    opacity: 0.65,
  },
});
