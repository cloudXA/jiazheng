/// <reference path="./types/index.d.ts" />

interface UserInfo {
  avatarUrl: string
  nickName: string
  phone?: string
  openid?: string
}

interface IAppOption {
  globalData: {
    userInfo?: UserInfo
    token?: string
  }
  userInfoReadyCallback?: (userInfo: UserInfo) => void
}
