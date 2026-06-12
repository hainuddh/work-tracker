// pages/bosses/bosses.js - 老板管理页面
const { api } = require('../../utils/api');

Page({
  data: {
    bosses: [],
    searchText: '',
    showDialog: false,
    isEdit: false,
    formData: { name: '', phone: '', unit_price: '', remark: '' },
    editId: null
  },

  onShow() {
    this.loadBosses();
  },

  async loadBosses() {
    try {
      const bosses = await api.listBosses({ limit: 1000 });
      this.setData({ bosses });
    } catch (e) {
      console.error('加载老板列表失败:', e);
    }
  },

  onSearch(e) {
    const text = e.detail.value;
    this.setData({ searchText: text });
    if (!text) {
      this.setData({ bosses: [] });
      return;
    }
    api.listBosses({ search: text, limit: 100 }).then(bosses => {
      this.setData({ bosses });
    });
  },

  showAddDialog() {
    this.setData({
      showDialog: true,
      isEdit: false,
      formData: { name: '', phone: '', unit_price: '', remark: '' },
      editId: null
    });
  },

  onEditBoss(e) {
    const boss = e.currentTarget.dataset.boss;
    this.setData({
      showDialog: true,
      isEdit: true,
      editId: boss.id,
      formData: {
        name: boss.name,
        phone: boss.phone,
        unit_price: boss.unit_price,
        remark: boss.remark || ''
      }
    });
  },

  hideDialog() {
    this.setData({ showDialog: false });
  },

  onFormInput(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    this.setData({ [`formData.${field}`]: value });
  },

  async onSave() {
    const { formData, isEdit, editId } = this.data;
    
    if (!formData.name.trim() || !formData.phone.trim()) {
      return wx.showToast({ title: '姓名和手机号必填', icon: 'none' });
    }

    try {
      if (isEdit) {
        await api.updateBoss(editId, formData);
        wx.showToast({ title: '修改成功' });
      } else {
        await api.createBoss(formData);
        wx.showToast({ title: '添加成功' });
      }
      this.hideDialog();
      this.loadBosses();
    } catch (e) {
      // error handled in api.js
    }
  }
});
