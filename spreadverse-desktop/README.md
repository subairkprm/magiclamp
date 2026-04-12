# 🚀 SpreadVerse Admin Hub

**Multi-tenant Enterprise CRM Desktop Application**

A secure, blazing-fast desktop application built with Tauri, React, TypeScript, and Tailwind CSS for managing the SpreadVerse CRM platform.

---

## 📋 Overview

SpreadVerse Admin Hub is a cross-platform desktop application that provides a modern, secure interface for managing multi-tenant enterprise CRM operations. Built with cutting-edge technologies, it offers:

- 🔐 **Secure Authentication**: JWT-based authentication with automatic token refresh
- ⚡ **Lightning Fast**: Powered by Tauri for native performance
- 🎨 **Modern UI**: Beautiful interface built with React and Tailwind CSS
- 🔒 **Type-Safe**: Full TypeScript support for reliability
- 📱 **Cross-Platform**: Runs on Windows, macOS, and Linux

---

## 🏗️ Tech Stack

- **Tauri 1.5+**: Native desktop framework
- **React 18+**: Modern UI library
- **TypeScript 5+**: Type-safe development
- **Tailwind CSS 3+**: Utility-first CSS framework
- **Vite 5+**: Fast build tool
- **Axios**: HTTP client with interceptors
- **React Router 6+**: Client-side routing

---

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** 18+ and npm 9+
- **Rust** 1.70+ (for Tauri)
- **System Dependencies** for Tauri:
  - **Linux**: `sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev`
  - **macOS**: Xcode Command Line Tools
  - **Windows**: Microsoft Visual Studio C++ Build Tools

---

## 🚀 Installation

### 1. Clone or Navigate to Project

```bash
cd spreadverse-desktop
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and update the API URL:

```env
VITE_API_URL=https://your-backend-url.com/api/v1
```

Replace `https://your-backend-url.com` with your actual MagicLamp backend URL.

---

## 💻 Development

### Run in Development Mode

```bash
# Start the development server (web view)
npm run dev

# Or start Tauri development (desktop app)
npm run tauri:dev
```

The application will open in a desktop window with hot-reload enabled.

### Build for Production

```bash
# Build the web assets
npm run build

# Build the desktop application
npm run tauri:build
```

The built application will be in `src-tauri/target/release/`.

---

## 📁 Project Structure

```
spreadverse-desktop/
├── src/
│   ├── api/
│   │   └── client.ts           # API client with JWT handling
│   ├── pages/
│   │   ├── Login.tsx           # Login page component
│   │   └── Dashboard.tsx       # Main dashboard component
│   ├── components/             # Reusable UI components
│   ├── types/                  # TypeScript type definitions
│   ├── utils/                  # Utility functions
│   ├── App.tsx                 # Main application component
│   ├── main.tsx                # Application entry point
│   └── index.css               # Global styles with Tailwind
├── src-tauri/
│   ├── src/
│   │   └── main.rs             # Tauri backend (Rust)
│   ├── Cargo.toml              # Rust dependencies
│   └── tauri.conf.json         # Tauri configuration
├── index.html                  # HTML entry point
├── vite.config.ts              # Vite configuration
├── tailwind.config.js          # Tailwind CSS configuration
├── tsconfig.json               # TypeScript configuration
└── package.json                # Node dependencies
```

---

## 🔌 API Integration

### API Client (`src/api/client.ts`)

The API client automatically handles:

1. **Base URL Configuration**: Reads from `VITE_API_URL` environment variable
2. **Token Management**: Stores JWT tokens in `localStorage`
3. **Request Interceptor**: Automatically attaches `Authorization: Bearer <token>` header
4. **Response Interceptor**: Handles token expiration and automatic refresh
5. **Error Handling**: Redirects to login on authentication failures

### Usage Example

```typescript
import api from './api/client';

// Make authenticated requests
const response = await api.get('/brain/memory/stats');
const data = await api.post('/brain/reason/ask', { question: 'How are you?' });
```

### Token Storage

- **Access Token**: `localStorage.getItem('spreadverse_access_token')`
- **Refresh Token**: `localStorage.getItem('spreadverse_refresh_token')`

---

## 🔐 Authentication Flow

1. User enters email/password on Login page
2. POST request to `/auth/login` endpoint
3. Backend returns `access_token` and `refresh_token`
4. Tokens saved to `localStorage`
5. User redirected to Dashboard
6. All subsequent requests include `Authorization` header
7. On token expiration (401), client automatically refreshes token

---

## 🎨 UI Components

### Login Page

- Email/password form with validation
- Loading states and error handling
- Responsive design
- Gradient background with modern card design

### Dashboard

- Collapsible sidebar navigation
- Stats cards with metrics
- Protected route (requires authentication)
- Logout functionality

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file with these variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | ✅ | `https://YOUR_REPLIT_URL_HERE/api/v1` | Backend API base URL |

### Tauri Configuration

Edit `src-tauri/tauri.conf.json` to customize:

- Window size and behavior
- Application name and version
- Security policies
- Build targets

---

## 🛠️ Scripts

```bash
# Development
npm run dev              # Start Vite dev server (web)
npm run tauri:dev        # Start Tauri desktop app

# Building
npm run build            # Build web assets
npm run tauri:build      # Build desktop application

# Preview
npm run preview          # Preview production build
```

---

## 🚢 Deployment

### Desktop Application

The `tauri:build` command creates platform-specific installers:

- **Windows**: `.exe` installer
- **macOS**: `.dmg` installer and `.app` bundle
- **Linux**: `.deb` and `.AppImage` packages

### Web Version

You can also deploy as a web application:

```bash
npm run build
# Deploy the 'dist' folder to your hosting provider
```

---

## 🔒 Security Best Practices

1. **Never commit `.env` files**: Keep sensitive data out of version control
2. **Use HTTPS**: Always connect to backend over HTTPS in production
3. **Token Rotation**: Implement refresh token rotation on the backend
4. **Input Validation**: All forms use proper validation
5. **XSS Protection**: React's JSX automatically escapes content

---

## 🧪 Testing

```bash
# Run tests (add test framework of your choice)
npm test

# Type checking
npm run build
```

---

## 📚 Additional Resources

- [Tauri Documentation](https://tauri.app/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [TypeScript Documentation](https://www.typescriptlang.org/)
- [Vite Documentation](https://vitejs.dev/)

---

## 🐛 Troubleshooting

### Build Errors

If you encounter build errors:

1. Clear node_modules: `rm -rf node_modules && npm install`
2. Clear Tauri cache: `cd src-tauri && cargo clean`
3. Ensure Rust is up to date: `rustup update`

### API Connection Issues

If API requests fail:

1. Check `.env` file has correct `VITE_API_URL`
2. Verify backend is running and accessible
3. Check browser console for CORS errors
4. Verify JWT tokens in localStorage

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Built with ❤️ for SpreadVerse Enterprise CRM**
