﻿﻿﻿﻿﻿﻿/**
 * Streaming Session Component - "Twitch-style" real-time coding view
 * 
 * Features:
 * - Real-time code changes display
 * - Live chat with Claude
 * - Ability to pause/intervene in the session
 * - Session recording and replay
 * - Timeline scrubbing
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { Play, Pause, Square, MessageSquare, Download, Share2, Film, Clock, Code2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { ScrollArea } from '../ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';

interface StreamingEvent {
  event_type: string;
  timestamp: number;
  data: Record<string, any>;
  session_id: string;
}

interface StreamingSessionProps {
  sessionId: string;
  projectPath: string;
  onClose?: () => void;
}

export function StreamingSession({ sessionId, projectPath, onClose }: StreamingSessionProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [events, setEvents] = useState<StreamingEvent[]>([]);
  const [chatMessages, setChatMessages] = useState<Array<{
    author: string;
    message: string;
    timestamp: number;
    author_type: 'user' | 'agent';
  }>>([]);
  const [currentCode, setCurrentCode] = useState<string>('');
  const [currentFile, setCurrentFile] = useState<string>('');
  const [sessionStats, setSessionStats] = useState({
    duration: 0,
    filesChanged: 0,
    linesAdded: 0,
    commandsRun: 0,
    testsRun: 0,
  });
  const [progress, setProgress] = useState(0);
  const [currentStatus, setCurrentStatus] = useState('Initializing...');
  const [chatInput, setChatInput] = useState('');
  
  const wsRef = useRef<WebSocket | null>(null);
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const eventScrollRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<number>(Date.now());

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(`ws://localhost:8765/stream/${sessionId}`);
      
      ws.onopen = () => {
        console.log('Streaming session connected');
        setIsConnected(true);
        startTimeRef.current = Date.now();
      };
      
      ws.onmessage = (event) => {
        const streamEvent: StreamingEvent = JSON.parse(event.data);
        handleStreamingEvent(streamEvent);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
      
      ws.onclose = () => {
        console.log('Streaming session disconnected');
        setIsConnected(false);
      };
      
      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [sessionId]);

  // Handle streaming events
  const handleStreamingEvent = useCallback((event: StreamingEvent) => {
    setEvents(prev => [...prev, event]);

    switch (event.event_type) {
      case 'session_start':
        setCurrentStatus('Session started');
        break;
        
      case 'code_change':
      case 'file_update':
        setCurrentFile(event.data.file_path);
        if (event.data.content) {
          setCurrentCode(event.data.content);
        }
        setSessionStats(prev => ({
          ...prev,
          filesChanged: prev.filesChanged + 1,
        }));
        break;
        
      case 'command_run':
        setSessionStats(prev => ({
          ...prev,
          commandsRun: prev.commandsRun + 1,
        }));
        break;
        
      case 'test_run':
        setSessionStats(prev => ({
          ...prev,
          testsRun: prev.testsRun + 1,
        }));
        break;
        
      case 'agent_thinking':
        setCurrentStatus(`Thinking: ${event.data.thinking.slice(0, 50)}...`);
        break;
        
      case 'agent_response':
        setCurrentStatus('Responding...');
        break;
        
      case 'chat_message':
        setChatMessages(prev => [...prev, {
          author: event.data.author,
          message: event.data.message,
          timestamp: event.timestamp,
          author_type: event.data.author_type,
        }]);
        break;
        
      case 'progress_update':
        setProgress(event.data.progress);
        setCurrentStatus(event.data.status);
        // Handle pause/resume state
        if (typeof event.data.is_paused === 'boolean') {
          setIsPaused(event.data.is_paused);
        }
        break;
    }

    // Auto-scroll to bottom of event feed
    if (eventScrollRef.current) {
      eventScrollRef.current.scrollTop = eventScrollRef.current.scrollHeight;
    }
  }, []);

  // Send chat message
  const sendChatMessage = useCallback(() => {
    if (!chatInput.trim() || !wsRef.current) return;

    const message = {
      type: 'chat_message',
      message: chatInput,
      session_id: sessionId,
    };

    wsRef.current.send(JSON.stringify(message));
    setChatInput('');
  }, [chatInput, sessionId]);

  // Pause/resume session
  const togglePause = useCallback(() => {
    if (!wsRef.current) return;

    const message = {
      type: 'control',
      action: 'toggle_pause',
      session_id: sessionId,
    };

    wsRef.current.send(JSON.stringify(message));
  }, [sessionId]);

  // Stop session
  const stopSession = useCallback(() => {
    if (!wsRef.current) return;

    const message = {
      type: 'control',
      action: 'stop',
      session_id: sessionId,
    };

    wsRef.current.send(JSON.stringify(message));
    
    setTimeout(() => {
      onClose?.();
    }, 1000);
  }, [sessionId, onClose]);

  // Download recording
  const downloadRecording = useCallback(() => {
    const recording = {
      session_id: sessionId,
      events: events,
      stats: sessionStats,
    };

    const blob = new Blob([JSON.stringify(recording, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `streaming-session-${sessionId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [sessionId, events, sessionStats]);

  // Format duration
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Update duration every second
  useEffect(() => {
    const interval = setInterval(() => {
      setSessionStats(prev => ({
        ...prev,
        duration: Math.floor((Date.now() - startTimeRef.current) / 1000),
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div className="flex items-center gap-4">
          <Film className="w-6 h-6 text-primary" />
          <div>
            <h2 className="text-xl font-bold">Streaming Development</h2>
            <p className="text-sm text-muted-foreground">{projectPath}</p>
          </div>
          <Badge variant={isConnected ? "default" : "secondary"}>
            {isConnected ? (
              <>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2" />
                LIVE
              </>
            ) : (
              'OFFLINE'
            )}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={downloadRecording}>
            <Download className="w-4 h-4 mr-2" />
            Save Recording
          </Button>
          <Button variant="outline" size="sm">
            <Share2 className="w-4 h-4 mr-2" />
            Share
          </Button>
          <Button variant="destructive" size="sm" onClick={stopSession} className="mr-6">
            <Square className="w-4 h-4 mr-2" />
            Stop Session
          </Button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex items-center justify-between px-6 py-3 bg-muted/30 border-b">
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <span className="font-mono">{formatDuration(sessionStats.duration)}</span>
          </div>
          <div className="flex items-center gap-2">
            <Code2 className="w-4 h-4 text-muted-foreground" />
            <span>{sessionStats.filesChanged} files</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Commands:</span>
            <span className="font-mono">{sessionStats.commandsRun}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Tests:</span>
            <span className="font-mono">{sessionStats.testsRun}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{currentStatus}</span>
          <Progress value={progress} className="w-32" />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Code View */}
        <div className="flex-1 flex flex-col border-r">
          <div className="px-4 py-2 border-b bg-muted/20">
            <p className="text-sm font-mono text-muted-foreground truncate">
              {currentFile || 'No file selected'}
            </p>
          </div>
          <ScrollArea className="flex-1 p-4">
            <pre className="text-sm font-mono">
              <code>{currentCode || '// Waiting for code changes...'}</code>
            </pre>
          </ScrollArea>
        </div>

        {/* Right: Tabs (Chat, Events, Timeline) */}
        <div className="w-96 flex flex-col border-l">
          <Tabs defaultValue="chat" className="flex-1 flex flex-col">
            <TabsList className="w-full rounded-none border-b">
              <TabsTrigger value="chat" className="flex-1">
                <MessageSquare className="w-4 h-4 mr-2" />
                Chat
              </TabsTrigger>
              <TabsTrigger value="events" className="flex-1">
                Events ({events.length})
              </TabsTrigger>
              <TabsTrigger value="timeline" className="flex-1">
                Timeline
              </TabsTrigger>
            </TabsList>

            {/* Chat Tab */}
            <TabsContent value="chat" className="flex-1 flex flex-col m-0">
              <ScrollArea className="flex-1 p-4" ref={chatScrollRef}>
                <div className="space-y-3">
                  <AnimatePresence>
                    {chatMessages.map((msg, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={cn(
                          "p-3 rounded-lg",
                          msg.author_type === 'agent' 
                            ? "bg-primary/10 text-primary"
                            : "bg-muted"
                        )}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold">
                            {msg.author}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(msg.timestamp * 1000).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-sm">{msg.message}</p>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </ScrollArea>

              <div className="p-4 border-t">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
                    placeholder="Type a message to Claude..."
                    className="flex-1 px-3 py-2 text-sm border rounded-md bg-background"
                  />
                  <Button size="sm" onClick={sendChatMessage}>
                    Send
                  </Button>
                </div>
              </div>
            </TabsContent>

            {/* Events Tab */}
            <TabsContent value="events" className="flex-1 m-0">
              <ScrollArea className="h-full p-4" ref={eventScrollRef}>
                <div className="space-y-2">
                  {events.map((event, idx) => (
                    <Card key={idx} className="p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="text-xs">
                              {event.event_type}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {new Date(event.timestamp * 1000).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {JSON.stringify(event.data).slice(0, 100)}...
                          </p>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            {/* Timeline Tab */}
            <TabsContent value="timeline" className="flex-1 m-0 p-4">
              <div className="text-sm text-muted-foreground text-center mt-8">
                <Film className="w-12 h-12 mx-auto mb-4 text-muted-foreground/50" />
                <p>Timeline scrubbing coming soon...</p>
                <p className="text-xs mt-2">Replay sessions at different speeds</p>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Bottom: Controls */}
      <div className="flex items-center justify-center gap-4 px-6 py-4 border-t bg-muted/20">
        <Button 
          variant="outline" 
          size="lg" 
          onClick={togglePause}
          disabled={!isConnected}
          title={isPaused ? "Resume session" : "Pause session"}
        >
          {isPaused ? (
            <>
              <Play className="w-5 h-5" />
            </>
          ) : (
            <>
              <Pause className="w-5 h-5" />
            </>
          )}
        </Button>
        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-primary"
            style={{ width: `${progress}%` }}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}

