// pages/index/index.js - 首页
const { api } = require('../../utils/api');

Page({
  data: {
    isLoggedIn: false,
    password: '',
    stats: { totalBosses: 0, totalLogs: 0, totalAmount: 0 },
    recentLogs: []
  },

  onShow() {
    const app = getApp();
    this.setData({ isLoggedIn: app.isLoggedIn() });
    if (this.data.isLoggedIn) {
      this.loadDashboard();
    }
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value });
  },

  async onLogin() {
    const pwd = this.data.password.trim();
    if (!pwd) return wx.showToast({ title: '请输入密码', icon: 'none' });
    
    try {
      const res = await api.login(pwd);
      getApp().setToken(res.token);
      this.setData({ isLoggedIn: true, password: '' });
      wx.showToast({ title: '登录成功' });
      this.loadDashboard();
    } catch (e) {
      // error handled in api.js
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
      // 并行加载老板列表和最近日志
      const [bosses, logs] = await Promise.all([
        api.listBosses({ limit: 1000 }),
        api.listLogs({ limit: 5 })
      ]);
      
      const totalAmount = logs.reduce((s, l) => s + (l.amount || 0), 0);
      
      // 格式化最近日志日期
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
    } catch (e) {
      // handled
    } finally {
      wx.hideLoading();
    }
  }
});
