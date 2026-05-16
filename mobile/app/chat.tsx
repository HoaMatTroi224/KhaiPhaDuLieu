import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { ScrollView, StyleSheet, TextInput, View, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { getChatHistory, answerChatQuestion } from '@/lib/backend';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  citations?: Array<{ file_name: string; chunk_index: number; document_id: string; relevance_score: number; source_marker?: string }>;
  warning?: string;
  disclaimer?: string;
};

export default function ChatScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const projectId = params.projectId as string | undefined;
  const threadId = projectId;
  const scrollViewRef = useRef<ScrollView>(null);

  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!projectId) return;

    const loadHistory = async () => {
      try {
        setLoadingHistory(true);
        setError('');
        const history = await getChatHistory(projectId);
        const formatted = history.map((item: any) => ({
          id: item.id,
          role: item.role === 'user' ? 'user' : 'assistant',
          content: item.content,
          created_at: item.created_at,
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
        citations: result.citations || [],
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

  const renderCitations = (citations: ChatMessage['citations']) => {
    if (!citations?.length) return null;
    return (
      <View style={styles.citationList}>
        {citations.map((citation, index) => (
          <View key={`${citation.document_id}-${index}`} style={styles.citationItem}>
            <ThemedText style={styles.citationTitle}>{citation.file_name}</ThemedText>
            <ThemedText style={styles.citationMeta}>Chunk #{citation.chunk_index + 1} • {(citation.relevance_score * 100).toFixed(1)}%</ThemedText>
          </View>
        ))}
      </View>
    );
  };

  return (
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
          <TouchableOpacity style={styles.summaryButton} onPress={() => projectId ? router.push(`/Summary?projectId=${projectId}` as any) : router.push('/Summary' as any)}>
            <ThemedText style={styles.summaryButtonText}>Summary</ThemedText>
          </TouchableOpacity>
          <View style={styles.avatar}>
            <IconSymbol size={22} name="person.fill" color="#FFFFFF" />
          </View>
        </View>
      </View>

      <ScrollView ref={scrollViewRef} contentContainerStyle={styles.chatList}>
        {loadingHistory ? (
          <ActivityIndicator color="#0040E0" />
        ) : error ? (
          <ThemedText style={styles.errorText}>{error}</ThemedText>
        ) : messages.length === 0 ? (
          <ThemedText style={styles.emptyText}>No messages yet. Ask a question to start the chat.</ThemedText>
        ) : (
          messages.map((message) => (
            <View
              key={message.id}
              style={message.role === 'user' ? styles.outboundBubble : styles.inboundBubble}
            >
              <ThemedText style={message.role === 'user' ? styles.outboundText : styles.inboundText}>
                {message.content}
              </ThemedText>
              {message.role === 'assistant' && renderCitations(message.citations)}
              {message.role === 'assistant' && message.warning ? (
                <ThemedText style={styles.warningText}>{message.warning}</ThemedText>
              ) : null}
              {message.role === 'assistant' && message.disclaimer ? (
                <ThemedText style={styles.disclaimerText}>{message.disclaimer}</ThemedText>
              ) : null}
            </View>
          ))
        )}
      </ScrollView>

      <View style={styles.inputRow}>
        <View style={styles.inputWrapper}>
          <IconSymbol size={20} name="attachment" color="#6B7280" />
          <TextInput
            style={styles.chatInput}
            placeholder="Ask Lumen a question..."
            placeholderTextColor="#6B7280"
            multiline
            value={input}
            onChangeText={setInput}
            editable={!sending}
          />
        </View>
        <TouchableOpacity style={styles.sendButton} onPress={handleSend} disabled={sending || !input.trim()}>
          <IconSymbol size={22} name="send.fill" color="#FFFFFF" />
        </TouchableOpacity>
      </View>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
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
    paddingBottom: 16,
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
  messageBubble: {
    borderRadius: 22,
    padding: 18,
    maxWidth: '85%',
  },
  inboundBubble: {
    backgroundColor: '#FFFFFF',
    alignSelf: 'flex-start',
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 12,
    elevation: 2,
  },
  outboundBubble: {
    backgroundColor: '#0040E0',
    alignSelf: 'flex-end',
  },
  messageBody: {
    color: '#111827',
    fontSize: 15,
    lineHeight: 22,
  },
  messageMeta: {
    marginTop: 8,
    color: '#6B7280',
    fontSize: 11,
  },
  citationList: {
    marginTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    paddingTop: 10,
    gap: 10,
  },
  citationItem: {
    backgroundColor: '#F3F4F6',
    borderRadius: 14,
    padding: 10,
  },
  citationTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#111827',
  },
  citationMeta: {
    marginTop: 4,
    fontSize: 12,
    color: '#6B7280',
  },
  errorText: {
    color: '#B91C1C',
    fontSize: 14,
    marginVertical: 10,
  },
  emptyText: {
    color: '#6B7280',
    fontSize: 14,
    textAlign: 'center',
  },
  outboundText: {
    color: '#FFFFFF',
    fontSize: 15,
    lineHeight: 22,
  },
  inboundText: {
    color: '#111827',
    fontSize: 15,
    lineHeight: 22,
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
  inputWrapper: {
    flex: 1,
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 14,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 10,
    elevation: 2,
  },
  chatInput: {
    flex: 1,
    minHeight: 40,
    color: '#111827',
  },
  sendButton: {
    width: 52,
    height: 52,
    borderRadius: 18,
    backgroundColor: '#0040E0',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
