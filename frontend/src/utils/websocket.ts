/**
 * WebSocket Manager with auto-reconnect
 */
import type { WebSocketMessage } from '@/types/task'

type MessageHandler = (msg: WebSocketMessage) => void

export class WebSocketManager {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private onMessage: MessageHandler
  private taskId: string = ''
  private token: string = ''

  constructor(onMessage: MessageHandler) {
    this.onMessage = onMessage
  }

  connect(taskId: string, token: string) {
    this.taskId = taskId
    this.token = token
    this.reconnectAttempts = 0
    this._connect()
  }

  private _connect() {
    const wsBase = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
    const url = `${wsBase}/ws/design/${this.taskId}?token=${this.token}`
    this.ws = new WebSocket(url)

    this.ws.onmessage = (event) => {
      try {
        const msg: WebSocketMessage = JSON.parse(event.data)
        this.onMessage(msg)
      } catch {}
    }

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
        setTimeout(() => {
          this.reconnectAttempts++
          this._connect()
        }, delay)
      }
    }
  }

  disconnect() {
    this.reconnectAttempts = this.maxReconnectAttempts
    this.ws?.close()
    this.ws = null
  }
}
