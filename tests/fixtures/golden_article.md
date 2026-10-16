# MD2WX 双端渲染一致性评测样例

这是一段包含**加粗**、*斜体*、`行内代码` 与 ~~删除线~~ 的正文段落，
同时附带一个裸链接 https://example.com/docs/page 用于自动脚注转换验证。

## 二级标题：排版组件

### 三级小标题

#### 四级标题

##### 五级标题

###### 六级标题

- 无序列表项一
- 无序列表项二 **带加粗**
- [x] 已完成任务项
- [ ] 未完成任务任务

+ 加号标记列表项

1. 有序列表第一项
2. 有序列表第二项
5. 源文档编号保留

嵌套列表结构：

- 顶级项 A
  - 子级项 A1
  - 子级项 A2
    - 三级项 A2a
- 顶级项 B

1. 有序嵌套父项
   1. 子有序项
   - 子无序混合项

> 这是一段引言块内容，包含 `代码` 与 [带文本的外链](https://docs.example.com/api)。
>
> 引言块的第二行。
>> 嵌套引用内层内容。

| 模块 | 职责 | 状态 |
| --- | :---: | ---: |
| parser | 核心解析引擎 | 稳定 |
| cover | 封面渲染 | `beta` |

转义管道表格：

| 语法 | 说明 |
| --- | --- |
| a \| b | 竖线转义 |

```python
def hello(name: str) -> str:
    # 问候函数
    msg = f"Hello, {name} & <world>"
    return msg
```

```javascript
const add = (a, b) => {
  // 求和
  return a + b;
};
```

```
纯文本代码块 保 留 空 格
不做词法高亮拆分
```

~~~波浪字符围栏
tildes fence content
~~~

    def indented_code():
        return "四空格缩进代码块"

Setext 一级标题
===

Setext 二级标题
---

- - -

空格分隔的变体分割线验证完毕。

![示例图片](https://cdn.example.com/img/hero.png "hero")

*▲ 图：示例图注*

段落中内联图片 ![行内图](https://cdn.example.com/img/inline.png) 验证。

Obsidian wiki 图片：块级 ![[wiki-block.png]] 与内联 ![[wiki-inline.png]] 嵌入验证。
带别名 ![[wiki-alias.png|别名说明]] 与尺寸 ![[wiki-size.png|320]] 写法验证。
含空格文件名 ![[wiki space.png]] 与裸图片链接 [[wiki-bare.jpg]] 归一化验证。
非图片裸链接 [[某篇笔记链接]] 保持原样不改写。

```md
代码围栏内的 ![[literal.png]] 不应被转换
```

参考式链接见 [参考手册][manual] 与折叠式 [manual]，定义在文末。
参考式图片 ![参考图][logo]。

[manual]: https://docs.example.com/manual
[logo]: https://cdn.example.com/img/logo.png

脚注引用验证[^1]与第二个脚注[^note]。

[^1]: 第一个脚注的正文说明
[^note]: 带修饰的脚注：**加粗** 与 `代码`

扩展行内语法：__下划线加粗__ 与 _下划线斜体_ 与 ==高亮标记== 与 <kbd>不被放行</kbd>。

双反引号代码 ``内含 ` 单反引号`` 验证。

尖括号自动链接 <https://auto.example.com/link> 验证。

1\. 转义句点不是有序列表；\* 转义星号不成斜体。

实体透传：&copy; &amp; &#123; 不应双重转义。

白名单 HTML：<b>粗体</b>、<u>下划线</u>、<mark>标记</mark> 放行。

段尾两空格硬换行  
下一行继续。

段尾反斜杠硬换行\
下一行继续。

正常段落收尾，包含 HTML 转义验证 <tag> 与引号 "quote" 及 & 符号。
