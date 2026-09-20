"use strict";

const menu = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#primary-navigation");
if (menu && navigation) {
    menu.hidden = false;
    const setMenu = (open) => {
        menu.setAttribute("aria-expanded", String(open));
        menu.textContent = open ? "收起菜单" : "菜单";
        navigation.classList.toggle("is-collapsed", !open);
    };
    setMenu(false);
    menu.addEventListener("click", () => setMenu(menu.getAttribute("aria-expanded") !== "true"));
    navigation.addEventListener("click", (event) => {
        if (event.target.closest("a")) setMenu(false);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && menu.getAttribute("aria-expanded") === "true") {
            setMenu(false);
            menu.focus();
        }
    });
}

document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.hidden = false;
    button.addEventListener("click", async () => {
        const endpoint = document.getElementById(button.dataset.copyTarget);
        const status = button.nextElementSibling;
        try {
            await navigator.clipboard.writeText(endpoint.textContent.trim());
            status.textContent = "地址已复制";
        } catch {
            const range = document.createRange();
            range.selectNodeContents(endpoint);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            endpoint.focus();
            status.textContent = "自动复制不可用，请长按选中地址或按 Ctrl+C / ⌘C 复制。";
        }
    });
});
