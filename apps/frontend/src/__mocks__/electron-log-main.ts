/**
 * Mock for electron-log/main.js
 *
 * Prevents CI failures caused by electron-log requiring the electron binary
 * (which is not installed in CI when --ignore-scripts is used).
 */

const mockLog = {
  initialize: () => {
    // Mock initialize function - no implementation needed
  },
  transports: {
    file: {
      maxSize: 10 * 1024 * 1024,
      format: '',
      fileName: 'main.log',
      level: 'info' as const,
      getFile: () => ({ path: '/tmp/test.log' })
    },
    console: {
      level: 'warn' as const,
      format: ''
    }
  },
  debug: (..._args: unknown[]) => {
    // Mock debug function - no logging in tests
  },
  info: (..._args: unknown[]) => {
    // Mock info function - no logging in tests
  },
  warn: (..._args: unknown[]) => {
    // Mock warn function - no logging in tests
  },
  error: (..._args: unknown[]) => {
    // Mock error function - no logging in tests
  },
  silly: (..._args: unknown[]) => {
    // Mock silly function - no logging in tests
  },
  verbose: (..._args: unknown[]) => {
    // Mock verbose function - no logging in tests
  }
};

export default mockLog;
