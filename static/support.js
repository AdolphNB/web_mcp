"use strict";
(() => {
    const form = document.getElementById("support-form");
    if (!form) return;
    const input = document.getElementById("support-question");
    const send = document.getElementById("support-send");
    const clear = document.getElementById("support-clear");
    const status = document.getElementById("support-status");
    const log = document.getElementById("support-messages");
    const feedback = document.getElementById("support-feedback");
    const suggestions = [...document.querySelectorAll("[data-support-question]")];
    const session = [...crypto.getRandomValues(new Uint8Array(32))].map(n => n.toString(16).padStart(2, "0")).join("");
    let history = [], busy = false, online = false;
    const fallback = "客服暂时未能回复，请稍后重试或邮件联系 304633698@qq.com。";
    const controls = () => {
        input.disabled = busy || !online;
        send.disabled = busy || !online;
        clear.disabled = busy;
        suggestions.forEach(button => button.disabled = busy || !online);
        send.textContent = busy ? "正在回复…" : "发送消息";
    };
    async function fetchJSON(url, options = {}) {
        const response = await fetch(url, {...options, signal: AbortSignal.timeout(12000), headers: {
            "Content-Type": "application/json", "X-Support-Session": session, ...(options.headers || {})
        }});
        const data = await response.json();
        if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "请求未成功，请稍后重试。");
        return data;
    }
    async function checkStatus() {
        if (busy) return;
        try { online = (await fetchJSON("/api/support/status")).online; }
        catch { online = false; }
        status.textContent = online ? "在线 · 可以咨询" : "暂时离线 · 可邮件联系";
        status.classList.toggle("is-online", online);
        controls();
    }
    function bubble(role, text) {
        const item = document.createElement("div");
        item.className = `support-message ${role}`;
        const label = document.createElement("span");
        label.textContent = role === "user" ? "您" : "奇点小助手";
        const paragraph = document.createElement("p");
        paragraph.textContent = text;
        item.append(label, paragraph);
        log.append(item);
        log.scrollTop = log.scrollHeight;
        return item;
    }
    form.addEventListener("submit", async event => {
        event.preventDefault();
        const message = input.value.trim();
        if (!message || busy || !online) return;
        busy = true;
        controls();
        feedback.textContent = "正在联系 Hermes，通常需要十几秒，请稍候…";
        bubble("user", message);
        const requestId = crypto.randomUUID();
        let submitted = false;
        try {
            // Retry uncertain delivery with the SAME id: the server deduplicates it.
            let job;
            for (let attempt = 0; attempt < 2; attempt++) {
                try {
                    job = await fetchJSON("/api/support/chat", {method: "POST", body: JSON.stringify({request_id: requestId, message, history: history.slice(-8)})});
                    break;
                } catch (error) {
                    if (attempt || !["TimeoutError", "TypeError"].includes(error.name)) throw error;
                }
            }
            submitted = true;
            const deadline = Date.now() + 155000;
            while (Date.now() < deadline) {
                await new Promise(resolve => setTimeout(resolve, 2000));
                const result = await fetchJSON(`/api/support/chat/${job.id}`);
                if (["done", "failed"].includes(result.status)) {
                    if (result.status === "failed") throw new Error(result.answer || fallback);
                    bubble("assistant", result.answer);
                    history.push({role: "user", content: message}, {role: "assistant", content: result.answer.slice(0, 3000)});
                    history = history.slice(-8);
                    input.value = "";
                    feedback.textContent = "已回复。您可以继续提问。";
                    return;
                }
            }
            throw new Error(fallback);
        } catch (error) {
            feedback.textContent = (error.message && !["TypeError", "TimeoutError"].includes(error.name)) ? error.message : fallback;
            if (submitted) feedback.textContent += " 您的问题已保留在输入框中。";
        } finally {
            busy = false;
            await checkStatus();
            if (!input.disabled) input.focus();
        }
    });
    suggestions.forEach(button => button.addEventListener("click", () => {
        input.value = button.dataset.supportQuestion;
        input.focus();
    }));
    clear.addEventListener("click", () => {
        history = [];
        while (log.children.length > 1) log.lastElementChild.remove();
        input.value = "";
        feedback.textContent = "已清空本页对话。服务器上的记录按保留期限清理。";
        if (!input.disabled) input.focus();
    });
    controls();
    checkStatus();
    const timer = setInterval(checkStatus, 15000);
    window.addEventListener("pagehide", () => clearInterval(timer), {once:true});
})();
