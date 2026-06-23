<template>
  <div class="app-container" :class="{ 'light-theme': isLightTheme }">
    <!-- Header -->
    <header class="app-header">
      <div class="logo-area">
        <div class="logo-icon">G</div>
        <div class="logo-text">
          <h1>GICS 行业星图与 AI 协同分析大屏</h1>
          <p>Global Industry Classification Standard & AI Agent Console</p>
        </div>
      </div>
      
      <!-- Global Search & Register Action -->
      <div class="header-actions">
        <!-- Theme Toggle Button -->
        <button class="theme-toggle-btn" @click="toggleTheme" :title="isLightTheme ? '切换至暗黑模式' : '切换至明亮模式'">
          <svg v-if="isLightTheme" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="theme-icon">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="theme-icon">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
        </button>

        <div class="search-box">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="搜索股票代码、名称或行业 (如: AAPL)" 
            @input="handleSearch"
          />
          <button v-if="searchQuery" @click="clearSearch" class="clear-btn">&times;</button>
        </div>
        
        <button class="primary-btn btn-glow" @click="openRegisterDrawer()">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          登记个股映射
        </button>
      </div>
    </header>

    <!-- AI Task Progress Banner -->
    <section v-if="progress" class="progress-banner">
      <div class="progress-info">
        <div class="progress-title">
          <span class="pulse-dot" :class="{ 'inactive': progress.processing_count === 0 }"></span>
          <span><strong>AI 通宵跑批分析控制台</strong></span>
          <span v-if="progress.processing_count > 0" class="current-task-name">
            (正在分析: {{ progress.processing.map(p => p.ticker).join(', ') }})
          </span>
          <span v-else class="current-task-name">(分析任务空闲中)</span>
        </div>
        <div class="progress-stats">
          <span>总股数: <strong>{{ progress.total }}</strong></span>
          <span class="text-success">已分析: <strong>{{ progress.completed_count }}</strong></span>
          <span class="text-primary">分析中: <strong>{{ progress.processing_count }}</strong></span>
          <span class="text-warning">待分析: <strong>{{ progress.pending_count }}</strong></span>
        </div>
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar-fill" :style="{ width: progressPercentage + '%' }"></div>
        <span class="progress-percentage">{{ progressPercentage }}%</span>
      </div>
      <button class="icon-btn-sync" @click="fetchData" title="刷新进度">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="sync-icon">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
      </button>
    </section>

    <!-- Main Workspace -->
    <main class="workspace">
      <!-- Left Panel: Companies List -->
      <aside class="sidebar-panel">
        <div class="panel-header">
          <h2>已登记公司 ({{ companies.length }})</h2>
        </div>
        <div class="sidebar-list">
          <div 
            v-for="company in filteredCompanies" 
            :key="company.ticker"
            class="company-card"
            :class="{ 
              'highlighted': activeCompanyTicker === company.ticker,
              'has-report': company.report_status === 'completed' 
            }"
            @click="locateCompanyInTree(company)"
          >
            <div class="company-card-top">
              <span class="ticker-badge">{{ company.ticker }}</span>
              <div class="card-actions">
                <!-- Report button if completed -->
                <button 
                  v-if="company.report_status === 'completed'" 
                  class="action-icon-btn report-active-btn" 
                  @click.stop="openReportPanel(company.ticker)"
                  title="查看八维行研报告"
                >
                  📄 研报
                </button>
                <button class="delete-btn" @click.stop="confirmDeleteCompany(company.ticker)" title="删除个股">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                </button>
              </div>
            </div>
            <h3>{{ company.name }}</h3>
            <p v-if="company.description" class="comp-desc">{{ company.description }}</p>
            <div class="comp-industry-tag">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              <span>{{ company.industry_name_zh || company.industry_name_en || '未分配子行业' }}</span>
            </div>
          </div>
          
          <div v-if="filteredCompanies.length === 0" class="empty-state">
            <p>没有找到匹配的公司</p>
          </div>
        </div>
      </aside>

      <!-- Right Panel: Interactive GICS Tree -->
      <section class="tree-panel">
        <div class="panel-header">
          <h2>GICS 行业分类树 ({{ flatCategoriesCount }} 个分级节点)</h2>
          <div class="tree-controls">
            <button class="text-btn" @click="expandAllSectors">全部展开</button>
            <span class="divider">|</span>
            <button class="text-btn" @click="collapseAllSectors">全部折叠</button>
          </div>
        </div>

        <div class="tree-viewport">
          <div v-if="loading" class="loading-state">
            <div class="spinner"></div>
            <p>正在读取 GICS 数据库...</p>
          </div>
          
          <div v-else class="sectors-grid">
            <!-- Sector Level (Level 1 Card) -->
            <div 
              v-for="sector in gicsTree" 
              :key="sector.code" 
              class="sector-card"
              :class="{ 'expanded': isExpanded(sector.code), 'has-highlight': sectorHasHighlight(sector) }"
              :id="'node-' + sector.code"
            >
              <div class="sector-card-header" @click="toggleExpand(sector.code)">
                <div class="sector-info">
                  <span class="sector-code">{{ sector.code }}</span>
                  <div class="sector-titles">
                    <h3>{{ sector.name_zh }}</h3>
                    <span>{{ sector.name_en }}</span>
                  </div>
                </div>
                <div class="sector-meta">
                  <span class="count-badge" :class="{ 'has-companies': sector.company_count > 0 }">
                    {{ sector.company_count }} 家公司
                  </span>
                  <svg class="chevron-icon" :class="{ 'rotate': isExpanded(sector.code) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </div>
              </div>

              <!-- Level 2: Industry Groups -->
              <div v-if="isExpanded(sector.code)" class="sector-card-body">
                <div 
                  v-for="group in sector.children" 
                  :key="group.code" 
                  class="group-node"
                  :class="{ 'has-highlight': sectorHasHighlight(group) }"
                  :id="'node-' + group.code"
                >
                  <div class="group-header" @click="toggleExpand(group.code)">
                    <svg class="fold-icon" :class="{ 'open': isExpanded(group.code) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                    <span class="node-code">{{ group.code }}</span>
                    <span class="node-title">{{ group.name_zh }} <span class="en-sub">{{ group.name_en }}</span></span>
                    <span class="badge-mini" v-if="group.company_count > 0">{{ group.company_count }}</span>
                  </div>

                  <!-- Level 3: Industries -->
                  <div v-if="isExpanded(group.code)" class="group-body">
                    <div 
                      v-for="industry in group.children" 
                      :key="industry.code" 
                      class="industry-node"
                      :class="{ 'has-highlight': sectorHasHighlight(industry) }"
                      :id="'node-' + industry.code"
                    >
                      <div class="industry-header" @click="toggleExpand(industry.code)">
                        <svg class="fold-icon" :class="{ 'open': isExpanded(industry.code) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                        <span class="node-code">{{ industry.code }}</span>
                        <span class="node-title">{{ industry.name_zh }} <span class="en-sub">{{ industry.name_en }}</span></span>
                        <span class="badge-mini" v-if="industry.company_count > 0">{{ industry.company_count }}</span>
                      </div>

                      <!-- Level 4: Sub-Industries (Leaf Nodes) -->
                      <div v-if="isExpanded(industry.code)" class="industry-body">
                        <div 
                          v-for="sub in industry.children" 
                          :key="sub.code" 
                          class="sub-industry-node"
                          :class="{ 'highlighted-leaf': activeSubIndustryCode === sub.code }"
                          :id="'node-' + sub.code"
                        >
                          <div class="sub-industry-header">
                            <span class="leaf-dot"></span>
                            <span class="node-code">{{ sub.code }}</span>
                            <span class="node-title">{{ sub.name_zh }} <span class="en-sub">{{ sub.name_en }}</span></span>
                          </div>

                          <!-- Companies mapped to this sub-industry -->
                          <div class="mapped-companies-list" v-if="sub.companies && sub.companies.length > 0">
                            <div 
                              v-for="comp in sub.companies" 
                              :key="comp.ticker"
                              class="company-pill"
                              :class="{ 
                                'pulse-highlight': activeCompanyTicker === comp.ticker,
                                'pill-has-report': comp.report_status === 'completed'
                              }"
                              @click="handleCompanyPillClick(comp)"
                              :title="comp.description || comp.name"
                            >
                              <span class="pill-ticker">{{ comp.ticker }}</span>
                              <span class="pill-name">{{ comp.name }}</span>
                              <span v-if="comp.report_status === 'completed'" class="report-indicator" title="点击查看AI研报">📄</span>
                            </div>
                          </div>
                        </div>
                      </div>

                    </div>
                  </div>

                </div>
              </div>

            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Side Drawer: Register / Edit Company mapping -->
    <transition name="slide">
      <div v-if="showRegisterDrawer" class="drawer-overlay" @click="closeRegisterDrawer">
        <div class="drawer-content" @click.stop>
          <div class="drawer-header">
            <h2>登记个股行业映射</h2>
            <button class="close-btn" @click="closeRegisterDrawer">&times;</button>
          </div>
          
          <form @submit.prevent="submitRegisterCompany" class="drawer-form">
            <div class="form-group">
              <label for="comp-ticker">股票代码 (Ticker) <span class="req">*</span></label>
              <input 
                id="comp-ticker"
                type="text" 
                v-model="form.ticker" 
                placeholder="例如: TSLA" 
                required 
                class="form-control"
              />
            </div>
            
            <div class="form-group">
              <label for="comp-name">公司名称 (Company Name) <span class="req">*</span></label>
              <input 
                id="comp-name"
                type="text" 
                v-model="form.name" 
                placeholder="例如: Tesla, Inc." 
                required
                class="form-control"
              />
            </div>

            <div class="form-group">
              <label for="comp-gics">GICS 子行业 (Sub-Industry) <span class="req">*</span></label>
              <div class="select-wrapper">
                <select 
                  id="comp-gics" 
                  v-model="form.gics_code" 
                  required
                  class="form-control select-control"
                >
                  <option value="" disabled>请选择标准 GICS 4级分类</option>
                  <option 
                    v-for="cat in leafCategories" 
                    :key="cat.code" 
                    :value="cat.code"
                  >
                    [{{ cat.code }}] {{ cat.name_zh }} ({{ cat.name_en }})
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label for="comp-desc">核心业务描述 (Description)</label>
              <textarea 
                id="comp-desc"
                v-model="form.description" 
                placeholder="输入主要业务收入来源，主营产品或服务..." 
                rows="4"
                class="form-control"
              ></textarea>
            </div>

            <div class="drawer-actions">
              <button type="button" class="secondary-btn" @click="closeRegisterDrawer">取消</button>
              <button type="submit" class="primary-btn btn-glow" :disabled="submitting">
                {{ submitting ? '保存中...' : '确认登记' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <!-- Side Drawer: AI Report Details & Org Chart -->
    <transition name="slide">
      <div v-if="showReportDrawer" class="drawer-overlay" @click="closeReportDrawer">
        <div class="report-drawer-content" @click.stop>
          <div class="drawer-header">
            <h2>GICS 行业八维深度研究报告</h2>
            <button class="close-btn" @click="closeReportDrawer">&times;</button>
          </div>
          
          <div class="report-workspace" v-if="selectedCompany">
            <!-- Left sub-panel: AI Org Chart -->
            <div class="report-org-panel">
              <h3>AI 研究协同团队 (Org Chart)</h3>
              <p class="org-subtitle">依据 GICS 编码 [{{ selectedCompany.gics_code }}] 动态匹配分工</p>
              
              <div v-if="loadingOrg" class="org-loading">
                <div class="spinner-mini"></div>
                <span>正在匹配 AI 员工体系...</span>
              </div>
              
              <div v-else class="org-list">
                <div v-for="emp in activeOrg" :key="emp.role_slug" class="employee-card-node">
                  <div class="emp-avatar">
                    <span v-if="emp.role_slug === 'ceo'">👑</span>
                    <span v-else-if="emp.role_slug === 'cfo'">📈</span>
                    <span v-else-if="emp.role_slug === 'cro'">🛡️</span>
                    <span v-else>🔬</span>
                  </div>
                  <div class="emp-info">
                    <h4>{{ emp.role_name }}</h4>
                    <span class="emp-tag">{{ emp.role_slug.toUpperCase() }}</span>
                    <p class="emp-prompt">{{ emp.system_prompt_template }}</p>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Right sub-panel: Report Document Viewer -->
            <div class="report-doc-panel">
              <div class="doc-header">
                <div class="doc-meta">
                  <h3>{{ selectedCompany.name }} ({{ selectedCompany.ticker }})</h3>
                  <span class="ticker-badge-large">GICS: {{ selectedCompany.gics_code }}</span>
                </div>
                <button class="secondary-btn btn-sm" @click="confirmDeleteCompany(selectedCompany.ticker)">
                  解除个股行业绑定
                </button>
              </div>
              
              <div class="doc-viewport">
                <div v-if="loadingReport" class="doc-loading">
                  <div class="spinner"></div>
                  <p>大模型读取报告中...</p>
                </div>
                <div v-else-if="!activeReport" class="doc-empty">
                  <p>该个股目前暂无 AI 八维行研报告。</p>
                  <p class="sub">您可以在终端运行 `/goal` 通宵批处理，或稍后由 AI Agent 自动生成。</p>
                </div>
                <div v-else class="markdown-body" v-html="renderedReport"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import { ref, onMounted, computed, onUnmounted } from 'vue';

const API_BASE = "http://127.0.0.1:8001/api";

export default {
  name: 'App',
  setup() {
    // Theme state
    const isLightTheme = ref(false);
    const toggleTheme = () => {
      isLightTheme.value = !isLightTheme.value;
      localStorage.setItem('theme', isLightTheme.value ? 'light' : 'dark');
      document.documentElement.classList.toggle('light-theme', isLightTheme.value);
    };

    // Reactive States
    const loading = ref(true);
    const submitting = ref(false);
    const showRegisterDrawer = ref(false);
    const showReportDrawer = ref(false);
    const gicsTree = ref([]);
    const companies = ref([]);
    const flatCategories = ref([]);
    const searchQuery = ref('');
    const expandedNodes = ref(new Set());
    
    // Seeding & progress
    const progress = ref(null);
    let progressTimer = null;
    
    // Highlight / selected company details
    const activeCompanyTicker = ref('');
    const activeSubIndustryCode = ref('');
    const selectedCompany = ref(null);
    const activeReport = ref('');
    const activeOrg = ref([]);
    const loadingReport = ref(false);
    const loadingOrg = ref(false);

    // Register Form
    const form = ref({
      ticker: '',
      name: '',
      gics_code: '',
      description: ''
    });

    // Toggle expand status of GICS node
    const isExpanded = (code) => expandedNodes.value.has(code);
    
    const toggleExpand = (code) => {
      if (expandedNodes.value.has(code)) {
        expandedNodes.value.delete(code);
      } else {
        expandedNodes.value.add(code);
      }
    };

    // Collapse and expand helper
    const expandAllSectors = () => {
      const collectCodes = (nodes) => {
        nodes.forEach(n => {
          if (n.children && n.children.length > 0) {
            expandedNodes.value.add(n.code);
            collectCodes(n.children);
          }
        });
      };
      collectCodes(gicsTree.value);
    };

    const collapseAllSectors = () => {
      expandedNodes.value.clear();
      activeCompanyTicker.value = '';
      activeSubIndustryCode.value = '';
    };

    // Calculate total GICS nodes count
    const flatCategoriesCount = computed(() => flatCategories.value.length);

    // Progress percentage
    const progressPercentage = computed(() => {
      if (!progress.value || progress.value.total === 0) return 0;
      return Math.round((progress.value.completed_count / progress.value.total) * 100);
    });

    // Filtered lists
    const filteredCompanies = computed(() => {
      if (!searchQuery.value) return companies.value;
      const query = searchQuery.value.toLowerCase().trim();
      return companies.value.filter(c => 
        c.ticker.toLowerCase().includes(query) ||
        c.name.toLowerCase().includes(query) ||
        (c.industry_name_zh && c.industry_name_zh.toLowerCase().includes(query)) ||
        (c.industry_name_en && c.industry_name_en.toLowerCase().includes(query))
      );
    });

    // Filter GICS Leaf nodes (Level 4 Sub-industries)
    const leafCategories = computed(() => {
      return flatCategories.value.filter(c => c.level === 4);
    });

    // Simple custom line-by-line Markdown and Table renderer
    const renderedReport = computed(() => {
      if (!activeReport.value) return '';
      const lines = activeReport.value.split('\n');
      let inList = false;
      let inTable = false;
      let html = [];
      
      for (let line of lines) {
        let trimmed = line.trim();
        
        // Table processing
        if (trimmed.startsWith('|')) {
          if (!inTable) {
            inTable = true;
            html.push('<table class="report-table">');
            const cells = trimmed.split('|').slice(1, -1).map(c => c.trim());
            // Skip separator line |---|---|
            if (cells.every(c => c.match(/^:-*|-*:-*|-*:$/) || c === '---' || c === '')) {
              continue;
            }
            html.push('<tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr>');
          } else {
            const cells = trimmed.split('|').slice(1, -1).map(c => c.trim());
            if (cells.every(c => c.match(/^:-*|-*:-*|-*:$/) || c === '---' || c === '')) {
              continue;
            }
            html.push('<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>');
          }
          continue;
        } else if (inTable) {
          inTable = false;
          html.push('</table>');
        }
        
        // Headers
        if (trimmed.startsWith('# ')) {
          html.push(`<h1>${trimmed.substring(2)}</h1>`);
        } else if (trimmed.startsWith('## ')) {
          html.push(`<h2>${trimmed.substring(3)}</h2>`);
        } else if (trimmed.startsWith('### ')) {
          html.push(`<h3>${trimmed.substring(4)}</h3>`);
        } else if (trimmed.startsWith('#### ')) {
          html.push(`<h4>${trimmed.substring(5)}</h4>`);
        }
        // Lists
        else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          if (!inList) {
            inList = true;
            html.push('<ul>');
          }
          const itemText = trimmed.substring(2).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
          html.push(`<li>${itemText}</li>`);
        } else {
          if (inList) {
            inList = false;
            html.push('</ul>');
          }
          if (trimmed) {
            const boldText = trimmed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            html.push(`<p>${boldText}</p>`);
          }
        }
      }
      if (inList) html.push('</ul>');
      if (inTable) html.push('</table>');
      return html.join('\n');
    });

    // Fetch flat list of categories recursively from GICS Tree
    const buildFlatCategories = (nodes) => {
      let list = [];
      const traverse = (ns) => {
        ns.forEach(n => {
          list.push({
            code: n.code,
            name_en: n.name_en,
            name_zh: n.name_zh,
            level: n.level,
            parent_code: n.parent_code
          });
          if (n.children && n.children.length > 0) {
            traverse(n.children);
          }
        });
      };
      traverse(nodes);
      flatCategories.value = list;
    };

    // Fetch all core data from FastAPI backend
    const fetchData = async () => {
      loading.value = true;
      try {
        const [treeRes, compRes, progRes] = await Promise.all([
          fetch(`${API_BASE}/gics/tree`),
          fetch(`${API_BASE}/companies`),
          fetch(`${API_BASE}/progress`)
        ]);

        if (treeRes.ok && compRes.ok && progRes.ok) {
          gicsTree.value = await treeRes.json();
          companies.value = await compRes.json();
          progress.value = await progRes.json();
          buildFlatCategories(gicsTree.value);
        } else {
          console.error("API error loading dashboard data.");
        }
      } catch (err) {
        console.error("Network error:", err);
      } finally {
        loading.value = false;
      }
    };

    // Poll task progress every 5 seconds to keep track of overnight running progress
    const fetchProgressOnly = async () => {
      try {
        const progRes = await fetch(`${API_BASE}/progress`);
        if (progRes.ok) {
          progress.value = await progRes.json();
        }
      } catch (err) {
        console.warn("Silent background progress fetch failed:", err);
      }
    };

    // Open/Close Register drawer
    const openRegisterDrawer = (company = null) => {
      if (company) {
        form.value = {
          ticker: company.ticker,
          name: company.name,
          gics_code: company.gics_code,
          description: company.description || ''
        };
      } else {
        form.value = { ticker: '', name: '', gics_code: '', description: '' };
      }
      showRegisterDrawer.value = true;
    };

    const closeRegisterDrawer = () => {
      showRegisterDrawer.value = false;
    };

    // Open Report Panel and load report/org chart
    const openReportPanel = async (ticker) => {
      const comp = companies.value.find(c => c.ticker === ticker);
      if (!comp) return;

      selectedCompany.value = comp;
      showReportDrawer.value = true;
      loadingReport.value = true;
      loadingOrg.value = true;
      activeReport.value = '';
      activeOrg.value = [];

      try {
        // 1. Fetch AI Org Chart
        const orgRes = await fetch(`${API_BASE}/gics/org/${ticker}`);
        if (orgRes.ok) {
          const orgData = await orgRes.json();
          activeOrg.value = orgData.org_chart;
        }
      } catch (err) {
        console.error("Failed to load org chart:", err);
      } finally {
        loadingOrg.value = false;
      }

      try {
        // 2. Fetch GICS Report
        const repRes = await fetch(`${API_BASE}/reports/${ticker}`);
        if (repRes.ok) {
          const repData = await repRes.json();
          activeReport.value = repData.report_md;
        }
      } catch (err) {
        console.log("No report or failed to load:", err);
      } finally {
        loadingReport.value = false;
      }
    };

    const closeReportDrawer = () => {
      showReportDrawer.value = false;
      selectedCompany.value = null;
      activeReport.value = '';
      activeOrg.value = [];
    };

    const handleCompanyPillClick = (comp) => {
      locateCompanyInTree(comp);
      // If it has a completed report, open the report reader automatically
      if (comp.report_status === 'completed') {
        openReportPanel(comp.ticker);
      }
    };

    // Handle submit for adding/updating company mapping
    const submitRegisterCompany = async () => {
      submitting.value = true;
      try {
        const response = await fetch(`${API_BASE}/companies`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form.value)
        });

        if (response.ok) {
          await fetchData();
          closeRegisterDrawer();
          const newComp = companies.value.find(c => c.ticker.toUpperCase() === form.value.ticker.toUpperCase());
          if (newComp) locateCompanyInTree(newComp);
        } else {
          const err = await response.json();
          alert(`登记失败: ${err.detail || '未知错误'}`);
        }
      } catch (err) {
        alert("网络连接错误，无法提交登记表单");
      } finally {
        submitting.value = false;
      }
    };

    // Handle delete mapping
    const confirmDeleteCompany = async (ticker) => {
      if (confirm(`确定要解除股票 [${ticker}] 的行业映射关系吗？（这将同步删除其已生成的AI研报）`)) {
        try {
          const response = await fetch(`${API_BASE}/companies/${ticker}`, {
            method: 'DELETE'
          });
          if (response.ok) {
            if (activeCompanyTicker.value === ticker) {
              activeCompanyTicker.value = '';
              activeSubIndustryCode.value = '';
            }
            if (selectedCompany.value && selectedCompany.value.ticker === ticker) {
              closeReportDrawer();
            }
            await fetchData();
          } else {
            alert("解除映射失败");
          }
        } catch (err) {
          alert("网络错误");
        }
      }
    };

    // Locate and highlight a company inside the tree view
    const locateCompanyInTree = (company) => {
      const code = company.gics_code;
      if (!code) return;

      activeCompanyTicker.value = company.ticker;
      activeSubIndustryCode.value = code;

      // Expand all parent nodes recursively
      if (code.length >= 2) expandedNodes.value.add(code.substring(0, 2));
      if (code.length >= 4) expandedNodes.value.add(code.substring(0, 4));
      if (code.length >= 6) expandedNodes.value.add(code.substring(0, 6));

      // Scroll highlighted element into view
      setTimeout(() => {
        const element = document.getElementById(`node-${code}`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
    };

    const highlightSidebarCompany = (ticker) => {
      activeCompanyTicker.value = ticker;
    };

    // Search and auto-expand highlights
    const sectorHasHighlight = (node) => {
      if (!searchQuery.value) return false;
      const query = searchQuery.value.toLowerCase().trim();
      
      const checkNode = (n) => {
        if (n.code.toLowerCase().includes(query) ||
            n.name_zh.toLowerCase().includes(query) ||
            n.name_en.toLowerCase().includes(query)) {
          return true;
        }
        if (n.companies && n.companies.some(c => 
          c.ticker.toLowerCase().includes(query) || c.name.toLowerCase().includes(query)
        )) {
          return true;
        }
        if (n.children && n.children.length > 0) {
          return n.children.some(checkNode);
        }
        return false;
      };
      
      return checkNode(node);
    };

    const handleSearch = () => {
      if (!searchQuery.value) return;
      
      const query = searchQuery.value.toLowerCase().trim();
      const expandMatching = (nodes) => {
        nodes.forEach(n => {
          const isMatch = n.code.toLowerCase().includes(query) ||
                          n.name_zh.toLowerCase().includes(query) ||
                          n.name_en.toLowerCase().includes(query) ||
                          (n.companies && n.companies.some(c => 
                            c.ticker.toLowerCase().includes(query) || c.name.toLowerCase().includes(query)
                          ));
          if (isMatch && n.children && n.children.length > 0) {
            expandedNodes.value.add(n.code);
            expandMatching(n.children);
          } else if (n.children && n.children.length > 0) {
            const hasMatch = (ns) => ns.some(x => {
              const matches = x.code.toLowerCase().includes(query) ||
                              x.name_zh.toLowerCase().includes(query) ||
                              x.name_en.toLowerCase().includes(query) ||
                              (x.companies && x.companies.some(c => 
                                c.ticker.toLowerCase().includes(query) || c.name.toLowerCase().includes(query)
                              ));
              if (matches) return true;
              if (x.children && x.children.length > 0) return hasMatch(x.children);
              return false;
            });
            
            if (hasMatch(n.children)) {
              expandedNodes.value.add(n.code);
              expandMatching(n.children);
            }
          }
        });
      };
      expandMatching(gicsTree.value);
    };

    const clearSearch = () => {
      searchQuery.value = '';
      activeCompanyTicker.value = '';
      activeSubIndustryCode.value = '';
    };

    // Lifecycle: start polling progress
    onMounted(() => {
      fetchData();
      progressTimer = setInterval(fetchProgressOnly, 5000);
      
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme === 'light') {
        isLightTheme.value = true;
        document.documentElement.classList.add('light-theme');
      } else {
        document.documentElement.classList.remove('light-theme');
      }
    });

    onUnmounted(() => {
      if (progressTimer) clearInterval(progressTimer);
    });

    return {
      loading,
      submitting,
      showRegisterDrawer,
      showReportDrawer,
      gicsTree,
      companies,
      leafCategories,
      searchQuery,
      flatCategoriesCount,
      filteredCompanies,
      activeCompanyTicker,
      activeSubIndustryCode,
      selectedCompany,
      activeReport,
      activeOrg,
      loadingReport,
      loadingOrg,
      progress,
      progressPercentage,
      renderedReport,
      form,
      isExpanded,
      toggleExpand,
      expandAllSectors,
      collapseAllSectors,
      openRegisterDrawer,
      closeRegisterDrawer,
      openReportPanel,
      closeReportDrawer,
      handleCompanyPillClick,
      submitRegisterCompany,
      confirmDeleteCompany,
      locateCompanyInTree,
      highlightSidebarCompany,
      sectorHasHighlight,
      handleSearch,
      clearSearch,
      fetchData,
      isLightTheme,
      toggleTheme
    };
  }
};
</script>

<style>
/* Global Imports & CSS Variables */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
  color-scheme: dark;
  --bg-color: #0b0d10;
  --bg-sidebar: rgba(18, 22, 28, 0.7);
  --bg-card: rgba(255, 255, 255, 0.03);
  --border-color: rgba(255, 255, 255, 0.08);
  --border-highlight: rgba(0, 240, 255, 0.3);
  --text-primary: #f3f4f6;
  --text-secondary: #9ca3af;
  --text-muted: #6b7280;
  
  --color-primary: hsl(185, 100%, 50%);       /* Neon Cyan */
  --color-primary-glow: hsla(185, 100%, 50%, 0.15);
  --color-accent: hsl(275, 100%, 65%);        /* Neon Purple */
  --color-success: hsl(140, 70%, 50%);         /* Mint Emerald */
  --color-warning: hsl(40, 90%, 55%);          /* Amber Gold */
  --color-danger: hsl(355, 85%, 60%);          /* Rose red */
  
  --font-sans: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  --bg-header: rgba(15, 18, 23, 0.85);
  --bg-drawer: #11141a;
  --bg-panel: rgba(10, 12, 16, 0.3);
  --bg-input: rgba(255, 255, 255, 0.04);
  --bg-input-focus: rgba(255, 255, 255, 0.07);
  --text-markdown: #d1d5db;
  --text-strong: #ffffff;

  --color-scrollbar-track: rgba(255, 255, 255, 0.01);
  --color-scrollbar-thumb: rgba(255, 255, 255, 0.15);
  scrollbar-color: var(--color-scrollbar-thumb) var(--color-scrollbar-track);
  scrollbar-width: thin;
}

