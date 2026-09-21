# 页面样式

页面加载本地 `tailwind.css` 和 `site.css`，无需连接外部样式 CDN。

更新 CSS 或 JS 时，同步更新模板中对应资源的 `?v=` 版本，避免已访问过的浏览器继续使用旧缓存。
`site.css` 通过开头的 CSS 变量统一全站深色主题，包含品牌、导航、首页、工具、新闻、客服及无障碍样式；`site.js` 提供菜单和复制交互。移动导航在 1100px 以下折叠，内容布局在 767px 以下切换为单列。减少动态效果的系统偏好会关闭平滑滚动和过渡。

品牌 SVG、分享卡片和图标见 `res/README.md`。更新应只影响模板和静态文件，保留表单字段、客服元素 ID、公开链接与接口行为。

修改模板中的 Tailwind 类后，在项目根目录重新生成并提交 `tailwind.css`：

```powershell
npx --yes --package tailwindcss@3.4.17 tailwindcss -i ./static/tailwind.input.css -o ./static/tailwind.css --content "./templates/**/*.html" --minify
```

构建需要 Node.js 和 npm；运行网站不需要它们。
