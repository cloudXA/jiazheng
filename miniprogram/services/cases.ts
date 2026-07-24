import { RiskAnalysis, RiskCaseRecord, RiskCaseStatus } from './types'

const STORAGE_KEY = 'domestic-service-risk-cases-v2'

function isRiskCaseRecord(value: unknown): value is RiskCaseRecord {
  if (!value || typeof value !== 'object') return false
  const record = value as Partial<RiskCaseRecord>
  return (
    typeof record.id === 'string' &&
    typeof record.createdAt === 'number' &&
    typeof record.title === 'string' &&
    (record.status === 'pending' || record.status === 'confirmed')
  )
}

export function listRiskCases(): RiskCaseRecord[] {
  const stored = wx.getStorageSync(STORAGE_KEY) as unknown
  if (!Array.isArray(stored)) return []
  return stored
    .filter(isRiskCaseRecord)
    .sort((left, right) => right.createdAt - left.createdAt)
}

export function getRiskCase(id: string): RiskCaseRecord | undefined {
  return listRiskCases().find((item) => item.id === id)
}

export function saveRiskCase(analysis: RiskAnalysis): RiskCaseRecord {
  const records = listRiskCases()
  const existing = records.find((item) => item.id === analysis.id)
  const record: RiskCaseRecord = {
    ...analysis,
    status: existing ? existing.status : 'pending',
  }
  const nextRecords = [record, ...records.filter((item) => item.id !== analysis.id)]
  wx.setStorageSync(STORAGE_KEY, nextRecords)
  return record
}

export function updateRiskCaseStatus(id: string, status: RiskCaseStatus): RiskCaseRecord | undefined {
  const records = listRiskCases()
  const current = records.find((item) => item.id === id)
  if (!current) return undefined

  const updated: RiskCaseRecord = { ...current, status }
  wx.setStorageSync(
    STORAGE_KEY,
    records.map((item) => (item.id === id ? updated : item)),
  )
  return updated
}
