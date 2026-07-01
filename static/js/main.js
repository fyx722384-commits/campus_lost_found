(function () {
    var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function setStagger(selector, step, limit) {
        if (reducedMotion) return;
        document.querySelectorAll(selector).forEach(function (node, index) {
            var capped = typeof limit === "number" ? Math.min(index, limit) : index;
            node.style.animationDelay = (capped * step) + "ms";
        });
    }

    function showToast(message, category) {
        var root = document.getElementById("toast-root");
        if (!root) return;
        var toast = document.createElement("div");
        toast.className = "toast " + (category || "success");
        toast.textContent = message;
        root.appendChild(toast);
        setTimeout(function () {
            toast.classList.add("is-leaving");
            setTimeout(function () { toast.remove(); }, 220);
        }, 2800);
    }

    document.querySelectorAll(".flash-message").forEach(function (node) {
        showToast(node.textContent, node.dataset.category);
    });

    document.querySelectorAll("[data-filter-form]").forEach(function (form) {
        var keyword = form.querySelector('input[name="keyword"]');
        var cards = document.querySelectorAll("[data-search]");
        var resultList = document.querySelector("[data-results-list]");
        var dateMode = form.querySelector("[data-date-mode-field]");
        form.querySelectorAll("[data-date-input]").forEach(function (input) {
            input.addEventListener("change", function () {
                if (dateMode && input.value) {
                    dateMode.remove();
                    dateMode = null;
                }
            });
        });
        if (!keyword || !cards.length) return;
        keyword.addEventListener("input", function () {
            var value = keyword.value.trim().toLowerCase();
            cards.forEach(function (card) {
                var text = (card.dataset.search || "").toLowerCase();
                var visible = !value || text.indexOf(value) !== -1;
                card.style.display = visible ? "" : "none";
                if (visible) {
                    card.classList.remove("fade-list");
                    void card.offsetWidth;
                    card.classList.add("fade-list");
                }
            });
            if (resultList) {
                resultList.classList.remove("fade-list");
                void resultList.offsetWidth;
                resultList.classList.add("fade-list");
            }
        });
    });

    document.body.classList.add("page-ready");

    setStagger(".stat-card", 50, 8);
    setStagger(".admin-reminder-card", 60, 5);
    setStagger(".notice-card", 80, 4);
    setStagger(".item-grid .item-card", 55, 12);
    setStagger(".match-card", 70, 10);
    setStagger(".notification-card", 55, 10);

    document.querySelectorAll(".btn").forEach(function (button) {
        button.addEventListener("click", function () {
            if (button.disabled || reducedMotion) return;
            button.classList.remove("is-pressed");
            void button.offsetWidth;
            button.classList.add("is-pressed");
            setTimeout(function () {
                button.classList.remove("is-pressed");
            }, 220);
        });
    });

    document.querySelectorAll(".progress span").forEach(function (bar) {
        var target = bar.style.getPropertyValue("--target");
        bar.style.setProperty("--target", target || "0%");
        bar.style.animation = "none";
        void bar.offsetWidth;
        bar.style.animation = "";
    });

    document.querySelectorAll("[data-priority-level]").forEach(function (select) {
        var tip = document.querySelector("[data-priority-tip]");
        var copy = {
            "普通加急": "普通加急：模拟费用 3 元，置顶 24 小时",
            "重点加急": "重点加急：模拟费用 6 元，置顶 72 小时",
            "公益加急": "公益加急：0 元，仅限校园卡、证件、钥匙等重要物品，需管理员审核"
        };
        function updateTip() {
            if (tip) tip.textContent = copy[select.value] || "";
        }
        select.addEventListener("change", updateTip);
        updateTip();
    });

    document.querySelectorAll("[data-read-form]").forEach(function (form) {
        form.addEventListener("submit", function () {
            var button = form.querySelector("button[type='submit']");
            if (!button) return;
            button.classList.add("is-pressed");
            button.dataset.originalText = button.textContent;
            button.textContent = "处理中...";
            button.disabled = true;
        });
    });
})();
