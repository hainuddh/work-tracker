// app.js - 全局初始化（微信登录）
const { api } = require('./utils/api');

App({
  globalData: {
    baseUrl: 'https://api.ddhlf.xyz',
    token: null,
    user: null,  // { id, nickname, avatar_url }
    bosses: []
  },

  onLaunch() {
    // 尝试从本地缓存恢复登录状态
    const token = wx.getStorageSync('token');
    const user = wx.getStorageSync('user');
    if (token && user) {
      this.globalData.token = token;
      this.globalData.user = user;
    } else {
      // 没有缓存 token，尝试静默 wx.login 重新获取
      this.autoLogin();
    }
  },

  // 自动登录：wx.login 获取 code，后端换 token
  autoLogin() {
    wx.login({
      success: async (res) => {
        if (!res.code) return;
        try {
          const data = await api.wechatLogin(res.code);
          this.globalData.token = data.token;
          this.globalData.user = data.user;
          wx.setStorageSync('token', data.token);
          wx.setStorageSync('user', data.user);
        } catch (e) {
          // 静默失败（可能是首次使用，用户未授权）
          console.log('自动登录失败（可能需要手动授权）:', e);
        }
      }
    });
  },

  // 判断是否已登录
  isLoggedIn() {
    return !!this.globalData.token;
  },

  // 设置 token（用于旧登录流程，保留兼容）
  setToken(token) {
    this.globalData.token = token;
    wx.setStorageSync('token', token);
  },

  // 清除登录状态
  logout() {
    this.globalData.token = null;
    this.globalData.user = null;
    wx.removeStorageSync('token');
    wx.removeStorageSync('user');
    wx.reLaunch({ url: '/pages/index/index' });
  }
});
