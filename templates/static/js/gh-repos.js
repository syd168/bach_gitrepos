/**
 * Element Plus 仓库列表（CDN + 表单 POST 删除）
 * 模板：templates/partials/gh-repos-app-template.html → repos.html 中 #gh-repos-app-template
 */
function mountReposPage(cfg) {
  var mountEl = cfg.el || '#app-repos';
  var sel = cfg.templateSelector || '#gh-repos-app-template';
  if (!document.querySelector(sel)) {
    console.error('缺少模板节点：请在页面中放置 id="gh-repos-app-template" 的 text/x-template');
    return;
  }
  var app = Vue.createApp({
    data: function () {
      return {
        repos: cfg.repos || [],
        sortMode: cfg.sort_mode || 'updated',
        forbidNonFork: !!cfg.forbid_non_fork,
        classicWarn: cfg.classic_warn || '',
        total: cfg.total != null ? cfg.total : 0,
        sortHint: cfg.sort_hint || '',
        urls: cfg.urls,
        multipleSelection: [],
        dialogVisible: false,
        confirmText: '',
        forkToggleLabel: '全选 Fork'
      };
    },
    computed: {
      forkRows: function () {
        var self = this;
        return this.repos.filter(function (r) {
          return r.fork && self.rowSelectable(r);
        });
      }
    },
    watch: {
      multipleSelection: function () {
        this.updateForkLabel();
      }
    },
    methods: {
      rowSelectable: function (row) {
        return !(this.forbidNonFork && !row.fork);
      },
      rowClassName: function (_ref) {
        var row = _ref.row;
        if (this.forbidNonFork && !row.fork) return 'row-blocked';
        if (row.fork) return 'row-fork';
        return '';
      },
      applyFilter: function () {
        var u = new URL(this.urls.repos, window.location.origin);
        u.searchParams.set('sort', this.sortMode);
        u.searchParams.set('forbid', this.forbidNonFork ? '1' : '0');
        window.location.href = u.pathname + u.search;
      },
      handleSelectionChange: function (val) {
        this.multipleSelection = val;
      },
      updateForkLabel: function () {
        var forks = this.forkRows;
        if (!forks.length) {
          this.forkToggleLabel = '全选 Fork';
          return;
        }
        var sel = this.multipleSelection;
        var allOn = forks.every(function (r) {
          return sel.some(function (m) {
            return m.full_name === r.full_name;
          });
        });
        this.forkToggleLabel = allOn ? '取消 Fork 全选' : '全选 Fork';
      },
      toggleForkSelection: function () {
        var table = this.$refs.tableRef;
        if (!table) return;
        var forks = this.forkRows;
        if (!forks.length) {
          ElementPlus.ElMessage.warning('当前没有可选的 fork 仓库');
          return;
        }
        var sel = this.multipleSelection;
        var allOn = forks.every(function (r) {
          return sel.some(function (m) {
            return m.full_name === r.full_name;
          });
        });
        forks.forEach(function (row) {
          table.toggleRowSelection(row, !allOn);
        });
      },
      openDeleteDialog: function () {
        if (!this.multipleSelection.length) {
          ElementPlus.ElMessage.warning('请先勾选要删除的仓库');
          return;
        }
        this.confirmText = '';
        this.dialogVisible = true;
      },
      submitDelete: function () {
        if (this.confirmText !== 'DELETE') return;
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = this.urls.delete_repos;
        form.style.display = 'none';
        this.multipleSelection.forEach(function (row) {
          var inp = document.createElement('input');
          inp.type = 'hidden';
          inp.name = 'full_name';
          inp.value = row.full_name;
          form.appendChild(inp);
        });
        var x = document.createElement('input');
        x.type = 'hidden';
        x.name = 'confirm';
        x.value = 'DELETE';
        form.appendChild(x);
        x = document.createElement('input');
        x.type = 'hidden';
        x.name = 'forbid_delete_non_fork';
        x.value = this.forbidNonFork ? '1' : '0';
        form.appendChild(x);
        document.body.appendChild(form);
        form.submit();
      },
      descText: function (row) {
        var d = row.description;
        return d && String(d).trim() ? d : '—';
      },
      sortByName: function (a, b) {
        return a.full_name.localeCompare(b.full_name, 'zh-Hans-CN', { numeric: true });
      },
      sortByPrivate: function (a, b) {
        return (a.private ? 1 : 0) - (b.private ? 1 : 0);
      },
      sortByFork: function (a, b) {
        return (a.fork ? 1 : 0) - (b.fork ? 1 : 0);
      },
      sortByArchived: function (a, b) {
        return (a.archived ? 1 : 0) - (b.archived ? 1 : 0);
      },
      sortByDesc: function (a, b) {
        var da = (a.description || '').trim();
        var db = (b.description || '').trim();
        if (!da) da = '';
        if (!db) db = '';
        return da.localeCompare(db, 'zh-Hans-CN', { numeric: true });
      }
    },
    mounted: function () {
      this.updateForkLabel();
    },
    template: sel
  });
  app.use(ElementPlus);
  app.mount(mountEl);
}
