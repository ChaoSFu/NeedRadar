# Phase 2 — 数据地基

Phase 2 只交付一件事：**真实市场数据能持续进入 NeedRadar，且在进入过程中不丢失它的含义。**
Watchlist 操作、验证简报、UI 打磨全部明确排除在外。

本文档取代 [backend/SCHEMA.md](backend/SCHEMA.md) 中 `raw_signals` 的指标字段设计。
它记录的是那些**改起来代价极高**的决策，所以在写代码之前先定下来。

## 一、这套设计要防的四个失败

1. **指标坍缩。** Google Trends 给的是相对于本次请求的 0–100 搜索兴趣；百度指数给的是它自己的指数；
   千瓜给的是热度值；Reddit 给的是 upvote。把它们塞进同一个 `search_volume` 列是**类型错误**，
   而且是静默的：不会报错，只会让下游每一个分数都错。
2. **派生值污染证据。** SCHEMA.md 声明 `raw_signals` 不可变。
   如果把 `normalized_value` 写在 `raw_value` 旁边，就只能二选一：
   要么改归一化算法时去修改"不可变"的证据行，要么永远不能改算法。
3. **没有时间轴。** Momentum 占 Market Score 的 25%，并且撑起整个 "why now" 的主张。
   它是**时间导数**。一次性导入算不出它，而一个只跑过一次的管道，各项检查依然会显示绿色。
4. **簇不稳定。** 如果 DemandTopic 在两次运行之间不是同一个对象，它的时间序列就没有意义 ——
   Momentum 测量的将是"簇在漂移"，而不是需求在增长。

## 二、v0.1 范围：中国优先

v0.1 只服务 `CN` 市场。国际市场的表结构从第一天就存在（`market` 列贯穿全链路），
但不填充数据；前端预留市场切换入口并标记 TODO，不实现。

这个决定有一个直接后果需要记住：**Google Trends 对中国大陆无效**。
Google 在大陆基本不可用，其 "China" 切片来自极小且高度非代表性的人群。
它是本设计中唯一拥有官方 API 和真实搜索兴趣语义的数据源，
但在 v0.1 里它**不能**参与 `CN` 的需求打分或交叉验证。
这条约束由 `signal_sources.valid_markets` 在数据层强制执行，不依赖人的记忆。

## 三、分层

```text
Adapter（只负责抓取）
   └─ RawSignalDraft
        └─ Ingestion：去重 → 落库
             ├─ raw_signals      （不可变）
             └─ signal_metrics   （不可变）
                  └─ metric_normalizations  （派生、带版本、可重算）
                       └─ Topic 归属（确定性）
                            └─ demand_topics + topic_queries
                                 └─ Scoring（确定性、带版本）
                                      └─ opportunities + opportunity_snapshots
                                           └─ LLM：命名 / JTBD / pain / AI fit
```

两条贯穿所有层的不变量：

- **ingestion 线以上的任何东西都不写数据库。** Adapter 只返回 draft，只有 ingestion 管道落库。
- **LLM 永远不产出进入分数的数字。** 它负责命名、抽取、解释。Demand 和 Momentum 来自数据。

## 四、表结构

### `signal_sources`

```sql
CREATE TABLE signal_sources (
    id                    bigserial PRIMARY KEY,
    name                  text NOT NULL UNIQUE,
    platform              text NOT NULL,
    access_mode           text NOT NULL,   -- api | export | manual

    -- 该数据源对哪些市场产出【有效】的需求数据。
    -- Google Trends 不得包含 'CN'：Google 在大陆不可用，其中国切片来自
    -- 极小且非代表性的人群。交叉验证只统计对当前市场有效的数据源。
    valid_markets         text[] NOT NULL,

    -- 从该源派生的数据能否展示给终端用户。付费数据产品通常限制再分发；
    -- 做成列意味着这个约束由代码强制执行，而不是靠人记得。
    -- 条款确认前一律 internal_only（最严格）。
    redistribution_scope  text NOT NULL DEFAULT 'internal_only',
                                           -- internal_only | derived_only | full

    is_active             boolean NOT NULL DEFAULT true,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);
```

