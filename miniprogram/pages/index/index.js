// pages/index/index.js - 首页
const { api } = require('../../utils/api');

Page({
  data: {
    isLoggedIn: false,
    user: null,
    stats: { totalBosses: 0, totalLogs: 0, totalAmount: 0 },
    recentLogs: []
  },

  onShow() {
    const app = getApp();
    this.setData({
      isLoggedIn: app.isLoggedIn(),
      user: app.globalData.user
    });
    if (this.data.isLoggedIn) {
      this.loadDashboard();
    }
  },

  // 微信一键登录
  async onWechatLogin() {
    wx.showLoading({ title: '登录中...' });
    try {
      // 1. 获取微信登录凭证 code
      const loginRes = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject });
      });
      
      // 2. 用 code 向后端换取 JWT token
      const loginData = await api.wechatLogin(loginRes.code);
      
      // 3. 保存 token 和用户信息
      const app = getApp();
      app.globalData.token = loginData.token;
      app.globalData.user = loginData.user;
      wx.setStorageSync('token', loginData.token);
      wx.setStorageSync('user', loginData.user);
      
      this.setData({
        isLoggedIn: true,
        user: loginData.user
      });
      
      wx.showToast({ title: '登录成功' });
      this.loadDashboard();
    } catch (e) {
      wx.showToast({ title: '登录失败，请重试', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  // 更新用户资料（昵称、头像）
  async updateUserInfo() {
    try {
      const userInfo = await new Promise((resolve, reject) => {
        wx.getUserProfile({
          desc: '用于完善个人资料',
          success: resolve,
          fail: reject
        });
      });
      
      await api.updateProfile(userInfo.userInfo.nickName, userInfo.userInfo.avatarUrl);
      
      // 更新本地缓存
      const app = getApp();
      app.globalData.user.nickname = userInfo.userInfo.nickName;
      app.globalData.user.avatar_url = userInfo.userInfo.avatarUrl;
      wx.setStorageSync('user', app.globalData.user);
      
      this.setData({ user: app.globalData.user });
      wx.showToast({ title: '资料已更新' });
    } catch (e) {
      wx.showToast({ title: '授权被拒绝', icon: 'none' });
    }
  },

  onLogout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) getApp().logout();
      }
    });
  },

  goTo(e) {
    wx.navigateTo({ url: e.currentTarget.dataset.url });
  },

  async loadDashboard() {
    try {
      const [bosses, logs] = await Promise.all([
        api.listBosses({ limit: 1000 }),
        api.listLogs({ limit: 5 })
      ]);
      
      const totalAmount = logs.reduce((s, l) => s + (l.amount || 0), 0);
      
      const recentLogs = logs.map(l => ({
        ...l,
        date: (new Date(l.date)).toLocaleDateString('zh-CN')
      }));

      this.setData({
        'stats.totalBosses': bosses.length,
        'stats.totalLogs': logs.length,
        'stats.totalAmount': totalAmount.toFixed(2),
        recentLogs
      });
    } catch (e) {
      console.error('加载仪表盘失败:', e);
    }
  },

  async onBackup() {
    wx.showLoading({ title: '备份中...' });
    try {
      await api.backup();
      wx.showToast({ title: '备份成功' });
    } catch (e) {}
    finally {
      wx.hideLoading();
    }
  }
});