/* Light Theme Variables */
.light-theme {
  color-scheme: light;
  --bg-color: #f3f4f6;
  --bg-sidebar: rgba(255, 255, 255, 0.8);
  --bg-card: rgba(0, 0, 0, 0.02);
  --border-color: rgba(0, 0, 0, 0.08);
  --border-highlight: rgba(0, 180, 210, 0.4);
  --text-primary: #111827;
  --text-secondary: #4b5563;
  --text-muted: #9ca3af;
  
  --color-primary: hsl(190, 90%, 40%);
  --color-primary-glow: rgba(0, 180, 210, 0.15);
  --color-accent: hsl(275, 75%, 50%);
  --color-success: hsl(140, 75%, 35%);
  --color-warning: hsl(35, 85%, 45%);
  --color-danger: hsl(355, 75%, 45%);
  
  --bg-header: rgba(255, 255, 255, 0.85);
  --bg-drawer: #ffffff;
  --bg-panel: rgba(0, 0, 0, 0.02);
  --bg-input: rgba(0, 0, 0, 0.03);
  --bg-input-focus: rgba(0, 0, 0, 0.06);
  --text-markdown: #374151;
  --text-strong: #111827;

  --color-scrollbar-track: rgba(0, 0, 0, 0.02);
  --color-scrollbar-thumb: rgba(0, 0, 0, 0.15);
}

