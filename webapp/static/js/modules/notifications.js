/**
 * Notifications Module
 * Handles toast notifications for success/error messages
 */

function showNotification(type, title, message, duration = 5000) {
  const container = document.getElementById('notif');
  if (!container) return;

  const id = 'notif-' + Date.now();

  const notification = document.createElement('div');
  notification.id = id;
  notification.className = `notification ${type}`;
  notification.innerHTML = `
    <div class="notification-icon">
      ${type === 'error' ?
        '<i data-feather="alert-circle" style="color: #da1e28;"></i>' :
        '<i data-feather="check-circle" style="color: #24a148;"></i>'}
    </div>
    <div class="notification-content">
      <div class="notification-title">${title}</div>
      <div class="notification-message">${message}</div>
    </div>
    <button class="notification-close" onclick="this.parentElement.remove()">
      <i data-feather="x" style="width: 16px; height: 16px;"></i>
    </button>
  `;

  container.appendChild(notification);
  if (typeof feather !== 'undefined') feather.replace();

  if (duration > 0) {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (el) el.remove();
    }, duration);
  }
}

function toastError(msg) {
  showNotification('error', 'Error', msg);
}

function toastSuccess(msg) {
  showNotification('success', 'Success', msg);
}

// Backward compatibility: global setLoading function
function setLoading(visible) {
  const overlay = document.getElementById('overlay');
  if (overlay) {
    overlay.classList.toggle('visible', !!visible);
  }
}
