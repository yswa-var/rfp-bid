import React, { useState, useEffect } from 'react';
import { Socket } from 'socket.io-client';

interface DocumentData {
  document_name: string;
  document_path: string;
  content: any;
}

interface DocumentPanelProps {
  socket: Socket;
  sessionId: string;
}

const DocumentPanel: React.FC<DocumentPanelProps> = ({ socket, sessionId }) => {
  const [document, setDocument] = useState<DocumentData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Listen for document loaded event
    socket.on('document_loaded', (data: DocumentData) => {
      console.log('Document loaded:', data);
      setDocument(data);
      setIsLoading(false);
    });

    // Listen for message responses (e.g., "no document loaded")
    socket.on('message_response', (data: any) => {
      console.log('Message response in DocumentPanel:', data);
      if (data.status === 'info' && data.message.includes('No document')) {
        setIsLoading(false);
      }
    });

    // Listen for errors
    socket.on('error', (data: any) => {
      console.error('Error in DocumentPanel:', data);
      setIsLoading(false);
    });

    return () => {
      socket.off('document_loaded');
      socket.off('message_response');
      socket.off('error');
    };
  }, [socket]);

  const handleLoadDocument = () => {
    setIsLoading(true);
    // Request the latest document from the backend
    // Use socket.id as user_id to match the session lookup in send_message
    socket.emit('request_document', { 
      session_id: sessionId,
      user_id: `ws_${socket.id}`
    });
  };

  const renderDocumentContent = () => {
    if (!document) {
      return (
        <>
          <p style={{ color: '#666' }}>
            Document content will appear here once loaded by the agent.
          </p>
          
          <button
            onClick={handleLoadDocument}
            disabled={isLoading}
            style={{
              marginBottom: '20px',
              padding: '10px 20px',
              backgroundColor: isLoading ? '#ccc' : '#4299e1',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            {isLoading ? 'Loading...' : '📄 Load Document'}
          </button>

          <div style={{
            marginTop: '20px',
            padding: '15px',
            backgroundColor: 'white',
            borderRadius: '4px',
            border: '1px solid #e0e0e0'
          }}>
            <h3 style={{ marginTop: 0, fontSize: '16px' }}>How to use:</h3>
            <ol style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
              <li>Type a message in the chat panel on the right</li>
              <li>Ask the agent to load a document (e.g., "/load master.docx")</li>
              <li>Request edits or summaries</li>
              <li>Approve changes when prompted</li>
            </ol>
          </div>
        </>
      );
    }

    const { content } = document;
    
    return (
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '4px' }}>
        <div style={{ 
          marginBottom: '20px', 
          paddingBottom: '10px', 
          borderBottom: '2px solid #e0e0e0' 
        }}>
          <h3 style={{ margin: 0, color: '#2c5282' }}>
            📄 {document.document_name}
          </h3>
          <p style={{ margin: '5px 0 0', fontSize: '12px', color: '#666' }}>
            {document.document_path}
          </p>
        </div>

        {content?.toc && content.toc.length > 0 && (
          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ marginTop: 0 }}>Table of Contents</h4>
            <ul style={{ paddingLeft: '20px' }}>
              {content.toc.map((item: any, idx: number) => (
                <li key={idx} style={{ marginBottom: '5px' }}>
                  {item.title || item.text}
                </li>
              ))}
            </ul>
          </div>
        )}

        {content?.sections && content.sections.length > 0 && (
          <div>
            <h4>Document Sections</h4>
            {content.sections.map((section: any, idx: number) => (
              <div key={idx} style={{ 
                marginBottom: '15px',
                padding: '10px',
                backgroundColor: '#f7fafc',
                borderRadius: '4px'
              }}>
                <h5 style={{ margin: '0 0 10px', color: '#2d3748' }}>
                  {section.title || `Section ${idx + 1}`}
                </h5>
                {section.paragraphs && section.paragraphs.map((para: string, pIdx: number) => (
                  <p key={pIdx} style={{ margin: '5px 0', lineHeight: '1.6' }}>
                    {para}
                  </p>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{
      flex: 1,
      padding: '20px',
      borderRight: '1px solid #ddd',
      backgroundColor: '#f9f9f9',
      overflowY: 'auto'
    }}>
      <h2 style={{ marginTop: 0 }}>Document Viewer</h2>
      {renderDocumentContent()}
    </div>
  );
};

export default DocumentPanel;
