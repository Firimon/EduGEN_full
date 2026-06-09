// assets/js/data.js

// Simple mock "database" of careers.
// Later, you can replace this with API calls or a real DB via your backend.

const CAREER_DATA = [
    {
        id: "data-analyst",
        title: "Data Analyst",
        cluster: "tech",
        level: ["student", "junior", "mid"],
        growthScore: 88,
        description:
            "Collect, clean, and analyze data to help organizations make better decisions.",
        tags: ["SQL", "Python", "Dashboards", "Business Intelligence"],
    },
    {
        id: "ml-engineer",
        title: "Machine Learning Engineer",
        cluster: "tech",
        level: ["junior", "mid", "senior"],
        growthScore: 92,
        description:
            "Design and deploy ML models, work closely with data scientists and engineers.",
        tags: ["ML", "Python", "MLOps", "Cloud"],
    },
    {
        id: "ux-designer",
        title: "UX / UI Designer",
        cluster: "creative",
        level: ["student", "junior", "mid"],
        growthScore: 81,
        description:
            "Design intuitive user experiences and interfaces for digital products.",
        tags: ["Prototyping", "User Research", "Figma", "Visual Design"],
    },
    {
        id: "content-strategist",
        title: "Content Strategist",
        cluster: "creative",
        level: ["student", "junior", "mid"],
        growthScore: 76,
        description:
            "Plan and create content that supports brand, marketing, and product goals.",
        tags: ["Writing", "Storytelling", "SEO", "Campaigns"],
    },
    {
        id: "career-counselor",
        title: "Career Counselor",
        cluster: "social",
        level: ["junior", "mid", "senior"],
        growthScore: 74,
        description:
            "Guide individuals in understanding their skills, interests, and career options.",
        tags: ["Coaching", "Psychology", "Communication"],
    },
    {
        id: "hr-business-partner",
        title: "HR Business Partner",
        cluster: "social",
        level: ["mid", "senior"],
        growthScore: 79,
        description:
            "Work with leaders to align people strategy with business strategy.",
        tags: ["HR", "Leadership", "People Development"],
    },
    {
        id: "product-manager",
        title: "Product Manager",
        cluster: "tech",
        level: ["mid", "senior"],
        growthScore: 86,
        description:
            "Own product vision, roadmap, and execution across cross-functional teams.",
        tags: ["Roadmaps", "Prioritization", "Stakeholders"],
    },
    {
        id: "instructional-designer",
        title: "Instructional Designer",
        cluster: "creative",
        level: ["student", "junior", "mid"],
        growthScore: 80,
        description:
            "Design learning experiences, courses, and digital training content.",
        tags: ["Education", "Design", "E-learning"],
    },
];

// Utility: choose recommended cluster based on simple scoring from answers
function getDominantCluster(scores) {
    const entries = Object.entries(scores);
    entries.sort((a, b) => b[1] - a[1]);
    return entries[0][0]; // "tech" | "creative" | "social"
}

// Filter careers based on cluster + experience level
function filterCareersByProfile(cluster, experienceLevel) {
    return CAREER_DATA.filter((career) => {
        const clusterMatch = cluster === "all" ? true : career.cluster === cluster;
        const levelMatch = experienceLevel
            ? career.level.includes(experienceLevel)
            : true;
        return clusterMatch && levelMatch;
    });
}
