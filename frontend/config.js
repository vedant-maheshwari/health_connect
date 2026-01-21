const API_CONFIG = {
  getApiBaseUrl: () => {
    if (window.location.hostname.includes('azurewebsites.net')) {
      return "https://telehealthapp.azurewebsites.net";
    }
    // Use the same hostname and port as the current page
    // This works for both localhost and network access (e.g., 192.168.x.x or 172.20.10.3)
    const hostname = window.location.hostname;
    const port = '8000';
    return `http://${hostname}:${port}`;
  },

  getApiBaseUrlWithouthttp: () => {
    if (window.location.hostname.includes('azurewebsites.net')) {
      return "telehealthapp.azurewebsites.net";
    }
    // Use the same hostname and port as the current page
    const hostname = window.location.hostname;
    const port = '8000';
    return `${hostname}:${port}`;
  },

  endpoints: {
    USER_ME: '/user/me',
    CHATS_CREATE: '/chats/create',
    CHATS_MY: '/chats/my',
    ADD_VITAL: '/add_vital',
    GET_VITALS: '/get_vital',
    FAMILY_VITALS: '/family/patient-records',
    ADMIN_USERS: '/admin/users',
    ADMIN_APPOINTMENTS: '/admin/appointments',
    ADMIN_CHATS: '/admin/chats',
    ADMIN_ANALYTICS: '/admin/analytics/dashboard',
    ADMIN_HEALTH: '/admin/system/health',
    ADMIN_LOGS: '/admin/logs',
    ADMIN_LOGS: '/admin/logs/recent',
    ADMIN_ANALYTICS: '/admin/analytics/overview',
    ADMIN_SETTINGS: '/admin/settings'
  }
};

window.API_CONFIG = API_CONFIG;
