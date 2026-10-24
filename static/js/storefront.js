/**
 * GlowMint Accessories — Storefront & Checkout Client Script
 * Handles gallery interaction, coupon live verification, drawer checkout,
 * and Razorpay payment flow.
 */

// Global State
const state = {
  quantity: 1,
  unitPrice: 600.0,
  referencePrice: 600.0,
  couponCode: '',
  appliedCoupon: null,
  discountAmount: 0.0,
  shippingFee: 0.0,
  totalAmount: 600.0,
  customerName: '',
  customerPhone: '',
  customerEmail: '',
  addressLine: '',
  landmark: '',
  city: '',
  state: '',
  pincode: '',
  paymentMethod: 'razorpay',
  isCalculating: false,
  isSubmitting: false,
  activeGalleryIndex: 0,
  galleryImages: [
    { src: '/static/images/hero.jpg', title: 'Luxury Plum Presentation', desc: 'Handcrafted antique gold filigree with illuminated warm LED core' },
    { src: '/static/images/detail.jpg', title: 'Macro Filigree Detail', desc: 'Precision dome lattice cutouts, micro-pearl fringe, and ruby accents' },
    { src: '/static/images/packaging.jpg', title: 'Royal Plum Velvet Box', desc: 'Includes velvet gift box, gold travel pouch & spare coin cells' },
    { src: '/static/images/model.jpg', title: 'Festive Wear Silhouette', desc: 'Graceful drape, lightweight 28g balance & gentle ambient glow' }
  ]
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {
  initGallery();
  initFaqAccordions();
  initCheckoutEvents();
  initIlluminationToggle();
  initStickyMobileBar();
  initLightbox();
  fetchInitialPricing();
});

// -----------------------------------------------------------------------------
// Interactive Evening Illumination Toggle
// -----------------------------------------------------------------------------
function initIlluminationToggle() {
  const toggleBtn = document.getElementById('btn-toggle-glow');
  const heroImg = document.getElementById('hero-product-image');
  const glowStatus = document.getElementById('glow-status-text');
  const heroCard = document.getElementById('hero-media-card');
  const heroSection = document.getElementById('hero');

  if (!toggleBtn || !heroImg) return;

  let isGlowOn = true; // Default warm ambient glow

  toggleBtn.addEventListener('click', () => {
    isGlowOn = !isGlowOn;
    if (isGlowOn) {
      heroImg.classList.add('led-illumination-glow');
      if (heroCard) heroCard.classList.add('lantern-glow-card');
      if (heroSection) heroSection.classList.add('night-glow-mode');
      toggleBtn.classList.add('bg-gold-500', 'text-plum-950');
      toggleBtn.classList.remove('bg-black/60', 'text-gold-200');
      if (glowStatus) glowStatus.textContent = '🌙 Festival Glow: ON';
      if (window.showToast) window.showToast('✨ Warm candlelight lantern aura active!');
    } else {
      heroImg.classList.remove('led-illumination-glow');
      if (heroCard) heroCard.classList.remove('lantern-glow-card');
      if (heroSection) heroSection.classList.remove('night-glow-mode');
      toggleBtn.classList.remove('bg-gold-500', 'text-plum-950');
      toggleBtn.classList.add('bg-black/60', 'text-gold-200');
      if (glowStatus) glowStatus.textContent = '☀️ Daylight: OFF';
    }
  });
}

// -----------------------------------------------------------------------------
// Sticky Mobile Action Bar
// -----------------------------------------------------------------------------
function initStickyMobileBar() {
  const stickyBar = document.getElementById('mobile-sticky-bar');
  if (!stickyBar) return;

  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY || window.pageYOffset;
    const heroEl = document.getElementById('hero');
    const heroHeight = heroEl ? heroEl.offsetHeight : 400;

    const drawer = document.getElementById('checkout-drawer');
    const isDrawerOpen = drawer && !drawer.classList.contains('hidden');

    if (scrollY > heroHeight && !isDrawerOpen) {
      stickyBar.classList.add('visible');
    } else {
      stickyBar.classList.remove('visible');
    }
  }, { passive: true });
}

