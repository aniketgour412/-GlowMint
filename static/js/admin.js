/**
 * GlowMint Accessories — Admin Dashboard Control Script
 */

let currentOrderPage = 1;
let activeModalOrderId = null;

document.addEventListener('DOMContentLoaded', () => {
  loadDashboardData();
  loadProductConfig();
  loadCouponsData();
  loadSettingsData();
  setupEventListeners();
});

function switchTab(tabId) {
  document.querySelectorAll('.admin-tab-btn').forEach(btn => {
    btn.classList.remove('border-gold-500', 'text-plum-900');
    btn.classList.add('border-transparent', 'text-gray-500');
  });
  const activeBtn = document.getElementById(`tab-btn-${tabId}`);
  if (activeBtn) {
    activeBtn.classList.add('border-gold-500', 'text-plum-900');
    activeBtn.classList.remove('border-transparent', 'text-gray-500');
  }

  document.querySelectorAll('.admin-tab-content').forEach(content => {
    content.classList.add('hidden');
  });
  const activeContent = document.getElementById(`tab-content-${tabId}`);
  if (activeContent) {
    activeContent.classList.remove('hidden');
  }

  if (tabId === 'orders') {
    loadOrdersData();
  }
}

// -----------------------------------------------------------------------------
// 1. Dashboard Overview
// -----------------------------------------------------------------------------
async function loadDashboardData() {
  try {
    const res = await fetch('/api/admin/dashboard');
    if (res.status === 401) {
      window.location.href = '/admin/login';
      return;
    }
    const data = await res.json();

    document.getElementById('kpi-revenue').textContent = `₹${data.paid_revenue.toFixed(2)}`;
    document.getElementById('kpi-total-orders').textContent = data.total_orders;
    document.getElementById('kpi-paid-orders-sub').textContent = `${data.paid_orders} paid • ${data.pending_orders} pending`;
    document.getElementById('kpi-aov').textContent = `₹${data.average_order_value.toFixed(2)}`;
    document.getElementById('kpi-stock').textContent = `${data.product_stock} units`;
    document.getElementById('kpi-stock-status').textContent = data.is_in_stock ? 'In Stock (Live)' : 'Sold Out / Inactive';

    // Render recent orders
    const tbody = document.getElementById('recent-orders-tbody');
    if (!data.recent_orders || data.recent_orders.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="py-4 text-center text-gray-400">No orders recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = data.recent_orders.map(o => `
      <tr class="hover:bg-gray-50">
        <td class="py-3 font-mono font-bold text-plum-900">${o.id}</td>
        <td class="py-3 font-medium text-gray-800">${escapeHtml(o.customer_name)}</td>
        <td class="py-3 font-mono text-gray-600">${escapeHtml(o.customer_phone)}</td>
        <td class="py-3 font-semibold text-gray-900">₹${o.total_amount.toFixed(2)}</td>
        <td class="py-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${o.payment_status === 'paid' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
            ${o.payment_status.toUpperCase()}
          </span>
        </td>
        <td class="py-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-800">
            ${o.order_status.toUpperCase()}
          </span>
        </td>
        <td class="py-3 text-right">
          <button onclick="openOrderDetailModal('${o.id}')" class="text-plum-900 font-bold hover:underline">
            Manage
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading dashboard:', err);
  }
}

// -----------------------------------------------------------------------------
// 2. Orders Management
// -----------------------------------------------------------------------------
async function loadOrdersData(page = 1) {
  currentOrderPage = page;
  const search = document.getElementById('order-search-input')?.value.trim() || '';
  const statusFilter = document.getElementById('order-status-filter')?.value || 'all';

  const params = new URLSearchParams({
    page: currentOrderPage,
    limit: 20,
    status_filter: statusFilter
  });
  if (search) params.append('search', search);

  try {
    const res = await fetch(`/api/admin/orders?${params.toString()}`);
    if (res.status === 401) {
      window.location.href = '/admin/login';
      return;
    }
    const data = await res.json();

    const tbody = document.getElementById('all-orders-tbody');
    if (!data.orders || data.orders.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="py-6 text-center text-gray-400">No matching orders found.</td></tr>';
      document.getElementById('pagination-info').textContent = 'Showing 0 orders';
      return;
    }

    tbody.innerHTML = data.orders.map(o => `
      <tr class="hover:bg-gray-50">
        <td class="py-3 font-mono font-bold text-plum-900">${o.id}</td>
        <td class="py-3">
          <div class="font-medium text-gray-900">${escapeHtml(o.customer_name)}</div>
          <div class="font-mono text-[10px] text-gray-500">${escapeHtml(o.customer_phone)}</div>
        </td>
        <td class="py-3 text-gray-600">${escapeHtml(o.city)}, ${escapeHtml(o.state)} (${escapeHtml(o.pincode)})</td>
        <td class="py-3">
          <span class="font-bold text-gray-900">₹${o.total_amount.toFixed(2)}</span>
          <span class="text-[10px] text-gray-500 block">Qty: ${o.quantity}</span>
        </td>
        <td class="py-3">
          ${o.coupon_code ? `<span class="px-1.5 py-0.5 font-mono text-[10px] font-bold bg-gold-100 text-gold-900 rounded">${o.coupon_code}</span>` : '<span class="text-gray-400">—</span>'}
        </td>
        <td class="py-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${o.payment_status === 'paid' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
            ${o.payment_status.toUpperCase()}
          </span>
        </td>
        <td class="py-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-800">
            ${o.order_status.toUpperCase()}
          </span>
          ${o.tracking_number ? `<span class="text-[9px] block text-gray-500 font-mono mt-0.5">${o.tracking_number}</span>` : ''}
        </td>
        <td class="py-3 text-right">
          <button onclick="openOrderDetailModal('${o.id}')" class="px-2.5 py-1 bg-ivory-100 hover:bg-ivory-200 text-plum-900 font-bold rounded-lg border border-gray-300">
            View / Edit
          </button>
        </td>
      </tr>
    `).join('');

    document.getElementById('pagination-info').textContent = `Page ${data.page} of ${data.pages} (${data.total} total orders)`;
    document.getElementById('btn-page-prev').disabled = data.page <= 1;
    document.getElementById('btn-page-next').disabled = data.page >= data.pages;
  } catch (err) {
    console.error('Error fetching orders:', err);
  }
}

async function openOrderDetailModal(orderId) {
  activeModalOrderId = orderId;
  const modal = document.getElementById('order-detail-modal');

  try {
    const res = await fetch(`/api/admin/orders/${orderId}`);
    if (!res.ok) {
      alert('Order could not be loaded.');
      return;
    }
    const order = await res.json();

    document.getElementById('modal-order-id').textContent = order.id;
    document.getElementById('modal-customer-name').textContent = order.customer_name;
    document.getElementById('modal-customer-phone').textContent = order.customer_phone;
    document.getElementById('modal-customer-email').textContent = order.customer_email;
    document.getElementById('modal-address').innerHTML = `
      ${escapeHtml(order.address_line)}${order.landmark ? ', Landmark: ' + escapeHtml(order.landmark) : ''}<br>
      ${escapeHtml(order.city)}, ${escapeHtml(order.state)} — <strong>${escapeHtml(order.pincode)}</strong>
    `;

    document.getElementById('modal-quantity').textContent = `${order.quantity} pair(s)`;
    document.getElementById('modal-subtotal').textContent = `₹${order.subtotal.toFixed(2)}`;
    document.getElementById('modal-coupon-code').textContent = order.coupon_code || 'None';
    document.getElementById('modal-discount').textContent = `-₹${order.discount_amount.toFixed(2)}`;
    document.getElementById('modal-shipping').textContent = order.shipping_fee === 0 ? 'FREE' : `₹${order.shipping_fee.toFixed(2)}`;
    document.getElementById('modal-total').textContent = `₹${order.total_amount.toFixed(2)}`;

    document.getElementById('modal-payment-status').value = order.payment_status;
    document.getElementById('modal-order-status').value = order.order_status;
    document.getElementById('modal-courier-name').value = order.courier_name || '';
    document.getElementById('modal-tracking-number').value = order.tracking_number || '';
    document.getElementById('modal-notes').value = order.notes || '';

    modal.classList.remove('hidden');
    modal.classList.add('flex');
  } catch (err) {
    console.error('Error opening order detail:', err);
  }
}

function closeOrderDetailModal() {
  const modal = document.getElementById('order-detail-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
  activeModalOrderId = null;
}

// -----------------------------------------------------------------------------
// 3. Product Configuration
// -----------------------------------------------------------------------------
async function loadProductConfig() {
  try {
    const res = await fetch('/api/admin/product');
    if (!res.ok) return;
    const p = await res.json();

    document.getElementById('prod-title').value = p.title || '';
    document.getElementById('prod-subtitle').value = p.subtitle || '';
    document.getElementById('prod-regular-price').value = p.regular_price || 600;
    document.getElementById('prod-reference-price').value = p.reference_price || 600;
    document.getElementById('prod-stock').value = p.stock_quantity || 100;
    document.getElementById('prod-is-active').value = p.is_active ? '1' : '0';
    document.getElementById('prod-description').value = p.description || '';
    document.getElementById('prod-led-note').value = p.led_note || '';
    document.getElementById('prod-package-contents').value = p.package_contents || '';
    document.getElementById('prod-care-instructions').value = p.care_instructions || '';
  } catch (err) {
    console.error('Error loading product:', err);
  }
}

// -----------------------------------------------------------------------------
// 4. Milestone Coupons
// -----------------------------------------------------------------------------
async function loadCouponsData() {
  try {
    const res = await fetch('/api/admin/coupons');
    if (!res.ok) return;
    const coupons = await res.json();

    const tbody = document.getElementById('coupons-tbody');
    tbody.innerHTML = coupons.map(c => `
      <tr class="hover:bg-gray-50">
        <td class="py-3 font-mono font-bold text-plum-900">${c.code}</td>
        <td class="py-3">
          <input type="number" id="coupon-pct-${c.id}" value="${c.discount_percent}" class="w-16 px-2 py-1 text-xs border rounded"> %
        </td>
        <td class="py-3">
          ₹ <input type="number" id="coupon-cap-${c.id}" value="${c.max_discount}" class="w-20 px-2 py-1 text-xs border rounded">
        </td>
        <td class="py-3">
          ₹ <input type="number" id="coupon-min-${c.id}" value="${c.min_order_val}" class="w-20 px-2 py-1 text-xs border rounded">
        </td>
        <td class="py-3">
          <select id="coupon-req-${c.id}" class="px-2 py-1 text-xs border rounded">
            <option value="1" ${c.required_order_number === 1 ? 'selected' : ''}>1st Order Only</option>
            <option value="2" ${c.required_order_number === 2 ? 'selected' : ''}>2nd Order Only</option>
            <option value="3" ${c.required_order_number === 3 ? 'selected' : ''}>3rd Order Only</option>
            <option value="0" ${c.required_order_number === 0 ? 'selected' : ''}>Any Order</option>
          </select>
        </td>
        <td class="py-3 font-semibold text-gray-700">${c.usage_count} times</td>
        <td class="py-3">
          <select id="coupon-active-${c.id}" class="px-2 py-1 text-xs border rounded">
            <option value="1" ${c.is_active ? 'selected' : ''}>Active</option>
            <option value="0" ${!c.is_active ? 'selected' : ''}>Inactive</option>
          </select>
        </td>
        <td class="py-3 text-right">
          <button onclick="saveCoupon(${c.id})" class="px-3 py-1 bg-plum-800 text-gold-100 rounded text-xs font-bold hover:bg-plum-700">
            Save
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading coupons:', err);
  }
}

async function saveCoupon(couponId) {
  const payload = {
    discount_percent: parseFloat(document.getElementById(`coupon-pct-${couponId}`).value),
    max_discount: parseFloat(document.getElementById(`coupon-cap-${couponId}`).value),
    min_order_val: parseFloat(document.getElementById(`coupon-min-${couponId}`).value),
    required_order_number: parseInt(document.getElementById(`coupon-req-${couponId}`).value),
    is_active: parseInt(document.getElementById(`coupon-active-${couponId}`).value),
    description: ''
  };

  const feedback = document.getElementById('coupons-feedback');
  try {
    const res = await fetch(`/api/admin/coupons/${couponId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      feedback.textContent = 'Coupon rules updated successfully!';
      feedback.className = 'p-3 rounded-lg text-xs font-semibold mb-4 bg-emerald-50 text-emerald-800 border border-emerald-200';
      feedback.classList.remove('hidden');
    } else {
      feedback.textContent = 'Failed to update coupon.';
      feedback.className = 'p-3 rounded-lg text-xs font-semibold mb-4 bg-rose-50 text-rose-800 border border-rose-200';
      feedback.classList.remove('hidden');
    }
  } catch (err) {
    console.error(err);
  }
}

// -----------------------------------------------------------------------------
// 5. Store & Gateway Settings
// -----------------------------------------------------------------------------
async function loadSettingsData() {
  try {
    const res = await fetch('/api/admin/settings');
    if (!res.ok) return;
    const s = await res.json();

    document.getElementById('setting-announcement').value = s.announcement_bar || '';
    document.getElementById('setting-shipping-fee').value = s.shipping_fee || '0';
    document.getElementById('setting-free-thresh').value = s.free_shipping_threshold || '0';
    document.getElementById('setting-support-email').value = s.support_email || '';
    document.getElementById('setting-support-phone').value = s.support_phone || '';
    document.getElementById('setting-support-hours').value = s.support_hours || '';

    document.getElementById('rzp-key-preview').textContent = s.razorpay_key_preview || 'Not Configured';
    const liveEl = document.getElementById('rzp-live-status');
    if (s.razorpay_configured === 'true') {
      liveEl.textContent = 'Live Active';
      liveEl.className = 'text-emerald-600 font-bold ml-1';
    } else {
      liveEl.textContent = 'Simulation / Test Mode';
      liveEl.className = 'text-amber-600 font-bold ml-1';
    }
  } catch (err) {
    console.error('Error loading settings:', err);
  }
}

// -----------------------------------------------------------------------------
// Form Submissions & Event Listeners
// -----------------------------------------------------------------------------
function setupEventListeners() {
  // Product Config Form
  const productForm = document.getElementById('product-config-form');
  if (productForm) {
    productForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const feedback = document.getElementById('product-feedback');
      const payload = {
        title: document.getElementById('prod-title').value.trim(),
        subtitle: document.getElementById('prod-subtitle').value.trim(),
        regular_price: parseFloat(document.getElementById('prod-regular-price').value),
        reference_price: parseFloat(document.getElementById('prod-reference-price').value),
        stock_quantity: parseInt(document.getElementById('prod-stock').value),
        is_active: parseInt(document.getElementById('prod-is-active').value),
        description: document.getElementById('prod-description').value.trim(),
        led_note: document.getElementById('prod-led-note').value.trim(),
        package_contents: document.getElementById('prod-package-contents').value.trim(),
        care_instructions: document.getElementById('prod-care-instructions').value.trim()
      };

      try {
        const res = await fetch('/api/admin/product', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          feedback.textContent = 'Product settings and live pricing saved successfully!';
          feedback.className = 'p-3 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200';
          feedback.classList.remove('hidden');
          loadDashboardData();
        } else {
          feedback.textContent = 'Failed to save product settings.';
          feedback.className = 'p-3 rounded-lg text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200';
          feedback.classList.remove('hidden');
        }
      } catch (err) {
        console.error(err);
      }
    });
  }

  // Settings Form
  const settingsForm = document.getElementById('settings-form');
  if (settingsForm) {
    settingsForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const feedback = document.getElementById('settings-feedback');
      const updates = {
        announcement_bar: document.getElementById('setting-announcement').value.trim(),
        shipping_fee: document.getElementById('setting-shipping-fee').value.trim(),
        free_shipping_threshold: document.getElementById('setting-free-thresh').value.trim(),
        support_email: document.getElementById('setting-support-email').value.trim(),
        support_phone: document.getElementById('setting-support-phone').value.trim(),
        support_hours: document.getElementById('setting-support-hours').value.trim()
      };

      try {
        const res = await fetch('/api/admin/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates)
        });
        if (res.ok) {
          feedback.textContent = 'Store settings saved successfully!';
          feedback.className = 'p-3 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200';
          feedback.classList.remove('hidden');
        } else {
          feedback.textContent = 'Failed to save store settings.';
          feedback.className = 'p-3 rounded-lg text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200';
          feedback.classList.remove('hidden');
        }
      } catch (err) {
        console.error(err);
      }
    });
  }

  // Order Detail Update Form
  const orderUpdateForm = document.getElementById('order-update-form');
  if (orderUpdateForm) {
    orderUpdateForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!activeModalOrderId) return;

      const payload = {
        payment_status: document.getElementById('modal-payment-status').value,
        order_status: document.getElementById('modal-order-status').value,
        courier_name: document.getElementById('modal-courier-name').value.trim(),
        tracking_number: document.getElementById('modal-tracking-number').value.trim(),
        notes: document.getElementById('modal-notes').value.trim()
      };

      try {
        const res = await fetch(`/api/admin/orders/${activeModalOrderId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          alert('Order updated successfully!');
          closeOrderDetailModal();
          loadOrdersData(currentOrderPage);
          loadDashboardData();
        } else {
          alert('Failed to update order.');
        }
      } catch (err) {
        console.error(err);
      }
    });
  }

  // Order Filters & Search
  const searchInput = document.getElementById('order-search-input');
  if (searchInput) {
    let debounce = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        loadOrdersData(1);
      }, 400);
    });
  }

  const statusSelect = document.getElementById('order-status-filter');
  if (statusSelect) {
    statusSelect.addEventListener('change', () => {
      loadOrdersData(1);
    });
  }

  document.getElementById('btn-page-prev')?.addEventListener('click', () => {
    if (currentOrderPage > 1) loadOrdersData(currentOrderPage - 1);
  });
  document.getElementById('btn-page-next')?.addEventListener('click', () => {
    loadOrdersData(currentOrderPage + 1);
  });
}

async function handleLogout() {
  try {
    await fetch('/api/admin/logout', { method: 'POST' });
  } finally {
    window.location.href = '/admin/login';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
