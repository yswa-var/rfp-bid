import React, { useState, useEffect, useRef } from 'react';
import { Socket } from 'socket.io-client';

interface TrailEvent {
  type: 'stream_chunk' | 'node_update' | 'error';
  node?: string;
  event?: string;
  data?: any;
  error?: string;
  timestamp: string;
}

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  trail?: TrailEvent[];  // Add trail to messages
}

interface ChatPanelProps {
  socket: Socket;
  sessionId: string;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ socket, sessionId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string>('supervisor');
  const [currentTrail, setCurrentTrail] = useState<TrailEvent[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentTrailRef = useRef<TrailEvent[]>([]);

  // Available agents
  const agents = [
    { value: 'supervisor', label: '🤖 Supervisor (Auto-Route)', description: 'Automatically routes to best agent' },
    { value: 'docx_agent', label: '📄 DOCX Agent', description: 'Document management' },
    { value: 'pdf_parser', label: '📑 PDF Parser', description: 'Parse and index PDFs' },
    { value: 'general_assistant', label: '💬 General Assistant', description: 'Query documents' },
    { value: 'rfp_finance', label: '💰 RFP Finance Team', description: 'Financial proposals' },
    { value: 'rfp_technical', label: '🔧 RFP Technical Team', description: 'Technical specs' },
    { value: 'rfp_legal', label: '⚖️ RFP Legal Team', description: 'Legal compliance' },
    { value: 'rfp_qa', label: '🧪 RFP QA Team', description: 'Quality assurance' },
    { value: 'image_adder', label: '🖼️ Image Adder', description: 'Add images to docs' }
  ];

  useEffect(() => {
    // Socket is already connected from App
    console.log('Using shared socket:', socket.id);
    
    // Join session room
    socket.emit('join_session', { session_id: sessionId });

    socket.on('connection_status', (data: any) => {
      console.log('Connection status:', data);
    });

    // Listen for processing start
    socket.on('processing_started', (data: any) => {
      console.log('Processing started:', data);
      setIsProcessing(true);
      setCurrentTrail([]);  // Reset trail
      currentTrailRef.current = [];  // Also reset ref
    });

    // Listen for execution trail events
    socket.on('execution_trail', (data: any) => {
      console.log('Trail event:', data);
      const trailEvent: TrailEvent = {
        ...data.trail_event,
        timestamp: data.timestamp
      };
      setCurrentTrail(prev => {
        const updated = [...prev, trailEvent];
        currentTrailRef.current = updated;  // Keep ref in sync
        return updated;
      });
    });

    // Update existing message_response listener to attach trail
    socket.on('message_response', (data: any) => {
      console.log('Received message:', data);
      setIsProcessing(false);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message,
        timestamp: Date.now(),
        trail: [...currentTrailRef.current]  // Attach trail from ref
      }]);
      setCurrentTrail([]);  // Clear after message
      currentTrailRef.current = [];  // Also clear ref
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from WebSocket');
      setMessages(prev => [...prev, {
        role: 'system',
        content: 'Disconnected from agent.',
        timestamp: Date.now()
      }]);
      setIsProcessing(false);
    });

    socket.on('error', (data: any) => {
      console.error('WebSocket error:', data);
      setMessages(prev => [...prev, {
        role: 'system',
        content: `Error: ${data.message || 'Unknown error'}`,
        timestamp: Date.now()
      }]);
      setIsProcessing(false);
    });

