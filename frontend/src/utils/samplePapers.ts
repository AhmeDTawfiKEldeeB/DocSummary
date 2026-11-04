export interface SamplePaper {
  id: string;
  title: string;
  authors: string;
  year: number;
  filename: string;
  fileSizeBytes: number;
  pageCount: number;
  expectedPipeline: 'SMALL_DOC' | 'LARGE_DOC';
  summaryMarkdown: string;
}

export const SAMPLE_RESEARCH_PAPERS: SamplePaper[] = [
  {
    id: 'deepseek-r1',
    title: 'DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning',
    authors: 'DeepSeek-AI Team',
    year: 2025,
    filename: 'deepseek_r1_reasoning_study.pdf',
    fileSizeBytes: 3_840_000,
    pageCount: 32,
    expectedPipeline: 'LARGE_DOC',
    summaryMarkdown: `# DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning

> **Executive Brief:** DeepSeek-R1 represents a pivotal shift in training reasoning models. By applying large-scale reinforcement learning (RL) directly without prior supervised fine-tuning (SFT), the model autonomously develops multi-step chain-of-thought, self-verification, and self-correction capabilities comparable to OpenAI's o1-0912.

---

## 1. Core Architectural & Methodological Innovations

The research explores two distinct training paradigms designed to instill robust reasoning behaviors in language models: **DeepSeek-R1-Zero** (pure RL without human demonstrations) and **DeepSeek-R1** (multi-stage training with cold-start data).

### 1.1 Pure Reinforcement Learning: DeepSeek-R1-Zero

- **Direct Policy Optimization:** Applied Group Relative Policy Optimization (GRPO) directly to the base model *DeepSeek-V3-Base*.
- **Rule-Based Reward Model:** Replaced complex learned reward neural networks with deterministic, verifiable outcome verifiers:
  - *Accuracy Rewards:* Automated unit-testing for code outputs and symbolic match for mathematical results.
  - *Formatting Rewards:* Enforcing structured \`<think>...</think>\` reasoning traces before producing the final response.
- **Emergence of Cognitive Behaviors:**
  - Dynamic Chain-of-Thought (CoT) generation extending up to tens of thousands of tokens.
  - Spontaneous "Aha Moments" where the model identifies logical flaws in prior reasoning steps and restarts search branches.

### 1.2 Two-Stage RL Pipeline: DeepSeek-R1

To resolve language inconsistency and readability degradation observed in DeepSeek-R1-Zero, the authors introduced an orchestrated 4-stage pipeline:

1. **Cold-Start Data Collection:** Curated thousands of long CoT examples via few-shot prompting, human post-editing, and structured templates.
2. **Reasoning-Oriented RL (Stage 1):** Large-scale GRPO focused strictly on coding, mathematics, and logic verification.
3. **Rejection Sampling & General SFT:** Combining 600k verified reasoning traces with 200k non-reasoning instruction-following pairs.
4. **All-Scenario Alignment RL (Stage 2):** Secondary RL phase balancing helpfulness, harmlessness, preference alignment, and concise answering.

---

## 2. Key Empirical Findings & Benchmark Evaluation

DeepSeek-R1 was benchmarked against state-of-the-art open and proprietary frontier models.

### 2.1 Benchmark Performance Matrix

| Evaluation Benchmark | Domain | DeepSeek-V3 | OpenAI-o1-0912 | DeepSeek-R1 | Relative Improvement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AIME 2024 (Pass@1)** | Olympiad Math | 39.2% | 79.2% | **79.8%** | +103.5% |
| **MATH-500** | Advanced Math | 74.8% | 96.4% | **97.3%** | +30.1% |
| **Codeforces (Percentile)** | Competitive Code | 58.7% | 96.6% | **96.3%** | +64.1% |
| **MMLU (Acc)** | General Knowledge | 88.5% | 91.8% | **90.8%** | +2.6% |
| **SWE-bench Verified** | Software Eng | 41.6% | 48.9% | **49.2%** | +18.3% |

### 2.2 Distillation vs. RL from Scratch for Small Models

A central contribution is demonstrating that **distilling reasoning traces from DeepSeek-R1 into smaller dense architectures (1.5B to 32B)** outperforms applying direct RL on small base models:

- **DeepSeek-R1-Distill-Qwen-32B** achieved **72.6% on AIME 2024**, surpassing o1-mini.
- **DeepSeek-R1-Distill-Qwen-1.5B** scored **28.9% on AIME 2024**, demonstrating unprecedented reasoning density in sub-2B parameter regimes.

---

## 3. Critical Analysis & Engineering Trade-offs

### 3.1 Advantages
- **Elimination of Annotation Bottleneck:** Rule-based rewards drastically reduce dependence on costly human-annotated reasoning steps.
- **Self-Correcting Search:** Explicit reasoning loops mimic Monte Carlo Tree Search (MCTS) without requiring external search tree infrastructure during inference.
- **Democratized Frontier Weights:** Open weights for both the full 671B MoE and distilled models enable verifiable local deployment.

### 3.2 Limitations & Known Failure Modes
- **Language Mixing:** The model occasionally oscillates between English and Chinese within internal thinking chains when prompted in multilingual contexts.
- **Inference Latency:** Extremely long reasoning traces (averaging 4,000–12,000 thinking tokens) increase per-request compute requirements and latency.
- **Software Engineering Tasks:** On interactive multi-turn debugging benchmarks, performance gains are less pronounced compared to single-turn mathematical proofs.

---

## 4. Synthesis & Practical Takeaways

- **Architecture Strategy:** Complex multi-step reasoning can be acquired through reinforcement learning driven solely by objective rule-based reward verifiers.
- **Deployment Recommendation:** For production workloads requiring high reasoning accuracy, \`DeepSeek-R1-Distill-Qwen-32B\` offers the optimal cost-performance Pareto frontier.
- **Future Direction:** Unifying search-based reasoning with tool-augmented execution and autonomous multi-agent code refactoring.
`,
  },
  {
    id: 'attention-is-all-you-need',
    title: 'Attention Is All You Need',
    authors: 'Vaswani et al. (Google Brain & Google Research)',
    year: 2017,
    filename: 'attention_is_all_you_need.pdf',
    fileSizeBytes: 2_210_000,
    pageCount: 11,
    expectedPipeline: 'SMALL_DOC',
    summaryMarkdown: `# Attention Is All You Need: Architectural Paradigm Analysis

> **Executive Brief:** The seminal 2017 paper by Vaswani et al. introduced the **Transformer**, replacing recurrent neural networks (RNNs) and convolutional architectures entirely with multi-head self-attention mechanisms. This transition unlocked massive parallelization during training and became the foundational architecture for modern Large Language Models.

---

## 1. Architectural Foundation

Prior sequence transduction models relied heavily on sequential RNN cells (LSTM, GRU), which suffered from linear computation time complexity $O(n)$ with respect to sequence length, fundamentally bottlenecking GPU hardware acceleration.

### 1.1 The Multi-Head Attention Mechanism

The Transformer computes attention scores across query, key, and value vectors:

$$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$$

- **Scaled Dot-Product:** Dividing by $\\sqrt{d_k}$ prevents gradients from vanishing in high-dimensional spaces where dot products grow excessively large.
- **Multi-Head Projections:** Rather than computing single attention matrices, queries, keys, and values are projected into $h = 8$ distinct representation subspaces, enabling the network to jointly attend to semantic, syntactic, and positional cues simultaneously.

### 1.2 Positional Encodings & Feed-Forward Sublayers

- **Sinusoidal Position Functions:** Because self-attention has no innate sense of sequence ordering, geometric sinusoids are injected into input embeddings.
- **Position-Wise FFN:** Each attention layer is followed by a two-layer feed-forward network with ReLU activation and residual skip-connections.

---

## 2. Key Empirical Results & Efficiency

The paper validated the Transformer on standard machine translation benchmarks:

- **WMT 2014 English-to-German:** Established a new state-of-the-art **28.4 BLEU**, improving over existing ensemble models by over 2.0 BLEU.
- **WMT 2014 English-to-French:** Achieved **41.0 BLEU** after training for 3.5 days on 8 NVIDIA P100 GPUs.
- **Training Speedup:** Reduced training cost to a fraction of ByteNet and GNMT architectures due to removing sequential recurrent time steps.

---

## 3. Practical Implications

- **Pervasive AI Architecture:** The Transformer encoder-decoder pattern birthed subsequent generational breakthroughs including BERT (encoder-only), GPT series (decoder-only), and T5 (encoder-decoder).
- **Scalability Frontier:** Provided the structural baseline that demonstrated direct power-law scaling properties with parameter and dataset size.
`,
  },
];
