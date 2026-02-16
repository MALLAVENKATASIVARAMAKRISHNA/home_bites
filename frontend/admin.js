// Check if user is admin
const token = localStorage.getItem('access_token');
const user = JSON.parse(localStorage.getItem('user') || '{}');

if (!token || user.role !== 'admin') {
  alert('Admin access required!');
  window.location.href = './index.html';
}

// Display admin info
document.getElementById('adminName').textContent = user.name || 'Admin';
document.getElementById('adminEmail').textContent = user.email || '';

// Logout function
function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  window.location.href = './index.html';
}

function fetchFresh(url, options = {}) {
  return fetch(url, {
    cache: 'no-store',
    ...options
  });
}

// Tab Switching
function switchTab(tabName) {
  // Update nav items
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
  });
  document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

  // Update tab content
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  document.getElementById(`${tabName}-tab`).classList.add('active');

  // Update page title
  const titles = {
    overview: 'Dashboard Overview',
    items: 'Manage Items',
    users: 'Manage Users',
    orders: 'Manage Orders'
  };
  document.getElementById('pageTitle').textContent = titles[tabName];

  // Load data for the tab
  if (tabName === 'items') loadItems();
  if (tabName === 'users') loadUsers();
  if (tabName === 'orders') loadOrders();
}

// Load Overview Stats
async function loadOverviewStats() {
  try {
    const [itemsRes, usersRes, ordersRes] = await Promise.all([
      fetchFresh(`${API_BASE_URL}/items`),
      fetchFresh(`${API_BASE_URL}/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      }),
      fetchFresh(`${API_BASE_URL}/orders`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
    ]);

    const items = await itemsRes.json();
    const users = await usersRes.json();
    const orders = await ordersRes.json();

    document.getElementById('totalItems').textContent = items.length;
    document.getElementById('totalUsers').textContent = users.length;
    document.getElementById('totalOrders').textContent = orders.length;
    
    const pending = orders.filter(o => o.order_status === 'pending').length;
    document.getElementById('pendingOrders').textContent = pending;

    // Load recent orders
    loadRecentOrders(orders);

  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

// Load Recent Orders
function loadRecentOrders(orders) {
  const container = document.getElementById('recentOrders');
  const recent = orders.slice(0, 5);

  if (recent.length === 0) {
    container.innerHTML = '<p class="empty-state">No orders yet</p>';
    return;
  }

  const html = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Order ID</th>
          <th>Amount</th>
          <th>Status</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>
        ${recent.map(order => `
          <tr>
            <td>#${order.order_id}</td>
            <td>₹${order.amount}</td>
            <td><span class="status-badge ${order.order_status}">${order.order_status}</span></td>
            <td>${order.order_date}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
  container.innerHTML = html;
}

// Load Items
async function loadItems() {
  const container = document.getElementById('itemsTable');
  container.innerHTML = '<p class="loading">Loading items...</p>';

  try {
    const res = await fetchFresh(`${API_BASE_URL}/items`);
    const items = await res.json();

    if (!res.ok) {
      throw new Error(items.detail || 'Failed to load items');
    }

    if (!Array.isArray(items)) {
      throw new Error('Invalid items response from server');
    }

    if (items.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🍱</div>
          <p>No items added yet. Click "Add New Item" to get started.</p>
        </div>
      `;
      return;
    }

    const html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Price</th>
            <th>Weight</th>
            <th>Description</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${items.map(item => `
            <tr>
              <td>${item.item_id}</td>
              <td>${escapeHtml(item.item_name)}</td>
              <td>₹${item.price}</td>
              <td>${escapeHtml(item.weight)}</td>
              <td>${escapeHtml((item.description || '').substring(0, 50))}...</td>
              <td>
                <button class="action-btn delete" onclick="deleteItem(${item.item_id})">Delete</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
    container.innerHTML = html;

  } catch (err) {
    container.innerHTML = `<p class="error" style="color: var(--danger); text-align: center; padding: 40px;">Error: ${err.message}</p>`;
  }
}

// Load Users
async function loadUsers() {
  const container = document.getElementById('usersTable');
  container.innerHTML = '<p class="loading">Loading users...</p>';

  try {
    const res = await fetchFresh(`${API_BASE_URL}/users`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const users = await res.json();

    const html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Email</th>
            <th>Phone</th>
            <th>City</th>
            <th>Role</th>
          </tr>
        </thead>
        <tbody>
          ${users.map(user => `
            <tr>
              <td>${user.user_id}</td>
              <td>${escapeHtml(user.name)}</td>
              <td>${escapeHtml(user.email)}</td>
              <td>${user.phone_number}</td>
              <td>${escapeHtml(user.city)}</td>
              <td><span class="status-badge ${user.role}">${user.role}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
    container.innerHTML = html;

  } catch (err) {
    container.innerHTML = `<p class="error" style="color: var(--danger); text-align: center; padding: 40px;">Error: ${err.message}</p>`;
  }
}

// Load Orders
let allOrders = [];

async function loadOrders() {
  const container = document.getElementById('ordersTable');
  container.innerHTML = '<p class="loading">Loading orders...</p>';

  try {
    const res = await fetchFresh(`${API_BASE_URL}/orders`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    allOrders = await res.json();

    displayOrders(allOrders);

  } catch (err) {
    container.innerHTML = `<p class="error" style="color: var(--danger); text-align: center; padding: 40px;">Error: ${err.message}</p>`;
  }
}

function displayOrders(orders) {
  const container = document.getElementById('ordersTable');

  if (orders.length === 0) {
    container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📦</div><p>No orders found</p></div>';
    return;
  }

  const html = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Order ID</th>
          <th>User ID</th>
          <th>Amount</th>
          <th>Status</th>
          <th>Payment</th>
          <th>Date</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${orders.map(order => `
          <tr>
            <td>#${order.order_id}</td>
            <td>${order.user_id}</td>
            <td>₹${order.amount}</td>
            <td>
              <select id="orderStatus-${order.order_id}" class="status-select">
                <option value="pending" ${order.order_status === 'pending' ? 'selected' : ''}>pending</option>
                <option value="confirmed" ${order.order_status === 'confirmed' ? 'selected' : ''}>confirmed</option>
                <option value="delivered" ${order.order_status === 'delivered' ? 'selected' : ''}>delivered</option>
                <option value="cancelled" ${order.order_status === 'cancelled' ? 'selected' : ''}>cancelled</option>
              </select>
            </td>
            <td>
              <select id="paymentStatus-${order.order_id}" class="status-select">
                <option value="pending" ${order.payment_status === 'pending' ? 'selected' : ''}>pending</option>
                <option value="paid" ${order.payment_status === 'paid' ? 'selected' : ''}>paid</option>
                <option value="failed" ${order.payment_status === 'failed' ? 'selected' : ''}>failed</option>
              </select>
            </td>
            <td>${order.order_date}</td>
            <td>
              <button class="action-btn view" onclick="viewOrderDetails(${order.order_id})">View</button>
              <button class="action-btn edit" onclick="updateOrderStatus(${order.order_id})">Update</button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
  container.innerHTML = html;
}

async function updateOrderStatus(orderId) {
  const ordersMessage = document.getElementById('ordersMessage');
  clearAlert(ordersMessage);

  const order = allOrders.find(o => o.order_id === orderId);
  if (!order) {
    setAlert(ordersMessage, 'error', 'Order not found');
    return;
  }

  const orderStatusEl = document.getElementById(`orderStatus-${orderId}`);
  const paymentStatusEl = document.getElementById(`paymentStatus-${orderId}`);
  if (!orderStatusEl || !paymentStatusEl) {
    setAlert(ordersMessage, 'error', 'Unable to read selected status values');
    return;
  }

  const updatedPayload = {
    user_id: order.user_id,
    amount: order.amount,
    order_status: orderStatusEl.value,
    payment_status: paymentStatusEl.value,
    payment_mode: order.payment_mode,
    order_date: order.order_date,
    delivery_date: order.delivery_date,
    address: order.address,
    city: order.city
  };

  try {
    const res = await fetch(`${API_BASE_URL}/orders/${orderId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(updatedPayload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Failed to update order');
    }

    const idx = allOrders.findIndex(o => o.order_id === orderId);
    if (idx >= 0) {
      allOrders[idx] = data;
    }

    const activeFilter = document.getElementById('orderStatusFilter').value;
    if (!activeFilter) {
      displayOrders(allOrders);
    } else {
      displayOrders(allOrders.filter(o => o.order_status === activeFilter));
    }

    loadOverviewStats();
    setAlert(document.getElementById('ordersMessage'), 'success', `Order #${orderId} updated successfully`);
  } catch (err) {
    setAlert(document.getElementById('ordersMessage'), 'error', err.message || 'Failed to update order');
  }
}

function filterOrders() {
  const status = document.getElementById('orderStatusFilter').value;
  
  if (!status) {
    displayOrders(allOrders);
  } else {
    const filtered = allOrders.filter(o => o.order_status === status);
    displayOrders(filtered);
  }
}

// Add Item Modal
function openAddItemModal() {
  document.getElementById('addItemModal').classList.add('active');
  document.body.style.overflow = 'hidden';
  updateItemMeasureInput();
}

function closeAddItemModal() {
  document.getElementById('addItemModal').classList.remove('active');
  document.body.style.overflow = 'auto';
  document.getElementById('addItemForm').reset();
  updateItemMeasureInput();
  clearAlert(document.getElementById('addItemMessage'));
}

function updateItemMeasureInput() {
  const type = document.getElementById('itemMeasureType').value;
  const label = document.getElementById('itemWeightLabel');
  const input = document.getElementById('itemWeight');

  if (type === 'pieces') {
    label.textContent = 'Pieces';
    input.placeholder = '12';
  } else {
    label.textContent = 'Weight';
    input.placeholder = '500g';
  }
}

document.getElementById('itemMeasureType').addEventListener('change', updateItemMeasureInput);

// Add Item Form Handler
document.getElementById('addItemForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = document.getElementById('addItemMessage');
  const btn = document.getElementById('addItemBtn');
  clearAlert(message);

  const payload = {
    item_name: document.getElementById('itemName').value.trim(),
    price: Number(document.getElementById('itemPrice').value),
    weight: (() => {
      const measureType = document.getElementById('itemMeasureType').value;
      const value = document.getElementById('itemWeight').value.trim();
      if (measureType === 'pieces') {
        return /\bpiece/.test(value.toLowerCase()) ? value : `${value} pieces`;
      }
      return value;
    })(),
    description: document.getElementById('itemDescription').value.trim(),
    photos: document.getElementById('itemPhotos').value.trim() || '',
    videos: document.getElementById('itemVideos').value.trim() || ''
  };

  try {
    setButtonLoading(btn, 'Adding...', true);

    const res = await fetch(`${API_BASE_URL}/items/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || 'Failed to add item');
    }

    setAlert(message, 'success', 'Item added successfully!');
    document.getElementById('addItemForm').reset();
    
    setTimeout(() => {
      closeAddItemModal();
      loadItems();
      loadOverviewStats();
    }, 1500);

  } catch (err) {
    setAlert(message, 'error', err.message);
  } finally {
    setButtonLoading(btn, 'Add Item', false);
  }
});

// Delete Item
async function deleteItem(itemId) {
  if (!confirm('Are you sure you want to delete this item?')) return;

  try {
    const res = await fetch(`${API_BASE_URL}/items/${itemId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!res.ok) {
      throw new Error('Failed to delete item');
    }

    alert('Item deleted successfully!');
    loadItems();
    loadOverviewStats();

  } catch (err) {
    alert('Error: ' + err.message);
  }
}

// View Order Details
async function viewOrderDetails(orderId) {
  document.getElementById('orderDetailsModal').classList.add('active');
  document.body.style.overflow = 'hidden';
  
  const container = document.getElementById('orderDetailsContent');
  container.innerHTML = '<p class="loading">Loading order details...</p>';

  try {
    const res = await fetchFresh(`${API_BASE_URL}/orders/${orderId}/complete`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    const data = await res.json();
    const order = data.order;
    const items = data.items;

    const html = `
      <div class="order-info">
        <h3>Order Information</h3>
        <div class="order-info-grid">
          <div class="order-info-item">
            <label>Order ID</label>
            <span>#${order.order_id}</span>
          </div>
          <div class="order-info-item">
            <label>User ID</label>
            <span>${order.user_id}</span>
          </div>
          <div class="order-info-item">
            <label>Total Amount</label>
            <span>₹${order.amount}</span>
          </div>
          <div class="order-info-item">
            <label>Order Status</label>
            <span class="status-badge ${order.order_status}">${order.order_status}</span>
          </div>
          <div class="order-info-item">
            <label>Payment Status</label>
            <span class="status-badge ${order.payment_status}">${order.payment_status}</span>
          </div>
          <div class="order-info-item">
            <label>Payment Mode</label>
            <span>${order.payment_mode}</span>
          </div>
          <div class="order-info-item">
            <label>Order Date</label>
            <span>${order.order_date}</span>
          </div>
          <div class="order-info-item">
            <label>Delivery Date</label>
            <span>${order.delivery_date || 'Not set'}</span>
          </div>
          <div class="order-info-item">
            <label>Address</label>
            <span>${escapeHtml(order.address)}</span>
          </div>
          <div class="order-info-item">
            <label>City</label>
            <span>${escapeHtml(order.city)}</span>
          </div>
        </div>
      </div>

      <div class="order-items">
        <h3>Order Items</h3>
        ${items.map(item => `
          <div class="order-item">
            <div class="order-item-header">
              <span>${escapeHtml(item.item_name)}</span>
              <span>₹${item.price} × ${item.quantity} = ₹${item.price * item.quantity}</span>
            </div>
            <div class="order-item-details">
              ${escapeHtml(item.description)} • ${escapeHtml(item.weight)}
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.innerHTML = html;

  } catch (err) {
    container.innerHTML = `<p class="error" style="color: var(--danger);">Error: ${err.message}</p>`;
  }
}

function closeOrderDetailsModal() {
  document.getElementById('orderDetailsModal').classList.remove('active');
  document.body.style.overflow = 'auto';
}

// Escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Close modals on Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeAddItemModal();
    closeOrderDetailsModal();
  }
});

// Initialize
loadOverviewStats();
