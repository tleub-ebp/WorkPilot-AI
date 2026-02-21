import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Play, Wifi, WifiOff } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { Task } from '../../shared/types';

interface StreamingTestProps {
  tasks: Task[];
  onTaskStart?: (taskId: string, options?: any) => void;
}

export function StreamingTest({ tasks, onTaskStart }: StreamingTestProps) {
  const { t } = useTranslation(['streaming', 'common']);
  const [isStreamingServerRunning, setIsStreamingServerRunning] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [selectedTaskId, setSelectedTaskId] = useState('');
  const [isConnected, setIsConnected] = useState(false);

  // Check if streaming server is running
  const checkStreamingServer = async () => {
    try {
      const response = await fetch('http://localhost:8765/health');
      setIsStreamingServerRunning(response.ok);
    } catch (error) {
      setIsStreamingServerRunning(false);
    }
  };

  // Start streaming server
  const startStreamingServer = async () => {
    try {
      await ipcRenderer.invoke('streaming-server-start', { port: 8765 });
      setIsStreamingServerRunning(true);
    } catch (error) {
      console.error('Failed to start streaming server:', error);
    }
  };

  // Generate a unique session ID
  const generateSessionId = () => {
    const id = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(id);
    return id;
  };

  // Start task with streaming
  const startTaskWithStreaming = () => {
    if (!selectedTaskId) {
      alert('Please select a task');
      return;
    }

    const streamingSessionId = sessionId || generateSessionId();
    
    if (onTaskStart) {
      onTaskStart(selectedTaskId, {
        enableStreaming: true,
        streamingSessionId: streamingSessionId,
      });
    } else {
      // Fallback: direct IPC call
      ipcRenderer.invoke(IPC_CHANNELS.TASK_START, selectedTaskId, {
        enableStreaming: true,
        streamingSessionId: streamingSessionId,
      });
    }
  };

  // Check connection status
  const checkConnection = async () => {
    if (!sessionId) return;
    
    try {
      const ws = new WebSocket(`ws://localhost:8765/stream/${sessionId}`);
      ws.onopen = () => {
        setIsConnected(true);
        ws.close();
      };
      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch (error) {
      setIsConnected(false);
    }
  };

  React.useEffect(() => {
    checkStreamingServer();
    const interval = setInterval(checkStreamingServer, 5000);
    return () => clearInterval(interval);
  }, []);

  React.useEffect(() => {
    if (sessionId) {
      checkConnection();
      const interval = setInterval(checkConnection, 3000);
      return () => clearInterval(interval);
    }
  }, [sessionId]);

  const availableTasks = tasks.filter(task => task.status === 'backlog' || task.status === 'queue');

  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Streaming Test</h3>
          <div className="flex items-center gap-2">
            <Badge variant={isStreamingServerRunning ? "default" : "secondary"}>
              {isStreamingServerRunning ? (
                <>
                  <Wifi className="w-3 h-3 mr-1" />
                  Server Running
                </>
              ) : (
                <>
                  <WifiOff className="w-3 h-3 mr-1" />
                  Server Stopped
                </>
              )}
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Session ID</label>
              <div className="flex gap-2">
                <Input
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                  placeholder="Auto-generated or enter custom"
                />
                <Button
                  variant="outline"
                  onClick={generateSessionId}
                  disabled={!isStreamingServerRunning}
                >
                  Generate
                </Button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Connection Status</label>
              <Badge variant={isConnected ? "default" : "secondary"}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Select Task</label>
              <select
                value={selectedTaskId}
                onChange={(e) => setSelectedTaskId(e.target.value)}
                className="w-full p-2 border rounded-md"
                disabled={availableTasks.length === 0}
              >
                <option value="">Select a task...</option>
                {availableTasks.map(task => (
                  <option key={task.id} value={task.id}>
                    {task.title} ({task.id})
                  </option>
                ))}
              </select>
            </div>

            <Button
              onClick={startTaskWithStreaming}
              disabled={!isStreamingServerRunning || !selectedTaskId || !sessionId}
              className="w-full"
            >
              <Play className="w-4 h-4 mr-2" />
              Start Task with Streaming
            </Button>
          </div>
        </div>

        {!isStreamingServerRunning && (
          <div className="text-center py-4">
            <Button onClick={startStreamingServer} variant="outline">
              Start Streaming Server
            </Button>
          </div>
        )}

        <div className="text-xs text-muted-foreground">
          <p>Instructions:</p>
          <ol className="list-decimal list-inside space-y-1">
            <li>Start the streaming server if not running</li>
            <li>Generate or enter a session ID</li>
            <li>Select a task from backlog/queue</li>
            <li>Click "Start Task with Streaming"</li>
            <li>The task will execute with live streaming events</li>
          </ol>
        </div>
      </div>
    </Card>
  );
}
