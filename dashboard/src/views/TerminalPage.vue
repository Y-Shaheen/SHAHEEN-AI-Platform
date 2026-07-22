<template>
  <div class="terminal-page">
    <!-- Header -->
    <div class="terminal-header">
      <div>
        <h1 class="text-h2 mb-1">Terminal</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Interactive shell · working directory:
          <span class="terminal-cwd">{{ cwd || '…' }}</span>
        </p>
      </div>
      <div class="d-flex align-center gap-2">
        <v-chip
          :color="wsStatus === 'connected' ? 'success' : wsStatus === 'connecting' ? 'warning' : 'error'"
          size="small"
          variant="tonal"
        >
          <v-icon start size="14">mdi-circle</v-icon>
          {{ wsStatus }}
        </v-chip>
        <v-btn variant="text" size="small" icon="mdi-delete-sweep-outline" @click="clearOutput" title="Clear" />
        <v-btn variant="text" size="small" icon="mdi-refresh" @click="reconnect" title="Reconnect" />
        <v-btn
          v-if="running"
          color="error"
          variant="tonal"
          size="small"
          @click="killProcess"
        >
          <v-icon start>mdi-stop</v-icon>Kill
        </v-btn>
      </div>
    </div>

    <!-- Terminal output -->
    <div
      ref="outputEl"
      class="terminal-output"
      :class="{ 'is-dark': isDark }"
      @click="focusInput"
    >
      <div v-for="(line, idx) in outputLines" :key="idx" :class="['terminal-line', line.type]">
        <span v-if="line.type === 'cmd'" class="terminal-prompt">{{ line.prompt }}</span>
        <span class="terminal-text" v-html="ansiToHtml(line.text)" />
      </div>
      <div v-if="running" class="terminal-line">
        <span class="terminal-cursor blink">█</span>
      </div>
    </div>

    <!-- Input row -->
    <div class="terminal-input-row" :class="{ 'is-dark': isDark }">
      <span class="terminal-prompt-label">{{ promptLabel }}</span>
      <input
        ref="inputEl"
        v-model="currentInput"
        class="terminal-input"
        :disabled="running || wsStatus !== 'connected'"
        :placeholder="wsStatus !== 'connected' ? 'Connecting…' : ''"
        spellcheck="false"
        autocomplete="off"
        autocorrect="off"
        autocapitalize="off"
        @keydown.enter="sendCommand"
        @keydown.up.prevent="historyUp"
        @keydown.down.prevent="historyDown"
        @keydown.c.ctrl.prevent="killProcess"
        @keydown.l.ctrl.prevent="clearOutput"
      />
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';
import { useTheme } from 'vuetify';

const MAX_LINES = 2000;

