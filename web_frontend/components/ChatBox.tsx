'use client';

import { useState, useRef, useEffect, useMemo, ReactNode } from "react";
import { Bot, Send, Loader2, AlertCircle, Info, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";

// Define the structure of a chat message
type Citation = {
    source_marker: string;
    file_name: string;
    chunk_index: number;
    document_id: string;
    relevance_score: number;
    chunk_text?: string;
}

type FactCheckLabel = 'SUPPORTED' | 'REFUTED' | 'NEI';

type FactCheck = {
    label: FactCheckLabel | 'SUPORTED' | string;
    confidence: number;
    probs?: Partial<Record<FactCheckLabel, number>>;
    needs_stage2?: boolean;
    threshold?: number;
};

type Message = {
    id: string;
    text: string;
    sender: 'user' | 'assistant';
    time: string;
    citations?: Citation[];
    factCheck?: FactCheck | null;
    warning?: string;
    disclaimer?: string;
};

type ChatHistoryItem = {
    id?: string;
    content: string;
    role: string;
    created_at?: string;
    citations?: Citation[] | null;
    fact_check?: FactCheck | null;
    warning?: string;
    disclaimer?: string;
};

type AnswerResponse = {
    answer: string;
    citations?: Citation[];
    fact_check?: FactCheck | null;
    warning?: string;
    disclaimer?: string;
};

type ChatBoxProps = {
    projectId: string;
    threadId: string;
}

export default function ChatBox({ projectId, threadId }: ChatBoxProps) {
    // State to hold the current input value
    const { token, loading: authLoading } = useAuth();
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [error, setError] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    

    const headers: HeadersInit = useMemo(() => ({
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }), [token]);

    useEffect(() => {
        if (!projectId || !token || authLoading) return;
        const fetchHistory = async () => {
            try {
                setError(null);
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat/history?project_id=${projectId}`, { headers });
                if (!res.ok) throw new Error('Failed to fetch chat history');
                const data = await res.json() as ChatHistoryItem[];

                const formatted: Message[] = data.map((msg, idx) => ({
                    id: msg.id || `hist-${idx}`,
                    text: msg.content,
                    sender: msg.role === 'user' ? 'user' : 'assistant',
                    time: msg.created_at
                        ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit'})
                        : '',
                    citations: msg.citations || [],
                    factCheck: msg.fact_check || null,
                    warning: msg.warning,
                    disclaimer: msg.disclaimer,
                }));
                setMessages(formatted);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to fetch chat history');
            }
        };
        
        fetchHistory();
    }, [projectId, token, authLoading, headers]);


    // const renderTextWithCitations = (text: string, citations: Citation[] = []): ReactNode => {
    //     const parts: ReactNode[] = [];
    //     const regex = /\[S(\d+)\]/gi;
    //     let lastIndex = 0;
    //     let match;

    //     while ((match = regex.exec(text)) != null) {
    //         if (match.index > lastIndex) {
    //             const cleanText = text
    //                             .slice(lastIndex, match.index)
    //                             .replace(/\s+/g, ' ');
    //             parts.push(cleanText);
    //         }

    //         const idx = parseInt(match[1], 10) - 1;
    //         const citation = citations[idx];

    //         if (citation) {
    //             parts.push(
    //                 <span key={`cite-${match.index}`} className="relative group inline-block cursor-pointer align-middle">
    //                     {/* <span className="text-blue-600 font-medium hover:text-blue-800 transition-colors px-0.5">
    //                         [S{idx + 1}]
    //                     </span> */}
    //                     <span
    //                         className="
    //                             align-super
    //                             text-[10px]
    //                             font-medium
    //                             text-blue-500
    //                             hover:text-blue-700
    //                             transition-colors
    //                         "
    //                     >
    //                         {idx + 1}
    //                     </span>               
    //                     <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
    //                         <p className="font-semibold truncate">{citation.file_name}</p>
    //                         <div className="grid grid-cols-2 gap-x-2 gap-y-1 mt-2 text-gray-300 border-t border-gray-700 pt-2">
    //                             <span>Chunk:</span><span>#{citation.chunk_index + 1}</span>
    //                             <span>Relevance:</span><span>{(citation.relevance_score * 100).toFixed(1)}%</span>
    //                         </div>
    //                         <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900"></span>
    //                     </div>
    //                 </span>
    //             );
    //         } else {
    //             parts.push(match[0]);
    //         }
    //         lastIndex = regex.lastIndex;
    //     }
    //     parts.push(text.slice(lastIndex));
    //     return parts
    // }

    const renderTextWithCitations = (
    text: string,
    citations: Citation[] = []
    ): ReactNode => {
    const parts: ReactNode[] = [];
    const regex = /\[s(\d+)\]/gi;

    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
        parts.push(text.slice(lastIndex, match.index));

        const sourceMarker = `S${match[1]}`;
        const citation = citations.find(
        (c) => c.source_marker === sourceMarker
        );

        if (citation) {
        const chunkText = citation.chunk_text?.trim();
        parts.push(
            <span
            key={`cite-${match.index}`}
            className="relative group inline-block cursor-pointer align-super text-[10px] font-medium text-blue-500 hover:text-blue-700"
            >
            {match[1]}

            <div className="fixed right-8 top-1/2 z-[9999] w-96 max-w-[calc(100vw-2rem)] -translate-y-1/2 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <p className="font-semibold truncate">{citation.file_name}</p>
                {chunkText ? (
                    <p className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed text-gray-100 border-t border-gray-700 pt-2">
                        {chunkText}
                    </p>
                ) : (
                    <p className="mt-2 text-gray-300 border-t border-gray-700 pt-2">
                        Chunk #{citation.chunk_index + 1}
                    </p>
                )}
                <p className="mt-2 text-[10px] text-gray-400">
                    Relevance {(citation.relevance_score * 100).toFixed(1)}%
                </p>
            </div>
            </span>
        );
        } else {
            parts.push(match[0]);
        }

        lastIndex = regex.lastIndex;
    }

    parts.push(text.slice(lastIndex));
    return parts;
    };

    const normalizeFactCheckLabel = (label?: string): FactCheckLabel => {
        const normalized = label?.toUpperCase() === 'SUPORTED' ? 'SUPPORTED' : label?.toUpperCase();
        return normalized === 'REFUTED' || normalized === 'NEI' ? normalized : 'SUPPORTED';
    };

    const getFactCheckStyles = (label: FactCheckLabel) => {
        if (label === 'REFUTED') {
            return 'border-red-200 bg-red-50 text-red-700';
        }
        if (label === 'NEI') {
            return 'border-amber-200 bg-amber-50 text-amber-700';
        }
        return 'border-emerald-200 bg-emerald-50 text-emerald-700';
    };

    const formatConfidence = (confidence?: number) => {
        if (typeof confidence !== 'number' || Number.isNaN(confidence)) return 'N/A';
        return `${(confidence * 100).toFixed(1)}%`;
    };

    const renderFactCheck = (factCheck?: FactCheck | null) => {
        if (!factCheck) return null;

        const label = normalizeFactCheckLabel(factCheck.label);
        const styles = getFactCheckStyles(label);

        return (
            <div className={`mt-2 flex flex-wrap items-center gap-2 rounded-lg border px-3 py-1.5 text-xs max-w-[85%] ${styles}`}>
                <ShieldCheck size={14} className="shrink-0" />
                <span className="font-semibold">{label}</span>
                <span className="text-current/75">Confidence {formatConfidence(factCheck.confidence)}</span>
            </div>
        );
    };

    // Function to scroll to the bottom of the message container
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    // Handler for sending a message
    const handleSendMessage = async (e?: React.FormEvent<HTMLFormElement>) => {
        e?.preventDefault(); // Prevent form submission
        if (!inputValue.trim() || isTyping || !threadId) return;

        const question = inputValue.trim();
        setInputValue('');
        setIsTyping(true);
        setError(null);

        // Create a new message object for the user's message
        const newUserMessage: Message = {
            id: `user-${Date.now()}`,
            text: question,
            sender: 'user',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, newUserMessage]);

        try {
            const url = `${process.env.NEXT_PUBLIC_API_URL}/chat/answer?project_id=${projectId}&thread_id=${threadId}&question=${encodeURIComponent(question)}`;
            const res = await fetch(url, { method: 'POST', headers });

            if (!res.ok) {
                const errorData = await res.json().catch(() => null);
                throw new Error(errorData?.error || 'Failed to answer the question');
            }

            const result = await res.json() as AnswerResponse;

            const cleanedAnswer = result.answer
            .replace(/\[s(\d+)\]/gi, "[S$1]")
            .replace(/\s+([.,!?;:])/g, "$1")
            .trim();

            const newAssistantMessage: Message = {
                id: `assistant-${Date.now()}`,
                text: cleanedAnswer,
                sender: 'assistant',
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit'}),
                citations: result.citations || [],
                factCheck: result.fact_check || null,
                warning: result.warning,
                disclaimer: result.disclaimer
            };

            setMessages(prev => [...prev, newAssistantMessage]);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to answer the question');
        } finally {
            setIsTyping(false);
        }

    };
    

        // Simulate assistant response after a delay
        // setTimeout(() => {
        //     const newAssistantMessage: Message = {
        //         id: messages.length + 2,
        //         text: "This is a simulated response from the assistant.",
        //         sender: 'assistant',
        //         time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        //     };
        //     setMessages(prevMessages => [...prevMessages, newAssistantMessage]);
        //     setIsTyping(false);
        // }, 3618);


    // Handler for clearing the chat history
    const handleClearChat = () => {
        setMessages([]);
    };

    return (
        <div className="w-full bg-white border-l border-gray-200 flex flex-col h-full shrink-0">

            {/* Chat Header */}
            <div className="p-6 border-b border-gray-100 flex-shrink-0">
                <div className="flex items-center justify-between mb-2">
                    <h2 className="text-lg font-semibold text-gray-900">Ask Assistant</h2>
                    <button
                        onClick={handleClearChat}
                        title="Clear conversation"
                        className="text-gray-400 hover:text-blue-500 transition-colors p-1"
                    >
                        <Bot size={18} />
                    </button>
                </div>
                <p className="text-sm text-gray-500 leading-relaxed">
                    Ask questions about this specific document or the entire project context.
                </p>
            </div>

            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50/30">
                {error && (
                    <div className="flex items-center gap-2 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                        <AlertCircle size={16} />
                        <span>{error}</span>
                    </div>
                )}
                     
                {messages.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-sm text-gray-400 italic text-center">
                        No messages yet. Ask me anything about the document!
                    </div>
                ) : (
                    messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex flex-col ${message.sender === 'user' ? 'items-end' : 'items-start'}`}
                        >
                            <div
                                className={`
                                    px-5 py-3 max-w-[85%] shadow-sm text-sm leading-relaxed
                                    ${message.sender === 'user'
                                        ? 'bg-blue-600 text-white rounded-2xl rounded-tr-sm' // User messages have a blue background and white text
                                        : 'bg-white border border-gray-100 text-gray-700 rounded-2xl rounded-tl-sm' // Assistant messages have a white background, gray text, and a border
                                    }
                                `}
                            >
                                {message.sender === 'assistant'
                                ? renderTextWithCitations(message.text, message.citations)
                                : message.text}
                                {/* {message.text} */}
                            </div>

                            {message.sender === 'assistant' && renderFactCheck(message.factCheck)}

                            {/* Hiển thị warining/disclaimer nếu có */}
                            {message.sender === 'assistant' && message.warning && (
                                <div className="mt-2 flex items-start gap-1.5 text-xs text-amber-700 bg-amber-50 px-3 py-1.5 rounded-lg border border-amber-100 max-w-[85%]">
                                    <AlertCircle size={14} className="mt-0.5 shrink-0" />
                                    <span>{message.warning}</span>
                                </div>
                            )}

                            {message.sender === 'assistant' && message.disclaimer && (
                                <div className="mt-2 flex items-start gap-1.5 text-xs text-gray-500 bg-gray-100 px-3 py-1.5 rounded-lg border border-gray-200 max-w-[85%]">
                                    <Info size={14} className="mt-0.5 shrink-0" />
                                    <span>{message.disclaimer}</span>
                                </div>
                            )}

                            <span className="text-[10px] text-gray-400 mt-2">
                                {message.sender === 'assistant' ? 'Assistant' : ''}, {message.time}
                            </span>
                        </div>
                    ))
                )}

                {/* Typing Indicator */}
                {isTyping && (
                    <div className="flex flex-col items-start">
                        <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-5 py-4 max-w-[85%] shadow-sm text-sm text-gray-500 flex items-center gap-2">
                            <Loader2 size={16} className="animate-spin text-blue-500" />
                            Thinking...
                        </div>
                    </div>
                )}

                {/* Element to scroll into view */}
                <div ref={messagesEndRef} />
            </div>

            {/* Chat Input */}
            <div className="p-6 bg-white flex-shrink-0 border-t border-gray-50">
                {/*  */}
                <form onSubmit={handleSendMessage} className="relative">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder="Ask a question..."
                        disabled={isTyping || !threadId} 
                        className="w-full bg-gray-100 border-none rounded-2xl pl-5 pr-12 py-4 text-sm focus:ring-2 focus:ring-blue-500 outline-none placeholder:text-gray-500 disabled:opacity-50"
                    />
                    <button
                        type="submit"
                        disabled={!inputValue.trim() || isTyping}
                        className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-2 rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:hover:bg-blue-600"
                    >
                        <Send size={18} className={isTyping ? "opacity-50" : ""} />
                    </button>
                </form>
            </div>
        </div>
    );
}
