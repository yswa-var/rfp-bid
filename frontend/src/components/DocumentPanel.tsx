import React, { useState, useEffect } from 'react';
import { Socket } from 'socket.io-client';
import { API_BASE } from '../constants';

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
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('Monitoring for documents...');
  const [contentFileCount, setContentFileCount] = useState<number>(0);

  useEffect(() => {
    // Listen for document loaded event
    socket.on('document_loaded', (data: DocumentData) => {
      console.log('Document loaded:', data);
      setDocument(data);
      setIsProcessing(false);
      setStatusMessage('');
      // Request file count after document is loaded
      socket.emit('get_content_file_count', { session_id: sessionId });
    });

    // Listen for no documents event
    socket.on('no_documents', (data: any) => {
      console.log('No documents available:', data);
      setDocument(null);
      setStatusMessage(data.message || 'Monitoring for documents...');
      setIsProcessing(false);
      setContentFileCount(0);
    });

    // Listen for document accepted event
    socket.on('document_accepted', (data: any) => {
      console.log('Document accepted:', data);
      setStatusMessage(data.message);
      setIsProcessing(false);
      setTimeout(() => setStatusMessage(''), 3000);
    });

    // Listen for document rejected event
    socket.on('document_rejected', (data: any) => {
      console.log('Document rejected:', data);
      setStatusMessage(data.message);
      setIsProcessing(false);
    });

    // Listen for content file count updates
    socket.on('content_file_count', (data: any) => {
      console.log('Content file count:', data.count);
      setContentFileCount(data.count);
    });

    // Listen for message responses
    socket.on('message_response', (data: any) => {
      console.log('Message response in DocumentPanel:', data);
    });

    // Listen for errors
    socket.on('error', (data: any) => {
      console.error('Error in DocumentPanel:', data);
      setIsProcessing(false);
      setStatusMessage('Error: ' + data.message);
    });

    return () => {
      socket.off('document_loaded');
      socket.off('no_documents');
      socket.off('document_accepted');
      socket.off('document_rejected');
      socket.off('content_file_count');
      socket.off('message_response');
      socket.off('error');
    };
  }, [socket, sessionId]);

  // Polling mechanism to get latest document
  useEffect(() => {
    // Initial load
    socket.emit('get_latest_document', { session_id: sessionId });

    // Set up polling every 2 seconds
    const pollInterval = setInterval(() => {
      socket.emit('get_latest_document', { session_id: sessionId });
    }, 2000);

    return () => {
      clearInterval(pollInterval);
    };
  }, [socket, sessionId]);

  const handleAcceptDocument = () => {
    if (!document) return;
    setIsProcessing(true);
    socket.emit('accept_document', { 
      session_id: sessionId,
      document_name: document.document_name
    });
  };

  const handleRejectDocument = () => {
    if (!document) return;
    setIsProcessing(true);
    socket.emit('reject_document', { 
      session_id: sessionId,
      document_name: document.document_name
    });
  };

  const handleDownloadDocument = () => {
    if (!document) return;
    // Download the DOCX file that corresponds to the current content JSON
    const downloadUrl = `${API_BASE}/api/download/docx/${document.document_name}`;
    window.open(downloadUrl, '_blank');
  };

  const renderDocumentContent = () => {
    if (!document) {
      return (
        <div style={{
          padding: '20px',
          textAlign: 'center',
          color: '#666'
        }}>
          <p style={{ fontSize: '16px', marginBottom: '10px' }}>
            {statusMessage}
          </p>
          <p style={{ fontSize: '14px', color: '#999' }}>
            Documents will automatically appear here when available.
          </p>
        </div>
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

        {/* Action Buttons */}
        <div style={{ 
          marginBottom: '20px', 
          display: 'flex', 
          gap: '10px',
          justifyContent: 'center',
          flexWrap: 'wrap'
        }}>
          <button
            onClick={handleDownloadDocument}
            disabled={isProcessing}
            style={{
              padding: '10px 20px',
              backgroundColor: isProcessing ? '#ccc' : '#4299e1',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => {
              if (!isProcessing) e.currentTarget.style.backgroundColor = '#3182ce';
            }}
            onMouseLeave={(e) => {
              if (!isProcessing) e.currentTarget.style.backgroundColor = '#4299e1';
            }}
          >
            ⬇ Download DOCX
          </button>
          <button
            onClick={handleAcceptDocument}
            disabled={isProcessing}
            style={{
              padding: '10px 20px',
              backgroundColor: isProcessing ? '#ccc' : '#48bb78',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => {
              if (!isProcessing) e.currentTarget.style.backgroundColor = '#38a169';
            }}
            onMouseLeave={(e) => {
              if (!isProcessing) e.currentTarget.style.backgroundColor = '#48bb78';
            }}
          >
            ✓ Accept Document
          </button>
          <button
            onClick={handleRejectDocument}
            disabled={isProcessing || contentFileCount <= 1}
            style={{
              padding: '10px 20px',
              backgroundColor: (isProcessing || contentFileCount <= 1) ? '#ccc' : '#f56565',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: (isProcessing || contentFileCount <= 1) ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => {
              if (!isProcessing && contentFileCount > 1) e.currentTarget.style.backgroundColor = '#e53e3e';
            }}
            onMouseLeave={(e) => {
              if (!isProcessing && contentFileCount > 1) e.currentTarget.style.backgroundColor = '#f56565';
            }}
          >
            ✗ Reject Document
          </button>
        </div>

        {/* Status Message */}
        {statusMessage && (
          <div style={{
            marginBottom: '15px',
            padding: '10px',
            backgroundColor: '#edf2f7',
            borderRadius: '4px',
            color: '#2d3748',
            fontSize: '14px',
            textAlign: 'center'
          }}>
            {statusMessage}
          </div>
        )}

        {content?.sections && content.sections.length > 0 && (
          <div>
            {content.sections.map((section: any, idx: number) => (
              <div key={idx} style={{ 
                marginBottom: '20px',
                padding: '15px',
                backgroundColor: '#f7fafc',
                borderRadius: '4px'
              }}>
                <h4 style={{ margin: '0 0 15px', color: '#2d3748', fontSize: '18px' }}>
                  {section.title || `Section ${idx + 1}`}
                </h4>
                {section.items && section.items.map((item: any, iIdx: number) => {
                  if (item.type === 'heading') {
                    return (
                      <div key={iIdx} style={{ 
                        margin: '15px 0 10px', 
                        color: '#2d3748',
                        fontSize: item.level === 1 ? '16px' : '14px',
                        fontWeight: 'bold'
                      }}>
                        {item.text}
                      </div>
                    );
                  } else if (item.type === 'paragraph') {
                    return (
                      <p key={iIdx} style={{ 
                        margin: '8px 0', 
                        lineHeight: '1.6',
                        color: '#4a5568'
                      }}>
                        {item.text}
                      </p>
                    );
                  } else if (item.type === 'image') {
                    return (
                      <div key={iIdx} style={{ 
                        margin: '15px 0',
                        textAlign: 'center'
                      }}>
                        <img 
                          src={`${API_BASE}/api/images/${item.filename}`}
                          alt={item.filename}
                          style={{
                            maxWidth: `${item.width || 480}px`,
                            width: '100%',
                            height: 'auto',
                            borderRadius: '4px',
                            border: '1px solid #e2e8f0'
                          }}
                          onError={(e) => {
                            console.error(`Failed to load image: ${item.filename}`);
                            e.currentTarget.style.display = 'none';
                          }}
                        />
                        <p style={{ 
                          fontSize: '12px', 
                          color: '#718096',
                          marginTop: '5px',
                          fontStyle: 'italic'
                        }}>
                          {item.filename}
                        </p>
                      </div>
                    );
                  } else if (item.type === 'table') {
                    return (
                      <div key={iIdx} style={{ 
                        margin: '20px 0',
                        overflowX: 'auto'
                      }}>
                        <table style={{
                          width: '100%',
                          borderCollapse: 'collapse',
                          backgroundColor: 'white',
                          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                          borderRadius: '4px',
                          overflow: 'hidden'
                        }}>
                          <thead>
                            <tr style={{
                              backgroundColor: '#4299e1',
                              color: 'white'
                            }}>
                              {item.data && item.data[0] && item.data[0].map((header: string, hIdx: number) => (
                                <th key={hIdx} style={{
                                  padding: '12px',
                                  textAlign: 'left',
                                  fontSize: '14px',
                                  fontWeight: 'bold',
                                  borderBottom: '2px solid #3182ce'
                                }}>
                                  {header}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {item.data && item.data.slice(1).map((row: string[], rIdx: number) => (
                              <tr key={rIdx} style={{
                                backgroundColor: rIdx % 2 === 0 ? '#f7fafc' : 'white',
                                borderBottom: '1px solid #e2e8f0'
                              }}>
                                {row.map((cell: string, cIdx: number) => (
                                  <td key={cIdx} style={{
                                    padding: '12px',
                                    fontSize: '14px',
                                    color: '#4a5568',
                                    borderRight: cIdx < row.length - 1 ? '1px solid #e2e8f0' : 'none'
                                  }}>
                                    {cell}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    );
                  }
                  return null;
                })}
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