/* Theme Toggle Button */
.theme-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-color);
  border-radius: 50%;
  color: var(--text-primary);
  cursor: pointer;
  transition: var(--transition-smooth);
}

.theme-toggle-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--color-primary);
  color: var(--color-primary);
  box-shadow: 0 0 10px var(--color-primary-glow);
}

.theme-icon {
  width: 18px;
  height: 18px;
}

/* Light theme specific class overrides for non-inherited properties */
.light-theme.app-container {
  background-image: 
    radial-gradient(at 10% 20%, hsla(275, 100%, 90%, 0.4) 0px, transparent 50%),
    radial-gradient(at 90% 80%, hsla(185, 100%, 90%, 0.4) 0px, transparent 50%);
}

.light-theme .sector-card:hover {
  border-color: rgba(0, 0, 0, 0.12);
  background: rgba(0, 0, 0, 0.04);
}

.light-theme .sector-code {
  background: rgba(0, 0, 0, 0.03);
}

.light-theme .group-header:hover, 
.light-theme .industry-header:hover {
  background: rgba(0, 0, 0, 0.03);
}

.light-theme .node-code {
  background: rgba(0, 0, 0, 0.04);
}

.light-theme .badge-mini {
  background: rgba(0, 0, 0, 0.08);
}

.light-theme .sub-industry-node {
  background: rgba(0, 0, 0, 0.01);
}

