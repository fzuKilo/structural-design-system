/**
 * Task Store
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { StageUpdate, AskHumanRequest } from '@/types/task'

export const useTaskStore = defineStore('task', () => {
  const currentTaskId = ref<string | null>(null)
  const stages = ref<StageUpdate[]>([])
  const askHumanRequest = ref<AskHumanRequest | null>(null)

  const addStage = (stage: StageUpdate) => {
    stages.value.push(stage)
  }

  const setAskHuman = (request: AskHumanRequest) => {
    askHumanRequest.value = request
  }

  const clearAskHuman = () => {
    askHumanRequest.value = null
  }

  const reset = () => {
    currentTaskId.value = null
    stages.value = []
    askHumanRequest.value = null
  }

  return { currentTaskId, stages, askHumanRequest, addStage, setAskHuman, clearAskHuman, reset }
})