### `import_batches`

每一行落库的数据都能追溯到唯一一个批次。

```sql
CREATE TABLE import_batches (
    id                bigserial PRIMARY KEY,
    source_id         bigint NOT NULL REFERENCES signal_sources(id),
    adapter           text NOT NULL,
    adapter_version   text NOT NULL,
    collection_method text NOT NULL,   -- api_pull | file_export | manual_entry
    started_at        timestamptz NOT NULL DEFAULT now(),
    completed_at      timestamptz,
    status            text NOT NULL,   -- running | succeeded | failed | partial
    row_count         integer NOT NULL DEFAULT 0,
    accepted_count    integer NOT NULL DEFAULT 0,
    rejected_count    integer NOT NULL DEFAULT 0,
    error_summary     text
);
```

### `raw_signals` — 不可变，且不携带任何指标

```sql
CREATE TABLE raw_signals (
    id                bigserial PRIMARY KEY,
    source_id         bigint NOT NULL REFERENCES signal_sources(id),
    import_batch_id   bigint NOT NULL REFERENCES import_batches(id),

    query_text        text NOT NULL,
    content_excerpt   text,
    source_record_id  text,
    source_url        text,

    observed_at       date NOT NULL,        -- 这条观测【描述的】时间
    collected_at      timestamptz NOT NULL, -- 【我们】抓取它的时间

    country_code      text NOT NULL,        -- ISO 3166-1 alpha-2
    province_code     text,                 -- ISO 3166-2 省级
    city_code         text,                 -- 中国用 GB/T 2260，禁止自造编码
    geo_precision     text NOT NULL,        -- country | province | city | unknown

    -- 「广东」有三种完全不同的含义，绝不能合并：
    --   搜索行为来自广东 / 用户画像是广东 / 内容里提到广东
    geo_basis         text NOT NULL,        -- search_origin | audience_profile
                                            -- | content_location | platform_scope
                                            -- | unknown
    language          text,

    raw_payload       jsonb NOT NULL,
    raw_payload_hash  text NOT NULL,
    collector_version text NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT raw_signals_geo_precision_check
        CHECK (geo_precision IN ('country','province','city','unknown')),
    CONSTRAINT raw_signals_geo_basis_check
        CHECK (geo_basis IN ('search_origin','audience_profile',
                             'content_location','platform_scope','unknown')),
    CONSTRAINT raw_signals_dedupe UNIQUE (source_id, raw_payload_hash)
);
```

只允许 `INSERT`。repository 层不提供 `UPDATE` 路径。

### `signal_metrics` — 不可变，每个被测量的量一行

```sql
CREATE TABLE signal_metrics (
    id             bigserial PRIMARY KEY,
    raw_signal_id  bigint NOT NULL REFERENCES raw_signals(id),
    metric_name    text NOT NULL,   -- search_interest | hot_keyword_index
                                    -- | engagement_count | note_count | rank | ...
    raw_value      numeric NOT NULL,
    unit           text NOT NULL,   -- index_0_100 | platform_index | count | rank
    window_start   date NOT NULL,
    window_end     date NOT NULL,

    -- 这个值【是否允许】和另一个值比较。
    -- Google Trends 是 relative_within_request：两次不同请求的数值本就不可比，
    -- 除非两次请求共享了缩放锚点。归一化器据此【拒绝】执行非法比较，
    -- 而不是默默算出一个错的数。
    comparability  text NOT NULL,   -- absolute | relative_within_request
                                    -- | relative_within_platform | ordinal
    created_at     timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT signal_metrics_unique
        UNIQUE (raw_signal_id, metric_name, window_start, window_end)
);
```

任何指标都不得为了迁就另一个源的词汇而改名。
千瓜的热度值存为 `hot_keyword_index`，**永远不存为 `search_interest`**。

