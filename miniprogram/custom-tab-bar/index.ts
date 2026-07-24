Component({
  data: {
    selected: 0,
    safeBottom: 0,
    list: [
      { pagePath: '/pages/home/home', text: '首页', icon: '🏠' },
      { pagePath: '/pages/ai/ai', text: '风控助手', icon: '✓' },
      { pagePath: '/pages/mine/mine', text: '我的', icon: '👤' },
    ],
  },
  lifetimes: {
    attached() {
      const info = wx.getSystemInfoSync() as ReturnType<typeof wx.getSystemInfoSync> & {
        safeAreaInsets?: { bottom: number }
      }
      const safeBottom = (info.safeAreaInsets && info.safeAreaInsets.bottom) || 0
      this.setData({ safeBottom })
    },
  },
  methods: {
    switchTab(e: WechatMiniprogram.TouchEvent) {
      const index = Number(e.currentTarget.dataset.index)
      const url = this.data.list[index].pagePath
      wx.switchTab({ url })
    },
  },
})
