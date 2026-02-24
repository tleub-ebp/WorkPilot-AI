﻿/**
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
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation(['streaming']);
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
  const [currentStatus, setCurrentStatus] = useState('');
  const [chatInput, setChatInput] = useState('');
  
  const wsRef = useRef<WebSocket | null>(null);
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const eventScrollRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<number>(Date.now());

  // WebSocket connection
  useEffect(() => {
    let connectionTimeout: NodeJS.Timeout;
    let isMounted = true;
    
    // Prevent multiple connections
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }
    
    const connectWebSocket = () => {
      if (!isMounted) return;
      
      const wsUrl = `ws://localhost:8765/stream/${sessionId}`;
      const ws = new WebSocket(wsUrl);
      
      // Set a timeout for connection attempt
      connectionTimeout = setTimeout(() => {
        if (!isMounted) return;
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.close(1006, 'Connection timeout');
        }
      }, 5000);
      
      ws.onopen = () => {
        if (!isMounted) return;
        
        clearTimeout(connectionTimeout);
        setIsConnected(true);
        startTimeRef.current = Date.now();
        
        // Send session initialization message to ensure correct session ID
        const initMessage = {
          type: 'init_session',
          session_id: sessionId
        };
        ws.send(JSON.stringify(initMessage));
      };
      
      ws.onmessage = (event) => {
        if (!isMounted) return;
        
        try {
          const streamEvent: StreamingEvent = JSON.parse(event.data);
          handleStreamingEvent(streamEvent);
        } catch (error) {
          console.error('❌ Error parsing WebSocket message:', error);
        }
      };
      
      ws.onerror = (error) => {
        if (!isMounted) return;
        
        clearTimeout(connectionTimeout);
        console.error('❌ WebSocket error:', error);
        console.error('🔍 WebSocket state:', ws.readyState);
        console.error('🔍 WebSocket URL:', ws.url);
        setIsConnected(false);
      };
      
      ws.onclose = (event) => {
        if (!isMounted) return;
        
        clearTimeout(connectionTimeout);
        setIsConnected(false);
        
        // NO automatic reconnection - let user manually reconnect
      };
      
      wsRef.current = ws;
    };

    // Wait a bit before connecting to ensure dialog is fully rendered
    const initialTimeout = setTimeout(() => {
      if (isMounted) {
        connectWebSocket();
      }
    }, 500);

    return () => {
      isMounted = false;
      if (initialTimeout) clearTimeout(initialTimeout);
      if (connectionTimeout) clearTimeout(connectionTimeout);
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [sessionId]);

  // Handle streaming events
  const handleStreamingEvent = useCallback((event: StreamingEvent) => {
    setEvents(prev => [...prev, event]);

    switch (event.event_type) {
      case 'session_start':
        setCurrentStatus(t('streaming:status.sessionStarted'));
        break;
        
      case 'session_confirmed':
        setCurrentStatus(t('streaming:status.sessionConfirmed'));
        break;
        
      case 'code_change':
      case 'file_update':
      case 'file_operation':
        setCurrentFile(event.data.file_path);
        if (event.data.content) {
          setCurrentCode(event.data.content);
        } else {
        }
        setSessionStats(prev => ({
          ...prev,
          filesChanged: prev.filesChanged + 1,
        }));
        break;
        
      case 'command':
      case 'command_run':
        setSessionStats(prev => ({
          ...prev,
          commandsRun: prev.commandsRun + 1,
        }));
        break;
        
      case 'command_output':
        // Command output could be displayed in a console view
        break;
        
      case 'test_run':
        setSessionStats(prev => ({
          ...prev,
          testsRun: prev.testsRun + 1,
        }));
        break;
        
      case 'test_result':
        // Test result could update the test status
        break;
        
      case 'agent_thinking':
        setCurrentStatus(t('streaming:status.thinking', { thought: event.data.thinking.slice(0, 50) }));
        break;
        
      case 'agent_response':
        setCurrentStatus(t('streaming:status.responding'));
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
            <h2 className="text-xl font-bold">{t('streaming:title')}</h2>
            <p className="text-sm text-muted-foreground">{projectPath}</p>
          </div>
          <Badge variant={isConnected ? "default" : "secondary"}>
            {isConnected ? (
              <>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2" />
                {t('streaming:status.live')}
              </>
            ) : (
              t('streaming:status.offline')
            )}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={downloadRecording}>
            <Download className="w-4 h-4 mr-2" />
            {t('streaming:header.saveRecording')}
          </Button>
          <Button variant="outline" size="sm">
            <Share2 className="w-4 h-4 mr-2" />
            {t('streaming:header.share')}
          </Button>
          <Button variant="destructive" size="sm" onClick={stopSession} className="mr-6">
            <Square className="w-4 h-4 mr-2" />
            {t('streaming:header.stopSession')}
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
            <span>{t('streaming:stats.files', { count: sessionStats.filesChanged })}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">{t('streaming:stats.commands')}</span>
            <span className="font-mono">{sessionStats.commandsRun}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">{t('streaming:stats.tests')}</span>
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
              {currentFile || t('streaming:codeView.noFile')}
            </p>
          </div>
          <ScrollArea className="flex-1 p-4">
            <pre className="text-sm font-mono">
              <code>{currentCode || t('streaming:codeView.waitingForChanges')}</code>
            </pre>
          </ScrollArea>
        </div>

        {/* Right: Tabs (Chat, Events, Timeline) */}
        <div className="w-96 flex flex-col border-l">
          <Tabs defaultValue="chat" className="flex-1 flex flex-col">
            <TabsList className="w-full rounded-none border-b">
              <TabsTrigger value="chat" className="flex-1">
                <MessageSquare className="w-4 h-4 mr-2" />
                {t('streaming:tabs.chat')}
              </TabsTrigger>
              <TabsTrigger value="events" className="flex-1">
                {t('streaming:tabs.events')} ({events.length})
              </TabsTrigger>
              <TabsTrigger value="timeline" className="flex-1">
                {t('streaming:tabs.timeline')}
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
                    placeholder={t('streaming:chat.placeholder')}
                    className="flex-1 px-3 py-2 text-sm border rounded-md bg-background"
                  />
                  <Button size="sm" onClick={sendChatMessage}>
                    {t('streaming:chat.send')}
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
                            {JSON.stringify(event.data || {}).slice(0, 100)}...
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
                <p>{t('streaming:timeline.comingSoon')}</p>
                <p className="text-xs mt-2">{t('streaming:timeline.replayDescription')}</p>
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
          title={isPaused ? t('streaming:controls.resume') : t('streaming:controls.pause')}
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

