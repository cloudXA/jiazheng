import { getHomeData, HomeData } from '../../services/home'

const ASSISTANT_DRAFT_KEY = 'risk-assistant-draft'

const ENTRY_DRAFTS: Record<string, string> = {
  new: '',
  fee: '请帮我核对这笔订单的收费约定：',
  care: '这是一笔老人或儿童照护订单，请重点检查健康信息、安全责任和应急联系人：',
}

Component({
  data: {
    loading: true,
    greeting: '你好',
    metrics: [] as HomeData['metrics'],
    entries: [] as HomeData['entries'],
    cases: [] as HomeData['cases'],
  },
  methods: {
    onShow() {
      const tabBar = this.getTabBar() as any
      if (tabBar) tabBar.setData({ selected: 0 })
      this.loadData()
    },
    onLoad() {
      this.loadData()
    },
    async loadData() {
      try {
        const data = await getHomeData()
        this.setData({
          greeting: data.greeting,
          metrics: data.metrics,
          entries: data.entries,
          cases: data.cases,
        })
      } catch {
        wx.showToast({ title: '首页数据加载失败', icon: 'none' })
      } finally {
        this.setData({ loading: false })
      }
    },
    onPrimaryTap() {
      wx.removeStorageSync(ASSISTANT_DRAFT_KEY)
      wx.switchTab({ url: '/pages/ai/ai' })
    },
    onEntryTap(e: WechatMiniprogram.TouchEvent) {
      const key = String(e.currentTarget.dataset.key || '')
      const draft = ENTRY_DRAFTS[key] || ''
      if (draft) {
        wx.setStorageSync(ASSISTANT_DRAFT_KEY, draft)
      } else {
        wx.removeStorageSync(ASSISTANT_DRAFT_KEY)
      }
      wx.switchTab({ url: '/pages/ai/ai' })
    },
    onCaseTap(e: WechatMiniprogram.TouchEvent) {
      const id = String(e.currentTarget.dataset.id || '')
      if (!id) return
      wx.navigateTo({ url: `/pages/detail/detail?id=${id}` }).catch(() => {})
    },
  },
})