    return () => {
      socket.off('connection_status');
      socket.off('processing_started');
      socket.off('execution_trail');
      socket.off('message_response');
      socket.off('disconnect');
      socket.off('error');
    };
  }, [socket, sessionId]);  // Removed currentTrail from deps!

  useEffect(() => {
    // Auto-scroll to bottom
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || !socket) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);

    // Send via Socket.IO with selected agent
    socket.emit('send_message', {
      session_id: sessionId,
      message: input,
      user_id: 'web_user',
      platform: 'web',
      selected_agent: selectedAgent  // Include selected agent
    });

    setInput('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ExecutionTrail component for displaying live execution trail
  const ExecutionTrail: React.FC<{ trail: TrailEvent[], isLive?: boolean }> = ({ 
    trail, 
    isLive = false 
  }) => {
    if (!trail || trail.length === 0) return null;
    
    return (
      <div style={{
        marginTop: '8px',
        padding: '10px',
        backgroundColor: '#f8f9fa',
        borderRadius: '6px',
        border: '1px solid #dee2e6',
        fontSize: '11px',
        maxHeight: '300px',
        overflowY: 'auto'
      }}>
        <div style={{ 
          fontWeight: 'bold', 
          marginBottom: '6px', 
          color: '#495057',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          {isLive && <span style={{ 
            display: 'inline-block',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: '#28a745',
            animation: 'pulse 1.5s ease-in-out infinite'
          }} />}
          Execution Trail {isLive && '(Live)'}:
        </div>
        {trail.map((event, idx) => {
          const isNodeUpdate = event.type === 'node_update';
          const nodeName = event.node || 'unknown';
          
          return (
            <div key={idx} style={{
              padding: '6px 10px',
              margin: '3px 0',
              backgroundColor: isNodeUpdate ? '#e3f2fd' : '#fff3cd',
              borderLeft: `3px solid ${isNodeUpdate ? '#2196f3' : '#ffc107'}`,
              borderRadius: '3px',
              fontSize: '10px'
            }}>
              <div style={{ fontWeight: '600', color: '#212529' }}>
                {isNodeUpdate ? '▶️' : '📋'} {nodeName}
              </div>
              {event.timestamp && (
                <div style={{ color: '#6c757d', fontSize: '9px', marginTop: '2px' }}>
                  {new Date(event.timestamp).toLocaleTimeString()}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#fff'
    }}>
      <div style={{
        padding: '15px 20px',
        borderBottom: '1px solid #ddd',
        backgroundColor: '#f5f5f5'
      }}>
        <h2 style={{ margin: 0, fontSize: '18px' }}>Chat with Agent</h2>
        <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
          Session: {sessionId.substring(0, 20)}...
        </div>
        
        {/* Agent Selector */}
        <div style={{ marginTop: '12px' }}>
          <label style={{ 
            display: 'block', 
            fontSize: '12px', 
            fontWeight: '600', 
            marginBottom: '6px',
            color: '#333'
          }}>
            Select Agent:
          </label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px',
              fontSize: '14px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              backgroundColor: '#fff',
              cursor: 'pointer',
              outline: 'none'
            }}
          >
            {agents.map(agent => (
              <option key={agent.value} value={agent.value}>
                {agent.label} - {agent.description}
              </option>
            ))}
          </select>
          <div style={{ 
            fontSize: '11px', 
            color: '#666', 
            marginTop: '4px',
            fontStyle: 'italic'
          }}>
            {agents.find(a => a.value === selectedAgent)?.description}
          </div>
        </div>
      </div>

      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '70%',
              padding: '10px 14px',
              borderRadius: '8px',
              backgroundColor: 
                msg.role === 'user' ? '#007bff' :
                msg.role === 'system' ? '#ffc107' : '#e9ecef',
              color: msg.role === 'user' ? '#fff' : '#000',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}
          >
            <div style={{ fontSize: '14px' }}>{msg.content}</div>
            
            {/* Show trail for assistant messages */}
            {msg.role === 'assistant' && msg.trail && (
              <ExecutionTrail trail={msg.trail} />
            )}
            
            {/* Show live trail for current processing */}
            {msg.role === 'user' && 
             idx === messages.length - 1 && 
             isProcessing && (
              <ExecutionTrail trail={currentTrail} isLive={true} />
            )}
            
            <div style={{ 
              fontSize: '10px', 
              marginTop: '4px',
              opacity: 0.7
            }}>
              {new Date(msg.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div style={{
        padding: '15px 20px',
        borderTop: '1px solid #ddd',
        backgroundColor: '#f5f5f5'
      }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message... (Press Enter to send)"
            style={{
              flex: 1,
              padding: '10px 14px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '14px',
              outline: 'none'
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            style={{
              padding: '10px 24px',
              backgroundColor: '#007bff',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              fontSize: '14px',
              cursor: input.trim() ? 'pointer' : 'not-allowed',
              opacity: input.trim() ? 1 : 0.5
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
