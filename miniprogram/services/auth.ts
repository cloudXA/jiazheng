import { request } from './request'

// 登录入参：
//  code      —— wx.login() 返回的 code，后端走 code2Session 取 openid/session_key
//  phoneCode —— getPhoneNumber 返回的手机 code，后端调 getuserphonenumber 换手机号
//  avatarUrl / nickName —— 客户端收集（chooseAvatar + nickname input），随登录一并落库
export interface LoginParams {
  code: string
  phoneCode: string
  avatarUrl?: string
  nickName?: string
}

export interface LoginResult {
  token: string
  userInfo: UserInfo
}

export function phoneLogin(params: LoginParams): Promise<LoginResult> {
  return request({ url: '/api/auth/login', method: 'POST', data: params, showLoading: true, loadingText: '登录中' })
}

export function fetchUserInfo(): Promise<UserInfo> {
  return request({ url: '/api/user/info', method: 'GET' })
}

export function logout(): Promise<void> {
  return request({ url: '/api/auth/logout', method: 'POST', showLoading: true, loadingText: '退出中' })
}

export function saveLoginState(token: string, userInfo: UserInfo): void {
  const app = getApp<IAppOption>()
  if (app) {
    app.globalData.token = token
    app.globalData.userInfo = userInfo
  }
  wx.setStorageSync('token', token)
  wx.setStorageSync('userInfo', userInfo)
}

export function clearLoginState(): void {
  const app = getApp<IAppOption>()
  if (app) {
    app.globalData.token = ''
    app.globalData.userInfo = undefined
  }
  wx.removeStorageSync('token')
  wx.removeStorageSync('userInfo')
}
