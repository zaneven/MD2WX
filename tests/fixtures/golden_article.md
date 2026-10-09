# MD2WX 双端渲染一致性评测样例

这是一段包含**加粗**、*斜体*、`行内代码` 与 ~~删除线~~ 的正文段落，
同时附带一个裸链接 https://example.com/docs/page 用于自动脚注转换验证。

## 二级标题：排版组件

### 三级小标题

#### 四级标题按三级渲染

- 无序列表项一
- 无序列表项二 **带加粗**
- [x] 已完成任务项
- [ ] 未完成任务项

1. 这不是有序列表语法，按普通段落处理

> 这是一段引言块内容，包含 `代码` 与 [带文本的外链](https://docs.example.com/api)。
>
> 引言块的第二行。

| 模块 | 职责 | 状态 |
| --- | --- | --- |
| parser | 核心解析引擎 | 稳定 |
| cover | 封面渲染 | `beta` |

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

![示例图片](https://cdn.example.com/img/hero.png "hero")

*▲ 图：示例图注*

---

正常段落收尾，包含 HTML 转义验证 <tag> 与引号 "quote" 及 & 符号。
