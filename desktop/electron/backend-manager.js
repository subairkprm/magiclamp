const { spawn } = require('child_process')
const path = require('path')
const { app } = require('electron')

let backendProcess = null
let backendStatus = 'stopped'

function getBrainPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'brain')
  }
  return path.join(__dirname, '..', '..', 'brain')
}

function getPythonCmd() {
  return process.platform === 'win32' ? 'python' : 'python3'
}

function startBackend() {
  if (backendProcess) return

  const brainPath = getBrainPath()
  const python = getPythonCmd()

  console.log('[Backend] Starting uvicorn from:', brainPath)
  backendStatus = 'starting'

  backendProcess = spawn(
    python,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '9000', '--workers', '1'],
    {
      cwd: brainPath,
      env: { ...process.env },
      stdio: ['ignore', 'pipe', 'pipe'],
    }
  )

  backendProcess.stdout.on('data', (data) => {
    const msg = data.toString().trim()
    console.log('[Brain]', msg)
    if (msg.includes('Application startup complete') || msg.includes('Uvicorn running')) {
      backendStatus = 'running'
    }
  })

  backendProcess.stderr.on('data', (data) => {
    const msg = data.toString().trim()
    // uvicorn logs to stderr by default
    console.log('[Brain]', msg)
    if (msg.includes('Application startup complete') || msg.includes('Uvicorn running')) {
      backendStatus = 'running'
    }
    if (msg.includes('error') || msg.includes('Error')) {
      console.error('[Brain ERROR]', msg)
    }
  })

  backendProcess.on('exit', (code) => {
    console.log('[Backend] Process exited with code:', code)
    backendProcess = null
    backendStatus = 'stopped'
  })

  backendProcess.on('error', (err) => {
    console.error('[Backend] Failed to start:', err.message)
    backendStatus = 'error'
  })
}

function stopBackend() {
  if (!backendProcess) return
  console.log('[Backend] Stopping...')
  backendProcess.kill('SIGTERM')
  backendProcess = null
  backendStatus = 'stopped'
}

function getStatus() {
  return backendStatus
}

module.exports = { startBackend, stopBackend, getStatus }
