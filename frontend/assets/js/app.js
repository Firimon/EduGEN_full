// assets/js/app.js

document.addEventListener("DOMContentLoaded", () => {
    const currentYearEl = document.getElementById("currentYear");
    if (currentYearEl) currentYearEl.textContent = new Date().getFullYear();

    const assessmentForm = document.getElementById("assessmentForm");
    const careerList = document.getElementById("careerList");
    const recommendationSubtitle = document.getElementById("recommendationSubtitle");
    const chipButtons = document.querySelectorAll(".chip-group .chip");
    const searchInput = document.getElementById("searchCareer");

    const statDominantCluster = document.getElementById("statDominantCluster");
    const statSavedCount = document.getElementById("statSavedCount");
    const statReadinessScore = document.getElementById("statReadinessScore");
    const savedCareersContainer = document.getElementById("savedCareers");

    const btnStartAssessment = document.getElementById("btnStartAssessment");
    const btnExploreCareers = document.getElementById("btnExploreCareers");

    // Scroll helpers
    btnStartAssessment?.addEventListener("click", () => {
        document.getElementById("assessment")?.scrollIntoView({ behavior: "smooth" });
    });

    btnExploreCareers?.addEventListener("click", () => {
        document.getElementById("recommendations")?.scrollIntoView({ behavior: "smooth" });
    });

    // State
    let currentClusterFilter = "all";
    let currentExperienceLevel = "student";
    let currentSearchQuery = "";
    let currentScores = { tech: 0, creative: 0, social: 0 };

    // LocalStorage keys
    const SAVED_CAREERS_KEY = "edugen_saved_careers";

    // User helper (auth.js stores user here)
    function getCurrentUser() {
        try {
            const raw = localStorage.getItem("edugen_user");
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    }

    // Load saved careers from localStorage
    function loadSavedCareers() {
        try {
            const raw = localStorage.getItem(SAVED_CAREERS_KEY);
            if (!raw) return [];
            const parsed = JSON.parse(raw);
            if (!Array.isArray(parsed)) return [];
            return parsed;
        } catch (e) {
            console.warn("Failed to parse saved careers", e);
            return [];
        }
    }

    function saveCareerIds(ids) {
        localStorage.setItem(SAVED_CAREERS_KEY, JSON.stringify(ids));
    }

    // Render career grid
    function renderCareerCards(list) {
        if (!careerList) return;
        careerList.innerHTML = "";

        if (list.length === 0) {
            careerList.innerHTML =
                '<p class="text-muted small">No careers match your filters yet. Try broadening your search.</p>';
            return;
        }

        const savedIds = loadSavedCareers();

        list.forEach((career) => {
            const card = document.createElement("article");
            card.className = "card career-card";

            const isSaved = savedIds.includes(career.id);

            card.innerHTML = `
                <span class="career-chip">${formatClusterLabel(career.cluster)}</span>
                <h3>${career.title}</h3>
                <p>${career.description}</p>
                <div class="career-meta">
                    <span>Growth Outlook: <strong>${career.growthScore}%</strong></span>
                    <span>Levels: ${career.level.join(", ")}</span>
                </div>
                <div class="career-tags">
                    ${career.tags
                        .map((t) => `<span class="career-tag">${t}</span>`)
                        .join("")}
                </div>
                <div style="margin-top: 12px; display:flex; gap:8px; flex-wrap:wrap;">
                    <button class="btn btn-ghost btn-save" data-id="${
                        career.id
                    }">${isSaved ? "Saved" : "Save Path"}</button>
                    <button class="btn btn-ghost btn-details" data-id="${
                        career.id
                    }">View Details</button>
                </div>
            `;

            careerList.appendChild(card);
        });

        // Attach save handlers
        careerList.querySelectorAll(".btn-save").forEach((btn) => {
            btn.addEventListener("click", (event) => {
                const id = event.currentTarget.getAttribute("data-id");
                toggleSaveCareer(id);
            });
        });

        // Placeholder details
        careerList.querySelectorAll(".btn-details").forEach((btn) => {
            btn.addEventListener("click", (event) => {
                const id = event.currentTarget.getAttribute("data-id");
                const career = CAREER_DATA.find((c) => c.id === id);
                if (career) {
                    alert(
                        `${career.title}\n\n${career.description}\n\n(Here you can later open a dedicated page or modal with AI-generated pathways, skill gaps, and learning resources.)`
                    );
                }
            });
        });
    }

    function formatClusterLabel(cluster) {
        if (cluster === "tech") return "Tech & Data";
        if (cluster === "creative") return "Creative & Design";
        if (cluster === "social") return "People & Service";
        return cluster;
    }

    // Save / remove careers (requires login)
    function toggleSaveCareer(id) {
        const user = getCurrentUser();
        if (!user) {
            alert("Please log in to save career paths.");
            document.getElementById("auth")?.scrollIntoView({ behavior: "smooth" });
            return;
        }

        let saved = loadSavedCareers();
        if (saved.includes(id)) {
            saved = saved.filter((x) => x !== id);
        } else {
            saved.push(id);
        }
        saveCareerIds(saved);
        updateSavedCareersUI();
        // Re-render careers to update button text
        syncCareerRendering();
    }

    function updateSavedCareersUI() {
        if (!savedCareersContainer) return;
        const savedIds = loadSavedCareers();
        statSavedCount.textContent = String(savedIds.length);

        savedCareersContainer.innerHTML = "";

        if (savedIds.length === 0) {
            savedCareersContainer.innerHTML =
                '<p class="text-muted small">No paths saved yet. Tap “Save Path” on a role you like.</p>';
            return;
        }

        savedIds.forEach((id) => {
            const career = CAREER_DATA.find((c) => c.id === id);
            if (!career) return;

            const pill = document.createElement("div");
            pill.className = "saved-career-pill";
            pill.innerHTML = `
                <span>${career.title}</span>
                <button data-id="${career.id}">Remove</button>
            `;
            savedCareersContainer.appendChild(pill);
        });

        savedCareersContainer.querySelectorAll("button").forEach((btn) => {
            btn.addEventListener("click", (event) => {
                const id = event.currentTarget.getAttribute("data-id");
                let saved = loadSavedCareers().filter((x) => x !== id);
                saveCareerIds(saved);
                updateSavedCareersUI();
                syncCareerRendering();
            });
        });
    }

    // Apply filters and search
    function syncCareerRendering() {
        const filtered = filterCareersByProfile(currentClusterFilter, currentExperienceLevel);

        const finalList = filtered.filter((c) => {
            if (!currentSearchQuery) return true;
            const q = currentSearchQuery.toLowerCase();
            return (
                c.title.toLowerCase().includes(q) ||
                c.description.toLowerCase().includes(q) ||
                c.tags.some((t) => t.toLowerCase().includes(q))
            );
        });

        renderCareerCards(finalList);
    }

    // Assessment submission
    assessmentForm?.addEventListener("submit", (event) => {
        event.preventDefault();

        const form = event.currentTarget;
        const data = new FormData(form);

        const answers = [data.get("q1"), data.get("q2"), data.get("q3")];

        currentScores = { tech: 0, creative: 0, social: 0 };

        answers.forEach((ans) => {
            if (!ans) return;
            currentScores[ans] += 1;
        });

        currentExperienceLevel = data.get("experienceLevel") || "student";

        const dominantCluster = getDominantCluster(currentScores);
        currentClusterFilter = dominantCluster;

        if (recommendationSubtitle) {
            recommendationSubtitle.textContent = `Based on your current answers, you lean towards: ${formatClusterLabel(
                dominantCluster
            )}. Showing recommended roles.`;
        }

        if (statDominantCluster) {
            statDominantCluster.textContent = formatClusterLabel(dominantCluster);
        }

        if (statReadinessScore) {
            const total = answers.filter(Boolean).length || 1;
            const score = Math.round(((currentScores[dominantCluster] || 0) / total) * 40 + 60);
            statReadinessScore.textContent = `${score}%`;
        }

        // Highlight active chip
        chipButtons.forEach((chip) => {
            const filter = chip.getAttribute("data-filter");
            chip.classList.toggle("chip-active", filter === dominantCluster);
        });

        syncCareerRendering();
        document.getElementById("recommendations")?.scrollIntoView({ behavior: "smooth" });
    });

    // Chips filter
    chipButtons.forEach((chip) => {
        chip.addEventListener("click", () => {
            chipButtons.forEach((c) => c.classList.remove("chip-active"));
            chip.classList.add("chip-active");
            currentClusterFilter = chip.getAttribute("data-filter") || "all";
            syncCareerRendering();
        });
    });

    // Search
    searchInput?.addEventListener("input", (event) => {
        currentSearchQuery = event.target.value;
        syncCareerRendering();
    });

    // Initialize UI
    updateSavedCareersUI();
    syncCareerRendering();

    // AI placeholder: later you can connect this to your backend API
    const btnAskAI = document.getElementById("btnAskAI");
    const aiQuestion = document.getElementById("aiQuestion");
    const aiResponsePlaceholder = document.getElementById("aiResponsePlaceholder");

    btnAskAI?.addEventListener("click", () => {
        if (!aiQuestion.value.trim()) {
            alert("Please type a question first.");
            return;
        }
        aiResponsePlaceholder.textContent =
            "This is a placeholder. Here you will see responses from your EduGEN LLM + RAG backend.";
    });
});
