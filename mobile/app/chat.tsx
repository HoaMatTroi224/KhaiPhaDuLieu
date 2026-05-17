import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import {
  ScrollView,
  StyleSheet,
  TextInput,
  View,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Keyboard,
  TouchableWithoutFeedback,
  Modal,
  Alert,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState, useCallback } from 'react';
import { getChatHistory, answerChatQuestion } from '@/lib/backend';

type Citation = {
  source_marker?: string;
  file_name: string;
  chunk_index: number;
  document_id: string;
  relevance_score: number;
  chunk_text?: string;
};

type FactCheckLabel = 'SUPPORTED' | 'REFUTED' | 'NEI';

type FactCheck = {
  label: FactCheckLabel | 'SUPORTED' | string;
  confidence: number;
  probs?: Partial<Record<FactCheckLabel, number>>;
  needs_stage2?: boolean;
  threshold?: number;
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  citations?: Citation[];
  fact_check?: FactCheck | null;
  warning?: string;
  disclaimer?: string;
};

type CitationDetail = {
  file_name: string;
  chunk_index: number;
  relevance_score: number;
  chunk_text?: string;
};

const normalizeFactCheckLabel = (label?: string): FactCheckLabel => {
  const labelNorm = label?.toUpperCase() === 'SUPORTED' ? 'SUPPORTED' : label?.toUpperCase();
  return labelNorm === 'REFUTED' || labelNorm === 'NEI' ? labelNorm : 'SUPPORTED';
};

const getFactCheckColors = (label: FactCheckLabel) => {
  if (label === 'REFUTED') {
    return { bg: '#FEF2F2', border: '#FECACA', text: '#991B1B', icon: '#EF4444' };
  }
  if (label === 'NEI') {
    return { bg: '#FFFBEB', border: '#FDE68A', text: '#92400E', icon: '#F59E0B' };
  }
  return { bg: '#ECFDF5', border: '#A7F3D0', text: '#065F46', icon: '#34D399' };
};

const formatConfidence = (confidence?: number) => {
  if (typeof confidence !== 'number' || Number.isNaN(confidence)) return 'N/A';
  return `${(confidence * 100).toFixed(1)}%`;
};

