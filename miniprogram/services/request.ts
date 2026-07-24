// 统一网络请求层：封装 wx.request 为 Promise，注入 token、统一错误处理与 401 跳转。
// 注意：前端不持有任何密钥，所有鉴权/AI 调用都打到你的 Python 后端。

// ======== 开发阶段配置 ========
export const MOCK_MODE = false // 后端未就绪时为 true，跳过真实网络请求，用 mock 数据跑通流程
// ============================

const BASE_URL = MOCK_MODE ? '' : 'http://10.154.61.117:8000'

export function getApiBaseUrl(): string {
  return BASE_URL
}

interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: Record<string, any>
  showLoading?: boolean
  auth?: boolean
  loadingText?: string
}

interface ResponseBody<T> {
  code: number
  data: T
  message: string
}

function getToken(): string {
  const app = getApp<IAppOption>()
  return (app && app.globalData.token as string) || wx.getStorageSync('token') || ''
}

// 401：清空登录态并跳回登录页（reLaunch 会清掉 tabBar 栈）
function handleUnauthorized(): void {
  const app = getApp<IAppOption>()
  if (app) {
    app.globalData.token = ''
    app.globalData.userInfo = undefined
  }
  wx.removeStorageSync('token')
  wx.removeStorageSync('userInfo')
  wx.reLaunch({ url: '/pages/login/login' })
}

export function request<T = any>(options: RequestOptions): Promise<T> {
  const {
    url,
    method = 'GET',
    data,
    showLoading = false,
    auth = true,
    loadingText = '加载中',
  } = options

  // Mock 模式：拦截请求，返回本地模拟数据，不发起真实网络请求
  if (MOCK_MODE) {
    return new Promise<T>((resolve, reject) => {
      if (showLoading) wx.showLoading({ title: loadingText, mask: true })
      // 模拟网络延迟
      setTimeout(() => {
        if (showLoading) wx.hideLoading()
        try {
          const result = handleMock(url, method, data)
          resolve(result as T)
        } catch (e: any) {
          wx.showToast({ title: e.message || '请求失败', icon: 'none' })
          reject(e)
        }
      }, 600)
    })
  }

  return new Promise<T>((resolve, reject) => {
    if (showLoading) wx.showLoading({ title: loadingText, mask: true })

    wx.request({
      url: BASE_URL + url,
      method,
      data,
      timeout: 15000,
      header: {
        'content-type': 'application/json',
        ...(auth && getToken() ? { Authorization: 'Bearer ' + getToken() } : {}),
      },
      success: (res) => {
        if (showLoading) wx.hideLoading()
        const status = res.statusCode
        const body = res.data as ResponseBody<T>
        if (status === 401) {
          handleUnauthorized()
          const msg = (body && body.message) || '登录已过期'
          reject(new Error(msg))
          return
        }
        if (status >= 200 && status < 300 && body && body.code === 0) {
          resolve(body.data)
        } else {
          const msg = (body && body.message) || '请求失败 (' + status + ')'
          wx.showToast({ title: msg, icon: 'none' })
          reject(new Error(msg))
        }
      },
      fail: (err) => {
        if (showLoading) wx.hideLoading()
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' })
        reject(err)
      },
    })
  })
}

// ======== Mock 数据处理器（后端就绪后删除此函数即可） ========
const DEFAULT_MOCK_AVATAR =
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect width="200" height="200" fill="%23E5E7EB"/%3E%3Ccircle cx="100" cy="78" r="38" fill="%23B6BCC8"/%3E%3Cpath d="M40 170c0-33 27-58 60-58s60 25 60 58z" fill="%23B6BCC8"/%3E%3C/svg%3E'

function handleMock(url: string, method: string, data: Record<string, any> | undefined): any {
  // 登录
  if (url === '/api/auth/login' && method === 'POST') {
    const phoneNum = data && data.phoneCode ? '138' + String(Date.now()).slice(-8) : '138****0001'
    return {
      token: 'mock-token-' + Date.now(),
      userInfo: {
        avatarUrl: (data && data.avatarUrl) || DEFAULT_MOCK_AVATAR,
        nickName: (data && data.nickName) || '微信用户',
        phone: phoneNum,
      },
    }
  }
  // 获取用户信息
  if (url === '/api/user/info') {
    return {
      avatarUrl: getApp<IAppOption>().globalData.userInfo
        ? getApp<IAppOption>().globalData.userInfo!.avatarUrl
        : DEFAULT_MOCK_AVATAR,
      nickName: getApp<IAppOption>().globalData.userInfo
        ? getApp<IAppOption>().globalData.userInfo!.nickName
        : '微信用户',
      phone: getApp<IAppOption>().globalData.userInfo
        ? getApp<IAppOption>().globalData.userInfo!.phone
        : '138****0001',
    }
  }
  // 家政签约风险分析
  if (url === '/api/risk/analyze' && method === 'POST') {
    const sourceText = data && typeof data.sourceText === 'string' ? data.sourceText : ''
    return buildMockRiskAnalysis(sourceText)
  }
  // 退出登录
  if (url === '/api/auth/logout') {
    return undefined
  }
  throw new Error('未知接口: ' + method + ' ' + url)
}

