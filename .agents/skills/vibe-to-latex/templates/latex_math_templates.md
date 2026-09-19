# LaTeX Math & Theorem Environment Templates

以下是可直接用于 NeurIPS / ICLR / ICML 格式的标准 LaTeX 模板代码块：

## 1. Problem Formulation & Setup (问题形式化)

```latex
\section{Problem Formulation and Preliminaries}
\label{sec:preliminaries}

Let $\mathcal{G} = (\mathcal{V}, \mathcal{E}, \mathbf{W})$ denote a weighted graph representing the dynamical interaction network, where $|\mathcal{V}| = N$ vertices and $\mathbf{W} \in \mathbb{R}^{N \times N}_{+}$ is the adjacency weight matrix. The normalized graph Laplacian operator is defined as $\mathbf{L} = \mathbf{I}_N - \mathbf{D}^{-1/2} \mathbf{W} \mathbf{D}^{-1/2}$, with degree matrix $\mathbf{D}_{ii} = \sum_{j} \mathbf{W}_{ij}$.

\begin{definition}[Spectral Instability Index]
\label{def:spectral_instability}
Given a temporal trajectory of states $\{\mathbf{x}(t)\}_{t \ge 0}$ evolving on manifold $\mathcal{M}$, the \emph{Spectral Instability Index} $\Phi(t)$ is defined as:
\begin{equation}
    \Phi(t) \triangleq \sum_{k=1}^{K} \omega_k \log \left( 1 + \frac{1}{\lambda_k(t) + \epsilon} \right),
\end{equation}
where $\lambda_1(t) \le \lambda_2(t) \le \dots \le \lambda_K(t)$ denote the $K$ smallest non-zero eigenvalues of the instantaneous differential operator $\mathcal{L}_t$, and $\omega_k > 0$ are spectral decay weights.
\end{definition}
```

---

## 2. Theoretical Guarantee (定理与证明骨架)

```latex
\begin{theorem}[Early Warning Bounds under Perturbation]
\label{thm:early_warning_bound}
Assume the dynamical system undergoes a supercritical Hopf bifurcation at critical time $t^*$. Under additive observation noise $\boldsymbol{\xi}_t \sim \mathcal{N}(0, \sigma^2 \mathbf{I})$, there exists a positive constant $C(\sigma)$ such that for any threshold $\tau > 0$, the early detection lead time $\Delta t \triangleq t^* - t_{\mathrm{detect}}$ satisfies:
\begin{equation}
    \mathbb{P}\left( \Delta t \ge C(\sigma) \cdot \frac{1}{\sqrt{\gamma_0}} \log \frac{1}{\tau} \right) \ge 1 - \exp\left( -\frac{\kappa^2}{2\sigma^2} \right),
\end{equation}
where $\gamma_0$ is the unperturbed spectral gap and $\kappa$ characterizes the sectional curvature bound on $\mathcal{M}$.
\end{theorem}

\begin{proof}[Proof Sketch]
The proof proceeds in two steps. First, we apply the Davis-Kahan $\sin\Theta$ theorem to bound the eigenvector deviation under perturbation $\boldsymbol{\xi}_t$. Second, by constructing a Lyapunov barrier function along the tangent bundle, we demonstrate that the spectral gap $\gamma(t)$ decays exponentially as $t \to t^*$. The full formal proof is deferred to Appendix~\ref{app:proof_thm1}.
\end{proof}
```

---

## 3. Algorithm Pseudocode (算法伪代码)

```latex
\begin{algorithm}[t]
\caption{Generic Project Framework Indicator (\texttt{OursMethod})}
\label{alg:OursMethod}
\begin{algorithmic}[1]
\REQUIRE State trajectory $\{\mathbf{x}_t\}_{t=1}^T$, window size $W$, spectral truncation rank $K$, threshold $\tau$.
\ENSURE Early warning trigger flag $F \in \{0, 1\}$, warning timestamp $t_{\mathrm{warn}}$.
\STATE Initialize rolling buffer $\mathcal{B} \leftarrow \emptyset$, $F \leftarrow 0$.
\FOR{$t = 1, 2, \dots, T$}
    \STATE Append $\mathbf{x}_t$ to $\mathcal{B}$.
    \IF{$|\mathcal{B}| \ge W$}
        \STATE Compute empirical covariance / Laplacian $\mathbf{L}_t \leftarrow \mathrm{EstimateLaplacian}(\mathcal{B})$.
        \STATE Compute smallest $K$ eigenvalues $\{\lambda_k(t)\}_{k=1}^K$ of $\mathbf{L}_t$.
        \STATE Calculate spectral instability $\Phi(t) \leftarrow \mathrm{EvalIndex}(\{\lambda_k(t)\})$.
        \IF{$\Phi(t) \ge \tau$ \AND $F == 0$}
            \STATE $F \leftarrow 1$, $t_{\mathrm{warn}} \leftarrow t$.
            \STATE \textbf{emit} \texttt{"Critical Transition Imminent at"} $t_{\mathrm{warn}}$.
        \ENDIF
    \ENDIF
\ENDFOR
\RETURN $F, t_{\mathrm{warn}}$
\end{algorithmic}
\end{algorithm}
```

