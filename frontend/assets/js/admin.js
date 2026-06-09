const API_BASE_URL = "https://edugen-full.onrender.com";

document.addEventListener("DOMContentLoaded", () => {
    
    // 1. SECURITY CHECK (Redirect if not admin)
    const currentUser = JSON.parse(localStorage.getItem("edugen_user"));
    
    // Checks if role is admin OR name is "System Admin" (to match our dummy data)
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.name !== 'System Admin')) {
        alert("Access Denied: You must be an Administrator.");
        window.location.href = "login.html"; 
        return;
    }

    // 2. LOGOUT LOGIC
    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", (e) => {
            e.preventDefault();
            localStorage.removeItem("edugen_user");
            window.location.href = "home.html";
        });
    }

    // Notice: We removed the old fetchUsers() function! 
    // The students are now safely loaded by the script inside admin_dashboard.html.
});