
const authSection = document.getElementById("auth-section");
const taskSection = document.getElementById("task-section");
const authMsg = document.getElementById("auth-msg");
const taskMsg = document.getElementById("task-msg");
const list = document.getElementById("task-list");
const emptyMsg = document.getElementById("empty-msg");
const countEl = document.getElementById("task-count");

const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");

const titleInput = document.getElementById("task-title");
const categoryInput = document.getElementById("task-category");
const priorityInput = document.getElementById("task-priority");
const dueInput = document.getElementById("task-due");

const editModal = document.getElementById("edit-modal");
const editTitle = document.getElementById("edit-title");
const editCategory = document.getElementById("edit-category");
const editPriority = document.getElementById("edit-priority");
const editDue = document.getElementById("edit-due");
const editMsg = document.getElementById("edit-msg");

let editingTaskId = null;
let searchTimer = null;
let currentFilter = "all";

async function api(url, method = "GET", body = null) {
    try {
        const options = {
            method,
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin"
        };

        if (body !== null) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(url, options);

        const data = await response.json();

        return {
            ok: response.ok,
            data: data
        };

    } catch (error) {
        console.error(error);

        return {
            ok: false,
            data: { error: "Server connection failed. Check Flask server." }
        };
    }
}

function showApp() {
    authSection.classList.add("hidden");
    taskSection.classList.remove("hidden");
}

function showAuth() {
    taskSection.classList.add("hidden");
    authSection.classList.remove("hidden");
}

function makeButton(text, callback) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = text;
    button.addEventListener("click", callback);
    return button;
}

function createBadge(text, className) {
    const badge = document.createElement("span");
    badge.className = className;
    badge.textContent = text;
    return badge;
}

// Dashboard
async function loadDashboard() {
    const result = await api("/api/dashboard");

    if (!result.ok) return;

    const data = result.data;

    const elements = {
        "stat-total": data.total ?? 0,
        "stat-pending": data.pending ?? 0,
        "stat-done": data.done ?? 0,
        "stat-overdue": data.overdue ?? 0,
        "stat-progress": (data.progress ?? 0) + "%"
    };

    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    });

    const fill = document.getElementById("progress-fill");

    if (fill) {
        fill.style.width = (data.progress ?? 0) + "%";
    }
}

// Edit modal
function openEditModal(task) {
    editingTaskId = task.id;

    editTitle.value = task.title;
    editCategory.value = task.category || "work";
    editPriority.value = task.priority || "medium";
    editDue.value = task.due_date || "";

    editMsg.textContent = "";
    editModal.classList.remove("hidden");
}

function closeEditModal() {
    editModal.classList.add("hidden");
    editingTaskId = null;
    editMsg.textContent = "";
}

document.getElementById("close-modal")?.addEventListener(
    "click", closeEditModal
);

document.getElementById("cancel-edit")?.addEventListener(
    "click", closeEditModal
);

document.getElementById("save-edit")?.addEventListener("click", async () => {
    const title = editTitle.value.trim();

    if (!title) {
        editMsg.textContent = "Please enter task title";
        return;
    }

    const result = await api(`/api/tasks/${editingTaskId}`, "PUT", {
        title,
        category: editCategory.value,
        priority: editPriority.value,
        due_date: editDue.value
    });

    if (result.ok) {
        closeEditModal();
        await loadTasks();
    } else {
        editMsg.textContent = result.data.error || "Unable to update task";
    }
});

// Update task status
async function updateTask(id, status) {
    const result = await api(`/api/tasks/${id}`, "PUT", { status });

    if (result.ok) {
        await loadTasks();
    } else {
        alert(result.data.error || "Unable to update task");
    }
}

