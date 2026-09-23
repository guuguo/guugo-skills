# Persistent `sub-*.md` Template

Use only when a sub-block has long-term fact value. Do not use for execution phases.

Create under:

```text
docs/harness/specs/<需求目录>/sub-<中文短名>.md
```

```md
# 子需求：{名称}

## 创建理由

- 为什么不能只作为执行拆分：
- 独立长期事实价值：

## 与主需求关系

- 主需求：`plan.md`
- 关系：包含 / 依赖 / 例外 / 外部契约

## 独立目标

{只写这个子块独有的目标。}

## 独立范围

### 包含

- {scope}

### 不包含

- {non-goal}

## 差异事实

- {only differences from plan.md}

## 独立验收引用

- `acceptance.md#A?`

## 待确认问题

| 优先级 | 问题 | 推荐答案 | 状态 |
| --- | --- | --- | --- |
```

Do not copy the main background, generic constraints, or execution tasks.