// -----------------------------------------------------------------------------
// Image Lightbox Viewer
// -----------------------------------------------------------------------------
function initLightbox() {
  window.openImageLightbox = function(src, title) {
    const modal = document.getElementById('image-lightbox-modal');
    const img = document.getElementById('lightbox-image');
    const titleEl = document.getElementById('lightbox-title');
    if (!modal || !img) return;

    img.src = src;
    if (titleEl) titleEl.textContent = title || 'GlowMint LED Lantern Jhumka';
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.style.overflow = 'hidden';
  };

  window.closeImageLightbox = function() {
    const modal = document.getElementById('image-lightbox-modal');
    if (modal) {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
      document.body.style.overflow = '';
    }
  };
}

// -----------------------------------------------------------------------------
// Gallery Interaction
// -----------------------------------------------------------------------------
function initGallery() {
  const mainImage = document.getElementById('gallery-main-image');
  const captionTitle = document.getElementById('gallery-caption-title');
  const captionDesc = document.getElementById('gallery-caption-desc');
  const thumbnails = document.querySelectorAll('.gallery-thumb');

  window.selectGalleryImage = function(index) {
    if (index < 0 || index >= state.galleryImages.length) return;
    state.activeGalleryIndex = index;
    const item = state.galleryImages[index];

    if (mainImage) {
      mainImage.style.opacity = '0';
      setTimeout(() => {
        mainImage.src = item.src;
        mainImage.style.opacity = '1';
      }, 150);
    }
    if (captionTitle) captionTitle.textContent = item.title;
    if (captionDesc) captionDesc.textContent = item.desc;

    thumbnails.forEach((t, i) => {
      if (i === index) {
        t.classList.add('ring-2', 'ring-[#D4AF37]', 'scale-105');
      } else {
        t.classList.remove('ring-2', 'ring-[#D4AF37]', 'scale-105');
      }
    });
  };

  // Video Demo Modal / Drawer toggle
  const videoBtn = document.getElementById('btn-play-video-demo');
  if (videoBtn) {
    videoBtn.addEventListener('click', () => {
      openVideoModal();
    });
  }
}

function openVideoModal() {
  const modal = document.getElementById('video-demo-modal');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }
}

function closeVideoModal() {
  const modal = document.getElementById('video-demo-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}

// -----------------------------------------------------------------------------
// FAQ Accordion
// -----------------------------------------------------------------------------
function initFaqAccordions() {
  const triggers = document.querySelectorAll('.faq-trigger');
  triggers.forEach(btn => {
    btn.addEventListener('click', () => {
      const content = btn.nextElementSibling;
      const icon = btn.querySelector('.faq-icon');
      const isExpanded = btn.getAttribute('aria-expanded') === 'true';

      // Toggle state
      btn.setAttribute('aria-expanded', !isExpanded);
      if (!isExpanded) {
        content.classList.remove('hidden');
        if (icon) icon.style.transform = 'rotate(180deg)';
      } else {
        content.classList.add('hidden');
        if (icon) icon.style.transform = 'rotate(0deg)';
      }
    });
  });
}

// -----------------------------------------------------------------------------
// Checkout Drawer / Modal
// -----------------------------------------------------------------------------
function openCheckoutDrawer(prefillCoupon = '') {
  const drawer = document.getElementById('checkout-drawer');
  if (!drawer) return;

  if (prefillCoupon) {
    const input = document.getElementById('checkout-coupon-input');
    if (input) input.value = prefillCoupon;
    state.couponCode = prefillCoupon;
  }

  drawer.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  recalculatePrice();
}

function closeCheckoutDrawer() {
  const drawer = document.getElementById('checkout-drawer');
  if (!drawer) return;
  drawer.classList.add('hidden');
  document.body.style.overflow = '';
}

function initCheckoutEvents() {
  // Quantity Controls
  const qtyMinus = document.getElementById('checkout-qty-minus');
  const qtyPlus = document.getElementById('checkout-qty-plus');
  const qtyDisplay = document.getElementById('checkout-qty-display');

  if (qtyMinus && qtyPlus && qtyDisplay) {
    qtyMinus.addEventListener('click', () => {
      if (state.quantity > 1) {
        state.quantity--;
        qtyDisplay.textContent = state.quantity;
        recalculatePrice();
      }
    });
    qtyPlus.addEventListener('click', () => {
      if (state.quantity < 5) {
        state.quantity++;
        qtyDisplay.textContent = state.quantity;
        recalculatePrice();
      }
    });
  }

  // Coupon Apply Button & Enter Key
  const btnApplyCoupon = document.getElementById('btn-apply-coupon');
  const couponInput = document.getElementById('checkout-coupon-input');
  if (btnApplyCoupon && couponInput) {
    btnApplyCoupon.addEventListener('click', () => {
      state.couponCode = couponInput.value.trim().toUpperCase();
      recalculatePrice(true);
    });
    couponInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        state.couponCode = couponInput.value.trim().toUpperCase();
        recalculatePrice(true);
      }
    });
  }

  // Customer Contact Fields for dynamic coupon check
  const phoneInput = document.getElementById('customer-phone');
  const emailInput = document.getElementById('customer-email');

  let debounceTimer = null;
  const triggerDebouncedRecalc = () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (state.couponCode) {
        recalculatePrice(false);
      }
    }, 600);
  };

  if (phoneInput) phoneInput.addEventListener('input', triggerDebouncedRecalc);
  if (emailInput) emailInput.addEventListener('input', triggerDebouncedRecalc);

  // Form Submission
  const checkoutForm = document.getElementById('checkout-form');
  if (checkoutForm) {
    checkoutForm.addEventListener('submit', handleCheckoutSubmit);
  }
}

