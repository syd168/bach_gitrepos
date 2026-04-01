/**
 * Element Plus 登录页
 * 模板：templates/partials/gh-login-app-template.html，由 login.html 中 <script type="text/x-template" id="gh-login-app-template"> 引入
 */
function mountLoginPage(cfg) {
  var el = cfg.el || '#app-login';
  var loginUrl = cfg.loginUrl;
  var sel = cfg.templateSelector || '#gh-login-app-template';
  if (!document.querySelector(sel)) {
    console.error('缺少模板节点：请在页面中放置 id="gh-login-app-template" 的 text/x-template');
    return;
  }
  var app = Vue.createApp({
    data: function () {
      return { token: '', loginUrl: loginUrl };
    },
    methods: {
      submitLogin: function () {
        var t = (this.token || '').trim();
        if (!t) {
          ElementPlus.ElMessage.warning('请输入 Personal Access Token');
          return;
        }
        var f = document.createElement('form');
        f.method = 'POST';
        f.action = this.loginUrl;
        f.style.display = 'none';
        var i = document.createElement('input');
        i.name = 'token';
        i.value = t;
        f.appendChild(i);
        document.body.appendChild(f);
        f.submit();
      }
    },
    template: sel
  });
  app.use(ElementPlus);
  app.mount(el);
}