.light-theme .sub-industry-node:hover {
  background: rgba(0, 0, 0, 0.02);
}

.light-theme .sub-industry-node.highlighted-leaf {
  background: rgba(0, 180, 210, 0.05);
}

.light-theme .company-pill {
  background: rgba(0, 0, 0, 0.03);
}

.light-theme .company-pill:hover {
  background: rgba(0, 0, 0, 0.06);
}

.light-theme .company-pill.pulse-highlight {
  background: rgba(0, 180, 210, 0.1);
}

.light-theme .company-card:hover {
  background: rgba(0, 0, 0, 0.04);
  border-color: rgba(0, 0, 0, 0.12);
}

.light-theme .company-card.highlighted {
  border-color: var(--color-primary);
  background: rgba(0, 180, 210, 0.04);
  box-shadow: 0 0 10px rgba(0, 180, 210, 0.1);
}

.light-theme .ticker-badge {
  background: rgba(0, 180, 210, 0.12);
}

.light-theme .theme-toggle-btn {
  background: rgba(0, 0, 0, 0.03);
  color: var(--text-primary);
  border-color: var(--border-color);
}

.light-theme .theme-toggle-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.light-theme .drawer-content,
.light-theme .report-drawer-content {
  box-shadow: -10px 0 30px rgba(0,0,0,0.1);
}

