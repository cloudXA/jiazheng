import { logout, clearLoginState } from '../../services/auth'

Component({
  data: {
    userInfo: { avatarUrl: '', nickName: '微信用户', phone: '' } as UserInfo,
  },
  methods: {
    onShow() {
      const tabBar = this.getTabBar() as any
      if (tabBar) tabBar.setData({ selected: 2 })
      const app = getApp<IAppOption>()
      if (app && app.globalData.userInfo) {
        this.setData({ userInfo: app.globalData.userInfo })
      }
    },
    onEdit() {
      wx.showToast({ title: '资料编辑开发中', icon: 'none' })
    },
    onAbout() {
      wx.showModal({
        title: '关于',
        content: '家政签约风控助手 · 用于订单留痕、风险提示和客户确认，不替代法律意见。',
        showCancel: false,
      })
    },
    async onLogout() {
      const res = await wx.showModal({ title: '提示', content: '确定退出登录？' })
      if (!res.confirm) return
      try {
        await logout()
      } catch {
        // 即使后端失败也清除本地登录态
      }
      clearLoginState()
      wx.reLaunch({ url: '/pages/login/login' })
    },
  },
})
