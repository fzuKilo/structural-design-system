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
    console.log('[WebSocket] Connecting to:', url)
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('[WebSocket] Connected successfully')
    }

    this.ws.onmessage = (event) => {
      console.log('[WebSocket] Received message:', event.data)
      try {
        const msg: WebSocketMessage = JSON.parse(event.data)
        this.onMessage(msg)
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', e)
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
    }

    this.ws.onclose = (event) => {
      console.log('[WebSocket] Closed:', event.code, event.reason)
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
        console.log(`[WebSocket] Reconnecting in ${delay}ms...`)
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
