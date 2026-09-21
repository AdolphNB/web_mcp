# 页面样式

页面加载本地 `tailwind.css` 和 `site.css`，无需连接外部样式 CDN。

更新 `site.css` 或 `support.js` 时，同步更新模板中对应资源的 `?v=` 版本，避免已访问过的浏览器继续使用旧缓存。
`site.css` 包含导航、筛选表单和无障碍样式；`site.js` 提供菜单和复制交互。

修改模板中的 Tailwind 类后，在项目根目录重新生成并提交 `tailwind.css`：

```powershell
npx --yes --package tailwindcss@3.4.17 tailwindcss -i ./static/tailwind.input.css -o ./static/tailwind.css --content "./templates/**/*.html" --minify
```

构建需要 Node.js 和 npm；运行网站不需要它们。