/* Reset */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-sans);
  background-color: var(--bg-color);
  color: var(--text-primary);
  overflow: hidden;
  height: 100vh;
}

/* Scrollbars */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: var(--color-scrollbar-track);
}
::-webkit-scrollbar-thumb {
  background: var(--color-scrollbar-thumb);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--color-primary);
}

/* App Container Layout */
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-image: 
    radial-gradient(at 10% 20%, hsla(275, 100%, 15%, 0.1) 0px, transparent 50%),
    radial-gradient(at 90% 80%, hsla(185, 100%, 15%, 0.08) 0px, transparent 50%);
}

/* App Header styling (Glassmorphism) */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--bg-header);
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(16px);
  z-index: 10;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  border-radius: 10px;
  font-weight: 700;
  font-size: 20px;
  color: #000;
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.3);
}

.logo-text h1 {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.logo-text p {
  font-size: 11px;
  color: var(--text-secondary);
}

/* Header Actions */
.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  width: 320px;
}

.search-icon {
  position: absolute;
  left: 12px;
  width: 16px;
  height: 16px;
  color: var(--text-secondary);
}

.search-box input {
  width: 100%;
  padding: 9px 36px 9px 36px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 13px;
  outline: none;
  transition: var(--transition-smooth);
}

.search-box input:focus {
  border-color: var(--color-primary);
  background: var(--bg-input-focus);
  box-shadow: 0 0 12px var(--color-primary-glow);
}

