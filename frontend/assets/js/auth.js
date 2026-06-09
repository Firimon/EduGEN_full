// Ensure this matches your Python port (5001)
const API_BASE_URL = "https://edugen-full.onrender.com"; 

document.addEventListener("DOMContentLoaded", () => {
    // --- UI Elements ---
    const btnLogout = document.getElementById("logoutLink") || document.getElementById("btnLogout");
    const btnLoginNav = document.getElementById("navLoginLink"); 
    const signupLink = document.getElementById("navSignupLink");
    const navJobs = document.getElementById("navJobs");
    const userNavContainer = document.getElementById("userNavContainer");
    const welcomeText = document.getElementById("welcomeText");
    const exploreMoreBtn = document.getElementById("exploreMoreBtn");

    // Forms
    const registerForm = document.getElementById("registerForm");
    const loginForm = document.getElementById("loginForm");
    const forgotPasswordForm = document.getElementById("forgotPasswordForm"); 
    const loginMessage = document.getElementById("loginMessage");
    const registerMessage = document.getElementById("registerMessage");

    // --- 1. SESSION MANAGEMENT ---
    let currentUser = null;
    try {
        const raw = localStorage.getItem("edugen_user");
        currentUser = (raw && raw !== "null" && raw !== "undefined") ? JSON.parse(raw) : null;
    } catch { currentUser = null; }

    function updateAuthUI() {
        if (currentUser) {
            if (btnLoginNav) btnLoginNav.style.display = "none";
            if (signupLink) signupLink.style.display = "none";
            if (btnLogout) btnLogout.style.display = "inline-block";
            if (navJobs) navJobs.style.display = "block";
            if (userNavContainer) userNavContainer.style.display = "flex";
            if (welcomeText) {
                welcomeText.textContent = "Hi, " + (currentUser.name || "User");
                welcomeText.style.display = "inline-block";
            }
        } else {
            if (btnLoginNav) btnLoginNav.style.display = "block";
            if (signupLink) signupLink.style.display = "inline-flex";
            if (btnLogout) btnLogout.style.display = "none";
            if (navJobs) navJobs.style.display = "none";
            if (userNavContainer) userNavContainer.style.display = "none";
            if (welcomeText) welcomeText.style.display = "none";
        }
    }
    updateAuthUI();

    // --- EXPLORE MORE BUTTON PROTECTION ---
    if (exploreMoreBtn) {
        exploreMoreBtn.addEventListener("click", function(e) {
            e.preventDefault();
            // Re-check storage in case they logged in/out in another tab
            const session = localStorage.getItem("edugen_user");
            if (session && session !== "null") {
                window.location.href = "job-engine.html";
            } else {
                window.location.href = "login.html";
            }
        });
    }

    // Logout
    btnLogout?.addEventListener("click", (e) => {
        e.preventDefault();
        localStorage.removeItem("edugen_user");
        window.location.href = "home.html"; 
    });

    // --- 2. LOGIN HANDLER ---
    loginForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("loginEmail").value.trim();
        const password = document.getElementById("loginPassword").value;
        const role = document.getElementById("loginRole")?.value || "user";

        try {
            const res = await fetch(`${API_BASE_URL}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password, role }),
            });
            const data = await res.json();
            if (!res.ok) {
                if (loginMessage) loginMessage.textContent = data.message || "Login failed.";
                return;
            }
            localStorage.setItem("edugen_user", JSON.stringify(data.user));
            window.location.href = (data.user.role === 'admin') ? "admin_dashboard.html" : "dashboard.html";
        } catch (err) {
            if (loginMessage) loginMessage.textContent = "Server error. Is Flask running?";
        }
    });

    // --- 3. REGISTER HANDLER ---
    registerForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = document.getElementById("regName")?.value.trim() || document.getElementById("fullname")?.value.trim();
        const email = document.getElementById("regEmail")?.value.trim() || document.getElementById("email")?.value.trim();
        const password = document.getElementById("regPassword")?.value || document.getElementById("password")?.value;

        try {
            const res = await fetch(`${API_BASE_URL}/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, password }),
            });
            const data = await res.json();
            if (!res.ok) {
                if (registerMessage) registerMessage.textContent = data.message;
                return;
            }
            window.location.href = "login.html";
        } catch (err) {
            if (registerMessage) registerMessage.textContent = "Network error.";
        }
    });
});