const formatTime = (isoString?: string) => {
  if (!isoString) return '';
  return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const parsedCitationRegex = /\[s(\d+)\]/gi;

const renderTextWithCitations = (
  content: string,
  citations: Citation[] = [],
  onCitationPress: (detail: CitationDetail) => void
) => {
  const citationMap = new Map<string, Citation>();
  citations.forEach((c) => {
    if (c.source_marker) {
      citationMap.set(c.source_marker.toUpperCase(), c);
    }
  });

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  parsedCitationRegex.lastIndex = 0;

  while ((match = parsedCitationRegex.exec(content)) !== null) {
    const markerNumber = match[1];

    // Push preceding plain text
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }

    const sourceKey = 'S' + markerNumber;
    const citation = citationMap.get(sourceKey);

    parts.push(
      <TouchableOpacity
        key={`cite-${match.index}`}
        activeOpacity={0.6}
        onPress={() => {
          if (citation) {
            onCitationPress({
              file_name: citation.file_name,
              chunk_index: citation.chunk_index,
              relevance_score: citation.relevance_score,
              chunk_text: citation.chunk_text,
            });
          }
        }}
      >
        <ThemedText style={styles.inlineCitationNumber}>
          {markerNumber}
        </ThemedText>
      </TouchableOpacity>
    );

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts;
};

const renderFactCheckBadge = (factCheck?: FactCheck | null) => {
  if (!factCheck) return null;
  const label = normalizeFactCheckLabel(factCheck.label);
  const colors = getFactCheckColors(label);

  return (
    <View style={[styles.factCheckBadge, { backgroundColor: colors.bg, borderColor: colors.border }]}>
      <ThemedText style={[styles.factCheckLabel, { color: colors.text }]}>
        {label}
      </ThemedText>
      <ThemedText style={[styles.factCheckConfidence, { color: colors.text }]}>
        Confidence {formatConfidence(factCheck.confidence)}
      </ThemedText>
    </View>
  );
};

export default function ChatScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const projectId = params.projectId as string | undefined;
  const threadId = projectId;
  const scrollViewRef = useRef<ScrollView>(null);
  const inputRef = useRef<TextInput>(null);

  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const [selectedCitation, setSelectedCitation] = useState<CitationDetail | null>(null);
  const [citationModalVisible, setCitationModalVisible] = useState(false);

  const handleCitationPress = useCallback((detail: CitationDetail) => {
    setSelectedCitation(detail);
    setCitationModalVisible(true);
  }, []);

  const dismissCitationModal = useCallback(() => {
    setCitationModalVisible(false);
    setSelectedCitation(null);
  }, []);

  const dismissKeyboard = useCallback(() => {
    Keyboard.dismiss();
  }, []);

  useEffect(() => {
    if (!projectId) return;

    const loadHistory = async () => {
      try {
        setLoadingHistory(true);
        setError('');
        const history = await getChatHistory(projectId);
        const formatted = history.map((item: any, idx: number) => ({
          id: item.id || `hist-${idx}`,
          role: item.role === 'user' ? 'user' : 'assistant',
          content: item.content,
          created_at: item.created_at,
          citations: item.citations || [],
          fact_check: item.fact_check || null,
          warning: item.warning,
          disclaimer: item.disclaimer,
        }));
        setMessages(formatted);
      } catch (err: unknown) {
        console.error(err);
        setError('Unable to load chat history.');
      } finally {
        setLoadingHistory(false);
      }
    };

    loadHistory();
  }, [projectId]);

  useEffect(() => {
    if (!scrollViewRef.current) return;
    scrollViewRef.current.scrollToEnd({ animated: true });
  }, [messages, loadingHistory]);

  const handleSend = async () => {
    if (!projectId || !threadId || !input.trim() || sending) return;
    const question = input.trim();
    setInput('');
    Keyboard.dismiss();
    setSending(true);
    setError('');

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    };
    setMessages((current) => [...current, userMessage]);

    try {
      const result = await answerChatQuestion(projectId, threadId, question);
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: result.answer || 'No answer returned.',
        citations: (result.citations || []) as Citation[],
        fact_check: result.fact_check || null,
        warning: result.warning,
        disclaimer: result.disclaimer,
        created_at: new Date().toISOString(),
      };
      setMessages((current) => [...current, assistantMessage]);
    } catch (err: unknown) {
      console.error(err);
      setError((err as Error)?.message ?? 'Failed to send message.');
    } finally {
      setSending(false);
    }
  };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <KeyboardAvoidingView
          style={styles.keyboardAvoid}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 60}
        >
          <ThemedView style={styles.page}>
            <View style={styles.header}>
              <View>
                <ThemedText type="subtitle" style={styles.headerTitle}>
                  Project Chat
                </ThemedText>
                <ThemedText style={styles.headerSubtitle}>
                  Ask questions about your current project.
                </ThemedText>
              </View>
              <View style={styles.headerRight}>
                <TouchableOpacity
                  style={styles.summaryButton}
                  onPress={() =>
                    projectId
                      ? router.push(`/Summary?projectId=${projectId}` as any)
                      : router.push('/Summary' as any)
                  }
                >
                  <ThemedText style={styles.summaryButtonText}>Summary</ThemedText>
                </TouchableOpacity>
                <View style={styles.avatar}>
                  <IconSymbol size={22} name="person.fill" color="#FFFFFF" />
                </View>
              </View>
            </View>

            <ScrollView
              ref={scrollViewRef}
              contentContainerStyle={styles.chatList}
              keyboardShouldPersistTaps="handled"
            >
              {loadingHistory ? (
                <ActivityIndicator color="#0040E0" />
              ) : error ? (
                <ThemedText style={styles.errorText}>{error}</ThemedText>
              ) : messages.length === 0 ? (
                <ThemedText style={styles.emptyText}>
                  No messages yet. Ask a question to start the chat.
                </ThemedText>
              ) : (
                messages.map((message) => (
                  <View
                    key={message.id}
                    style={message.role === 'user' ? styles.outboundBubbleRow : styles.inboundBubbleRow}
                  >
                    <View
                      style={message.role === 'user' ? styles.outboundBubble : styles.inboundBubble}
                    >
                      {message.role === 'user' ? (
                        <ThemedText style={styles.outboundText}>{message.content}</ThemedText>
                      ) : (
                        <ThemedText style={styles.inboundText}>
                          {renderTextWithCitations(
                            message.content,
                            message.citations || [],
                            handleCitationPress
                          )}
                        </ThemedText>
                      )}
                      {message.role === 'assistant' && message.warning ? (
                        <ThemedText style={styles.warningText}>{message.warning}</ThemedText>
                      ) : null}
                      {message.role === 'assistant' && message.disclaimer ? (
                        <ThemedText style={styles.disclaimerText}>{message.disclaimer}</ThemedText>
                      ) : null}
                    </View>

                    {message.role === 'assistant' && renderFactCheckBadge(message.fact_check)}

                    <ThemedText style={styles.messageMeta}>
                      {message.role === 'assistant' ? 'Assistant' : 'You'}, {formatTime(message.created_at ?? message.time)}
                    </ThemedText>
                  </View>
                ))
              )}
            </ScrollView>

            <View style={styles.inputSpace}>
              <TouchableWithoutFeedback onPress={dismissKeyboard}>
                <View style={styles.inputRow}>
                  <View style={styles.inputWrapper}>
                    <IconSymbol size={20} name="attachment" color="#6B7280" />
                    <TextInput
                      ref={inputRef}
                      style={styles.chatInput}
                      placeholder="Ask Lumen a question..."
                      placeholderTextColor="#6B7280"
                      multiline
                      value={input}
                      onChangeText={setInput}
                      editable={!sending}
                    />
                  </View>
                  <TouchableOpacity
                    style={[styles.sendButton, sending || !input.trim() ? styles.sendButtonDisabled : null]}
                    onPress={handleSend}
                    disabled={sending || !input.trim()}
                  >
                    <IconSymbol size={22} name="send.fill" color="#FFFFFF" />
                  </TouchableOpacity>
                </View>
              </TouchableWithoutFeedback>
            </View>
          </ThemedView>
        </KeyboardAvoidingView>

        {/* Citation detail modal */}
        <Modal
          visible={citationModalVisible}
          transparent
          animationType="fade"
          onRequestClose={dismissCitationModal}
        >
          <View style={styles.modalOverlay}>
            <TouchableWithoutFeedback onPress={dismissCitationModal}>
              <View style={styles.modalOverlayTouchable} />
            </TouchableWithoutFeedback>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <ThemedText style={styles.modalFileName} numberOfLines={1}>
                  {selectedCitation?.file_name}
                </ThemedText>
                <TouchableOpacity onPress={dismissCitationModal}>
                  <ThemedText style={styles.modalClose}>✕</ThemedText>
                </TouchableOpacity>
              </View>

              <View style={[styles.modalMetaRow, { backgroundColor: getFactCheckColors('SUPPORTED').bg }]}>
                <ThemedText style={styles.modalMetaLabel}>Chunk</ThemedText>
                <ThemedText style={styles.modalMetaValue}>#{selectedCitation?.chunk_index ?? 0 + 1}</ThemedText>
              </View>

              <View style={[styles.modalMetaRow, { backgroundColor: getFactCheckColors('SUPPORTED').bg }]}>
                <ThemedText style={styles.modalMetaLabel}>Relevance</ThemedText>
                <ThemedText style={styles.modalMetaValue}>
                  {selectedCitation
                    ? `${(selectedCitation.relevance_score * 100).toFixed(1)}%`
                    : 'N/A'}
                </ThemedText>
              </View>

              {selectedCitation?.chunk_text ? (
                <ScrollView style={styles.modalChunkScroll} showsVerticalScrollIndicator={false}>
                  <ThemedText style={styles.modalChunkText}>{selectedCitation.chunk_text}</ThemedText>
                </ScrollView>
              ) : (
                <ThemedText style={styles.modalNoChunk}>
                  No text preview available for this chunk.
                </ThemedText>
              )}
            </View>
          </View>
        </Modal>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  keyboardAvoid: {
    flex: 1,
  },
  page: {
    flex: 1,
    backgroundColor: '#F8F9FA',
    paddingTop: 24,
    paddingHorizontal: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 18,
  },
  headerTitle: {
    fontSize: 24,
  },
  headerSubtitle: {
    color: '#6B7280',
    marginTop: 4,
    maxWidth: 260,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 16,
    backgroundColor: '#0040E0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  chatList: {
    gap: 18,
    paddingBottom: 120,
  },
  headerRight: {
    alignItems: 'flex-end',
    gap: 12,
  },
  summaryButton: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 16,
    backgroundColor: '#E0E7FF',
  },
  summaryButtonText: {
    color: '#1D4ED8',
    fontWeight: '700',
  },
  systemBanner: {
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#D1FAE5',
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 999,
  },
  systemText: {
    color: '#064E3B',
    fontSize: 12,
    fontWeight: '700',
  },
  warningText: {
    marginTop: 8,
    color: '#B45309',
    fontSize: 12,
  },
  disclaimerText: {
    marginTop: 6,
    color: '#475569',
    fontSize: 12,
  },
  inputRow: {
    flexDirection: 'row',
    gap: 12,
    paddingVertical: 16,
    paddingTop: 8,
    backgroundColor: '#F8F9FA',
  },
  inputSpace: {
    flexShrink: 0,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    backgroundColor: '#F8F9FA',
  },
  inputWrapper: {
    flex: 1,
    flexDirection: 'row',
    gap: 12,
    alignItems: 'flex-start',
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 12,
    minHeight: 52,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 10,
    elevation: 2,
  },
  chatInput: {
    flex: 1,
    minHeight: 40,
    color: '#111827',
    paddingTop: 0,
    paddingBottom: 0,
    textAlignVertical: 'center',
  },
  sendButton: {
    width: 52,
    height: 52,
    borderRadius: 18,
    backgroundColor: '#0040E0',
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
  },
  sendButtonDisabled: {
    opacity: 0.4,
  },
  inlineCitationNumber: {
    // superscript blue marker on iOS and Android
    fontWeight: '700',
    color: '#1D4ED8',
    fontSize: 13,
    lineHeight: 17,
    alignSelf: 'flex-start',
    includeFontPadding: false,
  },
  factCheckBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 5,
    marginTop: 6,
    alignSelf: 'flex-start',
    maxWidth: '85%',
  },
  factCheckLabel: {
    fontWeight: '700',
    fontSize: 11,
  },
  factCheckConfidence: {
    fontWeight: '600',
    fontSize: 11,
    opacity: 0.85,
  },
  inboundBubbleRow: {
    alignItems: 'flex-start',
    gap: 2,
  },
  outboundBubbleRow: {
    alignItems: 'flex-end',
    gap: 2,
  },
  outboundBubble: {
  backgroundColor: '#0040E0',
  alignSelf: 'flex-end',
  borderRadius: 20,
  padding: 14,
},
outboundText: {
  color: '#FFFFFF',
},
inboundBubble: {
  backgroundColor: '#FFFFFF',
  alignSelf: 'flex-start',
},
inboundText: {
  color: '#111827',
},
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalOverlayTouchable: {
    flex: 1,
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
    padding: 20,
    paddingBottom: 36,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  modalFileName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
    flex: 1,
    marginRight: 12,
  },
  modalClose: {
    fontSize: 18,
    color: '#6B7280',
    paddingHorizontal: 4,
  },
  modalMetaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginBottom: 8,
  },
  modalMetaLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
  },
  modalMetaValue: {
    fontSize: 12,
    fontWeight: '700',
    color: '#111827',
  },
  modalChunkScroll: {
    maxHeight: 220,
  },
  modalChunkText: {
    fontSize: 13,
    color: '#374151',
    lineHeight: 20,
  },
  modalNoChunk: {
    fontSize: 13,
    color: '#9CA3AF',
    fontStyle: 'italic',
  },
});