.clear-btn {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 18px;
  cursor: pointer;
}

/* Button UI */
.primary-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  background: linear-gradient(135deg, var(--color-primary), hsl(190, 100%, 45%));
  border: none;
  border-radius: 20px;
  color: #000;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 13.5px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.primary-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 18px rgba(0, 240, 255, 0.4);
}

.btn-glow {
  box-shadow: 0 0 10px var(--color-primary-glow);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.secondary-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-weight: 500;
  font-size: 12.5px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.secondary-btn:hover {
  background: rgba(255, 255, 255, 0.08);
}

.btn-sm {
  padding: 4px 10px;
  font-size: 11px;
}

/* Progress Banner controls */
.progress-banner {
  background: rgba(0, 240, 255, 0.02);
  border-bottom: 1px solid rgba(0, 240, 255, 0.1);
  padding: 10px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 24px;
  font-size: 12.5px;
}

.progress-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 10px var(--color-success);
  animation: beacon 1.5s infinite;
}

.pulse-dot.inactive {
  background: var(--text-muted);
  box-shadow: none;
  animation: none;
}

@keyframes beacon {
  0% { transform: scale(0.9); opacity: 0.8; }
  50% { transform: scale(1.1); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.8; }
}

.current-task-name {
  color: var(--color-primary);
  font-family: monospace;
}