// -----------------------------------------------------------------------------
// Price & Coupon Server-Side Calculation
// -----------------------------------------------------------------------------
async function fetchInitialPricing() {
  try {
    const res = await fetch('/api/calculate-price', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity: 1 })
    });
    if (res.ok) {
      const data = await res.json();
      state.unitPrice = data.unit_price;
      state.referencePrice = data.reference_price;
      updatePricingUI(data);
    }
  } catch (err) {
    console.error('Failed to load initial pricing:', err);
  }
}

async function recalculatePrice(isUserAction = false) {
  const phone = document.getElementById('customer-phone')?.value.trim() || '';
  const email = document.getElementById('customer-email')?.value.trim() || '';
  const feedbackEl = document.getElementById('checkout-coupon-feedback');

  if (isUserAction && feedbackEl) {
    feedbackEl.innerHTML = '<span class="text-xs text-amber-700 animate-pulse font-medium">Validating offer with server...</span>';
  }

  try {
    const res = await fetch('/api/calculate-price', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        quantity: state.quantity,
        coupon_code: state.couponCode || undefined,
        customer_phone: phone || undefined,
        customer_email: email || undefined
      })
    });

    const data = await res.json();

    if (!res.ok) {
      if (feedbackEl) {
        feedbackEl.innerHTML = `<span class="text-xs text-red-600 font-medium">${data.detail || 'Error calculating price'}</span>`;
      }
      return;
    }

    state.unitPrice = data.unit_price;
    state.subtotal = data.subtotal;
    state.discountAmount = data.discount_amount;
    state.shippingFee = data.shipping_fee;
    state.totalAmount = data.total_amount;
    state.appliedCoupon = data.coupon_code;

    updatePricingUI(data);

    if (feedbackEl) {
      if (data.coupon_valid) {
        feedbackEl.innerHTML = `
          <div class="flex items-center justify-between text-xs text-emerald-700 font-semibold bg-emerald-50 p-2 rounded border border-emerald-200">
            <span>✓ ${data.coupon_message}</span>
            <button type="button" onclick="removeCoupon()" class="text-red-600 underline text-[11px] ml-2">Remove</button>
          </div>`;
      } else if (data.coupon_message) {
        feedbackEl.innerHTML = `<span class="text-xs text-rose-700 font-medium bg-rose-50 p-2 rounded block border border-rose-200">${data.coupon_message}</span>`;
      } else {
        feedbackEl.innerHTML = '';
      }
    }
  } catch (err) {
    console.error('Recalculate error:', err);
    if (feedbackEl) {
      feedbackEl.innerHTML = '<span class="text-xs text-red-600 font-medium">Network error checking pricing.</span>';
    }
  }
}

