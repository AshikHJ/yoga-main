# Mathematical Formulations and Algorithmic Specifications

This document outlines the mathematical and algorithmic foundations powering the AI Yoga Assistant.

---

## 1. Joint Angle Calculation Formulation

Joint angles are computed at the anatomical vertex $B$ formed by landmark coordinates $A = (x_a, y_a)$ and $C = (x_c, y_c)$.

### Vector Definitions
$$\vec{u} = \vec{BA} = \begin{bmatrix} x_a - x_b \\ y_a - y_b \end{bmatrix}, \quad \vec{v} = \vec{BC} = \begin{bmatrix} x_c - x_b \\ y_c - y_b \end{bmatrix}$$

### Euclidean Norms & Dot Product
$$\|\vec{u}\| = \sqrt{(x_a - x_b)^2 + (y_a - y_b)^2}, \quad \|\vec{v}\| = \sqrt{(x_c - x_b)^2 + (y_c - y_b)^2}$$
$$\vec{u} \cdot \vec{v} = (x_a - x_b)(x_c - x_b) + (y_a - y_b)(y_c - y_b)$$

### Interior Angle Formulation
$$\cos(\theta) = \text{clip}\left(\frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\| \|\vec{v}\|}, -1.0, 1.0\right)$$
$$\theta = \arccos(\cos(\theta)) \times \left(\frac{180^\circ}{\pi}\right)$$

Where $\theta \in [0.0^\circ, 180.0^\circ]$.

### Spine & Torso Vertical Alignment
For mid-shoulder point $P_{top} = (x_t, y_t)$ and mid-hip point $P_{bottom} = (x_b, y_b)$:
$$\Delta x = x_t - x_b, \quad \Delta y = y_b - y_t \quad (\text{inverted image coordinate correction})$$
$$\theta_{vertical} = \text{atan2}(\Delta y, \Delta x) \times \left(\frac{180^\circ}{\pi}\right)$$

---

## 2. Posture Accuracy Scoring Algorithm

For a given joint $i$ with measured angle $\theta_i$, target angle $\theta_{target, i}$, and tolerance $\delta_i$:

### Absolute Deviation
$$\Delta_i = |\theta_i - \theta_{target, i}|$$

### Granular Joint Score Function
$$S_i(\Delta_i) = \begin{cases} 
100 - \left(\frac{\Delta_i}{\delta_i} \times 10\right), & \text{if } \Delta_i \le \delta_i \\
\max\left(0, 90 - \frac{\Delta_i - \delta_i}{\text{span}_{penalty}} \times 90\right), & \text{if } \Delta_i > \delta_i
\end{cases}$$

Where $\text{span}_{penalty} = 45.0^\circ$.

### Aggregate Weighted Posture Score
Given joint weights $w_i \ge 1$:
$$\text{Total Score} = \frac{\sum_{i=1}^{N} S_i \times w_i}{\sum_{i=1}^{N} w_i}, \quad \text{Total Score} \in [0.0, 100.0]$$

### Qualitative Score Tiers
- **$90.0 \le \text{Score} \le 100.0$**: **Excellent Posture** (Green `#10B981`)
- **$80.0 \le \text{Score} < 90.0$**: **Good Posture** (Cyan `#06B6D4`)
- **$70.0 \le \text{Score} < 80.0$**: **Needs Improvement** (Amber `#F59E0B`)
- **$\text{Score} < 70.0$**: **Incorrect / Needs Correction** (Red `#EF4444`)

---

## 3. Pose Identification Heuristic

To identify the pose currently being performed across the catalog:
$$\text{MatchScore}(P) = \frac{\sum_{j \in \text{Rules}(P)} S_j \times w_j}{\sum_{j \in \text{Rules}(P)} w_j}$$
$$P^* = \arg\max_{P \in \text{Catalog}} \text{MatchScore}(P)$$

- If $\text{MatchScore}(P^*) \ge 65.0\%$: Identified as $P^*$.
- If $50.0\% \le \text{MatchScore}(P^*) < 65.0\%$: Transitioning into $P^*$.
- Otherwise: Unknown / Neutral Stance.

---

## 4. Multi-Frame Custom Reference Capture

When capturing a custom pose template:
1. $M = 30$ consecutive frames are sampled while the subject holds the pose.
2. For each joint $j$, the sample mean $\bar{\theta}_j$ and standard deviation $\sigma_j$ are calculated:
   $$\bar{\theta}_j = \frac{1}{M}\sum_{k=1}^M \theta_{j, k}, \quad \sigma_j = \sqrt{\frac{1}{M}\sum_{k=1}^M (\theta_{j, k} - \bar{\theta}_j)^2}$$
3. Adaptive tolerance $\delta_j$ is initialized from natural body tremor:
   $$\delta_j = \text{clamp}(2.5 \times \sigma_j, 10.0^\circ, 25.0^\circ)$$

---

## 5. Personalized Recommendation Engine

Recommendations combine 4 primary factors:
1. **Goal Compatibility**:
   $$\text{Score}_{goal}(P) = \begin{cases} 1.0, & \text{if } P.goal = U.goal \text{ or } P.category = U.goal \\ 0.5, & \text{otherwise} \end{cases}$$
2. **Difficulty Progression**:
   $$\text{Score}_{diff}(P, U) = \begin{cases} 1.0, & \text{if } P.difficulty = U.experience \\ 0.8, & \text{if } P \text{ is adjacent difficulty} \\ 0.3, & \text{otherwise} \end{cases}$$
3. **Weakness Correction Priority**:
   For poses with historical session average $\bar{S}_{hist}(P) < 80.0\%$:
   $$\text{Priority}_{weakness}(P) = 100.0 - \bar{S}_{hist}(P)$$
4. **Daily Routine Sequencing**:
   Constructs a balanced routine consisting of $[P_{warmup}, P_{peak\_1}, P_{peak\_2}, P_{cooldown}]$.
