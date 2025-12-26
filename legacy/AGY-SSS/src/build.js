const fs = require('fs');
const path = require('path');
const ical = require('node-ical');
const { createEvents } = require('ics');
const { addDays, startOfWeek, addWeeks } = require('date-fns');

// Configuration
const SOURCES = [
    {
        id: '134920',
        name: 'Atlanta United',
        url: 'https://pub.fotmob.com/prod/pub/api/v2/calendar/team/773958.ics',
        category: 'Atlanta United',
        color: '#80000A',
        badge: '🔴'
    },
    {
        id: '133604',
        name: 'Arsenal',
        url: 'https://pub.fotmob.com/prod/pub/api/v2/calendar/team/9825.ics',
        category: 'Arsenal',
        color: '#EF0107',
        badge: '🔴'
    },
    {
        id: '135364',
        name: 'USA',
        url: 'https://pub.fotmob.com/prod/pub/api/v2/calendar/team/6637.ics',
        category: 'USMNT',
        color: '#002868',
        badge: '🇺🇸'
    }
];

const SHOWS = [
    {
        name: 'MLS 360',
        dayOfWeek: 6, // Saturday
        time: '19:30',
        duration: 240, // 4 hours
        platform: 'Apple TV+',
        category: 'Soccer Shows',
        color: '#4CAF50',
        badge: '📺'
    },
    {
        name: 'Goalazo',
        dayOfWeek: 2, // Tuesday
        time: '14:00',
        duration: 60,
        platform: 'Paramount+',
        category: 'Soccer Shows',
        color: '#4CAF50',
        badge: '📺'
    }
];

const OUTPUT_DIR = path.join(__dirname, '../public');
const ASSETS_DIR = path.join(OUTPUT_DIR, 'assets/team-logos');

// Helper: Ensure directories exist
if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });
if (!fs.existsSync(ASSETS_DIR)) fs.mkdirSync(ASSETS_DIR, { recursive: true });

function determineStreaming(summary, description) {
    const text = (summary + ' ' + description).toLowerCase();

    if (text.includes('mls') || text.includes('major league soccer')) return [{ name: 'Apple TV+', url: 'https://tv.apple.com/sports', icon: 'tv' }];
    if (text.includes('premier league')) return [{ name: 'Peacock', url: 'https://www.peacocktv.com/sports', icon: 'tv' }, { name: 'Fubo', url: 'https://www.fubo.tv', icon: 'tv' }];
    if (text.includes('champions league')) return [{ name: 'Paramount+', url: 'https://www.paramountplus.com', icon: 'tv' }];
    if (text.includes('usa') || text.includes('usmnt') || text.includes('friendlies')) return [{ name: 'Max / TNT', url: 'https://www.max.com', icon: 'tv' }, { name: 'Peacock', url: 'https://www.peacocktv.com', icon: 'tv' }];

    return [{ name: 'Check Listings', url: '#', icon: 'search' }];
}

function determineCategory(sourceCategory, summary) {
    // If it's a Champions League match, override category for filtering
    if (summary.toLowerCase().includes('champions league')) return 'Champions League';
    return sourceCategory;
}

async function fetchAndParseICS(source) {
    console.log(`Fetching schedule for ${source.name}...`);
    try {
        const events = await ical.async.fromURL(source.url);
        const parsedEvents = [];
        const now = new Date();
        now.setHours(0, 0, 0, 0); // Include today's events

        for (const k in events) {
            const ev = events[k];
            if (ev.type === 'VEVENT') {
                const start = new Date(ev.start);
                // Filter out past events (keep last 2 days just in case)
                if (start < new Date(now.getTime() - 86400000 * 2)) continue;
                // Filter out events too far in future (e.g. > 6 months)
                if (start > new Date(now.getTime() + 86400000 * 180)) continue;

                const streaming = determineStreaming(ev.summary, ev.description || '');
                const category = determineCategory(source.category, (ev.description || '') + ' ' + ev.summary);

                parsedEvents.push({
                    id: ev.uid || `${source.id}-${start.getTime()}`,
                    title: ev.summary.replace(' - ', ' vs '), // FotMob uses " - "
                    start: start,
                    end: new Date(ev.end),
                    location: ev.location || 'Unknown Venue',
                    description: ev.description || `Match involving ${source.name}`,
                    category: category,
                    color: source.color,
                    badge: source.badge,
                    league: ev.description ? ev.description.split('\n')[0] : 'Match', // FotMob puts league in description often
                    streaming: streaming,
                    teamId: source.id
                });
            }
        }
        return parsedEvents;
    } catch (error) {
        console.error(`Error fetching ${source.name}:`, error.message);
        return [];
    }
}

function generateShowEvents() {
    const events = [];
    const today = new Date();

    SHOWS.forEach(show => {
        // Generate for next 12 weeks
        let current = startOfWeek(today);
        // Advance to the correct day of week
        while (current.getDay() !== show.dayOfWeek) {
            current = addDays(current, 1);
        }
        if (current < today) current = addWeeks(current, 1);

        for (let i = 0; i < 12; i++) {
            const [hours, minutes] = show.time.split(':').map(Number);
            const start = new Date(current);
            start.setHours(hours, minutes, 0, 0);

            const end = new Date(start.getTime() + (show.duration * 60 * 1000));

            events.push({
                id: `show-${show.name}-${i}`,
                title: `${show.name}`,
                start: start,
                end: end,
                location: show.platform,
                description: `Watch ${show.name} on ${show.platform}`,
                category: show.category,
                color: show.color,
                badge: show.badge,
                league: 'TV Show',
                streaming: [{ name: show.platform, url: '#', icon: 'tv' }],
                isShow: true
            });

            current = addWeeks(current, 1);
        }
    });
    return events;
}

async function main() {
    console.log('Starting build...');

    let allEvents = [];

    // 1. Fetch Team Events from ICS
    for (const source of SOURCES) {
        const events = await fetchAndParseICS(source);
        allEvents = allEvents.concat(events);
    }

    // 2. Generate Shows
    const showEvents = generateShowEvents();
    allEvents = allEvents.concat(showEvents);

    // 3. Sort
    allEvents.sort((a, b) => a.start - b.start);

    // 4. Generate ICS Output
    const icsEvents = allEvents.map(e => {
        const start = [e.start.getFullYear(), e.start.getMonth() + 1, e.start.getDate(), e.start.getHours(), e.start.getMinutes()];
        const end = [e.end.getFullYear(), e.end.getMonth() + 1, e.end.getDate(), e.end.getHours(), e.end.getMinutes()];

        return {
            start,
            end,
            title: `${e.badge} ${e.title}`,
            description: e.description,
            location: e.location,
            url: 'https://sss.beltlineconsulting.co',
            categories: [e.category],
            status: 'CONFIRMED',
            busyStatus: 'BUSY'
        };
    });

    createEvents(icsEvents, (error, value) => {
        if (error) {
            console.error('Error generating ICS:', error);
            return;
        }
        fs.writeFileSync(path.join(OUTPUT_DIR, 'demestihas-soccer.ics'), value);
        console.log('ICS file generated.');
    });

    // 5. Generate JSON for Web UI
    const jsonEvents = allEvents.map(e => ({
        ...e,
        start: e.start.toISOString(),
        end: e.end.toISOString()
    }));

    const outputData = {
        lastUpdated: new Date().toISOString(),
        events: jsonEvents
    };

    fs.writeFileSync(path.join(OUTPUT_DIR, 'data.json'), JSON.stringify(outputData, null, 2));
    console.log('JSON data generated.');
}

main();
