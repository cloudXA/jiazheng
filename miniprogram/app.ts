App<IAppOption>({
  globalData: {
    userInfo: undefined,
    token: '',
  },
  onLaunch() {
    // 从本地存储恢复登录态（token 持久化，运行时 userInfo 放 globalData）
    const token = wx.getStorageSync('token') || ''
    const userInfo = wx.getStorageSync('userInfo') || undefined
    this.globalData.token = token
    this.globalData.userInfo = userInfo
  },
})
