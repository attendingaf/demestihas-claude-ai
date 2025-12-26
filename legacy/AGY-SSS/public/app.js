document.addEventListener('DOMContentLoaded', async () => {
    let allEvents = [];
    let calendar;
    const activeFilters = new Set(['all']); // 'all' or specific categories

    // DOM Elements
    const heroCard = document.getElementById('hero-card');
    const modal = document.getElementById('event-modal');
    const subscribeModal = document.getElementById('subscribe-modal');
    const filterChips = document.querySelectorAll('.filter-chip');
    const lastUpdatedEl = document.getElementById('last-updated');

    // 1. Fetch Data
    try {
        const response = await fetch('data.json');
        const data = await response.json();

        // Handle new structure or fallback
        if (data.events) {
            allEvents = data.events;
            if (data.lastUpdated && lastUpdatedEl) {
                const date = new Date(data.lastUpdated);
                lastUpdatedEl.textContent = `Last updated: ${date.toLocaleString()}`;
            }
        } else {
            allEvents = data; // Fallback for old format
        }

        initApp();
    } catch (error) {
        console.error('Failed to load data:', error);
        document.querySelector('main').innerHTML = '<p style="text-align:center; padding: 2rem;">Failed to load calendar data. Please try again later.</p>';
    }

    function initApp() {
        initCalendar();
        updateHeroCard();
        setupFilters();
        setupModals();
        setupHeroClick();

        // Refresh hero timer every minute
        setInterval(updateHeroCard, 60000);
    }

    function initCalendar() {
        const calendarEl = document.getElementById('calendar');
        calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: window.innerWidth < 768 ? 'listWeek' : 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,dayGridWeek,listWeek'
            },
            buttonText: {
                today: 'Today',
                dayGridMonth: 'Month',
                dayGridWeek: 'Week',
                listWeek: 'List'
            },
            height: 'auto',
            events: allEvents,
            eventClick: function (info) {
                openEventModal(info.event);
            },
            eventDidMount: function (info) {
                // Filter logic
                if (!activeFilters.has('all') && !activeFilters.has(info.event.extendedProps.category)) {
                    info.el.style.display = 'none';
                }
            },
            eventContent: function (arg) {
                // Custom render for grid views to show badge
                if (arg.view.type === 'dayGridMonth' || arg.view.type === 'dayGridWeek') {
                    return {
                        html: `<div class="fc-content">
                                <span class="fc-title" style="font-weight:600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block;">
                                    ${arg.event.extendedProps.badge || ''} ${arg.event.title}
                                </span>
                               </div>`
                    };
                }
                // Return undefined for List view to use default rendering (which includes title)
            }
        });
        calendar.render();
    }

    function updateHeroCard() {
        const now = new Date();
        // Find next event
        const upcoming = allEvents
            .map(e => ({ ...e, start: new Date(e.start) }))
            .filter(e => e.start > now)
            .sort((a, b) => a.start - b.start)[0];

        if (!upcoming) {
            heroCard.classList.add('hidden');
            return;
        }

        heroCard.classList.remove('hidden');
        // Store event ID on the card for click handler
        heroCard.dataset.eventId = upcoming.id;

        // Update Content
        document.getElementById('hero-home-name').textContent = upcoming.title.split(' vs ')[0] || upcoming.title;
        document.getElementById('hero-away-name').textContent = upcoming.title.split(' vs ')[1] || '';

        // Logos
        const homeLogo = document.getElementById('hero-home-logo');
        const awayLogo = document.getElementById('hero-away-logo');

        if (upcoming.teamId) {
            homeLogo.src = `assets/team-logos/${upcoming.teamId}.png`;
        }

        document.getElementById('hero-venue').textContent = upcoming.location;
        document.getElementById('hero-time').textContent = new Date(upcoming.start).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });

        // Timer
        const diff = upcoming.start - now;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        document.getElementById('hero-timer').textContent = `IN ${days}D ${hours}H`;

        // Watch Button
        const btn = document.getElementById('hero-watch-btn');
        if (upcoming.streaming && upcoming.streaming.length > 0) {
            btn.href = upcoming.streaming[0].url;
            btn.textContent = `Watch on ${upcoming.streaming[0].name}`;
            // Prevent card click when clicking button
            btn.onclick = (e) => e.stopPropagation();
        } else {
            btn.href = '#';
            btn.textContent = 'Check Listings';
        }
    }

    function setupHeroClick() {
        heroCard.addEventListener('click', () => {
            const eventId = heroCard.dataset.eventId;
            if (eventId) {
                const event = calendar.getEventById(eventId);
                if (event) {
                    openEventModal(event);
                } else {
                    // Fallback if event not in calendar (e.g. filtered out?) 
                    // Actually we have allEvents array
                    const evtData = allEvents.find(e => e.id === eventId);
                    if (evtData) {
                        // Create a mock event object for the modal
                        openEventModal({
                            title: evtData.title,
                            start: new Date(evtData.start),
                            extendedProps: {
                                badge: evtData.badge,
                                location: evtData.location,
                                streaming: evtData.streaming
                            }
                        });
                    }
                }
            }
        });

        // Keyboard support
        heroCard.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                heroCard.click();
            }
        });
    }

    function setupFilters() {
        filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                const filter = chip.dataset.filter;

                // Toggle logic
                if (filter === 'all') {
                    activeFilters.clear();
                    activeFilters.add('all');
                    filterChips.forEach(c => {
                        c.classList.remove('active');
                        c.setAttribute('aria-pressed', 'false');
                    });
                    chip.classList.add('active');
                    chip.setAttribute('aria-pressed', 'true');
                } else {
                    activeFilters.delete('all');
                    const allChip = document.querySelector('[data-filter="all"]');
                    allChip.classList.remove('active');
                    allChip.setAttribute('aria-pressed', 'false');

                    if (activeFilters.has(filter)) {
                        activeFilters.delete(filter);
                        chip.classList.remove('active');
                        chip.setAttribute('aria-pressed', 'false');
                    } else {
                        activeFilters.add(filter);
                        chip.classList.add('active');
                        chip.setAttribute('aria-pressed', 'true');
                    }

                    if (activeFilters.size === 0) {
                        activeFilters.add('all');
                        allChip.classList.add('active');
                        allChip.setAttribute('aria-pressed', 'true');
                    }
                }

                // Rerender calendar events
                calendar.removeAllEvents();
                const filteredEvents = allEvents.filter(e => {
                    if (activeFilters.has('all')) return true;
                    return activeFilters.has(e.category);
                });
                calendar.addEventSource(filteredEvents);
            });
        });
    }

    function openEventModal(event) {
        const props = event.extendedProps;

        document.getElementById('modal-title').textContent = event.title;
        document.getElementById('modal-badge').textContent = props.badge;
        document.getElementById('modal-date-time').textContent = `📅 ${event.start.toLocaleString([], { weekday: 'long', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}`;
        document.getElementById('modal-venue').textContent = `📍 ${props.location}`;

        const streamContainer = document.getElementById('modal-streaming-options');
        streamContainer.innerHTML = '';

        if (props.streaming) {
            props.streaming.forEach(s => {
                const a = document.createElement('a');
                a.className = 'stream-btn';
                a.href = s.url;
                a.target = '_blank';
                a.textContent = `Watch on ${s.name}`;
                streamContainer.appendChild(a);
            });
        }

        modal.classList.remove('hidden');
        // Focus management
        const closeBtn = modal.querySelector('.close-modal');
        if (closeBtn) closeBtn.focus();
    }

    function setupModals() {
        // Close buttons
        document.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.classList.add('hidden');
                subscribeModal.classList.add('hidden');
            });
        });

        // Click outside
        window.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.add('hidden');
            if (e.target === subscribeModal) subscribeModal.classList.add('hidden');
        });

        // Subscribe button
        document.getElementById('subscribe-btn').addEventListener('click', () => {
            subscribeModal.classList.remove('hidden');
            const closeBtn = subscribeModal.querySelector('.close-modal');
            if (closeBtn) closeBtn.focus();
        });
    }
});