function includesAny(text: string, keywords: string[]): boolean {
  return keywords.some((keyword) => text.includes(keyword))
}

function hasPositiveMention(text: string, keywords: string[]): boolean {
  return keywords.some((keyword) => {
    const index = text.indexOf(keyword)
    if (index < 0) return false
    const context = text.slice(Math.max(0, index - 10), index + keyword.length + 14)
    return !includesAny(context, [
      '没有',
      '还没',
      '尚未',
      '未确认',
      '没确认',
      '未说明',
      '没说明',
      '没说清',
      '不清楚',
    ])
  })
}

function pickServiceType(text: string): string {
  if (includesAny(text, ['老人', '照护', '护理', '陪护'])) return '老人照护'
  if (includesAny(text, ['育儿', '育婴', '月嫂'])) return '育儿服务'
  if (includesAny(text, ['钟点', '小时工'])) return '钟点服务'
  if (includesAny(text, ['保洁', '清洁'])) return '保洁服务'
  if (includesAny(text, ['住家', '保姆'])) return '住家服务'
  return '待补充'
}

function buildMockRiskAnalysis(sourceText: string): any {
  const text = sourceText.trim()
  const trialMatch = text.match(/(?:试工|试用)\s*(\d+)\s*天/)
  const percentMatch = text.match(/(\d+(?:\.\d+)?)\s*%/)
  const fixedFeeMatch = text.match(/(\d+(?:\.\d+)?)\s*(?:元|块)/)
  const customerMatch = text.match(
    /客户(?:叫|姓名是|是)?\s*([\u4e00-\u9fa5]{1,4}(?:女士|先生))/,
  )
  const serviceType = pickServiceType(text)
  const customerName = customerMatch ? customerMatch[1] : '未记录'
  const workerSource = text.includes('第三方')
    ? '第三方阿姨'
    : text.includes('合作')
      ? '合作阿姨'
      : includesAny(text, ['公司员工', '公司阿姨'])
        ? '公司阿姨'
        : '待补充'
  const chargeMethod = percentMatch
    ? '按首月工资比例'
    : includesAny(text, ['年费', '包年'])
      ? '年费'
      : fixedFeeMatch
        ? '固定金额'
        : '待补充'
  const chargeValue = percentMatch
    ? `${percentMatch[1]}%`
    : fixedFeeMatch
      ? `${fixedFeeMatch[1]}元`
      : '待补充'
  const writtenConfirmed = hasPositiveMention(text, [
    '微信确认',
    '书面确认',
    '签字',
    '已签合同',
    '回复确认',
  ])
  const decisionMakerConfirmed = hasPositiveMention(text, [
    '决策人',
    '本人决定',
    '家属同意',
    '子女同意',
  ])
  const noBypassConfirmed = hasPositiveMention(text, [
    '不得绕开',
    '不能绕开',
    '不私签',
    '不得私签',
    '禁止私签',
  ])
  const refundExplained = hasPositiveMention(text, [
    '退款规则',
    '退费规则',
    '退款约定',
    '退费约定',
  ])
  const hasFeeDispute = includesAny(text, ['反悔', '不认', '不收费', '不要收费', '拒绝付费'])
  const hasSafetyEvent = includesAny(text, ['噎', '受伤', '摔倒', '事故', '急救'])
  const isCareService = serviceType === '老人照护' || serviceType === '育儿服务'

  const missingEvidence: string[] = []
  if (customerName === '未记录') missingEvidence.push('客户姓名或脱敏代号')
  if (serviceType === '待补充') missingEvidence.push('具体服务类型与服务范围')
  if (workerSource === '待补充') missingEvidence.push('阿姨来源及合作关系')
  if (chargeValue === '待补充') missingEvidence.push('收费方式与具体金额或比例')
  if (!writtenConfirmed) missingEvidence.push('客户对收费规则的书面确认')
  if (!decisionMakerConfirmed) missingEvidence.push('家庭实际决策人的确认')
  if (!noBypassConfirmed) missingEvidence.push('不得绕开公司私签的书面约定')
  if (!refundExplained) missingEvidence.push('试工结束、换人及退款规则')
  if (isCareService && !includesAny(text, ['病史', '禁忌', '应急联系人'])) {
    missingEvidence.push('照护对象病史、禁忌及应急联系人')
  }

  const reasons: string[] = []
  if (hasFeeDispute) reasons.push('客户已出现收费反悔或拒绝确认信号，口头承诺难以单独支撑后续追偿。')
  if (workerSource === '第三方阿姨') reasons.push('阿姨来自第三方，服务责任、人员关系和保险边界需要另行明确。')
  if (!writtenConfirmed) reasons.push('收费目前缺少微信或合同书面确认，容易产生“介绍成功后不认服务费”的争议。')
  if (!noBypassConfirmed) reasons.push('尚未确认防私签条款，试工后客户与阿姨绕开公司的风险较高。')
  if (isCareService && (hasSafetyEvent || missingEvidence.some((item) => item.includes('病史')))) {
    reasons.push('照护服务涉及人身安全，健康信息和紧急处置责任尚未形成完整记录。')
  }
  if (reasons.length === 0) reasons.push('关键信息较完整，仍应在派单前让客户以文字回复确认。')

  const highRiskSignal =
    hasFeeDispute ||
    hasSafetyEvent ||
    workerSource === '第三方阿姨' ||
    includesAny(text, ['绕开公司', '私下签约'])
  const riskLevel = highRiskSignal ? 'high' : missingEvidence.length >= 3 ? 'medium' : 'low'
  const riskLabel = riskLevel === 'high' ? '高风险' : riskLevel === 'medium' ? '中风险' : '低风险'
  const trialValue = trialMatch ? `${trialMatch[1]}天` : '未说明'
  const titleCustomer = customerName === '未记录' ? '待补客户' : customerName
  const now = Date.now()

  const beforeDispatch = [
    '确认客户本人或家庭实际决策人，并留存微信回复。',
    `确认服务类型、试工期限和阿姨来源：${serviceType} / ${trialValue} / ${workerSource}。`,
    `确认服务费标准：${chargeMethod}，${chargeValue}。`,
    '明确不得绕开公司与阿姨私签、私下结算。',
    '发送换人、终止和退款规则，并让客户回复“确认无误”。',
  ]
  if (isCareService) {
    beforeDispatch.push('收集照护对象病史、饮食禁忌、吞咽/行动风险和紧急联系人。')
  }

  const confirmationMessage = [
    `您好，为避免后续理解不一致，现将本次${serviceType === '待补充' ? '家政服务' : serviceType}合作要点确认如下：`,
    `1. 客户称呼：${customerName}；试工安排：${trialValue}。`,
    `2. 阿姨来源：${workerSource}。`,
    `3. 服务成功后的服务费：${chargeMethod}，标准为${chargeValue}。`,
    '4. 未经公司书面同意，客户与阿姨不绕开公司私下签约或结算。',
    '5. 换人、终止及退款按双方书面确认的规则执行。',
    '请核对后回复“以上确认无误”。收到确认后，我们再安排派单。',
  ].join('\n')

  return {
    id: `case-${now}`,
    createdAt: now,
    sourceText: text,
    title: `${titleCustomer} · ${serviceType}`,
    riskLevel,
    riskLabel,
    summary:
      riskLevel === 'high'
        ? '先暂停派单，补齐收费、责任和人员关系证据。'
        : riskLevel === 'medium'
          ? '信息尚不完整，完成书面确认后再派单。'
          : '核心信息基本完整，发送确认话术留证后可推进。',
    fields: [
      { key: 'customer', label: '客户', value: customerName, status: customerName === '未记录' ? 'missing' : 'info' },
      { key: 'service', label: '服务类型', value: serviceType, status: serviceType === '待补充' ? 'missing' : 'info' },
      { key: 'trial', label: '试工', value: trialValue, status: trialMatch ? 'info' : 'missing' },
      { key: 'worker', label: '阿姨来源', value: workerSource, status: workerSource === '待补充' ? 'missing' : 'info' },
      { key: 'fee', label: '收费', value: `${chargeMethod} · ${chargeValue}`, status: chargeValue === '待补充' ? 'missing' : 'info' },
      { key: 'written', label: '书面确认', value: writtenConfirmed ? '已确认' : '未确认', status: writtenConfirmed ? 'confirmed' : 'missing' },
      { key: 'decision', label: '决策人', value: decisionMakerConfirmed ? '已确认' : '未确认', status: decisionMakerConfirmed ? 'confirmed' : 'missing' },
      { key: 'bypass', label: '防私签', value: noBypassConfirmed ? '已确认' : '未确认', status: noBypassConfirmed ? 'confirmed' : 'missing' },
      { key: 'refund', label: '退款规则', value: refundExplained ? '已说明' : '未说明', status: refundExplained ? 'confirmed' : 'missing' },
    ],
    reasons: reasons.slice(0, 4),
    missingEvidence,
    beforeDispatch,
    confirmationMessage,
    internalNote: `原始沟通已留存。当前${riskLabel}，缺失项${missingEvidence.length}个。派单前由业务人员复核，AI结果不替代合同审核。`,
    refusalAction: '客户拒绝书面确认时暂停派单，不继续垫付人员与协调成本；由负责人再次说明收费和责任边界。',
  }
}