// Minimal ANSI-to-HTML converter (handles common colour/style codes)
function ansiToHtml(text) {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const colorMap = {
    30: '#3d3d3d', 31: '#e06c75', 32: '#98c379', 33: '#e5c07b',
    34: '#61afef', 35: '#c678dd', 36: '#56b6c2', 37: '#abb2bf',
    90: '#7f848e', 91: '#e06c75', 92: '#98c379', 93: '#e5c07b',
    94: '#61afef', 95: '#c678dd', 96: '#56b6c2', 97: '#ffffff',
  };

  return escaped.replace(
    // eslint-disable-next-line no-control-regex
    /\x1B\[([0-9;]*)m/g,
    (_, codes) => {
      if (!codes || codes === '0') return '</span><span>';
      const parts = codes.split(';').map(Number);
      let style = '';
      for (const code of parts) {
        if (code === 1) style += 'font-weight:bold;';
        else if (code === 3) style += 'font-style:italic;';
        else if (code === 4) style += 'text-decoration:underline;';
        else if (colorMap[code]) style += `color:${colorMap[code]};`;
        else if (code >= 40 && code <= 47) {
          const bg = colorMap[code - 10];
          if (bg) style += `background:${bg};`;
        }
      }
      return style ? `</span><span style="${style}">` : '</span><span>';
    },
  );
}

export default {
  name: 'TerminalPage',

  setup() {
    const theme = useTheme();
    const isDark = computed(() => theme.global.current.value.dark);
    return { isDark };
  },

  data() {
    return {
      outputLines: [],
      currentInput: '',
      history: [],
      historyIndex: -1,

      cwd: '',
      running: false,
      wsStatus: 'disconnected', // connecting | connected | disconnected | error

      ws: null,
      pingInterval: null,
    };
  },

  computed: {
    promptLabel() {
      const dir = this.cwd ? this.cwd.split('/').pop() || this.cwd : '~';
      return `${dir} $ `;
    },
  },

  mounted() {
    this.connect();
  },

  beforeUnmount() {
    this.disconnect();
  },

  methods: {
    ansiToHtml,

    // ── WebSocket ─────────────────────────────────────────────────────────────

    connect() {
      this.wsStatus = 'connecting';
      const token = localStorage.getItem('token') || '';
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${proto}://${location.host}/api/v1/terminal/ws?token=${encodeURIComponent(token)}`;

      try {
        this.ws = new WebSocket(url);
      } catch (e) {
        this.wsStatus = 'error';
        this.pushLine('error', `WebSocket error: ${e}`);
        return;
      }

      this.ws.onopen = () => {
        // ping every 25 s to keep alive
        this.pingInterval = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      this.ws.onmessage = (ev) => {
        let msg;
        try { msg = JSON.parse(ev.data); } catch { return; }
        this.handleMessage(msg);
      };

      this.ws.onclose = () => {
        this.wsStatus = 'disconnected';
        this.running = false;
        clearInterval(this.pingInterval);
        this.pushLine('info', '[Connection closed]');
      };

      this.ws.onerror = () => {
        this.wsStatus = 'error';
        this.running = false;
        this.pushLine('error', '[WebSocket error]');
      };
    },

    disconnect() {
      clearInterval(this.pingInterval);
      if (this.ws) {
        try { this.ws.send(JSON.stringify({ type: 'close' })); } catch { /* ignore */ }
        this.ws.close();
        this.ws = null;
      }
    },

    reconnect() {
      this.disconnect();
      this.outputLines = [];
      setTimeout(() => this.connect(), 300);
    },

    handleMessage(msg) {
      switch (msg.type) {
        case 'ready':
          this.wsStatus = 'connected';
          this.cwd = msg.cwd || '';
          this.pushLine('info', `Connected · ${this.cwd}`);
          this.$nextTick(() => this.focusInput());
          break;

        case 'output':
          this.appendOutput(msg.data || '', msg.stream);
          break;

        case 'done':
          this.running = false;
          if (msg.cwd) this.cwd = msg.cwd;
          if (msg.exit_code !== 0 && msg.exit_code != null) {
            this.pushLine('info', `[exited ${msg.exit_code}]`);
          }
          this.$nextTick(() => this.focusInput());
          break;

        case 'cwd':
          this.cwd = msg.cwd || this.cwd;
          break;

        case 'killed':
          this.running = false;
          this.pushLine('info', '[process killed]');
          this.$nextTick(() => this.focusInput());
          break;

        case 'error':
          this.running = false;
          this.pushLine('error', `Error: ${msg.data}`);
          break;

        case 'pong':
          break;

        default:
          break;
      }
    },

    // ── Output management ────────────────────────────────────────────────────

    pushLine(type, text) {
      this.outputLines.push({ type, text, prompt: '' });
      if (this.outputLines.length > MAX_LINES) {
        this.outputLines.splice(0, this.outputLines.length - MAX_LINES);
      }
      this.$nextTick(() => this.scrollBottom());
    },

    appendOutput(raw, stream) {
      // Split on newlines but keep them attached so partial lines are shown
      const parts = raw.split(/(\n)/);
      let fragment = '';
      for (const part of parts) {
        if (part === '\n') {
          this.pushLine(stream === 'stderr' ? 'stderr' : 'stdout', fragment);
          fragment = '';
        } else {
          fragment += part;
        }
      }
      if (fragment) {
        this.pushLine(stream === 'stderr' ? 'stderr' : 'stdout', fragment);
      }
    },

    clearOutput() {
      this.outputLines = [];
    },

    scrollBottom() {
      const el = this.$refs.outputEl;
      if (el) el.scrollTop = el.scrollHeight;
    },

    focusInput() {
      this.$refs.inputEl?.focus();
    },

    // ── Command handling ──────────────────────────────────────────────────────

    sendCommand() {
      const cmd = this.currentInput.trim();
      if (!cmd || this.running || this.wsStatus !== 'connected') return;

      // Show command in output
      this.outputLines.push({
        type: 'cmd',
        text: cmd,
        prompt: this.promptLabel,
      });
      this.scrollBottom();

      // History
      if (this.history[this.history.length - 1] !== cmd) {
        this.history.push(cmd);
      }
      this.historyIndex = -1;
      this.currentInput = '';

      this.running = true;
      this.ws.send(JSON.stringify({ type: 'exec', command: cmd, cwd: this.cwd }));
    },

    killProcess() {
      if (this.running && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'kill' }));
      }
    },

    historyUp() {
      if (this.history.length === 0) return;
      if (this.historyIndex === -1) {
        this.historyIndex = this.history.length - 1;
      } else if (this.historyIndex > 0) {
        this.historyIndex--;
      }
      this.currentInput = this.history[this.historyIndex] || '';
    },

    historyDown() {
      if (this.historyIndex === -1) return;
      this.historyIndex++;
      if (this.historyIndex >= this.history.length) {
        this.historyIndex = -1;
        this.currentInput = '';
      } else {
        this.currentInput = this.history[this.historyIndex];
      }
    },
  },
};
</script>

