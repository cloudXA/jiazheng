import { listRiskCases } from './cases'
import { RiskLevel } from './types'

export interface MetricItem {
  key: string
  label: string
  value: string
  tone: 'default' | 'warning' | 'danger'
}

export interface QuickEntry {
  key: string
  label: string
  desc: string
  symbol: string
}

export interface HomeCaseItem {
  id: string
  title: string
  summary: string
  createdLabel: string
  riskLevel: RiskLevel
  riskLabel: string
  statusLabel: string
}

export interface HomeData {
  greeting: string
  metrics: MetricItem[]
  entries: QuickEntry[]
  cases: HomeCaseItem[]
}

function formatCreatedAt(timestamp: number): string {
  const date = new Date(timestamp)
  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  if (sameDay) {
    const hour = String(date.getHours()).padStart(2, '0')
    const minute = String(date.getMinutes()).padStart(2, '0')
    return `今天 ${hour}:${minute}`
  }
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

export function getHomeData(): Promise<HomeData> {
  const records = listRiskCases()
  const userInfo = getApp<IAppOption>().globalData.userInfo
  const pendingCount = records.filter((item) => item.status === 'pending').length
  const highRiskCount = records.filter(
    (item) => item.status === 'pending' && item.riskLevel === 'high',
  ).length
  const confirmedCount = records.filter((item) => item.status === 'confirmed').length

  return Promise.resolve({
    greeting: userInfo && userInfo.nickName ? `${userInfo.nickName}，你好` : '你好',
    metrics: [
      { key: 'pending', label: '待确认', value: String(pendingCount), tone: 'warning' },
      { key: 'high-risk', label: '高风险', value: String(highRiskCount), tone: 'danger' },
      { key: 'confirmed', label: '已留证', value: String(confirmedCount), tone: 'default' },
    ],
    entries: [
      { key: 'new', label: '新建记录', desc: '录入客户沟通', symbol: '+' },
      { key: 'fee', label: '收费确认', desc: '生成确认话术', symbol: '¥' },
      { key: 'care', label: '照护核对', desc: '补齐安全信息', symbol: '!' },
    ],
    cases: records.slice(0, 8).map((item) => ({
      id: item.id,
      title: item.title,
      summary: item.summary,
      createdLabel: formatCreatedAt(item.createdAt),
      riskLevel: item.riskLevel,
      riskLabel: item.riskLabel,
      statusLabel: item.status === 'confirmed' ? '已确认' : '待确认',
    })),
  })
}
