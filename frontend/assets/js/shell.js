const MENUS = {
    student: [
        ['dashboard.html', 'layout-dashboard', 'Dashboard'],
        ['profile.html', 'user', 'Profile & Skills'],
        ['portfolio.html', 'folder-kanban', 'Projects & Certificates'],
        ['resume.html', 'file-text', 'Resume AI'],
        ['opportunities.html', 'briefcase-business', 'Opportunities'],
        ['applications.html', 'send', 'Applications'],
        ['career.html', 'route', 'Career Readiness'],
        ['chat.html', 'bot', 'AI Career Chat'],
        ['collaborations.html', 'handshake', 'Collaborations'],
        ['challenges.html', 'trophy', 'Challenges'],
        ['notifications.html', 'bell', 'Notifications']
    ],

    recruiter: [
        ['dashboard.html', 'layout-dashboard', 'Dashboard'],
        ['company.html', 'building-2', 'Company'],
        ['opportunities.html', 'briefcase-business', 'Opportunities'],
        ['applications.html', 'users', 'Applicants'],
        ['collaborations.html', 'handshake', 'Collaborations'],
        ['challenges.html', 'trophy', 'Challenges']
    ],

    college: [
        ['dashboard.html', 'layout-dashboard', 'Dashboard'],
        ['profile.html', 'landmark', 'College Profile'],
        ['departments.html', 'layers-3', 'Departments'],
        ['analytics.html', 'chart-no-axes-column-increasing', 'Skill Analytics'],
        ['collaborations.html', 'handshake', 'Collaborations']
    ],

    admin: [
        ['dashboard.html', 'shield-check', 'Admin Dashboard']
    ]
};


/* =========================================================
   MOBILE SIDEBAR FUNCTIONS
========================================================= */

window.openSidebar = function () {

    const sidebar = document.getElementById('appSidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (!sidebar || !overlay) return;

    sidebar.classList.remove('-translate-x-full');
    overlay.classList.remove('hidden');

    document.body.classList.add('overflow-hidden');
};


window.closeSidebar = function () {

    const sidebar = document.getElementById('appSidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (!sidebar || !overlay) return;

    sidebar.classList.add('-translate-x-full');
    overlay.classList.add('hidden');

    document.body.classList.remove('overflow-hidden');
};


/* =========================================================
   BUILD SHELL
========================================================= */

(async () => {

    const role = window.SKILLBRIDGE_ROLE;

    if (!role) return;


    const me = await Auth.guard(role);

    if (!me) return;


    const current =
        location.pathname
            .split('/')
            .pop() || 'dashboard.html';


    const nav = (MENUS[role] || [])
        .map(([file, icon, label]) => {

            const active =
                current === file
                    ? 'active'
                    : '';

            return `
                <a
                    class="sidebar-link ${active}"
                    href="/${role}/${file}"
                    onclick="closeSidebar()"
                >
                    <i
                        data-lucide="${icon}"
                        class="h-5 w-5 shrink-0"
                    ></i>

                    <span>
                        ${SB.esc(label)}
                    </span>
                </a>
            `;
        })
        .join('');


    const portalName =
        `${role.toUpperCase()} PORTAL`;


    /* =====================================================
       MOBILE TOP BAR
    ===================================================== */

    const mobileHeader = `

        <header
            id="mobileHeader"
            class="mobile-header lg:hidden"
        >

            <div class="flex items-center gap-3">

                <div
                    class="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 font-black text-white"
                >
                    S
                </div>

                <div>

                    <div
                        class="text-sm font-black text-slate-900"
                    >
                        SkillBridge AI
                    </div>

                    <div
                        class="text-[10px] font-bold uppercase tracking-wider text-slate-500"
                    >
                        ${SB.esc(portalName)}
                    </div>

                </div>

            </div>


            <button
                type="button"
                onclick="openSidebar()"
                class="mobile-menu-btn"
                aria-label="Open navigation menu"
            >

                <i
                    data-lucide="menu"
                    class="h-6 w-6"
                ></i>

            </button>

        </header>
    `;


    /* =====================================================
       OVERLAY
    ===================================================== */

    const overlay = `

        <div
            id="sidebarOverlay"
            onclick="closeSidebar()"
            class="sidebar-overlay hidden lg:hidden"
        ></div>
    `;


    /* =====================================================
       SIDEBAR
    ===================================================== */

    const sidebar = `

        <aside
            id="appSidebar"
            class="
                app-sidebar
                fixed
                inset-y-0
                left-0
                z-50
                flex
                w-72
                -translate-x-full
                flex-col
                bg-slate-950
                p-5
                text-white
                transition-transform
                duration-300
                ease-in-out
                lg:translate-x-0
            "
        >

            <!-- HEADER -->

            <div
                class="mb-7 flex items-center justify-between"
            >

                <a
                    href="/"
                    class="flex min-w-0 items-center gap-3"
                >

                    <div
                        class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-indigo-600 font-black"
                    >
                        S
                    </div>

                    <div class="min-w-0">

                        <div
                            class="truncate font-black"
                        >
                            SkillBridge AI
                        </div>

                        <div
                            class="truncate text-xs text-slate-400"
                        >
                            ${SB.esc(portalName)}
                        </div>

                    </div>

                </a>


                <!-- MOBILE CLOSE -->

                <button
                    type="button"
                    onclick="closeSidebar()"
                    class="sidebar-close-btn lg:hidden"
                    aria-label="Close navigation menu"
                >

                    <i
                        data-lucide="x"
                        class="h-5 w-5"
                    ></i>

                </button>

            </div>


            <!-- NAVIGATION -->

            <nav
                class="sidebar-nav flex-1 space-y-1 overflow-y-auto pr-1"
            >

                ${nav}

            </nav>


            <!-- USER -->

            <div
                class="mt-5 rounded-xl bg-white/5 p-4"
            >

                <div
                    class="truncate text-sm font-bold"
                >
                    ${SB.esc(
                        me.full_name ||
                        me.email ||
                        'User'
                    )}
                </div>


                <div
                    class="mt-1 truncate text-xs text-slate-400"
                >
                    ${SB.esc(
                        me.email || ''
                    )}
                </div>


                <button
                    type="button"
                    onclick="Auth.logout()"
                    class="
                        mt-3
                        flex
                        items-center
                        gap-2
                        text-sm
                        font-bold
                        text-rose-300
                        hover:text-rose-200
                    "
                >

                    <i
                        data-lucide="log-out"
                        class="h-4 w-4"
                    ></i>

                    Sign out

                </button>

            </div>

        </aside>
    `;


    document.body.insertAdjacentHTML(
        'afterbegin',
        mobileHeader + overlay + sidebar
    );


    /* =====================================================
       MOBILE CONTENT SPACING
    ===================================================== */

    document.body.classList.add(
        'has-skillbridge-shell'
    );


    /* =====================================================
       ESC KEY CLOSE
    ===================================================== */

    document.addEventListener(
        'keydown',
        event => {

            if (event.key === 'Escape') {
                closeSidebar();
            }

        }
    );


    /* =====================================================
       CLOSE WHEN SCREEN CHANGES TO DESKTOP
    ===================================================== */

    window.addEventListener(
        'resize',
        () => {

            if (window.innerWidth >= 1024) {

                const overlay =
                    document.getElementById(
                        'sidebarOverlay'
                    );

                if (overlay) {
                    overlay.classList.add('hidden');
                }

                document.body.classList.remove(
                    'overflow-hidden'
                );
            }

        }
    );


    if (window.lucide) {
        lucide.createIcons();
    }

})();