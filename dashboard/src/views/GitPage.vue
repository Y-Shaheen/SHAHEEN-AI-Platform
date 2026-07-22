<template>
  <div class="git-page">
    <!-- Header -->
    <div class="git-header">
      <div>
        <h1 class="text-h2 mb-1">Git</h1>
        <p class="text-body-2 text-medium-emphasis mb-0">
          Repository management, commits, branches and diffs
        </p>
      </div>
      <div class="d-flex align-center gap-2">
        <v-btn
          variant="text"
          prepend-icon="mdi-refresh"
          :loading="refreshing"
          @click="refreshAll"
        >Refresh</v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          prepend-icon="mdi-source-repository"
          @click="cloneDialog = true"
        >Clone Repo</v-btn>
      </div>
    </div>

    <!-- Repo selector -->
    <v-card class="mb-4" variant="outlined">
      <v-card-text class="py-3">
        <div class="d-flex align-center gap-3 flex-wrap">
          <v-icon icon="mdi-folder-open-outline" />
          <v-select
            v-model="selectedRepo"
            :items="repos"
            item-title="name"
            item-value="path"
            label="Repository"
            hide-details
            density="compact"
            variant="outlined"
            style="max-width: 380px; min-width: 200px"
            @update:model-value="refreshAll"
          />
          <span v-if="currentBranch" class="d-flex align-center gap-1">
            <v-icon icon="mdi-source-branch" size="16" />
            <span class="text-body-2 font-weight-medium">{{ currentBranch }}</span>
            <v-chip v-if="statusData.ahead" size="x-small" color="success" class="ml-1">↑{{ statusData.ahead }}</v-chip>
            <v-chip v-if="statusData.behind" size="x-small" color="warning" class="ml-1">↓{{ statusData.behind }}</v-chip>
          </span>
          <v-spacer />
          <div class="d-flex gap-2">
            <v-btn size="small" variant="tonal" :loading="pulling" @click="doPull">
              <v-icon start>mdi-arrow-down</v-icon>Pull
            </v-btn>
            <v-btn size="small" variant="tonal" color="success" :loading="pushing" @click="doPush">
              <v-icon start>mdi-arrow-up</v-icon>Push
            </v-btn>
            <v-btn size="small" variant="tonal" color="info" :loading="fetching" @click="doFetch">
              <v-icon start>mdi-cloud-download-outline</v-icon>Fetch
            </v-btn>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Operation result snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="4000" location="top right">
      {{ snackbar.message }}
    </v-snackbar>

    <!-- Main tabs -->
    <v-card variant="outlined">
      <v-tabs v-model="activeTab" color="primary">
        <v-tab value="status">
          <v-icon start>mdi-pencil-outline</v-icon>
          Changes
          <v-badge v-if="changedFiles.length" :content="changedFiles.length" color="primary" class="ml-2" inline />
        </v-tab>
        <v-tab value="log">
          <v-icon start>mdi-history</v-icon>Log
        </v-tab>
        <v-tab value="branches">
          <v-icon start>mdi-source-branch</v-icon>Branches
        </v-tab>
        <v-tab value="diff">
          <v-icon start>mdi-compare</v-icon>Diff
        </v-tab>
        <v-tab value="remotes">
          <v-icon start>mdi-cloud-outline</v-icon>Remotes
        </v-tab>
      </v-tabs>

      <v-divider />

      <v-window v-model="activeTab">
        <!-- STATUS -->
        <v-window-item value="status">
          <div class="tab-content">
            <div v-if="loadingStatus" class="d-flex justify-center pa-8">
              <v-progress-circular indeterminate />
            </div>
            <div v-else-if="changedFiles.length === 0" class="d-flex flex-column align-center pa-10 text-medium-emphasis">
              <v-icon size="64" class="mb-3">mdi-check-circle-outline</v-icon>
              <p>Working tree is clean</p>
            </div>
            <div v-else>
              <!-- Conflict alert -->
              <v-alert v-if="conflicts.length" type="warning" variant="tonal" class="ma-4 mb-0" density="compact">
                {{ conflicts.length }} conflict(s) detected. Resolve before committing.
              </v-alert>

              <!-- File list -->
              <v-list lines="one" class="py-0">
                <v-list-item
                  v-for="file in changedFiles"
                  :key="file.path"
                  :class="['file-item', { 'file-selected': selectedFile === file.path }]"
                  @click="selectFile(file)"
                >
                  <template #prepend>
                    <v-chip
                      :color="fileStatusColor(file.xy)"
                      size="x-small"
                      class="mr-3 font-weight-bold"
                      style="min-width: 26px; justify-content: center;"
                    >{{ file.status || file.xy.trim() }}</v-chip>
                  </template>
                  <v-list-item-title class="text-body-2 font-weight-medium">{{ file.path }}</v-list-item-title>
                </v-list-item>
              </v-list>

              <!-- Commit area -->
              <v-divider />
              <div class="pa-4">
                <v-textarea
                  v-model="commitMessage"
                  label="Commit message"
                  variant="outlined"
                  rows="3"
                  hide-details
                  class="mb-3"
                  :placeholder="'feat: describe your changes'"
                />
                <div class="d-flex gap-2">
                  <v-btn
                    color="primary"
                    :loading="committing"
                    :disabled="!commitMessage.trim()"
                    @click="doCommit"
                  >
                    <v-icon start>mdi-check</v-icon>Commit All
                  </v-btn>
                  <v-btn variant="text" @click="refreshStatus">Refresh</v-btn>
                </div>
              </div>
            </div>
          </div>
        </v-window-item>

        <!-- LOG -->
        <v-window-item value="log">
          <div class="tab-content">
            <div v-if="loadingLog" class="d-flex justify-center pa-8">
              <v-progress-circular indeterminate />
            </div>
            <div v-else-if="commits.length === 0" class="d-flex flex-column align-center pa-10 text-medium-emphasis">
              <v-icon size="64" class="mb-3">mdi-git</v-icon>
              <p>No commits found</p>
            </div>
            <v-list v-else lines="two" class="py-0">
              <v-list-item
                v-for="commit in commits"
                :key="commit.hash"
                :class="['commit-item', { 'commit-selected': selectedCommit === commit.hash }]"
                @click="selectCommit(commit)"
              >
                <template #prepend>
                  <v-avatar size="32" color="primary" class="mr-1">
                    <span class="text-caption font-weight-bold">{{ commit.author_name[0]?.toUpperCase() }}</span>
                  </v-avatar>
                </template>
                <v-list-item-title class="text-body-2 font-weight-medium">{{ commit.message }}</v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  <span class="font-weight-medium text-primary">{{ commit.short_hash }}</span>
                  · {{ commit.author_name }} · {{ formatDate(commit.date) }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
            <!-- Commit detail -->
            <v-divider v-if="commitDetail" />
            <div v-if="commitDetail" class="pa-4">
              <div class="d-flex align-center mb-2">
                <span class="text-caption text-medium-emphasis">Commit diff</span>
                <v-spacer />
                <v-btn size="x-small" variant="text" icon="mdi-close" @click="commitDetail = ''" />
              </div>
              <pre class="diff-viewer">{{ commitDetail }}</pre>
            </div>
          </div>
        </v-window-item>

        <!-- BRANCHES -->
        <v-window-item value="branches">
          <div class="tab-content">
            <!-- New branch row -->
            <div class="d-flex align-center gap-2 pa-4 pb-0">
              <v-text-field
                v-model="newBranchName"
                label="New branch name"
                variant="outlined"
                density="compact"
                hide-details
                style="max-width: 300px"
                @keyup.enter="createBranch"
              />
              <v-btn
                color="primary"
                variant="tonal"
                :disabled="!newBranchName.trim()"
                :loading="creatingBranch"
                @click="createBranch"
              >Create</v-btn>
              <v-spacer />
              <v-btn variant="text" :loading="loadingBranches" @click="refreshBranches">
                <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </div>

            <div v-if="loadingBranches" class="d-flex justify-center pa-8">
              <v-progress-circular indeterminate />
            </div>
            <v-list v-else lines="one" class="py-2">
              <v-list-item
                v-for="branch in branches"
                :key="branch.name"
              >
                <template #prepend>
                  <v-icon :color="branch.current ? 'primary' : ''" size="20">
                    {{ branch.current ? 'mdi-source-branch-check' : 'mdi-source-branch' }}
                  </v-icon>
                </template>
                <v-list-item-title :class="branch.current ? 'text-primary font-weight-bold' : ''">
                  {{ branch.name }}
                  <v-chip v-if="branch.current" size="x-small" color="primary" class="ml-2">current</v-chip>
                </v-list-item-title>
                <v-list-item-subtitle v-if="branch.hash" class="text-caption">
                  {{ branch.hash }} {{ branch.message ? '· ' + branch.message : '' }}
                </v-list-item-subtitle>
                <template #append>
                  <div class="d-flex gap-1">
                    <v-btn
                      v-if="!branch.current"
                      size="x-small"
                      variant="tonal"
                      @click="checkoutBranch(branch.name)"
                    >Checkout</v-btn>
                    <v-btn
                      v-if="!branch.current"
                      size="x-small"
                      variant="text"
                      color="error"
                      icon="mdi-delete-outline"
                      @click="deleteBranch(branch.name)"
                    />
                  </div>
                </template>
              </v-list-item>
            </v-list>
          </div>
        </v-window-item>

        <!-- DIFF -->
        <v-window-item value="diff">
          <div class="tab-content">
            <div class="d-flex align-center gap-2 pa-4 pb-0">
              <v-text-field
                v-model="diffFile"
                label="File path (leave blank for full diff)"
                variant="outlined"
                density="compact"
                hide-details
                style="max-width: 380px"
              />
              <v-switch v-model="diffStaged" label="Staged" hide-details density="compact" inset color="primary" />
              <v-btn color="primary" variant="tonal" :loading="loadingDiff" @click="loadDiff">
                <v-icon start>mdi-compare</v-icon>View Diff
              </v-btn>
            </div>
            <div v-if="loadingDiff" class="d-flex justify-center pa-8">
              <v-progress-circular indeterminate />
            </div>
            <div v-else-if="diffContent" class="pa-4">
              <pre class="diff-viewer">{{ diffContent }}</pre>
            </div>
            <div v-else class="d-flex flex-column align-center pa-10 text-medium-emphasis">
              <v-icon size="64" class="mb-3">mdi-compare</v-icon>
              <p>Click "View Diff" to see changes</p>
            </div>
          </div>
        </v-window-item>

        <!-- REMOTES -->
        <v-window-item value="remotes">
          <div class="tab-content">
            <div v-if="loadingRemotes" class="d-flex justify-center pa-8">
              <v-progress-circular indeterminate />
            </div>
            <div v-else-if="remotes.length === 0" class="d-flex flex-column align-center pa-10 text-medium-emphasis">
              <v-icon size="64" class="mb-3">mdi-cloud-off-outline</v-icon>
              <p>No remotes configured</p>
            </div>
            <v-list v-else lines="one" class="py-2">
              <v-list-item v-for="remote in remotes" :key="remote.name">
                <template #prepend>
                  <v-icon>mdi-cloud-outline</v-icon>
                </template>
                <v-list-item-title class="font-weight-medium">{{ remote.name }}</v-list-item-title>
                <v-list-item-subtitle class="text-caption">{{ remote.url }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </div>
        </v-window-item>
      </v-window>
    </v-card>

    <!-- Clone dialog -->
    <v-dialog v-model="cloneDialog" max-width="480">
      <v-card>
        <v-card-title class="text-h3 pa-4 pb-0 pl-6">Clone Repository</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="cloneUrl"
            label="Repository URL"
            variant="outlined"
            placeholder="https://github.com/user/repo.git"
            class="mb-3"
          />
          <v-text-field
            v-model="clonePath"
            label="Destination path (optional)"
            variant="outlined"
            placeholder="Leave blank to use repo name"
          />
          <v-text-field
            v-model="cloneBranch"
            label="Branch (optional)"
            variant="outlined"
            placeholder="main"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cloneDialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="cloning" :disabled="!cloneUrl.trim()" @click="doClone">Clone</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { apiV1Client } from '@/api/http';

export default {
  name: 'GitPage',

  data() {
    return {
      // repo
      repos: [],
      selectedRepo: null,
      refreshing: false,

      // tabs
      activeTab: 'status',

      // status
      loadingStatus: false,
      statusData: { files: [], branch: '', ahead: 0, behind: 0 },
      commitMessage: '',
      committing: false,
      selectedFile: null,
      conflicts: [],

      // log
      loadingLog: false,
      commits: [],
      selectedCommit: null,
      commitDetail: '',

      // branches
      loadingBranches: false,
      branches: [],
      newBranchName: '',
      creatingBranch: false,

      // diff
      loadingDiff: false,
      diffContent: '',
      diffFile: '',
      diffStaged: false,

      // remotes
      loadingRemotes: false,
      remotes: [],

      // actions
      pulling: false,
      pushing: false,
      fetching: false,

      // clone dialog
      cloneDialog: false,
      cloneUrl: '',
      clonePath: '',
      cloneBranch: '',
      cloning: false,

      // snackbar
      snackbar: { show: false, message: '', color: 'success' },
    };
  },

  computed: {
    currentBranch() {
      return this.statusData.branch || '';
    },
    changedFiles() {
      return this.statusData.files || [];
    },
  },

  async mounted() {
    await this.loadRepos();
  },

  watch: {
    activeTab(tab) {
      if (tab === 'status') this.refreshStatus();
      else if (tab === 'log') this.refreshLog();
      else if (tab === 'branches') this.refreshBranches();
      else if (tab === 'remotes') this.refreshRemotes();
    },
  },

  methods: {
    // ── helpers ──────────────────────────────────────────────────────────────

    repoQuery() {
      return this.selectedRepo ? { params: { path: this.selectedRepo } } : {};
    },

    notify(message, color = 'success') {
      this.snackbar = { show: true, message, color };
    },

    formatDate(iso) {
      if (!iso) return '';
      try {
        const d = new Date(iso);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } catch {
        return iso;
      }
    },

    fileStatusColor(xy) {
      if (!xy) return 'grey';
      const s = xy.trim();
      if (s === 'M' || s === 'MM') return 'orange';
      if (s === 'A' || s === '??' ) return 'success';
      if (s === 'D') return 'error';
      if (s === 'R') return 'info';
      if (s === 'UU' || s === 'AA') return 'warning';
      return 'grey';
    },

    // ── data loading ─────────────────────────────────────────────────────────

    async loadRepos() {
      try {
        const res = await apiV1Client.get('/git/repos');
        this.repos = res.data?.data?.repos || [];
        if (this.repos.length && !this.selectedRepo) {
          this.selectedRepo = this.repos[0].path;
        }
        await this.refreshAll();
      } catch (e) {
        console.error('Failed to load repos', e);
      }
    },

    async refreshAll() {
      this.refreshing = true;
      try {
        await Promise.all([
          this.refreshStatus(),
          this.refreshLog(),
          this.refreshBranches(),
          this.refreshRemotes(),
        ]);
      } finally {
        this.refreshing = false;
      }
    },

    async refreshStatus() {
      this.loadingStatus = true;
      try {
        const res = await apiV1Client.get('/git/status', this.repoQuery());
        this.statusData = res.data?.data || {};
        // also check conflicts
        const c = await apiV1Client.get('/git/conflicts', this.repoQuery());
        this.conflicts = c.data?.data?.conflicts || [];
      } catch (e) {
        console.error(e);
      } finally {
        this.loadingStatus = false;
      }
    },

    async refreshLog() {
      this.loadingLog = true;
      try {
        const res = await apiV1Client.get('/git/log', this.repoQuery());
        this.commits = res.data?.data?.commits || [];
        this.commitDetail = '';
        this.selectedCommit = null;
      } catch (e) {
        console.error(e);
      } finally {
        this.loadingLog = false;
      }
    },

    async refreshBranches() {
      this.loadingBranches = true;
      try {
        const res = await apiV1Client.get('/git/branches', this.repoQuery());
        this.branches = res.data?.data?.branches || [];
      } catch (e) {
        console.error(e);
      } finally {
        this.loadingBranches = false;
      }
    },

    async refreshRemotes() {
      this.loadingRemotes = true;
      try {
        const res = await apiV1Client.get('/git/remotes', this.repoQuery());
        this.remotes = res.data?.data?.remotes || [];
      } catch (e) {
        console.error(e);
      } finally {
        this.loadingRemotes = false;
      }
    },

    async loadDiff() {
      this.loadingDiff = true;
      try {
        const params = { ...(this.selectedRepo ? { path: this.selectedRepo } : {}) };
        if (this.diffFile) params.file = this.diffFile;
        if (this.diffStaged) params.staged = true;
        const res = await apiV1Client.get('/git/diff', { params });
        this.diffContent = res.data?.data?.diff || '(no diff)';
      } catch (e) {
        this.diffContent = String(e?.response?.data?.message || e);
      } finally {
        this.loadingDiff = false;
      }
    },

    // ── actions ──────────────────────────────────────────────────────────────

    async selectFile(file) {
      this.selectedFile = file.path;
      this.diffFile = file.path;
      this.activeTab = 'diff';
      await this.loadDiff();
    },

    async selectCommit(commit) {
      this.selectedCommit = commit.hash;
      try {
        const params = { hash: commit.hash, ...(this.selectedRepo ? { path: this.selectedRepo } : {}) };
        const res = await apiV1Client.get('/git/show', { params });
        this.commitDetail = res.data?.data?.output || '';
      } catch (e) {
        this.commitDetail = String(e?.response?.data?.message || e);
      }
    },

    async doCommit() {
      if (!this.commitMessage.trim()) return;
      this.committing = true;
      try {
        await apiV1Client.post('/git/commit', { message: this.commitMessage }, this.repoQuery());
        this.notify('Committed successfully');
        this.commitMessage = '';
        await this.refreshStatus();
        await this.refreshLog();
      } catch (e) {
        this.notify(e?.response?.data?.message || 'Commit failed', 'error');
      } finally {
        this.committing = false;
      }
    },

    async doPull() {
      this.pulling = true;
      try {
        const res = await apiV1Client.post('/git/pull', { remote: 'origin' }, this.repoQuery());
        this.notify(res.data?.message || 'Pull completed');
        await this.refreshAll();
      } catch (e) {
        this.notify(e?.response?.data?.message || 'Pull failed', 'error');
      } finally {
        this.pulling = false;
      }
    },

    async doPush() {
      this.pushing = true;
      try {
        const res = await apiV1Client.post('/git/push', { remote: 'origin' }, this.repoQuery());
        this.notify(res.data?.message || 'Push completed');
        await this.refreshStatus();
      } catch (e) {
        this.notify(e?.response?.data?.message || 'Push failed', 'error');
      } finally {
        this.pushing = false;
      }
    },

    async doFetch() {
      this.fetching = true;
      try {
        const res = await apiV1Client.post('/git/fetch', { remote: 'origin' }, this.repoQuery());
        this.notify(res.data?.message || 'Fetch completed');
        await this.refreshStatus();
      } catch (e) {
        this.notify(e?.response?.data?.message || 'Fetch failed', 'error');
      } finally {
        this.fetching = false;
      }
    },

    async createBranch() {
      if (!this.newBranchName.trim()) return;
      this.creatingBranch = true;
      try {
        await apiV1Client.post('/git/branch', { name: this.newBranchName }, this.repoQuery());
        this.notify(`Branch created: ${this.newBranchName}`);
        this.newBranchName = '';
        await this.refreshBranches();
      } catch (e) {
        this.notify(e?.response?.data?.message || 'Create branch failed', 'error');
      } finally {
        this.creatingBranch = false;
      }
    },

    async checkoutBranch(name) {
      try {
        await apiV1Client.post('/git/checkout', { branch: name }, this.repoQuery());
        this.notify(`Checked out: ${name}`);
        await Promise.all([this.refreshBranches(), this.refreshStatus()]);
      } catch (e) {
        this.notify(e?.response?.data?.message || 'Checkout failed', 'error');
      }
    },

    async deleteBranch(name) {
      try {
        await apiV1Client.post('/git/branch', { name, delete: true }, this.repoQuery());
        this.notify(`Deleted branch: ${name}`);
        await this.refreshBranches();
      } catch (e) {
        this.notify(e?.response?.data?.message || 'Delete failed', 'error');
      }
    },

    async doClone() {
      this.cloning = true;
      try {
        const payload = { url: this.cloneUrl };
        if (this.clonePath) payload.path = this.clonePath;
        if (this.cloneBranch) payload.branch = this.cloneBranch;
        await apiV1Client.post('/git/clone', payload);
        this.notify('Clone completed');
        this.cloneDialog = false;
        this.cloneUrl = '';
        this.clonePath = '';
        this.cloneBranch = '';
        await this.loadRepos();
      } catch (e) {
        this.notify(e?.response?.data?.message || 'Clone failed', 'error');
      } finally {
        this.cloning = false;
      }
    },
  },
};
</script>

<style scoped>
.git-page {
  height: 100%;
  margin: 0 auto;
  max-width: 1400px;
  padding: 24px;
  width: 100%;
}

.git-header {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.tab-content {
  min-height: 360px;
  max-height: calc(100vh - 380px);
  overflow-y: auto;
}

.file-item {
  cursor: pointer;
  transition: background 0.15s;
}

.file-item:hover {
  background: rgba(var(--v-theme-primary), 0.06);
}

.file-selected {
  background: rgba(var(--v-theme-primary), 0.1);
}

.commit-item {
  cursor: pointer;
  transition: background 0.15s;
}

.commit-item:hover {
  background: rgba(var(--v-theme-primary), 0.06);
}

.commit-selected {
  background: rgba(var(--v-theme-primary), 0.1);
}

.diff-viewer {
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  max-height: calc(100vh - 500px);
  overflow: auto;
  padding: 12px 16px;
  white-space: pre;
  word-break: break-all;
}

:deep(.v-theme--dark) .diff-viewer {
  background: rgba(255, 255, 255, 0.06);
}

.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }

@media (max-width: 768px) {
  .git-page {
    padding: 16px;
  }
  .git-header {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
