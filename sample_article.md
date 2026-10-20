---
title: 一份 Markdown 装下所有语法
author: MD2WX
digest: 从标题、表格到公式与流程图，用一篇示例跑通 MD2WX 的全部语法。
---

# 一份 Markdown 装下所有语法

> **用途**：这是 MD2WX 的默认示例，尽量把支持的 Markdown 语法放在同一篇里。
> **用法**：直接改写正文，或点「示例」重新载入。
> **提醒**：微信不支持外链跳转，正文里的链接会自动变成文末脚注。

这一段演示行内格式：**粗体**、*斜体*、***粗斜体***、~~删除线~~、==荧光高亮==、`行内代码`，以及 <u>下划线</u>、H<sub>2</sub>O、E=mc<sup>2</sup>。转义写法也不会丢：\*这里显示星号\*。  
行尾留两个空格可以强制换行；行尾加反斜杠\
同样有效。

Setext 一级标题
===

Setext 二级标题
---

## 01. 标题层级

### 三级标题

#### 四级标题

##### 五级标题

###### 六级标题

## 02. 列表与任务

- 无序列表项
  - 缩进两个空格就是子项
  - 还可以继续嵌套
- 列表项可以写多行，
  缩进后会自动并入同一项。

1. 有序列表保留源编号
2. 第二条
3. 第三条

- [x] 已完成的任务
- [ ] 待办的任务

## 03. 引用与分割线

> 一级引用适合放导读、结论或金句。
>
> > 二级引用可以表达对话与补充说明。
>
> 引用内也支持 **加粗**、`代码` 和 [链接](https://example.com)。

---

## 04. 表格

| 对齐方式 | 写法 | 效果 |
| :--- | :---: | ---: |
| 左对齐 | `:---` | 默认 |
| 居中 | `:---:` | 居中 |
| 右对齐 | `---:` | 右对齐 |

## 05. 代码

```python
def render(markdown: str, theme: str = "acid-bold") -> str:
    """把 Markdown 转成微信可用的内联 HTML。"""
    return markdown_to_wechat_html(markdown, theme_name=theme)
```

四个空格缩进也能写代码块：

    plain text stays plain
    keep the indentation

~~~javascript
// 波浪线围栏与反引号等价
console.log("MD2WX");
~~~

## 06. 公式与流程图

行内公式：$E = mc^2$。

$$
\int_{0}^{1} x^2 \, dx = \frac{1}{3}
$$

```mermaid
graph LR
  A[Markdown] --> B[Parser]
  B --> C[Inline CSS]
  C --> D[微信公众号]
```

## 07. 图片与图注

![MD2WX 全自动发布流水线](./assets/cloud-deploy-pipeline.png "发布流水线")

*▲ 图：独立成行的图片会自动居中，并支持图注。*

引用式图片：![MD2WX 标志][logo]

Obsidian 的 `![[...]]` 写法也可以直接用，例如 ![[./assets/sample-icon.png|MD2WX]]。

[logo]: ./assets/sample-icon.png

## 08. 链接与脚注

行内链接：[MD2WX 仓库](https://github.com/zaneven/MD2WX)。

引用式链接：[OpenAI][openai]。

裸链接同样会被识别：https://example.com

邮箱写法：<hello@example.com>

需要补充说明时用文本脚注[^note]，它会和链接脚注一起排到文末。

[openai]: https://openai.com
[^note]: 脚注定义可以包含 **格式** 与 `代码`，编号按首次引用顺序生成。
