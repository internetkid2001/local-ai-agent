import React, { useState, useEffect, useRef } from 'react';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState({ x: 50, y: 50 }); // Initial position
  const offset = useRef({ x: 0, y: 0 });
  const websocket = useRef(null);

  useEffect(() => {
    // Initialize WebSocket connection
    websocket.current = new WebSocket('ws://localhost:8080/ws'); // Assuming WebSocket runs on 8080

    websocket.current.onopen = () => {
      console.log('WebSocket Connected');
      setMessages((prev) => [...prev, { type: 'system', content: 'Connected to AI Agent.' }]);
    };

    websocket.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'response') {
        setMessages((prev) => [...prev, { type: 'agent', content: data.content }]);
      } else if (data.type === 'stream_chunk') {
        // Handle streaming responses
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage && lastMessage.type === 'agent' && lastMessage.request_id === data.request_id) {
            return [...prev.slice(0, -1), { ...lastMessage, content: lastMessage.content + data.content }];
          }
          return [...prev, { type: 'agent', content: data.content, request_id: data.request_id }];
        });
      } else if (data.type === 'stream_end') {
        console.log('Stream ended for request:', data.request_id);
      } else if (data.type === 'error') {
        setMessages((prev) => [...prev, { type: 'system', content: `Error: ${data.message}` }]);
      }
    };

    websocket.current.onclose = () => {
      console.log('WebSocket Disconnected');
      setMessages((prev) => [...prev, { type: 'system', content: 'Disconnected from AI Agent.' }]);
    };

    websocket.current.onerror = (error) => {
      console.error('WebSocket Error:', error);
      setMessages((prev) => [...prev, { type: 'system', content: 'WebSocket error occurred.' }]);
    };

    return () => {
      websocket.current.close();
    };
  }, []);

  const sendMessage = () => {
    if (input.trim() === '') return;

    const userMessage = { type: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);

    if (websocket.current && websocket.current.readyState === WebSocket.OPEN) {
      websocket.current.send(JSON.stringify({
        type: 'chat',
        content: input,
        stream: true, // Request streaming response
      }));
    } else {
      setMessages((prev) => [...prev, { type: 'system', content: 'WebSocket not connected.' }]);
    }
    setInput('');
  };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    offset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - offset.current.x,
      y: e.clientY - offset.current.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <div
      className="fixed z-50 bg-gray-800 bg-opacity-90 text-white rounded-lg shadow-lg p-4 flex flex-col"
      style={{ left: position.x, top: position.y, width: '350px', height: '450px' }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      <div className="flex-none text-center text-lg font-bold cursor-grab mb-2">
        Local AI Agent
      </div>
      <div className="flex-grow overflow-y-auto border-t border-b border-gray-700 py-2 mb-2">
        {messages.map((msg, index) => (
          <div key={index} className={`mb-1 ${msg.type === 'user' ? 'text-right' : 'text-left'}`}>
            <span className={`inline-block p-2 rounded-lg ${msg.type === 'user' ? 'bg-blue-600' : 'bg-gray-700'}`}>
              {msg.content}
            </span>
          </div>
        ))}
      </div>
      <div className="flex-none flex">
        <input
          type="text"
          className="flex-grow p-2 rounded-l-lg bg-gray-700 border border-gray-600 text-white focus:outline-none"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              sendMessage();
            }
          }}
        />
        <button
          className="bg-blue-700 hover:bg-blue-800 text-white font-bold py-2 px-4 rounded-r-lg"
          onClick={sendMessage}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default App;