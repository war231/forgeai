# 题材配置档案 (Genre Profiles)

> **来源**：Webnovel Writer genre-profiles.md（精简版）

---

## Profile 字段说明

| 字段 | 说明 |
|------|------|
| `preferred_hooks` | 偏好钩子类型 |
| `preferred_patterns` | 偏好爽点模式 |
| `density_per_chapter` | 爽点密度：high(2+)/medium(1)/low(0-1) |
| `min_micropayoff` | 每章微兑现下限 |
| `strand_quest_max` | Quest主线最大连续章数 |
| `strand_fire_gap_max` | Fire感情线最大断档章数 |
| `stagnation_threshold` | 节奏停滞阈值（连续N章无推进=HARD-003）|

---

## 内置题材 Profiles

### 爽文/系统流 (shuangwen)

```yaml
preferred_hooks: [渴望钩, 危机钩, 情绪钩]
preferred_patterns: [装逼打脸, 扮猪吃虎, 越级反杀, 迪化误解]
density_per_chapter: high
min_micropayoff: 2
strand_quest_max: 5
strand_fire_gap_max: 15
stagnation_threshold: 3
```

### 修仙/仙侠 (xianxia)

```yaml
preferred_hooks: [渴望钩, 危机钩, 悬念钩]
preferred_patterns: [越级反杀, 扮猪吃虎, 身份掉马]
density_per_chapter: medium
min_micropayoff: 1
strand_quest_max: 5
strand_fire_gap_max: 12
stagnation_threshold: 4
```

### 都市异能 (urban-power)

```yaml
preferred_hooks: [情绪钩, 渴望钩, 危机钩]
preferred_patterns: [装逼打脸, 打脸权威, 迪化误解]
density_per_chapter: high
min_micropayoff: 2
strand_quest_max: 4
strand_fire_gap_max: 10
stagnation_threshold: 3
```

### 古言/宫斗 (ancient-romance)

```yaml
preferred_hooks: [情绪钩, 选择钩, 悬念钩]
preferred_patterns: [甜蜜超预期, 反派翻车, 身份掉马]
density_per_chapter: medium
min_micropayoff: 1
strand_quest_max: 5
strand_fire_gap_max: 8
stagnation_threshold: 4
```

### 悬疑/规则怪谈 (mystery)

```yaml
preferred_hooks: [悬念钩, 危机钩, 选择钩]
preferred_patterns: [越级反杀, 反派翻车]
density_per_chapter: low
min_micropayoff: 1
strand_quest_max: 6
strand_fire_gap_max: 15
stagnation_threshold: 4
```

### 科幻/末世 (scifi)

```yaml
preferred_hooks: [危机钩, 渴望钩, 悬念钩]
preferred_patterns: [越级反杀, 扮猪吃虎, 打脸权威]
density_per_chapter: medium
min_micropayoff: 1
strand_quest_max: 5
strand_fire_gap_max: 12
stagnation_threshold: 4
```

### 日常/轻松 (daily)

```yaml
preferred_hooks: [情绪钩, 渴望钩]
preferred_patterns: [甜蜜超预期, 迪化误解]
density_per_chapter: low
min_micropayoff: 1
strand_quest_max: 3
strand_fire_gap_max: 8
stagnation_threshold: 5
```

---

## 复合题材规则

- 支持 `题材A+题材B`（最多2个）
- 主辅比例 7:3
- 主线遵循主题材逻辑，副题材提供钩子/规则/爽点

示例：
- `都市脑洞+规则怪谈`
- `修仙+系统流`
- `古言+悬疑`
