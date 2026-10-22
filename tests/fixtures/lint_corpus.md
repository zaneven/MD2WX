---
title: 这是一篇刻意写得超长的标题用来校验双端一致性检测能力
digest: 摘要混用半角逗号,还混用分号;同时长度明显超过五十个字的上限会被阻断规则拦下来
cover: ./cover.png
---

# 这是一篇刻意写得超长的标题用来校验双端一致性检测能力

正文直接跳到三级标题,并混用半角冒号:测试全半角标点规则。

### 三级小节

```text
# 代码围栏里的假标点,以及 <div> 标签都不应被检测
```

![](https://cdn.example.com/dup.png)

![](https://cdn.example.com/dup.png)

[坏协议](htp://example.com/a) 与 [缺少协议](www.example.com) 以及 [空链接]()

<div>未闭合的容器

正文里的表情 😀 也需要被检出。
