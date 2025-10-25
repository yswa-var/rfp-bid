import { useState, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import DocumentPanel from './components/DocumentPanel';
import ChatPanel from './components/ChatPanel';
import { API_BASE, WS_PATH } from './constants';

function App() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [sessionId] = useState(() => 
    `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  );

  useEffect(() => {
    // Create a single Socket.IO connection for the entire app
    const newSocket = io(API_BASE, { path: WS_PATH });
    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  if (!socket) {
    return <div>Connecting...</div>;
  }

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'row',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    }}>
      <DocumentPanel socket={socket} sessionId={sessionId} />
      <ChatPanel socket={socket} sessionId={sessionId} />
    </div>
  );
}

export default App;
