import { getApiBaseUrl, MOCK_MODE, request } from './request'
import { RiskAnalysis, TranscriptionResult } from './types'

// 前端只调用自有后端，由后端代理模型与语音服务，密钥不会暴露在小程序中。
export function analyzeContractRisk(sourceText: string): Promise<RiskAnalysis> {
  return request({
    url: '/api/risk/analyze',
    method: 'POST',
    data: { sourceText },
    showLoading: false,
  })
}

export function transcribeAudio(tempFilePath: string): Promise<TranscriptionResult> {
  if (MOCK_MODE) {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          simulated: true,
          text:
            '客户李女士需要住家照护，先试工7天。阿姨由合作方推荐，' +
            '服务成功后收取首月工资30%的服务费。客户电话里同意过，' +
            '但还没有微信书面确认，也没有说明退款和不得绕开公司私签的规则。',
        })
      }, 700)
    })
  }

  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token') as string
    wx.uploadFile({
      url: `${getApiBaseUrl()}/api/ai/transcribe`,
      filePath: tempFilePath,
      name: 'audio',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (response) => {
        try {
          const body = JSON.parse(response.data) as {
            code: number
            data: TranscriptionResult
            message: string
          }
          if (response.statusCode >= 200 && response.statusCode < 300 && body.code === 0) {
            resolve(body.data)
            return
          }
          reject(new Error(body.message || '语音转写失败'))
        } catch (error) {
          reject(error)
        }
      },
      fail: reject,
    })
  })
}
