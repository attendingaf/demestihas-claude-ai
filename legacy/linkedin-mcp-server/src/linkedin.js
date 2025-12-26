const axios = require('axios');
const fs = require('fs');
const { saveToken, loadToken } = require('./token_store');

const LINKEDIN_API_URL = 'https://api.linkedin.com/v2';
const TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken';
const AUTH_URL = 'https://www.linkedin.com/oauth/v2/authorization';

class LinkedInClient {
    constructor() {
        this.clientId = process.env.LINKEDIN_CLIENT_ID;
        this.clientSecret = process.env.LINKEDIN_CLIENT_SECRET;
        this.redirectUri = process.env.LINKEDIN_REDIRECT_URI;
        this.tokenData = loadToken();
    }

    getAuthUrl() {
        const scope = 'w_member_social profile email openid'; // w_member_social is required for posting
        return `${AUTH_URL}?response_type=code&client_id=${this.clientId}&redirect_uri=${encodeURIComponent(this.redirectUri)}&scope=${encodeURIComponent(scope)}`;
    }

    async exchangeToken(code) {
        try {
            const params = new URLSearchParams();
            params.append('grant_type', 'authorization_code');
            params.append('code', code);
            params.append('redirect_uri', this.redirectUri);
            params.append('client_id', this.clientId);
            params.append('client_secret', this.clientSecret);

            const response = await axios.post(TOKEN_URL, params, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            this.tokenData = {
                access_token: response.data.access_token,
                expires_in: response.data.expires_in,
                created_at: Date.now()
            };
            saveToken(this.tokenData);

            // Fetch and save user URN immediately
            await this.getProfile();

            return this.tokenData;
        } catch (error) {
            console.error('Token exchange failed:', error.response?.data || error.message);
            throw error;
        }
    }

    async getHeaders() {
        if (!this.tokenData || !this.tokenData.access_token) {
            throw new Error('No access token found. Please authenticate first.');
        }
        return {
            'Authorization': `Bearer ${this.tokenData.access_token}`,
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json'
        };
    }

    async getProfile() {
        const headers = await this.getHeaders();
        try {
            const response = await axios.get(`${LINKEDIN_API_URL}/userinfo`, { headers });
            // userinfo returns 'sub' which is the ID. We need to construct the URN.
            // Actually, for ugcPosts, we need urn:li:person:{id}
            // The userinfo endpoint returns 'sub' as the ID.
            this.userUrn = `urn:li:person:${response.data.sub}`;
            // Save URN to token data for persistence
            this.tokenData.user_urn = this.userUrn;
            saveToken(this.tokenData);
            return response.data;
        } catch (error) {
            console.error('Get profile failed:', error.response?.data || error.message);
            throw error;
        }
    }

    async postText(text) {
        const headers = await this.getHeaders();
        const author = this.tokenData.user_urn || (await this.getProfile()).sub;

        const body = {
            author: author,
            lifecycleState: 'PUBLISHED',
            specificContent: {
                'com.linkedin.ugc.ShareContent': {
                    shareCommentary: { text: text },
                    shareMediaCategory: 'NONE'
                }
            },
            visibility: { 'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC' }
        };

        try {
            const response = await axios.post(`${LINKEDIN_API_URL}/ugcPosts`, body, { headers });
            return response.data;
        } catch (error) {
            console.error('Post text failed:', error.response?.data || error.message);
            throw error;
        }
    }

    async postArticle(text, url) {
        const headers = await this.getHeaders();
        const author = this.tokenData.user_urn || (await this.getProfile()).sub;

        const body = {
            author: author,
            lifecycleState: 'PUBLISHED',
            specificContent: {
                'com.linkedin.ugc.ShareContent': {
                    shareCommentary: { text: text },
                    shareMediaCategory: 'ARTICLE',
                    media: [
                        {
                            status: 'READY',
                            description: { text: 'Article' },
                            originalUrl: url
                        }
                    ]
                }
            },
            visibility: { 'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC' }
        };

        try {
            const response = await axios.post(`${LINKEDIN_API_URL}/ugcPosts`, body, { headers });
            return response.data;
        } catch (error) {
            console.error('Post article failed:', error.response?.data || error.message);
            throw error;
        }
    }

    async postImage(text, imagePath) {
        const headers = await this.getHeaders();
        const author = this.tokenData.user_urn || (await this.getProfile()).sub;

        // Step 1: Register Upload
        const registerBody = {
            registerUploadRequest: {
                recipes: ['urn:li:digitalmediaRecipe:feedshare-image'],
                owner: author,
                serviceRelationships: [
                    {
                        relationshipType: 'OWNER',
                        identifier: 'urn:li:userGeneratedContent'
                    }
                ]
            }
        };

        let uploadUrl, asset;
        try {
            const registerResponse = await axios.post(`${LINKEDIN_API_URL}/assets?action=registerUpload`, registerBody, { headers });
            uploadUrl = registerResponse.data.value.uploadMechanism['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest'].uploadUrl;
            asset = registerResponse.data.value.asset;
        } catch (error) {
            console.error('Register upload failed:', error.response?.data || error.message);
            throw error;
        }

        // Step 2: Upload Image
        try {
            const imageBuffer = fs.readFileSync(imagePath);
            await axios.put(uploadUrl, imageBuffer, {
                headers: { 'Content-Type': 'application/octet-stream', 'Authorization': `Bearer ${this.tokenData.access_token}` }
            });
        } catch (error) {
            console.error('Image upload failed:', error.response?.data || error.message);
            throw error;
        }

        // Step 3: Create Post
        const body = {
            author: author,
            lifecycleState: 'PUBLISHED',
            specificContent: {
                'com.linkedin.ugc.ShareContent': {
                    shareCommentary: { text: text },
                    shareMediaCategory: 'IMAGE',
                    media: [
                        {
                            status: 'READY',
                            description: { text: 'Image' },
                            media: asset,
                            title: { text: 'Image' }
                        }
                    ]
                }
            },
            visibility: { 'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC' }
        };

        try {
            const response = await axios.post(`${LINKEDIN_API_URL}/ugcPosts`, body, { headers });
            return response.data;
        } catch (error) {
            console.error('Create image post failed:', error.response?.data || error.message);
            throw error;
        }
    }
}

module.exports = new LinkedInClient();
