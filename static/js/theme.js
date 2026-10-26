
(function () {
    const STORAGE_KEY = "site-theme";

    function getSavedTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY) || "light";
        } catch (error) {
            return "light";
        }
    }

    function applyTheme(theme) {
        const selectedTheme = theme === "dark" ? "dark" : "light";

        document.documentElement.setAttribute("data-theme", selectedTheme);

        const button = document.getElementById("theme-toggle");

        if (button) {
            button.textContent =
                selectedTheme === "dark" ? "Light mode" : "Dark mode";
        }
    }

    applyTheme(getSavedTheme());

    document.addEventListener("DOMContentLoaded", function () {
        const button = document.getElementById("theme-toggle");

        if (!button) return;

        button.addEventListener("click", function () {
            const currentTheme =
                document.documentElement.getAttribute("data-theme");

            const nextTheme =
                currentTheme === "dark" ? "light" : "dark";

            try {
                localStorage.setItem(STORAGE_KEY, nextTheme);
            } catch (error) {
                console.warn("Could not save theme preference.");
            }

            applyTheme(nextTheme);
        });
    });
})();
