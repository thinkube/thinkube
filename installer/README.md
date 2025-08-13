# thinkube Installer

A professional installer application for thinkube that configures inventory and triggers Ansible playbooks.

## Architecture

- **Frontend**: Vue.js 3 with Vuetify for Material Design UI
- **Backend**: FastAPI for handling configuration and Ansible execution
- **Desktop**: Electron for cross-platform desktop application
- **Platforms**: Ubuntu Linux (amd64 and arm64)

## Installation

Users can install thinkube with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/thinkube/thinkube/main/installer/scripts/install.sh | bash
```

## Project Structure

```
installer/
├── electron/       # Electron main process
├── frontend/       # Vue.js application
├── backend/        # FastAPI server
├── scripts/        # Installation and build scripts
└── build/          # Build outputs
```

## Development

### Prerequisites

- Node.js 18+
- Python 3.10+
- npm or yarn

### Setup

1. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Install backend dependencies:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Install Electron dependencies:
   ```bash
   cd electron
   npm install
   ```

### Running in Development

1. Start the FastAPI backend:
   ```bash
   cd backend
   python main.py
   ```

2. Start the Vue development server:
   ```bash
   cd frontend
   npm run dev
   ```

3. Start Electron:
   ```bash
   cd electron
   npm run dev
   ```

## Building

Build for both architectures:

```bash
npm run build:all
```

This creates:
- `dist/thinkube-installer_amd64.deb`
- `dist/thinkube-installer_arm64.deb`

## Features

- **Inventory Configuration**: Interactive forms for cluster setup
- **Validation**: Real-time validation of configuration
- **Progress Tracking**: Live progress of Ansible playbook execution
- **Error Handling**: Clear error messages and recovery options
- **Logs**: Detailed logs for troubleshooting

## License

Same as thinkube project - Apache-2.0