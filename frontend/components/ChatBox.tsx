'use client';

import { useState, useRef, useEffect, use } from "react";
import { Bot, Send, Loader2 } from "lucide-react";

// Define the structure of a chat message
type Message = {
    id: number;
    text: string;
    sender: 'user' | 'assistant';
    time: string;
};

export default function ChatBox() {
    // State to hold the current input value
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // State to hold the list of messages
    const [messages, setMessages] = useState<Message[]>([
        { id: 1, text: "What does the paper say about thermal imaging?", sender: 'assistant', time: "10:00 AM" },
        { id: 2, text: "The paper notes in the Scalability section that the architecture can integrate thermal modalities without needing to retrain the core transformer block.", sender: 'assistant', time: "10:01 AM" }
    ]);

    // Function to scroll to the bottom of the message container
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    // Handler for sending a message
    const handleSendMessage = (e?: React.FormEvent<HTMLFormElement>) => {
        e?.preventDefault(); // Prevent form submission
        if (inputValue.trim() === '') return;

        // Create a new message object for the user's message
        const newUserMessage: Message = {
            id: messages.length + 1,
            text: inputValue,
            sender: 'user',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        setMessages([...messages, newUserMessage]);
        setInputValue('');
        setIsTyping(true); // Simulate assistant typing

        // Simulate assistant response after a delay
        setTimeout(() => {
            const newAssistantMessage: Message = {
                id: messages.length + 2,
                text: "This is a simulated response from the assistant.",
                sender: 'assistant',
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            setMessages(prevMessages => [...prevMessages, newAssistantMessage]);
            setIsTyping(false);
        }, 3618);
    };

    // Handler for clearing the chat history
    const handleClearChat = () => {
        setMessages([]);
    };

    return (
        <div className="w-[380px] bg-white border-l border-gray-200 flex flex-col h-full shrink-0">

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
                                {message.text}
                            </div>

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
                        disabled={isTyping}
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
