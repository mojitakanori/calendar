// フラッシュメッセージを3秒後にフェードアウトさせる
setTimeout(function() {
    const flashMessages = document.querySelector('.flash-messages');
    if (flashMessages) {
        flashMessages.style.transition = 'opacity 0.5s ease';
        flashMessages.style.opacity = '0';
        setTimeout(() => flashMessages.remove(), 500);
    }
}, 3000);

// ハンバーガーメニューのトグル機能
function toggleMenu() {
    const navMenu = document.getElementById('nav-menu');
    navMenu.classList.toggle('open');
}