window.applyCouponFromCard = function(code) {
  openCheckoutDrawer(code);
};

window.removeCoupon = function() {
  state.couponCode = '';
  state.appliedCoupon = null;
  const input = document.getElementById('checkout-coupon-input');
  if (input) input.value = '';
  const feedbackEl = document.getElementById('checkout-coupon-feedback');
  if (feedbackEl) feedbackEl.innerHTML = '';
  recalculatePrice();
};

function updatePricingUI(pricing) {
  // Update Checkout Drawer breakdown
  const subtotalEl = document.getElementById('checkout-subtotal-val');
  const discountRow = document.getElementById('checkout-discount-row');
  const discountValEl = document.getElementById('checkout-discount-val');
  const shippingValEl = document.getElementById('checkout-shipping-val');
  const totalValEl = document.getElementById('checkout-total-val');
  const payBtnAmountEl = document.getElementById('pay-button-amount');

  if (subtotalEl) subtotalEl.textContent = `₹${pricing.subtotal.toFixed(2)}`;

  if (discountRow && discountValEl) {
    if (pricing.discount_amount > 0) {
      discountRow.classList.remove('hidden');
      discountValEl.textContent = `-₹${pricing.discount_amount.toFixed(2)}`;
    } else {
      discountRow.classList.add('hidden');
    }
  }

  if (shippingValEl) {
    if (pricing.shipping_fee === 0) {
      shippingValEl.innerHTML = '<span class="text-emerald-700 font-semibold">FREE (Launch Offer)</span>';
    } else {
      shippingValEl.textContent = `₹${pricing.shipping_fee.toFixed(2)}`;
    }
  }

  if (totalValEl) totalValEl.textContent = `₹${pricing.total_amount.toFixed(2)}`;
  if (payBtnAmountEl) payBtnAmountEl.textContent = `₹${pricing.total_amount.toFixed(2)}`;
}

