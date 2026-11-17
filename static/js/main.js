document.addEventListener("DOMContentLoaded", () => {
    const motion = window.PharmaMotion;
    if (motion) motion.initPage();

    const themeToggle = document.querySelector(".theme-toggle");
    const applyTheme = (theme) => {
        document.body.dataset.theme = theme;
        if (themeToggle) {
            const nextTheme = theme === "light" ? "sombre" : "clair";
            themeToggle.setAttribute("aria-label", `Activer le thème ${nextTheme}`);
            themeToggle.title = `Passer au thème ${nextTheme}`;
            themeToggle.querySelector("span").textContent = theme === "light" ? "☾" : "☼";
        }
    };
    const storedTheme = window.localStorage.getItem("pharmagest-theme");
    const preferredTheme = window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark";
    applyTheme(storedTheme === "light" || storedTheme === "dark" ? storedTheme : preferredTheme);
    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const nextTheme = document.body.dataset.theme === "light" ? "dark" : "light";
            applyTheme(nextTheme);
            window.localStorage.setItem("pharmagest-theme", nextTheme);
        });
    }

    const sidebar = document.getElementById("sidebar");
    const menuToggle = document.querySelector(".menu-toggle");
    const sidebarBackdrop = document.querySelector(".sidebar-backdrop");
    if (sidebar && menuToggle) {
        const closeMenu = () => {
            if (!sidebar.classList.contains("is-open")) return;
            menuToggle.setAttribute("aria-expanded", "false");
            menuToggle.setAttribute("aria-label", "Ouvrir le menu");
            const finishClose = () => {
                sidebar.classList.remove("is-open");
                if (sidebarBackdrop) sidebarBackdrop.classList.remove("is-visible");
            };
            if (motion) motion.setSidebar(sidebar, false, finishClose);
            else finishClose();
        };
        menuToggle.addEventListener("click", () => {
            const open = !sidebar.classList.contains("is-open");
            if (!open) {
                closeMenu();
                return;
            }
            sidebar.classList.add("is-open");
            if (sidebarBackdrop) sidebarBackdrop.classList.add("is-visible");
            menuToggle.setAttribute("aria-expanded", "true");
            menuToggle.setAttribute("aria-label", "Fermer le menu");
            if (motion) motion.setSidebar(sidebar, true);
        });
        if (sidebarBackdrop) sidebarBackdrop.addEventListener("click", closeMenu);
        document.addEventListener("click", (event) => {
            if (
                sidebar.classList.contains("is-open")
                && !sidebar.contains(event.target)
                && !menuToggle.contains(event.target)
            ) {
                closeMenu();
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeMenu();
        });
    }

    document.querySelectorAll("[data-confirm]").forEach((element) => {
        element.addEventListener("click", (event) => {
            if (!window.confirm(element.dataset.confirm)) event.preventDefault();
        });
    });

    const lines = document.getElementById("sale-lines");
    const addLine = document.getElementById("add-line");
    const totalDisplay = document.getElementById("cart-total");
    if (lines && addLine) {
        const totalForms = document.getElementById("id_lignes-TOTAL_FORMS");
        const emptyRow = document.querySelector("#empty-sale-line .sale-line");
        const catalogue = new Map(
            (window.pharmaCatalogue || []).map((item) => [String(item.id), Number(item.prix)])
        );
        const updateTotal = () => {
            let total = 0;
            lines.querySelectorAll(".sale-line").forEach((row) => {
                const deleted = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
                if (deleted && deleted.checked) return;
                const medicine = row.querySelector('select[name$="-medicament"]');
                const quantity = row.querySelector('input[name$="-quantite"]');
                total += (catalogue.get(medicine?.value) || 0) * (Number(quantity?.value) || 0);
            });
            if (totalDisplay) {
                totalDisplay.textContent = `${new Intl.NumberFormat("fr-FR", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                }).format(total)} Ar`;
            }
        };
        const bindRow = (row) => {
            row.querySelectorAll("select, input").forEach((input) => {
                input.addEventListener("change", updateTotal);
                input.addEventListener("input", updateTotal);
            });
            const remove = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
            if (remove) {
                remove.addEventListener("change", () => {
                    row.classList.toggle("hidden", remove.checked);
                    updateTotal();
                });
            }
        };
        lines.querySelectorAll(".sale-line").forEach(bindRow);
        addLine.addEventListener("click", () => {
            const index = Number(totalForms.value);
            const row = document.createElement("div");
            row.innerHTML = emptyRow.outerHTML.replaceAll("__prefix__", String(index));
            const newRow = row.firstElementChild;
            lines.append(newRow);
            totalForms.value = String(index + 1);
            bindRow(newRow);
            if (motion) motion.revealRow(newRow);
            updateTotal();
        });
        updateTotal();
    }

    const addPurchaseLine = document.getElementById("add-purchase-line");
    if (addPurchaseLine) {
        const totalForms = document.getElementById("id_lignes-TOTAL_FORMS");
        const target = document.getElementById("purchase-lines");
        const template = document.getElementById("empty-purchase-line");
        addPurchaseLine.addEventListener("click", () => {
            const index = Number(totalForms.value);
            const row = document.createElement("tbody");
            row.innerHTML = template.outerHTML
                .replace('id="empty-purchase-line"', "")
                .replace("hidden", "")
                .replaceAll("__prefix__", String(index));
            const newRow = row.firstElementChild;
            newRow.classList.remove("hidden");
            target.append(newRow);
            totalForms.value = String(index + 1);
            if (motion) motion.revealRow(newRow);
        });
    }
});
