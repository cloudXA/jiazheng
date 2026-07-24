export type RiskLevel = 'low' | 'medium' | 'high'

export type RiskFieldStatus = 'confirmed' | 'missing' | 'info'

export type RiskCaseStatus = 'pending' | 'confirmed'

export interface RiskField {
  key: string
  label: string
  value: string
  status: RiskFieldStatus
}

export interface RiskAnalysis {
  id: string
  createdAt: number
  sourceText: string
  title: string
  riskLevel: RiskLevel
  riskLabel: string
  summary: string
  fields: RiskField[]
  reasons: string[]
  missingEvidence: string[]
  beforeDispatch: string[]
  confirmationMessage: string
  internalNote: string
  refusalAction: string
}

export interface RiskCaseRecord extends RiskAnalysis {
  status: RiskCaseStatus
}

export interface TranscriptionResult {
  text: string
  simulated: boolean
}
