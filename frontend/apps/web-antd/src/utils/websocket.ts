type MessageHandler = (message: any) => void;
type ReconnectingHandler = (attempt: number, delay: number) => void;
type MaxRetriesReachedHandler = () => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private onMessage: MessageHandler;
  private onOpen?: () => void;
  private onClose?: () => void;
  private onReconnecting?: ReconnectingHandler;
  private onMaxRetriesReached?: MaxRetriesReachedHandler;
  private taskId: string = '';
  private token: string = '';
  private manualClose = false;

  constructor(
    onMessage: MessageHandler,
    onOpen?: () => void,
    onClose?: () => void,
    onReconnecting?: ReconnectingHandler,
    onMaxRetriesReached?: MaxRetriesReachedHandler
  ) {
    this.onMessage = onMessage;
    this.onOpen = onOpen;
    this.onClose = onClose;
    this.onReconnecting = onReconnecting;
    this.onMaxRetriesReached = onMaxRetriesReached;
  }

  connect(taskId: string, token: string) {
    this.taskId = taskId;
    this.token = token;
    this.reconnectAttempts = 0;
    this.manualClose = false;
    this._connect();
  }

  private _connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/design/${this.taskId}?token=${this.token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.onOpen?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        console.log('[WebSocketManager] Received message:', msg);
        this.onMessage(msg);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      this.onClose?.();

      // 如果是手动关闭，不重连
      if (this.manualClose) {
        return;
      }

      // 如果未达到最大重连次数，尝试重连（指数退避策略）
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        // 指数退避：1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
        const delay = Math.min(
          1000 * Math.pow(2, this.reconnectAttempts),
          60000  // 最大60秒
        );

        console.log(
          `WebSocket disconnected. Reconnecting in ${delay}ms... ` +
          `(attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`
        );

        // 通知UI重连中
        this.onReconnecting?.(this.reconnectAttempts + 1, delay);

        setTimeout(() => {
          this.reconnectAttempts++;
          this._connect();
        }, delay);
      } else {
        console.error('WebSocket max reconnection attempts reached');
        // 通知UI达到最大重连次数
        this.onMaxRetriesReached?.();
      }
    };
  }

  disconnect() {
    this.manualClose = true;
    this.reconnectAttempts = this.maxReconnectAttempts;
    this.ws?.close();
    this.ws = null;
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
