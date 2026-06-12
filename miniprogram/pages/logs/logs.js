// pages/logs/logs.js - 日志管理页面
const { api } = require('../../utils/api');

Page({
  data: {
    logs: [],
    bosses: [],
    bossNames: [],
    
    // 筛选
    filterBossIndex: -1,
    filterStartDate: '',
    filterEndDate: '',
    
    // 对话框
    showDialog: false,
    isEdit: false,
    bossIndex: -1,
    formData: {
      date: '',
      location: '',
      content: '',
      days: 0.5,
      amount: '',
      status: 0
    },
    editId: null
  },

  onShow() {
    this.loadBosses();
    this.loadLogs();
  },

  async loadBosses() {
    try {
      const bosses = await api.listBosses({ limit: 1000 });
      this.setData({
        bosses,
        bossNames: bosses.map(b => b.name)
      });
    } catch (e) {
      console.error('加载老板失败:', e);
    }
  },

  async loadLogs() {
    try {
      const params = {};
      if (this.data.filterBossIndex >= 0) params.boss_id = this.data.bosses[this.data.filterBossIndex].id;
      if (this.data.filterStartDate) params.start_date = this.data.filterStartDate;
      if (this.data.filterEndDate) params.end_date = this.data.filterEndDate;
      
      const logs = await api.listLogs(params);
      this.setData({ logs });
    } catch (e) {
      console.error('加载日志失败:', e);
    }
  },

  onFilterBoss(e) {
    this.setData({ filterBossIndex: parseInt(e.detail.value) });
    this.loadLogs();
  },

  onFilterStartDate(e) {
    this.setData({ filterStartDate: e.detail.value });
    this.loadLogs();
  },

  onFilterEndDate(e) {
    this.setData({ filterEndDate: e.detail.value });
    this.loadLogs();
  },

  resetFilter() {
    this.setData({ filterBossIndex: -1, filterStartDate: '', filterEndDate: '' });
    this.loadLogs();
  },

  showLogDialog() {
    this.setData({
      showDialog: true,
      isEdit: false,
      bossIndex: -1,
      editId: null,
      formData: { date: '', location: '', content: '', days: 0.5, amount: '', status: 0 }
    });
  },

  onEditLog(e) {
    const log = e.currentTarget.dataset.log;
    const bossIndex = this.data.bosses.findIndex(b => b.id === log.boss_id);
    this.setData({
      showDialog: true,
      isEdit: true,
      editId: log.id,
      bossIndex,
      formData: {
        date: typeof log.date === 'string' ? log.date : log.date.split('T')[0],
        location: log.location || '',
        content: log.content,
        days: log.days,
        amount: log.amount === 0 ? '' : String(log.amount),
        status: log.status
      }
    });
  },

  hideDialog() { this.setData({ showDialog: false }); },

  onBossChange(e) { this.setData({ bossIndex: parseInt(e.detail.value) }); },

  onDateChange(e) { this.setData({ 'formData.date': e.detail.value }); },

  onStatusChange(e) { this.setData({ 'formData.status': parseInt(e.detail.value) }); },

  onFormInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({ [`formData.${field}`]: e.detail.value });
  },

  async onSave() {
    const { formData, bossIndex, isEdit, editId } = this.data;
    
    if (!formData.date || !formData.content || bossIndex < 0) {
      return wx.showToast({ title: '请填写必填项', icon: 'none' });
    }

    const data = {
      boss_id: this.data.bosses[bossIndex].id,
      date: formData.date,
      location: formData.location,
      content: formData.content,
      days: parseFloat(formData.days) || 0.5,
      amount: formData.amount ? parseFloat(formData.amount) : null,
      status: parseInt(formData.status) || 0
    };

    try {
      if (isEdit) {
        await api.updateLog(editId, data);
        wx.showToast({ title: '修改成功' });
      } else {
        await api.createLog(data);
        wx.showToast({ title: '记录成功' });
      }
      this.hideDialog();
      this.loadLogs();
    } catch (e) {
      // handled
    }
  },

  async onDelete() {
    wx.showModal({
      title: '确认删除',
      content: '删除后无法恢复',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.deleteLog(this.data.editId);
            wx.showToast({ title: '已删除' });
            this.hideDialog();
            this.loadLogs();
          } catch (e) {}
        }
      }
    });
  }
});
