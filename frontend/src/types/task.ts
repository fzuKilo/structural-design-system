/**
 * Task Types
 */

export interface StageUpdate {
  type: 'stage'
  stage: string
  status: 'started' | 'completed' | 'failed'
  message: string
  timestamp: string
}

export interface AskHumanRequest {
  type: 'ask_human'
  question: string
  options: string[]
  default?: string
}

export interface ResultMessage {
  type: 'result'
  status: 'success' | 'failed'
  data: any
}

export interface ErrorMessage {
  type: 'error'
  error_code: string
  message: string
}

export type WebSocketMessage = StageUpdate | AskHumanRequest | ResultMessage | ErrorMessage
