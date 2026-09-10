/**
 * SAMADHAN SETU - National Societal Innovation Platform
 * Interactive Client-Side Logic & Utility Helpers
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Password Visibility Toggle
    const toggleBtns = document.querySelectorAll('.password-toggle-btn');
    toggleBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const targetId = btn.getAttribute('data-target') || 'password';
            const inputField = document.getElementById(targetId);
            const icon = btn.querySelector('i');
            if (inputField) {
                if (inputField.type === 'password') {
                    inputField.type = 'text';
                    if (icon) {
                        icon.classList.remove('fa-eye');
                        icon.classList.add('fa-eye-slash');
                    }
                } else {
                    inputField.type = 'password';
                    if (icon) {
                        icon.classList.remove('fa-eye-slash');
                        icon.classList.add('fa-eye');
                    }
                }
            }
        });
    });

    // 2. Auto-dismiss Flash Alerts after 5 seconds
    const flashAlerts = document.querySelectorAll('.alert-dismissible');
    flashAlerts.forEach(function (alert) {
        setTimeout(function () {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {
                alert.style.display = 'none';
            }
        }, 6000);
    });

    // 3. Share URL Clipboard Copy
    const shareBtns = document.querySelectorAll('.btn-copy-share');
    shareBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const url = window.location.href;
            navigator.clipboard.writeText(url).then(function () {
                const origText = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check me-1"></i> Copied!';
                btn.classList.add('btn-success');
                setTimeout(function () {
                    btn.innerHTML = origText;
                    btn.classList.remove('btn-success');
                }, 2500);
            }).catch(function () {
                alert('URL copied to clipboard: ' + url);
            });
        });
    });

    // 4. Client-side Realtime Filter for Challenges Marketplace (instant quick search)
    const clientSearchInput = document.getElementById('clientFilterInput');
    if (clientSearchInput) {
        clientSearchInput.addEventListener('input', function (e) {
            const term = e.target.value.toLowerCase().trim();
            const cards = document.querySelectorAll('.challenge-item-card');
            cards.forEach(function (card) {
                const text = card.textContent.toLowerCase();
                if (text.includes(term)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // 5. Sidebar Toggle on Small Screens
    const sidebarToggle = document.getElementById('sidebarToggleBtn');
    const sidebar = document.querySelector('.app-sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('d-none');
        });
    }
});

