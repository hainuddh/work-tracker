// utils/api.js - 统一 API 请求封装
const app = getApp();

function request(url, method, data, needAuth = true) {
  return new Promise((resolve, reject) => {
    const header = {
      'Content-Type': 'application/json'
    };
    
    if (needAuth && app.globalData.token) {
      header['Authorization'] = `Bearer ${app.globalData.token}`;
    }

    wx.request({
      url: `${app.globalData.baseUrl}${url}`,
      method,
      data,
      header,
      success(res) {
        if (res.statusCode === 401) {
          app.logout();
          wx.showToast({ title: '请先登录', icon: 'none' });
          reject(new Error('Unauthorized'));
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          const detail = res.data?.detail || res.data?.message || '请求失败';
          wx.showToast({ title: detail, icon: 'none' });
          reject(new Error(detail));
        }
      },
      fail(err) {
        wx.showToast({ title: '网络错误', icon: 'none' });
        reject(err);
      }
    });
  });
}

const api = {
  // 认证
  login(password) { return request('/api/auth/login', 'POST', { password }); },
  
  // 老板 CRUD
  listBosses(params = {}) { return request('/api/bosses/', 'GET', params); },
  createBoss(data) { return request('/api/bosses/', 'POST', data); },
  updateBoss(id, data) { return request(`/api/bosses/${id}`, 'PUT', data); },
  deleteBoss(id) { return request(`/api/bosses/${id}`, 'DELETE'); },
  
  // 日志 CRUD
  listLogs(params = {}) { return request('/api/logs/', 'GET', params); },
  createLog(data) { return request('/api/logs/', 'POST', data); },
  updateLog(id, data) { return request(`/api/logs/${id}`, 'PUT', data); },
  deleteLog(id) { return request(`/api/logs/${id}`, 'DELETE'); },
  
  // 统计
  getStats(params = {}) { return request('/api/logs/stats', 'POST', params); },
  
  // 导出
  exportLogs(fmt = 'xlsx', params = {}) {
    params.fmt = fmt;
    return request('/api/logs/export', 'POST', params, true);
  },
  
  // 备份
  backup() { return request('/api/backup/manual', 'POST'); },
  listBackups() { return request('/api/backup/list', 'GET'); },
  cleanupBackups() { return request('/api/backup/cleanup', 'DELETE'); }
};

module.exports = { api };
