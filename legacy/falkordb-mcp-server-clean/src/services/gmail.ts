import { google } from 'googleapis';

const oauth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET
);

oauth2Client.setCredentials({
    refresh_token: process.env.GOOGLE_REFRESH_TOKEN || null
});

const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

export async function sendEmail(to: string, subject: string, body: string) {
    const message = [
        `To: ${to}`,
        `Subject: ${subject}`,
        'Content-Type: text/html; charset=utf-8',
        '',
        body
    ].join('\n');

    const encodedMessage = Buffer.from(message)
        .toString('base64')
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');

    const res = await gmail.users.messages.send({
        userId: 'me',
        requestBody: {
            raw: encodedMessage
        }
    });

    return res.data;
}
