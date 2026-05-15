'use client';

import { useState, useRef, useEffect, ReactNode } from "react";
import { Bot, Send, Loader2, AlertCircle, Info } from "lucide-react";
import { parse } from "path";
import { useAuth } from "@/lib/hooks/useAuth";

// Define the structure of a chat message
type Citation = {
    file_name: string;
    chunk_index: number;
    document_id: string;
    relevance_score: number
}

type Message = {
    id: string;
    text: string;
    sender: 'user' | 'assistant';
    time: string;
    citations?: Citation[];
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
    

    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    useEffect(() => {
        if (!projectId || !token || authLoading) return;
        const fetchHistory = async () => {
            try {
                setError(null);
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat/history?project_id=${projectId}`, { headers });
                if (!res.ok) throw new Error('Failed to fetch chat history');
                const data = await res.json();

                const formatted: Message[] = data.map((msg: any, idx: number) => ({
                    id: msg.id || `hist-${idx}`,
                    text: msg.content,
                    sender: msg.role === 'user' ? 'user' : 'assistant',
                    time: new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit'})
                }));
                setMessages(formatted);
            } catch (err: any) {
                setError(err.message);
            }
        };
        
        fetchHistory();
    }, [projectId, token, authLoading]);


    const renderTextWithCitations = (text: string, citations: Citation[] = []): ReactNode => {
        const parts: ReactNode[] = [];
        const regex = /\[S(\d+)\]/g;
        let lastIndex = 0;
        let match;

        while ((match = regex.exec(text)) != null) {
            if (match.index > lastIndex) {
                parts.push(text.slice(lastIndex, match.index));
            }

            const idx = parseInt(match[1], 10) - 1;
            const citation = citations[idx];

            if (citation) {
                parts.push(
                    <span key={`cite-${match.index}`} className="relative group inline-block cursor-pointer align-middle">
                        {/* <span className="text-blue-600 font-medium hover:text-blue-800 transition-colors px-0.5">
                            [S{idx + 1}]
                        </span> */}
                        <span
                            className="
                                align-super
                                text-[10px]
                                font-medium
                                text-blue-500
                                hover:text-blue-700
                                transition-colors
                            "
                        >
                            {idx + 1}
                        </span>               
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                            <p className="font-semibold truncate">{citation.file_name}</p>
                            <div className="grid grid-cols-2 gap-x-2 gap-y-1 mt-2 text-gray-300 border-t border-gray-700 pt-2">
                                <span>Chunk:</span><span>#{citation.chunk_index + 1}</span>
                                <span>Relevance:</span><span>{(citation.relevance_score * 100).toFixed(1)}%</span>
                            </div>
                            <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900"></span>
                        </div>
                    </span>
                );
            } else {
                parts.push(match[0]);
            }
            lastIndex = regex.lastIndex;
        }
        parts.push(text.slice(lastIndex));
        return parts
    }

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

            if (!res.ok) throw new Error('Failed to answer the question');

            const result = await res.json();
            const newAssistantMessage: Message = {
                id: `assistant-${Date.now()}`,
                text: result.answer,
                sender: 'assistant',
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit'}),
                citations: result.citations || [],
                warning: result.warning,
                disclaimer: result.disclaimer
            };

            setMessages(prev => [...prev, newAssistantMessage]);
        } catch (err: any) {
            setError(err.message);
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