### `metric_normalizations` — 派生、带版本、可重算

```sql
CREATE TABLE metric_normalizations (
    id                    bigserial PRIMARY KEY,
    signal_metric_id      bigint NOT NULL REFERENCES signal_metrics(id),
    normalization_version text NOT NULL,   -- 例如 'demand-percentile@3'
    method                text NOT NULL,   -- percentile | zscore | minmax

    -- 该值是相对于【哪个参照分布】算出来的
    scope_key             text NOT NULL,   -- 'platform=xhs;market=CN;
                                           --  category=education;window=2026-W35'
    reference_n           integer NOT NULL,
    normalized_value      numeric NOT NULL,  -- 0..100
    computed_at           timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT metric_normalizations_unique
        UNIQUE (signal_metric_id, normalization_version)
);
```

**版本规则。** 归一化结果永不原地更新。改算法 = 以新的 `normalization_version` 写入新行 →
回填 → 在配置里切换生效版本。旧版本保持可读，历史快照因此保持可解释，
而不是在你不知情的情况下悄悄改变含义。

**拒绝规则。** 在自选关键词集合上算出的百分位，是你自己采样偏差的百分位，不是市场的百分位。
当 `reference_n < MIN_REFERENCE_N` 时，**不写入任何行**，下游需求分数是**缺失**而不是猜测。
"缺失"是一个合法的、可以展示给用户的状态。

### `demand_topics` / `topic_queries` / `topic_signals`

```sql
CREATE TABLE demand_topics (
    id                 bigserial PRIMARY KEY,
    slug               text NOT NULL UNIQUE,
    name               text NOT NULL,
    summary            text,
    category           text,
    centroid           vector(1024) NOT NULL,   -- pgvector，维度随所选模型
    embedding_model    text NOT NULL,
    clustering_version text NOT NULL,
    first_seen_at      timestamptz NOT NULL,
    last_seen_at       timestamptz NOT NULL,
    status             text NOT NULL DEFAULT 'active',
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

-- 同一个需求在不同平台、不同语言下的表达不同。
-- 「AI 英文面试」(小红书) 和 "AI interview practice" (Google Trends)
-- 是同一个 topic 的别名。没有这张表，跨源验证根本无法执行。
CREATE TABLE topic_queries (
    topic_id     bigint NOT NULL REFERENCES demand_topics(id),
    query_text   text NOT NULL,
    platform     text NOT NULL,
    market       text NOT NULL,
    is_canonical boolean NOT NULL DEFAULT false,
    PRIMARY KEY (topic_id, platform, query_text)
);

CREATE TABLE topic_signals (
    topic_id      bigint NOT NULL REFERENCES demand_topics(id),
    raw_signal_id bigint NOT NULL REFERENCES raw_signals(id),
    relevance     numeric NOT NULL,
    PRIMARY KEY (topic_id, raw_signal_id)
);
```

**稳定性规则。** 归属是确定性且增量的：把查询词做 embedding，与现有质心比较，
挂到相似度高于 `TOPIC_MATCH_THRESHOLD` 的最近 topic 上，只有全都不匹配时才新建 topic。

**LLM 绝不参与决定簇的成员归属** —— 非确定性的分组会让 topic 在两次运行之间变成不同的对象，
那么每一个 momentum 数字测量的都将是簇的漂移而不是需求。LLM 在 topic 存在之后才介入命名。

### `opportunities` / `opportunity_snapshots`

沿用 [backend/SCHEMA.md](backend/SCHEMA.md) 中的列，另加：

| 列 | 位置 | 用途 |
| --- | --- | --- |
| `market` | 两者 | 正在评分的市场（`CN`、`SG`、`US`），是枚举不是展示字符串 |
| `scoring_version` | 两者 | 产出这些数字的权重与公式版本 |
| `normalization_version` | 两者 | 输入来自哪个归一化版本 |
| `demand_score_suppressed` | 两者 | 参照集不足、需求分被抑制时为 true |
| `sources_confirming` | snapshot | 同向变动的、对该市场有效的数据源数量 |
| `sources_available` | snapshot | 当时该市场有效的数据源总数 |