<style scoped>
.terminal-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  margin: 0 auto;
  max-width: 1400px;
  padding: 24px;
  width: 100%;
}

.terminal-header {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.terminal-cwd {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  opacity: 0.85;
}

.terminal-output {
  background: #1a1a2e;
  border-radius: 10px 10px 0 0;
  color: #c9d1d9;
  cursor: text;
  flex: 1;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 13px;
  line-height: 1.6;
  min-height: 200px;
  overflow-y: auto;
  padding: 16px;
}

.terminal-output.is-dark {
  background: #0d0d1a;
}

.terminal-line {
  display: flex;
  white-space: pre-wrap;
  word-break: break-all;
}

.terminal-line.cmd .terminal-text {
  color: #79c0ff;
  font-weight: 600;
}

.terminal-line.stderr .terminal-text {
  color: #ff7b72;
}

.terminal-line.error .terminal-text {
  color: #ff7b72;
  font-style: italic;
}

.terminal-line.info .terminal-text {
  color: #8b949e;
  font-style: italic;
}

.terminal-prompt {
  color: #3fb950;
  flex-shrink: 0;
  margin-right: 4px;
  user-select: none;
}

.terminal-cursor {
  color: #79c0ff;
}

.blink {
  animation: cursor-blink 1s step-start infinite;
}

@keyframes cursor-blink {
  50% { opacity: 0; }
}

.terminal-input-row {
  align-items: center;
  background: #1a1a2e;
  border-radius: 0 0 10px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-shrink: 0;
  padding: 8px 16px;
}

.terminal-input-row.is-dark {
  background: #0d0d1a;
}

.terminal-prompt-label {
  color: #3fb950;
  flex-shrink: 0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  margin-right: 6px;
  user-select: none;
}

.terminal-input {
  background: transparent;
  border: none;
  caret-color: #79c0ff;
  color: #c9d1d9;
  flex: 1;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  outline: none;
  width: 100%;
}

.terminal-input::placeholder {
  color: #8b949e;
}

.terminal-input:disabled {
  opacity: 0.5;
}

.gap-2 { gap: 8px; }

@media (max-width: 768px) {
  .terminal-page {
    padding: 12px;
  }
  .terminal-header {
    flex-direction: column;
    gap: 10px;
  }
}
</style>