.progress-stats {
  display: flex;
  gap: 16px;
  color: var(--text-secondary);
}

.progress-stats strong {
  color: var(--text-primary);
}

.progress-bar-container {
  flex: 1;
  max-width: 400px;
  height: 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color);
}

.progress-bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-percentage {
  position: relative;
  z-index: 1;
  font-size: 9px;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0,0,0,0.8);
}

.icon-btn-sync {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  transition: var(--transition-smooth);
}

.icon-btn-sync:hover {
  color: var(--color-primary);
  background: rgba(255, 255, 255, 0.05);
}

.sync-icon {
  width: 16px;
  height: 16px;
}

.sync-icon:active {
  transform: rotate(180deg);
}

/* Colors helpers */
.text-success { color: var(--color-success) !important; }
.text-primary { color: var(--color-primary) !important; }
.text-warning { color: var(--color-warning) !important; }

/* Workspace Panels */
.workspace {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Panel Header design */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-color);
}

.panel-header h2 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

/* Left Sidebar Panel */
.sidebar-panel {
  width: 320px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Company Card in Sidebar */
.company-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.company-card:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.15);
  transform: translateX(2px);
}

.company-card.highlighted {
  border-color: var(--color-primary);
  background: rgba(0, 240, 255, 0.03);
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.1);
}

.company-card.has-report {
  border-left: 3px solid var(--color-success);
}

.company-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.ticker-badge {
  background: rgba(0, 240, 255, 0.15);
  color: var(--color-primary);
  font-weight: 700;
  font-size: 11.5px;
  padding: 2.5px 8px;
  border-radius: 6px;
  letter-spacing: 0.5px;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-icon-btn {
  background: rgba(48, 209, 88, 0.15);
  border: 1px solid rgba(48, 209, 88, 0.3);
  color: var(--color-success);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: var(--transition-smooth);
}

.action-icon-btn:hover {
  background: rgba(48, 209, 88, 0.25);
  box-shadow: 0 0 8px rgba(48, 209, 88, 0.3);
}

.delete-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  transition: var(--transition-smooth);
}

.delete-btn:hover {
  color: var(--color-danger);
}

.delete-btn svg {
  width: 14px;
  height: 14px;
}

.company-card h3 {
  font-size: 13.5px;
  font-weight: 500;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.comp-desc {
  font-size: 11.5px;
  color: var(--text-secondary);
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.comp-industry-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-secondary);
}

.comp-industry-tag svg {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

.comp-industry-tag span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Right Tree Panel */
.tree-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
}

.tree-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.text-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 12.5px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: var(--transition-smooth);
}

.text-btn:hover {
  text-shadow: 0 0 8px rgba(0, 240, 255, 0.4);
}

.divider {
  color: var(--text-muted);
  font-size: 12px;
}

.tree-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  gap: 12px;
  color: var(--text-secondary);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(255, 255, 255, 0.05);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-mini {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.05);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Sectors Grid */
.sectors-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1000px;
  margin: 0 auto;
}

/* Sector Level 1 Card */
.sector-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  overflow: hidden;
  transition: var(--transition-smooth);
}

.sector-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.04);
}

.sector-card.has-highlight {
  border-color: var(--color-accent);
  box-shadow: 0 0 10px rgba(191, 90, 242, 0.05);
}

.sector-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
}

.sector-info {
  display: flex;
  align-items: center;
  gap: 14px;
}

.sector-code {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  font-weight: 700;
  font-size: 13px;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.sector-card.has-highlight .sector-code {
  background: rgba(191, 90, 242, 0.15);
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.sector-titles h3 {
  font-size: 14.5px;
  font-weight: 600;
  margin-bottom: 2px;
}

.sector-titles span {
  font-size: 11px;
  color: var(--text-secondary);
}

.sector-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.count-badge {
  font-size: 11.5px;
  color: var(--text-muted);
  padding: 3px 8px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
}

.count-badge.has-companies {
  background: var(--color-primary-glow);
  color: var(--color-primary);
  font-weight: 500;
}

.chevron-icon {
  width: 16px;
  height: 16px;
  color: var(--text-secondary);
  transition: transform 0.25s ease;
}

.chevron-icon.rotate {
  transform: rotate(180deg);
}

/* Sector Card Body (Children) */
.sector-card-body {
  padding: 4px 20px 16px 20px;
  background: rgba(0, 0, 0, 0.1);
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Node Elements */
.group-node {
  padding: 6px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.03);
}

.group-node:last-child {
  border-bottom: none;
}

.group-header, .industry-header {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  font-weight: 500;
}

.group-header:hover, .industry-header:hover {
  background: rgba(255, 255, 255, 0.03);
}

.fold-icon {
  width: 14px;
  height: 14px;
  margin-right: 8px;
  color: var(--text-muted);
  transition: transform 0.2s ease;
}

.fold-icon.open {
  transform: rotate(90deg);
}

.node-code {
  font-family: monospace;
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-secondary);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  margin-right: 8px;
}

.node-title {
  color: var(--text-primary);
}

.en-sub {
  font-size: 10.5px;
  color: var(--text-secondary);
  margin-left: 6px;
}

.badge-mini {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  margin-left: 8px;
}

.has-highlight > .group-header,
.has-highlight > .industry-header {
  background: rgba(191, 90, 242, 0.04);
}

.has-highlight > .group-header .node-title,
.has-highlight > .industry-header .node-title {
  color: var(--color-accent);
}

/* Indents */
.group-body {
  padding-left: 20px;
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.industry-body {
  padding-left: 20px;
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* Sub-Industry Leaf Node */
.sub-industry-node {
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.01);
  border: 1px solid transparent;
}

.sub-industry-node:hover {
  background: rgba(255, 255, 255, 0.02);
}

.sub-industry-node.highlighted-leaf {
  border-color: var(--color-primary);
  background: rgba(0, 240, 255, 0.03);
}

.sub-industry-header {
  display: flex;
  align-items: center;
  font-size: 12.5px;
  margin-bottom: 8px;
}

.leaf-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  margin-right: 10px;
}

.highlighted-leaf .leaf-dot {
  background: var(--color-primary);
  box-shadow: 0 0 8px var(--color-primary);
}

/* Mapped Companies Pill list inside sub-industries */
.mapped-companies-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-left: 18px;
}