只有 `scoring_version` 和 `normalization_version` 都相同的两个快照才可比较。
API 不得在跨版本的情况下直接画趋势图而不加说明。

### `watch_queries` / `collection_runs` — 时间轴

```sql
CREATE TABLE watch_queries (
    id         bigserial PRIMARY KEY,
    query_text text NOT NULL,
    platform   text NOT NULL,
    market     text NOT NULL,
    topic_id   bigint REFERENCES demand_topics(id),
    cadence    text NOT NULL,   -- daily | weekly
    -- 对照词：刻意选取的平淡关键词，用于撑开参照分布。
    -- 没有它们，百分位衡量的是你的选词偏好，而不是市场。
    is_control boolean NOT NULL DEFAULT false,
    is_active  boolean NOT NULL DEFAULT true,
    UNIQUE (query_text, platform, market)
);

CREATE TABLE collection_runs (
    id              bigserial PRIMARY KEY,
    scheduled_for   timestamptz NOT NULL,
    started_at      timestamptz,
    completed_at    timestamptz,
    status          text NOT NULL,
    import_batch_id bigint REFERENCES import_batches(id)
);
```

**对同一个稳定查询集合的重复采集，是 Momentum 得以存在的唯一前提。
只导入一次的 Phase 2，不是一个能工作的 Phase 2。**

## 五、Adapter 接口

Adapter 只负责抓取和整形。它不落库、不归一化、不打分、不去重。

```python
# backend/app/adapters/base.py
class CollectionRequest(BaseModel):
    queries: list[str]
    market: str
    window_start: date
    window_end: date


class MetricDraft(BaseModel):
    metric_name: str
    raw_value: Decimal
    unit: str
    window_start: date
    window_end: date
    comparability: str


class RawSignalDraft(BaseModel):
    query_text: str
    content_excerpt: str | None = None
    source_record_id: str | None = None
    source_url: str | None = None
    observed_at: date
    country_code: str
    province_code: str | None = None
    city_code: str | None = None
    geo_precision: str
    geo_basis: str
    language: str | None = None
    raw_payload: dict
    metrics: list[MetricDraft]


class SignalAdapter(Protocol):
    name: str
    version: str

    def fetch(self, request: CollectionRequest) -> Iterable[RawSignalDraft]: ...
```

**排期规则。** `csv` 和 `manual` 是参考实现，也是 Phase 2 **唯一必需**的 adapter。
千瓜、新红、百度指数、Google Trends、巨量算数，每一个都只是同一协议的又一个实现，
且**任何一个都不得位于「Phase 2 完成」的关键路径上**。
它们的访问权是商业的、合同的，或受限于未开放的 alpha，全都不在我们控制之内。
数据层必须在没有它们的情况下也是完整且可测试的。

访问条款是一条并行推进的独立任务：每个源在再分发和衍生商业产品方面允许什么，
必须在其数据触达终端用户之前确认。确认结果记录在 `signal_sources.redistribution_scope`，
在此之前保持默认的 `internal_only`。

## 六、冷启动期的评分策略

[backend/SCHEMA.md](backend/SCHEMA.md) 中的权重保持不变 ——
Demand 30%、Momentum 25%、Intent 20%、AI Fit 15%、Supply Gap 10%。
改变的是：在参照分布建立之前，哪些东西可以被信任。

**水平比较有偏，变化率没有。** 跨关键词的比较会继承"你选了哪些词来导入"的全部偏差；
同一关键词自身的时间序列则不会。所以在 `reference_n` 还小的阶段：

- **Momentum 被信任**：由 topic 自身历史的斜率、加速度、持续性算出。
- **Demand 被抑制而非估计**：Market Score 标记为部分结果，`demand_score_suppressed = true`。
- **刻意导入对照词**（`watch_queries.is_control`）来撑开参照分布，这是修正偏差的唯一手段，
  提高 `MIN_REFERENCE_N` 只能修正方差。