// -----------------------------------------------------------------------------
// Checkout Submission & Razorpay Integration
// -----------------------------------------------------------------------------
async function handleCheckoutSubmit(e) {
  e.preventDefault();
  if (state.isSubmitting) return;

  const form = e.target;
  const name = form.customer_name.value.trim();
  const phone = form.customer_phone.value.trim();
  const email = form.customer_email.value.trim();
  const address = form.address_line.value.trim();
  const landmark = form.landmark?.value.trim() || '';
  const city = form.city.value.trim();
  const stateVal = form.state.value.trim();
  const pincode = form.pincode.value.trim();

  // Basic client validation
  if (!name || name.length < 2) {
    alert('Please enter your full name.');
    return;
  }
  if (!phone || phone.replace(/\D/g, '').length < 10) {
    alert('Please enter a valid 10-digit mobile number.');
    return;
  }
  if (!email || !email.includes('@')) {
    alert('Please enter a valid email address.');
    return;
  }
  if (!address || address.length < 5) {
    alert('Please enter your complete delivery street / flat address.');
    return;
  }
  if (!city || !stateVal) {
    alert('Please provide your city and state.');
    return;
  }
  if (!pincode || pincode.replace(/\D/g, '').length !== 6) {
    alert('Please enter a valid 6-digit PIN code.');
    return;
  }

  const submitBtn = document.getElementById('btn-submit-order');
  const originalBtnText = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="inline-flex items-center gap-2">Processing Secure Checkout...</span>';
  state.isSubmitting = true;

  try {
    // 1. Create order on backend
    const payload = {
      customer_name: name,
      customer_phone: phone,
      customer_email: email,
      address_line: address,
      landmark: landmark,
      city: city,
      state: stateVal,
      pincode: pincode,
      quantity: state.quantity,
      coupon_code: state.couponCode || null,
      payment_method: 'razorpay',
      idempotency_key: `idemp_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
    };

    const res = await fetch('/api/create-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const orderData = await res.json();
    if (!res.ok) {
      alert(orderData.detail || 'Unable to create order. Please check details.');
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnText;
      state.isSubmitting = false;
      return;
    }

    // 2. Launch Razorpay Gateway or Simulation Handler
    if (orderData.mode === 'live' && typeof Razorpay !== 'undefined') {
      const options = {
        key: orderData.key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        name: 'GlowMint Accessories',
        description: `LED Lantern Jhumka Earrings (Qty: ${state.quantity})`,
        image: window.location.origin + '/static/images/hero.jpg',
        order_id: orderData.razorpay_order_id,
        prefill: {
          name: name,
          email: email,
          contact: phone
        },
        theme: {
          color: '#3E0F20'
        },
        handler: async function (response) {
          await verifyAndFinalizePayment({
            order_id: orderData.order_id,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature
          });
        },
        modal: {
          ondismiss: function () {
            fetch('/api/record-payment-failure', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ order_id: orderData.order_id, reason: 'Customer closed payment window' })
            }).catch(() => {});
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
            state.isSubmitting = false;
          }
        }
      };

      const rzp = new Razorpay(options);
      rzp.on('payment.failed', function (response) {
        fetch('/api/record-payment-failure', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            order_id: orderData.order_id,
            reason: response.error?.description || 'Payment gateway failed'
          })
        }).catch(() => {});
        alert('Payment could not be completed: ' + (response.error?.description || 'Unknown reason'));
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
        state.isSubmitting = false;
      });
      rzp.open();
    } else {
      // Integration-ready simulation mode (when test keys or sandbox environment)
      showSimulationModal(orderData, name, phone, email);
    }
  } catch (err) {
    console.error('Order creation error:', err);
    alert('An unexpected error occurred. Please try again.');
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnText;
    state.isSubmitting = false;
  }
}

// -----------------------------------------------------------------------------
// Simulation Modal (For Testing / QA / Integration-ready mode)
// -----------------------------------------------------------------------------
function showSimulationModal(orderData, name, phone, email) {
  const modal = document.getElementById('payment-simulation-modal');
  if (!modal) {
    alert('Order created: ' + orderData.order_id);
    return;
  }

  document.getElementById('sim-order-id').textContent = orderData.order_id;
  document.getElementById('sim-amount').textContent = `₹${(orderData.amount / 100).toFixed(2)}`;
  document.getElementById('sim-customer-name').textContent = name;

  modal.classList.remove('hidden');
  modal.classList.add('flex');

  // Success button
  const btnSimSuccess = document.getElementById('btn-sim-pay-success');
  btnSimSuccess.onclick = async () => {
    btnSimSuccess.disabled = true;
    btnSimSuccess.textContent = 'Verifying HMAC Signature...';

    const simPaymentId = `pay_sim_${Date.now()}`;
    const simSignature = `sim_sig_${Date.now()}`;

    await verifyAndFinalizePayment({
      order_id: orderData.order_id,
      razorpay_order_id: orderData.razorpay_order_id,
      razorpay_payment_id: simPaymentId,
      razorpay_signature: simSignature
    });
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  };

  // Cancel button
  const btnSimCancel = document.getElementById('btn-sim-pay-cancel');
  btnSimCancel.onclick = () => {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    const submitBtn = document.getElementById('btn-submit-order');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span class="font-serif">PROCEED TO SECURE PAYMENT</span>';
    }
    state.isSubmitting = false;
  };
}

async function verifyAndFinalizePayment(verifyPayload) {
  try {
    const res = await fetch('/api/verify-payment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(verifyPayload)
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showOrderConfirmation(data.order_id);
    } else {
      alert(data.detail || 'Payment verification failed on the server.');
      resetSubmitButton();
    }
  } catch (err) {
    console.error('Payment verification error:', err);
    alert('Error communicating with verification server.');
    resetSubmitButton();
  }
}

function showOrderConfirmation(orderId) {
  closeCheckoutDrawer();
  const confirmationModal = document.getElementById('order-confirmation-modal');
  if (confirmationModal) {
    document.getElementById('confirmed-order-id').textContent = orderId;
    confirmationModal.classList.remove('hidden');
    confirmationModal.classList.add('flex');
    document.body.style.overflow = 'hidden';
  }
}

function resetSubmitButton() {
  const submitBtn = document.getElementById('btn-submit-order');
  if (submitBtn) {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<span class="font-serif">PROCEED TO SECURE PAYMENT</span>';
  }
  state.isSubmitting = false;
}

// -----------------------------------------------------------------------------
// Policy Modals
// -----------------------------------------------------------------------------
window.openPolicyModal = function(policyKey) {
  const modal = document.getElementById('policy-modal');
  const titleEl = document.getElementById('policy-modal-title');
  const bodyEl = document.getElementById('policy-modal-body');
  if (!modal || !titleEl || !bodyEl) return;

  const policies = {
    privacy: {
      title: 'Privacy Policy',
      content: `
        <h4 class="font-semibold text-base mb-2">1. Information Collection</h4>
        <p class="mb-3 text-sm">GlowMint Accessories collects personal information such as your name, delivery address, phone number, and email address solely for processing and fulfilling your orders, sending shipment tracking notifications, and providing dedicated customer care.</p>
        <h4 class="font-semibold text-base mb-2">2. Payment Security</h4>
        <p class="mb-3 text-sm">We do not store your credit/debit card details, UPI PINs, or net banking credentials on our servers. All financial transactions are securely handled through Razorpay, a PCI-DSS certified payment gateway utilizing 256-bit SSL encryption.</p>
        <h4 class="font-semibold text-base mb-2">3. Data Sharing</h4>
        <p class="mb-3 text-sm">We never sell, trade, or rent your personal data to third parties. Customer details are only shared with our verified logistics partners (such as Delhivery, Blue Dart, or India Post) strictly for the purpose of doorstep delivery.</p>
      `
    },
    terms: {
      title: 'Terms & Conditions',
      content: `
        <h4 class="font-semibold text-base mb-2">1. Acceptance of Terms</h4>
        <p class="mb-3 text-sm">By placing an order on GlowMint Accessories, you agree to be bound by these Terms and Conditions in accordance with Indian commercial regulations.</p>
        <h4 class="font-semibold text-base mb-2">2. Pricing & Launch Offers</h4>
        <p class="mb-3 text-sm">All prices listed on the website are in Indian Rupees (INR) and are inclusive of applicable goods and services taxes. Promotional coupon codes (FIRST50, SECOND20, THIRD10) are subject to verified order history validation and specified discount caps.</p>
        <h4 class="font-semibold text-base mb-2">3. Order Fulfillment</h4>
        <p class="mb-3 text-sm">Orders are subject to stock availability and prepaid payment confirmation. While we strive for dispatch within 24-48 business hours, unexpected courier transit delays due to regional logistics or natural events are beyond our direct control.</p>
      `
    },
    shipping: {
      title: 'Shipping & Delivery Policy',
      content: `
        <h4 class="font-semibold text-base mb-2">1. Dispatch Timeline</h4>
        <p class="mb-3 text-sm">Each pair of GlowMint LED Lantern Jhumka Earrings is carefully quality-inspected and dispatched within 24 to 48 business hours from our central fulfillment center.</p>
        <h4 class="font-semibold text-base mb-2">2. Delivery Timeframes</h4>
        <p class="mb-3 text-sm">• Metro Cities (Mumbai, Delhi, Bengaluru, Chennai, Kolkata, Hyderabad): 2 to 4 business days.<br>• Tier 2 & Tier 3 Cities / Rest of India: 4 to 6 business days.</p>
        <h4 class="font-semibold text-base mb-2">3. Shipping Fees & Tracking</h4>
        <p class="mb-3 text-sm">Standard delivery is currently FREE for all prepaid orders across India as part of our festive launch celebration. Once dispatched, a live tracking link is transmitted via SMS/WhatsApp.</p>
      `
    },
    refund: {
      title: 'Return & Refund Policy',
      content: `
        <h4 class="font-semibold text-base mb-2">1. 7-Day Replacement Guarantee</h4>
        <p class="mb-3 text-sm">Because our jewelry items are intimate personal adornments, we offer a hassle-free 7-day replacement for any item that arrives damaged in transit, defective, or with malfunctioning LED circuitry.</p>
        <h4 class="font-semibold text-base mb-2">2. Claim Procedure</h4>
        <p class="mb-3 text-sm">To initiate a replacement or refund claim, please notify our support team within 7 days of package delivery at support@glowmint.in or via WhatsApp (+91 98765 43210) along with a brief unboxing video or clear photographs of the defect.</p>
        <h4 class="font-semibold text-base mb-2">3. Refund Processing</h4>
        <p class="mb-3 text-sm">Approved refunds will be processed directly to your original payment method (bank account, UPI, or card) within 5-7 business days via our Razorpay settlement gateway.</p>
      `
    }
  };

  const selected = policies[policyKey] || { title: 'Store Policy', content: '<p>Please contact support for more details.</p>' };
  titleEl.textContent = selected.title;
  bodyEl.innerHTML = selected.content;

  modal.classList.remove('hidden');
  modal.classList.add('flex');
};

window.closePolicyModal = function() {
  const modal = document.getElementById('policy-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
};

// -----------------------------------------------------------------------------
// Interactive UI Helpers: Pincode, Copy Code, Toast, Gallery Navigation
// -----------------------------------------------------------------------------
window.showToast = function(message) {
  const toast = document.getElementById('toast-notification');
  const msgEl = document.getElementById('toast-message');
  if (!toast || !msgEl) return;
  msgEl.textContent = message;
  toast.classList.add('show');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => {
    toast.classList.remove('show');
  }, 3500);
};

window.copyCouponCode = function(code) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(code).then(() => {
      showToast(`✨ Coupon ${code} copied! Applying to cart...`);
      setTimeout(() => {
        openCheckoutDrawer(code);
      }, 300);
    }).catch(() => {
      openCheckoutDrawer(code);
    });
  } else {
    openCheckoutDrawer(code);
  }
};

window.navigateGallery = function(direction) {
  let newIndex = state.activeGalleryIndex + direction;
  if (newIndex < 0) newIndex = state.galleryImages.length - 1;
  if (newIndex >= state.galleryImages.length) newIndex = 0;
  if (window.selectGalleryImage) {
    window.selectGalleryImage(newIndex);
  }
};

window.checkPincodeDelivery = function() {
  const input = document.getElementById('pincode-input');
  const resultEl = document.getElementById('pincode-result');
  if (!input || !resultEl) return;

  const pin = input.value.trim().replace(/\D/g, '');
  if (pin.length !== 6) {
    resultEl.className = 'text-[11px] font-semibold text-rose-600 mt-2 block px-1';
    resultEl.textContent = 'Please enter a valid 6-digit Indian PIN code.';
    resultEl.classList.remove('hidden');
    return;
  }

  let zoneText = 'All-India Insured Dispatch';
  let days = '3–5 business days';
  const prefix = pin.substring(0, 2);

  if (['11', '12', '20'].includes(prefix)) {
    zoneText = 'Delhi NCR Express';
    days = 'Tomorrow (Guaranteed Priority Dispatch)';
  } else if (['40', '41'].includes(prefix)) {
    zoneText = 'Mumbai / Pune Region';
    days = '2 business days';
  } else if (['56', '57'].includes(prefix)) {
    zoneText = 'Bengaluru Hub';
    days = '2 business days';
  } else if (['50'].includes(prefix)) {
    zoneText = 'Hyderabad Hub';
    days = '2-3 business days';
  } else if (['60'].includes(prefix)) {
    zoneText = 'Chennai Hub';
    days = '3 business days';
  } else if (['70'].includes(prefix)) {
    zoneText = 'Kolkata Hub';
    days = '3 business days';
  }

  resultEl.className = 'text-[11px] font-semibold text-emerald-800 mt-2 block px-2.5 py-2 bg-emerald-50 rounded-xl border border-emerald-200 shadow-sm';
  resultEl.innerHTML = `✓ <strong>PIN ${pin} (${zoneText}):</strong> Free Insured Delivery by <strong>${days}</strong>. Covered by 7-Day transit guarantee.`;
  resultEl.classList.remove('hidden');
};

