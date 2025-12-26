import { google } from 'googleapis';

const oauth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET
);

oauth2Client.setCredentials({
    refresh_token: process.env.GOOGLE_REFRESH_TOKEN || null
});

const calendar = google.calendar({ version: 'v3', auth: oauth2Client });

export async function getTodayEvents() {
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);

    const res = await calendar.events.list({
        calendarId: 'primary',
        timeMin: startOfDay.toISOString(),
        timeMax: endOfDay.toISOString(),
        singleEvents: true,
        orderBy: 'startTime'
    });

    return res.data.items || [];
}

export async function getEventsInRange(timeMin: string, timeMax: string) {
    const res = await calendar.events.list({
        calendarId: 'primary',
        timeMin,
        timeMax,
        singleEvents: true,
        orderBy: 'startTime'
    });

    return res.data.items || [];
}
