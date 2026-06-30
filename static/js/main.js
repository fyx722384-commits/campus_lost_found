(function () {
    function showToast(message, category) {
        var root = document.getElementById("toast-root");
        if (!root) return;
        var toast = document.createElement("div");
        toast.className = "toast " + (category || "success");
        toast.textContent = message;
        root.appendChild(toast);
        setTimeout(function () {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(20px)";
            setTimeout(function () { toast.remove(); }, 220);
        }, 2800);
    }

    document.querySelectorAll(".flash-message").forEach(function (node) {
        showToast(node.textContent, node.dataset.category);
    });

    document.querySelectorAll("[data-filter-form]").forEach(function (form) {
        var keyword = form.querySelector('input[name="keyword"]');
        var cards = document.querySelectorAll("[data-search]");
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
        });
    });

    document.querySelectorAll(".stat-card").forEach(function (card, index) {
        card.style.animationDelay = (index * 45) + "ms";
    });

    document.querySelectorAll(".progress span").forEach(function (bar) {
        var target = bar.style.getPropertyValue("--target");
        bar.style.setProperty("--target", target || "0%");
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
})();