**交叉验证按市场分域。** 对 `CN` 的机会，有效数据源是 `valid_markets` 包含 `CN` 的那些；
Google Trends 不在其中。把无效源计入验证票数，等于用噪音抬高置信度 ——
而这恰恰是交叉验证机制本身要防的失败。

## 七、验收标准

| 能力 | 要求 |
| --- | --- |
| PostgreSQL + Alembic 迁移 | ✅ |
| `import_batches` 具备完整来源追溯 | ✅ |
| `raw_signals` / `signal_metrics` 分离，且均只允许插入 | ✅ |
| `raw_payload_hash` 去重，由一次重复导入实证 | ✅ |
| 结构化 Geo，含 `geo_basis` | ✅ |
| 归一化带版本、可重算，且不写入不可变表 | ✅ |
| `reference_n < MIN_REFERENCE_N` 时 Demand 被抑制 | ✅ |
| CSV adapter，且是 Phase 2 唯一必需的 adapter | ✅ |
| **同一查询集合在 ≥3 个不同时间点完成采集** | ✅ |
| **由该历史算出非平凡的 Momentum** | ✅ |
| **Topic 归属稳定：同输入在多次运行间 topic id 不变** | ✅ |
| 交叉验证只统计对该市场有效的数据源 | ✅ |
| Radar 能展示携带真实信号的 Opportunity | ✅ |

**刻意不设任何具体商业数据源的数量指标。**
那衡量的是供应商谈判进度，而不是数据地基是否可用。

## 八、已定决策

| # | 决策 | 结论 |
| --- | --- | --- |
| 1 | v0.1 目标市场 | **中国优先。** `market` 列全链路存在，国际市场表结构预留、前端预留入口标 TODO、不实现 |
| 2 | `MIN_REFERENCE_N` | **100**，且参照集中 **≥30% 为对照词**（`is_control = true`）。门槛治方差，对照词治偏差，缺一不可 |
| 3 | Demand 被抑制时的 UI | Opportunity 正常展示，Momentum 正常展示，Demand 显示 `—` 并注明 `参照样本不足 (N=23/100)`，Market Score 标为部分并列出缺失分项。**禁止填充默认值** |
| 4 | Embedding 模型 | **阿里云百炼 DashScope `text-embedding-v3`。** 服务器为 2核2G 且位于深圳，本地推理不可行、访问境外 API 不稳定；这不是技术最优解，是当前基础设施下唯一顺畅的选择。模型名记录在 `demand_topics.embedding_model`，换模型必须重跑标定 |
| 5 | `redistribution_scope` | 全部默认 **`internal_only`**，逐源在条款确认后放宽。不阻塞 Phase 2，因为验收标准不含任何商业源 |

## 九、待标定项

`TOPIC_MATCH_THRESHOLD` **无法从第一性原理推导**，必须在真实数据上标定。
它取决于所选 embedding 模型和实际查询词分布。暂定占位值 **0.82**，
在标定完成前明确标记为不可信。

标定流程：

1. 取约 200 条真实查询词，**人工标注**哪些属于同一需求
2. 阈值从 0.70 到 0.95 扫描，选与人工标注吻合度最高的
3. **稳定性测试**：同一批数据加少量新数据连跑两次，检查 topic id 是否错乱

第 3 步比第 2 步更重要：分得准但不稳定，时间序列一样是废的。

两端的失败形态：

```text
阈值过低（0.60）  →  「AI英文面试」与「AI高校答辩」合并成笼统的「AI模拟练习」，
                     具体机会消失

阈值过高（0.95）  →  「AI英文面试」与「AI英文面试练习」分裂成两个 topic，
                     下周同一需求又落到第三个上，每个 topic 只有一两个时间点，
                     Momentum 无从算起
```