// Load tasks
async function loadTasks() {
    const searchInput = document.getElementById("search-input");
    const search = searchInput ? searchInput.value.trim() : "";

    const result = await api(
        `/api/tasks?status=${encodeURIComponent(currentFilter)}&q=${encodeURIComponent(search)}`
    );

    if (!result.ok || !Array.isArray(result.data)) {
        list.innerHTML = "";
        emptyMsg.textContent = result.data.error || "Unable to load tasks";
        emptyMsg.classList.remove("hidden");
        return;
    }

    const tasks = result.data;
    list.innerHTML = "";

    countEl.textContent = `${tasks.length} Tasks`;

    if (tasks.length === 0) {
        emptyMsg.textContent = "No tasks found. Create your first task!";
        emptyMsg.classList.remove("hidden");
    } else {
        emptyMsg.classList.add("hidden");
    }

    tasks.forEach(task => {
        const item = document.createElement("li");
        item.className = "task-item";

        const details = document.createElement("div");
        details.className = "task-details";

        const heading = document.createElement("div");
        heading.className = "task-heading";

        const taskTitle = document.createElement("span");
        taskTitle.className = "task-title";
        taskTitle.textContent = task.title;

        if (task.status === "done") {
            taskTitle.classList.add("completed");
        }

        heading.appendChild(taskTitle);

        const meta = document.createElement("div");
        meta.className = "task-meta";

        const categories = {
            work: "Work",
            study: "Study",
            personal: "Personal"
        };

        meta.appendChild(createBadge(
            categories[task.category] || "Work",
            "category-badge"
        ));

        meta.appendChild(createBadge(
            (task.priority || "medium").toUpperCase(),
            `badge ${task.priority || "medium"}`
        ));

        if (task.due_date) {
            meta.appendChild(createBadge(
                `Due: ${task.due_date}`,
                "due-badge"
            ));
        }

        details.appendChild(heading);
        details.appendChild(meta);

        const actions = document.createElement("div");
        actions.className = "task-actions";

        actions.appendChild(makeButton(
            task.status === "done" ? "Undo" : "Done",
            () => updateTask(
                task.id,
                task.status === "done" ? "pending" : "done"
            )
        ));

        actions.appendChild(makeButton(
            "Edit",
            () => openEditModal(task)
        ));

        actions.appendChild(makeButton("Delete", async () => {
            if (!confirm("Are you sure you want to delete this task?")) {
                return;
            }

            const response = await api(`/api/tasks/${task.id}`, "DELETE");

            if (response.ok) {
                await loadTasks();
            } else {
                alert(response.data.error || "Unable to delete task");
            }
        }));

        item.appendChild(details);
        item.appendChild(actions);
        list.appendChild(item);
    });

    await loadDashboard();
}

// Register account
document.getElementById("register-btn").addEventListener("click", async () => {
    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    authMsg.textContent = "";

    if (!username || !password) {
        authMsg.textContent = "Please enter username and password";
        return;
    }

    if (password.length < 6) {
        authMsg.textContent = "Password must contain at least 6 characters";
        return;
    }

    const result = await api("/api/register", "POST", {
        username,
        password
    });

    if (result.ok) {
        authMsg.textContent = "Account created successfully! Please login.";
        passwordInput.value = "";
    } else {
        authMsg.textContent = result.data.error || "Registration failed";
    }
});

// Login
document.getElementById("login-btn").addEventListener("click", async () => {
    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    authMsg.textContent = "";

    if (!username || !password) {
        authMsg.textContent = "Please enter username and password";
        return;
    }

    const result = await api("/api/login", "POST", {
        username,
        password
    });

    if (result.ok) {
        showApp();
        authMsg.textContent = "";
        passwordInput.value = "";
        await loadTasks();
    } else {
        authMsg.textContent = result.data.error || "Login failed";
    }
});

// Logout
document.getElementById("logout-btn")?.addEventListener("click", async () => {
    await api("/api/logout", "POST");
    showAuth();
});

// Task filters
document.querySelectorAll(".filter-btn").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn").forEach(btn => {
            btn.classList.remove("active");
        });

        button.classList.add("active");
        currentFilter = button.dataset.filter || "all";

        loadTasks();
    });
});

// Search
document.getElementById("search-input")?.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadTasks, 300);
});

// Add task - activates when the add-task HTML form is present
document.getElementById("add-btn")?.addEventListener("click", async () => {
    const title = titleInput.value.trim();

    if (!title) {
        taskMsg.textContent = "Please enter a task title";
        return;
    }

    const result = await api("/api/tasks", "POST", {
        title,
        category: categoryInput.value,
        priority: priorityInput.value,
        due_date: dueInput.value
    });

    if (result.ok) {
        titleInput.value = "";
        dueInput.value = "";
        taskMsg.textContent = "Task added successfully!";
        await loadTasks();
    } else {
        taskMsg.textContent = result.data.error || "Unable to add task";
    }
});

// Check login session
async function checkSession() {
    const result = await api("/api/tasks");

    if (result.ok) {
        showApp();
        await loadTasks();
    } else {
        showAuth();
    }
}

checkSession();
document.getElementById("export-btn")?.addEventListener("click", () => {
    window.location.href = "/api/tasks/export";
});
const themeToggle = document.getElementById("theme-toggle");

// Load saved theme
if (localStorage.getItem("taskflow-theme") === "dark") {
    document.body.classList.add("dark-mode");
    themeToggle.textContent = "☀️ Light Mode";
}

themeToggle?.addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");

    const isDark = document.body.classList.contains("dark-mode");

    localStorage.setItem("taskflow-theme", isDark ? "dark" : "light");

    themeToggle.textContent = isDark ? "☀️ Light Mode" : "🌙 Dark Mode";
});