.company-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 11.5px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.company-pill:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--color-primary);
}

.pill-ticker {
  font-weight: 700;
  color: var(--color-primary);
}

.pill-name {
  color: var(--text-secondary);
}

.pill-has-report {
  border-left: 3px solid var(--color-success);
}

.report-indicator {
  font-size: 9px;
  margin-left: 4px;
}

.company-pill.pulse-highlight {
  border-color: var(--color-primary);
  background: rgba(0, 240, 255, 0.15);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(0, 240, 255, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(0, 240, 255, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 240, 255, 0); }
}

/* Side Drawers */
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  z-index: 100;
  display: flex;
  justify-content: flex-end;
}

.drawer-content {
  width: 420px;
  height: 100%;
  background: var(--bg-drawer);
  border-left: 1px solid var(--border-color);
  padding: 30px;
  display: flex;
  flex-direction: column;
  box-shadow: -10px 0 30px rgba(0,0,0,0.5);
}

/* Wide drawer for report analysis & org chart view */
.report-drawer-content {
  width: 1050px;
  height: 100%;
  background: var(--bg-drawer);
  border-left: 1px solid var(--border-color);
  padding: 30px;
  display: flex;
  flex-direction: column;
  box-shadow: -15px 0 45px rgba(0,0,0,0.6);
}

.report-workspace {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 30px;
  margin-top: 10px;
}

/* Left: Org Chart */
.report-org-panel {
  width: 320px;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.report-org-panel h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--text-primary);
}

.org-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 20px;
}

.org-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 12.5px;
  padding: 20px 0;
}

.org-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.employee-card-node {
  display: flex;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
}

.emp-avatar {
  font-size: 20px;
  width: 36px;
  height: 36px;
  background: var(--bg-input);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--border-color);
}

.emp-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.emp-info h4 {
  font-size: 13px;
  font-weight: 600;
}

.emp-tag {
  align-self: flex-start;
  font-size: 9px;
  font-weight: 700;
  background: var(--color-primary-glow);
  color: var(--color-primary);
  padding: 1px 4px;
  border-radius: 3px;
  margin: 2px 0 6px 0;
}

.emp-prompt {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 140%;
}

/* Right: Report Document Panel */
.report-doc-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.doc-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-panel);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.doc-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ticker-badge-large {
  background: rgba(48, 209, 88, 0.15);
  color: var(--color-success);
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid rgba(48, 209, 88, 0.3);
}

.doc-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.doc-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text-secondary);
}

.doc-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  gap: 8px;
}

.doc-empty .sub {
  font-size: 12px;
}

/* Markdown Rendering Styles */
.markdown-body {
  color: var(--text-primary);
  font-size: 14.5px;
  line-height: 165%;
}

.markdown-body h1 {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 18px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.markdown-body h2 {
  font-size: 17px;
  font-weight: 600;
  margin: 24px 0 12px 0;
  color: var(--color-primary);
}

.markdown-body h3 {
  font-size: 14.5px;
  font-weight: 600;
  margin: 18px 0 8px 0;
}

.markdown-body p {
  margin-bottom: 14px;
  color: var(--text-markdown);
}

.markdown-body ul {
  margin-bottom: 16px;
  padding-left: 20px;
}

.markdown-body li {
  margin-bottom: 6px;
  color: var(--text-markdown);
}

.markdown-body strong {
  color: var(--text-strong);
}

/* Table rendering in reports */
.report-table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13.5px;
}

.report-table th, .report-table td {
  border: 1px solid var(--border-color);
  padding: 8px 12px;
  text-align: left;
}

.report-table th {
  background-color: var(--bg-panel);
  font-weight: 600;
}

.report-table tr:nth-child(even) {
  background-color: var(--bg-card);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.drawer-header h2 {
  font-size: 17px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-smooth);
}

.close-btn:hover {
  color: var(--text-primary);
}

.drawer-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex: 1;
  overflow-y: auto;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-secondary);
}

.req {
  color: var(--color-danger);
}

.form-control {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 13px;
  outline: none;
  transition: var(--transition-smooth);
}

.form-control:focus {
  border-color: var(--color-primary);
  background: var(--bg-input-focus);
}

.select-wrapper {
  position: relative;
}

.select-control {
  appearance: none;
  cursor: pointer;
}

.drawer-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

/* Animations */
.slide-enter-active, .slide-leave-active {
  transition: opacity 0.3s ease;
}
.slide-enter-active .drawer-content, .slide-leave-active .drawer-content,
.slide-enter-active .report-drawer-content, .slide-leave-active .report-drawer-content {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-enter-from {
  opacity: 0;
}
.slide-enter-from .drawer-content, .slide-enter-from .report-drawer-content {
  transform: translateX(100%);
}
.slide-leave-to {
  opacity: 0;
}
.slide-leave-to .drawer-content, .slide-leave-to .report-drawer-content {
  transform: translateX(100%);
}
</style>
