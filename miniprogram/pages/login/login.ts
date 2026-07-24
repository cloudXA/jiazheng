import { phoneLogin, saveLoginState } from '../../services/auth'

const DEFAULT_AVATAR =
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect width="200" height="200" fill="%23E5E7EB"/%3E%3Ccircle cx="100" cy="78" r="38" fill="%23B6BCC8"/%3E%3Cpath d="M40 170c0-33 27-58 60-58s60 25 60 58z" fill="%23B6BCC8"/%3E%3C/svg%3E'

interface ILoginData {
  status: 'idle' | 'logged'
  avatarUrl: string
  nickName: string
  phone: string
  loginCode: string
}

interface AvatarEvent {
  detail: {
    avatarUrl: string
  }
}

interface TextInputEvent {
  detail: {
    value: string
  }
}

interface PhoneNumberEvent {
  detail: {
    errMsg: string
    code: string
  }
}

Component({
  data: {
    status: 'idle',
    avatarUrl: '',
    nickName: '',
    phone: '',
    loginCode: '',
    defaultAvatar: DEFAULT_AVATAR,
  } as ILoginData,
  lifetimes: {
    attached() {
      const app = getApp<IAppOption>()
      if (app.globalData.token) {
        // 已登录：直接进入首页（tabBar）
        wx.switchTab({ url: '/pages/home/home' })
        return
      }
      this.getLoginCode()
    },
  },
  methods: {
    getLoginCode() {
      wx.login({
        success: (res) => this.setData({ loginCode: res.code }),
      })
    },
    onChooseAvatar(e: AvatarEvent) {
      this.setData({ avatarUrl: e.detail.avatarUrl })
    },
    onInputChange(e: TextInputEvent) {
      this.setData({ nickName: e.detail.value })
    },
    async onGetPhoneNumber(e: PhoneNumberEvent) {
      if (e.detail.errMsg !== 'getPhoneNumber:ok') {
        wx.showToast({ title: '已取消授权', icon: 'none' })
        return
      }
      const phoneCode = e.detail.code
      if (!this.data.loginCode) this.getLoginCode()
      try {
        const res = await phoneLogin({
          code: this.data.loginCode,
          phoneCode,
          avatarUrl: this.data.avatarUrl || undefined,
          nickName: this.data.nickName || undefined,
        })
        saveLoginState(res.token, res.userInfo)
        this.setData({
          status: 'logged',
          avatarUrl: res.userInfo.avatarUrl,
          nickName: res.userInfo.nickName,
          phone: maskPhone(res.userInfo.phone || ''),
        })
      } catch {
        // 错误提示已在请求层统一处理
      }
    },
    enterApp() {
      wx.switchTab({ url: '/pages/home/home' })
    },
  },
})

function maskPhone(phone: string): string {
  if (!phone || phone.length < 7) return phone
  return phone.slice(0, 3) + '****' + phone.slice(-4)
}
