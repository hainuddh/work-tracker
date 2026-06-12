// pages/stats/stats.js - 统计导出页面
const { api } = require('../../utils/api');

Page({
  data: {
    bosses: [],
    bossNames: [],
    bossIndex: -1,
    startDate: '',
    endDate: '',
    stats: [],
    totalAmount: 0,
    totalDays: 0,
    totalCount: 0,
    hasCalculated: false
  },

  onShow() {
    this.loadBosses();
  },

  async loadBosses() {
    try {
      const bosses = await api.listBosses({ limit: 1000 });
      this.setData({ bosses, bossNames: bosses.map(b => b.name) });
    } catch (e) {}
  },

  onBossChange(e) { this.setData({ bossIndex: parseInt(e.detail.value) }); },
  onStartDate(e) { this.setData({ startDate: e.detail.value }); },
  onEndDate(e) { this.setData({ endDate: e.detail.value }); },

  async calcStats() {
    const params = {};
    if (this.data.bossIndex >= 0) params.boss_id = this.data.bosses[this.data.bossIndex].id;
    if (this.data.startDate) params.start_date = this.data.startDate;
    if (this.data.endDate) params.end_date = this.data.endDate;

    try {
      const stats = await api.getStats(params);
      
      // 格式化日期
      const formattedStats = stats.map(s => ({
        ...s,
        logs: (s.logs || []).map(l => ({
          ...l,
          date: typeof l.date === 'string' ? l.date : (l.date || '').split('T')[0]
        }))
      }));

      const totalAmount = stats.reduce((sum, s) => sum + s.total_amount, 0);
      const totalDays = stats.reduce((sum, s) => sum + s.total_days, 0);
      const totalCount = stats.reduce((sum, s) => sum + s.log_count, 0);

      this.setData({
        stats: formattedStats,
        totalAmount: totalAmount.toFixed(2),
        totalDays: totalDays.toFixed(1),
        totalCount,
        hasCalculated: true
      });
    } catch (e) {
      console.error('统计失败:', e);
    }
  },

  async onExport(e) {
    const fmt = e.currentTarget.dataset.fmt;
    wx.showLoading({ title: `正在导出${fmt.toUpperCase()}...` });
    
    try {
      const params = {};
      if (this.data.bossIndex >= 0) params.boss_id = this.data.bosses[this.data.bossIndex].id;
      if (this.data.startDate) params.start_date = this.data.startDate;
      if (this.data.endDate) params.end_date = this.data.endDate;

      // 注意：小程序中导出需要下载文件
      // 这里用 request 发 POST 请求拿到二进制数据
      const app = getApp();
      
      wx.request({
        url: `${app.globalData.baseUrl}/api/logs/export`,
        method: 'POST',
        data: { ...params, fmt },
        header: { 'Authorization': `Bearer ${app.globalData.token}` },
        responseType: 'arraybuffer',
        success(res) {
          const fs = wx.getFileSystemManager();
          const extMap = { xlsx: '.xlsx', csv: '.csv', json: '.json' };
          const fileName = `work_logs${extMap[fmt]}`;
          const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;
          
          fs.writeFileSync(filePath, res.data, 'binary');
          
          wx.hideLoading();
          wx.showToast({ title: `已导出 ${fmt.toUpperCase()}`, icon: 'success' });
          
          // 尝试打开分享
          wx.openDocument({
            filePath,
            fileType: extMap[fmt].replace('.', ''),
            showMenu: true,
            success: () => {},
            fail: () => {
              wx.showToast({ title: '文件已保存', icon: 'none' });
            }
          });
        },
        fail(err) {
          wx.hideLoading();
          wx.showToast({ title: '导出失败', icon: 'none' });
        }
      });
    } catch (e) {
      wx.hideLoading();
    }
  }
});
