type MessageHandler = (message: any) => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private onMessage: MessageHandler;
  private onOpen?: () => void;
  private onClose?: () => void;
  private taskId: string = '';
  private token: string = '';
  private manualClose = false;

  constructor(onMessage: MessageHandler, onOpen?: () => void, onClose?: () => void) {
    this.onMessage = onMessage;
    this.onOpen = onOpen;
    this.onClose = onClose;
  }

  connect(taskId: string, token: string) {
    this.taskId = taskId;
    this.token = token;
    this.reconnectAttempts = 0;
    this.manualClose = false;
    this._connect();
  }

  private _connect() {
    const wsUrl = `ws://localhost:8000/ws/design/${this.taskId}?token=${this.token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.onOpen?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
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

      // 如果未达到最大重连次数，尝试重连
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        console.log(`WebSocket disconnected. Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
          this.reconnectAttempts++;
          this._connect();
        }, delay);
      } else {
        console.error('WebSocket max reconnection attempts reached');
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
