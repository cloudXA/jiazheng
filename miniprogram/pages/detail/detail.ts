import { getRiskCase, updateRiskCaseStatus } from '../../services/cases'
import { RiskCaseRecord } from '../../services/types'

interface DetailData {
  id: string
  record: RiskCaseRecord | null
  createdLabel: string
  statusLabel: string
}

function formatCreatedAt(timestamp: number): string {
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}`
}

Component({
  data: {
    id: '',
    record: null,
    createdLabel: '',
    statusLabel: '',
  } as DetailData,
  methods: {
    onLoad(query: Record<string, string>) {
      const id = query.id || ''
      const record = getRiskCase(id)
      if (!record) {
        wx.showToast({ title: '记录不存在或已被删除', icon: 'none' })
        return
      }
      this.setData({
        id,
        record,
        createdLabel: formatCreatedAt(record.createdAt),
        statusLabel: record.status === 'confirmed' ? '已确认' : '待确认',
      })
    },
    onCopyMessage() {
      const record = this.data.record
      if (!record) return
      wx.setClipboardData({
        data: record.confirmationMessage,
        success: () => wx.showToast({ title: '确认话术已复制', icon: 'success' }),
      })
    },
    onMarkConfirmed() {
      if (!this.data.record || this.data.record.status === 'confirmed') return
      const updated = updateRiskCaseStatus(this.data.id, 'confirmed')
      if (!updated) return
      this.setData({ record: updated, statusLabel: '已确认' })
      wx.showToast({ title: '已标记为确认', icon: 'success' })
    },
  },
})
