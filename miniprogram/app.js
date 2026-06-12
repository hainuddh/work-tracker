// app.js - 全局初始化
App({
  globalData: {
    baseUrl: 'http://39.102.75.100:8000',
    token: null,
    bosses: []
  },

  onLaunch() {
    // 尝试从本地缓存读取 token
    const token = wx.getStorageSync('token');
    if (token) {
      this.globalData.token = token;
    }
  },

  // 判断是否已登录
  isLoggedIn() {
    return !!this.globalData.token;
  },

  // 设置 token
  setToken(token) {
    this.globalData.token = token;
    wx.setStorageSync('token', token);
  },

  // 清除登录状态
  logout() {
    this.globalData.token = null;
    wx.removeStorageSync('token');
    wx.reLaunch({ url: '/pages/index/index' });
  }
});
